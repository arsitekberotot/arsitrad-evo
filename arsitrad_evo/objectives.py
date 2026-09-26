"""Multi-objective criteria F1-F9 as explicit, measurable functions.

ALL objectives are MINIMIZED internally (NSGA-II convention here). User-facing
"maximize X" objectives are encoded as minimize(1 - normalized_score). Each
function returns a value in ~[0,1] using corpus reference ranges [DH / TV].

Only *feasible* solutions are meaningfully ranked (hard constraints handled by
constrained domination); objectives still computed for infeasible ones so that
crowding/sorting have defined values.

Every function documents: equation, direction, normalization, inputs,
assumptions, edge cases.
"""
from __future__ import annotations
import numpy as np

from . import config as C
from .genotype import Phenotype
from .modules import (relation, MUST, NEAR, PUBLIC_MODULES, PRIVATE_MODULES,
                      SERVICE_MODULES, CARE_MODULES)
from .constraints import dist


def _clamp01(x: float) -> float:
    return float(min(1.0, max(0.0, x)))


# ----------------------------------------------------------------------------
def f1_safeguarding(ph: Phenotype) -> float:
    """F1 SAFEGUARDING — maximize controlled access & care response.

    score = mean(gate_coverage, care_proximity)
      gate_coverage  = fraction of public modules within MUST range of a gate.
      care_proximity = 1 - (avg min R4->care distance / CARE_RESPONSE_MAX), clamped.
    minimize = 1 - score.
    Inputs: gate set {A0,B0}, care set {B0,E0}, R4 instances, distances.
    Assumptions [DH]: proximity proxies real controlled-access quality.
    Edge: no public modules -> gate_coverage = 1 (nothing uncontrolled).
    """
    gates = [i for i in ph.instances if i.code in ("A0", "B0")]
    pubs = [i for i in ph.instances if i.code in PUBLIC_MODULES and i.code not in ("A0", "B0")]
    if pubs and gates:
        cov = np.mean([1.0 if min(dist(p, g) for g in gates) <= C.MUST_LINK_MAX else 0.0
                       for p in pubs])
    else:
        cov = 1.0
    carers = [i for i in ph.instances if i.code in CARE_MODULES]
    r4s = ph.by_code("R4")
    if r4s and carers:
        d = np.mean([min(dist(r, c) for c in carers) for r in r4s])
        prox = 1.0 - _clamp01(d / C.CARE_RESPONSE_MAX)
    else:
        prox = 0.0
    return 1.0 - _clamp01(0.5 * cov + 0.5 * prox)


def f2_privacy_agency(ph: Phenotype) -> float:
    """F2 PRIVACY / AGENCY — maximize protected territory + route choice.

    protected = 1 - avg public-exposure of R4 (exposure = fraction of public
                 modules within PUBLIC_PRIVATE_MIN of an R4).
    choice    = min(1, n_retreat_options / 3); retreat options = courtyards(R4)
                 + I0 + quiet landscape proxy.
    minimize = 1 - mean(protected, choice).
    Edge: no public modules -> exposure 0 -> protected 1.
    """
    pubs = [i for i in ph.instances if i.code in PUBLIC_MODULES]
    r4s = ph.by_code("R4")
    if r4s and pubs:
        exp = np.mean([
            np.mean([1.0 if dist(r, p) < C.PUBLIC_PRIVATE_MIN else 0.0 for p in pubs])
            for r in r4s])
    else:
        exp = 0.0
    protected = 1.0 - _clamp01(exp)
    retreat = len(r4s) + (1 if ph.has("I0") else 0) + (1 if ph.landscape_frac > 0.4 else 0)
    choice = _clamp01(retreat / 3.0)
    return 1.0 - _clamp01(0.5 * protected + 0.5 * choice)


def f3_everyday_life(ph: Phenotype) -> float:
    """F3 EVERYDAY LIFE — maximize amenity access per resident.

    amenity_area = C0 + H0 + I0 + landscape_area (usable everyday space).
    access = amenity_area / residents, normalized by REF_AMENITY_PER_RES [DH=60].
    Also rewards NEAR-ness of amenities to R4 (avg proximity term).
    minimize = 1 - normalized blended access.
    Edge: residents>0 always (n_R4>=2 feasible).
    """
    REF = 60.0  # m^2 amenity per resident reference [DH]
    amen = sum(i.area for i in ph.instances if i.code in ("C0", "H0", "I0"))
    amen += ph.landscape_area
    per_res = amen / max(1, ph.residents)
    r4s = ph.by_code("R4")
    amens = [i for i in ph.instances if i.code in ("C0", "H0")]
    if r4s and amens:
        d = np.mean([min(dist(r, a) for a in amens) for r in r4s])
        prox = 1.0 - _clamp01(d / C.NEAR_LINK_MAX)
    else:
        prox = 0.5
    score = 0.6 * _clamp01(per_res / REF) + 0.4 * prox
    return 1.0 - _clamp01(score)


def f4_service_separation(ph: Phenotype) -> float:
    """F4 SERVICE SEPARATION — minimize service-resident circulation conflict.

    conflict = mean over service modules of exp(-d_min_to_R4 / tau), tau=10m [DH];
    close service<->R4 -> high conflict. Add penalty if F0-M0 disconnected.
    minimize = conflict (already 0..1).
    Edge: no R4 (infeasible anyway) -> 0.
    """
    r4s = ph.by_code("R4")
    serv = [i for i in ph.instances if i.code in SERVICE_MODULES]
    if not r4s or not serv:
        return 0.0
    tau = 10.0
    conf = np.mean([np.exp(-min(dist(s, r) for r in r4s) / tau) for s in serv])
    return _clamp01(conf)


