# arsitrad-evo — FINDINGS v2 (research interpretation, Campaign v2)
*Post-processing & architectural-evidence layer for **Campaign v2** @ commit
`615009f` + remediation. `campaign/REPORT.md` (v1) is preserved; v2 outputs live
in `campaign_v2/`. Campaign v2 remediated verified computational defects WITHOUT
redesigning the optimizer (see §1). Nothing here is an architectural claim until
marked so.*

## 1. Campaign v2 remediation — what was fixed and why
| # | Verified defect (v1) | Fix | Effect |
|---|---|---|---|
| 1 | **must_adjacency was inert**: marked soft, folded into CV as `0.1×soft`, but `feasible = hard_v≤tol` ignored soft — so among hard-feasible solutions MUST relationships had **zero** selection effect (v1 probe: 0/60 satisfied). | Split `cv` (hard) from `soft_cv` (MUST). Soft MUST now acts as a **feasibility-preserving discriminator** in binary tournament + elitist survival truncation among feasible solutions. | **71/429** archive solutions now fully satisfy all MUST links; mean shortfall 17.2 m. Selection visibly responds (soft_cv declines across generations). |
| 2 | **Seed provenance lost**: archive dropped `(seed, phenotype)`; representatives had no seed. | Archive rows + every representative trace now carry `seed` (and `soft_cv`, `cv`, `feasible`). | Traceability GENOTYPE→seed→objectives restored. |
| 3 | **Dilution measured wrong**: v1 used non-dominance *inside* the already-filtered archive (100% by construction — circular). | Dilution now measured via **per-generation rank-1 growth** from `histories.json`. | Correct, non-circular demonstration (§2). |
| 4 | **K-means clustered on RAW objectives** (`clustering.embed`), letting wide-range F8/F7 dominate distance over narrow F2/F4. | `embed` now min-max **normalizes** objectives — consistent with the interpretation layer. | k=6 noise → clean **k=2**; silhouette 0.232 → **0.338**. |
| 5 | **K-means-init vs evolutionary-seed stability conflated.** | Computed **separately** (§4). | Honest, distinct stability claims. |
| 6 | **Causal language** in module→objective stats. | Reframed as **associations** (no independent manipulation). | No causal overclaim (§3). |
| 7 | **Dormant genes** (`floors_H0` when H0 absent) in human-readable descriptions. | `genes_dict` drops masked genes; `public_intensity` reported as the derived value. | Clean traceability records. |

**All 16 optimizer tests still pass; NSGA-II operators, objectives, hard
constraints, and genotype encoding are otherwise unchanged.**

## 2. Many-objective dilution — correctly demonstrated
Measured as **rank-1 fraction growth per generation** (the proper signal):

> Every seed climbs from **1–2% rank-1 at generation 0 to ~100% rank-1 by
> mid-run** (`analysis_rank1_growth.png`).

Under 9 objectives the evolving population becomes almost entirely mutually
non-dominating, so Pareto rank stops discriminating. This is now shown as a
*dynamical* property of the search, not as a tautology about a filtered archive.
**Pareto membership is necessary but not sufficient evidence of quality.**

## 3. What the objectives measure — signal vs proxy artifact (unchanged core finding)
Spearman across 429 solutions (`analysis_objective_correlation.png`):
- **F5 ↔ F8 = −0.65 (CONFLICT)** — strengthened; the genuine site-efficiency vs
  community-connection trade-off.
- **F2 ↔ F9 = +0.56 (REDUNDANT)**; **F4 ↔ F6 = −0.41 (CONFLICT)**.
- **Proxy artifacts persist** (documented, not "fixed" — they are objective-model
  issues, not optimizer defects): F9 ≈ landscape_frac (r=−0.94); F8 ≈ public-module
  count (r=−0.73); F7 ≈ f(n_R4); F2/F4 near-binary.

**Module–objective ASSOCIATIONS** (`analysis_module_association.png`, descriptive
only): any public module is *associated with* lower F8 and slightly higher F5/F6.
These are co-occurring patterns under selection, **not** causal effects — module
presence co-varies with placement and other genes.

## 4. Two kinds of stability — now distinguished
- **K-means INITIALIZATION stability** (same archive, different inits): k=2 ARI
  = **1.000** → perfectly init-stable. Silhouette peaks at **k=2 (0.338)** and
  falls off for k≥3 (~0.17–0.20) (`analysis_kmeans_init_stability.png`).
- **EVOLUTIONARY-SEED stability** (do independent runs find the same programs?):
  **LOW** — only **1 of 92 unique structural signatures is shared by all 5 seeds**
  (recurrence Jaccard 0.011). Independent evolutionary runs converge to *different
  specific programs* even while populating the same objective-space structure.

> **Interpretation:** the *objective-space structure* is stable across evolutionary
> seeds, but the *specific programmatic solutions* are not. Conclusions must be
> drawn at the level of the trade-space and the shortlist, **not** at the level of
> "the algorithm found THE design."

## 5. The trade-space structure (v2, normalized clustering)
The clean k=2 partition is the **compactness / landscape axis**, NOT the
public-interface axis:
- **Cluster 0 (n=68):** compact schemes — n_R4 = 2 only, landscape ≈ 0.35, low
  F9-buffer, slightly better F5/F3.
- **Cluster 1 (n=361):** higher-landscape schemes — n_R4 = 2/3/4, landscape ≈ 0.46,
  high F9-buffer.

Silhouette 0.338 is still modest → the trade-space is **largely continuous**; k=2
is a defensible coarse split, not a rich taxonomy. **No basis for naming discrete
architectural typologies** (EVIDENCE INSUFFICIENT beyond the shortlist).

## 6. Program statistics (v2)
- **n_R4** skews to 2 (62%); 3 (28%); 4 (10%).
- **Optional module frequency:** H0 51% · I0 37% · L0 33% · J0 30% · **K0 7%**.
- **Public interface still skews low** (0–1 public modules in the majority) under
  safeguarding-as-hard-constraint.
- **Landscape fraction** mean 0.44 [0.30, 0.55].
- 92 unique structural signatures among 429 → convergence onto recurrent programs.

## 7. Do the v1 candidates survive? (gate question)
| v1 candidate | program | in v2 archive? | verdict |
|---|---|---|---|
| BALANCED (rep12) | R4×3 H1J1 | 10 solutions | program persists; **not** a v2 representative |
| SPECIALIZED (rep01) | R4×2 H1J1**K1** | 1 solution | **marginal** — K0-community now rare under MUST pressure |
| CONTRASTING (rep11) | R4×2 closed | 58 solutions | **strongly survives**, still dominant |

> **The v1 shortlist does NOT survive unchanged.** The must_adjacency remediation
> materially changed selection and the representative set. The v1 shortlist is
> superseded by the v2 shortlist (DESIGN_HANDOFF_v2). This is the expected and
> correct consequence of fixing a verified selection defect.

## 8. Where evidence is INSUFFICIENT
- No discrete typology beyond the 3-candidate shortlist (continuous trade-space).
- F8/F9/F7 are proxy-bound → their architectural meaning is DESIGN HYPOTHESIS.
- Cross-seed *program* recurrence is low → per-program claims are seed-dependent;
  only trade-space-level and shortlist-level claims are robust.

---
*Reproducible: `run_campaign.py --out campaign_v2` → `campaign_analysis_v2.py`
→ `campaign_v2/data/analysis_findings_v2.json`.*
