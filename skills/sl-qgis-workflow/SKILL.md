---
name: sl-qgis-workflow
description: Guide QGIS workflows for the Seoul slope-weather-transit walking accessibility project. Use when setting up EPSG:5179 layers, analysis masks, 250m 생활인구 joins, slope outlier QC, accessibility map styling, validation overlays, exports, or reproducible QGIS project steps.
---

# SL QGIS Workflow

Use this skill to keep project layers, processing steps, and map exports consistent.

## Workflow

1. Name, group, and style layers using `references/qgis-layer-conventions.md`.
2. Choose processing steps from `references/qgis-processing-recipes.md` and record parameters before running tools.
3. Review layouts with `references/map-export-checklist.md` before export.
4. Preserve intermediate outputs when they support auditability; remove only clearly temporary scratch layers.

## Output Expectations

- Identify the QGIS tool, input layer, output layer, CRS, and key parameters.
- Prefer reproducible processing steps over manual edits.
- Note when a step depends on plugin availability.
- Keep map exports legible in both Korean and English where project materials are bilingual.
