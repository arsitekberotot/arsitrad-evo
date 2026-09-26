"""Analysis helpers: objective normalization, representative selection, and
full per-phenotype traceability records (genes -> modules -> constraints ->
objectives -> assumptions).
"""
from __future__ import annotations
import numpy as np

from .genotype import Phenotype, STRUCT_GENES, N_STRUCT
from .objectives import OBJECTIVES
from .constraints import CONSTRAINTS, evaluate_constraints
from .modules import MODULES

OBJ_NAMES = [n for n, _ in OBJECTIVES]
GENE_NAMES = [n for n, _, _, _ in STRUCT_GENES]

# Open assumptions attached to every result (research honesty).
OPEN_ASSUMPTIONS = [
    "F1/F2/F4 use distance/area proxies, not measured safeguarding outcomes [DH]",
    "Accessibility/egress constraint is a placeholder; real dims TO VERIFY",
    "Care-response distance threshold CARE_RESPONSE_MAX is a DH proxy [TO VERIFY]",
    "Buffer/setback depths are not universal setbacks [TO VERIFY]",
    "Rectangular site envelope; real parcel shape/orientation TO VERIFY",
    "Objective normalization reference ranges uncalibrated [DH]",
    "Day-user/staff concurrency are test values, not demand forecasts [TO VERIFY]",
]


def normalize_objectives(phenos: list[Phenotype]) -> np.ndarray:
    """Min-max normalize the objective matrix across a population -> [0,1]."""
    X = np.array([np.asarray(p.objectives) for p in phenos], dtype=float)
    lo = X.min(0); hi = X.max(0)
    rng = np.where((hi - lo) < 1e-12, 1.0, hi - lo)
    return (X - lo) / rng


def genes_dict(ph: Phenotype) -> dict:
    d = {name: (int(round(ph.genes[i])) if t == "int" else round(float(ph.genes[i]), 4))
         for i, (name, t, _, _) in enumerate(STRUCT_GENES)}
    # reflect the DERIVED public_intensity actually used (gene slot is overridden)
    d["public_intensity"] = int(ph.public_intensity)
    return d


def traceability_record(ph: Phenotype, cluster: int | None = None,
                        role: str = "representative") -> dict:
    """Full machine-readable explanation of one phenotype."""
    _, feas, cv_detail = evaluate_constraints(ph)
    objs = np.asarray(ph.objectives)
    return {
        "role": role,
        "cluster": cluster,
        "feasible": bool(ph.feasible),
        "rank": int(ph.rank),
        "crowding_distance": (None if np.isinf(ph.crowding) else round(float(ph.crowding), 4)),
        "genes": genes_dict(ph),
        "capacity": {"residents": ph.residents, "n_R4": ph.n_R4,
                     "day_users": ph.day_users},
        "areas": {"gfa": round(ph.gfa, 1), "footprint": round(ph.footprint, 1),
                  "landscape_area": round(ph.landscape_area, 1),
                  "landscape_frac": round(ph.landscape_frac, 3),
                  "reserve_area": round(ph.reserve_area, 1)},
        "modules": [
            {"code": i.code, "name": MODULES[i.code].name, "x": round(i.x, 2),
             "y": round(i.y, 2), "w": i.w, "d": i.d, "floors": i.floors,
             "area": i.area, "privacy": i.privacy} for i in ph.instances
        ],
        "objectives": {OBJ_NAMES[m]: round(float(objs[m]), 4) for m in range(len(objs))},
        "strongest_objective": OBJ_NAMES[int(np.argmin(objs))],
        "weakest_objective": OBJ_NAMES[int(np.argmax(objs))],
        "constraint_violations": {k: round(v, 4) for k, v in cv_detail.items() if v > 1e-6},
        "open_assumptions": OPEN_ASSUMPTIONS,
    }


def comparison_matrix(reps: list[Phenotype]) -> list[dict]:
    """Row-per-representative comparison across capacity + objectives."""
    rows = []
    for i, ph in enumerate(reps):
        objs = np.asarray(ph.objectives)
        row = {"rep": i, "n_R4": ph.n_R4, "residents": ph.residents,
               "day_users": ph.day_users, "gfa": round(ph.gfa, 1),
               "footprint": round(ph.footprint, 1),
               "landscape_frac": round(ph.landscape_frac, 3)}
        row.update({OBJ_NAMES[m]: round(float(objs[m]), 3) for m in range(len(objs))})
        rows.append(row)
    return rows
