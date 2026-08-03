from sl_accessibility.accessibility.costs import (
    cap_grade_abs,
    cost_m0,
    cost_m1,
    cost_m2,
    cost_m3,
    sanitize_grade_abs,
)


def test_cost_models_increase_with_slope_and_weather():
    m0 = cost_m0(100)
    m1 = cost_m1(100, 10)
    m2 = cost_m2(100, 10, rain_mm=2)
    m3 = cost_m3(100, 10, rain_mm=2)
    assert m0 < m1 < m2 < m3


def test_slope_cap_and_error_threshold():
    assert sanitize_grade_abs(684.6) is None
    assert cap_grade_abs(47.7, cap=30) == 30


def test_no_weather_m3_equals_m1():
    assert cost_m3(100, 12, rain_mm=0, snow_cm=0) == cost_m1(100, 12)
