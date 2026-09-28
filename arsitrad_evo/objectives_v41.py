"""Six architectural objective families with inspectable spatial submetrics."""
from __future__ import annotations

import math
from statistics import mean

from .context_v41 import SiteContext
from .genotype_v4 import PhenotypeV4
from .objectives_v4 import ObjectiveResult, ObjectiveVector
from .pipeline_v41 import _segments_cross
from .site import distance_to_arrival


OBJECTIVE_NAMES = ("care_safeguarding", "privacy_domesticity",
                   "everyday_community", "access_service",
                   "site_environment", "adaptability_phasing")


def _clip(value):
    return max(0.0, min(1.0, float(value)))


def _distance(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def _nearest(source, targets):
    return min((_distance(source, target) for target in targets), default=None)


def _normalized_distance(value, scale):
    return _clip(1.0 - value / scale) if value is not None else 0.0


def _open_continuity(ph: PhenotypeV4, cell: float = 6.0) -> float:
    """Largest connected unbuilt parcel-grid component / all open cells."""
    from .site import point_in_polygon
    occupied = []
    nx = int(ph.site.width_m / cell) + 1
    ny = int(ph.site.height_m / cell) + 1
    for yi in range(ny):
        for xi in range(nx):
            x, y = (xi + 0.5) * cell, (yi + 0.5) * cell
            if not point_in_polygon((x, y), ph.site.boundary_polygon):
                continue
            if any(i.floor == 0 and abs(i.x - x) < i.w / 2 and abs(i.y - y) < i.d / 2
                   for i in ph.instances):
                continue
            occupied.append((xi, yi))
    open_cells = set(occupied)
    if not open_cells:
        return 0.0
    largest = 0
    while open_cells:
        start = open_cells.pop()
        queue = [start]
        size = 1
        for current in queue:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                adjacent = (current[0] + dx, current[1] + dy)
                if adjacent in open_cells:
                    open_cells.remove(adjacent)
                    queue.append(adjacent)
                    size += 1
        largest = max(largest, size)
    return largest / len(occupied)


def _line_crossings(first: list[tuple], second: list[tuple]) -> int:
    return sum(_segments_cross(a, b, c, d) for a, b in first for c, d in second)


def _line_intersects_footprint(a, b, inst) -> bool:
    corners = [(inst.x - inst.w / 2, inst.y - inst.d / 2),
               (inst.x + inst.w / 2, inst.y - inst.d / 2),
               (inst.x + inst.w / 2, inst.y + inst.d / 2),
               (inst.x - inst.w / 2, inst.y + inst.d / 2)]
    return any(_segments_cross(a, b, corners[j], corners[(j + 1) % 4])
               for j in range(4))


def _courtyard_quality(ph: PhenotypeV4) -> float:
    groups = {}
    for inst in ph.instances:
        if inst.floor == 0 and inst.family in {"R4", "C0", "H0", "I0"}:
            groups.setdefault(inst.group_id, []).append(inst)
    best = 0.0
    for modules in groups.values():
        if len(modules) < 2:
            continue
        cx = mean(i.x for i in modules)
        cy = mean(i.y for i in modules)
        if any(abs(i.x - cx) <= i.w / 2 and abs(i.y - cy) <= i.d / 2 for i in modules):
            continue
        quadrants = {(i.x >= cx, i.y >= cy) for i in modules}
        distances = [math.hypot(i.x - cx, i.y - cy) for i in modules]
        scale = mean(distances)
        score = (len(quadrants) / 4) * min(1.0, len(modules) / 4)
        if 5 <= scale <= 25:
            best = max(best, score)
    return best


def evaluate_objectives_v41(ph: PhenotypeV4) -> ObjectiveVector:
    context = SiteContext.from_site(ph.site)
    by = {family: [i for i in ph.instances if i.family == family]
          for family in {i.family for i in ph.instances}}
    r4 = by.get("R4", [])
    care = by.get("B0", [])
    commons = by.get("C0", [])
    arrival = by.get("A0", [])
    public = arrival + by.get("K0", [])
    service = by.get("F0", []) + by.get("M0", [])
    private = r4 + by.get("I0", [])
    diag = math.hypot(ph.site.width_m, ph.site.height_m)

    care_dist = mean([_nearest(i, care) for i in r4]) if r4 and care else None
    care_response = _normalized_distance(care_dist, diag * 0.55)
    controlled = mean([i.zone == "controlled_care" for i in care]) if care else 0.0
    safeguarding = _clip(0.65 * care_response + 0.35 * controlled)

    domestic_depth = mean(context.depth_fraction((i.x, i.y)) for i in private) if private else 0.0
    visual_pairs = [(a, b) for a in public for b in private if _distance(a, b) < diag * 0.55]
    # Public-to-domestic visual exposure is a schematic straight sightline
    # proxy. Exact apertures, eye heights and screening remain to verify.
    sightline_exposure = 0
    for a, b in visual_pairs:
        if not any(_line_intersects_footprint((a.x, a.y), (b.x, b.y), o)
                   for o in ph.instances if o is not a and o is not b and o.floor == 0):
            sightline_exposure += 1
    exposure_frac = sightline_exposure / max(1, len(visual_pairs))
    privacy_violations = sum(context.depth_fraction((a.x, a.y)) >= context.depth_fraction((b.x, b.y))
                             for a in public for b in private)
    privacy_score = _clip(0.50 * domestic_depth + 0.30 * (1 - exposure_frac)
                          + 0.20 * (1 - privacy_violations / max(1, len(public) * len(private))))

    amenity_dist = mean([_nearest(i, commons) for i in r4]) if r4 and commons else None
    amenity_score = _normalized_distance(amenity_dist, diag * 0.55)
    community_frontage = mean(context.sample("community_interface_suitability", (i.x, i.y))
                              for i in public) if public else 0.0
    program_diversity = len([family for family in ("C0", "H0", "J0", "K0", "I0")
                             if by.get(family)]) / 5.0
    everyday_score = _clip(0.48 * amenity_score + 0.30 * community_frontage
                           + 0.22 * program_diversity)

    arrival_dist = mean(distance_to_arrival(ph.site, (i.x, i.y)) for i in arrival) if arrival else None
    entry_relation = _normalized_distance(arrival_dist, diag * 0.42)
    resident_route_m = mean([_nearest(i, commons) for i in r4]) if r4 and commons else None
    visitor_route_m = mean([_nearest(i, care) for i in arrival]) if arrival and care else None
    service_route_m = mean([_nearest(i, by.get("F0", [])) for i in by.get("M0", [])]) if by.get("M0") and by.get("F0") else None
    visitor_segments = [((a.x, a.y), (b.x, b.y)) for a in arrival for b in care]
    resident_segments = [((a.x, a.y), (b.x, b.y)) for a in r4 for b in commons]
    service_segments = [((a.x, a.y), (b.x, b.y)) for a in by.get("M0", []) for b in by.get("F0", [])]
    route_conflicts = (_line_crossings(visitor_segments, resident_segments)
                       + _line_crossings(service_segments, resident_segments))
    conflict_score = 1 / (1 + route_conflicts)
    service_access = [context.sample("service_access_attraction", (i.x, i.y)) for i in service]
    known_service = [value for value in service_access if value is not None]
    access_parts = [entry_relation, conflict_score,
                    _normalized_distance(service_route_m, diag * 0.5)]
    if known_service:
        access_parts.append(mean(known_service))
    access_score = mean(access_parts)

    environmental = [context.sample("environmental_exposure", (i.x, i.y)) for i in private]
    known_exposure = [value for value in environmental if value is not None]
    landscape_continuity = _open_continuity(ph)
    courtyard_quality = _courtyard_quality(ph)
    landscape_score = _clip(ph.landscape_frac / 0.65)
    orientation_daylight = mean(i.w / (i.w + i.d) for i in private) if private else 0.0
    site_parts = [entry_relation, domestic_depth, landscape_continuity,
                  landscape_score, courtyard_quality, orientation_daylight]
    if known_exposure:
        site_parts.append(1 - mean(known_exposure))
    site_score = mean(site_parts)

    stacked_area = sum(i.area for i in ph.instances if i.floor > 0)
    stacking_efficiency = stacked_area / ph.gfa if ph.gfa else 0.0
    reserve_capacity = ph.reserve_area / ph.site.area_m2
    phase1 = ph.phases[0] if ph.phases else {}
    phase_viability = 1.0 if phase1.get("residents", 0) >= 8 and any(i.family == "B0" and i.phase == 1 for i in ph.instances) else 0.0
    adaptability = _clip(0.35 * min(1.0, reserve_capacity / 0.20)
                        + 0.20 * min(1.0, stacking_efficiency / 0.25)
                        + 0.25 * phase_viability
                        + 0.20 * min(1.0, ph.unit_population.get("variational_ratio", 0) / 0.40))

    submetrics = {
        "care_response_distance_m": care_dist,
        "controlled_access_integrity": controlled,
        "sensitive_sightline_exposure_count": sightline_exposure,
        "sensitive_sightline_exposure_ratio": exposure_frac,
        "privacy_transition_violations": privacy_violations,
        "domestic_protection_depth": domestic_depth,
        "domestic_cluster_count": len(r4),
        "amenity_access_distance_m": amenity_dist,
        "visitor_route_length_m": visitor_route_m,
        "resident_route_length_m": resident_route_m,
        "service_route_length_m": service_route_m,
        "route_conflict_count": route_conflicts,
        "entry_relationship_distance_m": arrival_dist,
        "frontage_use_score": community_frontage,
        "service_access_attraction": mean(known_service) if known_service else None,
        "environmental_exposure": mean(known_exposure) if known_exposure else None,
        "landscape_continuity": landscape_continuity,
        "courtyard_open_space_quality": courtyard_quality,
        "orientation_daylight_proxy": orientation_daylight,
        "stacking_efficiency": stacking_efficiency,
        "reserve_capacity_fraction": reserve_capacity,
        "phase_viability": phase_viability,
        "nominal_room_capacity": ph.nominal_day_capacity,
        "concurrent_day_users": ph.day_users,
        "method_note": "Distances and sightlines are schematic plan proxies; contextual nuisance and service layers are excluded when unverified.",
    }
    ph.objective_submetrics = submetrics
    values = (safeguarding, privacy_score, everyday_score, access_score,
              site_score, adaptability)
    results = [ObjectiveResult(name, _clip(value), provenance="[DESIGN HYPOTHESIS]")
               for name, value in zip(OBJECTIVE_NAMES, values)]
    ph.stage_records.append({"stage": "fitness_evaluation",
                             "inputs": ["phenotype", "site_fields", "occupancy_allocation"],
                             "outputs": ["objective_vector", "objective_submetrics"],
                             "provenance": "[DESIGN HYPOTHESIS]",
                             "data": {r.name: r.value for r in results}})
    return ObjectiveVector(results, mean(r.value for r in results), len(results))
