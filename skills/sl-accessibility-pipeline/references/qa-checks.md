# QA Checks

## Before Scoring

- Confirm all required columns exist.
- Count total, duplicate, null, invalid-geometry, and out-of-bound records.
- Verify CRS compatibility before spatial joins or distance calculations.
- Check whether service locations fall inside the expected study boundary.

## During Scoring

- Validate that every demand unit has a reachable-set calculation, even when the reachable set is empty.
- Inspect extreme scores for plausible causes.
- Confirm thresholds use the same units as impedance values.
- Check that aggregation does not duplicate supply or demand.

## After Scoring

- Compare row counts against the input demand table.
- Confirm score ranges, ranks, and categories are reproducible.
- Export QA notes with parameter values and exclusion counts.
- Treat unexplained score changes between runs as blockers.
