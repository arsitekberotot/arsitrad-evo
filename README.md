# arsitrad-evo

Evolutionary spatial programming for **The Threshold Community**, an exploratory safe-house and care campus on a **5,533.85 m²** reference site. The code adapts the modular spatial-programming inquiry of [Riskiyanto, Wibisono and Harani (2025)](https://mla.vilniustech.lt/index.php/JAU/article/view/22138) and uses constrained NSGA-II as described by Deb et al. (2002). It is an architectural research model, not a reproduction of the paper's office-interior experiment.

The current deliverable is the **v3 validated campaign and architectural publication package**. Earlier `campaign/` and `campaign_v2/` outputs remain as historical evidence; their shortlists are superseded.

## Reproduce v3

PowerShell commands from the repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe run_campaign.py --out campaign_v3_full --capacity-strata
.\.venv\Scripts\python.exe select_v3.py --campaign campaign_v3_full
.\.venv\Scripts\python.exe run_phenotype_gen.py --campaign campaign_v3_full
.\.venv\Scripts\python.exe run_publication_v3.py --campaign campaign_v3_full
.\.venv\Scripts\python.exe validate_v3.py --campaign campaign_v3_full
```

On macOS or Linux, substitute `.venv/bin/python` for the Python command. Set `MPLCONFIGDIR` to a writable directory if Matplotlib's user cache is restricted. The full campaign runs five free seeds and three seeds each at fixed R4×3 and R4×4 capacity, then its sensitivity sweeps; it takes much longer than the subsequent replay and rendering steps. The publication command independently reruns seed-42 snapshot tracks at Gen 0/10/20/40/60/80.

`select_v3.py` first replays every archived full genotype vector, checks hard constraints and objectives, and records SHA-256 hashes of the computational source and campaign inputs. Publication refuses a changed computational freeze. The 0.75 maximum single-objective shortlist screen and the sampled sightline screen are explicit **editorial design hypotheses**, not new optimization constraints or regulatory tests.

## Read the outputs

| Level | Main output | Purpose |
|---|---|---|
| Computational | `campaign_v3_full/data/pareto_genotypes.jsonl`, `pareto_archive.csv`, `freeze_manifest_v3.json`, `validation_gate_v3.json` | Exact seed/generation/vector replay and formal checks |
| Diagnostic | `campaign_v3_full/figures/` and `campaign_v3_full/phenotypes/` | Evolution and per-candidate plan, floor, route, sightline, privacy, open-space, stacking, objective figures plus JSON |
| Architectural sheets | `campaign_v3_full/publication/phenotype_sheets/` | Three coordinated one-page candidate studies |
| Comparative boards | `campaign_v3_full/publication/boards/` | Six generation boards, objective extremes, Pareto field, relative difference, rotation study, final shortlist |

Open [`campaign_v3_full/DESIGN_HANDOFF_v3.md`](campaign_v3_full/DESIGN_HANDOFF_v3.md) for the architectural decision package, [`campaign_v3_full/VALIDATION_GATE_v3.md`](campaign_v3_full/VALIDATION_GATE_v3.md) for before/after evidence, and [`campaign_v3_full/PHENOTYPE_SCHEMA_v3.md`](campaign_v3_full/PHENOTYPE_SCHEMA_v3.md) for the geometry and evidence tags. The machine-readable publication index is `campaign_v3_full/publication/manifest.json`.

## How the model works

`module library → mixed integer/real genotype → placed modules → hard constraint checks → F1–F9 proxies → NSGA-II generations → Pareto archive → exact genotype replay → architectural kit and route derivation → phenotype sheets → selection boards`

The phenotype layer expands each module into relative internal zones, user-specific access faces, internal path skeletons, and floor assignments. It derives resident, care/staff, visitor/community, service and emergency routes with a schematic site grid; it also records threshold paths, local building groups, shared-threshold opportunities, circulation spines, sampled sensitive views and open-space enclosure. Physical 90° module turns are available as **post-optimization architectural variants**, with distinct variant IDs and recomputed constraints, objectives, routes and sightlines. The archived genotype remains the parent record.

Every architectural claim is tagged `[PA5 CORPUS]`, `[DESIGN HYPOTHESIS]`, or `[TO VERIFY]`. The 90 × 61.5 m placement rectangle is an approximation of the reference area. Its +Y arrow is diagram orientation; real north and street access need survey confirmation.

## Limits that matter for design

- `MODEL_FEASIBLE` means the implemented schematic hard constraints have zero violation. Accessibility and egress currently have a placeholder check; the label does **not** establish code compliance or operational safeguarding.
- Sensitive views are sampled between facing footprint edges and tested for built-mass occlusion. Unobstructed pairs are flagged for screening; a zero result does not replace eye-level, sectional or opening studies.
- Routed lines follow a 1.5 m site grid around simplified footprints. Door locations, levels, turning radii, widths, weather cover and emergency operations remain to verify.
- Courtyards, pocket edges and open landscape are classified by four local 12 m enclosure rays. These are spatial hypotheses, not surveyed landscape quantities.
- The nine objectives are normalized proxies. K-means silhouette in the v3 archive is about 0.198, so cluster labels are kept diagnostic and are not presented as architectural typologies.

The three shortlisted schemes are starting points for real plan, section, massing and landscape work. The validation and handoff documents state their unresolved design questions by candidate.
