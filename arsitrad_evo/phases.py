"""Phaseability and growth v4 — explicit staged growth representation.

Every chromosome carries a phase mask and growth/reserve capacity.
Decodes full development plus partial phase states.

Provenance: [DESIGN HYPOTHESIS] for all phase assignments.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .genotype_v4 import PhenotypeV4, InstanceV4, N_GENE_STRUCT, V4_STRUCT_GENES


@dataclass
class PhaseRequirement:
    """Functional requirements for a phase."""
    phase: int
    must_have_families: list[str] = field(default_factory=list)
    min_residents: int = 0
    min_day_users: int = 0
    min_gfa: float = 0.0
    description: str = ""


@dataclass
class PhaseCheck:
    """Result of phase feasibility check."""
    phase: int
    feasible: bool
    shortfall_residents: float = 0.0
    shortfall_day_users: float = 0.0
    shortfall_gfa: float = 0.0
    missing_families: list[str] = field(default_factory=list)
    provenance: str = "[DESIGN HYPOTHESIS]"


@dataclass
class GrowthModel:
    """Growth and phasing model for a phenotype."""
    phase_count: int
    phases: list[dict] = field(default_factory=list)
    reserve_area: float = 0.0
    reserve_fraction: float = 0.0
    expansion_directions: list[str] = field(default_factory=list)
    infill_sites: list[tuple[float, float]] = field(default_factory=list)
    future_module_slots: int = 0
    phase_feasibility: list[PhaseCheck] = field(default_factory=list)
    provenance: str = "[DESIGN HYPOTHESIS]"


# Phase requirements [DH]
PHASE_REQUIREMENTS = [
    PhaseRequirement(
        phase=1,
        must_have_families=["R4", "A0", "B0"],
        min_residents=8,
        min_day_users=10,
        min_gfa=200.0,
        description="Safe arrival + minimal liveability"
    ),
    PhaseRequirement(
        phase=2,
        must_have_families=["R4", "C0", "F0"],
        min_residents=16,
        min_day_users=20,
        min_gfa=400.0,
        description="Stabilisation + care capacity"
    ),
    PhaseRequirement(
        phase=3,
        must_have_families=["H0", "J0"],
        min_residents=24,
        min_day_users=30,
        min_gfa=600.0,
        description="Learning + livelihood"
    ),
    PhaseRequirement(
        phase=4,
        must_have_families=["K0", "I0"],
        min_residents=32,
        min_day_users=40,
        min_gfa=800.0,
        description="Community + reflection + maturity"
    ),
]


def decode_phases(ph: PhenotypeV4, genes: np.ndarray) -> GrowthModel:
    """Decode phase information from genotype and phenotype."""
    idx = N_GENE_STRUCT
    phase_count = int(genes[idx + V4_STRUCT_GENES["phase_count"]])
    reserve_fraction = genes[idx + V4_STRUCT_GENES["reserve_expansion"]]
    
    site = ph.site
    reserve_area = site.area_m2 * reserve_fraction if site else 0.0
    
    # Group instances by phase
    phase_instances = {}
    for inst in ph.instances:
        if inst.phase not in phase_instances:
            phase_instances[inst.phase] = []
        phase_instances[inst.phase].append(inst)
    
    # Build phase descriptions
    phases = []
    for p in range(1, phase_count + 1):
        insts = phase_instances.get(p, [])
        phases.append({
            "phase": p,
            "modules": len(insts),
            "gfa": sum(i.area for i in insts),
            "residents": sum(i.capacity_residents for i in insts),
            "day_users": sum(i.capacity_day_users for i in insts),
            "families": list(set(i.family for i in insts)),
            "cumulative_residents": sum(
                i.capacity_residents for i in ph.instances if i.phase <= p
            ),
            "cumulative_gfa": sum(
                i.area for i in ph.instances if i.phase <= p
            ),
        })
    
    # Check phase feasibility
    checks = []
    for req in PHASE_REQUIREMENTS:
        if req.phase > phase_count:
            break
        check = check_phase_feasibility(ph, req.phase)
        checks.append(check)
    
    # Find expansion directions and infill sites
    expansion_dirs = _find_expansion_directions(ph)
    infill_sites = _find_infill_sites(ph)
    
    return GrowthModel(
        phase_count=phase_count,
        phases=phases,
        reserve_area=reserve_area,
        reserve_fraction=reserve_fraction,
        expansion_directions=expansion_dirs,
        infill_sites=infill_sites,
        future_module_slots=int(reserve_area / 50.0),  # rough: 50m² per module
        phase_feasibility=checks,
    )


def check_phase_feasibility(ph: PhenotypeV4, phase: int) -> PhaseCheck:
    """Check if a phase is functionally feasible."""
    req = next((r for r in PHASE_REQUIREMENTS if r.phase == phase), None)
    if req is None:
        return PhaseCheck(phase=phase, feasible=True)
    
    # Get all instances up to this phase
    insts = [i for i in ph.instances if i.phase <= phase]
    
    # Check must-have families
    present_families = set(i.family for i in insts)
    missing = [f for f in req.must_have_families if f not in present_families]
    
    # Check capacity
    total_residents = sum(i.capacity_residents for i in insts)
    total_day = sum(i.capacity_day_users for i in insts)
    total_gfa = sum(i.area for i in insts)
    
    shortfall_res = max(0, req.min_residents - total_residents)
    shortfall_day = max(0, req.min_day_users - total_day)
    shortfall_gfa = max(0, req.min_gfa - total_gfa)
    
    feasible = (len(missing) == 0 and shortfall_res == 0 and 
                shortfall_day == 0 and shortfall_gfa == 0)
    
    return PhaseCheck(
        phase=phase,
        feasible=feasible,
        shortfall_residents=shortfall_res,
        shortfall_day_users=shortfall_day,
        shortfall_gfa=shortfall_gfa,
        missing_families=missing,
    )


def _find_expansion_directions(ph: PhenotypeV4) -> list[str]:
    """Find directions where site can expand."""
    site = ph.site
    if not site or site.mode.value == "legacy_rect":
        return ["E", "S"]  # default for rectangle
    
    directions = []
    
    # Check each edge for available space
    for edge in site.edges:
        # Simplified: if edge length > 20m, it's a potential expansion edge
        if edge.length_m > 20:
            directions.append(edge.orientation)
    
    return directions if directions else ["N", "E", "S", "W"]


def _find_infill_sites(ph: PhenotypeV4) -> list[tuple[float, float]]:
    """Find potential infill sites (gaps between modules)."""
    site = ph.site
    if not site:
        return []
    
    sites = []
    
    # Check gaps between modules
    for i, m1 in enumerate(ph.instances):
        for m2 in ph.instances[i+1:]:
            # Check if there's space between them
            gap_x = abs(m1.x - m2.x) - (m1.w + m2.w) / 2
            gap_y = abs(m1.y - m2.y) - (m1.d + m2.d) / 2
            
            if gap_x > 5 or gap_y > 5:  # potential infill if gap > 5m
                mid_x = (m1.x + m2.x) / 2
                mid_y = (m1.y + m2.y) / 2
                sites.append((mid_x, mid_y))
    
    return sites[:5]  # limit to 5 sites


def required_modules_for_phase(phase: int) -> list[str]:
    """Get required module families for a phase."""
    req = next((r for r in PHASE_REQUIREMENTS if r.phase == phase), None)
    return req.must_have_families if req else []


def phase_capacity(ph: PhenotypeV4, phase: int) -> dict:
    """Get capacity metrics for a phase."""
    insts = [i for i in ph.instances if i.phase <= phase]
    return {
        "residents": sum(i.capacity_residents for i in insts),
        "day_users": sum(i.capacity_day_users for i in insts),
        "staff": sum(i.capacity_staff for i in insts),
        "gfa": sum(i.area for i in insts),
        "modules": len(insts),
        "families": list(set(i.family for i in insts)),
    }


def encode_phase_mask(genes: np.ndarray, phase: int) -> np.ndarray:
    """Encode genotype to only express modules active in given phase."""
    masked = genes.copy()
    
    # Decode to find which instances are active
    from .genotype_v4 import decode_v4, create_legacy_site
    site = create_legacy_site()
    ph = decode_v4(genes, site)
    
    # Zero out genes for inactive instances
    # This is a simplified approach — full implementation would
    # precisely map gene indices to instances
    idx = N_GENE_STRUCT + len(V4_STRUCT_GENES)
    for i, inst in enumerate(ph.instances):
        if inst.phase > phase:
            # Zero out position genes for this instance
            pos = idx + i * 5  # N_GENES_PER_MODULE_V4
            if pos + 4 < len(masked):
                masked[pos:pos+5] = 0
    
    return masked


def phasing_score(ph: PhenotypeV4) -> float:
    """Score phaseability of a phenotype (0-1).
    
    Higher = better phased growth with viable intermediate states.
    """
    if not ph.phases:
        return 0.0
    
    score = 0.0
    
    # Check each phase is feasible
    feasible_phases = sum(1 for p in ph.phases 
                         if check_phase_feasibility(ph, p["phase"]).feasible)
    score += (feasible_phases / len(ph.phases)) * 0.5
    
    # Check resident growth is monotonic
    residents = [p["residents"] for p in ph.phases]
    if residents == sorted(residents):
        score += 0.3
    
    # Check no phase has too many modules (spread)
    max_modules = max(p["modules"] for p in ph.phases)
    if max_modules <= 8:
        score += 0.2
    
    return min(1.0, score)
