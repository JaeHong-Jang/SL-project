from pathlib import Path
from uuid import uuid4

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

from sl_accessibility.cli import _life_mobility_outputs_are_reusable
from sl_accessibility.population.mobility import (
    aggregate_life_mobility_od_admin_csv,
    area_weight_mobility_admin_to_hex,
    build_mobility_admin_geography,
)


def test_aggregate_life_mobility_od_admin_csv_builds_activity_pressure():
    path = _write_life_mobility_fixture(
        [
            [202501, "월", 8, 1106081, 1106081, "F", 30, "HH", 10.0, 0.0, 5.0],
            [202501, "월", 8, 1106081, 1101053, "F", 30, "HW", 20.0, 0.0, 30.0],
            [202501, "월", 18, 1101053, 1106081, "M", 35, "WH", 5.0, 0.0, 40.0],
            [202501, "월", 12, 1106081, 21000, "M", 40, "HE", 7.0, 0.0, 60.0],
            [202501, "월", 17, 21000, 1101053, "F", 25, "EH", 3.0, 0.0, 50.0],
            [202501, "월", 18, 1101053, 1101053, "F", 25, "HH", 0.0, 1.0, None],
        ]
    )

    progress = []
    result, report = aggregate_life_mobility_od_admin_csv(
        path,
        ["1106081", "1101053"],
        chunksize=2,
        peak_hours=(8, 17, 18),
        progress_every_chunks=1,
        progress_callback=progress.append,
    )
    by_code = result.set_index("mobility_admin_code")

    assert by_code.loc["1106081", "mobility_departures"] == pytest.approx(37.0)
    assert by_code.loc["1106081", "mobility_arrivals"] == pytest.approx(15.0)
    assert by_code.loc["1106081", "mobility_internal_trips"] == pytest.approx(10.0)
    assert by_code.loc["1106081", "mobility_outbound_to_nonseoul"] == pytest.approx(7.0)
    assert by_code.loc["1101053", "mobility_inbound_from_nonseoul"] == pytest.approx(3.0)
    assert by_code.loc["1101053", "mobility_home_work_departures"] == pytest.approx(5.0)
    assert by_code.loc["1106081", "mobility_origin_avg_move_time_min"] == pytest.approx(
        (10 * 5 + 20 * 30 + 7 * 60) / 37
    )
    assert report["input_row_count"] == 6
    assert report["zero_or_negative_move_pop_count"] == 1
    assert report["total_move_pop"] == pytest.approx(45.0)
    assert [item["input_row_count"] for item in progress] == [2, 4, 6]


def test_build_mobility_admin_geography_dissolves_to_life_mobility_code():
    boundary = gpd.GeoDataFrame(
        {
            "district_name": ["강남구", "강남구"],
            "admin_name": ["신사동", "개포3동"],
            "admin_code": ["11230510", "11230511"],
        },
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)],
        crs="EPSG:5179",
    )

    result = build_mobility_admin_geography(boundary)

    assert result["mobility_admin_code"].tolist() == ["1123051"]
    assert result.geometry.area.iloc[0] == pytest.approx(2.0)
    assert result["source_admin_codes"].iloc[0] == "11230510,11230511"


def test_area_weight_mobility_admin_to_hex_preserves_mass_inside_mask():
    mobility_admin = gpd.GeoDataFrame(
        {
            "mobility_admin_code": ["1106081"],
            "mobility_departures": [100.0],
            "mobility_arrivals": [50.0],
        },
        geometry=[box(0, 0, 4, 1)],
        crs="EPSG:5179",
    )
    hexes = gpd.GeoDataFrame(
        {"hex_id": ["h1", "h2"]},
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)],
        crs="EPSG:5179",
    )

    result = area_weight_mobility_admin_to_hex(
        mobility_admin,
        hexes,
        value_columns=("mobility_departures", "mobility_arrivals"),
    )

    assert result["mobility_departures"].sum() == pytest.approx(100.0)
    assert result["mobility_arrivals"].sum() == pytest.approx(50.0)
    assert result.set_index("hex_id")["mobility_departures"].to_dict() == pytest.approx(
        {"h1": 50.0, "h2": 50.0}
    )


def test_life_mobility_reuse_guard_checks_source_size_and_complete_report():
    workdir = Path(".pytest-tmp") / f"reuse_guard_{uuid4().hex}"
    workdir.mkdir(parents=True, exist_ok=True)
    source = workdir / "life_mobility.csv"
    source.write_text("source", encoding="utf-8")
    parquet = workdir / "mobility.parquet"
    csv = workdir / "mobility.csv"
    gpkg = workdir / "mobility.gpkg"
    report = workdir / "mobility_qa.json"

    pd.DataFrame({"mobility_admin_code": ["1101053"]}).to_parquet(parquet, index=False)
    csv.write_text("placeholder", encoding="utf-8")
    gpkg.write_text("placeholder", encoding="utf-8")
    report.write_text(
        (
            "{"
            '"status": "complete", '
            '"max_rows": null, '
            f'"source_size_bytes": {source.stat().st_size}, '
            '"input_row_count": 10'
            "}"
        ),
        encoding="utf-8",
    )

    assert _life_mobility_outputs_are_reusable(
        source_path=source,
        parquet_path=parquet,
        csv_path=csv,
        gpkg_path=gpkg,
        report_path=report,
        max_rows=None,
    )

    source.write_text("source changed", encoding="utf-8")
    assert not _life_mobility_outputs_are_reusable(
        source_path=source,
        parquet_path=parquet,
        csv_path=csv,
        gpkg_path=gpkg,
        report_path=report,
        max_rows=None,
    )


def _write_life_mobility_fixture(rows: list[list[object]]) -> Path:
    path = Path(".pytest-tmp") / f"life_mobility_{uuid4().hex}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(
        rows,
        columns=[
            "대상연월",
            "요일",
            "도착시간",
            "출발 행정동 코드",
            "도착 행정동 코드",
            "성별",
            "나이",
            "이동유형",
            "move_pop",
            "masked_count",
            "avg_move_time_min",
        ],
    )
    frame.to_csv(path, index=False, encoding="utf-8")
    return path
