"""Site-aware constraints v4 — boundary, setback, rotation, stacking.

Extends v3 constraints with real site geometry validation.

Provenance: [DESIGN HYPOTHESIS] for all constraint thresholds.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .site import Site, point_in_polygon, nearest_edge
from .genotype_v4 import PhenotypeV4, InstanceV4
from .modules_v4 import ground_required_modules, stackable_modules


@dataclass
class ConstraintResult:
    """Result of a single constraint check."""
    name: str
    category: str          # boundary, setback, stacking, access, etc.
    passed: bool
    value: float = 0.0     # measured value
    threshold: float = 0.0 # limit
    severity: str = "hard" # hard, soft, advisory
    provenance: str = "[DESIGN HYPOTHESIS]"
    description: str = ""


@dataclass
class ConstraintReport:
    """Aggregate constraint evaluation."""
    feasible: bool
    hard_violations: int = 0
    soft_violations: int = 0
    advisory_flags: int = 0
    results: list[ConstraintResult] = field(default_factory=list)
    total_shortfall: float = 0.0
    provenance: str = "[DESIGN HYPOTHESIS]"
    # Experiment tier: None = Tier 1 (nominal full program); a day-user stratum
    # int = Tier 2 (controlled demand scenario). Reported, never fabricated.
    target_day_users: Optional[int] = None


def validate_boundary(ph: PhenotypeV4) -> ConstraintResult:
    """Check all modules are within site boundary."""
    site = ph.site
    violations = 0
    
    for inst in ph.instances:
        # Check module corners
        hw, hd = inst.w / 2, inst.d / 2
        corners = [
            (inst.x - hw, inst.y - hd),
            (inst.x + hw, inst.y - hd),
            (inst.x + hw, inst.y + hd),
            (inst.x - hw, inst.y + hd),
        ]
        
        for corner in corners:
            if not point_in_polygon(corner, site.boundary_polygon):
                violations += 1
                break
    
    return ConstraintResult(
        name="boundary_containment",
        category="boundary",
        passed=violations == 0,
        value=float(violations),
        threshold=0.0,
        severity="hard",
        description=f"{violations} module corners outside site boundary"
    )


def validate_setback(ph: PhenotypeV4, min_setback: "float | None" = None) -> ConstraintResult:
    """Check modules respect minimum setback from boundary.

    min_setback defaults to the site-derived side/rear setback so placement
    and constraint use one source of truth [DESIGN HYPOTHESIS].
    """
    site = ph.site
    if min_setback is None:
        sb = getattr(site, "setbacks_m", {}) or {}
        min_setback = max(float(sb.get("side", 3.0)),
                          float(sb.get("rear", 3.0))) if sb else 3.0
    violations = 0
    min_dist = float('inf')
    
    for inst in ph.instances:
        # Check module edge distance to boundary
        hw, hd = inst.w / 2, inst.d / 2
        
        # Sample points along module perimeter
        for dx, dy in [(-hw, 0), (hw, 0), (0, -hd), (0, hd),
                       (-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)]:
            px, py = inst.x + dx, inst.y + dy
            _, dist = nearest_edge((px, py), site.boundary_polygon)
            min_dist = min(min_dist, dist)
            if dist < min_setback:
                violations += 1
                break
    
    return ConstraintResult(
        name="setback_compliance",
        category="setback",
        passed=violations == 0,
        value=min_dist,
        threshold=min_setback,
        # SOFT: hard boundary containment is enforced at placement; setback is a
        # quality gradient the GA optimises, not a hard feasibility gate. This
        # keeps a feasible placement manifold on the irregular parcel [DH].
        severity="soft",
        description=f"Min setback: {min_dist:.1f}m (required: {min_setback}m)"
    )


def validate_rotation(inst: InstanceV4) -> ConstraintResult:
    """Check module rotation is allowed."""
    from .modules_v4 import get_module
    mt = get_module(inst.code)
    
    allowed = mt.allowed_rotations
    passed = inst.rotation in allowed
    
    return ConstraintResult(
        name=f"rotation_{inst.code}",
        category="rotation",
        passed=passed,
        value=float(inst.rotation),
        threshold=float(allowed[0]) if allowed else 0.0,
        severity="hard" if not passed else "advisory",
        description=f"Rotation {inst.rotation}° allowed: {allowed}"
    )


def validate_stacking(ph: PhenotypeV4) -> ConstraintResult:
    """Check stacking rules are respected."""
    violations = []
    
    ground_req = set(ground_required_modules())
    stackable = set(stackable_modules())
    
    for inst in ph.instances:
        # Ground-required modules must be on ground
        if inst.code in ground_req and inst.floor != 0:
            violations.append(f"{inst.code} requires ground but on floor {inst.floor}")
        
        # Non-stackable modules must be on ground
        if inst.code not in stackable and inst.floor > 0:
            violations.append(f"{inst.code} not stackable but on floor {inst.floor}")
        
        # If explicitly stacked (floor > 0), must be stackable type
        if inst.floor > 0 and inst.code not in stackable:
            violations.append(f"{inst.code} on floor {inst.floor} but not stackable")
    
    return ConstraintResult(
        name="stacking_rules",
        category="stacking",
        passed=len(violations) == 0,
        value=float(len(violations)),
        threshold=0.0,
        severity="hard",
        description=f"{len(violations)} stacking violations"
    )


def validate_access(inst: InstanceV4, site: Site) -> ConstraintResult:
    """Check module access face is toward a valid edge."""
    # Simplified: check access face is not blocked by another module
    # Full implementation would check path connectivity
    return ConstraintResult(
        name=f"access_{inst.code}",
        category="access",
        passed=True,  # simplified for now
        value=0.0,
        threshold=0.0,
        severity="advisory",
        description="Access validation simplified"
    )


def validate_module_fit(ph: PhenotypeV4) -> ConstraintResult:
    """Check all modules fit within site (no overlap with boundary)."""
    site = ph.site
    total_area = sum(i.area for i in ph.instances if i.floor == 0)
    footprint_ratio = total_area / site.area_m2 if site.area_m2 > 0 else 0
    
    # Advisory if footprint > 50% of site
    passed = footprint_ratio <= 0.60  # hard limit at 60%
    
    return ConstraintResult(
        name="site_footprint",
        category="boundary",
        passed=passed,
        value=footprint_ratio,
        threshold=0.60,
        severity="hard" if not passed else "advisory",
        description=f"Footprint: {footprint_ratio:.1%} of site area"
    )


# --- CAPACITY STRATA [DESIGN HYPOTHESIS] ------------------------------------
# The V4 experiment searches R4x2 .. R4x8 (provisionally 8..32 residents) and
# day-user strata 8..48. These are EXPERIMENTAL SEARCH STRATA, not recommended
# shelter capacities. The upper bound is a hard gate (larger populations are
# outside the validated search envelope); the lower bound and the privacy /
# domestic-scale signals are advisory so the GA can still explore and the
# trade-off metrics can show *where* capacity begins to compromise the brief.
MAX_RESIDENTS = 32      # R4x8 upper stratum
MAX_DAY_USERS = 48      # highest experimental day-user stratum
MIN_RESIDENTS = 8       # R4x2 lower stratum

# Module families that make up the public / day-user programme. In the
# controlled day-user experiments (Tier 2) these become evolvable so the GA
# can select a low-capacity subset; the residential + service backbone
# (R4, F0, M0, L0) is always present.
PUBLIC_PROGRAM_FAMILIES = ("A0", "B0", "C0", "H0", "J0", "K0", "I0")
# Minimum functional coverage the GA may not delete even at the lowest day-user
# stratum: arrival + care + commons + service are essential to The Threshold's
# identity [PA5 CORPUS]. (family -> minimum count)
MIN_FUNCTIONAL_COVERAGE = {"A0": 1, "B0": 1, "C0": 1, "F0": 1, "M0": 1}


def validate_capacity(ph: PhenotypeV4,
                      target_day_users: Optional[int] = None) -> list:
    """Check resident / day-user strata against the experimental envelope.

    Returns hard ConstraintResults for over-capacity (beyond the search
    envelope) and advisory results that flag where the population begins to
    press against privacy, domestic scale and landscape — the quantities the
    research question asks about.

    ``target_day_users`` selects the active day-user stratum for the hard cap.
    ``None`` (Tier 1 default/reference run) applies the full experimental
    envelope (MAX_DAY_USERS) so the nominal full-program capacity is reported
    rather than gated. A value from {8,16,24,32,40,48} (Tier 2 controlled
    demand scenarios) caps the run at that stratum.
    """
    results = []
    day_cap = MAX_DAY_USERS if target_day_users is None else int(target_day_users)
    # Tier 1 (target_day_users=None) reports the NOMINAL day-user capacity of
    # the fixed full corpus program as an advisory signal rather than a hard
    # gate — the nominal figure (148) exceeds the experimental envelope by
    # design, and the research question is where capacity bites. Tier 2
    # (stratum int) hard-caps the controlled demand scenario.
    day_severity = "hard" if target_day_users is not None else "advisory"

    # Hard: beyond the validated search envelope.
    results.append(ConstraintResult(
        name="resident_capacity_max",
        category="capacity",
        passed=ph.residents <= MAX_RESIDENTS,
        value=float(ph.residents),
        threshold=float(MAX_RESIDENTS),
        severity="hard",
        description=(f"{ph.residents} residents vs experimental max "
                     f"{MAX_RESIDENTS} (R4x8)"),
    ))
    results.append(ConstraintResult(
        name="day_user_capacity_max",
        category="capacity",
        passed=ph.day_users <= day_cap,
        value=float(ph.day_users),
        threshold=float(day_cap),
        severity=day_severity,
        description=(f"{ph.day_users} day users vs stratum cap {day_cap}"),
    ))

    # Advisory: below the lower experimental stratum (under-programmed).
    results.append(ConstraintResult(
        name="resident_capacity_min",
        category="capacity",
        passed=ph.residents >= MIN_RESIDENTS,
        value=float(ph.residents),
        threshold=float(MIN_RESIDENTS),
        severity="advisory",
        description=(f"{ph.residents} residents below experimental min "
                     f"{MIN_RESIDENTS} (R4x2)"),
    ))

    # Advisory: day users per resident — a proxy for public/private pressure.
    # When the day-user:resident ratio climbs, care access, service separation
    # and domestic scale come under pressure [DESIGN HYPOTHESIS].
    if ph.residents > 0:
        ratio = ph.day_users / ph.residents
        results.append(ConstraintResult(
            name="day_user_per_resident",
            category="capacity",
            passed=ratio <= 4.0,
            value=ratio,
            threshold=4.0,
            severity="advisory",
            description=(f"{ratio:.1f} day users per resident "
                         f"(privacy / service-separation pressure)"),
        ))

    return results


def validate_functional_coverage(
        ph: PhenotypeV4,
        min_coverage: Optional[dict] = None) -> ConstraintResult:
    """Hard gate: the GA may not delete essential program functions.

    Enforces MIN_FUNCTIONAL_COVERAGE so a controlled day-user scenario cannot
    reach its target merely by dropping arrival / care / commons / service —
    the functions that carry The Threshold's identity [PA5 CORPUS]. A scenario
    that would require deleting these to fit is reported infeasible, which is
    itself a finding: it marks where a demand stratum is incompatible with the
    core brief.
    """
    coverage = MIN_FUNCTIONAL_COVERAGE if min_coverage is None else min_coverage
    present = {}
    for inst in ph.instances:
        present[inst.family] = present.get(inst.family, 0) + 1
    missing = [fam for fam, need in coverage.items()
               if present.get(fam, 0) < need]
    return ConstraintResult(
        name="functional_coverage",
        category="program",
        passed=not missing,
        value=float(len(coverage) - len(missing)),
        threshold=float(len(coverage)),
        severity="hard",
        description=("all essential functions present" if not missing
                     else f"missing essential functions: {','.join(missing)}"),
    )


def evaluate_constraints(ph: PhenotypeV4,
                         target_day_users: Optional[int] = None,
                         min_coverage: Optional[dict] = None) -> ConstraintReport:
    """Run all constraint checks on a phenotype.

    ``target_day_users`` / ``min_coverage`` select the experiment tier:
    Tier 1 (default) passes ``target_day_users=None`` so the nominal
    full-program day-user capacity is reported against the full envelope;
    Tier 2 (controlled day-user scenarios) passes a stratum cap and enforces
    functional coverage.
    """
    report = ConstraintReport(feasible=True)
    report.target_day_users = target_day_users

    # Hard constraints
    checks = [
        validate_boundary(ph),
        validate_setback(ph),
        validate_stacking(ph),
        validate_module_fit(ph),
        validate_functional_coverage(ph, min_coverage),
    ]
    # Capacity strata (hard over-envelope gate + advisory trade-off signals)
    checks.extend(validate_capacity(ph, target_day_users))
    
    # Per-module checks
    for inst in ph.instances:
        checks.append(validate_rotation(inst))
    
    # Aggregate
    for check in checks:
        report.results.append(check)
        if not check.passed:
            if check.severity == "hard":
                report.hard_violations += 1
                report.feasible = False
            elif check.severity == "soft":
                report.soft_violations += 1
            else:
                report.advisory_flags += 1
    
    report.total_shortfall = sum(r.value for r in report.results if not r.passed)
    
    return report
