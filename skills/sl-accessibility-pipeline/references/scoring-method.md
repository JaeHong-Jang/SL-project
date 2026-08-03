# Scoring Method

## Core Pattern

Define accessibility as the amount of reachable service supply available to a demand location under a stated impedance rule.

Common score:

```text
accessibility_i = sum(supply_j * weight_ij) for all j reachable from i
```

where `weight_ij` is based on distance, travel time, network cost, or a binary threshold.

## Weighting Options

- Binary threshold: `1` inside the service threshold, `0` outside.
- Distance decay: reduce contribution as impedance increases.
- Capacity weighting: multiply service availability by facility capacity or service intensity.
- Demand adjustment: divide reachable supply by nearby demand when the analysis asks about competition.

## Reporting

- Name the impedance measure and units.
- State thresholds, decay parameters, and normalization.
- Report whether higher scores mean better access.
- Preserve raw scores when producing ranks or categories.
