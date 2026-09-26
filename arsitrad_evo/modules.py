"""Threshold module library & relationship rules.

Data grounded in the PA5 corpus (district workbook + adjacency matrix), tagged
DESIGN HYPOTHESIS / TO VERIFY. Areas are net m^2. Phase-1 modules are
axis-aligned rectangles defined by (w, d); w*d ~= net area.
"""
from __future__ import annotations
from dataclasses import dataclass

# Privacy levels (ordered). Lower index = more public.
PRIVACY = ["PUBLIC", "CONTROLLED", "SHARED", "DOMESTIC", "PERSONAL"]
PUB, CTRL, SHR, DOM, PER = range(5)


@dataclass(frozen=True)
class ModuleType:
    code: str
    name: str
    w: float                 # rect width  (m)  [DH]
    d: float                 # rect depth  (m)  [DH]
    area: float              # net area    (m^2) [CORPUS/DH]
    privacy: int             # PRIVACY index
    developmental: bool      # True = essential DNA, must be present
    repeatable: bool         # True = may appear multiple times (R4)
    max_floors: int          # stacking cap (R4 = 1)
    stackable_above_service: bool  # may sit above F0/M0? (always False for safety)


# --- Module catalogue -------------------------------------------------------
# w*d chosen to approximate net area as a buildable rectangle [DH].
MODULES: dict[str, ModuleType] = {
    "A0": ModuleType("A0", "Civic Threshold",        11.5, 8.0,  92, CTRL, True,  False, 1, False),
    "B0": ModuleType("B0", "Care & Safeguarding",    11.5, 8.0,  92, CTRL, True,  False, 1, False),
    "C0": ModuleType("C0", "Everyday Commons",       14.0, 10.7, 150, SHR, True,  False, 2, False),
    "R4": ModuleType("R4", "Domestic Cluster",       11.0, 8.0,  88, DOM, True,  True,  1, False),
    "E0": ModuleType("E0", "Staff Base",              9.5, 8.0,  76, CTRL, True,  False, 1, False),
    "F0": ModuleType("F0", "Service Edge",           18.0, 9.6, 173, CTRL, True,  False, 1, False),
    "M0": ModuleType("M0", "Technical Commons",      10.0, 8.2,  82, CTRL, True,  False, 1, False),
    "H0": ModuleType("H0", "Learning House",         12.0, 9.0, 108, SHR, False, False, 2, False),
    "I0": ModuleType("I0", "Reflection Pavilion",     6.0, 6.0,  36, SHR, False, False, 1, False),
    "J0": ModuleType("J0", "Livelihood House",       13.5, 9.0, 122, SHR, False, False, 1, False),
    "K0": ModuleType("K0", "Community House",        13.5, 8.9, 120, PUB, False, False, 1, False),
    "L0": ModuleType("L0", "Transition House",        9.5, 7.4,  70, CTRL, False, False, 1, False),
}

# Modules always present (developmental DNA), in fixed decode order.
# G0 (landscape) is handled as site fraction, not a placed rectangle.
ALWAYS_PRESENT = ["A0", "B0", "C0", "E0", "F0", "M0"]
# Optional modules keyed by their has_* gene.
OPTIONAL = {"H0": "has_H0", "J0": "has_J0", "K0": "has_K0",
            "I0": "has_I0", "L0": "has_L0"}

# Relationship values for adjacency.
MUST, NEAR, SCREENED, AVOID, PROHIBITED = "MUST", "NEAR", "SCREENED", "AVOID", "PROHIBITED"

# Adjacency matrix over the placed module codes. Symmetric. [CORPUS -> DH]
# (G0/N0 handled separately; not placed rectangles here.)
_CODES = ["A0", "B0", "C0", "R4", "E0", "F0", "M0", "H0", "J0", "K0", "L0"]
_M = {
    ("A0", "B0"): MUST, ("A0", "C0"): NEAR, ("A0", "R4"): SCREENED,
    ("A0", "E0"): NEAR, ("A0", "F0"): AVOID, ("A0", "H0"): NEAR,
    ("A0", "J0"): NEAR, ("A0", "K0"): NEAR, ("A0", "L0"): NEAR, ("A0", "M0"): AVOID,
    ("B0", "C0"): NEAR, ("B0", "R4"): MUST, ("B0", "E0"): MUST,
    ("B0", "F0"): AVOID, ("B0", "H0"): NEAR, ("B0", "J0"): AVOID,
    ("B0", "K0"): AVOID, ("B0", "L0"): MUST, ("B0", "M0"): AVOID,
    ("C0", "R4"): MUST, ("C0", "E0"): NEAR, ("C0", "F0"): SCREENED,
    ("C0", "H0"): NEAR, ("C0", "J0"): SCREENED, ("C0", "K0"): SCREENED,
    ("C0", "L0"): NEAR, ("C0", "M0"): AVOID,
    ("R4", "E0"): NEAR, ("R4", "F0"): PROHIBITED, ("R4", "M0"): PROHIBITED,
    ("R4", "H0"): SCREENED, ("R4", "J0"): AVOID, ("R4", "K0"): PROHIBITED,
    ("R4", "L0"): NEAR,
    ("E0", "F0"): NEAR, ("E0", "M0"): NEAR, ("E0", "H0"): AVOID,
    ("E0", "J0"): AVOID, ("E0", "K0"): AVOID, ("E0", "L0"): NEAR,
    ("F0", "M0"): MUST, ("F0", "H0"): AVOID, ("F0", "J0"): NEAR,
    ("F0", "K0"): AVOID, ("F0", "L0"): AVOID,
    ("M0", "H0"): AVOID, ("M0", "J0"): NEAR, ("M0", "K0"): AVOID, ("M0", "L0"): AVOID,
    ("H0", "J0"): NEAR, ("H0", "K0"): NEAR, ("H0", "L0"): NEAR,
    ("J0", "K0"): NEAR, ("J0", "L0"): AVOID,
    ("K0", "L0"): AVOID,
}


def relation(a: str, b: str) -> str | None:
    """Required relationship between module codes a,b (None if unspecified)."""
    if a == b:
        return None
    return _M.get((a, b)) or _M.get((b, a))


# Public-edge and private-territory module sets for shortcut/hierarchy checks.
PUBLIC_MODULES = {"K0", "A0"}          # public-facing entry points
PRIVATE_MODULES = {"R4"}               # domestic/personal territory
CARE_MODULES = {"B0", "E0"}            # must reach R4
SERVICE_MODULES = {"F0", "M0"}         # independent service access
CONTROLLED_GATE = {"A0", "B0"}         # legitimate public->private gates
