# arsitrad-evo — DESIGN HANDOFF v2 (architectural decision package)
*The Threshold Community · 5,533.85 m² · derived from **Campaign v2** (post-remediation).
This supersedes `campaign/DESIGN_HANDOFF.md` (v1). The v1 shortlist did **not**
survive the must_adjacency remediation unchanged (FINDINGS_v2 §7); the candidates
below are the frozen v2 shortlist. The evolutionary algorithm explored the
trade-space; it did **not** select the architecture. Labels describe **selection
role**, assigned only *after* measuring module composition + objective behaviour —
they are not claimed typologies (FINDINGS_v2 §8: EVIDENCE INSUFFICIENT for a
typology). Machine-readable source: `campaign_v2/data/shortlist_v2.json` / `.csv`.*

---

## CANDIDATE A — BALANCED  *(rep 02 · seed 42 · no severe relative weakness)*
**Program:** `R4×2 + A0 B0 C0 E0 F0 M0 + H0 J0 K0 I0` · 2-floor C0, 2-floor H0 · public intensity 3
**Capacity / mass:** 8 residents · 32 day users · GFA **1,485 m²** · footprint 1,226 m² ·
landscape **46.3%** · reserve 114 m² · **MUST links fully satisfied (soft_cv = 0)**
**Genotype:** n_R4=2, H1J1K1I1L0, floors_C0=2, floors_H0=2, landscape 0.463, service_depth 9.8, buffer 21.6, reserve 114
**Objective vector (lower=better):** F1 0.33 · F2 0.00 · F3 0.30 · F4 0.11 · F5 0.41 ·
F6 **0.58** · F7 0.28 · F8 **0.00** · F9 0.41
**Why balanced:** lowest worst-objective of all 11 v2 representatives (0.581). The
*only* candidate carrying the full public interface H0+J0+K0 **and** satisfying all
MUST-adjacency links. Best-possible F8 (0.00) and F2 (0.00); its relative weakness
is F6 adaptability (0.58) — the measured cost of the largest module population.

- **Computationally established:** feasible, 0 hard violations, all MUST links
  satisfied; mid-to-open position on the F5–F8 conflict plane; seed-42 provenance.
- **Design hypothesis:** that the H0+J0+K0 interface yields a *graduated* threshold
  sequence — F8 is a module-count proxy (FINDINGS_v2 §3), so threshold *quality* is
  unmeasured; F6 weakness may be a proxy artefact of counting modules.
- **To verify:** **safeguarding authority review of K0 exposure** (mandatory);
  non-exposure sightlines between public modules and R4 (PROHIBITED checks distance
  only); real landscape performance at 46.3% (F9 is an area proxy); accessibility/
  egress (placeholder); parcel shape/orientation.

---

## CANDIDATE B — SPECIALIZED  *(rep 09 · seed 2024 · optimises everyday-life accessibility)*
**Program:** `R4×2 + A0 B0 C0 E0 F0 M0 + H0 I0 L0` · single-storey C0 · public intensity 1
**Capacity / mass:** 8 residents · 16 day users · GFA **1,055 m²** · footprint 1,055 m² ·
landscape **53.8%** · reserve 261 m² (largest) · MUST soft_cv 17.5 m (1 link short)
**Genotype:** n_R4=2, H1J0K0I1L1, floors_C0=1, landscape 0.538, service_depth 9.1, buffer 21.2, reserve 261
**Objective vector:** F1 0.19 · F2 0.00 · F3 **0.13** · F4 0.05 · F5 0.36 · F6 0.29 ·
F7 0.25 · F8 **0.67** · F9 0.23
**Specialisation:** best **everyday-life accessibility (F3 = 0.132)** in the
representative set, with strong safeguarding (F1 0.19) and landscape buffer (F9 0.23),
through a *minimal single public front* (H0) plus learning/livelihood modules (I0, L0).
**Explicit cost:** F8 = 0.667 — no community module (J0/K0 absent), so controlled
community connection is weak; one MUST link is ~17.5 m short (placement-level,
fixable in schematic design, flagged honestly).

- **Computationally established:** best F3 + good F1/F9; feasible, 0 hard violations;
  distinct program (only candidate with L0); seed-2024 provenance.
- **Design hypothesis:** that a single H0 front with I0/L0 can deliver everyday-life
  quality *without* a community module — F3 is a centroid-distance proxy, so actual
  route quality is unmeasured.
- **To verify:** the 17.5 m MUST shortfall (which link, and whether schematic
  placement resolves it); whether F8 = 0.67 (no community interface) is acceptable
  to the operator's reintegration policy; single-storey C0 capacity vs day users.

---

