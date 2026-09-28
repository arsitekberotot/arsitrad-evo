"""V4.1 model-feasibility gates, including independent object collision."""
from __future__ import annotations

from collections import Counter

from .constraints_v4 import ConstraintReport, ConstraintResult
from .genotype_v4 import PhenotypeV4
from .pipeline_v41 import collision_gate, footprint_inside, intersection_area
from .modules_v4 import MODULE_LIBRARY_V4


ESSENTIAL_PROGRAM = {"A0": 1, "B0": 1, "C0": 1, "F0": 1, "M0": 1, "R4": 2}


def evaluate_constraints_v41(ph: PhenotypeV4,
                             requested_day_users: int,
                             target_residents: int | None = None) -> ConstraintReport:
    checks = []
    actual_collision = collision_gate(ph.instances)
    generated_collision = ph.collision_report or actual_collision
    checks.append(ConstraintResult(
        "object_collision", "collision", generated_collision["illegal_overlap_count"] == 0
        and actual_collision["illegal_overlap_count"] == 0,
        value=float(generated_collision["illegal_overlap_area_m2"] + actual_collision["illegal_overlap_area_m2"]),
        threshold=0.0, severity="hard",
        description=f"{generated_collision['illegal_overlap_count']} generated and {actual_collision['illegal_overlap_count']} retained illegal same-floor overlaps"))
    unpermitted = max(generated_collision["unpermitted_shared_edge_count"],
                      actual_collision["unpermitted_shared_edge_count"])
    checks.append(ConstraintResult("attachment_grammar", "collision", unpermitted == 0,
                                   float(unpermitted), 0.0, "hard",
                                   description=f"{unpermitted} shared-edge contacts without a permitted group connection"))
    outside = sum(not footprint_inside(i.x, i.y, i.w, i.d, ph.site) for i in ph.instances)
    checks.append(ConstraintResult("parcel_containment", "site", outside == 0,
                                   float(outside), 0.0, "hard",
                                   description=f"{outside} retained footprints outside parcel"))
    pop = Counter(i.family for i in ph.instances)
    missing = {fam: max(0, need - pop[fam]) for fam, need in ESSENTIAL_PROGRAM.items()}
    checks.append(ConstraintResult("essential_program", "program", sum(missing.values()) == 0,
                                   float(sum(missing.values())), 0.0, "hard",
                                   description=f"missing unit counts: {missing}"))
    checks.append(ConstraintResult("resident_minimum", "occupancy", ph.residents >= 8,
                                   float(max(0, 8 - ph.residents)), 0.0, "hard",
                                   description=f"{ph.residents} residents; minimum experimental stratum 8"))
    checks.append(ConstraintResult("resident_maximum", "occupancy", ph.residents <= 32,
                                   float(max(0, ph.residents - 32)), 0.0, "hard",
                                   description=f"{ph.residents} residents; maximum experimental stratum 32"))
    if target_residents is not None:
        checks.append(ConstraintResult("resident_stratum", "occupancy", ph.residents == target_residents,
                                       float(abs(ph.residents - target_residents)), 0.0, "hard",
                                       description=f"{ph.residents} residents in target stratum {target_residents}"))
    unmet = ph.occupancy_allocation.get("unmet_day_users", requested_day_users)
    checks.append(ConstraintResult("concurrent_occupancy", "occupancy", unmet == 0 and ph.day_users == requested_day_users,
                                   float(unmet), 0.0, "hard",
                                   description=(f"{ph.day_users} concurrent day users allocated of {requested_day_users} requested; "
                                                f"nominal room-capacity sum {ph.nominal_day_capacity}")))
    incompatible = sum(i.zone != i.target_zone for i in ph.instances if i.target_zone != "service")
    checks.append(ConstraintResult("dynamic_zone_compatibility", "zoning", incompatible == 0,
                                   float(incompatible), 0.0, "hard",
                                   description=f"{incompatible} retained units outside required ordered zone"))
    unsupported = 0
    for top in (i for i in ph.instances if i.floor > 0):
        mt = MODULE_LIBRARY_V4[top.code]
        below = [i for i in ph.instances if i.floor == top.floor - 1
                 and MODULE_LIBRARY_V4[i.code].stackable_below
                 and intersection_area(i, top) >= top.w * top.d - 1e-5]
        if not mt.stackable_above or not below:
            unsupported += 1
    checks.append(ConstraintResult("stacking_support", "stacking", unsupported == 0,
                                   float(unsupported), 0.0, "hard",
                                   description=f"{unsupported} unsupported stacked units"))
    checks.append(ConstraintResult("unit_filtration_accounting", "filtration",
                                   ph.generated_units == ph.retained_units + len(ph.filtered_units),
                                   float(abs(ph.generated_units - ph.retained_units - len(ph.filtered_units))),
                                   0.0, "hard", description="generated = retained + filtered"))
    setbacks = ph.setback_violations
    checks.append(ConstraintResult("schematic_setback", "site", setbacks == 0,
                                   float(setbacks), 0.0, "soft",
                                   description=f"{setbacks} modules within schematic setback band"))
    report = ConstraintReport(feasible=True, results=checks,
                              target_day_users=requested_day_users)
    for check in checks:
        if not check.passed:
            if check.severity == "hard":
                report.hard_violations += 1
                report.feasible = False
            elif check.severity == "soft":
                report.soft_violations += 1
            else:
                report.advisory_flags += 1
    report.total_shortfall = sum(max(1.0, c.value) for c in checks
                                 if not c.passed and c.severity == "hard")
    return report
