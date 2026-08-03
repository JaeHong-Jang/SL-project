from sl_accessibility.accessibility.scenario import (
    FrozenBaseline,
    evaluate_scenario,
    evaluate_scenario_rows,
)


def test_frozen_baseline_uses_s0_threshold_for_scenario():
    baseline = FrozenBaseline.fit(
        baseline_cost=[10, 20, 30, 40],
        demand=[1, 2, 3, 4],
        vulnerable_quantile=0.75,
    )

    assert baseline.vulnerable_mask([10, 20, 30, 40], [1, 2, 3, 4]).tolist() == [
        False,
        False,
        False,
        True,
    ]
    assert baseline.vulnerable_mask([10, 20, 30, 20], [1, 2, 3, 4]).tolist() == [
        False,
        False,
        False,
        False,
    ]


def test_evaluate_scenario_reports_fixed_baseline_improvement():
    summary = evaluate_scenario(
        scenario_name="S3",
        baseline_cost=[10, 20, 30, 40],
        scenario_cost=[8, 15, 25, 20],
        demand=[1, 2, 3, 4],
        population=[10, 20, 30, 40],
        senior_population=[5, 10, 15, 20],
        vulnerable_quantile=0.75,
    )

    assert summary.scenario_name == "S3"
    assert summary.baseline_vulnerable_count == 1
    assert summary.scenario_vulnerable_count == 0
    assert summary.vulnerable_hex_reduction == 1.0
    assert summary.vulnerable_population_reduction == 1.0
    assert summary.senior_vulnerable_population_reduction == 1.0
    assert summary.population_weighted_mean_cost_reduction > 0


def test_evaluate_scenario_rows_reports_delta_and_rank_change():
    rows = evaluate_scenario_rows(
        hex_id=["h1", "h2", "h3", "h4"],
        baseline_cost=[10, 20, 30, 40],
        scenario_cost=[10, 20, 30, 10],
        demand=[1, 2, 3, 4],
        official_400m_ok=[True, True, True, True],
        vulnerable_quantile=0.75,
    )

    h4 = rows.loc[rows["hex_id"] == "h4"].iloc[0]

    assert h4["delta_cost"] == 30
    assert h4["delta_vulnerability"] > 0
    assert h4["resolved_vulnerable"]
    assert h4["resolved_hidden"]
    assert h4["delta_rank_improvement"] > 0
