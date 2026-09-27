"""Two-tier capacity experiment for The Threshold (V4).

Tier 1 (reference): full corpus program fixed present; the reported day-user
figure is the NOMINAL capacity the full program implies. No day-user hard gate.

Tier 2 (controlled demand scenarios): public-program counts become evolvable,
each run is hard-capped at a day-user stratum (8..48), minimum functional
coverage is enforced so the GA cannot reach a target merely by deleting
essential program, and the initial population is seeded with feasible,
low-variant genomes. These strata are EXPERIMENTAL SEARCH STRATA — controlled
demand scenarios, NOT recommended shelter capacities.

The research output is the *reachability boundary* and the trade-off curve:
where (if anywhere) a demand stratum becomes infeasible under the corpus, and
how residents / day users / landscape / privacy / stacking shift across the
reachable strata. Results from Tier 1 and Tier 2 are kept separate.

Provenance: strata and coverage rules [DESIGN HYPOTHESIS]; module capacities
per-module tagged in modules_v4 ([PA5 CORPUS] / [DESIGN HYPOTHESIS]).
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict

import numpy as np
import pandas as pd

from arsitrad_evo.site import load_canonical_site
from arsitrad_evo.nsga2_v4 import run_v4, GAConfigV4
from arsitrad_evo.constraints_v4 import (
    MIN_FUNCTIONAL_COVERAGE, MAX_RESIDENTS, MAX_DAY_USERS,
)

DAY_USER_STRATA = [8, 16, 24, 32, 40, 48]     # controlled demand scenarios
RESIDENT_STRATA = [2, 3, 4, 5, 6, 7, 8]       # R4xN -> 4N residents (0..32)
OBJ_NAMES = ["site_response", "access_clarity", "landscape_quality",
             "stacking_efficiency", "exposure_gradient", "phaseability",
             "service_efficiency", "climate_daylight"]


def _objs(p):
    ov = p.objective_vector
    vals = ([r.value for r in ov.results] if ov is not None
            else [0.0] * len(OBJ_NAMES))
    return dict(zip(OBJ_NAMES, vals))


def _row(p, **extra):
    d = _objs(p)
    d.update({
        "residents": p.residents, "day_users": p.day_users, "staff": p.staff,
        "gfa": round(p.gfa, 1), "footprint": round(p.footprint, 1),
        "landscape_frac": round(p.landscape_frac, 3),
        "floors": p.floor_count, "n_instances": len(p.instances),
        "stacked_pairs": getattr(p, "stacked_pairs", 0),
    })
    d.update(extra)
    return d


def run_tier1(site, seeds, pop, gen, out):
    """Reference run: full program, nominal day capacity (no day gate)."""
    rows = []
    for seed in seeds:
        cfg = GAConfigV4(pop_size=pop, generations=gen, seed=seed)
        p, fronts, hist = run_v4(site, cfg, verbose=False)
        feas = [x for x in p if x.feasible]
        rank1 = [x for x in feas if x.rank == 0]
        best = (max(rank1, key=lambda x: getattr(x.objective_vector,
                                                 "weighted_sum", 0.0))
                if rank1 else (max(feas, key=lambda x: x.residents) if feas
                               else None))
        rows.append({
            "tier": 1, "seed": seed, "target_day_users": None,
            "feasible": len(feas), "pop": len(p),
            "pareto_size": len(rank1),
            "nominal_day_users": (best.day_users if best is not None else None),
            "residents": (best.residents if best is not None else None),
            "runtime_s": hist["runtime_s"],
            **({} if best is None else _row(best)),
        })
        print(f"  [tier1 seed={seed}] feasible={len(feas)}/{len(p)} "
              f"nominal_day={None if best is None else best.day_users} "
              f"residents={None if best is None else best.residents}")
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(out, "tier1_reference.csv"), index=False)
    return df


def run_tier2(site, seeds, pop, gen, out):
    """Controlled day-user scenarios across resident strata and seeds."""
    rows = []
    boundary = []
    for du in DAY_USER_STRATA:
        for r4 in RESIDENT_STRATA:
            target_res = r4 * 4
            if target_res > MAX_RESIDENTS:
                continue
            for seed in seeds:
                cfg = GAConfigV4(pop_size=pop, generations=gen, seed=seed,
                                 target_day_users=du, seed_feasible=True)
                p, fronts, hist = run_v4(site, cfg, verbose=False)
                feas = [x for x in p if x.feasible]
                # restrict to the intended resident stratum
                stratum = [x for x in feas if x.residents == target_res]
                reachable = len(stratum) > 0
                rank1 = [x for x in stratum if x.rank == 0]
                best = (max(rank1 or stratum,
                            key=lambda x: getattr(x.objective_vector,
                                                  "weighted_sum", 0.0))
                        if stratum else None)
                rows.append({
                    "tier": 2, "seed": seed, "target_day_users": du,
                    "r4_count": r4, "target_residents": target_res,
                    "reachable": reachable,
                    "feasible_in_stratum": len(stratum),
                    "feasible_total": len(feas),
                    **({} if best is None else _row(best)),
                })
                boundary.append({"target_day_users": du,
                                 "target_residents": target_res,
                                 "seed": seed, "reachable": reachable})
        # progress line per stratum
        sub = [b for b in boundary if b["target_day_users"] == du]
        frac = np.mean([b["reachable"] for b in sub])
        print(f"  [tier2 day={du:2d}] reachability={frac:.0%} "
              f"across resident strata x seeds")
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(out, "tier2_dayuser_scenarios.csv"), index=False)
    bdf = pd.DataFrame(boundary)
    bdf.to_csv(os.path.join(out, "reachability_boundary.csv"), index=False)
    return df, bdf


def summarize(out, tier1, tier2, boundary):
    """Human- and machine-readable experiment summary."""
    summary = {
        "experiment": "V4 two-tier capacity experiment",
        "tier1": "reference (full program, nominal day capacity)",
        "tier2": "controlled day-user demand scenarios (8..48)",
        "max_residents": MAX_RESIDENTS, "max_day_users": MAX_DAY_USERS,
        "min_functional_coverage": MIN_FUNCTIONAL_COVERAGE,
        "day_user_strata": DAY_USER_STRATA,
        "resident_strata_r4": RESIDENT_STRATA,
        "caveat": ("Strata are experimental search scenarios, not recommended "
                   "shelter capacities."),
    }
    # Reachability boundary: for each day-user stratum, fraction reachable.
    reach = (boundary.groupby("target_day_users")["reachable"]
             .mean().round(3).to_dict())
    summary["day_user_reachability"] = reach
    infeasible = [int(k) for k, v in reach.items() if v == 0.0]
    summary["infeasible_day_user_strata"] = infeasible
    if infeasible:
        summary["interpretation"] = (
            f"Day-user strata {infeasible} are NOT reachable while preserving "
            f"essential functional coverage (arrival+care+commons+service) and "
            f"the mandatory threshold (L0 x2) under the current module corpus. "
            f"This marks the lower bound of the demand envelope.")
    with open(os.path.join(out, "experiment_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    with open(os.path.join(out, "experiment_summary.txt"), "w") as f:
        f.write("THE THRESHOLD — V4 TWO-TIER CAPACITY EXPERIMENT\n")
        f.write("=" * 55 + "\n\n")
        f.write("TIER 1 — reference (full corpus program)\n")
        if len(tier1):
            f.write(f"  feasible runs: {int(tier1['feasible'].gt(0).sum())}/"
                    f"{len(tier1)}\n")
            f.write(f"  nominal day users: {tier1['nominal_day_users'].min()}"
                    f"–{tier1['nominal_day_users'].max()}\n")
            f.write(f"  residents: {tier1['residents'].min()}"
                    f"–{tier1['residents'].max()}\n\n")
        f.write("TIER 2 — controlled day-user scenarios\n")
        f.write(f"  day-user reachability: {reach}\n")
        if infeasible:
            f.write(f"  INFEASIBLE strata (functional coverage preserved): "
                    f"{infeasible}\n")
        f.write("\n" + summary["caveat"] + "\n")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pop", type=int, default=40)
    ap.add_argument("--gen", type=int, default=30)
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 7, 123])
    ap.add_argument("--out", type=str, default="results_capacity_v4")
    ap.add_argument("--site", type=str, default="data/site.geojson")
    ap.add_argument("--meta", type=str, default="data/site.yaml")
    ap.add_argument("--tier1-only", action="store_true")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    site = load_canonical_site(args.site, args.meta)
    print(f"[site] {site.name} area={site.area_m2:.1f} m2 "
          f"mode={site.mode.value}")

    print("[tier1] reference run ...")
    tier1 = run_tier1(site, args.seeds, args.pop, args.gen, args.out)

    tier2 = pd.DataFrame()
    boundary = pd.DataFrame()
    if not args.tier1_only:
        print("[tier2] controlled day-user scenarios ...")
        tier2, boundary = run_tier2(site, args.seeds, args.pop, args.gen,
                                    args.out)

    summary = summarize(args.out, tier1, tier2, boundary)

    # Architectural interpretation layer (why strata are reachable / what
    # trade-offs each reachable stratum implies).
    if not args.tier1_only and len(boundary):
        from arsitrad_evo.interpret_v4 import interpret_experiment
        interpret_experiment(
            os.path.join(args.out, "tier2_dayuser_scenarios.csv"),
            os.path.join(args.out, "reachability_boundary.csv"),
            os.path.join(args.out, "interpretation_v4.txt"))
        print("[interpretation] -> interpretation_v4.txt")

    print(f"[outputs] -> {args.out}/")
    print(json.dumps({"day_user_reachability":
                      summary["day_user_reachability"]}, indent=2))


if __name__ == "__main__":
    main()
