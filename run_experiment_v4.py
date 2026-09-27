"""Canonical REAL-SITE evolutionary run (v4).

Uses data/site.geojson (geometry) + data/site.yaml (metadata) as the single
site source of truth, runs the site-aware NSGA-II (nsga2_v4), and renders the
real polygon layouts. The legacy 90x61.5 m rectangle is retained only as a
regression fixture in tests.

Usage:
    python run_experiment_v4.py [--pop N] [--gen G] [--seed S] [--out DIR]
        [--site data/site.geojson] [--meta data/site.yaml]
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd

from arsitrad_evo.site import load_canonical_site
from arsitrad_evo.nsga2_v4 import run_v4, GAConfigV4
from arsitrad_evo.objectives_v4 import evaluate_objectives as eval_obj_v4
from arsitrad_evo import visualize_v4 as viz


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pop", type=int, default=60)
    ap.add_argument("--gen", type=int, default=60)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=str, default="results_v4")
    ap.add_argument("--site", type=str, default="data/site.geojson")
    ap.add_argument("--meta", type=str, default="data/site.yaml")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    site = load_canonical_site(args.site, args.meta)
    print(f"[site] {site.name} area={site.area_m2:.1f} m2 edges={len(site.edges)} "
          f"frontage={site.frontage_edges} setbacks={site.setbacks_m}")

    cfg = GAConfigV4(pop_size=args.pop, generations=args.gen, seed=args.seed)
    print(f"[run] NSGA-II v4 pop={cfg.pop_size} gen={cfg.generations} seed={cfg.seed}")
    pop, fronts, history = run_v4(site, cfg, verbose=True)

    feas = [p for p in pop if p.feasible]
    rank1 = [p for p in feas if p.rank == 0]
    print(f"[done] feasible={len(feas)}/{len(pop)}  pareto(rank1)={len(rank1)}")

    # ---- Pareto table ----
    obj_names = (["site_response", "access_clarity", "landscape_quality",
                  "stacking_efficiency", "exposure_gradient", "phaseability",
                  "service_efficiency", "climate_daylight"])
    rows = []
    for p in rank1:
        ov = p.objective_vector
        vals = ([r.value for r in ov.results] if ov is not None
                else list(np.zeros(8)))
        rows.append({
            **{f"obj_{n}": round(v, 4) for n, v in zip(obj_names, vals)},
            "residents": p.residents, "day_users": p.day_users,
            "staff": p.staff, "gfa": round(p.gfa, 1),
            "footprint": round(p.footprint, 1),
            "landscape_frac": round(p.landscape_frac, 3),
            "floors": p.floor_count, "n_instances": len(p.instances),
        })
    pd.DataFrame(rows).to_csv(os.path.join(args.out, "pareto_front_v4.csv"),
                              index=False)
    pd.DataFrame(history["generations"]).to_csv(
        os.path.join(args.out, "history_v4.csv"), index=False)

    # ---- visuals on the real polygon ----
    viz.plot_convergence_v4(history, os.path.join(args.out, "convergence_v4.png"))
    viz.plot_pareto_front(pop, os.path.join(args.out, "pareto_v4.png"))
    best = None
    if rank1:
        # most-balanced (max weighted-sum) representative
        best = max(rank1, key=lambda p: getattr(
            p.objective_vector, "weighted_sum", 0.0))
        viz.plot_layout_real(best, site, os.path.join(args.out, "layout_v4.png"),
                             title="Best-balanced v4 layout (real site)")
        viz.plot_privacy_real(best, site, os.path.join(args.out, "privacy_v4.png"))

    # ---- summary ----
    with open(os.path.join(args.out, "summary_v4.txt"), "w") as f:
        f.write("THE THRESHOLD — v4 REAL-SITE EVOLUTIONARY RUN\n")
        f.write("=" * 50 + "\n")
        f.write(f"Site: {site.name}\n")
        f.write(f"Area: {site.area_m2:.1f} m2 | edges: {len(site.edges)} | "
                f"mode: {site.mode.value}\n")
        f.write(f"Setbacks (m): {site.setbacks_m}\n")
        f.write(f"Frontage edges: {site.frontage_edges} | "
                f"expansion: {site.preferred_expansion_direction}\n\n")
        f.write(f"NSGA-II: pop={cfg.pop_size} gen={cfg.generations} seed={cfg.seed}\n")
        f.write(f"feasible: {len(feas)}/{len(pop)}  Pareto(rank1): {len(rank1)}\n")
        f.write(f"runtime: {history['runtime_s']}s\n")
        if best is not None:
            f.write(f"\nBest-balanced: residents={best.residents} "
                    f"day_users={best.day_users} gfa={best.gfa:.0f} "
                    f"floors={best.floor_count}\n")

    print(f"[outputs] -> {args.out}/")


if __name__ == "__main__":
    main()
