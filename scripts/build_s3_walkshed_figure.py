"""슬라이드 3용 walkshed 비교 그림 생성.

현행 400m 직선거리 원(법적 기준이 '커버된다'고 가정하는 영역)과,
같은 정류장에서 보행망 + 경사·기상 비용(M3)으로 실제 400m-등가 안에
도달하는 영역을 겹쳐, 그 차이(=양호로 착각된 사각지대)를 보여준다.

가장 가파른 지역의 정류장을 자동 선택해 경사 효과가 잘 드러나게 한다.
"""
from __future__ import annotations

import math
from pathlib import Path

import geopandas as gpd
import matplotlib
import networkx as nx
import pandas as pd
from shapely import wkt
from shapely.geometry import Point
from shapely.ops import unary_union

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(__file__).resolve().parents[1]
BUDGET = 400.0          # 도달 예산(거리/비용 등가, m)
EVAL_RADIUS = 250.0     # 정류장 후보 '경사' 평가 반경
PLOT_RADIUS = 520.0     # 그림에 표시할 도로 반경
EDGE_BUFFER = 22.0      # walkshed 폴리곤용 edge 버퍼
MIN_REACHABLE = 120     # 후보가 가져야 할 최소 M0 도달 노드 수(밀집 동네)
N_STEEP_CANDIDATES = 250


def load_edges() -> pd.DataFrame:
    edges = pd.read_parquet(ROOT / "data/interim/walking_edge_costs.parquet")
    edges = edges.dropna(subset=["u", "v", "cost_m0", "cost_m3"])
    edges["u"] = edges["u"].astype("int64")
    edges["v"] = edges["v"].astype("int64")
    return edges


def build_graph(edges: pd.DataFrame, weight_col: str) -> nx.DiGraph:
    best = edges.groupby(["u", "v"], sort=False)[weight_col].min().reset_index()
    return nx.from_pandas_edgelist(
        best, "u", "v", edge_attr=weight_col, create_using=nx.DiGraph
    )


def node_coords(edges: pd.DataFrame) -> pd.DataFrame:
    nodes = pd.read_csv(
        ROOT / "data/walking_network_nodes_with_elevation.csv",
        usecols=["node_id", "x", "y"],
    )
    nodes["node_id"] = pd.to_numeric(nodes["node_id"], errors="coerce")
    return nodes.dropna(subset=["node_id", "x", "y"]).astype({"node_id": "int64"})


def node_steepness(edges: pd.DataFrame) -> pd.Series:
    """노드별 인접 edge 평균 |경사|."""
    a = edges[["u", "grade_abs_percent"]].rename(columns={"u": "node_id"})
    b = edges[["v", "grade_abs_percent"]].rename(columns={"v": "node_id"})
    both = pd.concat([a, b], ignore_index=True)
    return both.groupby("node_id")["grade_abs_percent"].mean()


def pick_stop(edges, nodes, g_m0, g_m3):
    """가파른 동네에서 경사 효과(도달영역 축소)가 가장 큰 정류장을 고른다."""
    stops = gpd.read_file(
        ROOT / "qgis/out_transit_d_candidates.gpkg", layer="out_transit_d_candidates"
    )
    node_gdf = gpd.GeoDataFrame(
        nodes, geometry=gpd.points_from_xy(nodes["x"], nodes["y"]), crs="EPSG:5179"
    )
    if stops.crs != node_gdf.crs:
        stops = stops.to_crs(node_gdf.crs)
    snapped = gpd.sjoin_nearest(
        stops[["stop_name", "geometry"]],
        node_gdf[["node_id", "geometry"]],
        how="left",
        max_distance=50.0,
        distance_col="snap_m",
    ).dropna(subset=["node_id"])
    snapped["node_id"] = snapped["node_id"].astype("int64")

    steep = node_steepness(edges)
    snapped["steep"] = snapped["node_id"].map(steep).fillna(0.0)
    snapped = snapped.drop_duplicates("node_id").sort_values("steep", ascending=False)

    best = None
    for row in snapped.head(N_STEEP_CANDIDATES).itertuples(index=False):
        src = int(row.node_id)
        if src not in g_m0 or src not in g_m3:
            continue
        d0 = nx.single_source_dijkstra_path_length(g_m0, src, cutoff=BUDGET, weight="cost_m0")
        if len(d0) < MIN_REACHABLE:
            continue
        d3 = nx.single_source_dijkstra_path_length(g_m3, src, cutoff=BUDGET, weight="cost_m3")
        shrink = len(d3) / len(d0)
        cand = {"node_id": src, "shrink": shrink, "m0": len(d0), "m3": len(d3),
                "steep": row.steep, "geom": row.geometry}
        if best is None or shrink < best["shrink"]:
            best = cand
    if best is None:
        raise RuntimeError("적합한 정류장 후보를 찾지 못했습니다.")
    return best


def reachable_walkshed(edges_local: pd.DataFrame, dist_map: dict[int, float]) -> object:
    """양 끝점이 예산 안에 도달되는 edge들을 버퍼-합집합해 walkshed 폴리곤 생성."""
    mask = edges_local["u"].map(dist_map).notna() & edges_local["v"].map(dist_map).notna()
    geoms = edges_local.loc[mask, "geom"]
    if geoms.empty:
        return None
    return unary_union(geoms.values).buffer(EDGE_BUFFER).buffer(-EDGE_BUFFER * 0.4)


