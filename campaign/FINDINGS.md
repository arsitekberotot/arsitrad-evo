# arsitrad-evo — FINDINGS (research interpretation)
*Post-processing & architectural-evidence layer for campaign @ commit `22f486f`.
`campaign/REPORT.md` is preserved as the raw computational record; this document
interprets it. Nothing in the optimizer, objectives, constraints, genotype, or
campaign parameters was modified.*

## 0. Audit — do the outputs support the report's claims?
| Claim in REPORT.md | Verified against data | Result |
|---|---|---|
| 445-solution nondominated archive | `pareto_archive.csv` = 445 rows | ✅ |
| All 5 seeds → 100% feasible | `multiseed_summary.csv` feasible_rate = 1.0 × 5 | ✅ |
| All 5 seeds → 100% rank-1 | pareto_size == pop (100) × 5 | ✅ |
| 14 representatives | 14 `phenotype_*.json` traces | ✅ |
| K-means k=6, silhouette ≈ 0.232, elbow ≈ 4 | `campaign_summary.json` | ✅ |

**Audit caveats discovered:**
1. `pareto_archive.csv` carries **no seed/provenance column** and all rows are
   rank-0 — per-seed attribution of individual archive solutions is not
   recoverable from the CSV. Cross-seed recurrence is therefore assessed via
   *structural-signature recurrence*, not per-seed front tracking. *(Data
   limitation, not an optimizer defect.)*
2. Only the 13 structural genes are archived; the placement (x,y) tail is not in
   the CSV. Placement evidence lives in the per-phenotype JSON `modules` list.

## 1. The headline result is a dilution result, not a quality result
All 445 archive solutions are mutually nondominated **by construction of the
9-objective Pareto criterion**, not because they are all good. Measured directly:

> **100.0% of sampled archive pairs (7,140 pairs over a 150-solution sample) are
> mutually non-dominating.**

Under 9 objectives, almost no solution dominates any other, so rank-1 membership
is **vacuous as evidence of quality**. The 100%-feasible / 100%-rank-1 outcome
is the *expected symptom of many-objective dilution*, confirmed empirically here
rather than inferred from population counts. **Pareto membership must not be
read as "this is a good building."**

## 2. What the objectives actually measure — genuine signal vs proxy artifact
Spearman correlation across the 445 solutions (`analysis_objective_correlation.csv`,
`figures/analysis_objective_correlation.png`):

**Strong relationships (|r| ≥ 0.4):**
- **F5 ↔ F8 = −0.53 (CONFLICT).** Site efficiency trades against community
  connection — the most substantive *genuine* trade-off in the study.
- **F2 ↔ F9 = +0.50 (REDUNDANT).** Privacy/agency and landscape/buffer move
  together; they are not independent criteria here.
- **F4 ↔ F6 = −0.45 (CONFLICT).** Service separation vs adaptability.

**Proxy-artifact findings (objectives that collapse onto a decision variable):**
- **F9 (landscape/buffer) ≈ landscape_frac in disguise** — Spearman r = **−0.92**.
  F9 adds almost no information beyond the landscape gene it is computed from.
- **F8 (community connection) is largely a count of public modules** — Spearman
  r = **−0.73** vs (H0+J0+K0). It measures *whether public modules exist*, not the
  spatial *quality* of the public–private threshold.
- **F7 (domestic scale) is largely a function of n_R4** (mean 0.35 / 0.23 / 0.14
  for 2/3/4 clusters).
- **F2 and F4 are near-binary** (frac_extreme 0.85 and 0.60 respectively) — they
  behave as on/off switches rather than continuous gradients.

**Consequence:** of the 9 objectives, F1, F3, F5, F6 carry most of the genuine
continuous signal; F8, F9, F7 are substantially proxy-driven; F2, F4 are
threshold-like. Trade-off conclusions below are weighted accordingly.

## 3. Module & program statistics (the real structure of the trade-space)
- **Residential clusters skew low:** n_R4 = 2 in 58% (256/445), 3 in 22%, 4 in 20%.
- **Optional module frequency** (`figures/analysis_module_frequency.png`):
  H0 54% · J0 32% · I0 30% · L0 25% · **K0 (community) only 5.4%**.
- **Public interface intensity skews low:** 0 public modules in 33%, 1 in 45%,
  2 in 18%, 3 in 3%. The optimizer strongly favours a **closed / low-interface**
  scheme — consistent with safeguarding being a hard constraint.
- **Landscape fraction** mean 0.43, range [0.30, 0.55].
- **Stacking** is split roughly evenly (C0 2-floor 58%, H0 2-floor 48%) — no
  strong stacking preference emerged.

**Module → objective effects** (`figures/analysis_module_objective.png`): the
dominant effect of *any* public module is to lower F8 (K0: −0.53, J0: −0.31,
H0: −0.22) while slightly *worsening* F5 site efficiency (+0.04 to +0.06) and F6
adaptability (+0.05 to +0.14). This is the measurable cost of opening the
threshold — the computational shadow of the corpus's central tension.

## 4. Duplicates & convergence
- 17 exact full-genotype duplicates in the archive.
- Only **149 unique structural signatures** among 445 solutions; the two most
  common programs recur 22 and 20 times. The "445-solution archive" is really
  **~149 distinct programs** with placement variation — evidence of convergence
  onto a small set of recurrent programmatic strategies.

## 5. K-means families — reproducible but NOT well-separated
- Partition is **technically stable**: k=6 ARI = **0.943** (range 0.909–0.990)
  across 5 seeds. The same clustering recovers reliably.
- **But silhouette is weak and flat**: 0.22 / 0.21 / 0.19 / 0.19 / 0.18 / 0.19
  for k = 3…8 (`figures/analysis_kmeans_stability.png`). There is no k at which
  well-separated clusters appear.

> **Verdict: the families are reproducible partitions of a CONTINUOUS trade-space,
> not six discrete architectural types.** k=6 is a convenient discretisation, not
> a discovered taxonomy. Per the brief, k=6 is treated as **provisional** evidence.

## 6. Reassessment of the 14 representatives
The 14 medoid+extreme representatives are **not all meaningfully distinct**:
nearest-neighbour objective distances between several pairs are small (e.g.
rep04–rep08 d=0.57, rep10–rep11 d=0.56, rep05–rep12 d=0.61), and several share
near-identical programs (reps 6,7,9 are all `R4x4/closed`; reps 3,13 similar).
Auto-accepting all 14 would overstate the diversity of the result.

Reduced to **3 meaningfully distinct candidates** (§7) on two criteria:
(a) pairwise **normalised objective distance > 1.1**, and (b) **distinct program
signature**. Distances: BALANCED–SPECIALIZED 1.25, BALANCED–CONTRASTING 1.14,
SPECIALIZED–CONTRASTING 1.77 — genuinely separated in the trade-space.

## 7. Where evidence is INSUFFICIENT
- **No basis to name discrete architectural typologies** beyond the three
  candidates: the flat silhouette and continuous trade-space mean any richer
  "family" naming would be invented. → **EVIDENCE INSUFFICIENT** for a typology.
- **No basis to claim F8/F9 measure real threshold quality or ecological
  performance** — they are proxy-bound to module count / landscape area.
  → architectural interpretation of F8/F9 is **DESIGN HYPOTHESIS**.
- **No per-seed provenance** for archive solutions → cross-seed front-stability
  claims are limited to signature recurrence. → **EVIDENCE INSUFFICIENT** for
  per-seed convergence-rate comparison.

---
*All numbers reproducible via `campaign_analysis.py` → `campaign/data/analysis_findings.json`.*
