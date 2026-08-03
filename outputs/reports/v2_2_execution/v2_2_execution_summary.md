# v2.2 Execution Summary

Date: 2026-05-31

## Claim Boundary

These artifacts support potential-accessibility burden screening and field-review prioritization.
They do not support realized ridership demand prediction or policy-intervention effect claims.

## Core Counts

- Valid hex: 4,383
- M3 vulnerable hex: 877
- Hidden vulnerable hex: 632
- Robust-core hidden hex: 429
- Normalization-sensitive hidden candidates: 624

## M0 to M3 Environment Burden

- M0-M3 Spearman: 0.994695
- Mean cost increase: 15.4%
- Senior-weighted cost increase: 15.8%
- M0 <= 400m but M3 > 400m: 167
- New vulnerable under frozen M0 threshold: 275

## Robustness Table

| variant | hidden_hex_count | hidden_replacement_rate | claim_use |
|---|---:|---:|---|
| baseline_minmax_product | 632 | 0.000 | robustness_check_not_monte_carlo |
| winsorize_1_99_product | 636 | 0.006 | robustness_check_not_monte_carlo |
| log1p_product | 808 | 0.576 | robustness_check_not_monte_carlo |
| rank_product | 755 | 0.238 | robustness_check_not_monte_carlo |
| additive_minmax | 796 | 0.690 | robustness_check_not_monte_carlo |
| threshold_top_10pct | 252 | 0.601 | threshold_sensitivity_not_effect_claim |
| threshold_top_20pct | 632 | 0.000 | threshold_sensitivity_not_effect_claim |
| threshold_top_30pct | 1,040 | 0.392 | threshold_sensitivity_not_effect_claim |

## Quadrant

- Valid rows: 4,383
- High-cost and high-demand rows: 185
- High-cost and high-demand hidden rows: 156

## S4 Admin Label QA

- CSV label ready: True
- Original GPKG label ready: False
- Fixed GPKG label ready: True
- Fixed GPKG: `qgis\scenario3_weather_response_top20_admin_fixed.gpkg`

## Files

- `outputs/reports/v2_2_execution/normalization_combination_threshold_robustness.csv`
- `outputs/reports/v2_2_execution/hidden_vulnerable_robust_core.csv`
- `qgis/hidden_vulnerable_robust_core.gpkg`
- `outputs/reports/v2_2_execution/quadrant_4x4_matrix.csv`
- `qgis/quadrant_primary_output.gpkg`
- `outputs/reports/v2_2_execution/data_loss_ledger_v2_2.csv`
- `outputs/reports/v2_2_execution/scenario_effect_registry_v2_2.csv`
- `outputs/reports/v2_2_execution/m0_m3_environment_burden_effect.csv`
- `qgis/m0_m3_environment_burden_shift.gpkg`
- `outputs/reports/v2_2_execution/s4_top20_admin_label_qa.json`
