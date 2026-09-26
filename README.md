# arsitrad-evo
**AI-native evolutionary spatial programming toolkit** — applied to *The Threshold Community*, a trauma-informed modular safe-house/care campus, on an experimental **5,533.85 m²** site.

Pure-Python reproduction of the modularity-based spatial-programming method of **Riskiyanto, Wibisono & Harani (2025)** — *architectural-scale adaptation* — driven by **constrained NSGA-II** (**Deb, Pratap, Agarwal & Meyarivan, 2002**), with **K-means** used only to cluster Pareto-optimal results into representative families.

> **No** Rhino / Grasshopper / Wallacei / jMetal / Helix at runtime — methodological references only.

## Method lineage
| Layer | Source | Role here |
|---|---|---|
| Evolutionary algorithm | Deb et al. 2002 — NSGA-II `[PAPER METHOD]` | constrained nondominated sort, crowding distance, elitist survival, SBX/polynomial variation |
| Spatial-programming framework | Riskiyanto et al. 2025 `[PAPER METHOD]` | developmental/variational modularity, population→zoning→phenotype→selection chain |
| Program & rules | PA5 Threshold corpus `[PA5 CORPUS]` | module library, adjacency, privacy gradient, hard constraints, density regimes |
| Clustering | K-means `[DESIGN HYPOTHESIS]` | post-processing only (never feeds selection) |

**Discipline:** Riskiyanto et al. validated their method on *office-interior furniture*. This is an **unvalidated architectural-scale adaptation**. Uncertain values are tagged `[DESIGN HYPOTHESIS]` / `[TO VERIFY]`. Optimization never overrides safeguarding, accessibility, or dignity (enforced as hard constraints).

## Install
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt          # flexible (>= ranges)
# or, for bit-for-bit reproducibility of the recorded campaign:
.venv/bin/pip install -r requirements-lock.txt     # exact pinned versions
```

## Quick start
```bash
# validate the pipeline (16 invariant tests)
.venv/bin/python -m pytest tests/ -q

# single run
.venv/bin/python run_experiment.py --pop 100 --gen 80 --seed 42 --out results

# full experimental campaign: multi-seed + sensitivity + report
.venv/bin/python run_campaign.py --out campaign
```

## Architecture
```
arsitrad_evo/
  config.py       site + reference constants, GA & cluster settings (DH/TV tagged)
  modules.py      Threshold module library + adjacency matrix + privacy levels
  genotype.py     genotype->phenotype codec (mixed real/int genes, placement tail)
  constraints.py  hard rules -> violation scores (constrained domination)
  objectives.py   F1..F9 as explicit measurable (minimised) functions
  nsga2.py        constrained NSGA-II (Deb 2002) — faithful implementation
  clustering.py   K-means post-processing (silhouette + elbow, medoids + extremes)
  analyze.py      normalization, extreme/medoid selection, traceability records
  visualize.py    site plans, zoning, stacking, circulation, radar, parallel coords...
run_experiment.py single-run CLI
run_campaign.py   multi-seed + sensitivity + full report campaign
make_report.py    generates REPORT.md from campaign outputs
tests/            pytest invariant tests (NSGA-II correctness, constraints, codec)
SPEC.md           design spec: every architectural rule -> DV / OBJ / HC
REPORT.md         generated research report (full traceable chain)
```

## Traceable chain
`MODULE LIBRARY → GENOTYPE → DECODING → HARD CONSTRAINTS → OBJECTIVES → NSGA-II EVOLUTION → PARETO FRONT → K-MEANS CLUSTERS → REPRESENTATIVE PHENOTYPES → ARCHITECTURAL INTERPRETATION`

Every shortlisted phenotype is traceable from its genes, modules, constraint
violations, objective vector, and open assumptions (see `REPORT.md` and the
per-phenotype `*.json` traceability records in the campaign output).

## Honest findings & limitations
- **Many-objective dilution.** With 9 objectives the population tends to become
  mutually non-dominated (all rank-1) mid-run, weakening Pareto pressure. Expected
  NSGA-II behavior. Remedies: aggregate objectives, NSGA-III, or ε-dominance.
- **Objective proxies are `[DESIGN HYPOTHESIS]`.** F1/F2/F4 use distance/area
  heuristics, not measured safeguarding outcomes. Reference ranges need calibration.
- **Accessibility/egress** is a placeholder constraint; real dims need regulatory
  review `[TO VERIFY]`.
- **K-means silhouette is modest** — the front is continuous, so families are
  indicative, not discrete architectural types.

---
*References: Deb, K., Pratap, A., Agarwal, S., & Meyarivan, T. (2002). A fast and elitist multiobjective genetic algorithm: NSGA-II. IEEE TEVC 6(2). · Riskiyanto, R., Wibisono, A. B., & Harani, A. R. (2025). Exploring spatial programming through modularity based evolutionary computation. J. Architecture & Urbanism 49(1).*
