# arsitrad-evo — DESIGN SPECIFICATION
## Python-native evolutionary spatial programming for The Threshold Community
### Site: 5,533.85 m² — program + zoning phase only (no final form)

> **Method basis.** Evolutionary algorithm: **NSGA-II** (Deb, Pratap, Agarwal & Meyarivan, 2002) `[PAPER METHOD]`.
> Spatial-programming framework: **modularity-based** (Riskiyanto, Wibisono & Harani, 2025) `[PAPER METHOD]` — an *architectural-scale adaptation*, NOT validated by that paper, which used office furniture modules.
> Post-processing: **K-means** clusters Pareto-optimal phenotypes into representative families `[DESIGN HYPOTHESIS]`.
> **No** Rhino / Grasshopper / Wallacei / jMetal / Helix at runtime — methodological references only.
>
> **Evidence status:** `[PAPER METHOD]` · `[PA5 CORPUS]` · `[DESIGN HYPOTHESIS]` (=DH) · `[TO VERIFY]` (=TV).

---

## 1. GENOTYPE → PHENOTYPE MODEL

### 1.1 Genotype (decision-variable vector)
Mixed **real/integer** encoding. One vector = one candidate Threshold configuration.

| # | Gene | Type | Range | Meaning | Source |
|---|------|------|-------|---------|--------|
| g0 | `n_R4` | int | 2–4 | residential cluster count (complete clusters, 4 residents each) | CORPUS/DH |
| g1 | `has_H0` | int {0,1} | 0–1 | Learning module present | DH |
| g2 | `has_J0` | int {0,1} | 0–1 | Livelihood module present | DH |
| g3 | `has_K0` | int {0,1} | 0–1 | Community module present | DH |
| g4 | `has_I0` | int {0,1} | 0–1 | Worship/reflection present | DH |
| g5 | `has_L0` | int {0,1} | 0–1 | Transition/reintegration present | DH |
| g6 | `public_intensity` | int | 0–3 | 0=hosted,1=H0,2=+K0,3=+J0 interface | DH |
| g7 | `floors_C0` | int | 1–2 | C0 stacking (never above F0/M0) | DH/TV |
| g8 | `floors_H0` | int | 1–2 | H0 stacking | DH/TV |
| g9 | `landscape_frac` | real | 0.30–0.55 | fraction of site as landscape | DH |
| g10 | `service_depth` | real | 8–20 m | service-edge depth | DH/TV |
| g11 | `buffer_depth` | real | 10–30 m | environmental-buffer depth (NOT universal setback) | TV |
| g12 | `reserve_area` | real | 90–270 m² | N0 future-expansion reserve | DH |
| g13.. | `pos_x[i]`, `pos_y[i]` | real | site bbox | module centroid placement (phase-1 rectangles) | DH |

**Placement genes (g13+):** one (x,y) centroid per *placed instance*. Instance count varies with `n_R4` and the `has_*` flags, so the placement block is a **variable-length tail** sized to the maximum instance count; unused slots are masked at decode time. Positions are decoded in a fixed module order and projected/clamped into the site envelope.

### 1.2 Phenotype (decoded spatial configuration)
From a genotype, the decoder produces:

- **Instances:** list of placed modules `{id, module_type, centroid(x,y), w×d rectangle, floors, area}`.
- **Derived metrics:** total footprint (union of ground-floor rects), GFA (Σ area×floors), resident capacity (=4·n_R4), day-user capacity, occupancy, open-space area, landscape area.
- **Adjacency graph:** nodes = instances; edge weights = centroid distance; labelled with required relationship (MUST/NEAR/SCREENED/AVOID/PROHIBITED).
- **Access network:** simplified circulation — resident spine, care response routes, service edge route, public edge.
- **Privacy assignment:** each instance tagged PUBLIC/CONTROLLED/SHARED/DOMESTIC/PERSONAL; gradient checked along access network.
- **Zoning:** band assignment along the gradient axis.

Phase-1 geometry is **axis-aligned rectangles + centroids** — enough to measure overlap, distance, footprint, adjacency and privacy relationships **without** resolving final form. `[DH]`

---

## 2. RULE → COMPUTATIONAL-ELEMENT MAP

Every architectural rule becomes exactly one of: **DV** (decision variable), **OBJ** (objective), **HC** (hard constraint). Uncertain items tagged DH/TV.

| Architectural rule | Element | Where |
|---|---|---|
| Site = 5,533.85 m², not all buildable | HC | C1 footprint+reserve ≤ buildable band |
| Developmental modules must exist (A0,B0,C0,E0,F0,M0,G0 core) | HC | C2 required-module presence |
| Module population ranges (n_R4 2–4; has_* 0–1) | DV + HC | g0–g5 bounds; C3 permitted populations |
| Safeguarding / controlled access | OBJ + HC | F1; C4 no uncontrolled public→R4 path |
| Protected residential access (care reaches R4) | OBJ + HC | F1; C5 B0/E0 within response distance of every R4 |
| No public-to-private shortcut | HC | C6 no graph path PUBLIC→PERSONAL without CONTROLLED gate |
| Independent service access | HC | C7 service edge reaches F0/M0 without crossing DOMESTIC/PERSONAL |
| Minimum privacy hierarchy | HC | C8 no PUBLIC↔PERSONAL or PUBLIC↔DOMESTIC adjacency |
| Allowable stacking (R4 single-storey; none above F0/M0) | HC | C9 stacking rules |
| Landscape/environmental allocation | DV + OBJ + HC | g9; F9; C10 landscape_frac within band |
| Accessibility / egress | HC placeholder | C11 placeholder (real dims TV) |
| Adjacency requirements (MUST/NEAR/...) | OBJ + HC | F4/F8 soft; C12 PROHIBITED pairs hard |
| Service separation | OBJ | F4 minimize F0/M0↔R4 conflict |
| Site efficiency | OBJ | F5 minimize footprint/GFA per program delivered |
| Adaptability / modularity | OBJ | F6 module repeatability + reserve |
| Domestic scale | OBJ | F7 minimize largest residential mass |
| Community connection (controlled) | OBJ | F8 bounded semi-public reachability |
| Everyday-life accessibility | OBJ | F3 amenity access per resident |
| Privacy / agency | OBJ | F2 protected territory + route choice |

