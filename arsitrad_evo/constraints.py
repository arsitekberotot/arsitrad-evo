"""Hard constraints -> violation scores for constrained domination (Deb 2002).

Each function returns violation >= 0 (0 = satisfied). A solution is feasible
iff ALL violations are 0. Constrained dominance: feasible always dominates
infeasible; among infeasible, smaller total violation wins.

Geometry helpers use phase-1 axis-aligned rectangles + centroids [DH].
"""
from __future__ import annotations
import numpy as np

from . import config as C
from .genotype import Phenotype, Instance
from .modules import (relation, MUST, NEAR, PROHIBITED, AVOID,
                      PUBLIC_MODULES, PRIVATE_MODULES, CARE_MODULES,
                      SERVICE_MODULES, CONTROLLED_GATE, ALWAYS_PRESENT)


# --- geometry helpers --------------------------------------------------------
def dist(a: Instance, b: Instance) -> float:
    return float(np.hypot(a.x - b.x, a.y - b.y))


def overlap_area(a: Instance, b: Instance) -> float:
    dx = (a.w + b.w) / 2 - abs(a.x - b.x)
    dy = (a.d + b.d) / 2 - abs(a.y - b.y)
    if dx <= 0 or dy <= 0:
        return 0.0
    return dx * dy


# --- individual constraints ---------------------------------------------------
def c_overlap(ph: Phenotype) -> float:
    """Rectangles must not overlap beyond tolerance."""
    tot = 0.0
    inst = ph.instances
    for i in range(len(inst)):
        for j in range(i + 1, len(inst)):
            ov = overlap_area(inst[i], inst[j])
            if ov > C.OVERLAP_TOL:
                tot += ov
    return tot


def c_site_limit(ph: Phenotype) -> float:
    """Footprint + reserve must fit within the buildable band."""
    return max(0.0, ph.footprint + ph.reserve_area - C.BUILDABLE_MAX)


def c_site_boundary(ph: Phenotype) -> float:
    """Every module footprint must remain inside the schematic site frame [DH]."""
    return float(sum(
        max(0.0, i.w / 2 - i.x) + max(0.0, i.x + i.w / 2 - C.SITE_W)
        + max(0.0, i.d / 2 - i.y) + max(0.0, i.y + i.d / 2 - C.SITE_H)
        for i in ph.instances
    ))


def c_required_modules(ph: Phenotype) -> float:
    """Developmental DNA modules must be present."""
    missing = sum(0 if ph.has(code) else 1 for code in ALWAYS_PRESENT)
    missing += 0 if ph.n_R4 >= C.N_R4_MIN else 1
    return float(missing)


def c_population_range(ph: Phenotype) -> float:
    v = 0.0
    v += max(0, ph.n_R4 - C.N_R4_MAX) + max(0, C.N_R4_MIN - ph.n_R4)
    return float(v)


def _pairs(ph: Phenotype, code_a: str, code_b: str):
    for a in ph.by_code(code_a):
        for b in ph.by_code(code_b):
            yield a, b


def c_prohibited_adjacency(ph: Phenotype) -> float:
    """PROHIBITED pairs (R4-F0, R4-M0, R4-K0) must keep min separation. C12."""
    v = 0.0
    codes = {i.code for i in ph.instances}
    for a in codes:
        for b in codes:
            if a >= b:
                continue
            if relation(a, b) == PROHIBITED:
                for ia, ib in _pairs(ph, a, b):
                    short = C.PROHIBITED_MIN_SEP - dist(ia, ib)
                    if short > 0:
                        v += short
    return v


def c_privacy_hierarchy(ph: Phenotype) -> float:
    """No PUBLIC<->DOMESTIC/PERSONAL close adjacency. C8."""
    v = 0.0
    for pub in ph.instances:
        if pub.code not in PUBLIC_MODULES:
            continue
        for priv in ph.instances:
            if priv.code in PRIVATE_MODULES:
                short = C.PUBLIC_PRIVATE_MIN - dist(pub, priv)
                if short > 0:
                    v += short
    return v


def c_safeguarding_access(ph: Phenotype) -> float:
    """No uncontrolled public->R4 adjacency: public modules must be gated. C4.

    Proxy [DH]: each PUBLIC module must be within MUST range of a CONTROLLED
    gate (A0/B0); otherwise it is an uncontrolled access point.
    """
    v = 0.0
    gates = [i for i in ph.instances if i.code in CONTROLLED_GATE]
    for pub in ph.instances:
        if pub.code in PUBLIC_MODULES and pub.code not in CONTROLLED_GATE:
            if not gates or min(dist(pub, g) for g in gates) > C.MUST_LINK_MAX:
                v += 1.0
    return v


def c_care_access(ph: Phenotype) -> float:
    """Every R4 must be within care-response distance of B0 or E0. C5."""
    v = 0.0
    carers = [i for i in ph.instances if i.code in CARE_MODULES]
    for r in ph.by_code("R4"):
        if not carers or min(dist(r, c) for c in carers) > C.CARE_RESPONSE_MAX:
            v += 1.0
    return v


