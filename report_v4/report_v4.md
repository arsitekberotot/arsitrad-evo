# The Threshold — V4 Site-Aware Modular Evolutionary Programming

_Schema: v4-consolidated-report/1_

## 1. Canonical real-site model

- Geometry: `geojson` (site.geojson), area **5634.2 m²**, setbacks {'front': 4.0, 'side': 3.0, 'rear': 3.0, 'tpst_buffer': 10.0}
- Preferred expansion direction: S
- **Every attribute is evidence-tagged** (no fabrication):

| attribute | status |
|---|---|
| site | [SECONDARY] |
| orientation | [DESIGN HYPOTHESIS] |
| frontage.primary_street | [DESIGN HYPOTHESIS] |
| frontage.secondary_street | [TO VERIFY] |
| access.public_entry | [TO VERIFY] |
| access.service_entry | [TO VERIFY] |
| access.emergency_access | [TO VERIFY] |
| context.tpst_facing_edge | [TO VERIFY] |
| context.settlement_edge | [TO VERIFY] |
| context.preferred_expansion_direction | [DESIGN HYPOTHESIS] |
| existing_features.obstacles | [TO VERIFY] |
| existing_features.vegetation | [TO VERIFY] |
| existing_features.drainage | [TO VERIFY] |
| environmental_exposure.noise_source | [TO VERIFY] |
| environmental_exposure.odour_source | [TO VERIFY] |
| environmental_exposure.dust_source | [TO VERIFY] |
| environmental_exposure.prevailing_wind_direction | [TO VERIFY] |
| environmental_exposure.solar_notes | [DESIGN HYPOTHESIS] |
| setbacks.front_m | [DESIGN HYPOTHESIS] |
| setbacks.side_m | [DESIGN HYPOTHESIS] |
| setbacks.rear_m | [DESIGN HYPOTHESIS] |
| setbacks.tpst_buffer_m | [DESIGN HYPOTHESIS] |
| future_layers.planned_roads | [TO VERIFY] |
| future_layers.easements | [TO VERIFY] |
| future_layers.flood_overlay | [TO VERIFY] |

## 2. Module library catalogue

- 29 module codes across 11 functional families
- Axes: sizes ['S', 'M', 'L'], modularity ['developmental', 'variational', 'repeatable']
- Machine-readable schema `module-library-catalogue/v4` (see module_catalogue_v4.json/.csv/.png)

## 3. Two-tier capacity experiment

- Tier 1: reference (full program, nominal day capacity)
- Tier 2: controlled day-user demand scenarios (8..48)
- Day-user strata: [8, 16, 24, 32, 40, 48]; resident strata R4x[2, 3, 4, 5, 6, 7, 8]
- Day-user reachability: `{'8': 0.0, '16': 0.0, '24': 0.0, '32': 0.0, '40': 0.0, '48': 0.071}`

> Day-user strata [8, 16, 24, 32, 40] are NOT reachable while preserving essential functional coverage (arrival+care+commons+service) and the mandatory threshold (L0 x2) under the current module corpus. This marks the lower bound of the demand envelope.

## 4. Reachable-stratum selections (real polygon)

- Stratum: day_users = 48; objectives ['site_response', 'access_clarity', 'landscape_quality', 'stacking_efficiency', 'exposure_gradient', 'phaseability', 'service_efficiency', 'climate_daylight']
- Total feasible 2, residential candidates 0
- candidates = feasible AND residents >= MIN_RESIDENTS; degenerate zero-resident layouts are reported but never selected as representative.

| seed | feasible | candidates | pareto | selections |
|---|---|---|---|---|
| 42 | 1 | None | 1 | 10 |
| 7 | 1 | None | 1 | 10 |
| 123 | 0 | None | 0 | 0 |

## Key findings

1. Day-user strata [8, 16, 24, 32, 40] are NOT reachable while essential functional coverage (arrival+care+commons+service) and the mandatory threshold (L0 x2) are preserved. The reachable floor under the current PA5 module corpus is ~44 day users (A0-S 12 + B0-S 4 + C0-S 16 + L0x2 12).
2. Only day-user stratum ['48'] is reachable, and even there the feasible region is razor-thin (reachability [0.071]).
3. Across all seeds at the reachable stratum, NO feasible solution retained a residential core (residents >= 8): the only layouts meeting the day-user cap did so by deleting the domestic program — an unacceptable trade for a residential care facility. This is the capacity threshold at which the brief breaks.
4. Interpretive thresholds and strata are [DESIGN HYPOTHESIS]; module capacities are [PA5 CORPUS] where corpus-derived. These are experimental search strata, not recommended shelter capacities.