---

## 3. HARD CONSTRAINTS (constrained-domination violation scores)
Each returns a **violation ≥ 0** (0 = satisfied). A solution is feasible iff **all** violations = 0.
Constrained dominance (Deb et al.): feasible always dominates infeasible; among infeasible, smaller total violation wins; among feasible, normal Pareto dominance.

| ID | Constraint | Violation measure | Src |
|----|-----------|-------------------|-----|
| C1 | Site limit | `max(0, footprint + reserve − B_max)` | DH |
| C2 | Required developmental modules present | count of missing required modules | CORPUS |
| C3 | Permitted populations | out-of-range gene magnitudes | CORPUS |
| C4 | Safeguarding / controlled access | # uncontrolled PUBLIC→R4 adjacency edges | CORPUS/DH |
| C5 | Care access to R4 | # R4 beyond max care-response distance | CORPUS/DH |
| C6 | No public→private shortcut | # paths PUBLIC→PERSONAL lacking CONTROLLED gate | CORPUS/DH |
| C7 | Independent service access | 1 if service route crosses DOMESTIC/PERSONAL else 0 | CORPUS/DH |
| C8 | Privacy hierarchy | # forbidden PUBLIC↔DOMESTIC/PERSONAL adjacencies | CORPUS/DH |
| C9 | Stacking rules | # illegal stack events (R4>1 floor; any module above F0/M0) | CORPUS/DH |
| C10 | Landscape band | distance of landscape_frac outside [0.30,0.55] | DH |
| C11 | Accessibility/egress (placeholder) | 0 — placeholder; real dims `[TO VERIFY]` | TV |
| C12 | PROHIBITED adjacency pairs | # PROHIBITED pairs closer than min separation | CORPUS/DH |

**Overlap** between module rectangles is also a hard feasibility issue: `C0_overlap = total pairwise overlap area` (rectangles must not intersect beyond tolerance).

---

## 4. OBJECTIVES (explicit, measurable) — all **minimized** internally
NSGA-II here minimizes; "maximize X" objectives are encoded as `minimize (1 − normalized_X)`. Each is normalized to [0,1] using corpus-derived reference ranges `[DH]`. Equations, inputs, assumptions, edge cases documented in `objectives.py` docstrings.

| ID | Name | Internal form (minimize) | Direction (user-facing) |
|----|------|--------------------------|--------------------------|
| F1 | Safeguarding | `1 − gate_control_score` | maximize controlled access & response |
| F2 | Privacy / agency | `1 − (protected_territory + route_choice)/2` | maximize |
| F3 | Everyday life | `1 − amenity_access_per_resident` | maximize |
| F4 | Service separation | `service_resident_conflict` | minimize |
| F5 | Site efficiency | `footprint / site_area` (per program) | minimize |
| F6 | Adaptability | `1 − modularity_score` | maximize |
| F7 | Domestic scale | `largest_residential_mass / ref_mass` | minimize |
| F8 | Community connection | `1 − bounded_public_reachability` | maximize (controlled) |
| F9 | Landscape / buffer | `1 − landscape_quality` | maximize |

**Reference ranges / normalizers** are in `config.py` and marked DH/TV. F1 & F2 are never allowed to be traded below feasibility by C4–C8; the objectives only rank *among feasible* solutions.

---

## 5. NSGA-II IMPLEMENTATION (faithful to Deb et al. 2002)
Components in `nsga2.py`, each a tested function:

1. **Random initial population** (size N) within gene bounds.
2. **Fast nondominated sort** — O(MN²), assigns `rank`.
3. **Crowding distance** — per-front, per-objective, boundary = ∞.
4. **Crowded comparison operator** `≺n`: lower rank wins; tie → larger crowding distance.
5. **Binary tournament selection** using `≺n`.
6. **Crossover** — SBX for real genes, uniform for int genes.
7. **Mutation** — polynomial for real genes, random-reset for int genes.
8. **Offspring generation** → size N.
9. **Elitist survival** — combine parent+offspring (2N), sort, fill by front then crowding distance → N.
10. **Repeat** for G generations.
11. **Constrained domination** replaces plain domination everywhere (§3).

Mixed real/integer handled by per-gene-type variation operators.

---

## 6. K-MEANS POST-PROCESSING
After evolution, take the final **feasible rank-1 (Pareto) front**, embed each phenotype in its **objective vector** (optionally + key genes), run **K-means** (k chosen by silhouette over a small k range `[DH]`), and report **cluster medoids** as representative solution families (e.g. domestic-priority / balanced / community-interface). K-means is *post-processing only* — it never feeds selection.

---

## 7. REPRODUCIBILITY
- Seedable RNG (`config.seed`) threaded through all stochastic steps.
- `run_experiment.py` → writes `results/` (Pareto front CSV, per-generation metrics, cluster assignments, plots).
- Plots: Pareto front projections, objective-space clusters, example phenotype layout.
- `requirements.txt` + `.venv`. No GUI toolchains.

## 8. OPEN GATES `[TO VERIFY]`
- Real accessibility/egress dimensions (C11 placeholder).
- Care-response distance threshold value.
- Buffer/setback depths (not universal).
- Normalization reference ranges (currently DH proxies).
- Care/operator staffing assumptions behind capacity genes.
