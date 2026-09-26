# arsitrad-evo — DESIGN HANDOFF (architectural decision package)
*The Threshold Community · 5,533.85 m² · derived from campaign @ `22f486f`.
This is an **architectural decision package, not an algorithmic winner.** The
evolutionary algorithm explored the trade-space; it did **not** select the
architecture. The three candidates below are handed to the next PA5 phase for
plan, section, circulation, threshold-sequence, and massing development.*

> Labels (BALANCED / SPECIALIZED / CONTRASTING) describe **selection role**, and
> were assigned only *after* measuring module composition + objective behaviour.
> They are not claimed architectural typologies (see FINDINGS §7: evidence is
> insufficient for a typology). Machine-readable source: `campaign/data/shortlist.json` / `.csv`.

---

## CANDIDATE A — BALANCED  *(rep 12 · no severe relative weakness)*
**Program:** `R4×3 + A0 B0 C0 E0 F0 M0 + H0 J0` · 2-floor C0, 2-floor H0
**Capacity / mass:** 12 residents · day users per genotype · GFA **1,417 m²** ·
footprint 1,158 m² · landscape **36.6%** · reserve 90–270 m²
**Objective vector (lower=better):** F1 0.26 · F2 0.00 · F3 0.21 · F4 0.01 ·
F5 0.39 · F6 0.41 · F7 0.34 · F8 0.33 · F9 **0.54**
**Why balanced:** lowest *worst-objective* of all 14 representatives (0.543).
No objective is at an extreme; its only relative weakness is F9 (landscape),
which is itself a landscape-area proxy (FINDINGS §2) and here simply reflects
the moderate 36.6% landscape allocation.

- **Computationally established:** all hard constraints satisfied (0 violations);
  feasible; sits mid-trade-space; public modules H0+J0 give a controlled interface
  (F8 0.33) without K0.
- **Design hypothesis:** that the H0+J0 interface produces a *graduated* threshold
  sequence (F8 is a count proxy — actual threshold *quality* is unmeasured).
- **To verify:** real landscape adequacy at 36.6% (F9 is area-proxy); accessibility
  /egress placeholder; parcel shape/orientation; safeguarding review of the
  H0+J0 interface placement.

---

## CANDIDATE B — SPECIALIZED  *(rep 01 · optimises community connection at a cost)*
**Program:** `R4×2 + A0 B0 C0 E0 F0 M0 + H0 J0 K0` · 2-floor C0, 2-floor H0
**Capacity / mass:** 8 residents · GFA **1,449 m²** · footprint 1,190 m² ·
landscape **39.1%**
**Objective vector:** F1 0.32 · F2 0.17 · F3 0.38 · F4 0.00 · F5 0.40 · F6 0.40 ·
F7 0.52 · F8 **0.00** · F9 **0.58**
**Specialisation:** the **only** candidate carrying **K0 (community module)** —
rare in the archive (5.4%). It achieves the best-possible F8 (0.00, full
controlled community connection) and the best F4 (0.00). **Explicit cost:** worst
F9 (0.581) and elevated F7 (0.52) and F1 (0.32). This is the clearest measured
F5/F8-conflict position: it pays site-efficiency and landscape to open the
threshold.

- **Computationally established:** best-in-campaign community connection (F8=0)
  with full public module set; feasible; 0 violations.
- **Design hypothesis:** that a 3-module public interface (H0+J0+K0) can remain
  *safeguarding-compatible* — F8 being a count proxy means the actual exposure
  risk is NOT established. This is the corpus's "distributed village" open question.
- **To verify:** **safeguarding authority sign-off is mandatory** before any K0
  development; non-exposure control between K0 and R4 (PROHIBITED-adjacency only
  checks distance ≥ 18 m, not sightlines); real public-frontage design.

---

## CANDIDATE C — CONTRASTING  *(rep 11 · a fundamentally different strategy)*
**Program:** `R4×2 + A0 B0 C0 E0 F0 M0` — **no optional/public modules** ·
2-floor C0, 2-floor H0
**Capacity / mass:** 8 residents · GFA **991 m²** (smallest) · footprint 841 m² ·
landscape **48.7%** (highest)
**Objective vector:** F1 **0.11** · F2 0.00 · F3 0.28 · F4 0.05 · F5 **0.28** ·
F6 0.26 · F7 0.54 · F8 **1.00** · F9 0.35
**Why contrasting:** the **closed / safeguarding-maximal** strategy. Best F1
safeguarding (0.106) and best F5 site efficiency (0.284) in the representative
set, achieved by *eliminating the public interface entirely*. **Explicit cost:**
worst-possible F8 (1.00 — zero community connection) and high F7 (0.54). This is
the opposite pole of Candidate B on the F5–F8 axis — the two are 1.77 apart in
normalised objective space, the widest separation in the shortlist.

- **Computationally established:** best safeguarding + best site efficiency;
  smallest footprint/GFA; highest landscape; feasible; 0 violations.
- **Design hypothesis:** that a fully closed scheme is *therapeutically and
  socially acceptable* — total absence of community connection (F8=1) may conflict
  with the corpus's reintegration aims. This is a **programmatic stance**, not an
  optimisation output.
- **To verify:** operator position on reintegration vs protection; whether the
  F8=1 penalty is *acceptable policy* or a *disqualifier*; domestic-scale quality
  at R4×2 (F7 0.54).

---

## Handoff chain

**COMPUTATIONAL RESULT** → 445-solution archive (really ~149 programs), a
*continuous* trade-space dominated by a genuine F5–F8 conflict and a low-public-
interface skew; 100% Pareto-saturated (dilution), so rank ≠ quality.

**ARCHITECTURAL MEANING** → the program's central tension is real and measurable:
opening the threshold (H0/J0/K0) buys community connection and everyday-life
access at a measurable cost to site efficiency, landscape, and adaptability. The
three candidates span this axis: **A** mid-trade-space compromise, **B** open /
connected, **C** closed / protected.

**DESIGN DECISION** → develop **all three** in parallel at schematic level; the
choice between them is a **safeguarding + operator + policy decision** (how much
community interface is acceptable), *not* a computational one. Do not collapse
to a single weighted score.

**TO VERIFY** (before any scaled drawing):
1. **Safeguarding authority** — K0/J0/H0 interface exposure (esp. Candidate B).
2. **Regulatory** — accessibility/egress (placeholder constraint), stacking limits.
3. **Real site** — parcel shape/orientation (rectangular envelope assumed), real
   setbacks/buffers.
4. **Operator** — resident capacity target (8 / 12 / 16 here), day-user demand,
   reintegration policy (acceptability of Candidate C's F8=1).
5. **Objective proxies** — recalibrate F8 (threshold *quality*, not count), F9
   (ecological performance, not area), F2/F4 (currently near-binary) with real
   safeguarding/clinical criteria.

*Next PA5 phase: develop plan, section, circulation, threshold sequence, and
massing from A, B, and C — carrying each candidate's TO-VERIFY list forward.*
