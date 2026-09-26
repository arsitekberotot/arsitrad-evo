"""arsitrad-evo — configuration & reference constants.

All uncertain values are DESIGN HYPOTHESIS (DH) or TO VERIFY (TV) per SPEC.md.
Distances in metres, areas in m^2. Site = 5,533.85 m^2 (never fully buildable).
"""
from dataclasses import dataclass, field

# ----------------------------------------------------------------------------
# SITE
# ----------------------------------------------------------------------------
SITE_AREA = 5533.85          # m^2  [PA5 CORPUS / DH]
# Buildable band: footprint + reserve must not exceed this. The remainder is
# buffer, drainage, courtyards, arrival, service yard, assembly, circulation.
# DH proxy — real parcel shape/orientation TO VERIFY.
BUILDABLE_MAX = 2960.0       # m^2  [DH / TV]  (top of Step-13 band)
BUILDABLE_MIN = 1700.0       # m^2  [DH]       (informational lower band)

# Simplified rectangular site envelope for phase-1 placement [DH].
# 5,533.85 m^2 -> approx 90m x 61.5m rectangle. Real parcel TO VERIFY.
SITE_W = 90.0
SITE_H = 61.5

# ----------------------------------------------------------------------------
# RESIDENTIAL / CAPACITY  [PA5 CORPUS / DH]
# ----------------------------------------------------------------------------
RESIDENTS_PER_CLUSTER = 4          # R4 = 4 residents  [CORPUS]
N_R4_MIN, N_R4_MAX = 2, 4          # clusters 2..4 -> 8..16 residents [CORPUS]
DAY_USER_PER_EXTRA_MODULE = 8      # DH concurrency proxy [DH/TV]

# ----------------------------------------------------------------------------
# DISTANCE / GEOMETRY REFERENCE RANGES  [DH / TV]
# ----------------------------------------------------------------------------
CARE_RESPONSE_MAX = 40.0     # m, B0/E0 -> farthest R4 centroid  [DH / TV]
MUST_LINK_MAX       = 25.0   # m, MUST adjacency satisfied if within this [DH]
NEAR_LINK_MAX       = 35.0   # m, NEAR satisfied if within this           [DH]
PROHIBITED_MIN_SEP  = 18.0   # m, PROHIBITED pairs must be at least this   [DH]
PUBLIC_PRIVATE_MIN  = 20.0   # m, PUBLIC<->PERSONAL/DOMESTIC min sep (C8)  [DH]
OVERLAP_TOL         = 0.5    # m^2 allowable rect overlap tolerance        [DH]

# Landscape band (fraction of site)  [DH]
LANDSCAPE_MIN, LANDSCAPE_MAX = 0.30, 0.55

# Reference mass for domestic-scale normalization (one R4 cluster ~ 88 m^2) [CORPUS]
REF_MASS = 88.0

# ----------------------------------------------------------------------------
# NSGA-II DEFAULTS  [PAPER METHOD]
# ----------------------------------------------------------------------------
@dataclass
class GAConfig:
    pop_size: int = 80
    generations: int = 60
    crossover_prob: float = 0.9
    mutation_prob: float | None = None   # default 1/n_var set at runtime
    sbx_eta: float = 20.0            # SBX distribution index (real)
    poly_eta: float = 20.0           # polynomial mutation index (real)
    seed: int = 42

# ----------------------------------------------------------------------------
# K-MEANS POST-PROCESSING  [DH]
# ----------------------------------------------------------------------------
@dataclass
class ClusterConfig:
    k_min: int = 2
    k_max: int = 6
    use_genes: bool = False          # embed objective space only by default
    random_state: int = 42
