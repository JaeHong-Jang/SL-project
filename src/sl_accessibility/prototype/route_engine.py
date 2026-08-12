"""단계 3 — M0/M3 경로 엔진 (docs/prototype_plan.md v2).

서버 시작 시 단계 2 산출물을 한 번만 로드하고, 요청마다:
좌표 스냅(100m) → SciPy Dijkstra(predecessor) → 노드열 복원 →
프로필별 대표 edge_id 지오메트리(방향 정합) → M0/M3 비교 → 고정 M3 경로 부담 분해.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import shapely
from pyproj import Transformer
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

from sl_accessibility.accessibility.costs import CostParameters

WEATHER_TO_PROFILE = {
    "clear": "m3_dry",
    "cloudy": "m3_dry",
    "rain": "m3_rain_2mm",
    "snow": "m3_snow_1cm",
}
WEATHER_VALUES = {
    "clear": (0.0, 0.0),
    "cloudy": (0.0, 0.0),
    "rain": (2.0, 0.0),
    "snow": (0.0, 1.0),
}
GRADE_BUCKETS = [(0, 5, "0-5%"), (5, 10, "5-10%"), (10, 15, "10-15%"),
                 (15, 20, "15-20%"), (20, 30, "20-30%"), (30, float("inf"), "30%+")]


class RouteError(Exception):
    """도메인 오류. code: origin_snap_failed | unknown_stop | same_node | no_path"""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def grade_bucket(g: float) -> str:
    for lo, hi, label in GRADE_BUCKETS:
        if lo <= g < hi:
            return label
    return GRADE_BUCKETS[-1][2]


def _rounded_breakdown(b: dict) -> dict:
    """0.1m 반올림 후에도 항목 합계 == 총계가 되도록 최대 항목에 잔여를 보정한다."""
    parts = ["physical_m", "slope_m", "weather_m", "interaction_m"]
    rounded = {k: round(b[k], 1) for k in parts}
    total = round(b["total_m"], 1)
    diff = round(total - sum(rounded.values()), 1)
    if diff:
        largest = max(parts, key=lambda k: rounded[k])
        rounded[largest] = round(rounded[largest] + diff, 1)
    rounded["total_m"] = total
    return rounded


@dataclass
class _Graph:
    matrix: csr_matrix
    indptr: np.ndarray
    indices: np.ndarray
    edge_ids: np.ndarray


class RouteEngine:
    def __init__(self, artifacts_dir: Path, snap_max_m: float = 100.0):
        self.dir = Path(artifacts_dir)
        self.snap_max_m = float(snap_max_m)
        self.params = CostParameters()

        n = np.load(self.dir / "nodes.npz")
        self.node_id = n["node_id"]
        self.node_xy = np.c_[n["x"], n["y"]]
        self.node_lonlat = np.c_[n["lon"], n["lat"]]
        self.n_nodes = len(self.node_id)
        self.kdtree = cKDTree(self.node_xy)
        self.to_5179 = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)
        self.to_4326 = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True)

        self.graphs: dict[str, _Graph] = {}
        for profile in ["m0", "m3_dry", "m3_rain_2mm", "m3_snow_1cm"]:
            a = np.load(self.dir / f"graph_{profile}.npz")
            m = csr_matrix(
                (a["data"], a["indices"], a["indptr"]), shape=(self.n_nodes, self.n_nodes)
            )
            self.graphs[profile] = _Graph(m, a["indptr"], a["indices"], a["edge_ids"])

        e = pd.read_parquet(self.dir / "edges.parquet")
        self.edges = e.set_index("edge_id")
        self.stops = pd.read_parquet(self.dir / "stops_snap.parquet").set_index("stop_id")

    # ---------- 스냅 ----------

    def snap(self, lng: float, lat: float) -> tuple[int, float]:
        x, y = self.to_5179.transform(lng, lat)
        dist, idx = self.kdtree.query([x, y], distance_upper_bound=self.snap_max_m)
        if not np.isfinite(dist):
            raise RouteError(
                "origin_snap_failed",
                f"입력 지점에서 {self.snap_max_m:.0f}m 이내에 보행망 노드가 없습니다.",
            )
        return int(idx), float(dist)

    def stop_node(self, stop_id: str) -> tuple[int, float]:
        if stop_id not in self.stops.index:
            raise RouteError("unknown_stop", f"알 수 없는 정류장입니다: {stop_id}")
        row = self.stops.loc[stop_id]
        return int(row["node_idx"]), float(row["snap_m"])

    # ---------- 경로 탐색 ----------

    def _shortest(self, profile: str, src: int, dst: int) -> tuple[float, list[int]]:
        dist, pred = dijkstra(
            self.graphs[profile].matrix, indices=src, return_predecessors=True
        )
        if not np.isfinite(dist[dst]):
            raise RouteError("no_path", "보행망에서 두 지점을 잇는 경로가 없습니다.")
        path = [dst]
        while path[-1] != src:
            p = pred[path[-1]]
            if p < 0:
                raise RouteError("no_path", "경로 복원에 실패했습니다.")
            path.append(int(p))
        path.reverse()
        return float(dist[dst]), path

    def _path_edge_ids(self, profile: str, path: list[int]) -> list[int]:
        g = self.graphs[profile]
        out = []
        for a, b in zip(path[:-1], path[1:]):
            lo, hi = g.indptr[a], g.indptr[a + 1]
            pos = lo + int(np.searchsorted(g.indices[lo:hi], b))
            if pos >= hi or g.indices[pos] != b:
                raise RouteError("no_path", "경로 엣지 조회에 실패했습니다.")
            out.append(int(g.edge_ids[pos]))
        return out

    def _edge_geometry_4326(self, edge_id: int, from_idx: int) -> list[list[float]]:
        row = self.edges.loc[edge_id]
        geom = shapely.from_wkt(row["geometry_wkt"])
        coords = np.asarray(geom.coords)
        # 방향 정합: 시작점이 from 노드와 더 가깝도록 뒤집는다.
        start = self.node_xy[from_idx]
        if np.sum((coords[0] - start) ** 2) > np.sum((coords[-1] - start) ** 2):
            coords = coords[::-1]
        lon, lat = self.to_4326.transform(coords[:, 0], coords[:, 1])
        return [[round(float(a), 6), round(float(b), 6)] for a, b in zip(lon, lat)]

    # ---------- 부담 분해 (M3 경로 고정) ----------

    def _decompose(self, edge_ids: list[int], weather: str) -> dict:
        p = self.params
        rain, snow = WEATHER_VALUES[weather]
        intensity = max(rain, 0.0) + p.snow_weight * max(snow, 0.0)
        rows = self.edges.loc[edge_ids]
        d = rows["length_m"].to_numpy()
        g = np.clip(rows["grade_abs_percent_cop"].to_numpy(), None, p.cap_grade_abs_percent)
        m0 = d
        m1 = d * (1.0 + p.slope_alpha * g)
        m2 = m1 * (1.0 + p.weather_beta * intensity)
        m3 = m1 * (1.0 + p.weather_beta * intensity + p.interaction_beta * intensity * g / 100.0)
        return {
            "physical_m": float(np.sum(m0)),
            "slope_m": float(np.sum(m1 - m0)),
            "weather_m": float(np.sum(m2 - m1)),
            "interaction_m": float(np.sum(m3 - m2)),
            "total_m": float(np.sum(m3)),
        }

    # ---------- 공개 API ----------

    def route(self, origin_lng: float, origin_lat: float, stop_id: str, weather: str) -> dict:
        if weather not in WEATHER_TO_PROFILE:
            raise RouteError("unknown_weather", f"지원하지 않는 날씨: {weather}")
        src, origin_snap_m = self.snap(origin_lng, origin_lat)
        dst, stop_snap_m = self.stop_node(stop_id)
        if src == dst:
            raise RouteError("same_node", "출발지와 도착지가 같은 보행망 노드에 스냅되었습니다.")

        profile = WEATHER_TO_PROFILE[weather]
        m0_cost, m0_path = self._shortest("m0", src, dst)
        m3_cost, m3_path = self._shortest(profile, src, dst)
        m0_edges = self._path_edge_ids("m0", m0_path)
        m3_edges = self._path_edge_ids(profile, m3_path)

        breakdown = self._decompose(m3_edges, weather)
        assert abs(breakdown["total_m"] - m3_cost) < 0.01, "분해 합계가 총부담과 불일치"
        assert m3_cost >= m0_cost - 1e-6, "min(M3) < min(M0) — 비용 정의 위반"

        m3_rows = self.edges.loc[m3_edges]
        m3_physical = float(m3_rows["length_m"].sum())
        segments = []
        for eid, (a, b) in zip(m3_edges, zip(m3_path[:-1], m3_path[1:])):
            row = self.edges.loc[eid]
            gval = float(row["grade_abs_percent_cop"])
            segments.append(
                {
                    "edge_id": int(eid),
                    "grade_abs_percent": round(gval, 2),
                    "grade_display_bucket": grade_bucket(gval),
                    "length_m": round(float(row["length_m"]), 1),
                    "geometry": self._edge_geometry_4326(eid, a),
                }
            )

        m0_coords: list[list[float]] = []
        for eid, (a, b) in zip(m0_edges, zip(m0_path[:-1], m0_path[1:])):
            seg = self._edge_geometry_4326(eid, a)
            m0_coords.extend(seg if not m0_coords else seg[1:])

        path_changed = m0_edges != m3_edges
        threshold = 400.0
        if m0_cost <= threshold and breakdown["total_m"] > threshold:
            status = "reclassified"
        elif m0_cost <= threshold:
            status = "within"
        else:
            status = "both_over"

        origin_xy = self.node_lonlat[src]
        return {
            "request": {"weather": weather, "profile": profile, "stop_id": stop_id},
            "snapping": {
                "origin": {
                    "snap_m": round(origin_snap_m, 1),
                    "node_lng": round(float(origin_xy[0]), 6),
                    "node_lat": round(float(origin_xy[1]), 6),
                },
                "destination": {"snap_m": round(stop_snap_m, 1)},
            },
            "m0": {
                "network_distance_m": round(m0_cost, 1),
                "edge_ids": m0_edges,
                "geometry": m0_coords,
            },
            "m3": {
                "physical_distance_m": round(m3_physical, 1),
                "equivalent_distance_m": _rounded_breakdown(breakdown)["total_m"],
                "edge_ids": m3_edges,
                "segments": segments,
            },
            "breakdown": _rounded_breakdown(breakdown),
            "comparison": {
                "path_changed": path_changed,
                "detour_m": round(m3_physical - m0_cost, 1),
                "detour_percent": round((m3_physical - m0_cost) / m0_cost * 100.0, 1)
                if m0_cost > 0
                else 0.0,
                "threshold_status": status,
            },
        }

    def meta(self) -> dict:
        report_path = self.dir / "build_report.json"
        data_version = None
        if report_path.exists():
            with open(report_path, encoding="utf-8") as f:
                data_version = json.load(f).get("generated_at")
        p = self.params
        return {
            "data_version": data_version,
            "crs": {"analysis": "EPSG:5179", "display": "EPSG:4326"},
            "weather_presets": {k: {"rain_mm": v[0], "snow_cm": v[1]} for k, v in WEATHER_VALUES.items()},
            "model_params": {
                "slope_alpha": p.slope_alpha,
                "weather_beta": p.weather_beta,
                "interaction_beta": p.interaction_beta,
                "snow_weight": p.snow_weight,
                "cost_cap_grade_abs_percent": p.cap_grade_abs_percent,
                "error_exclude_grade_abs_percent": p.error_grade_abs_percent,
            },
            "scenario_parameters_not_calibrated": True,
            "public_safe_data": True,
            "attribution": [
                "© OpenStreetMap contributors",
                "© European Union, contains modified Copernicus DEM data",
            ],
            "counts": {"nodes": int(self.n_nodes), "stops": int(len(self.stops))},
        }
