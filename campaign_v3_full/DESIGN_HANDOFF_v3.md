# The Threshold — architectural handoff v3

**Three exact archived starting points for plan, section, massing and landscape design.** This handoff supersedes the v2 shortlist. The drawings are schematic architectural propositions, with real parcel geometry, access, dimensions, code review and safeguarding still to resolve. Open the coordinated [`final_shortlist.png`](publication/boards/final_shortlist.png), then each phenotype sheet and its diagnostic JSON.

## Selection basis

The v2 protocol was rerun after making MUST adjacency hard for **each** R4 instance, keeping every full footprint inside the schematic site, and preserving full genotype seed/generation identity. Eleven v3 searches (five free, three R4×3, three R4×4) produced 756 archive rows and **750 distinct** exactly replayed model feasible genotypes: 381 at R4×2, 173 at R4×3, and 196 at R4×4. The six duplicate vectors have the same genotype fingerprint and are counted once for selection. All 750 unique records have zero implemented hard violation, zero MUST shortfall and no module overhang. The frozen computational hash is in `data/freeze_manifest_v3.json`.

For architectural selection, each normalized proxy F1–F9 must be at most **0.75** `[DESIGN HYPOTHESIS]`. Within each resident capacity, retain the fewest exposed sensitive pairs in sampled plan rays; among ties, retain the fewest visible rays. Only then select BALANCED by lowest worst objective, SPECIALIZED by lowest F3, and CONTRASTING by greatest minimum objective-space distance from the first two. This screen is editorial; it is not a new safeguarding standard. Objective-extreme and relative-difference boards retain the broader valid archive for comparison. K-means silhouette is **0.198**, so the k=6 result is a diagnostic, not an architectural typology.

| | BALANCED | SPECIALIZED | CONTRASTING |
|---|---:|---:|---:|
| Genotype ID | `d025145502ad4434` | `2bae568f51f78efc` | `76761399c98699cd` |
| Seed · born Gen · selected Gen | 2024 · 75 · 80 | 123 · 78 · 80 | 123 · 78 · 80 |
| Resident / day-user proxy | 8 / 24 | 12 / 16 | 16 / 24 |
| Model floor-area proxy | 1,071 m² | 1,201 m² | 1,541 m² |
| Ground footprint | 1,070 m² | 1,050 m² | 1,282 m² |
| Target landscape | 47.4% | 45.8% | 44.1% |
| Expansion reserve | 263 m² | 215 m² | 131 m² |
| MUST shortfall / route gaps | 0 m / 0 | 0 m / 0 | 0 m / 0 |
| Sensitive pairs with sampled exposure | **0 / 6** | **5 / 9** | **4 / 12** |
| Floor stacking | single-storey | C0 upper floor | C0 and H0 upper floors |

The `gfa` field in historical data is a sum of corpus **net module areas** over floors. It is labelled a model floor-area proxy in v3 boards; it cannot be used as a gross floor area, construction cost or code area without conversion.

## BALANCED — screened low-capacity campus

[`Phenotype sheet`](publication/phenotype_sheets/balanced_d025145502ad4434.png) · [`diagnostic JSON`](phenotypes/balanced_d025145502ad4434_prototype.json)

**Program.** Two R4 domestic clusters, civic A0, care B0/E0, everyday C0, service F0/M0, plus learning H0 and livelihood J0. All modules are single-storey. The spatial model finds a B0/C0/E0/R4 local cluster, a paired H0/J0 threshold, and several separate campus pieces. The resident A0→C0 trunk is 41 m; the two R4 threshold routes are approximately 48 m and 66 m. The farther R4 needs particular attention in the next plan.

**Measured proxy trade-off.** Strong service separation (F4 0.006) and no exposure in the sampled plan rays support this as the safer visual starting point. Domestic-scale F7 (0.439) and landscape-buffer F9 (0.382) are its weaker proxies. Four courtyards and fourteen pocket edges of at least 12 m² are detected by the local enclosure rule; these are spatial cues, not designed outdoor rooms.

**Develop next.** Draw a real entry and care control line from the surveyed street edge; test a shorter and weather-protected route to the remote R4; develop the two domestic clusters with personal retreat, WASH and supervised shared rooms; resolve outdoor rooms versus genuine open landscape. A physical 90° R4 rotation is shown in [`physical_rotation_study.png`](publication/boards/physical_rotation_study.png) as a distinct, model feasible architectural variant. Its parent genotype stays unchanged. Confirm the apparently screened views at eye level and in section, including glazing and landscape transparency `[TO VERIFY]`.

## SPECIALIZED — compact everyday-life core