def main() -> None:
    edges = load_edges()
    nodes = node_coords(edges)
    print("graph 빌드 중...")
    g_m0 = build_graph(edges, "cost_m0")
    g_m3 = build_graph(edges, "cost_m3")
    print("정류장 선택 중...")
    best = pick_stop(edges, nodes, g_m0, g_m3)
    src = best["node_id"]
    stop_pt: Point = best["geom"]
    print(f"선택: node={src} steep={best['steep']:.1f}% M0도달={best['m0']} M3도달={best['m3']} 축소율={best['shrink']:.2f}")

    # 구(區) 라벨
    try:
        admin = gpd.read_file(ROOT / "qgis/wrk_admin_dong_seoul_5179.gpkg")
        hit = admin[admin.contains(stop_pt)]
        district = str(hit.iloc[0]["district_name"]) if len(hit) else ""
        dong = str(hit.iloc[0]["admin_name"]) if len(hit) else ""
    except Exception:
        district, dong = "", ""

    # 도달 거리/비용 맵
    d0 = nx.single_source_dijkstra_path_length(g_m0, src, cutoff=BUDGET, weight="cost_m0")
    d3 = nx.single_source_dijkstra_path_length(g_m3, src, cutoff=BUDGET, weight="cost_m3")

    # 로컬 edge (그림용) — 정류장 주변 bbox
    cx, cy = stop_pt.x, stop_pt.y
    local = edges[
        (edges["u"].isin(d0) | edges["v"].isin(d0)
         | edges["u"].isin(d3) | edges["v"].isin(d3))
    ].copy()
    local["geom"] = local["geometry_wkt"].apply(wkt.loads)
    local_gdf = gpd.GeoDataFrame(local, geometry="geom", crs="EPSG:5179")

    ws_m0 = reachable_walkshed(local_gdf, d0)
    ws_m3 = reachable_walkshed(local_gdf, d3)
    circle = stop_pt.buffer(BUDGET)

    # 직선 원 안의 미도달 영역을 (a)도로 우회 (b)경사 로 분해
    detour_gap = circle.difference(ws_m0) if ws_m0 is not None else circle
    slope_gap = ws_m0.difference(ws_m3) if (ws_m0 is not None and ws_m3 is not None) else None

    # ---- 그림 ----
    fig, ax = plt.subplots(figsize=(9.5, 10.0))

    # (a) 도로 우회로 못 닿는 영역
    gpd.GeoSeries([detour_gap], crs="EPSG:5179").plot(
        ax=ax, facecolor="#f4b6b0", edgecolor="none", alpha=0.45, zorder=2
    )
    # (b) 경사 때문에 추가로 못 닿는 영역
    if slope_gap is not None and not slope_gap.is_empty:
        gpd.GeoSeries([slope_gap], crs="EPSG:5179").plot(
            ax=ax, facecolor="#f3922b", edgecolor="none", alpha=0.70, zorder=3
        )
    # 실제 보행 도달(M3)
    if ws_m3 is not None:
        gpd.GeoSeries([ws_m3], crs="EPSG:5179").plot(
            ax=ax, facecolor="#2c7fb8", edgecolor="#08519c", linewidth=1.4,
            alpha=0.60, zorder=4
        )
    # 400m 직선 원
    gpd.GeoSeries([circle.boundary], crs="EPSG:5179").plot(
        ax=ax, color="#333333", linewidth=2.2, linestyle="--", zorder=6
    )
    # 배경 도로
    local_gdf.plot(ax=ax, color="#9a9a9a", linewidth=0.4, alpha=0.55, zorder=5)
    # 정류장
    ax.scatter([cx], [cy], s=260, marker="*", color="#111111", zorder=7,
               edgecolor="white", linewidth=1.0)

    ax.set_xlim(cx - PLOT_RADIUS, cx + PLOT_RADIUS)
    ax.set_ylim(cy - PLOT_RADIUS, cy + PLOT_RADIUS)
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)

    loc = f"{district} {dong}".strip()
    fig.subplots_adjust(top=0.88)
    fig.suptitle("현행 400m 기준이 놓치는 것 — 직선거리 ≠ 보행거리",
                 y=0.95, fontsize=17, fontweight="bold")
    sub = (f"가파른 정류장 사례(주변 평균 경사 {best['steep']:.0f}%"
           + (f", {loc}" if loc else "") + ") — 직선 원 안에서 실제로 걸어 닿는 곳은 파란 영역뿐")
    ax.set_title(sub, fontsize=10.5, color="#555555", pad=10)

    legend = [
        Line2D([0], [0], color="#333333", lw=2.2, ls="--",
               label="현행 기준: 직선거리 400m (전부 '양호'로 가정)"),
        Patch(facecolor="#2c7fb8", alpha=0.60, edgecolor="#08519c",
              label="실제 보행 도달영역 (경사·기상 반영, 400m 등가)"),
        Patch(facecolor="#f3922b", alpha=0.70, edgecolor="none",
              label="경사 때문에 추가로 못 닿는 영역"),
        Patch(facecolor="#f4b6b0", alpha=0.45, edgecolor="none",
              label="도로 우회로 못 닿는 영역 (직선거리의 한계)"),
        Line2D([0], [0], marker="*", color="w", markerfacecolor="#111111",
               markersize=15, label="정류장"),
    ]
    ax.legend(handles=legend, loc="upper center", bbox_to_anchor=(0.5, -0.02),
              ncol=1, fontsize=10.5, frameon=False)

    out = ROOT / "outputs/figures/s3_walkshed_comparison.png"
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor="white")
    print("저장:", out)


if __name__ == "__main__":
    main()