def c_no_public_private_shortcut(ph: Phenotype) -> float:
    """No direct PUBLIC->PERSONAL adjacency bypassing a gate. C6.

    Proxy [DH]: each public module must be >= PUBLIC_PRIVATE_MIN from every R4
    (already in C8) AND each R4 must be reachable to a gate (A0/B0) so that a
    legitimate controlled path exists. Count R4 with no gate within NEAR range.
    """
    v = 0.0
    gates = [i for i in ph.instances if i.code in CONTROLLED_GATE]
    for r in ph.by_code("R4"):
        if not gates or min(dist(r, g) for g in gates) > C.NEAR_LINK_MAX:
            v += 1.0
    return v


def c_independent_service(ph: Phenotype) -> float:
    """Service modules must not sit inside private territory. C7.

    Proxy [DH]: F0/M0 must each be >= PROHIBITED_MIN_SEP from every R4
    (reinforces R4-F0/R4-M0 PROHIBITED) and F0-M0 must stay connected (MUST).
    """
    v = 0.0
    for s in ph.instances:
        if s.code in SERVICE_MODULES:
            for r in ph.by_code("R4"):
                short = C.PROHIBITED_MIN_SEP - dist(s, r)
                if short > 0:
                    v += short
    # F0-M0 MUST connect
    for f in ph.by_code("F0"):
        for m in ph.by_code("M0"):
            over = dist(f, m) - C.MUST_LINK_MAX
            if over > 0:
                v += over
    return v


def c_stacking(ph: Phenotype) -> float:
    """Stacking rules. C9. R4 single-storey; module floors within cap; no
    module above F0/M0 (phase-1: we simply forbid >1 floor on service modules
    and on R4, and cap C0/H0 at max_floors)."""
    from .modules import MODULES
    v = 0.0
    for i in ph.instances:
        cap = MODULES[i.code].max_floors
        if i.floors > cap:
            v += (i.floors - cap)
        if i.code in SERVICE_MODULES and i.floors > 1:
            v += 1.0
        if i.code == "R4" and i.floors > 1:
            v += 1.0
    return v


def c_landscape_band(ph: Phenotype) -> float:
    """Landscape fraction within [MIN, MAX]. C10."""
    f = ph.landscape_frac
    return float(max(0.0, C.LANDSCAPE_MIN - f) + max(0.0, f - C.LANDSCAPE_MAX))


def c_accessibility_egress(ph: Phenotype) -> float:
    """Placeholder C11 [TO VERIFY]: real egress/accessibility dimensions require
    authority review. Returns 0 (no violation) in phase 1."""
    return 0.0


def c_must_adjacency(ph: Phenotype) -> float:
    """Sum MUST-link shortfalls, checking every instance of a repeatable module.

    R4 clusters each need their own B0 and C0 relationship. A code-level minimum
    would let one nearby R4 hide disconnected residential clusters. A MUST
    shortfall makes the schematic configuration model-infeasible.
    """
    v = 0.0
    codes = sorted({i.code for i in ph.instances})
    for ai, a in enumerate(codes):
        for b in codes[ai + 1:]:
            if relation(a, b) == MUST:
                aa, bb = ph.by_code(a), ph.by_code(b)
                many, few = (aa, bb) if len(aa) >= len(bb) else (bb, aa)
                for inst in many:
                    v += max(0.0, min(dist(inst, other) for other in few)
                             - C.MUST_LINK_MAX)
    return v


# Ordered constraint registry. (name, function, is_hard)
CONSTRAINTS = [
    ("overlap",              c_overlap,              True),
    ("site_limit",           c_site_limit,           True),
    ("site_boundary",        c_site_boundary,        True),
    ("required_modules",     c_required_modules,     True),
    ("population_range",     c_population_range,     True),
    ("prohibited_adjacency", c_prohibited_adjacency, True),
    ("privacy_hierarchy",    c_privacy_hierarchy,    True),
    ("safeguarding_access",  c_safeguarding_access,  True),
    ("care_access",          c_care_access,          True),
    ("no_public_private",    c_no_public_private_shortcut, True),
    ("independent_service",  c_independent_service,  True),
    ("stacking",             c_stacking,             True),
    ("landscape_band",       c_landscape_band,       True),
    ("accessibility_egress", c_accessibility_egress, True),  # placeholder
    ("must_adjacency",       c_must_adjacency,       True),
]

# Hard constraints must be zero within numerical tolerance for feasibility.
FEAS_TOL = 1e-6


def evaluate_constraints(ph: Phenotype) -> tuple[float, bool, dict]:
    """Return (total_violation, feasible, per_constraint_dict).

    Hard violation drives constrained domination. The legacy soft_cv field is
    populated with MUST shortfall for old consumers, but MUST is hard in v3.
    """
    detail = {}
    hard_v = 0.0
    for name, fn, is_hard in CONSTRAINTS:
        val = fn(ph)
        detail[name] = val
        if is_hard:
            hard_v += val
    feasible = hard_v <= FEAS_TOL
    ph.cv = hard_v                    # constrained-domination violation = hard only
    ph.must_shortfall = detail["must_adjacency"]
    ph.soft_cv = ph.must_shortfall  # legacy field
    ph.feasible = feasible
    return hard_v, feasible, detail
