from sl_accessibility.accessibility.metrics import (
    gini,
    percentile,
    theil,
    vulnerable_population_reduction,
    weighted_mean,
    weighted_percentile,
)


def test_weighted_mean_and_percentile():
    assert weighted_mean([1, 3], [1, 3]) == 2.5
    assert percentile([1, 2, 3, 4], 50) == 2.5
    assert weighted_percentile([1, 2, 3], 50, [1, 1, 1]) == 2.0
    assert weighted_percentile([1, 2, 3], 50, [1, 1, 10]) == 3.0


def test_inequality_metrics_basic_bounds():
    assert gini([1, 1, 1]) == 0.0
    assert theil([1, 1, 1]) == 0.0
    assert gini([1, 2, 3]) > 0
    assert theil([1, 2, 3]) > 0


def test_vulnerable_population_reduction():
    reduction = vulnerable_population_reduction(
        baseline_vulnerable=[True, True, False],
        scenario_vulnerable=[False, True, False],
        population=[10, 30, 100],
    )
    assert reduction == 0.25
