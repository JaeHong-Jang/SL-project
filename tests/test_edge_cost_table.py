import pytest

from sl_accessibility.accessibility.edge_cost_table import build_edge_cost_table
from sl_accessibility.accessibility.edge_cost_table import add_edge_cost_columns_lazy

pl = pytest.importorskip("polars")


def test_edge_cost_table_adds_increasing_model_costs():
    rows = build_edge_cost_table(
        [{"edge_id": "a", "length_m": 100, "grade_abs_percent": 10}],
        rain_mm=2,
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["cost_m0"] < row["cost_m1"] < row["cost_m2"] < row["cost_m3"]


def test_edge_cost_table_excludes_unusable_slope_rows():
    rows = build_edge_cost_table(
        [
            {"edge_id": "ok", "length_m": 100, "grade_abs_percent": 8},
            {"edge_id": "bad", "length_m": 100, "grade_abs_percent": 684.6},
            {"edge_id": "missing", "length_m": 100, "grade_abs_percent": None},
        ]
    )

    assert [row["edge_id"] for row in rows] == ["ok"]


def test_edge_cost_table_does_not_mutate_source_rows():
    source = [{"edge_id": "steep", "length_m": 100, "grade_abs_percent": 47.7}]
    original = [dict(row) for row in source]

    rows = build_edge_cost_table(source)

    assert source == original
    assert "cost_m0" not in source[0]
    assert rows[0]["grade_abs_percent"] == 47.7


def test_lazy_edge_cost_columns_match_row_builder():
    source = [
        {"edge_id": "a", "length_m": 100, "grade_abs_percent": 10},
        {"edge_id": "bad", "length_m": 100, "grade_abs_percent": 684.6},
    ]

    expected = build_edge_cost_table(source, rain_mm=2)
    result = add_edge_cost_columns_lazy(pl.LazyFrame(source), rain_mm=2).collect().to_dicts()

    assert len(result) == 1
    for column in ("cost_m0", "cost_m1", "cost_m2", "cost_m3"):
        assert result[0][column] == expected[0][column]
