"""S0-M3 고정 정규화를 사용하는 시나리오 비교 도구.

정책 시나리오는 같은 척도에서 비교해야 한다.
이 모듈은 S0-M3의 비용/수요 정규화 기준과 취약 threshold를 고정한 뒤,
그 기준을 S1/S3/S4에 그대로 적용한다.
이렇게 해야 개선 효과가 정규화 재조정이 아니라 실제 시나리오 변화로 해석된다.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Sequence

import numpy as np
import pandas as pd

from sl_accessibility.accessibility.metrics import (
    BaselineNormalizer,
    gini,
    theil,
    vulnerable_population_reduction,
    weighted_mean,
    weighted_percentile,
)


def _float_array(values: Sequence[float]) -> np.ndarray:
    return np.asarray(values, dtype=float)


def _reduction_rate(baseline_value: float, scenario_value: float) -> float:
    if math.isnan(baseline_value) or baseline_value == 0:
        return math.nan
    return float((baseline_value - scenario_value) / baseline_value)


def _mask_reduction_rate(baseline_mask: np.ndarray, scenario_mask: np.ndarray) -> float:
    baseline_count = int(np.sum(baseline_mask))
    if baseline_count == 0:
        return math.nan
    improved_count = int(np.sum(baseline_mask & ~scenario_mask))
    return float(improved_count / baseline_count)


@dataclass(frozen=True)
class FrozenBaseline:
    """시나리오들이 재사용할 S0-M3 정규화 기준과 취약 threshold."""

    cost_normalizer: BaselineNormalizer
    demand_normalizer: BaselineNormalizer
    vulnerability_threshold: float
    vulnerable_quantile: float = 0.8

    @classmethod
    def fit(
        cls,
        baseline_cost: Sequence[float],
        demand: Sequence[float],
        *,
        vulnerable_quantile: float = 0.8,
    ) -> "FrozenBaseline":
        """S0-M3에서 한 번만 fit하고 모든 정책 시나리오에 재사용한다."""
        cost_normalizer = BaselineNormalizer.fit(baseline_cost)
        demand_normalizer = BaselineNormalizer.fit(demand)
        cost_norm = cost_normalizer.transform(baseline_cost)
        demand_norm = demand_normalizer.transform(demand)
        vulnerability = cost_norm * demand_norm
        threshold = float(np.nanquantile(vulnerability, vulnerable_quantile))
        return cls(
            cost_normalizer=cost_normalizer,
            demand_normalizer=demand_normalizer,
            vulnerability_threshold=threshold,
            vulnerable_quantile=vulnerable_quantile,
        )

    def normalized_cost(self, cost: Sequence[float]) -> np.ndarray:
        return self.cost_normalizer.transform(cost)

    def normalized_demand(self, demand: Sequence[float]) -> np.ndarray:
        return self.demand_normalizer.transform(demand)

    def vulnerability(self, cost: Sequence[float], demand: Sequence[float]) -> np.ndarray:
        return self.normalized_cost(cost) * self.normalized_demand(demand)

    def vulnerable_mask(self, cost: Sequence[float], demand: Sequence[float]) -> np.ndarray:
        return self.vulnerability(cost, demand) >= self.vulnerability_threshold


@dataclass(frozen=True)
class ScenarioEvaluation:
    scenario_name: str
    baseline_vulnerable_count: int
    scenario_vulnerable_count: int
    mean_cost_reduction: float
    population_weighted_mean_cost_reduction: float
    senior_weighted_mean_cost_reduction: float
    p90_cost_reduction: float
    population_weighted_p90_cost_reduction: float
    senior_weighted_p90_cost_reduction: float
    vulnerable_hex_reduction: float
    vulnerable_population_reduction: float
    senior_vulnerable_population_reduction: float
    gini_change: float
    theil_change: float

    def to_dict(self) -> dict[str, float | int | str]:
        return asdict(self)


def evaluate_scenario_rows(
    *,
    hex_id: Sequence[object],
    baseline_cost: Sequence[float],
    scenario_cost: Sequence[float],
    demand: Sequence[float],
    official_400m_ok: Sequence[bool] | None = None,
    frozen_baseline: FrozenBaseline | None = None,
    scenario_demand: Sequence[float] | None = None,
    vulnerable_quantile: float = 0.8,
) -> pd.DataFrame:
    """Return per-hex scenario deltas under one frozen baseline.

    `evaluate_scenario()` is aggregate-only. Scenario review maps also need the
    row-level burden change, rank movement, and hidden/resolved flags.  Higher
    vulnerability rank is reported as rank 1, so a positive
    `delta_rank_improvement` means the hex moved down the risk list.
    """

    base_cost = _float_array(baseline_cost)
    scen_cost = _float_array(scenario_cost)
    demand_arr = _float_array(demand)
    scen_demand = demand_arr if scenario_demand is None else _float_array(scenario_demand)
    frozen = frozen_baseline or FrozenBaseline.fit(
        base_cost,
        demand_arr,
        vulnerable_quantile=vulnerable_quantile,
    )

    base_vulnerability = frozen.vulnerability(base_cost, demand_arr)
    scen_vulnerability = frozen.vulnerability(scen_cost, scen_demand)
    base_mask = frozen.vulnerable_mask(base_cost, demand_arr)
    scen_mask = frozen.vulnerable_mask(scen_cost, scen_demand)
    if official_400m_ok is None:
        official_ok = np.zeros(len(base_cost), dtype=bool)
    else:
        official_ok = np.asarray(official_400m_ok, dtype=bool)

    baseline_rank = pd.Series(base_vulnerability).rank(ascending=False, method="average")
    scenario_rank = pd.Series(scen_vulnerability).rank(ascending=False, method="average")
    delta_cost = base_cost - scen_cost
    delta_cost_pct = np.full(len(base_cost), np.nan, dtype=float)
    np.divide(delta_cost, base_cost, out=delta_cost_pct, where=base_cost > 0)

    return pd.DataFrame(
        {
            "hex_id": list(hex_id),
            "baseline_cost": base_cost,
            "scenario_cost": scen_cost,
            "delta_cost": delta_cost,
            "delta_cost_pct": delta_cost_pct,
            "baseline_vulnerability": base_vulnerability,
            "scenario_vulnerability": scen_vulnerability,
            "delta_vulnerability": base_vulnerability - scen_vulnerability,
            "baseline_rank_worst_1": baseline_rank,
            "scenario_rank_worst_1": scenario_rank,
            "delta_rank_improvement": scenario_rank - baseline_rank,
            "baseline_vulnerable": base_mask,
            "scenario_vulnerable": scen_mask,
            "resolved_vulnerable": base_mask & ~scen_mask,
            "new_vulnerable": ~base_mask & scen_mask,
            "official_400m_ok": official_ok,
            "baseline_hidden": official_ok & base_mask,
            "scenario_hidden": official_ok & scen_mask,
            "resolved_hidden": (official_ok & base_mask) & ~(official_ok & scen_mask),
            "new_hidden": ~(official_ok & base_mask) & (official_ok & scen_mask),
        }
    )


def evaluate_scenario(
    *,
    baseline_cost: Sequence[float],
    scenario_cost: Sequence[float],
    demand: Sequence[float],
    population: Sequence[float],
    senior_population: Sequence[float] | None = None,
    frozen_baseline: FrozenBaseline | None = None,
    scenario_demand: Sequence[float] | None = None,
    scenario_name: str = "scenario",
    vulnerable_quantile: float = 0.8,
) -> ScenarioEvaluation:
    """고정된 S0-M3 기준으로 정책 시나리오를 비교한다.

    보통 `frozen_baseline`은 S0-M3에서 한 번 만든 뒤 S1/S3/S4에 재사용한다.
    전달하지 않으면 `baseline_cost`와 `demand`로 즉석에서 만든다.
    """

    base_cost = _float_array(baseline_cost)
    scen_cost = _float_array(scenario_cost)
    demand_arr = _float_array(demand)
    scen_demand = demand_arr if scenario_demand is None else _float_array(scenario_demand)
    pop = _float_array(population)
    senior_pop = pop if senior_population is None else _float_array(senior_population)
    frozen = frozen_baseline or FrozenBaseline.fit(
        base_cost,
        demand_arr,
        vulnerable_quantile=vulnerable_quantile,
    )

    # 두 mask는 같은 기준선 threshold를 사용한다.
    # 시나리오별 재정규화로 개선 효과가 과장되는 일을 막는 핵심 안전장치다.
    base_mask = frozen.vulnerable_mask(base_cost, demand_arr)
    scen_mask = frozen.vulnerable_mask(scen_cost, scen_demand)

    base_mean = weighted_mean(base_cost)
    scen_mean = weighted_mean(scen_cost)
    base_pop_mean = weighted_mean(base_cost, pop)
    scen_pop_mean = weighted_mean(scen_cost, pop)
    base_senior_mean = weighted_mean(base_cost, senior_pop)
    scen_senior_mean = weighted_mean(scen_cost, senior_pop)

    base_p90 = weighted_percentile(base_cost, 90)
    scen_p90 = weighted_percentile(scen_cost, 90)
    base_pop_p90 = weighted_percentile(base_cost, 90, pop)
    scen_pop_p90 = weighted_percentile(scen_cost, 90, pop)
    base_senior_p90 = weighted_percentile(base_cost, 90, senior_pop)
    scen_senior_p90 = weighted_percentile(scen_cost, 90, senior_pop)

    return ScenarioEvaluation(
        scenario_name=scenario_name,
        baseline_vulnerable_count=int(np.sum(base_mask)),
        scenario_vulnerable_count=int(np.sum(scen_mask)),
        mean_cost_reduction=_reduction_rate(base_mean, scen_mean),
        population_weighted_mean_cost_reduction=_reduction_rate(base_pop_mean, scen_pop_mean),
        senior_weighted_mean_cost_reduction=_reduction_rate(base_senior_mean, scen_senior_mean),
        p90_cost_reduction=_reduction_rate(base_p90, scen_p90),
        population_weighted_p90_cost_reduction=_reduction_rate(base_pop_p90, scen_pop_p90),
        senior_weighted_p90_cost_reduction=_reduction_rate(base_senior_p90, scen_senior_p90),
        vulnerable_hex_reduction=_mask_reduction_rate(base_mask, scen_mask),
        vulnerable_population_reduction=vulnerable_population_reduction(base_mask, scen_mask, pop),
        senior_vulnerable_population_reduction=vulnerable_population_reduction(
            base_mask,
            scen_mask,
            senior_pop,
        ),
        gini_change=gini(scen_cost, pop) - gini(base_cost, pop),
        theil_change=theil(scen_cost, pop) - theil(base_cost, pop),
    )
