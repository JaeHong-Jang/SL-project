from pathlib import Path

import pytest

from sl_accessibility.transit.ridership import has_valid_coordinates, normalize_transit_record
from sl_accessibility.weather.asos import normalize_asos_columns

pl = pytest.importorskip("polars")

FIXTURES = Path(__file__).parent / "fixtures"


def test_asos_normalization_maps_korean_columns():
    frame = normalize_asos_columns(pl.read_csv(FIXTURES / "sample_weather.csv"))
    assert {"station_id", "observed_at", "temp_c", "rain_mm", "snow_cm"}.issubset(frame.columns)
    assert frame["rain_mm"].to_list() == [0.0, 2.0]


def test_transit_coordinate_filter_requires_valid_flags():
    good = {
        "lon": "126.98",
        "lat": "37.56",
        "coord_valid": "True",
        "location_matched": "True",
    }
    bad = dict(good, location_matched="False")
    assert has_valid_coordinates(good)
    assert not has_valid_coordinates(bad)


def test_normalize_bus_record_to_common_schema():
    row = {
        "표준버스정류장ID": "100",
        "역명": "테스트정류장",
        "사용년월": "202501",
        "hour": "08",
        "ride_type": "승차",
        "passengers": "10",
        "lon": "126.98",
        "lat": "37.56",
    }
    normalized = normalize_transit_record(row, "bus")
    assert normalized["mode"] == "bus"
    assert normalized["stop_id"] == "100"
