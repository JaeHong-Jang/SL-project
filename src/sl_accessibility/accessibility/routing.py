"""H3 origin과 대중교통 D 후보를 보행망에 스냅하고 접근비용을 계산한다.

접근성 본계산은 모든 D 후보까지 각각 최단경로를 반복하지 않는다.
대신 D 후보가 스냅된 노드들을 여러 source로 두고, 보행망 방향을 뒤집은 뒤
multi-source Dijkstra를 수행한다. 그러면 각 네트워크 노드에서 가장 가까운
D까지의 비용을 비용모형별로 한 번에 얻을 수 있다.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable, Sequence

import geopandas as gpd
import networkx as nx
import pandas as pd


COST_COLUMNS = ("cost_m0", "cost_m1", "cost_m2", "cost_m3")


def read_network_nodes(path: str | Path, *, crs: str = "EPSG:5179") -> gpd.GeoDataFrame:
    """보행망 node CSV를 스냅용 point GeoDataFrame으로 읽는다."""
    nodes = pd.read_csv(path, usecols=["node_id", "x", "y"])
    nodes["node_id"] = pd.to_numeric(nodes["node_id"], errors="coerce").astype("Int64")
    nodes = nodes.dropna(subset=["node_id", "x", "y"])
    return gpd.GeoDataFrame(
        nodes,
        geometry=gpd.points_from_xy(nodes["x"], nodes["y"]),
        crs=crs,
    )


def snap_points_to_nodes(
    points: gpd.GeoDataFrame,
    nodes: gpd.GeoDataFrame,
    *,
    id_columns: Sequence[str],
    max_distance_m: float | None = 100.0,
) -> gpd.GeoDataFrame:
    """point 레이어를 가장 가까운 보행망 node에 스냅한다.

    `max_distance_m`보다 먼 점은 node_id가 비어 있는 상태로 남겨 QA에서 제외할 수
    있게 한다.
    """
    if points.crs != nodes.crs:
        points = points.to_crs(nodes.crs)
    left = points.loc[:, [*id_columns, "geometry"]].copy()
    nearest = gpd.sjoin_nearest(
        left,
        nodes.loc[:, ["node_id", "geometry"]],
        how="left",
        max_distance=max_distance_m,
        distance_col="snap_distance_m",
    )
    nearest = nearest.drop(columns=[column for column in ("index_right",) if column in nearest.columns])
    return nearest


def build_weighted_graph(edges: pd.DataFrame, *, weight_col: str) -> nx.DiGraph:
    """edge 비용 테이블에서 지정 비용 컬럼을 weight로 쓰는 directed graph를 만든다."""
    graph = nx.DiGraph()
    for row in edges[["u", "v", weight_col]].itertuples(index=False):
        if pd.isna(row.u) or pd.isna(row.v) or pd.isna(getattr(row, weight_col)):
            continue
        u = int(row.u)
        v = int(row.v)
        weight = float(getattr(row, weight_col))
        if weight < 0 or math.isnan(weight):
            continue
        current = graph.get_edge_data(u, v, default=None)
        if current is None or weight < current["weight"]:
            graph.add_edge(u, v, weight=weight)
    return graph


def nearest_destination_lengths(
    edges: pd.DataFrame,
    destination_nodes: Iterable[int],
    *,
    cost_columns: Sequence[str] = COST_COLUMNS,
) -> dict[str, dict[int, float]]:
    """비용모형별 모든 node의 가장 가까운 D까지 비용을 계산한다."""
    destinations = {int(node) for node in destination_nodes if pd.notna(node)}
    if not destinations:
        raise ValueError("스냅된 D 후보 node가 없습니다.")

    lengths: dict[str, dict[int, float]] = {}
    for cost_column in cost_columns:
        graph = build_weighted_graph(edges, weight_col=cost_column)
        reverse_graph = graph.reverse(copy=False)
        valid_destinations = [node for node in destinations if node in reverse_graph]
        if not valid_destinations:
            raise ValueError(f"{cost_column} 그래프에 포함된 D 후보 node가 없습니다.")
        lengths[cost_column] = nx.multi_source_dijkstra_path_length(
            reverse_graph,
            valid_destinations,
            weight="weight",
        )
    return lengths


def build_hex_accessibility_table(
    hexes: gpd.GeoDataFrame,
    origin_snaps: gpd.GeoDataFrame,
    d_snaps: gpd.GeoDataFrame,
    edges: pd.DataFrame,
    *,
    max_origin_snap_m: float = 100.0,
    max_destination_snap_m: float = 100.0,
) -> gpd.GeoDataFrame:
    """스냅 결과와 edge 비용 테이블로 H3별 M0-M3 접근비용을 산출한다."""
    valid_origins = origin_snaps[
        origin_snaps["node_id"].notna() & (origin_snaps["snap_distance_m"] <= max_origin_snap_m)
    ].copy()
    valid_destinations = d_snaps[
        d_snaps["node_id"].notna() & (d_snaps["snap_distance_m"] <= max_destination_snap_m)
    ].copy()
    lengths = nearest_destination_lengths(edges, valid_destinations["node_id"], cost_columns=COST_COLUMNS)

    cost_table = valid_origins.loc[:, ["hex_id", "node_id", "snap_distance_m"]].copy()
    cost_table = cost_table.rename(columns={"node_id": "origin_node_id", "snap_distance_m": "origin_snap_distance_m"})
    for cost_column in COST_COLUMNS:
        output_column = f"access_{cost_column}"
        cost_table[output_column] = cost_table["origin_node_id"].map(lengths[cost_column])

    output = hexes.merge(cost_table, on="hex_id", how="left")
    output["origin_snap_valid"] = output["origin_node_id"].notna()
    for cost_column in COST_COLUMNS:
        output[f"access_{cost_column}_reachable"] = output[f"access_{cost_column}"].notna()
    return output
