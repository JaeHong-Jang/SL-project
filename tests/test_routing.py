import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, box

from sl_accessibility.accessibility.routing import (
    build_hex_accessibility_table,
    nearest_destination_lengths,
    snap_points_to_nodes,
)


def test_snap_points_to_nodes_respects_max_distance():
    points = gpd.GeoDataFrame(
        {"hex_id": ["near", "far"]},
        geometry=[Point(1, 0), Point(1000, 0)],
        crs="EPSG:5179",
    )
    nodes = gpd.GeoDataFrame(
        {"node_id": [10]},
        geometry=[Point(0, 0)],
        crs="EPSG:5179",
    )

    snapped = snap_points_to_nodes(points, nodes, id_columns=["hex_id"], max_distance_m=10)

    assert snapped.loc[snapped["hex_id"] == "near", "node_id"].iloc[0] == 10
    assert pd.isna(snapped.loc[snapped["hex_id"] == "far", "node_id"].iloc[0])


def test_nearest_destination_lengths_uses_reversed_graph():
    edges = pd.DataFrame(
        {
            "u": [1, 2, 1],
            "v": [2, 3, 3],
            "cost_m0": [5.0, 6.0, 20.0],
            "cost_m1": [5.0, 6.0, 20.0],
            "cost_m2": [5.0, 6.0, 20.0],
            "cost_m3": [5.0, 6.0, 20.0],
        }
    )

    lengths = nearest_destination_lengths(edges, [3])

    assert lengths["cost_m0"][1] == 11.0
    assert lengths["cost_m0"][2] == 6.0
    assert lengths["cost_m0"][3] == 0.0


def test_build_hex_accessibility_table_preserves_all_hexes():
    hexes = gpd.GeoDataFrame(
        {"hex_id": ["h1", "h2"]},
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)],
        crs="EPSG:5179",
    )
    origins = gpd.GeoDataFrame(
        {"hex_id": ["h1"], "node_id": [1], "snap_distance_m": [3.0]},
        geometry=[Point(0, 0)],
        crs="EPSG:5179",
    )
    destinations = gpd.GeoDataFrame(
        {"stop_id": ["d1"], "node_id": [2], "snap_distance_m": [2.0]},
        geometry=[Point(1, 0)],
        crs="EPSG:5179",
    )
    edges = pd.DataFrame(
        {
            "u": [1],
            "v": [2],
            "cost_m0": [10.0],
            "cost_m1": [11.0],
            "cost_m2": [12.0],
            "cost_m3": [13.0],
        }
    )

    result = build_hex_accessibility_table(hexes, origins, destinations, edges)

    assert len(result) == 2
    assert result.loc[result["hex_id"] == "h1", "access_cost_m0"].iloc[0] == 10.0
    assert pd.isna(result.loc[result["hex_id"] == "h2", "access_cost_m0"].iloc[0])
