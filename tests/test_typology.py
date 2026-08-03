import pandas as pd
import pytest

from sl_accessibility.accessibility.typology import (
    classify_vulnerability_typology,
    vulnerability_type_summary,
)


def _base_row(hex_id, vulnerable, m0, m1, m2, m3):
    return {
        "hex_id": hex_id,
        "vulnerable_m3_final": vulnerable,
        "access_cost_m0": float(m0),
        "access_cost_m1": float(m1),
        "access_cost_m2": float(m2),
        "access_cost_m3": float(m3),
    }


def test_slope_vulnerable_classification():
    # slope_share = (m1-m0)/(m3-m0) = 150/165 ≈ 0.91 >> 0.40
    features = pd.DataFrame([
        _base_row("h1", True,  200, 350, 360, 365),
        _base_row("h2", False, 100, 105, 107, 108),
        _base_row("h3", False, 150, 155, 157, 158),
    ])

    result = classify_vulnerability_typology(features)

    assert result.loc[result["hex_id"] == "h1", "vulnerability_type"].iloc[0] == "slope_vulnerable"


def test_weather_amplified_classification():
    # interaction_share = (m3-m2)/(m3-m0) = 40/60 ≈ 0.67 >> 0.25
    # slope_share = (m1-m0)/(m3-m0) = 10/60 ≈ 0.17 < 0.40
    features = pd.DataFrame([
        _base_row("h1", True,  200, 210, 220, 260),
        _base_row("h2", False, 100, 105, 107, 108),
    ])

    result = classify_vulnerability_typology(features)

    assert result.loc[result["hex_id"] == "h1", "vulnerability_type"].iloc[0] == "weather_amplified"


def test_supply_shortage_classification():
    # slope_share = 3/8 = 0.375 < 0.40, interaction_share = 1/8 = 0.125 < 0.25
    # distance_quantile=0.5 → median of [500, 100] = 300 → h1(m0=500) >= 300 → supply_shortage
    features = pd.DataFrame([
        _base_row("h1", True,  500, 503, 507, 508),
        _base_row("h2", True,  100, 103, 107, 108),
        _base_row("h3", False, 150, 155, 157, 158),
    ])

    result = classify_vulnerability_typology(features, distance_quantile=0.5)

    assert result.loc[result["hex_id"] == "h1", "vulnerability_type"].iloc[0] == "supply_shortage"


def test_high_demand_classification():
    # slope_share = 3/8 = 0.375 < 0.40, interaction_share = 1/8 = 0.125 < 0.25
    # two vulnerable hexes: 0.75-quantile of [100, 150] = 137.5 → h1(m0=100) < 137.5 → high_demand
    features = pd.DataFrame([
        _base_row("h1", True,  100, 103, 107, 108),
        _base_row("h2", True,  150, 153, 157, 158),
        _base_row("h3", False, 200, 205, 207, 208),
    ])

    result = classify_vulnerability_typology(features)

    assert result.loc[result["hex_id"] == "h1", "vulnerability_type"].iloc[0] == "high_demand"


def test_non_vulnerable_hex_type_is_none():
    features = pd.DataFrame([
        _base_row("h1", True,  200, 350, 360, 365),
        _base_row("h2", False, 100, 105, 107, 108),
    ])

    result = classify_vulnerability_typology(features)

    assert result.loc[result["hex_id"] == "h2", "vulnerability_type"].iloc[0] is None


def test_all_vulnerable_hexes_receive_type():
    features = pd.DataFrame([
        _base_row("h1", True, 200, 350, 360, 365),
        _base_row("h2", True, 100, 105, 107, 108),
        _base_row("h3", True, 500, 510, 512, 514),
        _base_row("h4", False, 150, 155, 157, 158),
    ])

    result = classify_vulnerability_typology(features)

    vulnerable_mask = result["vulnerable_m3_final"]
    assert result.loc[vulnerable_mask, "vulnerability_type"].notna().all()


def test_no_internal_columns_leaked():
    features = pd.DataFrame([
        _base_row("h1", True, 200, 350, 360, 365),
        _base_row("h2", False, 100, 105, 107, 108),
    ])

    result = classify_vulnerability_typology(features)

    internal_cols = [
        "_slope_increment",
        "_weather_increment",
        "_interaction_increment",
        "_total_env_increment",
        "_slope_share",
        "_interaction_share",
    ]
    for col in internal_cols:
        assert col not in result.columns, f"내부 컬럼 {col!r}이 반환된 DataFrame에 남아 있음"


def test_vulnerability_type_summary_aggregation():
    # h1, h2: slope_share ≈ 0.91 → slope_vulnerable (2개)
    # h3: slope_share=3/8=0.375 < 0.40, interaction=1/8 < 0.25, m0=100 < quantile(200) → high_demand (1개)
    features = pd.DataFrame([
        _base_row("h1", True, 200, 350, 360, 365),
        _base_row("h2", True, 200, 350, 360, 365),
        _base_row("h3", True, 100, 103, 107, 108),
        _base_row("h4", False, 150, 155, 157, 158),
    ])
    features["registered_population"] = [100, 200, 50, 999]
    features["registered_senior_population"] = [10, 20, 5, 0]

    typed = classify_vulnerability_typology(features)
    summary = vulnerability_type_summary(typed)

    slope_row = summary.loc[summary["vulnerability_type"] == "slope_vulnerable"]
    demand_row = summary.loc[summary["vulnerability_type"] == "high_demand"]

    assert slope_row["hex_count"].iloc[0] == 2
    assert slope_row["population_sum"].iloc[0] == 300
    assert demand_row["hex_count"].iloc[0] == 1
    assert demand_row["population_sum"].iloc[0] == 50

    assert abs(summary["population_share"].sum() - 1.0) < 1e-6


def test_no_vulnerable_hexes_returns_none_type_column():
    features = pd.DataFrame([
        _base_row("h1", False, 200, 210, 220, 260),
        _base_row("h2", False, 100, 105, 107, 108),
    ])

    result = classify_vulnerability_typology(features)

    assert result["vulnerability_type"].isna().all()


def test_missing_required_column_raises_key_error():
    features = pd.DataFrame([
        {
            "hex_id": "h1",
            "vulnerable_m3_final": True,
            "access_cost_m0": 200.0,
            # access_cost_m1 intentionally omitted
            "access_cost_m2": 360.0,
            "access_cost_m3": 365.0,
        }
    ])

    with pytest.raises(KeyError):
        classify_vulnerability_typology(features)