## CANDIDATE C — CONTRASTING  *(rep 06 · seed 123 · fundamentally different strategy)*
**Program:** `R4×4 + A0 B0 C0 E0 F0 M0` — **no optional/public modules** · single-storey · public intensity 0
**Capacity / mass:** **16 residents** (largest) · 8 day users · GFA **1,017 m²** (smallest) ·
footprint 1,017 m² · landscape **54.8%** (highest) · reserve 140 m² · MUST soft_cv 20.5 m
**Genotype:** n_R4=4, all optional absent, floors_C0=1, landscape 0.548, service_depth 18.1, buffer 19.7, reserve 140
**Objective vector:** F1 0.23 · F2 0.00 · F3 0.40 · F4 0.01 · F5 0.34 · F6 0.24 ·
F7 0.30 · F8 **1.00** · F9 **0.005**
**Why contrasting:** the **closed, residential-maximal** strategy — four R4 clusters,
zero public interface, best-in-campaign **landscape buffer (F9 = 0.005)** and strong
service separation (F4 0.012) with the smallest building mass and highest landscape.
**Explicit cost:** worst-possible **F8 = 1.00** (zero community connection) and weak
everyday-life accessibility (F3 0.40). This is the opposite pole of Candidate A on
the F5–F8 axis (normalised distance 1.59).

- **Computationally established:** best F9 landscape buffer; smallest GFA/footprint;
  highest landscape fraction; feasible; seed-123 provenance. The closed strategy is
  also the **most recurrent program across the archive** (58 closed R4×2 variants).
- **Design hypothesis:** that a fully closed 16-resident scheme is *therapeutically
  and socially acceptable* — total absence of community connection (F8 = 1) may
  conflict with the corpus's reintegration aims. This is a **programmatic stance**,
  not an optimisation output.
- **To verify:** **operator position on reintegration vs protection** (is F8 = 1 a
  policy choice or a disqualifier?); domestic-scale quality of 4 clusters (F7 0.30);
  the 20.5 m MUST shortfall; day-user capacity with only C0.

---

## Candidate comparison (all lower=better except where noted)
| | A BALANCED | B SPECIALIZED | C CONTRASTING |
|---|---|---|---|
| Program | R4×2 +HJKI | R4×2 +HIL | R4×4 closed |
| Residents / day | 8 / 32 | 8 / 16 | 16 / 8 |
| GFA (m²) | 1,485 | 1,055 | 1,017 |
| Landscape | 46.3% | 53.8% | 54.8% |
| MUST satisfied | **yes (0 m)** | no (17.5 m) | no (20.5 m) |
| Best objective | F8 0.00 | F3 0.13 | F9 0.005 |
| Worst objective | F6 0.58 | F8 0.67 | F8 1.00 |
| Seed | 42 | 2024 | 123 |

Normalised objective distances: A–B 1.29 · A–C 1.59 · B–C 1.13 — genuinely separated.

## Handoff chain
**COMPUTATIONAL RESULT** → 429-solution archive with seed provenance (92 programs),
a largely continuous trade-space structured by the F5–F8 conflict and a compact-vs-
landscape k=2 split; rank-1 saturates by mid-run (dilution shown dynamically);
MUST-adjacency now genuinely shapes selection.

**ARCHITECTURAL MEANING** → opening the threshold (H0/J0/K0) buys community
connection and everyday-life access at measurable cost to site efficiency,
adaptability and (proxy-bound) landscape; closing it maximises buffer and
safeguarding at the cost of any community interface. A = graduated open; B =
minimal-front everyday-life; C = closed residential-maximal.

**DESIGN DECISION** → develop **all three** at schematic level. Choosing among them
is a **safeguarding + operator + policy decision** (how much community interface is
acceptable), *not* a computational one. No weighted-score collapse.

**TO VERIFY** (before scaled drawing):
1. **Safeguarding authority** — K0/J0/H0 exposure (esp. A); sightlines, not just distance.
2. **Operator** — reintegration policy (C's F8 = 1; B's F8 = 0.67), resident capacity target (8 vs 16), day-user demand.
3. **Regulatory** — accessibility/egress (placeholder), stacking limits.
4. **Real site** — parcel shape/orientation, setbacks/buffers (rectangular envelope assumed).
5. **Objective proxies** — recalibrate F8 (threshold quality, not module count), F9
   (ecological performance, not area), F2/F4 (near-binary) with safeguarding/clinical criteria.
6. **MUST shortfalls** — B (17.5 m) and C (20.5 m) links identified and resolved in schematic placement.

*Next: Spatial Phenotype Generator converts A, B, C genotypes into schematic
prototypes (plan / axonometric / stacking / privacy / circulation / composition /
objective profile), every component tagged [PA5 CORPUS] / [DESIGN HYPOTHESIS] /
[TO VERIFY]. The algorithm remains an explorer, not the architectural author.*
