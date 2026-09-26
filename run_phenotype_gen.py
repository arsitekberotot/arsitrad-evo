"""Spatial Phenotype Generator driver (Campaign v2).

Re-extracts the exact v2 candidate phenotypes (BALANCED / SPECIALIZED /
CONTRASTING) from a deterministic re-run of the campaign's seeded NSGA-II runs,
matching each candidate by (seed, structural signature). Builds a schematic
architectural prototype for each and renders the 7-figure suite.

Rule-based and traceable: every internal part / connection is tagged
[PA5 CORPUS] / [DESIGN HYPOTHESIS] / [TO VERIFY]; no detailed room dimensions,
structural systems, site precision, or unsupported safeguarding requirements
are fabricated.

Usage:
    PYTHONPATH=. ./.venv/bin/python run_phenotype_gen.py
"""
from __future__ import annotations
import json, os, sys
import numpy as np

from arsitrad_evo.nsga2 import run, fast_nondominated_sort, assign_crowding
from arsitrad_evo.config import GAConfig
from arsitrad_evo.phenotype_gen import build_prototype, render_suite
from arsitrad_evo.modules import MODULES

PROJ = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(PROJ, "campaign_v2", "phenotypes")

# Frozen v2 shortlist: (label, rep_index, seed, structural signature)
CANDIDATES = [
    ("A_BALANCED",   2, 42,   dict(n_R4=2, has_H0=1, has_J0=1, has_K0=1, has_I0=1, has_L0=0, floors_C0=2)),
    ("B_SPECIALIZED",9, 2024, dict(n_R4=2, has_H0=1, has_J0=0, has_K0=0, has_I0=1, has_L0=1, floors_C0=1)),
    ("C_CONTRASTING",6, 123,  dict(n_R4=4, has_H0=0, has_J0=0, has_K0=0, has_I0=0, has_L0=0, floors_C0=1)),
]


def struct_sig(ph):
    g = ph.genes
    return dict(n_R4=int(round(g[0])), has_H0=int(round(g[1])), has_J0=int(round(g[2])),
                has_K0=int(round(g[3])), has_I0=int(round(g[4])), has_L0=int(round(g[5])),
                floors_C0=int(round(g[7])))


def matches(ph, target):
    s = struct_sig(ph)
    return all(s[k] == v for k, v in target.items())


def main():
    os.makedirs(OUT, exist_ok=True)
    # deterministic re-run of the campaign's multiseed runs
    by_seed = {}
    seeds_needed = sorted({c[2] for c in CANDIDATES})
    for seed in seeds_needed:
        cfg = GAConfig(seed=seed, pop_size=100, generations=80)
        pop, fronts, history = run(cfg, verbose=False)
        by_seed[seed] = pop
        print(f"[phenotype_gen] re-ran seed {seed}: feasible {sum(p.feasible for p in pop)}/{len(pop)}")

    manifest = []
    for label, rep_idx, seed, sig in CANDIDATES:
        pool = by_seed[seed]
        cands = [p for p in pool if p.feasible and matches(p, sig)]
        if not cands:
            print(f"[phenotype_gen] WARN: no match for {label} (seed {seed}) — skipping")
            continue
        # choose the one whose objectives best match the shortlist record (lowest worst-obj tie-break)
        cands.sort(key=lambda p: float(np.max(p.objectives)))
        ph = cands[0]
        proto = build_prototype(ph, candidate_label=label, rep_index=rep_idx, seed=seed)
        stem = f"{label.lower()}_rep{rep_idx:02d}_seed{seed}"
        outs = render_suite(proto, OUT, stem)
        manifest.append({
            "candidate": label, "rep_index": rep_idx, "seed": seed,
            "program": proto.program, "residents": proto.residents,
            "day_users": proto.day_users, "gfa": proto.gfa,
            "landscape_frac": proto.landscape_frac,
            "n_modules": len(proto.modules), "n_connections": len(proto.connections),
            "n_courtyards": len(proto.courtyards),
            "n_to_verify": len(proto.to_verify), "n_design_hypotheses": len(proto.design_hypotheses),
            "objectives": proto.objectives,
            "figures": outs,
        })
        print(f"[phenotype_gen] {label}: {len(proto.modules)} modules, "
              f"{len(proto.connections)} connections, {len(proto.courtyards)} courtyards, "
              f"{len(proto.to_verify)} TO_VERIFY, {len(proto.design_hypotheses)} DESIGN_HYPOTHESIS")
    with open(os.path.join(OUT, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"[phenotype_gen] done -> {OUT}/ ({len(manifest)} prototypes)")


if __name__ == "__main__":
    main()
