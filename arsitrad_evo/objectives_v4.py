"""Extended objectives v4 — site-aware evaluation.

Extends v3 objectives with site response, access clarity, landscape quality,
stacking efficiency, exposure gradient, and phaseability.

Provenance: [DESIGN HYPOTHESIS] for all objective formulations.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .genotype_v4 import PhenotypeV4
from .spatial_analysis import (
    compute_privacy_field, compute_enclosure, compute_exposure_grid,
    cast_sightline
)
from .circulation import (
    derive_resident_routes, derive_staff_routes, derive_visitor_routes,
    derive_service_routes, route_exposure
)
from .phases import phasing_score, decode_phases


@dataclass
class ObjectiveResult:
    """Result of a single objective evaluation."""
    name: str
    value: float           # 0-1, higher is better (or lower if minimize)
    minimize: bool = False # True if lower is better
    weight: float = 1.0    # importance weight
    provenance: str = "[DESIGN HYPOTHESIS]"
    description: str = ""


@dataclass
class ObjectiveVector:
    """Complete objective evaluation for a phenotype."""
    results: list[ObjectiveResult]
    weighted_sum: float    # for quick comparison (not used in NSGA-II)
    n_objectives: int
    
    def to_array(self) -> np.ndarray:
        """Return as array for NSGA-II (minimization form)."""
        arr = []
        for r in self.results:
            v = r.value if r.minimize else -r.value  # negate for minimization
            arr.append(v)
        return np.array(arr)


def evaluate_site_response(ph: PhenotypeV4) -> ObjectiveResult:
    """How well does the layout respond to site geometry?"""
    from .site import nearest_edge
    site = ph.site
    if not site:
        return ObjectiveResult("site_response", 0.5, description="No site")
    
    aligned = 0
    for inst in ph.instances:
        _, dist = nearest_edge((inst.x, inst.y), site.boundary_polygon)
        if dist < 10.0:
            aligned += 1
    
    alignment_score = aligned / len(ph.instances) if ph.instances else 0
    violation_penalty = ph.boundary_violations * 0.1
    score = max(0.0, alignment_score - violation_penalty)
    
    return ObjectiveResult(
        name="site_response", value=score,
        description=f"Alignment: {alignment_score:.2f}, violations: {ph.boundary_violations}"
    )


def evaluate_access_clarity(ph: PhenotypeV4) -> ObjectiveResult:
    """How clear and legible are the access routes?"""
    resident = derive_resident_routes(ph)
    if not resident.routes:
        return ObjectiveResult("access_clarity", 0.0, description="No resident routes")
    
    directness_scores = []
    for route in resident.routes:
        if route.length_m > 0:
            straight = math.sqrt(
                (route.end.x - route.start.x)**2 + 
                (route.end.y - route.start.y)**2
            )
            if straight > 0:
                directness_scores.append(straight / route.length_m)
    
    avg_directness = sum(directness_scores) / len(directness_scores) if directness_scores else 0
    exposure_penalty = resident.avg_exposure * 0.5
    score = max(0.0, avg_directness - exposure_penalty)
    
    return ObjectiveResult(
        name="access_clarity", value=score,
        description=f"Directness: {avg_directness:.2f}, exposure: {resident.avg_exposure:.2f}"
    )


def evaluate_landscape_quality(ph: PhenotypeV4) -> ObjectiveResult:
    """Quality of open space provision."""
    site = ph.site
    if not site:
        return ObjectiveResult("landscape_quality", 0.5)
    
    target_frac = 0.35
    frac_score = 1.0 - abs(ph.landscape_frac - target_frac) / target_frac
    
    enclosure_scores = []
    for i in range(3):
        x = site.width_m * (0.25 + i * 0.25)
        y = site.height_m * 0.5
        enc = compute_enclosure((x, y), 8.0, ph.instances)
        enclosure_scores.append(enc.enclosure_ratio)
    
    avg_enclosure = sum(enclosure_scores) / len(enclosure_scores) if enclosure_scores else 0
    enclosure_score = 1.0 - abs(avg_enclosure - 0.5) * 2
    score = frac_score * 0.6 + enclosure_score * 0.4
    
    return ObjectiveResult(
        name="landscape_quality", value=score,
        description=f"Frac: {ph.landscape_frac:.2f}, enclosure: {avg_enclosure:.2f}"
    )


def evaluate_stacking_efficiency(ph: PhenotypeV4) -> ObjectiveResult:
    """Efficiency of vertical stacking."""
    if ph.floor_count <= 1:
        return ObjectiveResult("stacking_efficiency", 0.5)
    
    stacked = sum(1 for i in ph.instances if i.floor > 0)
    total = len(ph.instances)
    stack_ratio = stacked / total if total > 0 else 0
    
    target_min, target_max = 0.20, 0.40
    if target_min <= stack_ratio <= target_max:
        ratio_score = 1.0
    else:
        dist = min(abs(stack_ratio - target_min), abs(stack_ratio - target_max))
        ratio_score = max(0.0, 1.0 - dist * 5)
    
    footprint_ratio = ph.footprint / ph.site.area_m2 if ph.site else 0
    footprint_score = max(0.0, 1.0 - footprint_ratio * 2)
    score = ratio_score * 0.7 + footprint_score * 0.3
    
    return ObjectiveResult(
        name="stacking_efficiency", value=score,
        description=f"Stacked: {stack_ratio:.2f}, footprint: {footprint_ratio:.2f}"
    )


def evaluate_exposure_gradient(ph: PhenotypeV4) -> ObjectiveResult:
    """Quality of privacy gradient across site."""
    pf = compute_privacy_field(ph, resolution=5.0)
    grid = pf.grid
    h, w = grid.shape
    
    abrupt = 0
    total = 0
    for i in range(1, h-1):
        for j in range(1, w-1):
            if grid[i, j] >= 0:
                for di, dj in [(0, 1), (1, 0)]:
                    ni, nj = i + di, j + dj
                    if grid[ni, nj] >= 0:
                        diff = abs(grid[i, j] - grid[ni, nj])
                        if diff > 2:
                            abrupt += 1
                        total += 1
    
    smoothness = 1.0 - (abrupt / total) if total > 0 else 0.5
    
    r4s = [i for i in ph.instances if i.family == "R4"]
    r4_privacy = 0
    for r4 in r4s:
        priv = pf.privacy_at(r4.x, r4.y)
        r4_privacy += priv
    r4_score = (r4_privacy / len(r4s) / 4.0) if r4s else 0.5
    score = smoothness * 0.5 + r4_score * 0.5
    
    return ObjectiveResult(
        name="exposure_gradient", value=score,
        description=f"Smoothness: {smoothness:.2f}, R4 privacy: {r4_score:.2f}"
    )


def evaluate_phaseability(ph: PhenotypeV4) -> ObjectiveResult:
    """Quality of phased growth plan."""
    score = phasing_score(ph)
    return ObjectiveResult(
        name="phaseability", value=score,
        description=f"Phasing score: {score:.2f}"
    )


def evaluate_service_efficiency(ph: PhenotypeV4) -> ObjectiveResult:
    """Efficiency of service/back-of-house routing."""
    service = derive_service_routes(ph)
    if not service.routes:
        return ObjectiveResult("service_efficiency", 0.5)
    
    site_diag = math.sqrt(ph.site.width_m**2 + ph.site.height_m**2) if ph.site else 100
    avg_len = service.total_length / len(service.routes) / site_diag
    len_score = max(0.0, 1.0 - avg_len * 2)
    exposure_score = 1.0 - service.avg_exposure
    score = len_score * 0.6 + exposure_score * 0.4
    
    return ObjectiveResult(
        name="service_efficiency", value=score,
        description=f"Avg len: {avg_len:.2f}, exposure: {service.avg_exposure:.2f}"
    )


def evaluate_climate_daylight(ph: PhenotypeV4) -> ObjectiveResult:
    """Climate and daylight proxy."""
    r4s = [i for i in ph.instances if i.family == "R4"]
    good_orient = 0
    for r4 in r4s:
        if r4.access_face in ("S", "E"):
            good_orient += 1
    
    orient_score = good_orient / len(r4s) if r4s else 0.5
    outdoor_score = min(1.0, ph.landscape_frac * 2)
    score = orient_score * 0.6 + outdoor_score * 0.4
    
    return ObjectiveResult(
        name="climate_daylight", value=score,
        description=f"Orientation: {orient_score:.2f}, outdoor: {outdoor_score:.2f}"
    )


def evaluate_objectives(ph: PhenotypeV4) -> ObjectiveVector:
    """Run all objective evaluations."""
    results = [
        evaluate_site_response(ph),
        evaluate_access_clarity(ph),
        evaluate_landscape_quality(ph),
        evaluate_stacking_efficiency(ph),
        evaluate_exposure_gradient(ph),
        evaluate_phaseability(ph),
        evaluate_service_efficiency(ph),
        evaluate_climate_daylight(ph),
    ]
    
    total_weight = sum(r.weight for r in results)
    weighted = sum(r.value * r.weight for r in results) / total_weight if total_weight > 0 else 0
    
    return ObjectiveVector(
        results=results,
        weighted_sum=weighted,
        n_objectives=len(results),
    )
