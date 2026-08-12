"""단계 2 — 라우팅·지도 산출물 생성 (docs/prototype_plan.md v2).

edges_base(스무딩된 Copernicus 경사망)에서 다음을 만든다.

- 노드 연속 인덱스 배열(nodes.npz): OSM node ID 보존, EPSG:5179 좌표와 EPSG:4326 표시 좌표
- 4개 프로필(CSR) 그래프(graph_<profile>.npz): 병렬 엣지 대표 선택 + 대표 edge_id 보존
- 경로 복원용 엣지 메타(edges.parquet): 지오메트리·길이·경사·노드 인덱스
- 정류장 스냅 테이블(stops_snap.parquet)과 표시용 stops.geojson

비용식은 복사하지 않고 `accessibility.costs.CostParameters`의 계수를 그대로 참조해
벡터화하며, 무작위 표본을 `cost_by_model`과 대조해 일치(1e-9)를 강제한다.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer

from sl_accessibility.accessibility.costs import CostParameters, cost_by_model

# 프로필 정의: 이름 → (모델, rain_mm, snow_cm). 흐림은 m3_dry를 공유한다.
PROFILES: dict[str, tuple[str, float, float]] = {
    "m0": ("M0", 0.0, 0.0),
    "m3_dry": ("M3", 0.0, 0.0),
    "m3_rain_2mm": ("M3", 2.0, 0.0),
    "m3_snow_1cm": ("M3", 0.0, 1.0),
}


def profile_costs(
    length_m: np.ndarray, grade_abs: np.ndarray, profile: str, params: CostParameters | None = None
) -> np.ndarray:
    """프로필별 엣지 비용을 벡터화 계산한다 (costs.py 공식과 동일 계수)."""
    p = params or CostParameters()
    model, rain, snow = PROFILES[profile]
    if model == "M0":
        return length_m.astype("float64")
    g = np.clip(np.abs(grade_abs), None, p.cap_grade_abs_percent)
    m1 = length_m * (1.0 + p.slope_alpha * g)
    intensity = max(rain, 0.0) + p.snow_weight * max(snow, 0.0)
    factor = 1.0 + p.weather_beta * intensity + p.interaction_beta * intensity * g / 100.0
    return m1 * factor


def verify_costs_against_reference(
    edges: pd.DataFrame, n_sample: int = 1000, seed: int = 42, tol: float = 1e-9
) -> dict:
    """무작위 표본 엣지의 벡터화 비용을 기존 cost_by_model과 대조한다."""
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(edges), size=min(n_sample, len(edges)), replace=False)
    sample = edges.iloc[idx]
    worst = 0.0
    for profile, (model, rain, snow) in PROFILES.items():
        vec = profile_costs(
            sample["length_m"].to_numpy(), sample["grade_abs_percent_cop"].to_numpy(), profile
        )
        ref = np.array(
            [
                cost_by_model(
                    model, row.length_m, row.grade_abs_percent_cop, rain_mm=rain, snow_cm=snow
                )
                for row in sample.itertuples()
            ]
        )
        diff = float(np.max(np.abs(vec - ref) / np.maximum(np.abs(ref), 1.0)))
        worst = max(worst, diff)
        if diff > tol:
            raise AssertionError(f"프로필 {profile} 비용 불일치: 최대 상대오차 {diff}")
    return {"sampled_edges": int(len(sample)), "max_relative_error": worst, "tolerance": tol}


def build_node_index(edges: pd.DataFrame, nodes_csv: Path) -> pd.DataFrame:
    """엣지에 등장하는 노드만 연속 인덱스로 매핑하고 5179/4326 좌표를 붙인다."""
    used = pd.Index(np.union1d(edges["u"].unique(), edges["v"].unique()), name="node_id")
    coords = pd.read_csv(nodes_csv, usecols=["node_id", "x", "y"], low_memory=False)
    coords = coords.set_index("node_id").loc[used]
    tf = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True)
    lon, lat = tf.transform(coords["x"].to_numpy(), coords["y"].to_numpy())
    out = pd.DataFrame(
        {
            "node_id": used.to_numpy(),
            "node_idx": np.arange(len(used), dtype="int64"),
            "x": coords["x"].to_numpy(),
            "y": coords["y"].to_numpy(),
            "lon": lon,
            "lat": lat,
        }
    )
    return out


def build_profile_csr(
    edges: pd.DataFrame, node_index: pd.DataFrame, profile: str
) -> dict[str, np.ndarray]:
    """무방향 그래프의 CSR 배열을 만든다. 병렬 엣지는 프로필 최저 비용 대표를 남긴다.

    tie-break: cost → length_m → edge_id (결정적 재현).
    반환: indptr, indices, data(cost), edge_ids (data와 정렬 일치), n_nodes.
    """
    idx = node_index.set_index("node_id")["node_idx"]
    cost = profile_costs(
        edges["length_m"].to_numpy(), edges["grade_abs_percent_cop"].to_numpy(), profile
    )
    base = pd.DataFrame(
        {
            "a": edges["u"].map(idx).to_numpy(),
            "b": edges["v"].map(idx).to_numpy(),
            "cost": cost,
            "length_m": edges["length_m"].to_numpy(),
            "edge_id": edges["edge_id"].to_numpy(),
        }
    )
    arcs = pd.concat([base, base.rename(columns={"a": "b", "b": "a"})], ignore_index=True)
    arcs = arcs.sort_values(["a", "b", "cost", "length_m", "edge_id"], kind="mergesort")
    arcs = arcs.drop_duplicates(["a", "b"], keep="first")
    arcs = arcs.sort_values(["a", "b"], kind="mergesort").reset_index(drop=True)

    n = len(node_index)
    counts = np.bincount(arcs["a"].to_numpy(), minlength=n)
    indptr = np.concatenate([[0], np.cumsum(counts)]).astype("int64")
    return {
        "indptr": indptr,
        "indices": arcs["b"].to_numpy().astype("int64"),
        "data": arcs["cost"].to_numpy().astype("float64"),
        "edge_ids": arcs["edge_id"].to_numpy().astype("int64"),
        "n_nodes": np.array([n], dtype="int64"),
    }


def load_stops(bus_csv: Path, subway_csv: Path) -> pd.DataFrame:
    """버스·지하철 정류장을 stop_id·이름·좌표로 정규화한다."""
    bus = pd.read_csv(
        bus_csv,
        usecols=["standard_bus_stop_id", "bus_stop_name", "lon", "lat", "coord_valid"],
        low_memory=False,
    )
    bus = bus[bus["coord_valid"].fillna(False).astype(bool)].drop_duplicates("standard_bus_stop_id")
    bus = pd.DataFrame(
        {
            "stop_id": "bus:" + bus["standard_bus_stop_id"].astype(str),
            "name": bus["bus_stop_name"],
            "kind": "버스",
            "lon": bus["lon"],
            "lat": bus["lat"],
        }
    )
    sub = pd.read_csv(subway_csv, low_memory=False)
    sub = sub[sub["location_matched"].fillna(False).astype(bool)].drop_duplicates(
        subset=["호선명", "지하철역"]
    )
    sub = pd.DataFrame(
        {
            "stop_id": "subway:" + sub["호선명"].astype(str) + ":" + sub["지하철역"].astype(str),
            "name": sub["호선명"].astype(str) + " " + sub["지하철역"].astype(str),
            "kind": "지하철",
            "lon": sub["lon"],
            "lat": sub["lat"],
        }
    )
    stops = pd.concat([bus, sub], ignore_index=True).dropna(subset=["lon", "lat"])
    return stops.drop_duplicates("stop_id").reset_index(drop=True)


def snap_stops(stops: pd.DataFrame, node_index: pd.DataFrame, max_distance_m: float) -> pd.DataFrame:
    """정류장을 그래프 노드에 스냅한다. max_distance_m 초과는 제외한다."""
    from scipy.spatial import cKDTree

    tf = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)
    sx, sy = tf.transform(stops["lon"].to_numpy(), stops["lat"].to_numpy())
    tree = cKDTree(np.c_[node_index["x"], node_index["y"]])
    dist, ni = tree.query(np.c_[sx, sy], distance_upper_bound=max_distance_m)
    ok = np.isfinite(dist)
    snapped = stops.loc[ok].copy()
    snapped["node_idx"] = node_index["node_idx"].to_numpy()[ni[ok]]
    snapped["node_id"] = node_index["node_id"].to_numpy()[ni[ok]]
    snapped["snap_m"] = dist[ok]
    return snapped.reset_index(drop=True)


def stops_geojson(snapped: pd.DataFrame) -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [round(r.lon, 6), round(r.lat, 6)]},
                "properties": {"stop_id": r.stop_id, "name": r.name, "kind": r.kind},
            }
            for r in snapped.itertuples()
        ],
    }


def build_all(cfg: dict, root: Path, edges: pd.DataFrame) -> dict:
    """단계 2 산출물 전체를 생성하고 검증 요약을 반환한다."""
    out_dir = root / cfg["paths"]["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    cost_check = verify_costs_against_reference(edges)

    node_index = build_node_index(edges, root / cfg["paths"]["nodes_csv"])
    np.savez_compressed(
        out_dir / "nodes.npz",
        node_id=node_index["node_id"].to_numpy(),
        x=node_index["x"].to_numpy(),
        y=node_index["y"].to_numpy(),
        lon=node_index["lon"].to_numpy(),
        lat=node_index["lat"].to_numpy(),
    )

    graph_meta = {}
    for profile in PROFILES:
        arrays = build_profile_csr(edges, node_index, profile)
        assert np.all(np.isfinite(arrays["data"])) and np.all(arrays["data"] >= 0)
        assert arrays["indptr"][-1] == len(arrays["indices"]) == len(arrays["edge_ids"])
        np.savez_compressed(out_dir / f"graph_{profile}.npz", **arrays)
        graph_meta[profile] = {"arcs": int(len(arrays["indices"]))}

    idx = node_index.set_index("node_id")["node_idx"]
    edges_out = edges.copy()
    edges_out["u_idx"] = edges_out["u"].map(idx).astype("int64")
    edges_out["v_idx"] = edges_out["v"].map(idx).astype("int64")
    edges_out.to_parquet(out_dir / "edges.parquet", index=False)

    stops = load_stops(root / cfg["paths"]["bus_stops_csv"], root / cfg["paths"]["subway_stops_csv"])
    snapped = snap_stops(stops, node_index, float(cfg["snap"]["max_distance_m"]))
    snapped.to_parquet(out_dir / "stops_snap.parquet", index=False)
    with open(out_dir / "stops.geojson", "w", encoding="utf-8") as f:
        json.dump(stops_geojson(snapped), f, ensure_ascii=False)

    report = {
        "cost_verification": cost_check,
        "nodes": int(len(node_index)),
        "graphs": graph_meta,
        "stops_total": int(len(stops)),
        "stops_snapped": int(len(snapped)),
        "stops_excluded_over_snap_limit": int(len(stops) - len(snapped)),
        "outputs": [
            "nodes.npz",
            *[f"graph_{p}.npz" for p in PROFILES],
            "edges.parquet",
            "stops_snap.parquet",
            "stops.geojson",
        ],
    }
    with open(out_dir / "artifacts_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report
