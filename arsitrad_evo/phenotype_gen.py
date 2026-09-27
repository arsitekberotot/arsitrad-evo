"""Spatial Phenotype Generator — converts a selected genotype (abstract module
rectangles) into a READABLE but still SCHEMATIC architectural prototype.

This is NOT finished architecture. Each placed module is expanded into a small
internal DIAGRAMMATIC kit-of-parts grounded in the PA5 corpus, with module
orientation, entrance/connection anchors, circulation skeletons, privacy
gradients, landscape/courtyard zones, stacking relationships, building grouping,
threshold sequences, and protected/public/service interfaces.

PROVENANCE DISCIPLINE (enforced): every internal component and connection is
tagged  [PA5 CORPUS] | [DESIGN HYPOTHESIS] | [TO VERIFY].  The renderer never
fabricates detailed room dimensions, structural systems, site precision, or
safeguarding requirements that are not yet supported: internal parts are drawn
as labelled zones with RELATIVE positions inside the module rectangle, sized
from corpus module areas only. Where a fact is not supported, it is omitted and
recorded in the prototype's `to_verify` list.

Public API:
    build_prototype(ph, candidate_label=None, rep_index=None, seed=None)
        -> Prototype (dataclass; fully serialisable via .to_dict())
    render_suite(proto, outdir)  -> writes 12 schematic diagnostics + JSON
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
from dataclasses import dataclass, field, asdict
import heapq
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, Circle, Polygon
from matplotlib.lines import Line2D

from .genotype import Phenotype, Instance
from .modules import (MODULES, relation, MUST, NEAR, SCREENED, AVOID, PROHIBITED,
                      PRIVACY, PUB, CTRL, SHR, DOM, PER)
from .objectives import OBJECTIVES, evaluate_objectives
from .analyze import genotype_id
from .constraints import evaluate_constraints
from . import config as C

OBJ_NAMES = [n for n, _ in OBJECTIVES]

# ---------------------------------------------------------------------------
# Provenance tags
# ---------------------------------------------------------------------------
CORPUS, HYP, VERIFY = "[PA5 CORPUS]", "[DESIGN HYPOTHESIS]", "[TO VERIFY]"

# ---------------------------------------------------------------------------
# Internal kit-of-parts per module code.
# Each part: (name, rel_x, rel_y, rel_w, rel_h, privacy_index, provenance, note)
#   rel_* are FRACTIONS of the module rect (0..1), origin at module lower-left.
# These are DIAGRAMMATIC zones, not rooms with dimensions. Areas of parts are
# deliberately NOT stated (would fabricate unsupported room dimensions).
# ---------------------------------------------------------------------------
KIT: dict[str, list[tuple]] = {
    "R4": [  # Domestic Cluster [PA5 CORPUS]
        ("personal territory", 0.05, 0.45, 0.42, 0.50, PER, CORPUS, "resident private rooms"),
        ("shared domestic",    0.53, 0.45, 0.42, 0.50, DOM, CORPUS, "living / dining"),
        ("WASH",               0.05, 0.08, 0.30, 0.30, PER, HYP,   "hygiene cluster"),
        ("retreat / porch",    0.42, 0.02, 0.53, 0.26, DOM, CORPUS, "controlled threshold to landscape"),
        ("connection point",   0.47, 0.30, 0.06, 0.12, DOM, VERIFY, "controlled link to C0/care"),
    ],
    "B0": [  # Care & Safeguarding [PA5 CORPUS]
        ("intake",             0.05, 0.55, 0.28, 0.38, CTRL, CORPUS, "arrival / admission"),
        ("counselling",        0.38, 0.55, 0.28, 0.38, CTRL, CORPUS, "therapeutic rooms"),
        ("safeguarding",       0.70, 0.55, 0.26, 0.38, PER,  CORPUS, "protected records / response"),
        ("care response",      0.05, 0.10, 0.45, 0.36, CTRL, CORPUS, "rapid reach to R4"),
        ("staff control",      0.55, 0.10, 0.40, 0.36, CTRL, HYP,   "observation point"),
    ],
    "C0": [  # Everyday Commons [PA5 CORPUS]
        ("shared kitchen",     0.05, 0.50, 0.30, 0.42, SHR, CORPUS, "communal cooking"),
        ("dining / gathering", 0.38, 0.50, 0.34, 0.42, SHR, CORPUS, "shared meals"),
        ("everyday activity",  0.74, 0.50, 0.22, 0.42, SHR, HYP,   "laundry / workshop"),
        ("covered terrace",    0.05, 0.08, 0.55, 0.34, SHR, CORPUS, "outdoor everyday life"),
        ("commons threshold",  0.62, 0.08, 0.33, 0.34, SHR, VERIFY, "link to R4 / landscape"),
    ],
    "A0": [  # Civic Threshold [PA5 CORPUS]
        ("public forecourt",   0.05, 0.55, 0.50, 0.40, PUB,  CORPUS, "arrival from street"),
        ("controlled gate",    0.60, 0.55, 0.35, 0.40, CTRL, CORPUS, "legitimate public->private"),
        ("waiting / lobby",    0.05, 0.10, 0.45, 0.38, CTRL, HYP,   "visitor holding"),
        ("threshold marker",   0.55, 0.10, 0.40, 0.38, CTRL, VERIFY, "sequence node"),
    ],
    "E0": [  # Staff Base [PA5 CORPUS]
        ("staff room",         0.05, 0.50, 0.45, 0.42, CTRL, CORPUS, "care team base"),
        ("handover / admin",   0.55, 0.50, 0.40, 0.42, CTRL, HYP,   "shift handover"),
        ("rapid response",     0.05, 0.08, 0.55, 0.34, CTRL, CORPUS, "direct reach to R4"),
        ("service lock",       0.65, 0.08, 0.30, 0.34, CTRL, VERIFY, "staff-only access"),
    ],
    "F0": [  # Service Edge [PA5 CORPUS]
        ("delivery / loading", 0.05, 0.55, 0.45, 0.40, CTRL, CORPUS, "goods arrival"),
        ("storage",            0.55, 0.55, 0.40, 0.40, CTRL, HYP,   "supplies"),
        ("waste / utility",    0.05, 0.10, 0.45, 0.38, CTRL, CORPUS, "back-of-house"),
        ("service yard",       0.55, 0.10, 0.40, 0.38, CTRL, VERIFY, "independent service access"),
    ],
    "M0": [  # Technical Commons [PA5 CORPUS]
        ("plant / technical",  0.05, 0.50, 0.55, 0.42, CTRL, CORPUS, "building services"),
        ("workshop",           0.65, 0.50, 0.30, 0.42, SHR,  HYP,   "maintenance / making"),
        ("technical yard",     0.05, 0.08, 0.55, 0.34, CTRL, VERIFY, "linked to F0 (MUST)"),
    ],
    "H0": [  # Learning House [PA5 CORPUS]
        ("learning studio",    0.05, 0.50, 0.50, 0.42, SHR,  CORPUS, "education / skills"),
        ("quiet study",        0.60, 0.50, 0.35, 0.42, SHR,  HYP,   "focused learning"),
        ("learning court",     0.05, 0.08, 0.55, 0.34, SHR,  CORPUS, "outdoor learning"),
        ("teaching threshold", 0.65, 0.08, 0.30, 0.34, SHR,  VERIFY, "controlled public link"),
    ],
    "I0": [  # Reflection Pavilion [PA5 CORPUS]
        ("reflection space",   0.10, 0.40, 0.80, 0.50, SHR,  CORPUS, "contemplation / quiet"),
        ("garden niche",       0.10, 0.05, 0.80, 0.28, SHR,  HYP,   "landscape immersion"),
    ],
    "J0": [  # Livelihood House [PA5 CORPUS]
        ("workshop / making",  0.05, 0.50, 0.50, 0.42, SHR,  CORPUS, "vocational production"),
        ("enterprise front",   0.60, 0.50, 0.35, 0.42, CTRL, CORPUS, "controlled public-facing work"),
        ("livelihood yard",    0.05, 0.08, 0.55, 0.34, SHR,  HYP,   "outdoor work / display"),
        ("sales threshold",    0.65, 0.08, 0.30, 0.34, CTRL, VERIFY, "public exchange point"),
    ],
    "K0": [  # Community House [PA5 CORPUS]
        ("community hall",     0.05, 0.50, 0.55, 0.42, PUB,  CORPUS, "neighbourhood gathering"),
        ("community kitchen",  0.65, 0.50, 0.30, 0.42, SHR,  HYP,   "shared events"),
        ("public forecourt",   0.05, 0.08, 0.55, 0.34, PUB,  CORPUS, "open arrival"),
        ("safeguarded link",   0.65, 0.08, 0.30, 0.34, CTRL, VERIFY, "controlled link into community"),
    ],
    "L0": [  # Transition House [PA5 CORPUS]
        ("transition unit",    0.05, 0.50, 0.45, 0.42, CTRL, CORPUS, "move-on / step-down"),
        ("independence studio",0.55, 0.50, 0.40, 0.42, DOM,  HYP,   "semi-autonomous living"),
        ("reintegration court",0.05, 0.08, 0.55, 0.34, CTRL, CORPUS, "gradual public contact"),
        ("care link",          0.65, 0.08, 0.30, 0.34, CTRL, VERIFY, "support reach (MUST to B0)"),
    ],
}

_PRIV_NAME = {0: "PUBLIC", 1: "CONTROLLED", 2: "SHARED", 3: "DOMESTIC", 4: "PERSONAL"}
_PRIV_COLOR = {0: "#38bdf8", 1: "#a78bfa", 2: "#4ade80", 3: "#fbbf24", 4: "#fb7185"}
_MOD_COLOR = {"A0": "#7dd3fc", "B0": "#c4b5fd", "C0": "#86efac", "R4": "#fcd34d",
              "E0": "#c4b5fd", "F0": "#cbd5e1", "M0": "#94a3b8", "H0": "#6ee7b7",
              "I0": "#a7f3d0", "J0": "#fdba74", "K0": "#f9a8d4", "L0": "#ddd6fe"}
_INTERFACE_COLOR = {"public": "#38bdf8", "protected": "#fb7185", "service": "#94a3b8"}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class Part:
    name: str; x: float; y: float; w: float; d: float
    privacy: int; provenance: str; note: str
    floor: int = 1


@dataclass
class ModuleNode:
    inst_id: int; code: str; name: str
    x: float; y: float; w: float; d: float
    floors: int; privacy: int; orientation: str
    entrance_anchor: tuple; connection_anchors: list
    interface: str                      # public | protected | service | domestic
    parts: list = field(default_factory=list)   # list[Part]
    spatial_role: str = ""
    faces: dict = field(default_factory=dict)
    access_points: dict = field(default_factory=dict)
    access_edges: dict = field(default_factory=dict)
    grammar_rotation_degrees: int = 0
    internal_paths: list = field(default_factory=list)
    physical_rotation_degrees: int = 0
    quarter_turn_feasible: bool = False


@dataclass
class Connection:
    a_id: int; b_id: int; a_code: str; b_code: str
    kind: str; provenance: str; circulations: list


@dataclass
class Sightline:
    """Direct visual-exposure check between a private residential module and a
    public-facing / safeguarding-sensitive module. Diagrammatic: uses the
    straight segment between module rectangles and reports whether intervening
    built mass screens it. NOT a regulatory sightline study."""
    from_id: int; from_code: str; to_id: int; to_code: str
    relation: str                 # PROHIBITED | safeguarding-sensitive
    distance: float
    exposed: bool                 # True = direct unobstructed segment
    screened_by: list             # module codes lying on the segment
    provenance: str
    tested_rays: int = 0
    visible_rays: int = 0
    exposure_ratio: float = 0.0


@dataclass
class OpenSpace:
    """Open-space / landscape zone classified by DEGREE OF ENCLOSURE (schematic):
      3-4 enclosing sides -> COURTYARD
      2 enclosing sides    -> POCKET COURT / THRESHOLD EDGE
      0-1 enclosing sides  -> OPEN LANDSCAPE
    Explicitly diagrammatic, not a surveyed open space."""
    cx: float; cy: float; area_cells: int; enclosure: int
    space_type: str; provenance: str; area_m2: float = 0.0


@dataclass
class Prototype:
    candidate: str; rep_index: int; seed: object; program: str
    site_w: float; site_h: float
    residents: int; day_users: int; gfa: float; footprint: float
    landscape_frac: float; landscape_area: float
    modules: list = field(default_factory=list)       # list[ModuleNode]
    connections: list = field(default_factory=list)   # list[Connection]
    sightlines: list = field(default_factory=list)    # list[Sightline]
    open_spaces: list = field(default_factory=list)   # list[OpenSpace]
    courtyards: list = field(default_factory=list)    # derived subset (COURTYARD type)
    privacy_gradient: list = field(default_factory=list)
    threshold_sequence: list = field(default_factory=list)
    stacking: list = field(default_factory=list)
    groupings: list = field(default_factory=list)
    shared_thresholds: list = field(default_factory=list)
    spines: list = field(default_factory=list)
    objectives: dict = field(default_factory=dict)
    provenance_log: list = field(default_factory=list)
    to_verify: list = field(default_factory=list)
    design_hypotheses: list = field(default_factory=list)
    genotype_id: str = ""
    birth_generation: int | None = None
    selected_generation: int | None = None
    constraint_status: str = "UNASSESSED"
    constraint_violation: float = 0.0
    must_shortfall: float = 0.0
    site_budget: dict = field(default_factory=dict)
    route_networks: list = field(default_factory=list)
    floor_plans: list = field(default_factory=list)
    spatial_relationships: list = field(default_factory=list)
    threshold_paths: list = field(default_factory=list)
    exposure_status: str = "UNASSESSED"
    safeguarding_actions: list = field(default_factory=list)
    architectural_status: str = "UNASSESSED"
    architectural_variant_id: str | None = None
    physical_rotations: dict = field(default_factory=dict)

    def to_dict(self):
        d = asdict(self)
        return d


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _orientation(inst: Instance) -> str:
    """Long-axis orientation of the module rectangle (site frame). [DH]"""
    return "EW" if inst.w >= inst.d else "NS"


def _interface(code: str) -> str:
    """Building interface class [PA5 CORPUS -> DH]."""
    if code in ("A0", "K0"):
        return "public"
    if code in ("B0", "E0"):
        return "protected"
    if code in ("F0", "M0"):
        return "service"
    if code in ("R4",):
        return "domestic"
    return "shared"


SPATIAL_ROLES = {
    "A0": "civic edge", "B0": "care hinge", "C0": "shared commons",
    "R4": "domestic cluster", "E0": "care / staff edge",
    "F0": "service / environmental edge", "M0": "service / environmental edge",
    "H0": "learning threshold", "I0": "retreat landscape",
    "J0": "livelihood threshold", "K0": "community edge",
    "L0": "transition territory",
}


def _boundary_face(inst: Instance) -> str:
    distances = {"W": inst.x - inst.w / 2,
                 "E": C.SITE_W - inst.x - inst.w / 2,
                 "S": inst.y - inst.d / 2,
                 "N": C.SITE_H - inst.y - inst.d / 2}
    return min(distances, key=distances.get)


def _face_toward(inst: Instance, target: Instance | None) -> str:
    if target is None:
        return _boundary_face(inst)
    edges = _edges(inst)
    return min(edges, key=lambda e: np.hypot(edges[e][0] - target.x,
                                             edges[e][1] - target.y))


def _nearest(insts: list[Instance], idx: int, codes: set[str]) -> Instance | None:
    opts = [other for k, other in enumerate(insts)
            if k != idx and other.code in codes]
    return min(opts, key=lambda o: np.hypot(insts[idx].x-o.x,
                                            insts[idx].y-o.y)) if opts else None


def _opposite(edge: str) -> str:
    return {"N": "S", "S": "N", "E": "W", "W": "E"}[edge]


def _configure_node(node: ModuleNode, inst: Instance,
                    insts: list[Instance], idx: int) -> None:
    """Assign access faces by actual user relationship [DESIGN HYPOTHESIS]."""
    civic = _nearest(insts, idx, {"A0", "K0"})
    domestic = _nearest(insts, idx, {"R4"})
    commons = _nearest(insts, idx, {"C0"})
    care = _nearest(insts, idx, {"B0", "E0"})
    service = _nearest(insts, idx, {"F0", "M0"})
    public_edge = _boundary_face(inst) if inst.code in {"A0", "K0", "F0"} \
        else _face_toward(inst, civic)
    private_edge = _face_toward(inst, commons if inst.code == "R4" else domestic)
    care_edge = _face_toward(inst, care if inst.code == "R4" else domestic)
    service_edge = _boundary_face(inst) if inst.code == "F0" \
        else _face_toward(inst, service)
    node.spatial_role = SPATIAL_ROLES[inst.code]
    node.faces = {"public": public_edge if inst.code in {"A0", "H0", "J0", "K0"} else None,
                  "private": private_edge if inst.code not in {"F0", "M0", "K0"} else None,
                  "service": service_edge if inst.code in {"F0", "M0", "C0", "J0"} else None,
                  "retreat": _opposite(private_edge) if inst.code in {"R4", "I0", "L0"} else None}
    roles = {}
    if inst.code in {"A0", "C0", "R4", "H0", "I0", "J0", "K0", "L0"}:
        roles["resident"] = private_edge
    if inst.code in {"A0", "B0", "C0", "R4", "E0", "L0"}:
        roles["care_staff"] = care_edge
    if inst.code in {"A0", "H0", "J0", "K0"}:
        roles["visitor_community"] = public_edge
    if inst.code in {"F0", "M0", "C0", "J0"}:
        roles["service"] = service_edge
    if inst.code in {"A0", "B0", "E0", "R4"}:
        roles["emergency"] = care_edge if inst.code == "R4" else public_edge
    node.access_edges = roles
    node.access_points = {role: _edges(inst)[edge] for role, edge in roles.items()}
    primary = next(iter(roles.values()), private_edge)
    node.entrance_anchor = _edges(inst)[primary]
    node.connection_anchors = [_edges(inst)[e] for e in ("N", "S", "E", "W")
                               if e != primary]
    node.grammar_rotation_degrees = {"S": 0, "E": 90, "N": 180,
                                      "W": 270}[primary]


def _rotate_zone(rx: float, ry: float, rw: float, rh: float,
                 degrees: int) -> tuple[float, float, float, float]:
    """Rotate relative kit zones inside the fixed campaign footprint."""
    if degrees == 90:
        return 1 - ry - rh, rx, rh, rw
    if degrees == 180:
        return 1 - rx - rw, 1 - ry - rh, rw, rh
    if degrees == 270:
        return ry, 1 - rx - rw, rh, rw
    return rx, ry, rw, rh


def _part_floor(code: str, name: str, floors: int) -> int:
    if floors > 1 and ((code == "C0" and name == "everyday activity") or
                       (code == "H0" and name == "quiet study")):
        return 2
    return 1


def _edges(inst: Instance):
    """Return dict of edge midpoints (entrance/connection anchors) in site coords."""
    return {
        "N": (inst.x, inst.y + inst.d / 2),
        "S": (inst.x, inst.y - inst.d / 2),
        "E": (inst.x + inst.w / 2, inst.y),
        "W": (inst.x - inst.w / 2, inst.y),
    }


def _pick_entrance(inst: Instance, others: list[Instance]) -> str:
    """Choose an entrance edge: face the nearest neighbour (controlled threshold).
    [DESIGN HYPOTHESIS] — entrance side is diagrammatic, not a designed door."""
    if not others:
        return "S"
    best_edge, best_d = "S", 1e18
    edges = _edges(inst)
    for e, (ex, ey) in edges.items():
        d = min(np.hypot(ex - o.x, ey - o.y) for o in others)
        if d < best_d:
            best_d, best_edge = d, e
    return best_edge


PRIVATE = {"R4"}                       # private residential territory
PUBLIC_MOD = {"A0", "K0"}              # public-facing interface modules
CARE_MOD = {"B0", "E0"}                # care / safeguarding
SVC_MOD = {"F0", "M0"}                 # service / technical


def _circulation_for(code_a: str, code_b: str, kind: str = "") -> list:
    """Circulation skeletons for a connection, reflecting its architectural
    relationship and users. [PA5 CORPUS -> DH]

    RULE: a connection touching PRIVATE residential territory (R4) is NEVER
    public circulation, even if the other end is a public-facing module. A
    SCREENED/controlled A0–R4 relationship is a *controlled resident/care
    threshold*, not a public route. 'public' applies only to edges whose BOTH
    ends are public-facing and which do not cross private territory.
    """
    a, b = code_a, code_b
    pair = {a, b}
    touches_private = bool(pair & PRIVATE)
    circ = set()

    if pair & SVC_MOD:
        circ.add("service")
    if touches_private:
        # private-residential edge: care and/or resident only, never public
        if pair & CARE_MOD:
            circ.add("care")
        else:
            circ.add("resident")
        if kind == SCREENED:
            circ.add("controlled")          # screened threshold, controlled crossing
        return sorted(circ)

    # no private territory involved
    if pair & CARE_MOD:
        circ.add("care")
    if pair <= PUBLIC_MOD or (pair & PUBLIC_MOD and not (pair & CARE_MOD | SVC_MOD)):
        # both public-facing, or public-facing linked to a shared module (not
        # care/service/private) -> public circulation is legitimate
        circ.add("public")
    if not circ:
        circ.add("resident")
    return sorted(circ)


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------
def build_prototype(ph: Phenotype, candidate_label: str = "",
                    rep_index: int = -1, seed=None,
                    selected_generation: int | None = None,
                    rotations: dict[int, int] | None = None) -> Prototype:
    if seed is not None and ph.origin_seed is not None and seed != ph.origin_seed:
        raise ValueError("candidate seed disagrees with phenotype provenance")
    parent_id = genotype_id(ph)
    rotations = {int(k): int(v) for k, v in (rotations or {}).items()
                 if int(v) % 360}
    if any(k < 0 or k >= len(ph.instances) for k in rotations):
        raise ValueError("rotation references an absent module instance")
    if any(v not in (90, 180, 270) for v in rotations.values()):
        raise ValueError("physical rotation must be 90, 180, or 270 degrees")
    working = deepcopy(ph) if rotations else ph
    for idx, degrees in rotations.items():
        if degrees in (90, 270):
            inst = working.instances[idx]
            inst.w, inst.d = inst.d, inst.w
    _, feasible, _ = evaluate_constraints(working)
    if rotations:
        working.objectives = evaluate_objectives(working)
    insts = working.instances
    objs = working.objectives if working.objectives is not None else np.zeros(len(OBJ_NAMES))
    variant_id = (hashlib.sha256(json.dumps(
        {"parent": parent_id, "rotations": sorted(rotations.items())},
        sort_keys=True).encode()).hexdigest()[:16] if rotations else None)
    proto = Prototype(
        candidate=candidate_label, rep_index=rep_index,
        seed=ph.origin_seed if seed is None else seed,
        program=f"R4x{ph.n_R4} res={ph.residents} day={ph.day_users}",
        site_w=C.SITE_W, site_h=C.SITE_H,
        residents=working.residents, day_users=working.day_users, gfa=round(working.gfa, 1),
        footprint=round(working.footprint, 1), landscape_frac=round(working.landscape_frac, 3),
        landscape_area=round(working.landscape_area, 1),
        objectives={OBJ_NAMES[i]: round(float(objs[i]), 3)
                    for i in range(len(OBJ_NAMES))},
        genotype_id=parent_id, birth_generation=working.birth_generation,
        selected_generation=selected_generation,
        constraint_status="MODEL_FEASIBLE" if feasible else "MODEL_INFEASIBLE",
        constraint_violation=round(float(working.cv), 4),
        must_shortfall=round(float(working.must_shortfall), 4),
        architectural_variant_id=variant_id,
        physical_rotations=rotations,
    )
    proto.site_budget = {
        "site_area_m2": C.SITE_AREA,
        "building_footprint_m2": round(working.footprint, 1),
        "landscape_target_m2": round(working.landscape_area, 1),
        "expansion_reserve_m2": round(working.reserve_area, 1),
        "other_open_and_access_m2": round(C.SITE_AREA - working.footprint -
                                          working.landscape_area - working.reserve_area, 1),
        "provenance": HYP,
    }
    if proto.site_budget["other_open_and_access_m2"] < 0:
        proto.to_verify.append("SITE BUDGET exceeds parcel area [TO VERIFY]")
    if rotations:
        proto.provenance_log.append(
            f"physical quarter-turns {rotations} derived from parent genotype "
            f"{parent_id} as an architectural variant {HYP}; constraints, "
            f"objectives, routes and sightlines recomputed")
    proto.to_verify.extend([
        "Real parcel shape, street approach and north orientation [TO VERIFY]",
        "Accessibility, egress and emergency operations [TO VERIFY]",
    ])

    # --- module nodes with internal kit-of-parts ---
    for idx, inst in enumerate(insts):
        mt = MODULES[inst.code]
        orient = _orientation(inst)
        edges = _edges(inst)
        ent_edge = _pick_entrance(inst, [o for j, o in enumerate(insts) if j != idx])
        anchors = [e for e in ("N", "S", "E", "W") if e != ent_edge]
        node = ModuleNode(
            inst_id=idx, code=inst.code, name=mt.name,
            x=inst.x, y=inst.y, w=inst.w, d=inst.d,
            floors=inst.floors, privacy=inst.privacy, orientation=orient,
            entrance_anchor=edges[ent_edge], connection_anchors=[edges[a] for a in anchors],
            interface=_interface(inst.code),
        )
        _configure_node(node, inst, insts, idx)
        node.physical_rotation_degrees = rotations.get(idx, 0)
        node.grammar_rotation_degrees = (
            node.grammar_rotation_degrees + node.physical_rotation_degrees) % 360
        if not rotations:
            rotated = deepcopy(ph)
            trial = rotated.instances[idx]
            trial.w, trial.d = trial.d, trial.w
            _, node.quarter_turn_feasible, _ = evaluate_constraints(rotated)
        # expand internal kit-of-parts into site coordinates (relative zones)
        x0, y0 = inst.x - inst.w / 2, inst.y - inst.d / 2
        for (pname, rx, ry, rw, rh, priv, prov, note) in KIT.get(inst.code, []):
            rx, ry, rw, rh = _rotate_zone(rx, ry, rw, rh,
                                           node.grammar_rotation_degrees)
            node.parts.append(Part(pname, x0 + rx * inst.w, y0 + ry * inst.d,
                                   rw * inst.w, rh * inst.d, priv, prov, note,
                                   _part_floor(inst.code, pname, inst.floors)))
            if prov == VERIFY:
                proto.to_verify.append(f"{inst.code}:{pname} — {note}")
            elif prov == HYP:
                proto.design_hypotheses.append(f"{inst.code}:{pname} — {note}")
        if node.floors > 1:
            core = Part("vertical core", inst.x - inst.w * 0.07,
                        inst.y - inst.d * 0.10, inst.w * 0.14,
                        inst.d * 0.20, CTRL, VERIFY,
                        "diagrammatic lift/stair position; dimension and egress", 1)
            node.parts.append(core)
            proto.to_verify.append(f"{inst.code}:vertical core — dimension and egress")
        for part in node.parts:
            if part.floor == 1:
                node.internal_paths.append({
                    "from": node.entrance_anchor,
                    "to": (round(part.x + part.w / 2, 2),
                           round(part.y + part.d / 2, 2)),
                    "destination": part.name, "floor": 1, "provenance": HYP})
        proto.modules.append(node)
    proto.provenance_log.append(
        f"access faces, grammar rotation and internal route skeletons {HYP}; "
        f"street frontage and door dimensions {VERIFY}")

    # --- connections from the corpus adjacency (MUST/NEAR/SCREENED drawn) ---
    drawn_prov = {MUST: CORPUS, NEAR: CORPUS, SCREENED: HYP}
    for i in range(len(insts)):
        for j in range(i + 1, len(insts)):
            a, b = insts[i], insts[j]
            rel = relation(a.code, b.code)
            if rel in (MUST, NEAR, SCREENED):
                proto.connections.append(Connection(
                    a_id=i, b_id=j, a_code=a.code, b_code=b.code, kind=rel,
                    provenance=drawn_prov[rel],
                    circulations=_circulation_for(a.code, b.code, rel)))
    proto.provenance_log.append(
        f"connections drawn from corpus adjacency: MUST/NEAR {CORPUS}, SCREENED {HYP}")

    # --- direct visual-exposure checks for PROHIBITED / safeguarding-sensitive ---
    proto.sightlines = _check_sightlines(insts)
    exposed = [s for s in proto.sightlines if s.exposed]
    proto.exposure_status = ("EXPOSED_TO_VERIFY" if exposed else
                             "NO_EXPOSURE_IN_SAMPLED_RAYS")
    for sl in proto.sightlines:
        if sl.exposed:
            action = (
                "offset service openings and test an opaque service-yard edge"
                if sl.relation == "PROHIBITED" else
                "place a controlled visual screen at the civic-to-domestic threshold")
            proto.safeguarding_actions.append({
                "from_id": sl.from_id, "to_id": sl.to_id,
                "from_code": sl.from_code, "to_code": sl.to_code,
                "visible_rays": sl.visible_rays,
                "tested_rays": sl.tested_rays,
                "design_move": action, "provenance": HYP,
                "verification": "eye-level and sectional view study with operator review "
                                "[TO VERIFY]"})
            proto.to_verify.append(
                f"EXPOSED sightline {sl.from_code}->{sl.to_code} ({sl.relation}): "
                f"{sl.visible_rays}/{sl.tested_rays} sampled rays unobstructed; "
                f"screening required "
                f"[TO VERIFY].")
    if not exposed:
        proto.to_verify.append(
            "No exposure in sampled plan rays; eye-level, section, openings and "
            "landscape transparency still require review [TO VERIFY].")
    proto.provenance_log.append(
        f"sightline exposure checked with sampled face-to-face rays {HYP}; "
        f"diagrammatic, not a regulatory sightline study")

    # --- open spaces classified by DEGREE OF ENCLOSURE (schematic) ---
    proto.open_spaces = _classify_open_spaces(insts)
    proto.courtyards = [{"cx": s.cx, "cy": s.cy, "sides_enclosed": s.enclosure,
                         "space_type": s.space_type, "provenance": s.provenance}
                        for s in proto.open_spaces if s.space_type == "COURTYARD"]
    proto.provenance_log.append(
        f"open spaces classified by local 12 m enclosure: 3-4 sides=COURTYARD, "
        f"2=POCKET COURT/THRESHOLD EDGE, 0-1=OPEN LANDSCAPE {HYP}")

    # --- privacy gradient (site-level, PUBLIC -> PERSONAL ordering of modules) ---
    proto.privacy_gradient = sorted(
        [{"code": m.code, "id": m.inst_id, "privacy": _PRIV_NAME[m.privacy],
          "interface": m.interface} for m in proto.modules],
        key=lambda d: PRIVACY.index(d["privacy"]))

    # --- threshold sequence (public edge -> controlled gate -> domestic core) ---
    proto.threshold_sequence = _threshold_sequence(proto)
    proto.provenance_log.append(f"threshold sequence derived from interface classes {HYP}")

    # --- stacking relationships ---
    for m in proto.modules:
        if m.floors > 1:
            proto.stacking.append({"code": m.code, "id": m.inst_id,
                                   "floors": m.floors,
                                   "note": f"{m.code} stacked x{m.floors}",
                                   "provenance": CORPUS})
    proto.provenance_log.append(
        f"stacking from genotype floors genes {CORPUS}; R4 single-storey per corpus {CORPUS}")

    # --- physical clusters and shared-threshold opportunities ---
    proto.groupings = _groupings(proto)
    proto.shared_thresholds = _shared_thresholds(proto)
    proto.provenance_log.append(
        f"physical building groups and threshold opportunities require a "
        f"MUST/NEAR relation and a local edge gap {HYP}")

    proto.route_networks = _derive_route_networks(proto)
    proto.spines = _spines(proto)
    proto.floor_plans = _floor_plans(proto)
    proto.spatial_relationships = _spatial_relationships(proto)
    proto.threshold_paths = _threshold_paths(proto)
    proto.architectural_status = (
        "ROUTE_UNRESOLVED" if any(n["unresolved"] for n in proto.route_networks)
        or any(p["status"] == "UNRESOLVED" for p in proto.threshold_paths)
        else "ROUTES_CONNECTED; SIGHTLINES_TO_VERIFY" if exposed
        else "ROUTES_CONNECTED; SAMPLED_SIGHTLINES_SCREENED")

    # --- spatial-coherence flags (recorded, not silently drawn) ---
    for m in proto.modules:
        if (m.x - m.w / 2 < -0.05 or m.x + m.w / 2 > proto.site_w + 0.05 or
                m.y - m.d / 2 < -0.05 or m.y + m.d / 2 > proto.site_h + 0.05):
            proto.to_verify.append(
                f"BOUNDARY {m.code}: rectangle overhangs the site edge "
                f"(centroid placement from genotype; clipping is a design decision).")
    conn_ids = set()
    for c in proto.connections:
        conn_ids.add(c.a_id); conn_ids.add(c.b_id)
    for m in proto.modules:
        if m.inst_id not in conn_ids:
            proto.to_verify.append(
                f"ISOLATED {m.code}: no corpus MUST/NEAR/SCREENED connection — "
                f"architecturally unmoored; adjacency to the rest of the scheme "
                f"must be designed.")

    # de-duplicate verify/hypothesis lists
    proto.to_verify = sorted(set(proto.to_verify))
    proto.design_hypotheses = sorted(set(proto.design_hypotheses))
    return proto


def _rect_of(inst: Instance):
    return (inst.x - inst.w / 2, inst.y - inst.d / 2, inst.x + inst.w / 2, inst.y + inst.d / 2)


def _seg_intersects_rect(p0, p1, rect) -> bool:
    """Does segment p0->p1 cross the axis-aligned rect? (shrink rect slightly so a
    segment that merely grazes a corner is not counted)."""
    x0, y0, x1, y1 = rect
    eps = 0.3
    x0 += eps; y0 += eps; x1 -= eps; y1 -= eps
    # Liang-Barsky
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, p0[0] - x0), (dx, x1 - p0[0]),
                 (-dy, p0[1] - y0), (dy, y1 - p0[1])):
        if abs(p) < 1e-12:
            if q < 0:
                return False
        else:
            r = q / p
            if p < 0:
                if r > t1: return False
                if r > t0: t0 = r
            else:
                if r < t0: return False
                if r < t1: t1 = r
    return t0 < t1


def _check_sightlines(insts: list[Instance]) -> list[Sightline]:
    """Direct visual-exposure checks between R4/private residential territory and
    public-facing or safeguarding-sensitive modules, for all PROHIBITED or
    safeguarding-sensitive relationships.

    For each sensitive pair, sample boundary points on the faces toward the
    other module. A single central ray can claim a pair is screened while an
    oblique view remains open. Any clear sampled ray counts as exposure.
    Diagrammatic only [TO VERIFY], not a regulatory view-cone study."""
    sensitive_pairs = []
    for i, a in enumerate(insts):
        for j, b in enumerate(insts):
            if j <= i:
                continue
            rel = relation(a.code, b.code)
            private_side = a.code in PRIVATE or b.code in PRIVATE
            public_side = a.code in PUBLIC_MOD or b.code in PUBLIC_MOD
            is_sensitive = (rel == PROHIBITED) or (private_side and public_side)
            if is_sensitive:
                sensitive_pairs.append((i, j, "PROHIBITED" if rel == PROHIBITED
                                        else "safeguarding-sensitive"))
    out = []
    for i, j, rel_label in sensitive_pairs:
        a, b = insts[i], insts[j]
        # nearest points between the two rects (approx via clamped centres)
        pa = _clamp_point_to_rect((b.x, b.y), _rect_of(a))
        pb = _clamp_point_to_rect((a.x, a.y), _rect_of(b))
        dist = float(np.hypot(pb[0] - pa[0], pb[1] - pa[1]))
        screened_by = set()
        visible = 0
        source_pts = _facing_points(a, b)
        target_pts = _facing_points(b, a)
        for source in source_pts:
            for target in target_pts:
                blockers = [other.code for k, other in enumerate(insts)
                            if k not in (i, j) and
                            _seg_intersects_rect(source, target, _rect_of(other))]
                if blockers:
                    screened_by.update(blockers)
                else:
                    visible += 1
        tested = len(source_pts) * len(target_pts)
        out.append(Sightline(
            from_id=i, from_code=a.code, to_id=j, to_code=b.code,
            relation=rel_label, distance=round(dist, 2),
            exposed=visible > 0, screened_by=sorted(screened_by),
            provenance=VERIFY, tested_rays=tested, visible_rays=visible,
            exposure_ratio=round(visible / tested, 3)))
    return out


def _facing_points(source: Instance, target: Instance) -> list[tuple[float, float]]:
    """Three points on each face with a substantial view toward the target."""
    x0, y0, x1, y1 = _rect_of(source)
    dx, dy = target.x - source.x, target.y - source.y
    pts = []
    if abs(dx) >= abs(dy) / 2:
        x = x1 if dx >= 0 else x0
        pts.extend((x, y0 + f * (y1 - y0)) for f in (0.15, 0.5, 0.85))
    if abs(dy) >= abs(dx) / 2:
        y = y1 if dy >= 0 else y0
        pts.extend((x0 + f * (x1 - x0), y) for f in (0.15, 0.5, 0.85))
    return pts


def _clamp_point_to_rect(p, rect):
    x0, y0, x1, y1 = rect
    return (min(max(p[0], x0), x1), min(max(p[1], y0), y1))


def _classify_open_spaces(insts: list[Instance], res: int = 48,
                          view_depth: float = 12.0) -> list[OpenSpace]:
    """Classify open-space cells by DEGREE OF ENCLOSURE (schematic, [DESIGN
    HYPOTHESIS]):
      3-4 enclosing sides -> COURTYARD
      2  enclosing sides  -> POCKET COURT / THRESHOLD EDGE
      0-1 enclosing sides -> OPEN LANDSCAPE

    Enclosure is measured by casting four cardinal rays up to view_depth metres.
    Unlimited rays falsely turn gaps between distant blocks into courtyards.
    Contiguous cells of the same type are merged into one zone (centroid +
    area_cells)."""
    cw, ch = C.SITE_W / res, C.SITE_H / res
    nx = max(1, int(np.ceil(view_depth / cw)))
    ny = max(1, int(np.ceil(view_depth / ch)))
    built = np.zeros((res, res), dtype=bool)
    for inst in insts:
        i0 = max(0, int((inst.x - inst.w / 2) / cw)); i1 = min(res, int((inst.x + inst.w / 2) / cw) + 1)
        j0 = max(0, int((inst.y - inst.d / 2) / ch)); j1 = min(res, int((inst.y + inst.d / 2) / ch) + 1)
        built[i0:i1, j0:j1] = True

    def enc(i, j):
        """Count of 4 cardinal rays (W,E,S,N) that hit built mass before site edge."""
        s = 0
        if built[max(0, i-nx):i, j].any():            # West ray
            s += 1
        if built[i+1:min(res, i+nx+1), j].any():      # East ray
            s += 1
        if built[i, max(0, j-ny):j].any():            # South ray
            s += 1
        if built[i, j+1:min(res, j+ny+1)].any():      # North ray
            s += 1
        return s

    def stype(e):
        if e >= 3: return "COURTYARD"
        if e == 2: return "POCKET COURT / THRESHOLD EDGE"
        return "OPEN LANDSCAPE"

    typ = np.full((res, res), "", dtype=object)
    enclosure = np.zeros((res, res), dtype=np.uint8)
    for i in range(res):
        for j in range(res):
            if not built[i, j]:
                enclosure[i, j] = enc(i, j)
                typ[i, j] = stype(enclosure[i, j])

    # merge contiguous cells of the same type (4-connected flood fill)
    seen = np.zeros((res, res), dtype=bool)
    zones = []
    for i in range(res):
        for j in range(res):
            if built[i, j] or seen[i, j]:
                continue
            t = typ[i, j]
            stack, cells = [(i, j)], []
            seen[i, j] = True
            while stack:
                ci, cj = stack.pop(); cells.append((ci, cj))
                for di, dj in ((1,0),(-1,0),(0,1),(0,-1)):
                    ni, nj = ci+di, cj+dj
                    if 0 <= ni < res and 0 <= nj < res and not seen[ni, nj] \
                       and not built[ni, nj] and typ[ni, nj] == t:
                        seen[ni, nj] = True; stack.append((ni, nj))
            centre = np.mean(np.asarray(cells, dtype=float), axis=0)
            ci, cj = min(cells, key=lambda q: (q[0]-centre[0])**2 +
                         (q[1]-centre[1])**2)
            cx, cy = (ci + 0.5) * cw, (cj + 0.5) * ch
            e = min(int(enclosure[ii, jj]) for ii, jj in cells)
            zones.append(OpenSpace(cx=round(cx, 1), cy=round(cy, 1),
                                   area_cells=len(cells), enclosure=e,
                                   space_type=t, provenance=HYP,
                                   area_m2=round(len(cells) * cw * ch, 1)))
    # keep meaningful zones (>=2 cells); retain the FULL enclosure spectrum so the
    # diagram shows courtyard + pocket + open-landscape variety (no cap).
    zones = [z for z in zones if z.area_cells >= 2]
    zones.sort(key=lambda z: (z.space_type != "COURTYARD",
                              not z.space_type.startswith("POCKET"), -z.area_cells))
    return zones


def _threshold_sequence(proto: Prototype) -> list:
    """Order interfaces into a public->protected->domestic threshold sequence."""
    order = {"public": 0, "shared": 1, "protected": 2, "service": 2, "domestic": 3}
    seq = sorted(proto.modules, key=lambda m: order.get(m.interface, 1))
    return [{"step": k, "code": m.code, "interface": m.interface,
             "privacy": _PRIV_NAME[m.privacy], "provenance": HYP}
            for k, m in enumerate(seq)]


def _edge_gap(a: ModuleNode, b: ModuleNode) -> float:
    """Shortest distance between two nonoverlapping axis-aligned footprints."""
    dx = max(0.0, abs(a.x-b.x) - (a.w+b.w)/2)
    dy = max(0.0, abs(a.y-b.y) - (a.d+b.d)/2)
    return float(np.hypot(dx, dy))


def _groupings(proto: Prototype, max_gap: float = 6.0) -> list:
    """Local physical clusters, not code-level graph components [DH]."""
    n = len(proto.modules)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for cn in proto.connections:
        if cn.kind in (MUST, NEAR) and _edge_gap(
                proto.modules[cn.a_id], proto.modules[cn.b_id]) <= max_gap:
            union(cn.a_id, cn.b_id)
    groups = {}
    for m in proto.modules:
        groups.setdefault(find(m.inst_id), []).append(m)
    return [{"group": k,
             "module_ids": [m.inst_id for m in sorted(v, key=lambda m: m.inst_id)],
             "modules": [m.code for m in sorted(v, key=lambda m: m.inst_id)],
             "max_link_gap_m": max_gap, "provenance": HYP}
            for k, v in enumerate(groups.values())]


def _shared_thresholds(proto: Prototype, max_gap: float = 6.0) -> list:
    """Nearby related modules that could share a controlled threshold [DH]."""
    return [{"a_id": c.a_id, "b_id": c.b_id,
             "a_code": c.a_code, "b_code": c.b_code,
             "edge_gap_m": round(_edge_gap(proto.modules[c.a_id],
                                           proto.modules[c.b_id]), 1),
             "relation": c.kind, "provenance": HYP}
            for c in proto.connections
            if c.kind in (MUST, NEAR) and
            _edge_gap(proto.modules[c.a_id], proto.modules[c.b_id]) <= max_gap]


def _point_to_polyline(point: tuple, points: list) -> float:
    if len(points) < 2:
        return float("inf")
    p = np.asarray(point, dtype=float)
    best = float("inf")
    for a, b in zip(points, points[1:]):
        a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
        ab = b-a
        t = float(np.clip(np.dot(p-a, ab)/max(np.dot(ab, ab), 1e-12), 0, 1))
        best = min(best, float(np.linalg.norm(p-(a+t*ab))))
    return best


def _spines(proto: Prototype, alignment_max: float = 6.0) -> list:
    """Routed trunks and modules near them, for site organization [DH]."""
    specifications = (("resident", "A0", "C0", "R4"),
                      ("service", "F0", "M0", "C0"))
    spines = []
    for kind, source, destination, branch in specifications:
        network = next((n for n in proto.route_networks
                        if n["kind"] == kind), None)
        if network is None:
            continue
        trunk = next((r for r in network["routes"]
                      if r["from_code"] == source and
                      r["to_code"] == destination and r["points"]), None)
        if trunk is None:
            continue
        aligned = []
        for module in proto.modules:
            if module.code != branch or kind not in module.access_points:
                continue
            distance = _point_to_polyline(module.access_points[kind],
                                          trunk["points"])
            if distance <= alignment_max:
                aligned.append({"id": module.inst_id, "code": module.code,
                                "distance_m": round(distance, 1)})
        spines.append({"kind": kind, "from": source, "to": destination,
                       "points": trunk["points"], "length_m": trunk["length_m"],
                       "aligned_modules": aligned,
                       "alignment_distance_m": alignment_max,
                       "provenance": HYP})
    return spines


def _route_grid(proto: Prototype, access_kind: str, step: float = 1.5):
    """A* walkable site grid, with protected clearance for public/service paths."""
    nx = int(np.ceil(proto.site_w / step))
    ny = int(np.ceil(proto.site_h / step))
    blocked = np.zeros((ny, nx), dtype=bool)
    clearance = 3.0 if access_kind == "visitor_community" else (
        2.0 if access_kind == "service" else 0.0)
    for m in proto.modules:
        margin = clearance if m.code == "R4" else 0.0
        x0, x1 = m.x-m.w/2-margin, m.x+m.w/2+margin
        y0, y1 = m.y-m.d/2-margin, m.y+m.d/2+margin
        for iy in range(ny):
            cy = (iy + 0.5) * step
            if not y0 <= cy <= y1:
                continue
            for ix in range(nx):
                cx = (ix + 0.5) * step
                if x0 <= cx <= x1:
                    blocked[iy, ix] = True
    return blocked, step


def _grid_path(blocked: np.ndarray, step: float, start: tuple,
               end: tuple) -> list[tuple[float, float]]:
    ny, nx = blocked.shape
    free = np.argwhere(~blocked)
    if len(free) == 0:
        return []

    def snap(point):
        delta = (free[:, ::-1] + 0.5) * step - np.asarray(point)
        row = free[int(np.argmin(np.sum(delta * delta, axis=1)))]
        return int(row[0]), int(row[1])

    src, dst = snap(start), snap(end)
    best = {src: 0.0}
    prev = {}
    queue = [(0.0, 0.0, src)]
    while queue:
        _, cost, node = heapq.heappop(queue)
        if cost > best.get(node, float("inf")):
            continue
        if node == dst:
            break
        iy, ix = node
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nxt = (iy + dy, ix + dx)
            if not (0 <= nxt[0] < ny and 0 <= nxt[1] < nx):
                continue
            if blocked[nxt]:
                continue
            new_cost = cost + step
            if new_cost < best.get(nxt, float("inf")):
                best[nxt] = new_cost
                prev[nxt] = node
                heuristic = (abs(nxt[0]-dst[0]) + abs(nxt[1]-dst[1])) * step
                heapq.heappush(queue, (new_cost + heuristic, new_cost, nxt))
    if dst not in best:
        return []
    cells = [dst]
    while cells[-1] != src:
        cells.append(prev[cells[-1]])
    cells.reverse()
    pts = [tuple(round(float(v), 2) for v in start)]
    pts.extend(((ix + 0.5) * step, (iy + 0.5) * step)
               for iy, ix in cells)
    pts.append(tuple(round(float(v), 2) for v in end))
    return [(round(float(x), 2), round(float(y), 2)) for x, y in pts]


def _derive_route_networks(proto: Prototype) -> list:
    bycode = {}
    for m in proto.modules:
        bycode.setdefault(m.code, []).append(m.inst_id)

    def pairs(origin, dest):
        if origin not in bycode:
            return []
        return [(bycode[origin][0], target) for target in bycode.get(dest, [])]

    specs = {
        "resident": ([("A0", "C0"), ("C0", "R4"),
                      ("C0", "H0"), ("C0", "I0"),
                      ("C0", "J0"), ("C0", "L0")]),
        "care_staff": ([("A0", "B0"), ("B0", "E0"),
                        ("B0", "R4"), ("B0", "L0")]),
        "visitor_community": ([("A0", "H0"), ("A0", "J0"),
                                ("A0", "K0")]),
        "service": ([("F0", "M0"), ("F0", "C0"), ("F0", "J0")]),
        "emergency": ([("A0", "B0"), ("B0", "R4")]),
    }
    networks = []
    for kind, code_pairs in specs.items():
        blocked, step = _route_grid(proto, kind)
        routes, unresolved = [], []
        gate_code = "F0" if kind == "service" else "A0"
        if gate_code in bycode:
            gate = proto.modules[bycode[gate_code][0]]
            edge = gate.faces["service" if gate_code == "F0" else "public"]
            ax, ay = gate.access_points[kind]
            ex, ey = _edges(gate)[edge]
            site_point = {"W": (0.0, ey), "E": (proto.site_w, ey),
                          "S": (ex, 0.0), "N": (ex, proto.site_h)}[edge]
            pts = _grid_path(blocked, step, site_point, (ex, ey))
            length = sum(float(np.hypot(x1-x0, y1-y0))
                         for (x0, y0), (x1, y1) in zip(pts, pts[1:]))
            routes.append({"from_id": -1, "to_id": gate.inst_id,
                           "from_code": "SITE", "to_code": gate.code,
                           "points": pts, "length_m": round(length, 1),
                           "status": "CONNECTED" if pts else "UNRESOLVED",
                           "provenance": VERIFY})
            if not pts:
                unresolved.append(f"SITE->{gate.code}{gate.inst_id}")
            if (ax, ay) != (ex, ey):
                routes.append({"from_id": gate.inst_id, "to_id": gate.inst_id,
                               "from_code": gate.code, "to_code": gate.code,
                               "points": [(ex, ey), (ax, ay)],
                               "length_m": round(float(np.hypot(ax-ex, ay-ey)), 1),
                               "status": "CONTROLLED_INTERNAL",
                               "provenance": HYP})
        for source_code, target_code in code_pairs:
            if source_code not in bycode or target_code not in bycode:
                continue
            for a_id, b_id in pairs(source_code, target_code):
                a, b = proto.modules[a_id], proto.modules[b_id]
                start, end = a.access_points[kind], b.access_points[kind]
                pts = _grid_path(blocked, step, start, end)
                length = sum(float(np.hypot(x1-x0, y1-y0))
                             for (x0, y0), (x1, y1) in zip(pts, pts[1:]))
                route = {"from_id": a_id, "to_id": b_id,
                         "from_code": a.code, "to_code": b.code,
                         "points": pts, "length_m": round(length, 1),
                         "status": "CONNECTED" if pts else "UNRESOLVED",
                         "provenance": HYP}
                routes.append(route)
                if not pts:
                    unresolved.append(f"{a.code}{a_id}->{b.code}{b_id}")
        if unresolved:
            proto.to_verify.append(
                f"{kind} path network unresolved: {', '.join(unresolved)} {VERIFY}")
        networks.append({"kind": kind, "routes": routes,
                         "unresolved": unresolved, "provenance": HYP,
                         "site_entry": "nearest schematic site edge [TO VERIFY]"})
    return networks


def _floor_plans(proto: Prototype) -> list:
    plans = []
    for floor in range(1, max((m.floors for m in proto.modules), default=1) + 1):
        entries = []
        for m in proto.modules:
            if m.floors >= floor:
                entries.append({"id": m.inst_id, "code": m.code,
                                "x": m.x, "y": m.y, "w": m.w, "d": m.d,
                                "parts": [p.name for p in m.parts if p.floor == floor],
                                "provenance": HYP})
        plans.append({"floor": floor, "modules": entries,
                      "provenance": HYP})
    return plans


def _spatial_relationships(proto: Prototype) -> list:
    named = {frozenset(("A0", "B0")): "civic edge / care hinge",
             frozenset(("B0", "C0")): "care hinge / shared commons",
             frozenset(("C0", "R4")): "commons / domestic cluster",
             frozenset(("B0", "R4")): "care hinge / domestic cluster",
             frozenset(("F0", "M0")): "service / environmental edge"}
    out = []
    for c in proto.connections:
        name = named.get(frozenset((c.a_code, c.b_code)))
        if name is None:
            continue
        a, b = proto.modules[c.a_id], proto.modules[c.b_id]
        distance = float(np.hypot(a.x-b.x, a.y-b.y))
        out.append({"a_id": c.a_id, "b_id": c.b_id,
                    "relationship": name, "relation": c.kind,
                    "centroid_distance_m": round(distance, 1),
                    "within_must_range": distance <= C.MUST_LINK_MAX
                    if c.kind == MUST else None,
                    "provenance": CORPUS if c.kind == MUST else HYP})
    open_land = [s for s in proto.open_spaces if s.space_type == "OPEN LANDSCAPE"]
    if open_land:
        largest = max(open_land, key=lambda s: s.area_m2)
        out.append({"relationship": "landscape buffer / expansion zone",
                    "anchor": (largest.cx, largest.cy),
                    "reserve_area_m2": proto.site_budget["expansion_reserve_m2"],
                    "provenance": HYP})
    return out


def _threshold_paths(proto: Prototype) -> list:
    resident = next((n for n in proto.route_networks
                     if n["kind"] == "resident"), None)
    if resident is None:
        return []
    route_map = {(r["from_code"], r["to_id"]): r for r in resident["routes"]}
    commons = next((m for m in proto.modules if m.code == "C0"), None)
    if commons is None:
        return []
    entry = route_map.get(("A0", commons.inst_id))
    paths = []
    for m in proto.modules:
        if m.code != "R4":
            continue
        branch = route_map.get(("C0", m.inst_id))
        connected = bool(entry and branch and entry["points"] and branch["points"])
        points = (entry["points"] + branch["points"] if connected else [])
        paths.append({"to_id": m.inst_id,
                      "sequence": ["A0", "C0", f"R4:{m.inst_id}"],
                      "privacy": ["CONTROLLED", "SHARED", "DOMESTIC"],
                      "points": points,
                      "length_m": round(entry["length_m"] + branch["length_m"], 1)
                      if connected else None,
                      "status": "CONNECTED" if connected else "UNRESOLVED",
                      "provenance": HYP})
    return paths


# ---------------------------------------------------------------------------
# Rendering suite (7 schematic figures per phenotype)
# ---------------------------------------------------------------------------
def _module_box(ax, m: ModuleNode, facecolor, show_parts=False, label=True,
                floor: int = 1):
    ax.add_patch(Rectangle((m.x - m.w / 2, m.y - m.d / 2), m.w, m.d,
                           facecolor=facecolor, edgecolor="k", alpha=0.85, lw=1.0))
    if show_parts:
        for p in m.parts:
            if p.floor != floor:
                continue
            ax.add_patch(Rectangle((p.x, p.y), p.w, p.d,
                                   facecolor=_PRIV_COLOR[p.privacy], edgecolor="white",
                                   alpha=0.55, lw=0.4))
    if label:
        ax.text(m.x, m.y, m.code, ha="center", va="center", fontsize=7, weight="bold")


def _site_frame(ax, proto: Prototype):
    ax.add_patch(Rectangle((0, 0), proto.site_w, proto.site_h, fill=False,
                           edgecolor="k", lw=1.5))
    ax.set_xlim(-3, proto.site_w + 3); ax.set_ylim(-3, proto.site_h + 3)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])


def render_plan(proto: Prototype, path):
    """1. Simplified schematic plan: modules + internal kit-of-parts + entrances."""
    fig, ax = plt.subplots(figsize=(10, 7))
    _site_frame(ax, proto)
    for m in proto.modules:
        _module_box(ax, m, _MOD_COLOR.get(m.code, "#eee"), show_parts=True)
        ex, ey = m.entrance_anchor
        ax.plot([ex], [ey], marker="v", color="k", ms=5)   # entrance anchor
    # connection lines (MUST solid, NEAR dashed, SCREENED dotted)
    style = {MUST: ("-", 1.8, "#16a34a"), NEAR: ("--", 1.2, "#0284c7"),
             SCREENED: (":", 1.0, "#9333ea")}
    for cn in proto.connections:
        a = proto.modules[cn.a_id]; b = proto.modules[cn.b_id]
        ls, lw, col = style.get(cn.kind, ("-", 1, "#888"))
        ax.plot([a.x, b.x], [a.y, b.y], ls=ls, lw=lw, color=col, alpha=0.7, zorder=0)
    for c in proto.courtyards:
        ax.add_patch(Circle((c["cx"], c["cy"]), 2.2, facecolor="#bbf7d0",
                            edgecolor="#16a34a", alpha=0.6, ls="--"))
        ax.text(c["cx"], c["cy"], "courtyard", ha="center", va="center", fontsize=5, color="#166534")
    ax.set_title(f"Schematic plan — {proto.candidate or 'phenotype'} (rep {proto.rep_index}, seed {proto.seed})\n"
                 f"{proto.program} · area proxy {proto.gfa} m² · landscape {proto.landscape_frac*100:.0f}%")
    _legend_provenance(fig)
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def render_axonometric(proto: Prototype, path):
    """Exploded floor massing in diagram units, preserving each module's stack."""
    fig = plt.figure(figsize=(11, 8))
    ax = fig.add_subplot(111, projection="3d")
    for m in proto.modules:
        x0, y0 = m.x - m.w / 2, m.y - m.d / 2
        for floor in range(m.floors):
            z0 = floor * 3.8
            _bar3(ax, x0, y0, z0, m.w, m.d, 3.0,
                  _MOD_COLOR.get(m.code, "#eee"))
        ax.text(m.x, m.y, (m.floors - 1) * 3.8 + 3.5,
                m.code, ha="center", fontsize=7, weight="bold")
    ax.set_box_aspect((proto.site_w, proto.site_h, 12))
    ax.view_init(elev=28, azim=-58)
    ax.set_axis_off()
    ax.set_title(f"Exploded axonometric — {proto.candidate or 'phenotype'} "
                 f"(floors separated in diagram units; height/structure {VERIFY})")
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def render_floor_plans(proto: Prototype, path):
    """Ground and upper schematic layouts at one site scale."""
    n = len(proto.floor_plans)
    fig, axes = plt.subplots(1, n, figsize=(10 * n, 7))
    axes = np.atleast_1d(axes)
    for ax, plan in zip(axes, proto.floor_plans):
        _site_frame(ax, proto)
        floor = plan["floor"]
        for m in proto.modules:
            if m.floors >= floor:
                _module_box(ax, m, _MOD_COLOR.get(m.code, "#eee"),
                            show_parts=True, floor=floor)
        ax.set_title(f"Floor {floor} · {len(plan['modules'])} modules")
    fig.suptitle(f"Floor-by-floor spatial grammar — {proto.candidate or 'phenotype'} "
                 f"(internal zones {HYP}; dimensions {VERIFY})")
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def _bar3(ax, x, y, z, dx, dy, dz, color):
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    v = np.array([[x, y, z], [x+dx, y, z], [x+dx, y+dy, z], [x, y+dy, z],
                  [x, y, z+dz], [x+dx, y, z+dz], [x+dx, y+dy, z+dz], [x, y+dy, z+dz]])
    faces = [[v[0], v[1], v[2], v[3]], [v[4], v[5], v[6], v[7]],
             [v[0], v[1], v[5], v[4]], [v[2], v[3], v[7], v[6]],
             [v[1], v[2], v[6], v[5]], [v[4], v[7], v[3], v[0]]]
    ax.add_collection3d(Poly3DCollection(faces, facecolors=color,
                                         edgecolors="k", linewidths=0.5, alpha=0.9))


