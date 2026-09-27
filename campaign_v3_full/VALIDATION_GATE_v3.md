# Formal validation gate v3

**Gate scope:** computational campaign semantics, exact archive identity, spatial phenotype derivation, and publication reproducibility. This is a gate for **architectural exploration**, not building approval. The authoritative machine records are `data/validation_gate_v3.json`, `data/freeze_manifest_v3.json` and `data/verification_v3.json`. The final verifier passed on **2026-09-27 08:43 UTC**: 756 archive rows replayed, 750 distinct genotypes checked, 36 selected diagnostic PNGs, 3 phenotype sheets, 11 comparative boards and **52 passing tests**.

## Before → after evidence

| Check | Historical v2 evidence | Repaired v3 evidence |
|---|---|---|
| MUST adjacency selection | `soft_cv` was not part of hard constrained domination; only **71 / 429** archived v2 rows had zero recorded MUST shortfall. Each R4 instance could also be hidden by a code-level minimum. | MUST is hard; every repeated R4 is checked against its required partners. **756 / 756** capacity-stratified archive rows, **750 / 750** distinct replayed vectors, have zero MUST shortfall. |
| Site containment | Frozen v2 BALANCED/SPECIALIZED/CONTRASTING contained **3 / 4 / 1** modules overhanging the 90 × 61.5 m schematic envelope. | Decoder bounds centers by each active footprint, and `site_boundary` is hard. **750 / 750** distinct v3 vectors pass replayed containment. |
| Saved vs rendered identity | v2 BALANCED saved **1,485 m²** but its rendered manifest reported **1,377 m²**. The historical renderer located a candidate with a coarse signature rather than replaying its full genotype. | `pareto_genotypes.jsonl` stores full vectors, seed, born/selected generation and fingerprint. Each selected vector is replayed with the same objective, area and constraint status before rendering. The three selected sheets carry their exact IDs. |
| Capacity exploration | An initial repaired, free-only v3 rerun produced **383** archived solutions, all R4×2. | The frozen rerun adds fixed R4×3 and R4×4 research strata: **381 / 173 / 196** distinct replayed solutions at R4×2/3/4. The stratum is recorded; its role is diversity of architectural options, not a claim that free NSGA-II found the same balance. |
| Circulation and views | A public-to-R4 relation could be misread as public circulation; one central view segment could hide oblique exposure. | R4-touching links are resident/care and, when required, controlled. Five user networks route around footprints. Sensitive pairs test facing-edge sample rays; any clear ray is reported as exposure. |
| Open space and clustering | An unlimited-gap detector could mark distant gaps as courtyards. Code-level connectivity could imply a physical group across a wide site. | Local **12 m** enclosure rays classify courtyard / pocket edge / open landscape. Building groups and shared-threshold candidates require a local **6 m** edge gap on a MUST/NEAR pair. K-means silhouette **0.198** does not support discrete architectural types. |

The v2 baseline values come from the preserved `campaign_v2/data/shortlist_v2.json`, its renderer manifest, and `campaign_v2/data/pareto_archive.csv`. The old records are not silently edited. The repaired v2 protocol is rerun into `campaign_v3_full/` so the before/after evidence remains inspectable.

## Automated gate

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe validate_v3.py --campaign campaign_v3_full
```

The gate recomputes the computational freeze SHA-256, replays **every** full archive vector, compares CSV objective values and IDs, checks every hard/MUST/site result, verifies the unique capacity distribution and the shortlist's exposure screen, and rebuilds each selected prototype. It compares saved prototype JSON with the recomputed record, checks all selected route and threshold statuses, confirms that every exposed pair has a design action, verifies the three phenotype sheets and all eleven comparative boards as readable PNGs, and runs the complete regression suite. The verifier writes exact renderer-source and publication-image hashes to `data/verification_v3.json` when all checks pass.

The unit and regression suite covers full-footprint boundary behavior, repeated R4 MUST behavior, constrained tournament selection, seed/generation replay, capacity strata, public-to-R4 circulation, oblique sightlines, open-space enclosure, internal evidence tags, physical 90° rotation, local clustering and routed spines, and the historical manifest label mapping. The campaign-freeze hash includes the computational source, locked dependencies and campaign data. The publication verifier separately hashes phenotype and board renderer sources so a later graphic edit remains detectable in the final evidence record.

## Architectural acceptance condition

| Selected parent | Implemented constraints | Route network | Sampled sensitive views | Architectural reading |
|---|---|---|---|---|
| BALANCED `d025145502ad4434` | zero hard/MUST/site violation | connected | **0 / 6 exposed** | Can advance to measured plan and section, with eye-level view confirmation. |
| SPECIALIZED `2bae568f51f78efc` | zero hard/MUST/site violation | connected | **5 / 9 exposed** | Carries explicit visual-screening tasks for A0/F0/M0 to R4. |
| CONTRASTING `76761399c98699cd` | zero hard/MUST/site violation | connected | **4 / 12 exposed** | Carries explicit visual-screening tasks for A0/F0 to R4. |

`MODEL_FEASIBLE` is deliberately narrower than architectural or regulatory compliance. The accessibility/egress check is a placeholder that returns zero. The 1.5 m route grid, module dimensions, 12 m enclosure radius, screening moves and 0.75 shortlist objective cap are `[DESIGN HYPOTHESIS]`. The parcel, actual north, access, usable gross area, door and path dimensions, fire/egress/accessibility, eye-level sightlines, staffing and resident experience are `[TO VERIFY]`. No shortlisted scheme is presented as a finished or code-compliant building.

## Publication audit

The package presents a traceable progression: **generation → genotype → program assembly → routed spatial organization → architectural phenotype → F1–F9 trade-off → selection**. Six generation boards use the same 90 × 61.5 m frame; a Pareto field, nine objective extremes, relative-difference board, physical-rotation study and final shortlist board support comparisons. Three phenotype sheets integrate plan, exploded floor assembly, program/capacity, constraint and view status, domestic kit, upper-floor condition, open-zone counts, site budget and performance profile. Program colors, privacy outline, route colors, +Y diagram orientation and a 20 m model scale are explicit. Visual inspection of the rendered PNGs is a separate review of legibility; the automated verifier checks their existence, identity and resolution.
