"""V4.1 architectural phenotype construction from module populations.

This is the paper's population/packing/zoning/collision/filtration middle
layer adapted to an irregular architectural parcel. Every placement is a
deterministic consequence of the complete chromosome and site state.
"""
from __future__ import annotations

import hashlib
import math
from collections import Counter
from dataclasses import dataclass

import numpy as np

from .context_v41 import SiteContext, ZONE_ORDER, zone_at, zoning_state, target_depth
from .genotype_v4 import InstanceV4, PhenotypeV4
from .modules_v4 import MODULE_LIBRARY_V4, FAMILY_VARIANTS
from .program_v41 import allocate_concurrent_occupancy, module_record, population_summary, zone_for_family
from .site import Site, point_in_polygon, nearest_edge


FAMILIES = ("A0", "K0", "B0", "L0", "C0", "H0", "J0", "R4", "I0", "F0", "M0")
POP_BOUNDS = {"A0": (1, 2), "K0": (0, 2), "B0": (1, 2), "L0": (1, 3),
              "C0": (1, 2), "H0": (0, 2), "J0": (0, 2), "R4": (2, 8),
              "I0": (0, 2), "F0": (1, 2), "M0": (1, 2)}
SLOT_POOL = tuple((family, ordinal) for family in FAMILIES
                  for ordinal in range(POP_BOUNDS[family][1]))
HEADER = len(FAMILIES) + 5 + 4  # population, zone scales, seed/pattern/reserve/phases
PER_SLOT = 10  # variant,x,y,orientation,group,attachment,edge,connection,floor,zone-offset
N_GENES_V41 = HEADER + PER_SLOT * len(SLOT_POOL)
PATTERNS = ("detached", "linear", "courtyard", "wings", "mixed")
ATTACHMENTS = ("detached", "shared_edge", "linear", "courtyard", "wing")
EDGES = ("N", "E", "S", "W")
CONNECTIONS = ("threshold", "service", "porch", "circulation", "court")


def _stage(name: str, inputs: list[str], outputs: list[str], data: dict,
           provenance: str = "[DESIGN HYPOTHESIS]") -> dict:
    return {"stage": name, "inputs": inputs, "outputs": outputs,
            "provenance": provenance, "data": data}


def gene_bounds_v41(site: Site):
    lo = np.zeros(N_GENES_V41)
    hi = np.zeros(N_GENES_V41)
    is_int = np.zeros(N_GENES_V41, dtype=bool)
    for j, family in enumerate(FAMILIES):
        lo[j], hi[j] = POP_BOUNDS[family]
        is_int[j] = True
    offset = len(FAMILIES)
    lo[offset:offset + 5] = 0.1
    hi[offset:offset + 5] = 4.0
    lo[offset + 5], hi[offset + 5] = 0, 65535  # independent population seed
    lo[offset + 6], hi[offset + 6] = 0, len(PATTERNS) - 1
    lo[offset + 7], hi[offset + 7] = 0.02, 0.25  # reserved growth area fraction
    lo[offset + 8], hi[offset + 8] = 1, 4
    is_int[offset + 5:offset + 7] = True
    is_int[offset + 8] = True
    for slot, (family, _) in enumerate(SLOT_POOL):
        base = HEADER + slot * PER_SLOT
        lo[base], hi[base] = 0, len(FAMILY_VARIANTS[family]) - 1
        lo[base + 1], hi[base + 1] = 0, site.width_m
        lo[base + 2], hi[base + 2] = 0, site.height_m
        lo[base + 3:base + 9] = (0, 0, 0, 0, 0, 0)
        hi[base + 3:base + 9] = (3, 7, 4, 3, 4, 1)
        lo[base + 9], hi[base + 9] = -0.45, 0.45
        is_int[base] = True
        is_int[base + 3:base + 9] = True
    return lo, hi, is_int


