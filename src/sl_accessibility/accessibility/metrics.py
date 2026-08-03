"""접근성 분석과 시나리오 보고서에서 쓰는 작은 지표 함수 모음."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np


def weighted_mean(values: Sequence[float], weights: Sequence[float] | None = None) -> float:
    """결측을 제외하고 산술평균 또는 가중평균을 계산한다."""
    arr = np.asarray(values, dtype=float)
    if weights is None:
        return float(np.nanmean(arr))
    w = np.asarray(weights, dtype=float)
    mask = ~(np.isnan(arr) | np.isnan(w))
    if not mask.any() or np.sum(w[mask]) == 0:
        return math.nan
    return float(np.sum(arr[mask] * w[mask]) / np.sum(w[mask]))


def percentile(values: Sequence[float], q: float) -> float:
    """결측을 제외한 분위수를 반환한다."""
    return float(np.nanpercentile(np.asarray(values, dtype=float), q))


def weighted_percentile(
    values: Sequence[float],
    q: float,
    weights: Sequence[float] | None = None,
) -> float:
    """격자 수가 아니라 가중 사용자가 경험하는 분위수를 계산한다."""
    if weights is None:
        return percentile(values, q)
    x = np.asarray(values, dtype=float)
    w = np.asarray(weights, dtype=float)
    mask = ~(np.isnan(x) | np.isnan(w)) & (w > 0)
    x = x[mask]
    w = w[mask]
    if len(x) == 0 or np.sum(w) == 0:
        return math.nan
    order = np.argsort(x)
    x = x[order]
    w = w[order]
    cutoff = np.clip(q / 100.0, 0.0, 1.0) * np.sum(w)
    return float(x[np.searchsorted(np.cumsum(w), cutoff, side="left")])


def gini(values: Sequence[float], weights: Sequence[float] | None = None) -> float:
    """접근비용 분포의 Gini 계수를 계산한다.

    `weights`를 넣으면 격자 수가 아니라 인구가 경험하는 접근비용 불평등으로 해석한다.
    """
    x = np.asarray(values, dtype=float)
    if weights is None:
        w = np.ones_like(x)
    else:
        w = np.asarray(weights, dtype=float)
    mask = ~(np.isnan(x) | np.isnan(w))
    x = x[mask]
    w = w[mask]
    if len(x) == 0 or np.sum(w) == 0:
        return math.nan
    order = np.argsort(x)
    x = x[order]
    w = w[order]
    total_xw = np.sum(x * w)
    if total_xw == 0:
        return 0.0
    lorenz_x = np.concatenate(([0.0], np.cumsum(w) / np.sum(w)))
    lorenz_y = np.concatenate(([0.0], np.cumsum(x * w) / total_xw))
    area = float(np.sum((lorenz_y[1:] + lorenz_y[:-1]) * np.diff(lorenz_x) / 2.0))
    return float(1.0 - 2.0 * area)


def theil(values: Sequence[float], weights: Sequence[float] | None = None) -> float:
    """접근비용 분포의 Theil index를 계산한다."""
    x = np.asarray(values, dtype=float)
    if weights is None:
        w = np.ones_like(x)
    else:
        w = np.asarray(weights, dtype=float)
    mask = ~(np.isnan(x) | np.isnan(w)) & (x > 0) & (w > 0)
    x = x[mask]
    w = w[mask]
    if len(x) == 0:
        return math.nan
    mean = weighted_mean(x, w)
    ratio = x / mean
    return float(np.sum(w * ratio * np.log(ratio)) / np.sum(w))


def vulnerable_population_reduction(
    baseline_vulnerable: Iterable[bool],
    scenario_vulnerable: Iterable[bool],
    population: Iterable[float],
) -> float:
    """기준선 취약 인구 중 시나리오에서 취약하지 않게 된 비율을 계산한다."""
    base = np.asarray(list(baseline_vulnerable), dtype=bool)
    scen = np.asarray(list(scenario_vulnerable), dtype=bool)
    pop = np.asarray(list(population), dtype=float)
    baseline_pop = np.sum(pop[base])
    if baseline_pop == 0:
        return math.nan
    improved_pop = np.sum(pop[base & ~scen])
    return float(improved_pop / baseline_pop)


@dataclass(frozen=True)
class BaselineNormalizer:
    """기준선 min/max를 고정해 다른 시나리오에도 같은 척도를 적용한다."""

    minimum: float
    maximum: float

    @classmethod
    def fit(cls, baseline_values: Sequence[float]) -> "BaselineNormalizer":
        """기준선 값에서 min/max를 추정한다."""
        arr = np.asarray(baseline_values, dtype=float)
        return cls(minimum=float(np.nanmin(arr)), maximum=float(np.nanmax(arr)))

    def transform(self, values: Sequence[float]) -> np.ndarray:
        """저장된 기준선 min/max로 값을 0~1 근사 범위에 매핑한다."""
        arr = np.asarray(values, dtype=float)
        denom = self.maximum - self.minimum
        if denom == 0:
            return np.zeros_like(arr)
        return (arr - self.minimum) / denom

    def threshold(self, baseline_values: Sequence[float], quantile: float = 0.8) -> float:
        """정규화된 기준선 값의 분위수 threshold를 반환한다."""
        return float(np.nanquantile(self.transform(baseline_values), quantile))