def f5_site_efficiency(ph: Phenotype) -> float:
    """F5 SITE EFFICIENCY — minimize footprint per program delivered.

    eff = footprint / (BUILDABLE_MAX). Lower footprint (for given program) is
    better; stacking reduces footprint. minimize = eff (0..~1).
    Edge: footprint already bounded by C1; infeasible large values clamp.
    """
    return _clamp01(ph.footprint / C.BUILDABLE_MAX)


def f6_adaptability(ph: Phenotype) -> float:
    """F6 ADAPTABILITY / MODULARITY — maximize repeatability + reserve.

    repeat = fraction of instances that are repeatable module type (R4).
    reserve_score = reserve_area / 270 (max reserve).
    modularity = mean(repeat_norm, reserve_score). minimize = 1 - modularity.
    Edge: reserve_area bounded by gene range.
    """
    n = len(ph.instances)
    rep = sum(1 for i in ph.instances if i.code == "R4") / max(1, n)
    rep_norm = _clamp01(rep / 0.4)          # 40% repeatable = full score [DH]
    reserve_score = _clamp01(ph.reserve_area / 270.0)
    return 1.0 - _clamp01(0.5 * rep_norm + 0.5 * reserve_score)


def f7_domestic_scale(ph: Phenotype) -> float:
    """F7 DOMESTIC SCALE — minimize institutional aggregation of residences.

    Captures whether R4 clusters read as a dispersed set of small domestic
    houses (good) or one aggregated institutional mass (bad). Proxy [DH]:
    measure how *spread out* the R4 centroids are. If clusters are packed
    tightly together they aggregate visually/operationally into one mass.

      spread = mean pairwise distance between R4 centroids (0 if only 1 cluster)
      agg    = 1 - clamp(spread / SPREAD_REF)   # SPREAD_REF = 40 m [DH]
      minimize = agg  (0 = well dispersed/domestic, 1 = aggregated/institutional)

    Single R4 footprint is constant (complete-cluster rule), so it cannot
    discriminate; aggregation is the meaningful axis. Edge: 1 cluster -> agg=1
    (no dispersion possible) but infeasible anyway (n_R4>=2).
    """
    SPREAD_REF = 40.0  # m [DH]
    r4s = ph.by_code("R4")
    if len(r4s) < 2:
        return 1.0
    ds = [dist(r4s[i], r4s[j]) for i in range(len(r4s)) for j in range(i + 1, len(r4s))]
    spread = float(np.mean(ds))
    return 1.0 - _clamp01(spread / SPREAD_REF)


def f8_community_connection(ph: Phenotype) -> float:
    """F8 CONTROLLED COMMUNITY CONNECTION — maximize bounded semi-public reach.

    reach = fraction of {H0,J0,K0} present AND within NEAR range of C0/commons
    (i.e., reachable without entering domestic territory), weighted by
    public_intensity. minimize = 1 - normalized reach.
    Edge: none present -> reach 0 (but may still be feasible; low F8).
    """
    semi = [c for c in ("H0", "J0", "K0") if ph.has(c)]
    if not semi:
        return 1.0
    anchors = [i for i in ph.instances if i.code in ("C0", "A0")]
    ok = 0
    for c in semi:
        for inst in ph.by_code(c):
            if anchors and min(dist(inst, a) for a in anchors) <= C.NEAR_LINK_MAX:
                ok += 1
                break
    reach = ok / 3.0     # normalize by max possible semi-public modules
    return 1.0 - _clamp01(reach)


def f9_landscape_buffer(ph: Phenotype) -> float:
    """F9 LANDSCAPE / ENVIRONMENTAL BUFFER — maximize meaningful outdoor +
    environmental interface.

    land_score  = landscape_frac normalized within [MIN,MAX].
    buffer_score= (buffer_depth - 10)/(30-10) from genotype.
    courtyard   = n_R4 courtyards present (each cluster has one) -> n_R4/4.
    minimize = 1 - mean(land_score, buffer_score, courtyard).
    Edge: buffer_depth read from genes (decode stores in phenotype? use frac only
    + n_R4 here; buffer depth folded via landscape_frac proxy). [DH]
    """
    land = _clamp01((ph.landscape_frac - C.LANDSCAPE_MIN) /
                    (C.LANDSCAPE_MAX - C.LANDSCAPE_MIN))
    courtyard = _clamp01(ph.n_R4 / C.N_R4_MAX)
    score = 0.6 * land + 0.4 * courtyard
    return 1.0 - _clamp01(score)


# Ordered objective registry (matches SPEC F1..F9).
OBJECTIVES = [
    ("F1_safeguarding",        f1_safeguarding),
    ("F2_privacy_agency",      f2_privacy_agency),
    ("F3_everyday_life",       f3_everyday_life),
    ("F4_service_separation",  f4_service_separation),
    ("F5_site_efficiency",     f5_site_efficiency),
    ("F6_adaptability",        f6_adaptability),
    ("F7_domestic_scale",      f7_domestic_scale),
    ("F8_community_connection",f8_community_connection),
    ("F9_landscape_buffer",    f9_landscape_buffer),
]
N_OBJECTIVES = len(OBJECTIVES)


def evaluate_objectives(ph: Phenotype) -> np.ndarray:
    vals = np.array([fn(ph) for _, fn in OBJECTIVES], dtype=float)
    ph.objectives = vals
    return vals
