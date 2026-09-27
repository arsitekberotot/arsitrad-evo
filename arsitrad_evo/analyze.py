"""Analysis helpers: objective normalization, representative selection, and
full per-phenotype traceability records (genes -> modules -> constraints ->
objectives -> assumptions).
"""
from __future__ import annotations
import hashlib
import json
import numpy as np

from .genotype import Phenotype, STRUCT_GENES, N_STRUCT
from .objectives import OBJECTIVES
from .constraints import CONSTRAINTS, evaluate_constraints
from .modules import MODULES

OBJ_NAMES = [n for n, _ in OBJECTIVES]
GENE_NAMES = [n for n, _, _, _ in STRUCT_GENES]


def genotype_vector(ph: Phenotype) -> list[float]:
    """Canonical full vector for exact replay, including masked machine slots."""
    return [round(float(v), 12) for v in ph.genes]


def genotype_id(ph: Phenotype) -> str:
    raw = json.dumps(genotype_vector(ph), separators=(",", ":"),
                     allow_nan=False).encode("ascii")
    return hashlib.sha256(raw).hexdigest()[:16]

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
    """Human-readable genotype with DORMANT/MASKED genes removed (Campaign v2).

    Optional-module genes are masked when the module is absent (e.g. floors_H0
    when has_H0=0); the public_intensity slot is overridden by the derived
    value, so the raw slot is replaced. Only architecturally meaningful genes
    are reported."""
    d = {name: (int(round(ph.genes[i])) if t == "int" else round(float(ph.genes[i]), 4))
         for i, (name, t, _, _) in enumerate(STRUCT_GENES)}
    # drop dormant floor genes for absent optional modules
    if d.get("has_H0", 0) == 0:
        d.pop("floors_H0", None)
    # floors_C0 always meaningful (C0 is always present); keep.
    # public_intensity slot is overridden by the derived value -> report derived.
    d["public_intensity"] = int(ph.public_intensity)
    return d


def traceability_record(ph: Phenotype, cluster: int | None = None,
                        role: str = "representative",
                        selected_generation: int | None = None) -> dict:
    """Full machine-readable explanation of one phenotype."""
    _, feas, cv_detail = evaluate_constraints(ph)
    hard_names = {name for name, _, is_hard in CONSTRAINTS if is_hard}
    objs = np.asarray(ph.objectives)
    return {
        "role": role,
        "cluster": cluster,
        "seed": ph.origin_seed,
        "birth_generation": ph.birth_generation,
        "selected_generation": selected_generation,
        "genotype_id": genotype_id(ph),
        "feasible": bool(feas),
        "constraint_status": ("MODEL_FEASIBLE" if feas else "MODEL_INFEASIBLE"),
        "rank": int(ph.rank),
        "crowding_distance": (None if np.isinf(ph.crowding) else round(float(ph.crowding), 4)),
        "genotype_vector": genotype_vector(ph),
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
        "constraint_violations": {k: round(v, 4) for k, v in cv_detail.items()
                                  if k in hard_names and v > 1e-6},
        "must_adjacency_shortfall": round(float(ph.must_shortfall), 4),
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
