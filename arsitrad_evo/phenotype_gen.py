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
    render_suite(proto, outdir)  -> writes the 7 schematic figures + JSON
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
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
from .objectives import OBJECTIVES
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


@dataclass
class ModuleNode:
    inst_id: int; code: str; name: str
    x: float; y: float; w: float; d: float
    floors: int; privacy: int; orientation: str
    entrance_anchor: tuple; connection_anchors: list
    interface: str                      # public | protected | service | domestic
    parts: list = field(default_factory=list)   # list[Part]


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


@dataclass
class OpenSpace:
    """Open-space / landscape zone classified by DEGREE OF ENCLOSURE (schematic):
      3-4 enclosing sides -> COURTYARD
      2 enclosing sides    -> POCKET COURT / THRESHOLD EDGE
      0-1 enclosing sides  -> OPEN LANDSCAPE
    Explicitly diagrammatic, not a surveyed open space."""
    cx: float; cy: float; area_cells: int; enclosure: int
    space_type: str; provenance: str


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
    objectives: dict = field(default_factory=dict)
    provenance_log: list = field(default_factory=list)
    to_verify: list = field(default_factory=list)
    design_hypotheses: list = field(default_factory=list)

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
                    rep_index: int = -1, seed=None) -> Prototype:
    insts = ph.instances
    objs = ph.objectives if ph.objectives is not None else np.zeros(len(OBJ_NAMES))
    proto = Prototype(
        candidate=candidate_label, rep_index=rep_index, seed=seed,
        program=f"R4x{ph.n_R4} res={ph.residents} day={ph.day_users}",
        site_w=C.SITE_W, site_h=C.SITE_H,
        residents=ph.residents, day_users=ph.day_users, gfa=round(ph.gfa, 1),
        footprint=round(ph.footprint, 1), landscape_frac=round(ph.landscape_frac, 3),
        landscape_area=round(ph.landscape_area, 1),
        objectives={OBJ_NAMES[i]: round(float(objs[i]), 3)
                    for i in range(len(OBJ_NAMES))},
    )

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
        # expand internal kit-of-parts into site coordinates (relative zones)
        x0, y0 = inst.x - inst.w / 2, inst.y - inst.d / 2
        for (pname, rx, ry, rw, rh, priv, prov, note) in KIT.get(inst.code, []):
            node.parts.append(Part(pname, x0 + rx * inst.w, y0 + ry * inst.d,
                                   rw * inst.w, rh * inst.d, priv, prov, note))
            if prov == VERIFY:
                proto.to_verify.append(f"{inst.code}:{pname} — {note}")
            elif prov == HYP:
                proto.design_hypotheses.append(f"{inst.code}:{pname} — {note}")
        proto.modules.append(node)

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
    for sl in proto.sightlines:
        if sl.exposed:
            proto.to_verify.append(
                f"EXPOSED sightline {sl.from_code}->{sl.to_code} ({sl.relation}): "
                f"direct segment unobstructed at {sl.distance:.1f} m; screening required "
                f"[TO VERIFY].")
    proto.provenance_log.append(
        f"sightline exposure checked geometrically (segment-vs-rect) {HYP}; "
        f"diagrammatic, not a regulatory sightline study")

    # --- open spaces classified by DEGREE OF ENCLOSURE (schematic) ---
    proto.open_spaces = _classify_open_spaces(insts)
    proto.courtyards = [{"cx": s.cx, "cy": s.cy, "sides_enclosed": s.enclosure,
                         "space_type": s.space_type, "provenance": s.provenance}
                        for s in proto.open_spaces if s.space_type == "COURTYARD"]
    proto.provenance_log.append(
        f"open spaces classified by enclosure degree: 3-4 sides=COURTYARD, "
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

    # --- building grouping (connectivity clusters of MUST/NEAR) ---
    proto.groupings = _groupings(proto)
    proto.provenance_log.append(f"building groupings from MUST/NEAR connectivity {HYP}")

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

    For each sensitive (private <-> public-facing) pair, cast the straight
    segment between the two module rectangles' nearest points and test whether
    any OTHER built module's rectangle intersects it (i.e. screens it). Exposed
    = no intervening built mass. Diagrammatic only [TO VERIFY] — not a
    regulatory sightline/angle study."""
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
        screened_by = []
        for k, other in enumerate(insts):
            if k in (i, j):
                continue
            if _seg_intersects_rect(pa, pb, _rect_of(other)):
                screened_by.append(other.code)
        out.append(Sightline(
            from_id=i, from_code=a.code, to_id=j, to_code=b.code,
            relation=rel_label, distance=round(dist, 2),
            exposed=(len(screened_by) == 0), screened_by=sorted(set(screened_by)),
            provenance=VERIFY))
    return out


def _clamp_point_to_rect(p, rect):
    x0, y0, x1, y1 = rect
    return (min(max(p[0], x0), x1), min(max(p[1], y0), y1))


def _classify_open_spaces(insts: list[Instance], res: int = 24) -> list[OpenSpace]:
    """Classify open-space cells by DEGREE OF ENCLOSURE (schematic, [DESIGN
    HYPOTHESIS]):
      3-4 enclosing sides -> COURTYARD
      2  enclosing sides  -> POCKET COURT / THRESHOLD EDGE
      0-1 enclosing sides -> OPEN LANDSCAPE

    Enclosure is measured by casting a ray from the cell in each of the 4
    cardinal directions and counting how many rays strike built mass before
    leaving the site (a "wall" on that side). This captures courtyards enclosed
    by buildings a short distance away, not merely cells touching a building.
    Contiguous cells of the same type are merged into one zone (centroid +
    area_cells)."""
    cw, ch = C.SITE_W / res, C.SITE_H / res
    built = np.zeros((res, res), dtype=bool)
    for inst in insts:
        i0 = max(0, int((inst.x - inst.w / 2) / cw)); i1 = min(res, int((inst.x + inst.w / 2) / cw) + 1)
        j0 = max(0, int((inst.y - inst.d / 2) / ch)); j1 = min(res, int((inst.y + inst.d / 2) / ch) + 1)
        built[i0:i1, j0:j1] = True

    def enc(i, j):
        """Count of 4 cardinal rays (W,E,S,N) that hit built mass before site edge."""
        s = 0
        if built[:i, j].any():            # West ray
            s += 1
        if built[i+1:, j].any():          # East ray
            s += 1
        if built[i, :j].any():            # South ray
            s += 1
        if built[i, j+1:].any():          # North ray
            s += 1
        return s

    def stype(e):
        if e >= 3: return "COURTYARD"
        if e == 2: return "POCKET COURT / THRESHOLD EDGE"
        return "OPEN LANDSCAPE"

    typ = np.full((res, res), "", dtype=object)
    for i in range(res):
        for j in range(res):
            if not built[i, j]:
                typ[i, j] = stype(enc(i, j))

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
            cx = float(np.mean([(c + 0.5) * cw for c, _ in cells]))
            cy = float(np.mean([(r + 0.5) * ch for _, r in cells]))
            e = 4 if t == "COURTYARD" else (2 if t.startswith("POCKET") else 1)
            zones.append(OpenSpace(cx=round(cx, 1), cy=round(cy, 1),
                                   area_cells=len(cells), enclosure=e,
                                   space_type=t, provenance=HYP))
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


def _groupings(proto: Prototype) -> list:
    """Connected components over MUST/NEAR edges = building groups."""
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
        if cn.kind in (MUST, NEAR):
            union(cn.a_id, cn.b_id)
    groups = {}
    for m in proto.modules:
        groups.setdefault(find(m.inst_id), []).append(m.code)
    return [{"group": k, "modules": sorted(v), "provenance": HYP}
            for k, v in enumerate(groups.values())]


# ---------------------------------------------------------------------------
# Rendering suite (7 schematic figures per phenotype)
# ---------------------------------------------------------------------------
def _module_box(ax, m: ModuleNode, facecolor, show_parts=False, label=True):
    ax.add_patch(Rectangle((m.x - m.w / 2, m.y - m.d / 2), m.w, m.d,
                           facecolor=facecolor, edgecolor="k", alpha=0.85, lw=1.0))
    if show_parts:
        for p in m.parts:
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
                 f"{proto.program} · GFA {proto.gfa} m² · landscape {proto.landscape_frac*100:.0f}%")
    _legend_provenance(fig)
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def render_axonometric(proto: Prototype, path):
    """2. Exploded axonometric/isometric: modules lifted by privacy level,
    internal parts hinted. Diagrammatic massing only (no structural system)."""
    fig = plt.figure(figsize=(11, 8))
    ax = fig.add_subplot(111, projection="3d")
    for m in proto.modules:
        z0 = m.privacy * 3.0                      # explode vertically by privacy level
        hgt = m.floors * 3.0
        x0, y0 = m.x - m.w / 2, m.y - m.d / 2
        _bar3(ax, x0, y0, z0, m.w, m.d, hgt, _MOD_COLOR.get(m.code, "#eee"))
        ax.text(m.x, m.y, z0 + hgt + 0.6, m.code, ha="center", fontsize=7, weight="bold")
    ax.set_box_aspect((proto.site_w, proto.site_h, 30))
    ax.view_init(elev=28, azim=-58)
    ax.set_axis_off()
    ax.set_title(f"Exploded axonometric — {proto.candidate or 'phenotype'} "
                 f"(lifted by privacy level; diagrammatic massing, no structural system)")
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
    """5. Circulation skeleton: resident / care / service / public networks."""
    fig, ax = plt.subplots(figsize=(10, 7))
    _site_frame(ax, proto)
    for m in proto.modules:
        _module_box(ax, m, _MOD_COLOR.get(m.code, "#eee"), show_parts=False)
    circ_color = {"resident": "#f59e0b", "care": "#fb7185",
                  "service": "#64748b", "public": "#38bdf8", "controlled": "#a78bfa"}
    seen = set()
    for cn in proto.connections:
        a = proto.modules[cn.a_id]; b = proto.modules[cn.b_id]
        for ckind in cn.circulations:
            col = circ_color.get(ckind, "#888")
            ax.plot([a.x, b.x], [a.y, b.y], color=col, lw=2.0, alpha=0.6, zorder=1)
            seen.add(ckind)
    handles = [Line2D([0], [0], color=circ_color[k], lw=2.5) for k in seen]  # type: ignore[attr-defined]
    ax.legend(handles, list(seen), loc="upper right", fontsize=8, title="circulation")
    ax.set_title(f"Circulation skeleton — {proto.candidate or 'phenotype'} "
                 f"(resident/care/service/public)")
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
                 f"· GFA {proto.gfa} m²")
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
    """Safeguarded sightline diagram: private->public exposure, screened vs exposed."""
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
    ax.set_title(f"Safeguarded sightlines — {proto.candidate or 'phenotype'} "
                 f"({n_exp}/{len(proto.sightlines)} private-public EXPOSED; "
                 f"diagrammatic, not a regulatory study)")
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
