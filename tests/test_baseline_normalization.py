import numpy as np

from sl_accessibility.accessibility.metrics import BaselineNormalizer


def test_baseline_normalizer_reuses_s0_range_for_scenarios():
    normalizer = BaselineNormalizer.fit([10, 20, 30])
    scenario = normalizer.transform([5, 20, 25])
    assert np.allclose(scenario, [-0.25, 0.5, 0.75])
    assert normalizer.minimum == 10
    assert normalizer.maximum == 30


def test_threshold_is_defined_on_baseline_transform():
    normalizer = BaselineNormalizer.fit([10, 20, 30])
    assert normalizer.threshold([10, 20, 30], quantile=0.5) == 0.5
