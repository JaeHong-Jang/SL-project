from pathlib import Path

import pytest

from sl_accessibility.data.contracts import ASOS_WEATHER, BUS_RIDERSHIP, LOCAL_RESIDENT_250M, WALKING_EDGE
from sl_accessibility.data.validation import validate_contract, validate_coordinates, validate_numeric_ranges

pl = pytest.importorskip("polars")


FIXTURES = Path(__file__).parent / "fixtures"


def test_walking_edge_contract_accepts_fixture():
    frame = pl.read_csv(FIXTURES / "sample_edges.csv")
    assert validate_contract(frame, WALKING_EDGE).ok


def test_missing_slope_fails_contract():
    frame = pl.read_csv(FIXTURES / "sample_edges.csv").drop("grade_abs_percent")
    report = validate_contract(frame, WALKING_EDGE)
    assert not report.ok
    assert report.issues[0].column == "grade_abs_percent"


def test_asos_contract_accepts_korean_columns():
    frame = pl.read_csv(FIXTURES / "sample_weather.csv")
    assert validate_contract(frame, ASOS_WEATHER).ok


def test_bus_contract_accepts_fixture():
    frame = pl.read_csv(FIXTURES / "sample_bus_ridership.csv")
    assert validate_contract(frame, BUS_RIDERSHIP).ok


def test_local_population_contract_accepts_fixture():
    frame = pl.read_csv(FIXTURES / "sample_population.csv")
    assert validate_contract(frame, LOCAL_RESIDENT_250M).ok


def test_validate_coordinates_warns_on_invalid_and_out_of_bounds_records():
    report = validate_coordinates(
        [
            {"lon": 126.98, "lat": 37.56},
            {"lon": 128.0, "lat": 37.56},
            {"lon": "bad", "lat": 37.56},
        ]
    )

    assert report.ok
    assert [issue.level for issue in report.issues] == ["warning", "warning"]
    assert "invalid coordinates" in report.issues[0].message
    assert "outside Seoul bounds" in report.issues[1].message


def test_validate_numeric_ranges_warns_on_parse_and_range_failures():
    report = validate_numeric_ranges(
        [{"speed": "10"}, {"speed": "-1"}, {"speed": "fast"}, {"speed": ""}],
        {"speed": (0, 30)},
    )

    assert report.ok
    assert len(report.issues) == 1
    assert report.issues[0].column == "speed"
    assert "2 values outside expected range" in report.issues[0].message
