# Scenario Counterfactual QGIS Checklist

## Layer Sources
- S1: `qgis/S1_delta_vulnerability_runner.gpkg` + `qgis/S1_candidates.gpkg`.
- S3: `qgis/S3_delta_vulnerability_runner.gpkg` + `qgis/S3_improved_edges_cap15.gpkg`.
- S4: `qgis/S4_weather_off_delta_vulnerability_runner.gpkg` + `qgis/scenario3_weather_response_top20_admin_fixed.gpkg`.

## Claim Labels
- `upper_bound`: show as scenario screening or component upper bound.
- `counterfactual_effect`: may report accessibility-burden effect under the exact manifest assumption.
- Never label these as ridership demand increase, passenger redistribution, or observed behavior.

## Renderer Checks
- Use the same CRS (`EPSG:5179`) and the same color scale for all delta maps.
- Map `delta_vulnerability` with sequential positive-improvement colors.
- Label only `resolved_hidden=True` or top-20 `delta_vulnerability` if the map is crowded.
- Put manifest path and `effect_output_label` in the layout note.

## Registry Snapshot
| scenario_id | effect_output_label | path_research_run | resolved_hidden_count | counterfactual_effect_claim_allowed |
|---|---|---:|---:|---|
| S1 | upper_bound | True | 49 | False |
| S3 | counterfactual_effect | True | 0 | True |
| S4 | upper_bound | True | 102 | False |