"""Genotype -> Phenotype codec.

Genotype: fixed-length mixed real/integer vector. The first N_GENE_STRUCT genes
encode structure (populations, floors, landscape, depths, reserve). The tail
encodes (x, y) centroids for the maximum possible instance count; unused slots
are masked at decode time based on which modules are actually present.

Phenotype: decoded spatial configuration (placed rectangles, derived metrics,
adjacency graph, privacy assignment) suitable for constraint & objective
evaluation. Phase-1 geometry only [DH].
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np

from . import config as C
from .modules import MODULES, ALWAYS_PRESENT, OPTIONAL, PRIVACY, PUB, PER

# --- Structural gene layout (fixed length) ---------------------------------
# index, name, type('int'/'real'), lo, hi
STRUCT_GENES = [
    ("n_R4",            "int",  C.N_R4_MIN,        C.N_R4_MAX),
    ("has_H0",          "int",  0,                 1),
    ("has_J0",          "int",  0,                 1),
    ("has_K0",          "int",  0,                 1),
    ("has_I0",          "int",  0,                 1),
    ("has_L0",          "int",  0,                 1),
    ("public_intensity","int",  0,                 3),
    ("floors_C0",       "int",  1,                 2),
    ("floors_H0",       "int",  1,                 2),
    ("landscape_frac",  "real", C.LANDSCAPE_MIN,   C.LANDSCAPE_MAX),
    ("service_depth",   "real", 8.0,               20.0),
    ("buffer_depth",    "real", 10.0,              30.0),
    ("reserve_area",    "real", 90.0,              270.0),
]
N_STRUCT = len(STRUCT_GENES)

# Maximum instances: ALWAYS_PRESENT(6) + R4xN_R4_MAX(4) + 5 optional = 15.
MAX_INSTANCES = len(ALWAYS_PRESENT) + C.N_R4_MAX + len(OPTIONAL)
# Each instance contributes 2 placement genes (x, y).
N_GENES = N_STRUCT + 2 * MAX_INSTANCES

# Gene bounds arrays (for NSGA-II variation operators).
def gene_bounds():
    lo, hi, is_int = [], [], []
    for _, t, a, b in STRUCT_GENES:
        lo.append(a); hi.append(b); is_int.append(t == "int")
    for _ in range(MAX_INSTANCES):
        lo += [0.0, 0.0]; hi += [C.SITE_W, C.SITE_H]; is_int += [False, False]
    return np.array(lo), np.array(hi), np.array(is_int)


def instance_slots(n_R4: int, flags: dict[str, int]) -> list[str]:
    """Ordered list of module codes actually placed, matching placement-gene order.

    Order: ALWAYS_PRESENT, then R4 x n_R4, then present optionals (fixed order).
    """
    slots = list(ALWAYS_PRESENT)
    slots += ["R4"] * int(n_R4)
    for code in ["H0", "J0", "K0", "I0", "L0"]:
        if flags.get(OPTIONAL[code], 0):
            slots.append(code)
    return slots


@dataclass
class Instance:
    code: str
    x: float
    y: float
    w: float
    d: float
    area: float
    floors: int
    privacy: int
    @property
    def footprint(self) -> float:
        return self.w * self.d


@dataclass
class Phenotype:
    genes: np.ndarray
    instances: list[Instance] = field(default_factory=list)
    n_R4: int = 0
    residents: int = 0
    day_users: int = 0
    gfa: float = 0.0
    footprint: float = 0.0
    landscape_area: float = 0.0
    reserve_area: float = 0.0
    landscape_frac: float = 0.0
    public_intensity: int = 0
    # filled during evaluation
    objectives: np.ndarray | None = None
    cv: float = 0.0            # hard constraint violation (drives feasibility)
    soft_cv: float = 0.0       # MUST-adjacency shortfall (selection tie-break)
    feasible: bool = True
    rank: int = 0
    crowding: float = 0.0

    def by_code(self, code: str) -> list[Instance]:
        return [i for i in self.instances if i.code == code]

    def has(self, code: str) -> bool:
        return any(i.code == code for i in self.instances)


def decode(genes: np.ndarray) -> Phenotype:
    """Decode a genotype vector into a Phenotype (structure + geometry)."""
    g = np.asarray(genes, dtype=float).copy()
    # round structural ints
    for i, (_, t, a, b) in enumerate(STRUCT_GENES):
        if t == "int":
            g[i] = int(round(np.clip(g[i], a, b)))
        else:
            g[i] = float(np.clip(g[i], a, b))

    s = {name: g[i] for i, (name, _, _, _) in enumerate(STRUCT_GENES)}
    n_R4 = int(s["n_R4"])
    flags = {k: int(s[k]) for k in ["has_H0", "has_J0", "has_K0", "has_I0", "has_L0"]}
    slots = instance_slots(n_R4, flags)

    ph = Phenotype(genes=g)
    ph.n_R4 = n_R4
    ph.residents = n_R4 * C.RESIDENTS_PER_CLUSTER
    ph.landscape_frac = float(s["landscape_frac"])
    ph.reserve_area = float(s["reserve_area"])
    ph.landscape_area = ph.landscape_frac * C.SITE_AREA
    # public_intensity is DERIVED (coherence): count of public-facing modules
    # actually present (H0+J0+K0), capped at 3. Overrides the raw gene so a
    # phenotype can never claim high intensity with no public modules. [DH]
    ph.public_intensity = min(3, flags["has_H0"] + flags["has_J0"] + flags["has_K0"])

    # decode placements for active slots
    for k, code in enumerate(slots):
        x = float(np.clip(g[N_STRUCT + 2 * k],     0, C.SITE_W))
        y = float(np.clip(g[N_STRUCT + 2 * k + 1], 0, C.SITE_H))
        mt = MODULES[code]
        floors = 1
        if code == "C0":
            floors = int(s["floors_C0"])
        elif code == "H0":
            floors = int(s["floors_H0"]) if flags["has_H0"] else 1
        ph.instances.append(Instance(code, x, y, mt.w, mt.d, mt.area, floors, mt.privacy))

    # derived metrics
    ph.gfa = sum(i.area * i.floors for i in ph.instances)
    # footprint = union approx: sum of ground footprints (overlaps removed later
    # by penalty; here use sum as upper bound, refined in constraints).
    ph.footprint = sum(i.footprint for i in ph.instances)
    # day users: base + per public/optional module [DH]
    ph.day_users = 8 + sum(
        C.DAY_USER_PER_EXTRA_MODULE for code in ["H0", "J0", "K0"] if ph.has(code)
    )
    return ph


def random_genotype(rng: np.random.Generator) -> np.ndarray:
    lo, hi, is_int = gene_bounds()
    g = lo + (hi - lo) * rng.random(len(lo))
    g[is_int] = np.round(g[is_int])
    return g
