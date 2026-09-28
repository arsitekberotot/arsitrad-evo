"""Site-aware genotype v4 — extended with rotation, access, growth, stacking genes.

Extends v3 fixed-length mixed real/integer vector with site-aware genes:
  - rotation per module (0°, 90°, 180°, 270°)
  - access face selection per module
  - growth direction preference
  - landscape allocation ratio
  - buffer depth
  - courtyard orientation
  - stackable pair assignment

Backward compatible: can decode to legacy v3 rectangle mode.

Provenance: [DESIGN HYPOTHESIS] for all gene-to-architecture mappings.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .site import (Site, SiteMode, point_in_polygon, nearest_edge,
                   setback_polygon)
from .modules_v4 import (
    ModuleTypeV4, MODULE_LIBRARY_V4, SizeClass, RotationPolicy,
    get_module_variant, allowed_rotations, ground_required_modules,
    v3_code_to_v4, FAMILY_VARIANTS, CANONICAL_VARIANT
)


# Gene indices for structural genes (v3 compatible)
N_GENE_STRUCT = 12  # v3 used 12 structural genes

# Additional v4 structural genes
V4_STRUCT_GENES = {
    "growth_direction": 0,      # 0=N, 1=E, 2=S, 3=W
    "landscape_ratio": 1,       # 0.0-1.0
    "buffer_depth": 2,          # metres
    "courtyard_orientation": 3, # 0=N, 1=E, 2=S, 3=W
    "phase_count": 4,           # 1-4
    "reserve_expansion": 5,     # 0.0-1.0
}

N_V4_STRUCT = len(V4_STRUCT_GENES)

# Per-module genes (v4 adds variant choice, rotation, access_face, stack_pair)
# v3 had: x, y (2 genes per module)
# v4 has: variant_choice, x, y, rotation, access_face, stack_pair (6 per slot)
N_GENES_PER_MODULE_V3 = 2
N_GENES_PER_MODULE_V4 = 5   # legacy alias (position block only)
N_GENES_PER_MODULE = 6      # v4.1: choice + x,y,rotation,access,stack

# ---------------------------------------------------------------------------
# CAPACITY-SCALABLE SLOT ARCHITECTURE [DESIGN HYPOTHESIS]
#
# v3 / early-v4 used a fixed 11-slot layout whose R4 slots were set to 0, which
# physically capped the module population and could never represent R4x8 (the
# 8..32-resident experimental stratum). We replace it with an explicit pool of
# slots sized to the largest experiment:
#   * 8 R4 slots   -> R4x1 .. R4x8  (4..32 residents), variant chosen per slot
#   * 1 slot each for the single-instance public/care/commons/... families
#   * 2 L0 slots   -> the threshold/transition family is allowed to repeat
# Total = 8 + 10 + 2 = 20 slots. A slot is *active* only if its structural
# count gene is > 0, so small populations simply leave trailing slots empty.
# ---------------------------------------------------------------------------
MAX_R4 = 8          # R4x1 .. R4x8 -> 4..32 residents (experimental strata)
R4_VARIANTS = ["R4-S", "R4-M", "R4-L"]
MAX_OTHER = 2       # upper bound for non-fixed count genes

# Single-instance slot per family (the fixed-position families). Their variant
# is normally the canonical [PA5 CORPUS] baseline; capacity experiments may
# widen `family_variants` to admit the S/L evidence-based variants.
FIXED_FAMILIES = ["A0", "B0", "C0", "H0", "J0", "K0", "I0", "F0", "M0"]
N_L0_SLOTS = 2

# Structural count-gene layout (first N_GENE_STRUCT genes):
#   [0] R4 count (0..MAX_R4)
#   [1] reserved (0)
#   [2] reserved (0)
#   [3] reserved (0)
#   [4] A0  [5] B0  [6] C0  [7] H0  [8] J0  [9] K0  [10] I0  [11] F0
# (M0 is forced present = 1; L0 activates both of its slots when desired.)
OTHER_STRUCT_INDEX = {"A0": 4, "B0": 5, "C0": 6, "H0": 7, "J0": 8,
                      "K0": 9, "I0": 10, "F0": 11}

# ---------------------------------------------------------------------------
# SLOT POOL — deterministic ordered list of (family, slot_ordinal).
# ---------------------------------------------------------------------------
SLOT_POOL: list = (
    [("R4", i) for i in range(MAX_R4)]
    + [("A0", 0), ("B0", 0), ("C0", 0), ("H0", 0), ("J0", 0),
       ("K0", 0), ("I0", 0), ("L0", 0), ("L0", 1), ("F0", 0), ("M0", 0)]
)
TOTAL_MODULE_SLOTS = len(SLOT_POOL)
N_POSITION_GENES = TOTAL_MODULE_SLOTS * N_GENES_PER_MODULE

# Total genotype length
N_GENES_V4 = N_GENE_STRUCT + N_V4_STRUCT + N_POSITION_GENES


@dataclass
class InstanceV4:
    """A placed module instance with site-aware attributes."""
    code: str                    # v4 module code (e.g. "R4-M")
    family: str                  # module family (e.g. "R4")
    x: float                     # centroid x
    y: float                     # centroid y
    w: float                     # width (after rotation)
    d: float                     # depth (after rotation)
    rotation: int = 0            # 0, 90, 180, 270
    access_face: str = "S"       # primary access edge
    stack_pair_id: int = -1      # -1 = not stacked, else pair index
    floor: int = 0               # 0 = ground
    phase: int = 1               # phase when this module activates
    
    # Site relationships
    distance_to_boundary: float = 0.0
    nearest_edge_orientation: str = ""
    setback_compliant: bool = True
    within_buildable: bool = True
    
    # Derived
    area: float = 0.0
    privacy_level: int = 0
    capacity_residents: int = 0
    capacity_day_users: int = 0
    capacity_staff: int = 0
    # V4.1 relationship state. Defaults keep the original V4 decoder usable.
    instance_id: str = ""
    group_id: int = -1
    attachment_mode: str = "detached"
    shared_edge: str = ""
    connection_type: str = ""
    zone: str = ""
    target_zone: str = ""
    nominal_room_capacity: int = 0


@dataclass
class PhenotypeV4:
    """Decoded spatial configuration with site awareness."""
    # Identity
    genotype_id: str = ""
    birth_generation: int = 0
    selected_generation: int | None = None
    
    # Site
    site: Optional[Site] = None
    site_mode: SiteMode = SiteMode.LEGACY_RECT
    
    # Program
    residents: int = 0
    day_users: int = 0
    staff: int = 0
    nominal_day_capacity: int = 0
    nominal_staff_capacity: int = 0
    occupancy_allocation: dict = field(default_factory=dict)
    
    # Instances
    instances: list[InstanceV4] = field(default_factory=list)
    
    # Metrics
    gfa: float = 0.0
    footprint: float = 0.0
    landscape_area: float = 0.0
    landscape_frac: float = 0.0
    reserve_area: float = 0.0
    
    # Stacking
    floor_count: int = 1
    stacked_pairs: int = 0
    
    # Site response
    boundary_violations: int = 0
    setback_violations: int = 0
    
    # Phaseability
    phases: list[dict] = field(default_factory=list)
    
    # Constraints (v3 compatible)
    feasible: bool = True
    must_shortfall: float = 0.0
    exposure_count: int = 0
    
    # Objectives (v3 compatible)
    objectives: np.ndarray = field(default_factory=lambda: np.zeros(9))
    
    # --- v4 GA bookkeeping (declared, not dynamically attached) -----------
    origin_seed: Optional[int] = None
    genes: np.ndarray = field(default_factory=lambda: np.zeros(0))
    cv: float = 0.0                       # total constraint violation
    rank: int = 0                         # Pareto rank (NSGA-II)
    crowding: float = 0.0                 # crowding distance (NSGA-II)
    constraint_report: object = None      # constraints_v4.ConstraintReport
    objective_vector: object = None       # objectives_v4.ObjectiveVector
    # V4.1 construction and analytical state.
    population_seed: int = 0
    requested_unit_population: dict = field(default_factory=dict)
    unit_population: dict = field(default_factory=dict)
    zone_state: dict = field(default_factory=dict)
    zone_population: dict = field(default_factory=dict)
    generated_units: int = 0
    retained_units: int = 0
    filtered_units: list[dict] = field(default_factory=list)
    collision_report: dict = field(default_factory=dict)
    packing_pattern: str = ""
    packing_utilization: float = 0.0
    objective_submetrics: dict = field(default_factory=dict)
    stage_records: list[dict] = field(default_factory=list)
    
    def get_modules_by_family(self, family: str) -> list[InstanceV4]:
        return [i for i in self.instances if i.family == family]
    
    def get_modules_by_phase(self, phase: int) -> list[InstanceV4]:
        return [i for i in self.instances if i.phase <= phase]
    
    def module_count(self, family: str) -> int:
        return len(self.get_modules_by_family(family))


def gene_bounds_v4(site: Site, fixed_program: bool = True) -> tuple:
    """Return (lower, upper, is_integer) bounds for the v4 genotype.

    fixed_program=True (default): the supporting programme (A0, B0, C0, F0, M0,
    L0) is held at its canonical presence so the search concentrates on the
    *residential population* (R4 count + variants) and site placement. Set
    fixed_program=False to also evolve those counts (wider search).
    """
    lo = np.zeros(N_GENES_V4)
    hi = np.zeros(N_GENES_V4)
    is_int = np.zeros(N_GENES_V4, dtype=bool)

    # --- structural count genes -------------------------------------------
    # [0] R4 count: the residential stratum (0..MAX_R4 -> 0..32 residents).
    lo[0] = 0
    hi[0] = MAX_R4
    is_int[0] = True
    # [1..3] reserved (legacy R4 S/M/L split, now handled by variant genes).
    lo[1:4] = 0
    hi[1:4] = 0
    is_int[1:4] = True
    # [4..11] supporting-programme counts.
    for fam, gi in OTHER_STRUCT_INDEX.items():
        is_int[gi] = True
        if fixed_program:
            # Presence fixed to the canonical baseline (A0,B0,C0,F0 present;
            # H0,J0,K0,I0 optional but present in the baseline corpus program).
            lo[gi] = 1
            hi[gi] = 1
        else:
            lo[gi] = 0
            hi[gi] = MAX_OTHER

    # --- v4 site-response structural genes --------------------------------
    idx = N_GENE_STRUCT
    for name, offset in V4_STRUCT_GENES.items():
        if name == "growth_direction":
            lo[idx] = 0; hi[idx] = 3; is_int[idx] = True
        elif name == "landscape_ratio":
            lo[idx] = 0.15; hi[idx] = 0.50
        elif name == "buffer_depth":
            lo[idx] = 2.0; hi[idx] = 10.0
        elif name == "courtyard_orientation":
            lo[idx] = 0; hi[idx] = 3; is_int[idx] = True
        elif name == "phase_count":
            lo[idx] = 1; hi[idx] = 4; is_int[idx] = True
        elif name == "reserve_expansion":
            lo[idx] = 0.0; hi[idx] = 0.3
        idx += 1

    # --- per-slot genes (choice + position/rotation/access/stack) ---------
    idx = N_GENE_STRUCT + N_V4_STRUCT
    for slot_idx, (fam, ordinal) in enumerate(SLOT_POOL):
        variants = FAMILY_VARIANTS.get(fam, [CANONICAL_VARIANT[fam]])
        n_var = max(1, len(variants))
        # variant choice gene
        lo[idx] = 0; hi[idx] = n_var - 1; is_int[idx] = True
        # x, y
        lo[idx + 1] = 0; hi[idx + 1] = site.width_m
        lo[idx + 2] = 0; hi[idx + 2] = site.height_m
        # rotation (0-3 -> 0/90/180/270; remapped to allowed rotations)
        lo[idx + 3] = 0; hi[idx + 3] = 3; is_int[idx + 3] = True
        # access_face (0-3 -> N/E/S/W; remapped to allowed faces)
        lo[idx + 4] = 0; hi[idx + 4] = 3; is_int[idx + 4] = True
        # stack_pair_id (-1 = not stacked, 0+ = pair index)
        lo[idx + 5] = -1; hi[idx + 5] = 10; is_int[idx + 5] = True
        idx += N_GENES_PER_MODULE

    return lo, hi, is_int


def decode_v4(genes: np.ndarray, site: Site, 
              genotype_id: str = "", generation: int = 0) -> PhenotypeV4:
    """Decode v4 genotype to phenotype with site awareness."""
    ph = PhenotypeV4(
        genotype_id=genotype_id,
        birth_generation=generation,
        site=site,
        site_mode=site.mode,
    )
    
    # --- structural count genes -------------------------------------------
    r4_count = int(genes[0])                       # 0..MAX_R4
    other_counts = {fam: int(genes[gi])
                    for fam, gi in OTHER_STRUCT_INDEX.items()}

    # --- v4 site-response structural genes --------------------------------
    idx = N_GENE_STRUCT
    growth_dir = int(genes[idx + V4_STRUCT_GENES["growth_direction"]])
    landscape_ratio = genes[idx + V4_STRUCT_GENES["landscape_ratio"]]
    buffer_depth = genes[idx + V4_STRUCT_GENES["buffer_depth"]]
    courtyard_orient = int(genes[idx + V4_STRUCT_GENES["courtyard_orientation"]])
    phase_count = int(genes[idx + V4_STRUCT_GENES["phase_count"]])
    reserve_expansion = genes[idx + V4_STRUCT_GENES["reserve_expansion"]]

    # --- decode the slot pool --------------------------------------------
    # Each slot has: variant_choice, x, y, rotation, access_face, stack_pair.
    # A slot is *active* only when its family's structural count admits it.
    gene_idx = N_GENE_STRUCT + N_V4_STRUCT
    instances: list[InstanceV4] = []
    r4_seen = 0
    l0_seen = 0

    for slot_idx, (fam, ordinal) in enumerate(SLOT_POOL):
        active = False
        if fam == "R4":
            active = r4_seen < r4_count
            r4_seen += 1
        elif fam == "L0":
            # L0 (threshold) is a transitional space; activate both slots in
            # the baseline so the public->domestic gradient is always present.
            active = True
            l0_seen += 1
        elif fam == "M0":
            active = True                    # maintenance/service always present
        else:
            active = other_counts.get(fam, 0) > 0

        if active:
            variants = FAMILY_VARIANTS.get(fam, [CANONICAL_VARIANT[fam]])
            choice = int(genes[gene_idx]) % max(1, len(variants))
            code = variants[choice]
            mt = MODULE_LIBRARY_V4[code]
            inst = _decode_instance(genes, gene_idx, mt, slot_idx, site,
                                    phase_count)
            instances.append(inst)

        gene_idx += N_GENES_PER_MODULE

    ph.instances = instances

    # --- metrics -----------------------------------------------------------
    ph.gfa = sum(i.area for i in instances)
    ph.footprint = sum(i.area for i in instances if i.floor == 0)
    ph.residents = sum(i.capacity_residents for i in instances)
    ph.day_users = sum(i.capacity_day_users for i in instances)
    ph.staff = sum(i.capacity_staff for i in instances)

    # Landscape
    ph.landscape_area = site.area_m2 - ph.footprint - (site.area_m2 * reserve_expansion)
    ph.landscape_frac = ph.landscape_area / site.area_m2 if site.area_m2 > 0 else 0

    # Stacking
    ph.floor_count = max(i.floor for i in instances) + 1 if instances else 1
    ph.stacked_pairs = len(set(i.stack_pair_id for i in instances if i.stack_pair_id >= 0))

    # Site validation
    ph.boundary_violations = sum(1 for i in instances if not i.within_buildable)
    ph.setback_violations = sum(1 for i in instances if not i.setback_compliant)

    # Phase assignment
    ph.phases = _assign_phases(instances, phase_count)

    return ph


def _required_setback(site: Site) -> float:
    """Site-derived minimum setback for module placement [DESIGN HYPOTHESIS].

    Uses the side/rear setback from site metadata (canonical real site), else
    a conservative default. Frontage/arrival band is handled separately by the
    access logic, so placement enforces the side/rear buffer here.
    """
    if site.mode == SiteMode.GEOJSON and site.setbacks_m:
        return max(
            float(site.setbacks_m.get("side", 3.0)),
            float(site.setbacks_m.get("rear", 3.0)),
        )
    return 3.0


def _repair_position(x: float, y: float, w: float, d: float,
                     site: Site) -> tuple[float, float]:
    """Project an out-of-bounds module centre into the real parcel boundary.

    Deterministic (pure function of x, y) so genotypes stay reproducible.
    Repairs against the TRUE boundary (robust: the polygon centroid always
    falls inside even for concave parcels). Setback buffer is enforced by the
    soft constraint/objective, not by hard placement, so the GA keeps a
    feasible placement manifold [DESIGN HYPOTHESIS].
    """
    boundary = site.boundary_polygon

    def _fits(cx: float, cy: float) -> bool:
        for ox, oy in ((0, 0), (w/2, d/2), (-w/2, d/2), (w/2, -d/2), (-w/2, -d/2)):
            if not point_in_polygon((cx + ox, cy + oy), boundary):
                return False
        return True

    if _fits(x, y):
        return x, y

    ccx, ccy = site.centroid

    # Shrink toward parcel centroid until the footprint fits.
    for t in (0.8, 0.6, 0.45, 0.3, 0.18, 0.08):
        nx = ccx + (x - ccx) * t
        ny = ccy + (y - ccy) * t
        if _fits(nx, ny):
            return nx, ny

    return ccx, ccy


def _decode_instance(genes: np.ndarray, gene_idx: int, mt: ModuleTypeV4,
                     slot_idx: int, site: Site, phase_count: int) -> InstanceV4:
    """Decode a single module instance from its slot's genes.

    Slot layout (N_GENES_PER_MODULE=6): [choice, x, y, rotation, access, stack].
    `choice` has already been consumed by the caller to select `mt`, so it is
    skipped here (gene_idx points at the slot start).
    """
    x = genes[gene_idx + 1]
    y = genes[gene_idx + 2]
    rotation_idx = int(genes[gene_idx + 3])
    access_idx = int(genes[gene_idx + 4])
    stack_pair = int(genes[gene_idx + 5])
    
    # Map rotation index to degrees
    rotations = mt.allowed_rotations
    if len(rotations) > 0:
        rotation = rotations[rotation_idx % len(rotations)]
    else:
        rotation = 0
    
    # Map access index to face
    faces = mt.access_faces
    if len(faces) > 0:
        access_face = faces[access_idx % len(faces)]
    else:
        access_face = "S"
    
    # Apply rotation to dimensions
    w, d = mt.rotated_dimensions(rotation)

    # --- Site-aware placement repair ---------------------------------------
    # On the REAL site, raw gene x/y span the bbox; project out-of-polygon
    # placements into the buildable band so the GA searches feasible space
    # rather than wasting evaluations on out-of-bounds positions.
    if site.mode == SiteMode.GEOJSON:
        x, y = _repair_position(x, y, w, d, site)

    # Create instance
    inst = InstanceV4(
        code=mt.code,
        family=mt.family,
        x=x, y=y,
        w=w, d=d,
        rotation=rotation,
        access_face=access_face,
        stack_pair_id=stack_pair if stack_pair >= 0 else -1,
        floor=0 if mt.ground_required else (1 if stack_pair >= 0 else 0),
        area=mt.area,
        privacy_level=mt.privacy_level,
        capacity_residents=mt.capacity_residents,
        capacity_day_users=mt.capacity_day_users,
        capacity_staff=mt.capacity_staff,
    )
    
    # Site validation — full FOOTPRINT must sit inside the real polygon and
    # respect site-derived setbacks, not just the module centre point.
    corner_offsets = [(-w/2, -d/2), (w/2, -d/2), (w/2, d/2), (-w/2, d/2)]
    corners = [(x + cx, y + cy) for cx, cy in corner_offsets]
    probe = [(x, y)] + corners

    if site.mode == SiteMode.GEOJSON:
        # centre + all four corners inside the real parcel boundary
        inst.within_buildable = all(
            point_in_polygon(p, site.boundary_polygon) for p in probe)

        # Site-derived setback: distance from the nearest corner to the
        # nearest boundary edge must satisfy the relevant site setback.
        req = _required_setback(site)
        min_corner_dist = min(
            nearest_edge(c, site.boundary_polygon)[1] for c in corners)
        edge_idx, dist = nearest_edge((x, y), site.boundary_polygon)
        inst.distance_to_boundary = min_corner_dist
        inst.nearest_edge_orientation = site.edges[edge_idx].orientation if edge_idx < len(site.edges) else ""
        inst.setback_compliant = min_corner_dist >= req
    else:
        # Legacy mode: simple bounds + centre check
        inst.within_buildable = (0 <= x <= site.width_m and 0 <= y <= site.height_m)
        inst.distance_to_boundary = min(x, y, site.width_m - x, site.height_m - y)
        inst.setback_compliant = inst.distance_to_boundary >= 3.0
    
    # Phase assignment (simple: R4 and care in phase 1, others distributed)
    if mt.family in ("R4", "B0", "A0"):
        inst.phase = 1
    elif mt.family in ("C0", "F0", "M0"):
        inst.phase = min(2, phase_count)
    else:
        inst.phase = min(3, phase_count)
    
    return inst


def _assign_phases(instances: list[InstanceV4], phase_count: int) -> list[dict]:
    """Assign modules to phases and compute phase metrics."""
    phases = []
    for p in range(1, phase_count + 1):
        phase_instances = [i for i in instances if i.phase <= p]
        phases.append({
            "phase": p,
            "modules": len(phase_instances),
            "gfa": sum(i.area for i in phase_instances),
            "residents": sum(i.capacity_residents for i in phase_instances),
            "day_users": sum(i.capacity_day_users for i in phase_instances),
            "families": list(set(i.family for i in phase_instances)),
        })
    return phases


def random_genome_v4(rng: np.random.Generator, site: Site,
                     fixed_program: bool = True) -> np.ndarray:
    """Generate a random v4 genotype within bounds."""
    lo, hi, is_int = gene_bounds_v4(site, fixed_program=fixed_program)
    genes = lo + (hi - lo) * rng.random(len(lo))
    genes[is_int] = np.round(genes[is_int])
    return genes


def encode_phase(genes: np.ndarray, phase: int) -> np.ndarray:
    """Mask genotype to only include modules active in given phase."""
    # This is a simplified encoding — full implementation would
    # decode, filter by phase, re-encode
    masked = genes.copy()
    # For now, just adjust phase_count structural gene
    idx = N_GENE_STRUCT + V4_STRUCT_GENES["phase_count"]
    masked[idx] = phase
    return masked


def validate_placement_v4(inst: InstanceV4, site: Site, 
                          min_setback: float = 3.0) -> dict:
    """Validate a module placement against site constraints."""
    issues = []
    
    if not inst.within_buildable:
        issues.append(f"Module {inst.code} at ({inst.x:.1f}, {inst.y:.1f}) outside buildable area")
    
    if not inst.setback_compliant:
        issues.append(f"Module {inst.code} setback violation: {inst.distance_to_boundary:.1f}m < {min_setback}m")
    
    if inst.floor > 0 and inst.family in ("R4", "A0", "B0", "C0"):
        # These should generally be on ground [DH]
        issues.append(f"Module {inst.code} on floor {inst.floor} but family {inst.family} prefers ground")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "provenance": "[DESIGN HYPOTHESIS]",
    }


# Backward compatibility: decode v3 genotype using v4 decoder
def decode_v3_compat(genes: np.ndarray, site: Site,
                     genotype_id: str = "", generation: int = 0) -> PhenotypeV4:
    """Decode a legacy v3-length genotype through the v4 slot decoder.

    This path exists ONLY to keep the legacy 90 x 61.5 m rectangular frame as a
    regression/test fixture (see the V4 goal). It reconstructs a v4 genotype:
    the v3 structural counts are preserved, each v3 (x, y) position is mapped
    onto the matching v4 slot in SLOT_POOL order, and the new v4 genes
    (variant choice -> canonical baseline, rotation, access, stack, site
    response) are filled with deterministic defaults so results stay
    reproducible. No site fabrication occurs — all v4 defaults are neutral.
    """
    padded = np.zeros(N_GENES_V4)

    # --- structural counts -------------------------------------------------
    # v3 genes[0]=R4 count, genes[1..3]=0 (legacy S/M/L split unused),
    # genes[4..11]=A0..F0 counts in the same order as OTHER_STRUCT_INDEX.
    n_struct = min(N_GENE_STRUCT, len(genes))
    padded[:n_struct] = genes[:n_struct]
    # Collapse any legacy per-variant R4 split (genes 0..2) into one R4 count.
    if len(genes) >= 3:
        r4_total = int(genes[0]) + int(genes[1]) + int(genes[2])
        padded[0] = min(r4_total, MAX_R4)
        padded[1:4] = 0

    # --- v4 site-response defaults (neutral, deterministic) ---------------
    idx = N_GENE_STRUCT
    padded[idx + V4_STRUCT_GENES["growth_direction"]] = 1      # E
    padded[idx + V4_STRUCT_GENES["landscape_ratio"]] = 0.30
    padded[idx + V4_STRUCT_GENES["buffer_depth"]] = 5.0
    padded[idx + V4_STRUCT_GENES["courtyard_orientation"]] = 0  # N
    padded[idx + V4_STRUCT_GENES["phase_count"]] = 4
    padded[idx + V4_STRUCT_GENES["reserve_expansion"]] = 0.15

    # --- slot genes ---------------------------------------------------------
    # v3 carried 2 genes (x, y) per module in the same family order as
    # SLOT_POOL. Map them onto the v4 slot layout, filling v4-only genes.
    v3_pos = genes[N_GENE_STRUCT:] if len(genes) > N_GENE_STRUCT else np.zeros(0)
    v3_slots = len(v3_pos) // N_GENES_PER_MODULE_V3
    for i, (fam, ordinal) in enumerate(SLOT_POOL):
        slot_base = N_GENE_STRUCT + N_V4_STRUCT + i * N_GENES_PER_MODULE
        # variant choice -> canonical baseline (index of CANONICAL_VARIANT)
        variants = FAMILY_VARIANTS.get(fam, [CANONICAL_VARIANT[fam]])
        canon = CANONICAL_VARIANT.get(fam, variants[0])
        padded[slot_base + 0] = variants.index(canon) if canon in variants else 0
        # x, y from v3 if available, else a neutral interior point
        if i < v3_slots:
            vx = v3_pos[i * N_GENES_PER_MODULE_V3]
            vy = v3_pos[i * N_GENES_PER_MODULE_V3 + 1]
        else:
            vx, vy = site.width_m / 2.0, site.height_m / 2.0
        padded[slot_base + 1] = vx
        padded[slot_base + 2] = vy
        padded[slot_base + 3] = 0      # rotation index 0
        padded[slot_base + 4] = 2      # access index -> S (south)
        padded[slot_base + 5] = -1     # not stacked

    return decode_v4(padded, site, genotype_id, generation)