def random_genome_v41(rng: np.random.Generator, site: Site) -> np.ndarray:
    lo, hi, is_int = gene_bounds_v41(site)
    genes = lo + (hi - lo) * rng.random(N_GENES_V41)
    genes[is_int] = np.round(genes[is_int])
    # Initial unit population is sampled explicitly, independent of the
    # spatial seed and the per-slot coordinates.
    for j, family in enumerate(FAMILIES):
        low, high = POP_BOUNDS[family]
        genes[j] = int(rng.integers(low, high + 1))
    pattern = PATTERNS[int(genes[len(FAMILIES) + 6])]
    group_for = {"A0": 0, "K0": 0, "B0": 0, "L0": 0,
                 "C0": 2, "H0": 2, "J0": 2,
                 "R4": 1, "I0": 1, "F0": 3, "M0": 3}
    connection_for = {"A0": "threshold", "K0": "circulation",
                      "B0": "threshold", "L0": "threshold",
                      "C0": "circulation", "H0": "circulation", "J0": "circulation",
                      "R4": "porch", "I0": "court", "F0": "service", "M0": "service"}
    for slot, (family, _) in enumerate(SLOT_POOL):
        base = HEADER + slot * PER_SLOT
        genes[base + 4] = group_for[family]
        genes[base + 5] = (0 if pattern == "detached" else
                           1 if pattern == "linear" else
                           3 if pattern == "courtyard" else
                           4 if pattern == "wings" else int(rng.integers(0, 5)))
        genes[base + 7] = CONNECTIONS.index(connection_for[family])
    return genes


def _orientation(mt, gene: float) -> int:
    return mt.allowed_rotations[int(gene) % len(mt.allowed_rotations)]


