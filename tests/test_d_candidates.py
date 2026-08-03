import polars as pl
import geopandas as gpd
from shapely.geometry import Point, box

from sl_accessibility.transit.d_candidates import (
    build_bus_d_candidates,
    build_subway_d_candidates,
    split_candidates_by_boundary,
)


def test_build_bus_d_candidates_filters_invalid_rows():
    frame = pl.LazyFrame(
        [
            {
                "표준버스정류장ID": "1",
                "역명": "정류장",
                "standard_bus_stop_id": "1",
                "bus_stop_name": "정류장",
                "passengers": 10,
                "lon": 126.98,
                "lat": 37.56,
                "coord_valid": "True",
                "location_matched": "True",
            },
            {
                "표준버스정류장ID": "2",
                "역명": "오류",
                "standard_bus_stop_id": "2",
                "bus_stop_name": "오류",
                "passengers": 10,
                "lon": 0.0,
                "lat": 0.0,
                "coord_valid": "False",
                "location_matched": "False",
            },
        ]
    )

    result = build_bus_d_candidates(frame).collect()

    assert result.height == 1
    assert result["mode"].to_list() == ["bus"]
    assert result["stop_id"].to_list() == ["1"]


def test_build_bus_d_candidates_accepts_korean_only_columns():
    frame = pl.LazyFrame(
        [
            {
                "표준버스정류장ID": "1",
                "역명": "정류장",
                "passengers": 10,
                "lon": 126.98,
                "lat": 37.56,
                "coord_valid": "True",
                "location_matched": "True",
            },
        ]
    )

    result = build_bus_d_candidates(frame).collect()

    assert result["stop_id"].to_list() == ["1"]
    assert result["stop_name"].to_list() == ["정류장"]


def test_build_subway_d_candidates_groups_station_rows():
    frame = pl.LazyFrame(
        [
            {"지하철역": "서울역", "passengers": 10, "lon": 126.97, "lat": 37.55, "location_matched": "True"},
            {"지하철역": "서울역", "passengers": 20, "lon": 126.97, "lat": 37.55, "location_matched": "True"},
        ]
    )

    result = build_subway_d_candidates(frame).collect()

    assert result.height == 1
    assert result["mode"].to_list() == ["subway"]
    assert result["passengers_sum"].to_list() == [30.0]


def test_split_candidates_by_boundary_keeps_outside_for_qa():
    candidates = gpd.GeoDataFrame(
        {"stop_id": ["inside", "outside"]},
        geometry=[Point(0.5, 0.5), Point(2.0, 2.0)],
        crs="EPSG:4326",
    )
    boundary = gpd.GeoDataFrame({"name": ["mask"]}, geometry=[box(0, 0, 1, 1)], crs="EPSG:4326")

    inside, outside = split_candidates_by_boundary(candidates, boundary)

    assert inside["stop_id"].to_list() == ["inside"]
    assert outside["stop_id"].to_list() == ["outside"]
