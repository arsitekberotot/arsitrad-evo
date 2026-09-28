"""Reachable-capacity selections rendered on the REAL site polygon (V4).

Terminal stage of the adapted data flow:
  ARCHITECTURAL PHENOTYPE -> OBJECTIVES + CONSTRAINTS -> NSGA-II ->
  PARETO / FITTEST / RELATIVE-DIFFERENCE / SPECIALIZED SELECTION ->
  ARCHITECTURAL INTERPRETATION.

Runs the reachable day-user stratum (default 48, the experimentally derived
reachable floor is ~44) across seeds, keeps the resident stratum feasible,
applies the four selection modes, and renders each selected phenotype on the
actual Bantargebang parcel from site.geojson.

Selections:
  - pareto              : all rank-0 feasible solutions (the front)
  - fittest             : max weighted-sum among feasible (quick comparison)
  - relative_difference : most balanced across objectives (min std of the
                          normalised objective profile) [DESIGN HYPOTHESIS]
  - specialized         : best per individual objective [DESIGN HYPOTHESIS]

All render geometry is [VERIFIED via site]; selection heuristics beyond NSGA-II
ranking are [DESIGN HYPOTHESIS].
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np

from .site import load_canonical_site
from .nsga2_v4 import run_v4, GAConfigV4
from . import visualize_v4 as viz


def _feasible(pop):
    return [p for p in pop if p.feasible]


def select_pareto(pop):
    return [p for p in _feasible(pop) if p.rank == 0]


def select_fittest(pop):
    feas = _feasible(pop)
    if not feas:
        return None
    return max(feas, key=lambda p: p.objective_vector.weighted_sum)


def select_relative_difference(pop):
    """Most balanced: smallest dispersion across the objective profile.

    Uses the minimization-form objective array; lower spread = the solution
    trades objectives off evenly rather than excelling at one and failing
    another. [DESIGN HYPOTHESIS]
    """
    feas = _feasible(pop)
    if not feas:
        return None
    X = np.array([p.objectives for p in feas], dtype=float)
    spread = X.std(axis=1)
    return feas[int(np.argmin(spread))]


def select_specialized(pop, obj_names):
    """Best feasible per objective (most-negative value in min-form)."""
    feas = _feasible(pop)
    out = {}
    if not feas:
        return out
    X = np.array([p.objectives for p in feas], dtype=float)
    for k, name in enumerate(obj_names):
        out[name] = feas[int(np.argmin(X[:, k]))]
    return out


def run_selections(site, seeds, pop_size, generations, day_users, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    obj_names = None
    manifest = []

    for seed in seeds:
        cfg = GAConfigV4(pop_size=pop_size, generations=generations,
                         seed=seed, target_day_users=day_users,
                         seed_feasible=True)
        pop, fronts, history = run_v4(site, cfg, verbose=False)
        feas = _feasible(pop)
        pareto = select_pareto(pop)
        if obj_names is None and feas and feas[0].objective_vector is not None:
            obj_names = [str(r.name)
                         for r in feas[0].objective_vector.results]

        seed_dir = os.path.join(out_dir, f"seed_{seed}")
        os.makedirs(seed_dir, exist_ok=True)

        # convergence + pareto projection
        viz.plot_convergence_v4(history, os.path.join(seed_dir,
                                                      "convergence.png"))
        if pareto:
            viz.plot_pareto_front(pareto, os.path.join(seed_dir,
                                                       "pareto_front.png"))

        # ---- selections ------------------------------------------------
        selections = {}
        fittest = select_fittest(pop)
        if fittest is not None:
            selections["fittest"] = fittest
        rel = select_relative_difference(pop)
        if rel is not None:
            selections["relative_difference"] = rel
        if obj_names:
            for name, ph in select_specialized(pop, obj_names).items():
                selections[f"specialized_{name}"] = ph

        for tag, ph in selections.items():
            safe = tag.replace("/", "_")
            viz.plot_layout_real(
                ph, site, os.path.join(seed_dir, f"layout_{safe}.png"),
                title=f"{tag} · seed {seed} · day {day_users}")
        # privacy view for the fittest only (representative)
        if fittest is not None:
            viz.plot_privacy_real(fittest, site,
                                  os.path.join(seed_dir,
                                               "privacy_fittest.png"))

        rec = {
            "seed": seed,
            "feasible": len(feas), "pop": len(pop),
            "pareto_size": len(pareto),
            "selections": {t: {
                "residents": p.residents, "day_users": p.day_users,
                "gfa": round(p.gfa, 1), "floors": p.floor_count,
                "landscape_frac": round(p.landscape_frac, 3),
                "weighted_sum": round(float(p.objective_vector.weighted_sum), 4),
            } for t, p in selections.items()},
        }
        manifest.append(rec)
        print(f"  [seed {seed}] feasible {len(feas)}/{len(pop)} "
              f"pareto {len(pareto)} selections {len(selections)}")

    with open(os.path.join(out_dir, "selection_manifest.json"), "w") as f:
        json.dump({"day_user_stratum": day_users,
                   "objective_names": obj_names,
                   "runs": manifest}, f, indent=2)
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pop", type=int, default=48)
    ap.add_argument("--gen", type=int, default=40)
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 7])
    ap.add_argument("--day-users", type=int, default=48)
    ap.add_argument("--out", default="selections_v4_day48")
    ap.add_argument("--site", default="data/site.geojson")
    ap.add_argument("--meta", default="data/site.yaml")
    args = ap.parse_args()

    site = load_canonical_site(args.site, args.meta)
    print(f"[site] {site.name} area={site.area_m2:.1f} m2 mode={site.mode.value}")
    print(f"[run] reachable stratum day={args.day_users} "
          f"seeds={args.seeds} pop={args.pop} gen={args.gen}")
    run_selections(site, args.seeds, args.pop, args.gen,
                   args.day_users, args.out)
    print(f"[outputs] -> {args.out}/")


if __name__ == "__main__":
    main()