[`Phenotype sheet`](publication/phenotype_sheets/specialized_2bae568f51f78efc.png) · [`diagnostic JSON`](phenotypes/specialized_2bae568f51f78efc_prototype.json)

**Program.** Three R4 clusters plus A0/B0/C0/E0/F0/M0 and livelihood J0. The C0 commons has an upper floor; its vertical core is diagrammatic. The local A0/B0/C0/R4 group brings care and domestic functions together, while service is paired elsewhere. Three connected threshold routes are approximately 80 m, 82 m and 56 m, revealing a long-walk issue despite F3 everyday-life proxy **0.174**.

**Safeguarding task.** Five of nine sensitive pairs expose sampled views: A0→R4.3, F0→R4.1/R4.2 and M0→R4.1/R4.2. The first is a civic-to-domestic threshold problem; the latter four need an opaque service-yard edge and deliberate opening orientation. The schematic 18 m prohibited-pair and 20 m public/private centroid separation rules alone cannot screen a view. The next plan and section must test barrier height, controlled gates, windows, servicing operations and resident visibility `[TO VERIFY]`. This unresolved issue remains drawn and counted on the sheet.

**Develop next.** Consolidate the three R4 approaches into a legible resident spine, shorten the two long branches without losing care access, place a real C0 stair/lift and accessible ground-floor functions, and turn the six detected courtyards and sixteen pocket edges into a smaller set of usable, supervised outdoor rooms. Community connection F8 **0.667** is a weak proxy because this program has J0 but no H0/K0; review it against operator policy before choosing the 12 resident capacity.

## CONTRASTING — higher-capacity layered campus

[`Phenotype sheet`](publication/phenotype_sheets/contrasting_76761399c98699cd.png) · [`diagnostic JSON`](phenotypes/contrasting_76761399c98699cd_prototype.json)

**Program.** Four R4 clusters plus the six core modules, learning H0, livelihood J0 and reflection I0. C0 and H0 stack, so this is a useful section and massing study. The model finds three local building groups and a resident A0→C0 trunk of about 42 m. All four domestic threshold routes are connected, at approximately 61 m, 59 m, 45 m and 61 m.

**Measured proxy trade-off.** F1 safeguarding proxy is 0.172, but domestic-scale F7 **0.576** and site-efficiency F5 **0.433** are weaker. The scheme supports 16 residents with a 1,282 m² footprint and 44.1% target landscape. Seven diagrammed courtyards and sixteen pocket edges reflect local enclosure; their viability depends on scale, daylight, access and management.

**Safeguarding task.** Four of twelve sensitive pairs show sampled exposure: A0→R4.1/R4.4 and F0→R4.3/R4.4. The first asks for a designed civic/private visual threshold, the second for an opaque service edge, altered openings and possibly a changed service-yard alignment. The 49 visible sampled rays within those four pairs are a research diagnostic, not a performance standard. Resolve these relationships before developing a detailed plan `[TO VERIFY]`.

**Develop next.** Make a measured section through C0/H0 and two R4 clusters; prove the upper-floor use, vertical access and egress; test whether four domestic clusters can retain a noninstitutional scale; and allocate the 131 m² expansion reserve explicitly. Use the open-space hierarchy to choose a primary court and real landscape buffer rather than preserving every tiny algorithmic pocket.

## Decision and verification sequence

1. **Site + operation:** survey the parcel, north, street frontage and levels; confirm 8/12/16 resident and day-user demand with the operator `[TO VERIFY]`.
2. **Safeguarding:** map actual glazing, fence/wall height, visual permeability, staffed gates and resident movement in plan **and section**. Resolve every exposed pair for SPECIALIZED and CONTRASTING and confirm BALANCED's zero sampled views with an eye-level study `[TO VERIFY]`.
3. **Plan + section:** convert relative kit zones into dimensioned rooms and WASH, accessible routes, real doors, cores and emergency operations. The current egress/accessibility constraint is a placeholder `[TO VERIFY]`.
4. **Massing + landscape:** convert the floor-area proxy to a real gross area, design weather cover and outdoor thresholds, and check courtyard daylight, drainage, ecology and maintenance `[DESIGN HYPOTHESIS → TO VERIFY]`.
5. **Choose a proposition:** compare the three capacities against care staffing and reintegration policy. Preserve all three as design starting points until these decisions are made; proxy rankings alone cannot choose the architecture.

The [Riskiyanto et al. paper](https://mla.vilniustech.lt/index.php/JAU/article/view/22138) informs the population-to-phenotype-to-selection analytical chain. The program, safeguarding issues and architectural judgments above are specific to The Threshold and are not claims from that source.
