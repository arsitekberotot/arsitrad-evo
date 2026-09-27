"""Architectural interpretation for V4 experiment results.

Translates raw phenotype metrics into architectural trade-off explanations:
not simply *which* layouts fit, but *why* a module population / capacity
stratum creates particular consequences for privacy, safeguarding, domestic
scale, landscape, care access, service separation and adaptability.

All interpretive thresholds are [DESIGN HYPOTHESIS] unless the underlying
metric is evidence-tagged (module capacities are [PA5 CORPUS]).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

# [DESIGN HYPOTHESIS] interpretive thresholds for trade-off flags.
LANDSCAPE_LOW = 0.40          # below this, open space is compromised
PRIVACY_PRESSURE_RES = 24     # residents above which domestic scale strains
DOMESTIC_SCALE_RES = 16       # nominal 'domestic' upper bound for one cluster
STACKING_PRESSURE = 0.35      # stacked_pairs / instances above this -> vertical pressure


@dataclass
class Interpretation:
    """One row of architectural interpretation."""
    target_day_users: Optional[int]
    residents: Optional[int]
    reachable: bool
    findings: list[str] = field(default_factory=list)
    tradeoffs: list[str] = field(default_factory=list)


def interpret_stratum(day_users, residents, reachable, best_metrics=None):
    """Return an Interpretation for one (day-user, resident) cell.

    best_metrics: dict of objective/metric values for the representative
    (fittest) phenotype in this cell, or None when unreachable.
    """
    it = Interpretation(day_users, residents, reachable)

    if not reachable:
        it.findings.append(
            f"Day-user stratum {day_users} at {residents} residents is NOT "
            f"reachable while essential functional coverage (arrival, care, "
            f"commons, service) and the mandatory threshold (L0 x2) are "
            f"preserved.")
        it.tradeoffs.append(
            "Reaching this demand would require DELETING essential program — "
            "an unacceptable safeguarding / care-access compromise — or "
            "introducing smaller evidence-supported module variants that the "
            "current PA5 corpus does not yet justify.")
        return it

    m = best_metrics or {}
    lf = m.get("landscape_frac")
    floors = m.get("floors")
    n = m.get("n_instances")
    sp = m.get("stacked_pairs", 0)

    # Privacy / domestic scale ------------------------------------------------
    if residents is not None:
        if residents >= PRIVACY_PRESSURE_RES:
            it.tradeoffs.append(
                f"{residents} residents exceeds the domestic-scale comfort "
                f"band (~{DOMESTIC_SCALE_RES}); privacy and household identity "
                f"come under pressure and rely on cluster subdivision.")
        elif residents >= DOMESTIC_SCALE_RES:
            it.findings.append(
                f"{residents} residents sits at the upper edge of a single "
                f"domestic cluster; further growth pushes toward multiple "
                f"household clusters.")
        else:
            it.findings.append(
                f"{residents} residents preserves a legible domestic scale.")

    # Landscape ---------------------------------------------------------------
    if lf is not None:
        if lf < LANDSCAPE_LOW:
            it.tradeoffs.append(
                f"Landscape fraction {lf:.2f} is below {LANDSCAPE_LOW}: "
                f"building mass is crowding open space, compromising the "
                f"therapeutic / threshold landscape.")
        else:
            it.findings.append(
                f"Landscape fraction {lf:.2f} retains a viable open-space "
                f"armature.")

    # Verticality / stacking ---------------------------------------------------
    if floors is not None and floors > 1:
        ratio = (sp / n) if n else 0.0
        if ratio >= STACKING_PRESSURE:
            it.tradeoffs.append(
                f"{floors} floors with {sp} stacked pairs indicate vertical "
                f"pressure: capacity is being absorbed by stacking rather than "
                f"by site area, affecting the domestic, low-rise character.")
        else:
            it.findings.append(
                f"Selective stacking ({sp} pairs over {floors} floors) absorbs "
                f"capacity without eroding the low-rise threshold character.")

    # Day-user / service separation -------------------------------------------
    if day_users is not None and residents is not None and residents > 0:
        ratio = day_users / residents
        if ratio >= 3.0:
            it.tradeoffs.append(
                f"Day users ({day_users}) outnumber residents ({residents}) "
                f"{ratio:.1f}x: public/service flows dominate, demanding clear "
                f"public-service separation to protect resident safeguarding.")
    return it


def interpret_experiment(tier2_csv, boundary_csv, out_txt):
    """Build a stratum-by-stratum interpretation report from experiment CSVs."""
    t2 = pd.read_csv(tier2_csv)
    bd = pd.read_csv(boundary_csv)
    lines = []
    lines.append("THE THRESHOLD - V4 ARCHITECTURAL INTERPRETATION")
    lines.append("=" * 55)
    lines.append("")
    lines.append("Why module populations and capacities create different")
    lines.append("architectural trade-offs (interpretive thresholds are")
    lines.append("[DESIGN HYPOTHESIS]; capacities are [PA5 CORPUS]).")
    lines.append("")

    for du in sorted(bd["target_day_users"].unique()):
        sub = bd[bd["target_day_users"] == du]
        frac = sub["reachable"].mean()
        if frac == 0.0:
            it = interpret_stratum(du, None, False)
            lines.append(f"Day-user stratum {du}: UNREACHABLE")
            for tr in it.tradeoffs:
                lines.append(f"   - {tr}")
            continue
        # representative reachable cell: highest residents reached
        reach_rows = t2[(t2["target_day_users"] == du) & (t2["reachable"])]
        if len(reach_rows) == 0:
            continue
        best = reach_rows.sort_values(by="residents").iloc[-1]
        metrics = best.to_dict()
        it = interpret_stratum(du, int(best["residents"]), True, metrics)
        lines.append(f"Day-user stratum {du}: reachable up to "
                     f"{int(best['residents'])} residents "
                     f"(reachability {frac:.0%})")
        for f in it.findings:
            lines.append(f"   + {f}")
        for tr in it.tradeoffs:
            lines.append(f"   - {tr}")
        lines.append("")

    with open(out_txt, "w") as f:
        f.write("\n".join(lines))
    return "\n".join(lines)
