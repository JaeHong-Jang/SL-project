"""M0-M3 보행 접근비용 함수 모음.

보행 네트워크의 각 링크를 서로 비교 가능한 비용으로 바꾼다.
거리만 보는 M0, 경사를 더한 M1, 기상을 더한 M2,
경사와 기상의 상호작용까지 보는 M3의 연구 가정을 코드로 분리해 둔다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CostParameters:
    """현재 하네스에서 쓰는 시나리오용 비용함수 계수.

    아래 기본값은 서울 보행자료로 보정된 경험계수가 아니다.
    실제 보정값을 정하기 전까지 시나리오/민감도 분석을 돌리기 위한
    투명한 초기값으로 둔다.
    """

    slope_alpha: float = 0.03
    weather_beta: float = 0.03
    interaction_beta: float = 0.08
    snow_weight: float = 5.0
    cap_grade_abs_percent: float = 30.0
    error_grade_abs_percent: float = 100.0

    @classmethod
    def from_mapping(cls, values: dict[str, Any]) -> "CostParameters":
        slope = values.get("slope", {})
        weather = values.get("weather", {})
        return cls(
            slope_alpha=float(slope.get("linear_alpha", cls.slope_alpha)),
            weather_beta=float(weather.get("additive_beta", cls.weather_beta)),
            interaction_beta=float(weather.get("interaction_beta", cls.interaction_beta)),
            snow_weight=float(weather.get("snow_weight", cls.snow_weight)),
            cap_grade_abs_percent=float(slope.get("cost_cap_grade_abs_percent", cls.cap_grade_abs_percent)),
            error_grade_abs_percent=float(
                slope.get("error_exclude_grade_abs_percent", cls.error_grade_abs_percent)
            ),
        )


def sanitize_grade_abs(grade_abs_percent, *, error_threshold: float = 100.0) -> float | None:
    """그래프를 만들기 전에 물리적으로 비정상적인 경사값을 제외한다."""
    if grade_abs_percent in (None, ""):
        return None
    grade = abs(float(grade_abs_percent))
    if grade > error_threshold:
        return None
    return grade


def cap_grade_abs(grade_abs_percent: float, cap: float = 30.0) -> float:
    """원본 경사값은 보존하되 비용 계산에서만 경사의 영향력을 제한한다."""
    return min(abs(float(grade_abs_percent)), cap)


def slope_penalty(grade_abs_percent: float, params: CostParameters | None = None) -> float:
    p = params or CostParameters()
    # 실제 보행망에는 매우 큰 경사 이상치가 섞일 수 있다.
    # 한두 개 의심 링크가 전체 접근성 지도를 지배하지 않도록 cap을 적용한다.
    grade = cap_grade_abs(grade_abs_percent, p.cap_grade_abs_percent)
    return 1.0 + p.slope_alpha * grade


def weather_intensity(rain_mm: float = 0.0, snow_cm: float = 0.0, params: CostParameters | None = None) -> float:
    p = params or CostParameters()
    # 강설은 시나리오 비교를 위해 강수량에 준하는 부담으로 환산한다.
    return max(float(rain_mm or 0.0), 0.0) + p.snow_weight * max(float(snow_cm or 0.0), 0.0)


def weather_additive_factor(rain_mm: float = 0.0, snow_cm: float = 0.0, params: CostParameters | None = None) -> float:
    p = params or CostParameters()
    return 1.0 + p.weather_beta * weather_intensity(rain_mm, snow_cm, p)


def weather_interaction_factor(
    grade_abs_percent: float,
    rain_mm: float = 0.0,
    snow_cm: float = 0.0,
    params: CostParameters | None = None,
) -> float:
    p = params or CostParameters()
    grade_fraction = cap_grade_abs(grade_abs_percent, p.cap_grade_abs_percent) / 100.0
    # M3는 악천후가 서울 전역에 같은 불편을 더한다고 보지 않는다.
    # 경사가 큰 링크일수록 비/눈의 보행 부담이 더 커진다는 가정을 반영한다.
    return 1.0 + p.weather_beta * weather_intensity(rain_mm, snow_cm, p) + (
        p.interaction_beta * weather_intensity(rain_mm, snow_cm, p) * grade_fraction
    )


def cost_m0(length_m: float, *_args, **_kwargs) -> float:
    """현재 400m 커버리지 기준에 가까운 거리 전용 기준선."""
    return float(length_m)


def cost_m1(length_m: float, grade_abs_percent: float, params: CostParameters | None = None) -> float:
    return float(length_m) * slope_penalty(grade_abs_percent, params)


def cost_m2(
    length_m: float,
    grade_abs_percent: float,
    *,
    rain_mm: float = 0.0,
    snow_cm: float = 0.0,
    params: CostParameters | None = None,
) -> float:
    p = params or CostParameters()
    return cost_m1(length_m, grade_abs_percent, p) * weather_additive_factor(rain_mm, snow_cm, p)


def cost_m3(
    length_m: float,
    grade_abs_percent: float,
    *,
    rain_mm: float = 0.0,
    snow_cm: float = 0.0,
    params: CostParameters | None = None,
) -> float:
    p = params or CostParameters()
    return cost_m1(length_m, grade_abs_percent, p) * weather_interaction_factor(grade_abs_percent, rain_mm, snow_cm, p)


def cost_by_model(model: str, length_m: float, grade_abs_percent: float, **kwargs) -> float:
    normalized = model.upper()
    if normalized == "M0":
        return cost_m0(length_m)
    if normalized == "M1":
        return cost_m1(length_m, grade_abs_percent, kwargs.get("params"))
    if normalized == "M2":
        return cost_m2(length_m, grade_abs_percent, **kwargs)
    if normalized == "M3":
        return cost_m3(length_m, grade_abs_percent, **kwargs)
    raise ValueError(f"Unknown cost model: {model}")
