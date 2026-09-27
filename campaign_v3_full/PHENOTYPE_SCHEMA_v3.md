# Phenotype schema v3

This document describes the architectural interpretation of one **exact archived genotype**. The machine record is `phenotypes/*_prototype.json`; the source is `arsitrad_evo/phenotype_gen.py`. A parent genotype has a 16-character SHA-256-derived `genotype_id`, an `origin_seed`, a `birth_generation`, and a `selected_generation`. `architectural_variant_id` is populated only for a subsequent physical rotation study. A variant retains its parent `genotype_id` and lists the physical turns; its constraints, objective proxies, routes and sightlines are recalculated. It is never presented as a distinct optimizer result.

## Evidence key

| Tag | Use |
|---|---|
| `[PA5 CORPUS]` | The Threshold module functions, resident capacity, adjacency intent and allowed stacking as recorded in the project corpus. |
| `[DESIGN HYPOTHESIS]` | Schematic footprints, relative internal zone positions, path grid, grouping thresholds, enclosure rays, selection rules and visual language. These are design mechanisms to test. |
| `[TO VERIFY]` | Real parcel shape/north/frontage; doors, clearances, access and egress; eye-level and section views; screening details; material, structure, landscape performance and operator review. |

The module catalogue gives approximate rectangular `w × d` dimensions to represent corpus **net module areas**. The legacy numeric field `gfa` and archive column `gfa` are the sum of module areas across assigned floors. They are a **model floor-area proxy**, not a measured gross floor area. Ground `footprint` sums the rectangles; overlap is constrained. The 90 × 61.5 m placement frame approximates the 5,533.85 m² reference area; its 1.15 m² difference is a schematic rounding, not a surveyed site discrepancy.

## Module assembly

Each `ModuleNode` records its module code, instance ID, centroid, footprint, floor count and privacy. The kit translates functions into relative internal zones (`Part` records) with an evidence tag per zone. A domestic R4 contains shared domestic, personal, WASH, entry and retreat/porch territory; other modules use corresponding civic, care, commons, staff, service, learning, livelihood, reflection, community and transition grammars. These are **spatial zones**, not sized or code checked rooms. `faces`, `access_edges` and `access_points` distinguish public, private, retreat and service relationships. Internal paths connect the selected entry anchor to ground-floor zones as an access skeleton.

`grammar_rotation_degrees` rotates relative zones toward the selected access face within the archived footprint. `quarter_turn_feasible` reports whether swapping one instance's width and depth keeps the implemented hard constraints satisfied in isolation. `build_prototype(..., rotations={instance_id: 90})` creates a separate physical footprint variant, including 180°/270° options. The rotation study board demonstrates a model feasible, route connected R4 turn; it does not change the campaign or the three archived selections.

## Derived site relationships

| Field | Derivation and interpretation |
|---|---|
| `connections` | Corpus MUST/NEAR relationships and schematic SCREENED links, with user types. Every R4 instance must meet each relevant MUST partner within 25 m centroid distance. |
| `groupings` | Connected local MUST/NEAR pairs whose footprint edge gap is at most 6 m. A distant code-level link alone does not make a building group. |
| `shared_thresholds` | Nearby MUST/NEAR pairs within the same 6 m edge gap. These are opportunities for a shared controlled link, not constructed doorways. |
| `route_networks` | A* routes on a 1.5 m site grid around module footprints, separately for resident, care/staff, visitor/community, service and emergency users. Visitor routes add 3 m R4 clearance; service adds 2 m. Site entry is assumed from the nearest schematic site edge. |
| `spines` | Routed A0→C0 resident trunk and F0→M0 service trunk. Branch modules within 6 m of a trunk are recorded as aligned opportunities. |
| `threshold_paths` | Connected A0→C0→each R4 route sequence, with lengths and `CONNECTED`/`UNRESOLVED` status. |
| `privacy_gradient` | PUBLIC→CONTROLLED→SHARED→DOMESTIC→PERSONAL module ordering. It is an organizational gradient, not a measured privacy outcome. |
| `spatial_relationships` | Named civic edge, care hinge, shared commons, domestic cluster, service/environmental edge and landscape buffer/expansion relationships derived from the modules and adjacency. |
| `floor_plans` and `stacking` | Separate ground and upper-floor entries. Only C0 and H0 can stack under the current module rules; R4, F0 and M0 remain single-storey. Axon heights are diagrammatic. |

Routes are geometric sketches. The model does not yet prove that a door, internal junction, accessible path, emergency vehicle route or covered threshold can be built at the drawn line. The floor plans and exploded axon are development diagrams, not architectural documentation.

## Sensitive views and open space

`sightlines` includes every PROHIBITED module pair and each public-facing A0/K0 to R4 pair. Three samples on each facing edge are crossed into 9–36 test rays. A ray is screened only when another built footprint intersects it. One unobstructed ray makes the pair `exposed`; `visible_rays`, `tested_rays` and `exposure_ratio` remain available for review. `safeguarding_actions` proposes an opaque service edge or a controlled civic-to-domestic visual screen for exposed pairs, with `[DESIGN HYPOTHESIS]` and an explicit `[TO VERIFY]` eye-level/section study. Landscape planting alone is not counted as opaque screening. Zero sampled exposure means only that the sampled plan rays had built-mass occlusion.

`open_spaces` samples a 48 × 48 site grid. From each open cell, four cardinal rays look no farther than **12 m** for built mass. Three or four enclosing directions imply `COURTYARD`, two imply `POCKET COURT / THRESHOLD EDGE`, and zero or one imply `OPEN LANDSCAPE`. Four-connected cells of a common class form a zone; the stored representative point, minimum enclosure and area are diagrammatic. The sheets mark zones of at least 12 m². This method can distinguish local enclosure but cannot establish comfort, ecological performance, accessibility or actual landscape design.

## Reading status and objectives

`MODEL_FEASIBLE` means the implemented hard constraints evaluate within 1e-6 of zero, including footprint containment, all repeated MUST links, separation, area, population and stacking rules. The current accessibility/egress check is a placeholder returning zero, so model feasibility does not certify code compliance. `EXPOSED_TO_VERIFY` and `NO_EXPOSURE_IN_SAMPLED_RAYS` are separate view statuses; neither certifies operational safeguarding. F1–F9 are normalized minimization proxies and have uncalibrated reference ranges. A lower value on the radar corresponds to a better proxy value after display inversion (`1 − F`).

The three rendering levels use the same data: computational and candidate diagnostics; coordinated candidate sheets; and population, objective, Pareto, relative-difference and shortlist boards. Figures preserve seed, generation, genotype ID, program and constraint status so a visual can be traced to the archive. The +Y arrow is a **diagram orientation**. It must not be read as north until the real parcel is surveyed.
