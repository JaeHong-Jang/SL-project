"""M4-senior 고령자 보행 임피던스 edge 비용 함수.

M0-M3는 연령공통 distance-equivalent 비용이다. M4-senior는 v2.2 계획
(§0-quater)에 따라 edge 통과시간(minutes)을 기본 단위로 두고,
고령 평지속도 × 경사 시간계수 × 기상 시간계수 × 계단 정책을 분리해 계산한다.

여기 값들은 관측 보행자료로 보정된 계수가 아니라 profile scenario parameter다.
따라서 단일 숫자가 아니라 속도/기상/계단 프로필 조합의 민감도로 보고해야 한다.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


# 고령 보행속도 프로필 (m/s). v2.2 §0-quater.2 기준.
# 1.12m/s(현행 generic 67m/min)는 고령자 기본값으로 쓰지 않고 비교용으로만 둔다.
SENIOR_SPEED_PROFILES_M_PER_S: dict[str, float] = {
    "very_slow": 0.70,
    "slow": 0.80,
    "base": 0.90,
    "optimistic": 1.07,
}

# 계단 정책. barrier는 steps edge를 보행망에서 제거(도달 불가 처리)한다.
STEP_POLICIES: tuple[str, ...] = ("steps_allowed", "steps_penalty", "steps_barrier")
STEP_PENALTY_FACTOR: float = 3.0

# 기상 프로필. intensity = rain_mm + snow_weight * snow_cm.
# rain은 M3 기준선(rain_mm=2)과 정렬하고, snow는 적설 1cm에 snow_weight=8을 적용한다.
WEATHER_PROFILES: dict[str, dict[str, float]] = {
    "dry": {"beta_weather": 0.0, "intensity": 0.0},
    "rain": {"beta_weather": 0.03, "intensity": 2.0},
    "snow": {"beta_weather": 0.03, "intensity": 8.0},
}

# 경사 band 라벨 경계(%). 5%/8.33%는 접근로·ramp(1/12) 기준에서 온 해석용 threshold다.
GRADE_BAND_BOUNDS: tuple[tuple[float, str], ...] = (
    (2.0, "near_flat"),
    (5.0, "mild"),
    (8.33, "ramp_like"),
    (12.0, "steep"),
    (float("inf"), "very_steep"),
)


@dataclass(frozen=True)
class SeniorCostParameters:
    """M4-senior profile scenario parameter 묶음."""

    flat_speed_m_per_s: float = 0.90
    slope_cap_percent: float = 30.0
    tobler_scale: float = 3.5
    tobler_offset: float = 0.05
    step_penalty_factor: float = STEP_PENALTY_FACTOR


def grade_band_label(grade_abs_percent: float) -> str:
    """절대경사를 해석용 band 라벨로 바꾼다."""
    grade = abs(float(grade_abs_percent))
    for bound, label in GRADE_BAND_BOUNDS:
        if grade <= bound:
            return label
    return "very_steep"


def senior_base_time_min(length_m: float, flat_speed_m_per_s: float) -> float:
    """평지 기준 edge 통과시간(minutes)."""
    if flat_speed_m_per_s <= 0:
        raise ValueError("flat_speed_m_per_s는 양수여야 합니다.")
    return float(length_m) / (float(flat_speed_m_per_s) * 60.0)


def senior_slope_time_factor(
    grade_percent: float,
    params: SeniorCostParameters | None = None,
) -> float:
    """Tobler hiking function 기반 경사 시간계수.

    부호 있는 경사(오르막 +, 내리막 -)를 사용한다. Tobler 속도식을 평지속도로
    정규화한 시간비를 쓰되, 내리막 가속은 1.0 밑으로 내려가지 않게 clamp한다
    (v2.2 §0-quater.3 `slope_time_factor = max(1.0, tobler_time_factor)`).
    """
    p = params or SeniorCostParameters()
    capped = max(min(float(grade_percent), p.slope_cap_percent), -p.slope_cap_percent)
    s = capped / 100.0
    tobler_time = math.exp(p.tobler_scale * (abs(s + p.tobler_offset) - p.tobler_offset))
    return max(1.0, tobler_time)


def senior_weather_time_factor(weather_profile: str) -> float:
    """기상 프로필별 시간계수. ASOS 단일 관측소 기반 공간균일 시나리오다."""
    if weather_profile not in WEATHER_PROFILES:
        raise ValueError(f"알 수 없는 weather profile: {weather_profile}")
    profile = WEATHER_PROFILES[weather_profile]
    return 1.0 + profile["beta_weather"] * profile["intensity"]


def is_steps_highway(highway_value: object) -> bool:
    """OSM highway 값에 steps가 포함되는지 판정한다(list 문자열 포함)."""
    if highway_value is None:
        return False
    return "steps" in str(highway_value).lower()


def senior_step_time_factor(
    is_steps_edge: bool,
    step_policy: str,
    params: SeniorCostParameters | None = None,
) -> float | None:
    """계단 정책별 시간계수. barrier에서 steps edge는 None(제거)을 돌려준다."""
    if step_policy not in STEP_POLICIES:
        raise ValueError(f"알 수 없는 step policy: {step_policy}")
    if not is_steps_edge:
        return 1.0
    if step_policy == "steps_allowed":
        return 1.0
    if step_policy == "steps_penalty":
        p = params or SeniorCostParameters()
        return p.step_penalty_factor
    return None


def edge_cost_m4_senior_min(
    length_m: float,
    grade_percent: float,
    *,
    weather_profile: str = "rain",
    is_steps_edge: bool = False,
    step_policy: str = "steps_penalty",
    params: SeniorCostParameters | None = None,
) -> float | None:
    """edge 하나의 M4-senior 통과시간(minutes).

    barrier 정책에서 steps edge는 None을 돌려 보행망에서 제외하게 한다.
    속도 프로필은 모든 edge에 같은 상수로 곱해지므로 최단경로 자체는 바꾸지
    않는다. 경로를 바꾸는 항은 경사·기상×경사·계단이다.
    """
    p = params or SeniorCostParameters()
    step_factor = senior_step_time_factor(is_steps_edge, step_policy, p)
    if step_factor is None:
        return None
    return (
        senior_base_time_min(length_m, p.flat_speed_m_per_s)
        * senior_slope_time_factor(grade_percent, p)
        * senior_weather_time_factor(weather_profile)
        * step_factor
    )


def rescale_time_for_speed(
    time_min_at_reference: float,
    *,
    reference_speed_m_per_s: float,
    target_speed_m_per_s: float,
) -> float:
    """기준 속도로 계산한 통과/접근시간을 다른 평지속도 프로필로 환산한다.

    속도는 모든 edge에 동일 상수로 작용해 최단경로 집합을 바꾸지 않으므로,
    Dijkstra를 다시 돌리지 않고 시간만 비례 환산할 수 있다.
    """
    if target_speed_m_per_s <= 0:
        raise ValueError("target_speed_m_per_s는 양수여야 합니다.")
    return float(time_min_at_reference) * (reference_speed_m_per_s / target_speed_m_per_s)