def render_stacking(proto: Prototype, path):
    """3. Stacking diagram: floors per module + service/residential separation."""
    fig, ax = plt.subplots(figsize=(9, 6))
    stacked = [m for m in proto.modules if m.floors > 1]
    single = [m for m in proto.modules if m.floors == 1]
    ax.scatter([m.x for m in single], [m.y for m in single], s=90, marker="s",
               c="#94a3b8", edgecolor="k", label="single-storey", zorder=3)
    ax.scatter([m.x for m in stacked], [m.y for m in stacked], s=140, marker="^",
               c="#f59e0b", edgecolor="k", label="stacked (2 floors)", zorder=3)
    for m in proto.modules:
        ax.text(m.x, m.y, f"{m.code}\nx{m.floors}", ha="center", va="center",
                fontsize=6, weight="bold", zorder=4)
    _site_frame(ax, proto)
    ax.legend(loc="upper right", fontsize=8)
    ax.set_title(f"Stacking — {proto.candidate or 'phenotype'} "
                 f"({len(stacked)} stacked, {len(single)} single-storey; R4 always single)")
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def render_privacy(proto: Prototype, path):
    """4. Privacy zoning: module-level privacy + internal gradient."""
    fig, ax = plt.subplots(figsize=(10, 7))
    _site_frame(ax, proto)
    for m in proto.modules:
        _module_box(ax, m, _PRIV_COLOR[m.privacy], show_parts=True, label=True)
    handles = [Rectangle((0, 0), 1, 1, facecolor=_PRIV_COLOR[i], edgecolor="k")
               for i in range(5)]
    ax.legend(handles, [_PRIV_NAME[i] for i in range(5)], loc="upper right",
              fontsize=7, title="privacy")
    ax.set_title(f"Privacy zoning — {proto.candidate or 'phenotype'} "
                 f"(module + internal gradient; PUBLIC→PERSONAL)")
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def render_circulation(proto: Prototype, path):
    """Path networks through the open site between typed access anchors."""
    fig, ax = plt.subplots(figsize=(10, 7))
    _site_frame(ax, proto)
    for m in proto.modules:
        _module_box(ax, m, _MOD_COLOR.get(m.code, "#eee"), show_parts=False)
    circ_color = {"resident": "#bd7a13", "care_staff": "#7c58a5",
                  "service": "#596878", "visitor_community": "#168a9a",
                  "emergency": "#c64d45"}
    for net in proto.route_networks:
        for route in net["routes"]:
            if not route["points"]:
                continue
            pts = np.asarray(route["points"])
            ax.plot(pts[:, 0], pts[:, 1], color=circ_color[net["kind"]],
                    lw=1.35 if route["status"] != "CONTROLLED_INTERNAL" else 2,
                    alpha=0.7, zorder=1)
    handles = [Line2D([0], [0], color=color, lw=2) for color in circ_color.values()]
    ax.legend(handles, list(circ_color), loc="upper right", fontsize=7,
              title="user / access")
    ax.set_title(f"Circulation paths — {proto.candidate or 'phenotype'} "
                 f"(grid routes around built mass; widths and access {VERIFY})")
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def render_composition(proto: Prototype, path):
    """6. Module composition: counts + interface classes + program summary."""
    from collections import Counter
    cnt = Counter(m.code for m in proto.modules)
    iface = Counter(m.interface for m in proto.modules)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
    codes = sorted(cnt)
    ax1.barh(codes, [cnt[c] for c in codes],
             color=[_MOD_COLOR.get(c, "#eee") for c in codes], edgecolor="k")
    for i, c in enumerate(codes):
        ax1.text(cnt[c] + 0.05, i, str(cnt[c]), va="center", fontsize=8)
    ax1.set_title("module population"); ax1.grid(alpha=0.2, axis="x")
    ifs = sorted(iface)
    ax2.barh(ifs, [iface[i] for i in ifs],
             color=[_INTERFACE_COLOR.get(i, "#eee") for i in ifs], edgecolor="k")
    for i, v in enumerate(ifs):
        ax2.text(iface[v] + 0.05, i, str(iface[v]), va="center", fontsize=8)
    ax2.set_title("interface classes"); ax2.grid(alpha=0.2, axis="x")
    fig.suptitle(f"Composition — {proto.candidate or 'phenotype'} · {proto.program} "
                 f"· area proxy {proto.gfa} m²")
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def render_objectives(proto: Prototype, path):
    """7. Objective profile: radar of the 9 objectives (1-objective = performance)."""
    vals = [proto.objectives[n] for n in OBJ_NAMES]
    perf = [1 - v for v in vals]
    ang = np.linspace(0, 2 * np.pi, 9, endpoint=False).tolist(); ang += ang[:1]
    perf += perf[:1]
    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={"polar": True})
    ax.plot(ang, perf, color="#0284c7", lw=2); ax.fill(ang, perf, color="#0284c7", alpha=0.15)
    ax.set_xticks(ang[:-1]); ax.set_xticklabels([n.split("_")[0] for n in OBJ_NAMES], fontsize=8)
    ax.set_ylim(0, 1); ax.set_yticklabels([])
    worst = OBJ_NAMES[int(np.argmax(vals))]; best = OBJ_NAMES[int(np.argmin(vals))]
    ax.set_title(f"Objective profile — {proto.candidate or 'phenotype'} "
                 f"(1−objective; outer=better)\nstrongest {best.split('_')[0]} · weakest {worst.split('_')[0]}",
                 pad=18)
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def render_sightlines(proto: Prototype, path):
    """Sensitive sightline diagnostic: sampled exposure versus screening."""
    fig, ax = plt.subplots(figsize=(10, 7))
    _site_frame(ax, proto)
    for m in proto.modules:
        priv_col = "#fb7185" if m.code in PRIVATE else _MOD_COLOR.get(m.code, "#eee")
        _module_box(ax, m, priv_col, show_parts=False)
    n_exp = 0
    for sl in proto.sightlines:
        a = proto.modules[sl.from_id]; b = proto.modules[sl.to_id]
        if sl.exposed:
            n_exp += 1
            ax.plot([a.x, b.x], [a.y, b.y], color="#dc2626", lw=2.0, ls="-",
                    alpha=0.85, zorder=5)
            mx, my = (a.x + b.x) / 2, (a.y + b.y) / 2
            ax.plot([mx], [my], marker="x", color="#dc2626", ms=8, mew=2.5, zorder=6)
        else:
            ax.plot([a.x, b.x], [a.y, b.y], color="#16a34a", lw=1.2, ls="--",
                    alpha=0.5, zorder=1)
    handles = [Line2D([0], [0], color="#dc2626", lw=2),
               Line2D([0], [0], color="#16a34a", lw=1.2, ls="--")]
    ax.legend(handles, [f"EXPOSED (screening req.) {VERIFY}",
                        f"screened by built mass"], loc="upper right", fontsize=8)
    ax.set_title(f"Sensitive sightlines — {proto.candidate or 'phenotype'} "
                 f"({n_exp}/{len(proto.sightlines)} pairs EXPOSED in sampled rays; "
                 f"diagrammatic {VERIFY})")
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def render_open_space(proto: Prototype, path):
    """Open-space structure: COURTYARD / POCKET COURT / OPEN LANDSCAPE by enclosure."""
    fig, ax = plt.subplots(figsize=(10, 7))
    _site_frame(ax, proto)
    for m in proto.modules:
        _module_box(ax, m, _MOD_COLOR.get(m.code, "#eee"), show_parts=False)
    _OSP_COL = {"COURTYARD": "#16a34a", "POCKET COURT / THRESHOLD EDGE": "#f59e0b",
                "OPEN LANDSCAPE": "#38bdf8"}
    _OSP_MARK = {"COURTYARD": "o", "POCKET COURT / THRESHOLD EDGE": "s",
                 "OPEN LANDSCAPE": "^"}
    seen = set()
    for s in proto.open_spaces:
        col = _OSP_COL.get(s.space_type, "#888")
        mk_ = _OSP_MARK.get(s.space_type, "o")
        size = 60 + 6 * s.area_cells
        ax.scatter([s.cx], [s.cy], s=size, marker=mk_, facecolor="none",
                   edgecolor=col, lw=2.0, zorder=4)
        ax.text(s.cx, s.cy, f"{s.space_type.split(' / ')[0].title()}\nenc={s.enclosure}",
                ha="center", va="center", fontsize=5, color=col, zorder=5)
        seen.add(s.space_type)
    handles = [Line2D([0], [0], marker=_OSP_MARK[t], color="w", markerfacecolor="none",
                          markeredgecolor=_OSP_COL[t], ms=10, lw=0) for t in seen]
    ax.legend(handles, [t.title() for t in seen], loc="upper right", fontsize=7,
              title="open space (schematic)")
    ax.set_title(f"Open-space structure — {proto.candidate or 'phenotype'} "
                 f"(by enclosure degree; schematic)")
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def render_module_detail(proto: Prototype, path, n_panels: int = 6):
    """Internal module plan diagrams: enlarged kit-of-parts for key modules."""
    # prefer architecturally significant modules (domestic/care/public first)
    prio = {PUB: 0, DOM: 1, CTRL: 2, SHR: 3, PER: 4}
    mods = sorted(proto.modules, key=lambda m: (prio.get(m.privacy, 3),
                                                -MODULES[m.code].area))
    # unique codes, keep first occurrence
    seen, panels = set(), []
    for m in mods:
        if m.code not in seen:
            seen.add(m.code); panels.append(m)
        if len(panels) >= n_panels:
            break
    ncol = 3; nrow = int(np.ceil(len(panels) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(13, 4.2 * nrow))
    axes = np.atleast_1d(axes).ravel()
    for ax in axes:
        ax.set_xticks([]); ax.set_yticks([]); ax.set_aspect("equal")
    for k, m in enumerate(panels):
        ax = axes[k]
        x0, y0 = m.x - m.w / 2, m.y - m.d / 2
        ax.add_patch(Rectangle((0, 0), m.w, m.d, facecolor=_MOD_COLOR.get(m.code, "#eee"),
                               edgecolor="k", lw=1.5, alpha=0.4))
        for p in m.parts:
            ax.add_patch(Rectangle((p.x - x0, p.y - y0), p.w, p.d,
                                   facecolor=_PRIV_COLOR[p.privacy], edgecolor="white",
                                   lw=0.6, alpha=0.7))
            ax.text(p.x - x0 + p.w / 2, p.y - y0 + p.d / 2,
                    f"{p.name}\n{p.provenance.split(']')[0]}]", ha="center", va="center",
                    fontsize=4.5)
        ex, ey = m.entrance_anchor
        ax.plot([ex - x0], [ey - y0], marker="v", color="k", ms=7)
        ax.set_title(f"{m.code} {m.name} (x{m.floors}) · {_PRIV_NAME[m.privacy]}",
                     fontsize=9)
        ax.set_xlim(-1, m.w + 1); ax.set_ylim(-1, m.d + 1)
    fig.suptitle(f"Internal module plans — {proto.candidate or 'phenotype'} "
                 f"(kit-of-parts zones, tagged; ▼=entrance)", fontsize=11)
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def render_parallel(proto: Prototype, path):
    """Performance profile as parallel coordinates across the 9 objectives."""
    vals = [proto.objectives[n] for n in OBJ_NAMES]
    fig, ax = plt.subplots(figsize=(11, 4.5))
    xs = range(9)
    ax.plot(xs, vals, marker="o", color="#0284c7", lw=2, ms=7)
    for x, v in zip(xs, vals):
        ax.text(x, v + 0.02, f"{v:.2f}", ha="center", fontsize=7)
    ax.set_xticks(list(xs)); ax.set_xticklabels([n.split("_")[0] for n in OBJ_NAMES], fontsize=8)
    ax.set_ylim(0, max(vals) * 1.15 + 0.05); ax.invert_yaxis()  # lower=better at top
    ax.grid(alpha=0.25, axis="y")
    ax.set_ylabel("objective value (lower = better)")
    ax.set_title(f"Performance profile (parallel) — {proto.candidate or 'phenotype'}")
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def _legend_provenance(fig):
    fig.text(0.01, 0.005,
             f"green=MUST {CORPUS}  blue=NEAR {CORPUS}  purple=SCREENED {HYP}  "
             f"▲=entrance anchor {HYP}  internal zones=kit-of-parts (tagged)",
             fontsize=6, color="#444")


RENDERERS = [("plan", render_plan), ("axonometric", render_axonometric),
             ("floor_plans", render_floor_plans),
             ("stacking", render_stacking), ("privacy", render_privacy),
             ("circulation", render_circulation), ("sightlines", render_sightlines),
             ("open_space", render_open_space), ("module_detail", render_module_detail),
             ("composition", render_composition),
             ("objective_profile", render_objectives), ("parallel", render_parallel)]


def render_suite(proto: Prototype, outdir: str, stem: str) -> dict:
    """Render all schematic figures + JSON traceability. Returns {name: path}."""
    os.makedirs(outdir, exist_ok=True)
    import json
    outs = {}
    for name, fn in RENDERERS:
        p = os.path.join(outdir, f"{stem}_{name}.png")
        fn(proto, p)
        outs[name] = p
    jp = os.path.join(outdir, f"{stem}_prototype.json")
    with open(jp, "w") as f:
        json.dump(proto.to_dict(), f, indent=2)
    outs["json"] = jp
    return outs
