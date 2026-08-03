# Data Contracts

## Required Inputs

- Administrative or analysis zones must include a stable zone identifier, display name, valid geometry, and population or demand measure when scoring uses demand weighting.
- Candidate or service locations must include a stable location identifier, service category, status, and point geometry.
- Network, distance, or travel-time data must name origin identifiers, destination identifiers, impedance units, and the method used to produce them.

## Geometry Rules

- Use a projected CRS suitable for Seoul-area distance calculations before measuring length or area.
- Keep source CRS, working CRS, and export CRS explicit in notes.
- Treat empty, invalid, or self-intersecting geometries as QA failures until repaired or excluded with explanation.

## Join Rules

- Joins must preserve stable identifiers from both sides.
- Many-to-many joins require an explicit aggregation rule.
- Null identifiers, duplicated primary keys, and unmatched records must be counted and reported.
