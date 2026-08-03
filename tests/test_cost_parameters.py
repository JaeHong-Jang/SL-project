from sl_accessibility.accessibility.costs import CostParameters


def test_cost_parameters_load_from_model_param_mapping():
    params = CostParameters.from_mapping(
        {
            "slope": {
                "linear_alpha": 0.02,
                "cost_cap_grade_abs_percent": 25,
                "error_exclude_grade_abs_percent": 90,
            },
            "weather": {
                "additive_beta": 0.01,
                "interaction_beta": 0.04,
                "snow_weight": 3,
            },
        }
    )
    assert params.slope_alpha == 0.02
    assert params.cap_grade_abs_percent == 25
    assert params.error_grade_abs_percent == 90
    assert params.weather_beta == 0.01
    assert params.interaction_beta == 0.04
    assert params.snow_weight == 3
