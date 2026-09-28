"""Enhanced module library v4 — function × size × modularity × capacity.

Extends v3 ModuleType with architectural mini-typology grammars, site-aware
placement rules, and capacity metadata. All entries grounded in PA5 corpus
with [DESIGN HYPOTHESIS] / [TO VERIFY] provenance tags.

Module families:
  R4 = Domestic Cluster (residential)
  A0 = Arrival / Reception
  B0 = Care / Safeguarding
  C0 = Commons / Dining
  H0 = Learning / Education
  J0 = Livelihood / Workshop
  K0 = Community / Gathering
  I0 = Reflection / Prayer
  L0 = Transition / Threshold
  F0 = Service / Kitchen
  M0 = Maintenance / Utility
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ModularityCategory(Enum):
    DEVELOPMENTAL = "developmental"      # custom, one-off
    VARIATIONAL = "variational"          # parametric variations
    REPEATABLE = "repeatable"            # identical repetition


class SizeClass(Enum):
    SMALL = "S"
    MEDIUM = "M"
    LARGE = "L"


class AccessType(Enum):
    PUBLIC = "public"          # open to all
    CONTROLLED = "controlled"  # screened / gate
    PRIVATE = "private"        # residents / staff only
    SERVICE = "service"        # back-of-house


class RotationPolicy(Enum):
    NONE = "none"              # fixed orientation
    ORTHOGONAL = "orthogonal"  # 0°, 90°
    FULL = "full"              # 0°, 90°, 180°, 270°


@dataclass(frozen=True)
class ModuleGrammar:
    """Internal mini-typology grammar — simplified spatial organization.
    
    Not detailed design; diagrammatic internal structure only.
    All positions relative to module bounding box (0-1 normalized).
    """
    # Core zones
    entry_threshold: tuple[float, float, float, float] = (0.0, 0.0, 0.2, 0.3)   # x, y, w, d
    shared_space: tuple[float, float, float, float] = (0.2, 0.0, 0.5, 0.6)
    personal_territory: tuple[float, float, float, float] = (0.0, 0.3, 0.4, 0.4)
    service_zone: tuple[float, float, float, float] = (0.7, 0.0, 0.3, 0.3)
    retreat_edge: tuple[float, float, float, float] = (0.0, 0.6, 0.3, 0.4)
    
    # Circulation
    circulation_spine: tuple[float, float, float, float] = (0.4, 0.0, 0.2, 1.0)
    
    # Environmental
    light_well: Optional[tuple[float, float, float, float]] = None
    outdoor_interface: Optional[tuple[float, float, float, float]] = None
    
    # Metadata
    provenance: str = "[DESIGN HYPOTHESIS]"
    description: str = ""


@dataclass(frozen=True)
class ModuleTypeV4:
    """Extended module type with architectural grammar and site rules."""
    # Identity
    code: str                    # e.g. "R4", "R4-M", "A0"
    name: str
    family: str                  # e.g. "R4", "A0"
    size_class: SizeClass
    
    # Geometry
    w: float                     # metres
    d: float                     # metres
    area: float                  # m² (net)
    max_floors: int
    
    # Capacity
    capacity_residents: int = 0
    capacity_day_users: int = 0
    capacity_staff: int = 0
    
    # Modularity
    modularity: ModularityCategory = ModularityCategory.DEVELOPMENTAL
    repeatable: bool = False
    min_count: int = 0
    max_count: int = 0
    
    # Privacy
    privacy_level: int = 0       # 0=public, 4=personal (from v3 PRIVACY)
    
    # Site placement rules
    ground_required: bool = False
    stackable_above: bool = False
    stackable_below: bool = False
    rotation_policy: RotationPolicy = RotationPolicy.NONE
    allowed_rotations: tuple[int, ...] = (0,)  # degrees
    
    # Access faces (which edges can have entrances)
    access_faces: tuple[str, ...] = ("S",)     # N, S, E, W
    service_faces: tuple[str, ...] = ("N",)    # back-of-house edges
    open_edges: tuple[str, ...] = ("S",)       # edges that open to landscape
    
    # Grammar
    grammar: Optional[ModuleGrammar] = None
    
    # Provenance
    provenance: str = "[DESIGN HYPOTHESIS]"
    description: str = ""
    
    def rotated_dimensions(self, rotation: int) -> tuple[float, float]:
        """Return (w, d) after rotation."""
        if rotation in (0, 180):
            return (self.w, self.d)
        elif rotation in (90, 270):
            return (self.d, self.w)
        else:
            raise ValueError(f"Invalid rotation: {rotation}")


# =============================================================================
# GRAMMAR DEFINITIONS
# =============================================================================

_GRAMMAR_R4 = ModuleGrammar(
    entry_threshold=(0.0, 0.0, 0.25, 0.35),
    shared_space=(0.25, 0.0, 0.50, 0.65),
    personal_territory=(0.0, 0.35, 0.40, 0.40),
    service_zone=(0.75, 0.0, 0.25, 0.35),      # WASH
    retreat_edge=(0.0, 0.65, 0.35, 0.35),      # porch / retreat
    circulation_spine=(0.40, 0.0, 0.20, 1.0),
    light_well=(0.60, 0.40, 0.20, 0.20),
    outdoor_interface=(0.0, 0.65, 0.35, 0.35),
    provenance="[DESIGN HYPOTHESIS]",
    description="Domestic cluster: entry → shared domestic → personal territory; WASH service; retreat/porch edge",
)

_GRAMMAR_A0 = ModuleGrammar(
    entry_threshold=(0.0, 0.0, 0.30, 0.40),
    shared_space=(0.30, 0.0, 0.45, 0.70),
    personal_territory=(0.0, 0.0, 0.0, 0.0),   # N/A — public module
    service_zone=(0.75, 0.0, 0.25, 0.30),
    retreat_edge=(0.0, 0.70, 0.30, 0.30),
    circulation_spine=(0.45, 0.0, 0.10, 1.0),
    outdoor_interface=(0.0, 0.0, 0.30, 0.40),
    provenance="[DESIGN HYPOTHESIS]",
    description="Arrival: threshold → pause/wait → screened reception → orientation point",
)

_GRAMMAR_B0 = ModuleGrammar(
    entry_threshold=(0.0, 0.0, 0.20, 0.30),
    shared_space=(0.20, 0.0, 0.35, 0.50),      # intake
    personal_territory=(0.0, 0.30, 0.35, 0.45), # counselling / safeguarding
    service_zone=(0.55, 0.0, 0.25, 0.25),
    retreat_edge=(0.0, 0.75, 0.25, 0.25),
    circulation_spine=(0.35, 0.0, 0.15, 1.0),
    provenance="[DESIGN HYPOTHESIS]",
    description="Care: intake → counselling → safeguarding → response/support",
)

_GRAMMAR_C0 = ModuleGrammar(
    entry_threshold=(0.0, 0.0, 0.20, 0.25),
    shared_space=(0.20, 0.0, 0.55, 0.60),      # dining / everyday
    personal_territory=(0.0, 0.0, 0.0, 0.0),   # N/A
    service_zone=(0.75, 0.0, 0.25, 0.40),      # kitchen interface
    retreat_edge=(0.0, 0.60, 0.30, 0.40),      # indoor-outdoor commons
    circulation_spine=(0.40, 0.0, 0.20, 1.0),
    outdoor_interface=(0.0, 0.60, 0.30, 0.40),
    provenance="[DESIGN HYPOTHESIS]",
    description="Commons: shared dining → everyday activity → kitchen interface → indoor-outdoor commons",
)

_GRAMMAR_H0 = ModuleGrammar(
    entry_threshold=(0.0, 0.0, 0.20, 0.25),
    shared_space=(0.20, 0.0, 0.50, 0.55),      # learning / group activity
    personal_territory=(0.0, 0.25, 0.30, 0.40), # quiet study
    service_zone=(0.70, 0.0, 0.30, 0.25),      # storage
    retreat_edge=(0.0, 0.65, 0.25, 0.35),
    circulation_spine=(0.35, 0.0, 0.15, 1.0),
    provenance="[DESIGN HYPOTHESIS]",
    description="Learning: entry → group activity → quiet study → resource storage",
)

_GRAMMAR_J0 = ModuleGrammar(
    entry_threshold=(0.0, 0.0, 0.20, 0.30),
    shared_space=(0.20, 0.0, 0.55, 0.55),      # workshop / production
    personal_territory=(0.0, 0.0, 0.0, 0.0),   # N/A
    service_zone=(0.75, 0.0, 0.25, 0.35),      # storage / utility
    retreat_edge=(0.0, 0.55, 0.30, 0.45),      # market interface
    circulation_spine=(0.40, 0.0, 0.20, 1.0),
    outdoor_interface=(0.0, 0.55, 0.30, 0.45),
    provenance="[DESIGN HYPOTHESIS]",
    description="Livelihood: workshop → production → storage → market interface",
)

_GRAMMAR_K0 = ModuleGrammar(
    entry_threshold=(0.0, 0.0, 0.25, 0.30),
    shared_space=(0.25, 0.0, 0.55, 0.65),      # gathering / event
    personal_territory=(0.0, 0.0, 0.0, 0.0),   # N/A
    service_zone=(0.80, 0.0, 0.20, 0.30),
    retreat_edge=(0.0, 0.65, 0.35, 0.35),      # flexible / community interface
    circulation_spine=(0.45, 0.0, 0.10, 1.0),
    outdoor_interface=(0.0, 0.65, 0.35, 0.35),
    provenance="[DESIGN HYPOTHESIS]",
    description="Community: gathering → event → flexible use → community interface",
)

_GRAMMAR_I0 = ModuleGrammar(
    entry_threshold=(0.0, 0.0, 0.30, 0.40),
    shared_space=(0.30, 0.0, 0.40, 0.60),      # reflection / prayer
    personal_territory=(0.0, 0.40, 0.30, 0.40), # quiet / personal
    service_zone=(0.70, 0.0, 0.30, 0.20),
    retreat_edge=(0.0, 0.80, 0.40, 0.20),      # nature connection
    circulation_spine=(0.40, 0.0, 0.20, 1.0),
    outdoor_interface=(0.0, 0.80, 0.40, 0.20),
    provenance="[DESIGN HYPOTHESIS]",
    description="Reflection: entry → reflection → quiet → nature connection",
)

_GRAMMAR_L0 = ModuleGrammar(
    entry_threshold=(0.0, 0.0, 0.35, 0.50),
    shared_space=(0.35, 0.0, 0.35, 0.70),      # transition / decompression
    personal_territory=(0.0, 0.0, 0.0, 0.0),   # N/A
    service_zone=(0.70, 0.0, 0.30, 0.30),
    retreat_edge=(0.0, 0.70, 0.35, 0.30),      # orientation
    circulation_spine=(0.50, 0.0, 0.15, 1.0),
    provenance="[DESIGN HYPOTHESIS]",
    description="Transition: entry → decompression → threshold → orientation",
)

_GRAMMAR_F0 = ModuleGrammar(
    entry_threshold=(0.0, 0.0, 0.20, 0.25),
    shared_space=(0.20, 0.0, 0.50, 0.50),      # kitchen / prep
    personal_territory=(0.0, 0.0, 0.0, 0.0),   # N/A
    service_zone=(0.70, 0.0, 0.30, 0.60),      # storage / utility
    retreat_edge=(0.0, 0.0, 0.0, 0.0),         # N/A
    circulation_spine=(0.40, 0.0, 0.20, 1.0),
    provenance="[DESIGN HYPOTHESIS]",
    description="Service: kitchen → storage → utility → service access",
)

_GRAMMAR_M0 = ModuleGrammar(
    entry_threshold=(0.0, 0.0, 0.25, 0.30),
    shared_space=(0.25, 0.0, 0.45, 0.55),      # maintenance / waste
    personal_territory=(0.0, 0.0, 0.0, 0.0),   # N/A
    service_zone=(0.70, 0.0, 0.30, 0.70),      # environmental control
    retreat_edge=(0.0, 0.0, 0.0, 0.0),         # N/A
    circulation_spine=(0.45, 0.0, 0.15, 1.0),
    provenance="[DESIGN HYPOTHESIS]",
    description="Maintenance: maintenance → waste → environmental control → service yard",
)


# =============================================================================
# MODULE LIBRARY V4
# =============================================================================

MODULE_LIBRARY_V4: dict[str, ModuleTypeV4] = {}

def _register(mt: ModuleTypeV4) -> None:
    MODULE_LIBRARY_V4[mt.code] = mt


# --- R4 Domestic Cluster (size variants) ---
_register(ModuleTypeV4(
    code="R4-S", name="Domestic Cluster S", family="R4", size_class=SizeClass.SMALL,
    w=8.0, d=8.0, area=64.0, max_floors=1,
    capacity_residents=4, modularity=ModularityCategory.DEVELOPMENTAL, repeatable=True,
    min_count=0, max_count=4, privacy_level=3,
    ground_required=True, stackable_above=False, stackable_below=False,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("S", "E"), service_faces=("N",), open_edges=("S",),
    grammar=_GRAMMAR_R4,
    provenance="[PA5 CORPUS / DESIGN HYPOTHESIS]",
    description="Small domestic cluster for 4 residents",
))

_register(ModuleTypeV4(
    code="R4-M", name="Domestic Cluster M", family="R4", size_class=SizeClass.MEDIUM,
    w=10.0, d=8.8, area=88.0, max_floors=1,
    capacity_residents=4, modularity=ModularityCategory.DEVELOPMENTAL, repeatable=True,
    min_count=0, max_count=4, privacy_level=3,
    ground_required=True, stackable_above=False, stackable_below=False,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("S", "E"), service_faces=("N",), open_edges=("S",),
    grammar=_GRAMMAR_R4,
    provenance="[PA5 CORPUS]",
    description="Medium domestic cluster for 4 residents (v3 baseline)",
))

_register(ModuleTypeV4(
    code="R4-L", name="Domestic Cluster L", family="R4", size_class=SizeClass.LARGE,
    w=12.0, d=10.0, area=120.0, max_floors=1,
    capacity_residents=6, modularity=ModularityCategory.DEVELOPMENTAL, repeatable=True,
    min_count=0, max_count=3, privacy_level=3,
    ground_required=True, stackable_above=False, stackable_below=False,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("S", "E"), service_faces=("N",), open_edges=("S",),
    grammar=_GRAMMAR_R4,
    provenance="[DESIGN HYPOTHESIS]",
    description="Large domestic cluster for 6 residents",
))

# --- A0 Arrival ---
_register(ModuleTypeV4(
    code="A0-S", name="Arrival / Reception S", family="A0", size_class=SizeClass.SMALL,
    w=5.0, d=6.0, area=30.0, max_floors=1,
    capacity_day_users=12, capacity_staff=1,
    modularity=ModularityCategory.DEVELOPMENTAL, repeatable=False,
    min_count=0, max_count=1, privacy_level=1,
    ground_required=True, stackable_above=False, stackable_below=False,
    rotation_policy=RotationPolicy.FULL, allowed_rotations=(0, 90, 180, 270),
    access_faces=("S", "E", "W"), service_faces=("N",), open_edges=("S",),
    grammar=_GRAMMAR_A0,
    provenance="[DESIGN HYPOTHESIS]",
    description="Compact public arrival, screening, orientation for low-throughput thresholds",
))

_register(ModuleTypeV4(
    code="A0", name="Arrival / Reception", family="A0", size_class=SizeClass.MEDIUM,
    w=6.0, d=8.0, area=48.0, max_floors=1,
    capacity_day_users=20, capacity_staff=2,
    modularity=ModularityCategory.DEVELOPMENTAL, repeatable=False,
    min_count=1, max_count=1, privacy_level=1,
    ground_required=True, stackable_above=False, stackable_below=False,
    rotation_policy=RotationPolicy.FULL, allowed_rotations=(0, 90, 180, 270),
    access_faces=("S", "E", "W"), service_faces=("N",), open_edges=("S",),
    grammar=_GRAMMAR_A0,
    provenance="[PA5 CORPUS]",
    description="Public arrival, screening, orientation (baseline)",
))

# --- B0 Care ---
_register(ModuleTypeV4(
    code="B0-S", name="Care / Safeguarding S", family="B0", size_class=SizeClass.SMALL,
    w=6.0, d=8.0, area=48.0, max_floors=1,
    capacity_day_users=4, capacity_staff=2,
    modularity=ModularityCategory.DEVELOPMENTAL, repeatable=False,
    min_count=0, max_count=1, privacy_level=3,
    ground_required=True, stackable_above=False, stackable_below=False,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("S", "E"), service_faces=("N", "W"), open_edges=(),
    grammar=_GRAMMAR_B0,
    provenance="[DESIGN HYPOTHESIS]",
    description="Single-room intake + counselling pod; higher privacy, low throughput",
))

_register(ModuleTypeV4(
    code="B0", name="Care / Safeguarding", family="B0", size_class=SizeClass.MEDIUM,
    w=8.0, d=10.0, area=80.0, max_floors=1,
    capacity_day_users=8, capacity_staff=4,
    modularity=ModularityCategory.DEVELOPMENTAL, repeatable=False,
    min_count=1, max_count=1, privacy_level=2,
    ground_required=True, stackable_above=False, stackable_below=False,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("S", "E"), service_faces=("N", "W"), open_edges=(),
    grammar=_GRAMMAR_B0,
    provenance="[PA5 CORPUS]",
    description="Intake, counselling, safeguarding, response (baseline)",
))

_register(ModuleTypeV4(
    code="B0-L", name="Care / Safeguarding L", family="B0", size_class=SizeClass.LARGE,
    w=10.0, d=12.0, area=120.0, max_floors=1,
    capacity_day_users=14, capacity_staff=6,
    modularity=ModularityCategory.DEVELOPMENTAL, repeatable=False,
    min_count=0, max_count=1, privacy_level=2,
    ground_required=True, stackable_above=False, stackable_below=False,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("S", "E"), service_faces=("N", "W"), open_edges=(),
    grammar=_GRAMMAR_B0,
    provenance="[DESIGN HYPOTHESIS]",
    description="Full care suite: intake, counselling, safeguarding, quiet response rooms",
))

# --- C0 Commons ---
_register(ModuleTypeV4(
    code="C0-S", name="Commons / Dining S", family="C0", size_class=SizeClass.SMALL,
    w=8.0, d=10.0, area=80.0, max_floors=1,
    capacity_day_users=16, capacity_staff=2,
    modularity=ModularityCategory.VARIATIONAL, repeatable=False,
    min_count=0, max_count=1, privacy_level=2,
    ground_required=True, stackable_above=False, stackable_below=False,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("S", "E"), service_faces=("N",), open_edges=("S",),
    grammar=_GRAMMAR_C0,
    provenance="[DESIGN HYPOTHESIS]",
    description="Domestic-scale dining/everyday commons preserving household intimacy",
))

_register(ModuleTypeV4(
    code="C0", name="Commons / Dining", family="C0", size_class=SizeClass.MEDIUM,
    w=12.0, d=10.0, area=120.0, max_floors=1,
    capacity_day_users=32, capacity_staff=3,
    modularity=ModularityCategory.DEVELOPMENTAL, repeatable=False,
    min_count=1, max_count=1, privacy_level=2,
    ground_required=True, stackable_above=False, stackable_below=False,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("S", "E", "W"), service_faces=("N",), open_edges=("S", "E"),
    grammar=_GRAMMAR_C0,
    provenance="[PA5 CORPUS]",
    description="Shared dining, everyday activity, kitchen interface (baseline)",
))

_register(ModuleTypeV4(
    code="C0-L", name="Commons / Dining L", family="C0", size_class=SizeClass.LARGE,
    w=14.0, d=12.0, area=168.0, max_floors=1,
    capacity_day_users=48, capacity_staff=5,
    modularity=ModularityCategory.DEVELOPMENTAL, repeatable=False,
    min_count=0, max_count=1, privacy_level=2,
    ground_required=True, stackable_above=False, stackable_below=False,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("S", "E", "W"), service_faces=("N",), open_edges=("S", "E"),
    grammar=_GRAMMAR_C0,
    provenance="[DESIGN HYPOTHESIS]",
    description="Campus-scale commons for high day-user strata; risks institutional scale",
))

# --- H0 Learning ---
_register(ModuleTypeV4(
    code="H0-S", name="Learning / Education S", family="H0", size_class=SizeClass.SMALL,
    w=6.0, d=8.0, area=48.0, max_floors=1,
    capacity_day_users=8, capacity_staff=1,
    modularity=ModularityCategory.VARIATIONAL, repeatable=False,
    min_count=0, max_count=1, privacy_level=2,
    ground_required=False, stackable_above=True, stackable_below=True,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("S",), service_faces=("N",), open_edges=("S",),
    grammar=_GRAMMAR_H0,
    provenance="[DESIGN HYPOTHESIS]",
    description="Small tutorial / quiet-study room; stackable over compatible bases",
))

_register(ModuleTypeV4(
    code="H0", name="Learning / Education", family="H0", size_class=SizeClass.MEDIUM,
    w=8.0, d=8.0, area=64.0, max_floors=1,
    capacity_day_users=16, capacity_staff=2,
    modularity=ModularityCategory.VARIATIONAL, repeatable=False,
    min_count=0, max_count=1, privacy_level=2,
    ground_required=False, stackable_above=True, stackable_below=True,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("S",), service_faces=("N",), open_edges=("S",),
    grammar=_GRAMMAR_H0,
    provenance="[PA5 CORPUS]",
    description="Learning, quiet study, group activity (baseline)",
))

_register(ModuleTypeV4(
    code="H0-L", name="Learning / Education L", family="H0", size_class=SizeClass.LARGE,
    w=10.0, d=10.0, area=100.0, max_floors=1,
    capacity_day_users=24, capacity_staff=3,
    modularity=ModularityCategory.VARIATIONAL, repeatable=False,
    min_count=0, max_count=1, privacy_level=2,
    ground_required=False, stackable_above=True, stackable_below=True,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("S",), service_faces=("N",), open_edges=("S",),
    grammar=_GRAMMAR_H0,
    provenance="[DESIGN HYPOTHESIS]",
    description="Multi-room learning cluster: group activity + quiet study + storage",
))

# --- J0 Livelihood ---
_register(ModuleTypeV4(
    code="J0-S", name="Livelihood / Workshop S", family="J0", size_class=SizeClass.SMALL,
    w=8.0, d=8.0, area=64.0, max_floors=1,
    capacity_day_users=6, capacity_staff=1,
    modularity=ModularityCategory.VARIATIONAL, repeatable=False,
    min_count=0, max_count=1, privacy_level=2,
    ground_required=True, stackable_above=False, stackable_below=False,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("S", "E"), service_faces=("N", "W"), open_edges=("S",),
    grammar=_GRAMMAR_J0,
    provenance="[DESIGN HYPOTHESIS]",
    description="Compact craft / livelihood workshop with small market interface",
))

_register(ModuleTypeV4(
    code="J0", name="Livelihood / Workshop", family="J0", size_class=SizeClass.MEDIUM,
    w=10.0, d=10.0, area=100.0, max_floors=1,
    capacity_day_users=12, capacity_staff=2,
    modularity=ModularityCategory.VARIATIONAL, repeatable=False,
    min_count=0, max_count=1, privacy_level=2,
    ground_required=True, stackable_above=False, stackable_below=False,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("S", "E"), service_faces=("N", "W"), open_edges=("S",),
    grammar=_GRAMMAR_J0,
    provenance="[PA5 CORPUS]",
    description="Workshop, production, market interface (baseline)",
))

_register(ModuleTypeV4(
    code="J0-L", name="Livelihood / Workshop L", family="J0", size_class=SizeClass.LARGE,
    w=12.0, d=12.0, area=144.0, max_floors=1,
    capacity_day_users=20, capacity_staff=3,
    modularity=ModularityCategory.VARIATIONAL, repeatable=False,
    min_count=0, max_count=1, privacy_level=2,
    ground_required=True, stackable_above=False, stackable_below=False,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("S", "E"), service_faces=("N", "W"), open_edges=("S",),
    grammar=_GRAMMAR_J0,
    provenance="[DESIGN HYPOTHESIS]",
    description="Production-scale livelihood workshop with dedicated storage + market front",
))

# --- K0 Community ---
_register(ModuleTypeV4(
    code="K0-S", name="Community / Gathering S", family="K0", size_class=SizeClass.SMALL,
    w=8.0, d=8.0, area=64.0, max_floors=1,
    capacity_day_users=16, capacity_staff=1,
    modularity=ModularityCategory.VARIATIONAL, repeatable=False,
    min_count=0, max_count=1, privacy_level=1,
    ground_required=True, stackable_above=False, stackable_below=False,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("S", "E"), service_faces=("N",), open_edges=("S", "E"),
    grammar=_GRAMMAR_K0,
    provenance="[DESIGN HYPOTHESIS]",
    description="Neighbourhood-scale gathering room for smaller community events",
))

_register(ModuleTypeV4(
    code="K0", name="Community / Gathering", family="K0", size_class=SizeClass.MEDIUM,
    w=12.0, d=12.0, area=144.0, max_floors=1,
    capacity_day_users=40, capacity_staff=2,
    modularity=ModularityCategory.VARIATIONAL, repeatable=False,
    min_count=0, max_count=1, privacy_level=1,
    ground_required=True, stackable_above=False, stackable_below=False,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("S", "E", "W"), service_faces=("N",), open_edges=("S", "E", "W"),
    grammar=_GRAMMAR_K0,
    provenance="[PA5 CORPUS]",
    description="Gathering, event, flexible community use (baseline)",
))

_register(ModuleTypeV4(
    code="K0-L", name="Community / Gathering L", family="K0", size_class=SizeClass.LARGE,
    w=14.0, d=14.0, area=196.0, max_floors=1,
    capacity_day_users=56, capacity_staff=3,
    modularity=ModularityCategory.VARIATIONAL, repeatable=False,
    min_count=0, max_count=1, privacy_level=1,
    ground_required=True, stackable_above=False, stackable_below=False,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("S", "E", "W"), service_faces=("N",), open_edges=("S", "E", "W"),
    grammar=_GRAMMAR_K0,
    provenance="[DESIGN HYPOTHESIS]",
    description="Campus-hall community space for the largest public strata",
))

# --- I0 Reflection ---
_register(ModuleTypeV4(
    code="I0-S", name="Reflection / Prayer S", family="I0", size_class=SizeClass.SMALL,
    w=4.0, d=4.0, area=16.0, max_floors=1,
    capacity_day_users=4, capacity_staff=0,
    modularity=ModularityCategory.VARIATIONAL, repeatable=False,
    min_count=0, max_count=1, privacy_level=4,
    ground_required=False, stackable_above=True, stackable_below=True,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("S",), service_faces=(), open_edges=("S", "E"),
    grammar=_GRAMMAR_I0,
    provenance="[DESIGN HYPOTHESIS]",
    description="Single-person reflection niche; highest privacy, minimal footprint",
))

_register(ModuleTypeV4(
    code="I0", name="Reflection / Prayer", family="I0", size_class=SizeClass.MEDIUM,
    w=6.0, d=6.0, area=36.0, max_floors=1,
    capacity_day_users=8, capacity_staff=0,
    modularity=ModularityCategory.VARIATIONAL, repeatable=False,
    min_count=0, max_count=1, privacy_level=3,
    ground_required=False, stackable_above=True, stackable_below=True,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("S",), service_faces=(), open_edges=("S", "E"),
    grammar=_GRAMMAR_I0,
    provenance="[PA5 CORPUS]",
    description="Reflection, prayer, quiet, nature connection (baseline)",
))

_register(ModuleTypeV4(
    code="I0-L", name="Reflection / Prayer L", family="I0", size_class=SizeClass.LARGE,
    w=8.0, d=8.0, area=64.0, max_floors=1,
    capacity_day_users=16, capacity_staff=0,
    modularity=ModularityCategory.VARIATIONAL, repeatable=False,
    min_count=0, max_count=1, privacy_level=3,
    ground_required=False, stackable_above=True, stackable_below=True,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("S",), service_faces=(), open_edges=("S", "E"),
    grammar=_GRAMMAR_I0,
    provenance="[DESIGN HYPOTHESIS]",
    description="Communal prayer / reflection hall for larger resident groups",
))

# --- L0 Transition ---
_register(ModuleTypeV4(
    code="L0", name="Transition / Threshold", family="L0", size_class=SizeClass.SMALL,
    w=4.0, d=6.0, area=24.0, max_floors=1,
    capacity_day_users=6, capacity_staff=0,
    modularity=ModularityCategory.VARIATIONAL, repeatable=False,
    min_count=0, max_count=2, privacy_level=2,
    ground_required=True, stackable_above=False, stackable_below=False,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("N", "S"), service_faces=(), open_edges=(),
    grammar=_GRAMMAR_L0,
    provenance="[PA5 CORPUS]",
    description="Transition, decompression, threshold, orientation (baseline)",
))

_register(ModuleTypeV4(
    code="L0-L", name="Transition / Threshold L", family="L0", size_class=SizeClass.MEDIUM,
    w=6.0, d=8.0, area=48.0, max_floors=1,
    capacity_day_users=12, capacity_staff=0,
    modularity=ModularityCategory.VARIATIONAL, repeatable=False,
    min_count=0, max_count=2, privacy_level=2,
    ground_required=True, stackable_above=False, stackable_below=False,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("N", "S"), service_faces=(), open_edges=(),
    grammar=_GRAMMAR_L0,
    provenance="[DESIGN HYPOTHESIS]",
    description="Generous threshold / decompression gallery between public and domestic realms",
))

# --- F0 Service ---
_register(ModuleTypeV4(
    code="F0", name="Service / Kitchen", family="F0", size_class=SizeClass.MEDIUM,
    w=8.0, d=10.0, area=80.0, max_floors=1,
    capacity_staff=4,
    modularity=ModularityCategory.DEVELOPMENTAL, repeatable=False,
    min_count=1, max_count=1, privacy_level=1,
    ground_required=True, stackable_above=False, stackable_below=False,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("E", "W"), service_faces=("N", "S"), open_edges=(),
    grammar=_GRAMMAR_F0,
    provenance="[PA5 CORPUS]",
    description="Kitchen, storage, utility, service access (baseline)",
))

_register(ModuleTypeV4(
    code="F0-L", name="Service / Kitchen L", family="F0", size_class=SizeClass.LARGE,
    w=10.0, d=12.0, area=120.0, max_floors=1,
    capacity_staff=6,
    modularity=ModularityCategory.DEVELOPMENTAL, repeatable=False,
    min_count=0, max_count=1, privacy_level=1,
    ground_required=True, stackable_above=False, stackable_below=False,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("E", "W"), service_faces=("N", "S"), open_edges=(),
    grammar=_GRAMMAR_F0,
    provenance="[DESIGN HYPOTHESIS]",
    description="Central kitchen + storage for high-resident and high day-user strata",
))

# --- M0 Maintenance ---
_register(ModuleTypeV4(
    code="M0", name="Maintenance / Utility", family="M0", size_class=SizeClass.MEDIUM,
    w=6.0, d=8.0, area=48.0, max_floors=1,
    capacity_staff=2,
    modularity=ModularityCategory.DEVELOPMENTAL, repeatable=False,
    min_count=1, max_count=1, privacy_level=1,
    ground_required=True, stackable_above=False, stackable_below=False,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("E", "W"), service_faces=("N", "S"), open_edges=(),
    grammar=_GRAMMAR_M0,
    provenance="[PA5 CORPUS]",
    description="Maintenance, waste, environmental control, service yard (baseline)",
))

_register(ModuleTypeV4(
    code="M0-L", name="Maintenance / Utility L", family="M0", size_class=SizeClass.LARGE,
    w=8.0, d=10.0, area=80.0, max_floors=1,
    capacity_staff=3,
    modularity=ModularityCategory.DEVELOPMENTAL, repeatable=False,
    min_count=0, max_count=1, privacy_level=1,
    ground_required=True, stackable_above=False, stackable_below=False,
    rotation_policy=RotationPolicy.ORTHOGONAL, allowed_rotations=(0, 90),
    access_faces=("E", "W"), service_faces=("N", "S"), open_edges=(),
    grammar=_GRAMMAR_M0,
    provenance="[DESIGN HYPOTHESIS]",
    description="Larger service yard + plant for expanded campuses",
))


# =============================================================================
# QUERY FUNCTIONS
# =============================================================================

def get_module(code: str) -> ModuleTypeV4:
    """Get module by exact code."""
    return MODULE_LIBRARY_V4[code]


def get_family_modules(family: str) -> list[ModuleTypeV4]:
    """Get all size variants of a module family."""
    return [m for m in MODULE_LIBRARY_V4.values() if m.family == family]


def get_module_variant(family: str, size_class: SizeClass) -> Optional[ModuleTypeV4]:
    """Get specific size variant of a family."""
    for m in MODULE_LIBRARY_V4.values():
        if m.family == family and m.size_class == size_class:
            return m
    return None


def allowed_rotations(code: str) -> tuple[int, ...]:
    """Get allowed rotations for a module."""
    return MODULE_LIBRARY_V4[code].allowed_rotations


def ground_required_modules() -> list[str]:
    """List modules that must be on ground floor."""
    return [m.code for m in MODULE_LIBRARY_V4.values() if m.ground_required]


def stackable_modules() -> list[str]:
    """List modules that can be stacked."""
    return [m.code for m in MODULE_LIBRARY_V4.values() if m.stackable_above or m.stackable_below]


def service_modules() -> list[str]:
    """List service modules."""
    return [m.code for m in MODULE_LIBRARY_V4.values() if m.family in ("F0", "M0")]


def care_modules() -> list[str]:
    """List care modules."""
    return [m.code for m in MODULE_LIBRARY_V4.values() if m.family == "B0"]


def domestic_modules() -> list[str]:
    """List domestic modules."""
    return [m.code for m in MODULE_LIBRARY_V4.values() if m.family == "R4"]


def public_modules() -> list[str]:
    """List public modules."""
    return [m.code for m in MODULE_LIBRARY_V4.values() if m.privacy_level <= 1]


def private_modules() -> list[str]:
    """List private modules."""
    return [m.code for m in MODULE_LIBRARY_V4.values() if m.privacy_level >= 3]


# Compatibility with v3 — maps each legacy function to its canonical v4 baseline
# (the [PA5 CORPUS] variant, i.e. the original one-size assumption).
MODULES_V3_COMPAT = {
    "R4": "R4-M",  # v3 R4 → v4 R4-M
    "A0": "A0",
    "B0": "B0",
    "C0": "C0",
    "H0": "H0",
    "J0": "J0",
    "K0": "K0",
    "I0": "I0",
    "L0": "L0",
    "F0": "F0",
    "M0": "M0",
}

# Canonical (baseline / [PA5 CORPUS]) variant per family. The gene pool fixes
# these single-variant families; S/L variants are only activated by explicit
# capacity-strata experiments so the corpus baseline stays the default.
CANONICAL_VARIANT = {
    "R4": "R4-M",
    "A0": "A0",
    "B0": "B0",
    "C0": "C0",
    "H0": "H0",
    "J0": "J0",
    "K0": "K0",
    "I0": "I0",
    "L0": "L0",
    "F0": "F0",
    "M0": "M0",
}

# Evidence-based size variants available per family (FUNCTION × SIZE grid).
# Variants beyond the baseline are [DESIGN HYPOTHESIS] unless tagged otherwise.
FAMILY_VARIANTS: dict = {}
for _m in MODULE_LIBRARY_V4.values():
    FAMILY_VARIANTS.setdefault(_m.family, []).append(_m.code)
for _fam in FAMILY_VARIANTS:
    # Order S, M, L by area for deterministic choice-gene decoding.
    FAMILY_VARIANTS[_fam].sort(key=lambda c: MODULE_LIBRARY_V4[c].area)


def v3_code_to_v4(v3_code: str) -> str:
    """Map v3 module code to v4 code."""
    return MODULES_V3_COMPAT.get(v3_code, v3_code)
