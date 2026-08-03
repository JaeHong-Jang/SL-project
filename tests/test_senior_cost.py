"""M4-senior 비용함수 단위 테스트."""

import math

import pytest

from sl_accessibility.accessibility.senior_cost import (
    SENIOR_SPEED_PROFILES_M_PER_S,
    SeniorCostParameters,
    edge_cost_m4_senior_min,
    grade_band_label,
    is_steps_highway,
    rescale_time_for_speed,
    senior_base_time_min,
    senior_slope_time_factor,
    senior_step_time_factor,
    senior_weather_time_factor,
)


def test_base_time_matches_v2_2_example():
    # v2.2 §0-quater.2: 90m 평지를 0.90m/s로 걸으면 약 1.67분
    assert senior_base_time_min(90.0, 0.90) == pytest.approx(1.6667, abs=1e-3)
    assert senior_base_time_min(90.0, 1.12) == pytest.approx(1.3393, abs=1e-3)


def test_slope_factor_is_one_on_flat_and_increases_uphill():
    flat = senior_slope_time_factor(0.0)
    mild = senior_slope_time_factor(5.0)
    steep = senior_slope_time_factor(12.0)
    assert flat == pytest.approx(1.0)
    assert 1.0 < mild < steep


def test_slope_factor_downhill_never_speeds_up_below_flat():
    # 내리막 가속은 1.0 밑으로 내려가지 않게 clamp한다
    assert senior_slope_time_factor(-5.0) >= 1.0
    assert senior_slope_time_factor(-30.0) >= 1.0


def test_slope_factor_caps_extreme_grades():
    capped = senior_slope_time_factor(30.0)
    beyond = senior_slope_time_factor(96.0)
    assert beyond == pytest.approx(capped)


def test_weather_factor_ordering_dry_rain_snow():
    dry = senior_weather_time_factor("dry")
    rain = senior_weather_time_factor("rain")
    snow = senior_weather_time_factor("snow")
    assert dry == pytest.approx(1.0)
    assert dry < rain < snow


def test_step_policy_factors():
    assert senior_step_time_factor(False, "steps_barrier") == 1.0
    assert senior_step_time_factor(True, "steps_allowed") == 1.0
    assert senior_step_time_factor(True, "steps_penalty") == pytest.approx(3.0)
    assert senior_step_time_factor(True, "steps_barrier") is None


def test_edge_cost_barrier_removes_steps_edge():
    cost = edge_cost_m4_senior_min(
        100.0,
        0.0,
        weather_profile="dry",
        is_steps_edge=True,
        step_policy="steps_barrier",
    )
    assert cost is None


def test_edge_cost_combines_factors_multiplicatively():
    params = SeniorCostParameters(flat_speed_m_per_s=0.90)
    cost = edge_cost_m4_senior_min(
        100.0,
        10.0,
        weather_profile="rain",
        is_steps_edge=True,
        step_policy="steps_penalty",
        params=params,
    )
    expected = (
        senior_base_time_min(100.0, 0.90)
        * senior_slope_time_factor(10.0, params)
        * senior_weather_time_factor("rain")
        * 3.0
    )
    assert cost == pytest.approx(expected)


def test_speed_rescaling_is_pure_ratio():
    # 속도는 모든 edge 공통 상수라 경로를 바꾸지 않고 시간만 비례 환산된다
    t_base = edge_cost_m4_senior_min(120.0, 8.0, weather_profile="snow")
    t_slow = rescale_time_for_speed(
        t_base,
        reference_speed_m_per_s=0.90,
        target_speed_m_per_s=0.70,
    )
    assert t_slow == pytest.approx(t_base * 0.90 / 0.70)


def test_speed_profiles_match_plan_values():
    assert SENIOR_SPEED_PROFILES_M_PER_S == {
        "very_slow": 0.70,
        "slow": 0.80,
        "base": 0.90,
        "optimistic": 1.07,
    }


def test_grade_band_labels_follow_ramp_thresholds():
    assert grade_band_label(1.0) == "near_flat"
    assert grade_band_label(4.0) == "mild"
    assert grade_band_label(7.0) == "ramp_like"
    assert grade_band_label(10.0) == "steep"
    assert grade_band_label(20.0) == "very_steep"


def test_is_steps_highway_handles_list_strings_and_missing():
    assert is_steps_highway("steps")
    assert is_steps_highway("['footway', 'steps']")
    assert not is_steps_highway("footway")
    assert not is_steps_highway(None)


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        senior_weather_time_factor("typhoon")
    with pytest.raises(ValueError):
        senior_step_time_factor(True, "steps_unknown")
    with pytest.raises(ValueError):
        senior_base_time_min(100.0, 0.0)
    with pytest.raises(ValueError):
        rescale_time_for_speed(1.0, reference_speed_m_per_s=0.9, target_speed_m_per_s=0.0)


def test_math_sanity_tobler_shape():
    # +5% 경사에서 평지 대비 시간계수는 exp(3.5*(|0.10|-0.05)) = exp(0.175)
    assert senior_slope_time_factor(5.0) == pytest.approx(math.exp(0.175), rel=1e-9)
