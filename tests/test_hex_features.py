from pathlib import Path
from uuid import uuid4

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, box

from sl_accessibility.population.hex_features import (
    area_weight_living_population_to_hex,
    area_weight_registered_population_to_hex,
    build_final_hex_demand_features,
    count_poi_by_hex,
)


def test_area_weight_living_population_to_hex_preserves_grid_mass():
    grid = gpd.GeoDataFrame(
        {
            "CELL_ID": ["g1"],
            "livingpop_joined": [True],
            "mean_living_population": [100.0],
            "mean_senior_population": [20.0],
            "daytime_mean_population": [120.0],
            "nighttime_mean_population": [80.0],
            "commute_mean_population": [110.0],
        },
        geometry=[box(0, 0, 2, 1)],
        crs="EPSG:5179",
    )
    hexes = gpd.GeoDataFrame(
        {"hex_id": ["h1", "h2"]},
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)],
        crs="EPSG:5179",
    )

    result = area_weight_living_population_to_hex(grid, hexes)

    assert set(result["hex_id"]) == {"h1", "h2"}
    assert result["living_mean_living_population"].sum() == 100.0
    assert result["living_mean_senior_population"].sum() == 20.0


def test_area_weight_registered_population_to_hex_preserves_admin_mass():
    registered_admin = gpd.GeoDataFrame(
        {
            "adm_cd": ["a1", "a2"],
            "registered_population": [100.0, 300.0],
            "registered_senior_population": [25.0, 75.0],
        },
        geometry=[box(0, 0, 2, 1), box(2, 0, 4, 1)],
        crs="EPSG:5179",
    )
    hexes = gpd.GeoDataFrame(
        {"hex_id": ["h1", "h2", "h3"]},
        geometry=[box(0, 0, 1, 1), box(1, 0, 3, 1), box(3, 0, 4, 1)],
        crs="EPSG:5179",
    )

    result = area_weight_registered_population_to_hex(registered_admin, hexes)
    by_hex = result.set_index("hex_id")

    assert set(result["hex_id"]) == {"h1", "h2", "h3"}
    assert result["registered_population"].sum() == pytest.approx(400.0)
    assert result["registered_senior_population"].sum() == pytest.approx(100.0)
    assert by_hex["registered_population"].to_dict() == pytest.approx(
        {"h1": 50.0, "h2": 200.0, "h3": 150.0}
    )
    assert by_hex["registered_senior_population"].to_dict() == pytest.approx(
        {"h1": 12.5, "h2": 50.0, "h3": 37.5}
    )
    assert by_hex["registered_hex_coverage_ratio"].to_dict() == pytest.approx(
        {"h1": 1.0, "h2": 1.0, "h3": 1.0}
    )


def test_area_weight_registered_population_to_hex_preserves_mass_inside_analysis_mask():
    registered_admin = gpd.GeoDataFrame(
        {
            "registered_population": [100.0],
            "registered_senior_population": [25.0],
        },
        geometry=[box(0, 0, 4, 1)],
        crs="EPSG:5179",
    )
    hexes = gpd.GeoDataFrame(
        {"hex_id": ["h1", "h2"]},
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)],
        crs="EPSG:5179",
    )

    result = area_weight_registered_population_to_hex(registered_admin, hexes)

    assert result["registered_population"].sum() == pytest.approx(100.0)
    assert result["registered_senior_population"].sum() == pytest.approx(25.0)
    assert result.set_index("hex_id")["registered_population"].to_dict() == pytest.approx(
        {"h1": 50.0, "h2": 50.0}
    )


def test_build_final_hex_demand_features_combines_four_components():
    hexes = gpd.GeoDataFrame(
        {"hex_id": ["h1", "h2"], "h3_res": [9, 9]},
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)],
        crs="EPSG:5179",
    )
    living_grid = gpd.GeoDataFrame(
        {
            "CELL_ID": ["g1", "g2"],
            "livingpop_joined": [True, True],
            "mean_living_population": [100.0, 300.0],
            "mean_senior_population": [30.0, 90.0],
            "daytime_mean_population": [110.0, 310.0],
            "nighttime_mean_population": [95.0, 290.0],
            "commute_mean_population": [105.0, 305.0],
        },
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)],
        crs="EPSG:5179",
    )
    registered_admin = gpd.GeoDataFrame(
        {
            "registered_population": [100.0, 300.0],
            "registered_senior_population": [20.0, 90.0],
        },
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)],
        crs="EPSG:5179",
    )
    poi_points = gpd.GeoSeries(
        [Point(0.5, 0.5), Point(1.2, 0.5), Point(1.7, 0.5)],
        crs="EPSG:5179",
    ).to_crs("EPSG:4326")

    tmp_dir = Path(".pytest-tmp") / f"hex_final_{uuid4().hex}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    hex_path = tmp_dir / "hex.gpkg"
    living_path = tmp_dir / "living.gpkg"
    registered_path = tmp_dir / "registered.gpkg"
    poi_path = tmp_dir / "poi.csv"
    hexes.to_file(hex_path, layer="hex", driver="GPKG")
    living_grid.to_file(living_path, layer="living", driver="GPKG")
    registered_admin.to_file(registered_path, layer="registered", driver="GPKG")
    pd.DataFrame({"lon": poi_points.x, "lat": poi_points.y}).to_csv(poi_path, index=False)

    result = build_final_hex_demand_features(
        hex_path=hex_path,
        living_grid_path=living_path,
        registered_admin_path=registered_path,
        poi_sources={"sample": poi_path},
        hex_layer="hex",
        living_layer="living",
        registered_admin_layer="registered",
    ).sort_values("hex_id")

    assert result["registered_population"].tolist() == pytest.approx([100.0, 300.0])
    assert result["registered_senior_population"].tolist() == pytest.approx([20.0, 90.0])
    assert result["poi_total_count"].tolist() == [1, 2]
    assert result["demand_index_final"].tolist() == pytest.approx([0.0, 1.0])


def test_count_poi_by_hex_counts_points_inside():
    hexes = gpd.GeoDataFrame(
        {"hex_id": ["h1", "h2"]},
        geometry=[box(0, 0, 1000, 1000), box(1000, 0, 2000, 1000)],
        crs="EPSG:5179",
    ).to_crs("EPSG:4326")
    points = gpd.GeoSeries([Point(100, 100), Point(1200, 100)], crs="EPSG:5179").to_crs("EPSG:4326")
    tmp_dir = Path(".pytest-tmp")
    tmp_dir.mkdir(exist_ok=True)
    poi_path = tmp_dir / f"poi_{uuid4().hex}.csv"
    pd.DataFrame({"lon": points.x, "lat": points.y}).to_csv(poi_path, index=False)

    result = count_poi_by_hex(hexes.to_crs("EPSG:5179"), {"sample": poi_path})

    assert result["sample_poi_count"].tolist() == [1, 1]
    assert result["poi_total_count"].tolist() == [1, 1]