def _segments_cross(a, b, c, d) -> bool:
    def cross(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    ab1, ab2 = cross(a, b, c), cross(a, b, d)
    cd1, cd2 = cross(c, d, a), cross(c, d, b)
    return ab1 * ab2 < -1e-8 and cd1 * cd2 < -1e-8


def footprint_inside(x: float, y: float, w: float, d: float, site: Site) -> bool:
    """Full rectangle containment, including crossing a concave parcel edge."""
    corners = [(x - w / 2, y - d / 2), (x + w / 2, y - d / 2),
               (x + w / 2, y + d / 2), (x - w / 2, y + d / 2)]
    if not all(point_in_polygon(p, site.boundary_polygon) for p in corners):
        return False
    parcel = site.boundary_polygon
    for i in range(4):
        for j in range(len(parcel) - 1):
            if _segments_cross(corners[i], corners[(i + 1) % 4], parcel[j], parcel[j + 1]):
                return False
    return True


def intersection_area(a: InstanceV4, b: InstanceV4) -> float:
    left = max(a.x - a.w / 2, b.x - b.w / 2)
    right = min(a.x + a.w / 2, b.x + b.w / 2)
    bottom = max(a.y - a.d / 2, b.y - b.d / 2)
    top = min(a.y + a.d / 2, b.y + b.d / 2)
    return max(0.0, right - left) * max(0.0, top - bottom)


def shared_edge_length(a: InstanceV4, b: InstanceV4) -> float:
    x_gap = abs(a.x - b.x) - (a.w + b.w) / 2
    y_gap = abs(a.y - b.y) - (a.d + b.d) / 2
    if abs(x_gap) < 1e-5 and y_gap < -1e-5:
        return -y_gap
    if abs(y_gap) < 1e-5 and x_gap < -1e-5:
        return -x_gap
    return 0.0


def attachment_permitted(a: InstanceV4, b_family: str, connection: str) -> bool:
    pair = frozenset((a.family, b_family))
    grammar = {
        "threshold": {frozenset(("A0", "B0")), frozenset(("B0", "L0")),
                      frozenset(("L0", "C0")), frozenset(("L0", "R4"))},
        "service": {frozenset(("C0", "F0")), frozenset(("F0", "M0")),
                    frozenset(("J0", "F0"))},
        "porch": {frozenset(("R4", "R4")), frozenset(("R4", "C0")),
                  frozenset(("R4", "I0"))},
        "circulation": {frozenset(("H0", "C0")), frozenset(("J0", "C0")),
                        frozenset(("A0", "K0")), frozenset(("B0", "C0"))},
        "court": {frozenset(("R4", "R4")), frozenset(("R4", "C0")),
                  frozenset(("R4", "I0")), frozenset(("H0", "C0"))},
    }
    return pair in grammar[connection]


def intentional_shared_edge(a: InstanceV4, b: InstanceV4) -> bool:
    return (a.group_id == b.group_id
            and (a.attachment_mode != "detached" or b.attachment_mode != "detached")
            and any(attachment_permitted(a, b.family, connection)
                    for connection in {a.connection_type, b.connection_type}
                    if connection in CONNECTIONS))


def collision_gate(instances: list[InstanceV4]) -> dict:
    """Independent computational gate for same-floor unintended overlap."""
    illegal = []
    stacked = []
    shared = []
    for i, a in enumerate(instances):
        for b in instances[i + 1:]:
            overlap = intersection_area(a, b)
            if a.floor == b.floor:
                if overlap > 1e-6:
                    illegal.append({"a": a.instance_id or a.code, "b": b.instance_id or b.code,
                                    "floor": a.floor, "area_m2": round(overlap, 5)})
                elif shared_edge_length(a, b) > 0:
                    allowed = intentional_shared_edge(a, b)
                    shared.append({"a": a.instance_id or a.code, "b": b.instance_id or b.code,
                                   "length_m": round(shared_edge_length(a, b), 3),
                                   "intentional": allowed})
            elif overlap > 1e-6:
                stacked.append({"a": a.instance_id or a.code, "b": b.instance_id or b.code,
                                "overlap_m2": round(overlap, 5), "floors": [a.floor, b.floor]})
    return {"illegal_overlap_count": len(illegal),
            "illegal_overlap_area_m2": round(sum(x["area_m2"] for x in illegal), 5),
            "unpermitted_shared_edge_count": sum(not x["intentional"] for x in shared),
            "illegal_pairs": illegal, "stacked_footprint_pairs": stacked,
            "shared_edges": shared, "passed": not illegal and all(x["intentional"] for x in shared),
            "provenance": "[DESIGN HYPOTHESIS]"}


def _candidate_positions(target, w, d, placed, group, mode, edge, connection,
                         pattern, rng):
    positions = []
    anchors = [a for a in placed if a.group_id == group and a.floor == 0]
    if mode != "detached":
        for anchor in anchors:
            if not attachment_permitted(anchor, target[2], connection):
                continue
            gap = 4.0 if mode == "courtyard" else (2.0 if mode == "wing" else 0.0)
            if edge == "N":
                positions.append((anchor.x, anchor.y + (anchor.d + d) / 2 + gap, anchor))
            elif edge == "S":
                positions.append((anchor.x, anchor.y - (anchor.d + d) / 2 - gap, anchor))
            elif edge == "E":
                positions.append((anchor.x + (anchor.w + w) / 2 + gap, anchor.y, anchor))
            else:
                positions.append((anchor.x - (anchor.w + w) / 2 - gap, anchor.y, anchor))
    tx, ty = target[:2]
    positions.append((tx, ty, None))
    angles = np.arange(0, 2 * math.pi, math.pi / 4)
    phase = rng.uniform(0, 2 * math.pi)
    if pattern == "linear":
        angles = np.array((0, math.pi, math.pi / 8, math.pi + math.pi / 8,
                           math.pi / 2, 3 * math.pi / 2))
    elif pattern == "wings":
        angles = np.array((math.pi / 4, 3 * math.pi / 4, 5 * math.pi / 4,
                           7 * math.pi / 4, 0, math.pi))
    for radius in (5.0, 10.0, 16.0, 23.0, 31.0, 40.0, 50.0):
        for angle in angles + phase:
            positions.append((tx + radius * math.cos(angle),
                              ty + radius * math.sin(angle), None))
    return positions


def _candidate_score(inst, target, anchor, context, pattern):
    diag = math.hypot(context.site.width_m, context.site.height_m)
    score = math.hypot(inst.x - target[0], inst.y - target[1]) / diag
    if anchor is not None:
        score -= {"detached": 0.0, "linear": 0.65, "courtyard": 0.55,
                  "wings": 0.52, "mixed": 0.32}[pattern]
        if inst.attachment_mode == "shared_edge":
            score -= 0.12
    if inst.family in {"A0", "K0"}:
        score += 0.35 * (1 - context.sample("public_access_attraction", (inst.x, inst.y)))
    elif inst.family in {"R4", "I0"}:
        score += 0.25 * (1 - context.sample("domestic_protection_depth", (inst.x, inst.y)))
    elif inst.family in {"F0", "M0"}:
        value = context.sample("service_access_attraction", (inst.x, inst.y))
        if value is not None:
            score += 0.25 * (1 - value)
    exposure = context.sample("environmental_exposure", (inst.x, inst.y))
    if exposure is not None and inst.family in {"R4", "B0", "I0"}:
        score += 0.30 * exposure
    return score


def _build_instance(mt, slot, base, genes, site, floor, group, mode, edge, connection):
    rotation = _orientation(mt, genes[base + 3])
    w, d = mt.rotated_dimensions(rotation)
    inst = InstanceV4(mt.code, mt.family, 0.0, 0.0, w, d,
                      rotation=rotation, access_face=mt.access_faces[int(genes[base + 3]) % len(mt.access_faces)],
                      floor=floor, area=mt.area, privacy_level=mt.privacy_level,
                      capacity_residents=mt.capacity_residents,
                      capacity_day_users=mt.capacity_day_users,
                      capacity_staff=mt.capacity_staff,
                      nominal_room_capacity=mt.capacity_day_users,
                      instance_id=f"u{slot:02d}-{mt.code}", group_id=group,
                      attachment_mode=mode, shared_edge=edge,
                      connection_type=connection, target_zone=zone_for_family(mt.family))
    return inst


def usable_growth_reserve_area(site: Site, context: SiteContext,
                               instances: list[InstanceV4], cell: float = 5.0) -> float:
    """Largest connected vacant interior patch away from the arrival band."""
    cells = set()
    for yi in range(int(site.height_m / cell) + 1):
        for xi in range(int(site.width_m / cell) + 1):
            x, y = (xi + .5) * cell, (yi + .5) * cell
            if not point_in_polygon((x, y), site.boundary_polygon):
                continue
            if context.depth_fraction((x, y)) < .35:
                continue
            if any(inst.floor == 0 and abs(inst.x - x) < inst.w / 2 + cell / 2
                   and abs(inst.y - y) < inst.d / 2 + cell / 2 for inst in instances):
                continue
            cells.add((xi, yi))
    largest = 0
    while cells:
        queue = [cells.pop()]
        size = 1
        for current in queue:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                adjacent = (current[0] + dx, current[1] + dy)
                if adjacent in cells:
                    cells.remove(adjacent)
                    queue.append(adjacent)
                    size += 1
        largest = max(largest, size)
    return largest * cell * cell


def _place(inst, target, context, state, placed, pattern, rng, requested_floor):
    mt = MODULE_LIBRARY_V4[inst.code]
    if requested_floor == 1 and mt.stackable_above:
        supports = [p for p in placed if p.floor == 0 and p.group_id == inst.group_id
                    and MODULE_LIBRARY_V4[p.code].stackable_below
                    and p.w >= inst.w and p.d >= inst.d]
        supports.sort(key=lambda p: math.hypot(p.x - target[0], p.y - target[1]))
        for base in supports:
            trial = InstanceV4(**{**inst.__dict__, "x": base.x, "y": base.y, "floor": 1,
                                  "stack_pair_id": int(base.instance_id[1:3])})
            if any(intersection_area(trial, other) > 1e-6 for other in placed if other.floor == 1):
                continue
            trial.zone = zone_at(context, state, (trial.x, trial.y))
            return trial
    inst.floor = 0
    candidates = []
    for x, y, anchor in _candidate_positions(target, inst.w, inst.d, placed, inst.group_id,
                                              inst.attachment_mode, inst.shared_edge,
                                              inst.connection_type, pattern, rng):
        if not footprint_inside(x, y, inst.w, inst.d, context.site):
            continue
        zone = zone_at(context, state, (x, y))
        if inst.target_zone != "service" and zone != inst.target_zone:
            continue
        trial = InstanceV4(**{**inst.__dict__, "x": x, "y": y, "zone": zone})
        if any(intersection_area(trial, p) > 1e-6
               or (shared_edge_length(trial, p) > 1e-5 and not intentional_shared_edge(trial, p))
               for p in placed if p.floor == 0):
            continue
        candidates.append((_candidate_score(trial, target, anchor, context, pattern), trial))
    if not candidates:
        return None
    candidates.sort(key=lambda pair: pair[0])
    return candidates[0][1]


def decode_v41(genes: np.ndarray, site: Site, concurrent_day_users: int = 32,
               generation: int = 0, origin_seed: int | None = None) -> PhenotypeV4:
    genes = np.asarray(genes, dtype=float)
    if len(genes) != N_GENES_V41:
        raise ValueError(f"Expected {N_GENES_V41} genes, got {len(genes)}")
    context = SiteContext.from_site(site)
    digest = hashlib.sha256(genes.astype("<f8").tobytes()
                            + str(concurrent_day_users).encode("ascii")
                            + np.asarray(site.boundary_polygon, dtype="<f8").tobytes()).hexdigest()[:16]
    ph = PhenotypeV4(genotype_id=f"v41-{digest}", birth_generation=generation,
                     site=site, site_mode=site.mode, origin_seed=origin_seed,
                     genes=genes.copy())
    counts = {family: int(genes[j]) for j, family in enumerate(FAMILIES)}
    ph.population_seed = int(genes[len(FAMILIES) + 5])
    ph.packing_pattern = PATTERNS[int(genes[len(FAMILIES) + 6]) % len(PATTERNS)]
    reserve_fraction = float(genes[len(FAMILIES) + 7])
    phase_count = int(genes[len(FAMILIES) + 8])
    state = zoning_state(context, list(genes[len(FAMILIES):len(FAMILIES) + 5]))
    ph.zone_state = state
    ph.requested_unit_population = {"by_function": counts, "bounds": POP_BOUNDS,
                                    "population_seed": ph.population_seed}
    ph.stage_records.append(_stage("module_unit", ["function", "size", "modularity_category"],
                                   ["module_units"], {"catalogue_codes": len(MODULE_LIBRARY_V4)}))
    ph.stage_records.append(_stage("initial_unit_population", ["count_genes", "module_library"],
                                   ["requested_units"], {"by_function": counts, "bounds": POP_BOUNDS}))
    ph.stage_records.append(_stage("population_seed", ["seed_gene"], ["packing_rng"],
                                   {"value": ph.population_seed}))
    requested = []
    for slot, (family, ordinal) in enumerate(SLOT_POOL):
        if ordinal >= counts[family]:
            continue
        base = HEADER + slot * PER_SLOT
        variants = FAMILY_VARIANTS[family]
        code = variants[int(genes[base]) % len(variants)]
        requested.append((slot, base, MODULE_LIBRARY_V4[code]))
    requested_summary = Counter(mt.code for _, _, mt in requested)
    ph.requested_unit_population["by_variant"] = dict(sorted(requested_summary.items()))
    ph.requested_unit_population["by_modularity"] = dict(Counter(module_record(mt.code)["modularity_category"]
                                                          for _, _, mt in requested))
    specialized = sum(module_record(mt.code)["specialized_function"] for _, _, mt in requested)
    ph.requested_unit_population["specialized_function_population"] = specialized
    ph.requested_unit_population["specialized_function_ratio"] = specialized / len(requested) if requested else 0.0
    ph.requested_unit_population["modularity_ratios"] = {
        category: count / len(requested) if requested else 0.0
        for category, count in ph.requested_unit_population["by_modularity"].items()
    }
    ph.generated_units = len(requested)
    ph.stage_records.append(_stage("modularity_ratios", ["requested_units", "module_library"],
                                   ["requested_modularity_population"],
                                   {"by_modularity": ph.requested_unit_population["by_modularity"],
                                    "modularity_ratios": ph.requested_unit_population["modularity_ratios"],
                                    "specialized_function_ratio": ph.requested_unit_population["specialized_function_ratio"]}))
    rng = np.random.default_rng(ph.population_seed)
    placed = []
    filtered = []
    for slot, base, mt in requested:
        mode = ATTACHMENTS[int(genes[base + 5]) % len(ATTACHMENTS)]
        edge = EDGES[int(genes[base + 6]) % len(EDGES)]
        connection = CONNECTIONS[int(genes[base + 7]) % len(CONNECTIONS)]
        inst = _build_instance(mt, slot, base, genes, site, 0, int(genes[base + 4]), mode, edge, connection)
        raw = (float(genes[base + 1]), float(genes[base + 2]))
        desired = target_depth(state, inst.target_zone, float(genes[base + 9]))
        tx, ty = context.at_depth(raw, desired)
        placed_inst = _place(inst, (tx, ty, mt.family), context, state, placed,
                             ph.packing_pattern, rng, int(genes[base + 8]))
        if placed_inst is None:
            filtered.append({"instance_id": inst.instance_id, "code": inst.code,
                             "reason": "packing_failed_within_zone_and_parcel"})
            continue
        placed_inst.zone = zone_at(context, state, (placed_inst.x, placed_inst.y))
        corners = [(placed_inst.x + sx * placed_inst.w / 2,
                    placed_inst.y + sy * placed_inst.d / 2)
                   for sx in (-1, 1) for sy in (-1, 1)]
        placed_inst.distance_to_boundary = min(nearest_edge(p, site.boundary_polygon)[1] for p in corners)
        placed_inst.within_buildable = footprint_inside(placed_inst.x, placed_inst.y,
                                                        placed_inst.w, placed_inst.d, site)
        placed_inst.setback_compliant = placed_inst.distance_to_boundary >= max(site.setbacks_m.get("side", 3.0), site.setbacks_m.get("rear", 3.0))
        placed.append(placed_inst)
    ph.stage_records.append(_stage("architectural_packing_grouping",
                                   ["requested_units", "relationship_genes", "population_seed", "site_geometry", "zone_genes"],
                                   ["placed_units", "packing_pattern"],
                                   {"placed": len(placed), "pattern": ph.packing_pattern}))
    ph.stage_records.append(_stage("dynamic_zoning", ["zone_scale_genes", "site_geometry", "placed_units"],
                                   ["zone_boundaries", "zone_type", "zone_areas"], state))
    collision = collision_gate(placed)
    ph.collision_report = collision
    ph.stage_records.append(_stage("object_collision", ["placed_footprints", "floor", "attachment_grammar"],
                                   ["illegal_overlap_count", "collision_area"], collision))
    retained = []
    for inst in placed:
        if not inst.within_buildable:
            filtered.append({"instance_id": inst.instance_id, "code": inst.code, "reason": "outside_parcel"})
        elif inst.target_zone != "service" and inst.zone != inst.target_zone:
            filtered.append({"instance_id": inst.instance_id, "code": inst.code, "reason": "zone_incompatible"})
        else:
            retained.append(inst)
    ph.instances = retained
    ph.filtered_units = filtered
    ph.retained_units = len(retained)
    ph.stage_records.append(_stage("unit_filtration", ["placed_units", "collision_state", "zone_state"],
                                   ["retained_units", "filtered_units"],
                                   {"generated": ph.generated_units, "retained": ph.retained_units,
                                    "filtered": filtered}))
    ph.stage_records.append(_stage("site_external_references", ["site_context_layers", "retained_units"],
                                   ["active_spatial_fields"], context.field_manifest()))
    ph.unit_population = population_summary(retained)
    ph.zone_population = dict(Counter(i.target_zone for i in retained))
    ph.residents = sum(i.capacity_residents for i in retained)
    ph.nominal_day_capacity = sum(i.capacity_day_users for i in retained)
    ph.nominal_staff_capacity = sum(i.capacity_staff for i in retained)
    ph.occupancy_allocation = allocate_concurrent_occupancy(retained, concurrent_day_users)
    ph.day_users = ph.occupancy_allocation["allocated_concurrent_day_users"]
    ph.staff = min(ph.nominal_staff_capacity,
                   max(2, math.ceil(ph.residents / 5) + math.ceil(ph.day_users / 12)))
    ph.gfa = sum(i.area for i in retained)
    ph.footprint = sum(i.area for i in retained if i.floor == 0)
    ph.reserve_area = min(reserve_fraction * site.area_m2,
                          usable_growth_reserve_area(site, context, retained))
    ph.landscape_area = max(0.0, site.area_m2 - ph.footprint - ph.reserve_area)
    ph.landscape_frac = ph.landscape_area / site.area_m2
    ph.packing_utilization = ph.footprint / site.area_m2
    ph.floor_count = max((i.floor for i in retained), default=0) + 1
    ph.stacked_pairs = len(collision["stacked_footprint_pairs"])
    ph.boundary_violations = sum(not i.within_buildable for i in retained)
    ph.setback_violations = sum(not i.setback_compliant for i in retained)
    for index, inst in enumerate(retained):
        inst.phase = 1 if inst.family in {"A0", "B0", "R4"} else min(phase_count, 2 + index % max(1, phase_count - 1))
    ph.phases = [{"phase": p, "modules": sum(i.phase <= p for i in retained),
                  "gfa": sum(i.area for i in retained if i.phase <= p),
                  "residents": sum(i.capacity_residents for i in retained if i.phase <= p),
                  "day_users": ph.day_users if p == phase_count else 0}
                 for p in range(1, phase_count + 1)]
    ph.stage_records.append(_stage("architectural_phenotype",
                                   ["retained_units", "occupancy_scenario", "site_fields"],
                                   ["phenotype", "program_metrics", "spatial_metrics"],
                                   {"id": ph.genotype_id, "residents": ph.residents,
                                    "concurrent_day_users": ph.day_users,
                                    "nominal_room_capacity": ph.nominal_day_capacity,
                                    "gfa_m2": ph.gfa}))
    return ph
