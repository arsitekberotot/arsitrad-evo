"""Full experimental campaign for The Threshold evolutionary spatial programming.

Stages:
  1. Multi-seed NSGA-II runs (controlled seeds) — runtime, feasibility, Pareto,
     convergence recorded per seed.
  2. Sensitivity tests: population size, generations, crossover prob, mutation
     prob, mutation strength (eta).
  3. Aggregate the nondominated archive across seeds; normalize objectives.
  4. K-means clustering (silhouette + elbow); select medoids + objective extremes.
  5. Per-representative graphics + machine-readable traceability records.
  6. Reproducible result archive + generated REPORT.md.

Usage:
    .venv/bin/python run_campaign.py --out campaign [--quick]
"""
from __future__ import annotations
import argparse, json, os, time
import numpy as np
import pandas as pd

from arsitrad_evo.config import GAConfig, ClusterConfig
from arsitrad_evo.nsga2 import run
from arsitrad_evo.clustering import cluster_pareto
from arsitrad_evo.objectives import OBJECTIVES
from arsitrad_evo.genotype import STRUCT_GENES
from arsitrad_evo import analyze, visualize as viz

OBJ_NAMES = [n for n, _ in OBJECTIVES]
GENE_NAMES = [n for n, _, _, _ in STRUCT_GENES]


def single_run(cfg: GAConfig):
    t0 = time.time()
    pop, fronts, history = run(cfg, verbose=False)
    runtime = time.time() - t0
    feas = [p for p in pop if p.feasible]
    rank1 = [p for p in pop if p.feasible and p.rank == 0]
    return pop, rank1, history, runtime, feas


def phenotype_row(p, extra=None):
    objs = np.asarray(p.objectives)
    row = {f"obj_{n}": round(float(objs[m]), 4) for m, n in enumerate(OBJ_NAMES)}
    row.update({f"g_{n}": p.genes[i] for i, n in enumerate(GENE_NAMES)})
    row.update({"genotype_id": analyze.genotype_id(p),
                "birth_generation": p.birth_generation,
                "n_R4": p.n_R4, "residents": p.residents, "day_users": p.day_users,
                "gfa": round(p.gfa, 1), "footprint": round(p.footprint, 1),
                "landscape_frac": round(p.landscape_frac, 3), "rank": int(p.rank),
                "cv": round(float(p.cv), 4),
                "must_shortfall": round(float(p.must_shortfall), 3),
                "soft_cv": round(float(p.soft_cv), 3),
                "feasible": bool(p.feasible)})
    if extra:
        row.update(extra)
    return row


def run_campaign(out: str, quick: bool = False,
                 capacity_strata: bool = False):
    os.makedirs(out, exist_ok=True)
    figdir = os.path.join(out, "figures"); os.makedirs(figdir, exist_ok=True)
    datadir = os.path.join(out, "data"); os.makedirs(datadir, exist_ok=True)

    # ---- configuration -----------------------------------------------------
    if quick:
        seeds = [42, 7, 123]
        base = dict(pop_size=60, generations=40)
        sens = {
            "pop_size": [40, 60, 100],
            "generations": [25, 40, 60],
            "crossover_prob": [0.7, 0.9, 1.0],
            "mutation_prob": [None, 0.05, 0.15],
            "mutation_strength_eta": [10, 20, 30],
        }
    else:
        seeds = [42, 7, 123, 2024, 555]
        base = dict(pop_size=100, generations=80)
        sens = {
            "pop_size": [60, 100, 160],
            "generations": [40, 80, 120],
            "crossover_prob": [0.6, 0.8, 0.9, 1.0],
            "mutation_prob": [None, 0.03, 0.08, 0.15],
            "mutation_strength_eta": [5, 15, 20, 30],
        }

    # ---- STAGE 1: multi-seed runs -----------------------------------------
    print(f"[campaign] multi-seed runs: {seeds}")
    multiseed_rows, all_rank1, histories = [], [], {}
    for s in seeds:
        cfg = GAConfig(seed=s, **base)
        pop, rank1, history, runtime, feas = single_run(cfg)
        histories[s] = history
        all_rank1 += [(s, p) for p in rank1]
        multiseed_rows.append({
            "seed": s, "runtime_s": round(runtime, 2),
            "pop": cfg.pop_size, "gen": cfg.generations,
            "capacity_stratum": "free",
            "feasible_final": len(feas), "feasible_rate": round(len(feas)/len(pop), 3),
            "pareto_size": len(rank1),
        })
        print(f"  seed {s}: feasible {len(feas)}/{len(pop)}  pareto {len(rank1)}  {runtime:.1f}s")
    if capacity_strata:
        # Separate searches preserve the 12- and 16-resident design space after
        # per-R4 MUST links become hard. The unconstrained runs are still kept.
        stratum_seeds = seeds[:3]
        for n_r4 in (3, 4):
            for s in stratum_seeds:
                cfg = GAConfig(seed=s, n_R4_fixed=n_r4, **base)
                pop, rank1, history, runtime, feas = single_run(cfg)
                histories[f"{s}_R4x{n_r4}"] = history
                all_rank1 += [(s, p) for p in rank1]
                multiseed_rows.append({
                    "seed": s, "runtime_s": round(runtime, 2),
                    "pop": cfg.pop_size, "gen": cfg.generations,
                    "capacity_stratum": f"R4x{n_r4}",
                    "feasible_final": len(feas),
                    "feasible_rate": round(len(feas)/len(pop), 3),
                    "pareto_size": len(rank1),
                })
                print(f"  seed {s} R4x{n_r4}: feasible {len(feas)}/{len(pop)} "
                      f"pareto {len(rank1)} {runtime:.1f}s")
    df_ms = pd.DataFrame(multiseed_rows)
    df_ms.to_csv(os.path.join(datadir, "multiseed_summary.csv"), index=False)

    # combined convergence plot (feasible rate per seed)
    fig_path = os.path.join(figdir, "convergence_multiseed.png")
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for s, h in histories.items():
        ax.plot([x["gen"] for x in h], [x["feasible"] for x in h], label=f"seed {s}", alpha=0.8)
    ax.set_xlabel("generation"); ax.set_ylabel("feasible count")
    ax.set_title("Multi-seed convergence (feasible solutions)")
    ax.legend(fontsize=7); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(fig_path, dpi=140); plt.close(fig)

    # MANY-OBJECTIVE DILUTION, correctly measured (Campaign v2): rank-1 fraction
    # GROWTH per generation within each evolving population. A healthy 2-3
    # objective run keeps rank-1 small; under 9 objectives rank-1 saturates to
    # ~the whole population -> Pareto membership carries little discriminating
    # information. This is shown per-generation, NOT via non-dominance inside an
    # already-filtered archive.
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for s, h in histories.items():
        popn = base["pop_size"]
        ax.plot([x["gen"] for x in h], [x["rank1"]/popn for x in h],
                label=f"seed {s}", alpha=0.8)
    ax.axhline(1.0, ls="--", color="k", lw=0.8, alpha=0.5)
    ax.set_xlabel("generation"); ax.set_ylabel("rank-1 fraction of population")
    ax.set_ylim(0, 1.05)
    ax.set_title("Many-objective dilution: rank-1 fraction per generation")
    ax.legend(fontsize=7); ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(figdir, "rank1_growth_dilution.png"), dpi=140)
    plt.close(fig)

    # ---- STAGE 2: sensitivity sweeps --------------------------------------
    print("[campaign] sensitivity sweeps")
    sens_rows = []
    for param, values in sens.items():
        for v in values:
            kw = dict(base); kw["seed"] = seeds[0]
            if param == "pop_size": kw["pop_size"] = v
            elif param == "generations": kw["generations"] = v
            elif param == "crossover_prob": kw["crossover_prob"] = v
            elif param == "mutation_prob": kw["mutation_prob"] = v
            elif param == "mutation_strength_eta": kw["poly_eta"] = v; kw["sbx_eta"] = v
            cfg = GAConfig(**kw)
            pop, rank1, history, runtime, feas = single_run(cfg)
            sens_rows.append({
                "param": param, "value": ("default" if v is None else v),
                "runtime_s": round(runtime, 2), "feasible_rate": round(len(feas)/len(pop), 3),
                "pareto_size": len(rank1),
                "obj_F5_mean": round(float(np.mean([np.asarray(p.objectives)[4] for p in rank1])), 3) if rank1 else None,
            })
        print(f"  swept {param}: {values}")
    df_sens = pd.DataFrame(sens_rows)
    df_sens.to_csv(os.path.join(datadir, "sensitivity.csv"), index=False)

    # sensitivity plot
    fig, axes = plt.subplots(1, len(sens), figsize=(4*len(sens), 3.6), sharey=False)
    if len(sens) == 1: axes = [axes]
    for ax, (param, values) in zip(axes, sens.items()):
        sub = df_sens[df_sens.param == param]
        x = range(len(sub))
        ax.bar(x, sub["pareto_size"], color="#0284c7", alpha=0.8)
        ax.set_xticks(list(x)); ax.set_xticklabels([str(v) for v in sub["value"]], fontsize=7, rotation=45)
        ax.set_title(param, fontsize=9); ax.set_ylabel("pareto size" if param == list(sens)[0] else "")
        ax.grid(alpha=0.2, axis="y")
    fig.suptitle("Sensitivity — Pareto-front size by parameter", y=1.02)
    fig.tight_layout(); fig.savefig(os.path.join(figdir, "sensitivity.png"), dpi=140, bbox_inches="tight"); plt.close(fig)

    # ---- STAGE 3: combined nondominated archive ---------------------------
    # merge all seeds' rank-1 phenotypes, re-run nondominated sort on union.
    # SEED PROVENANCE is preserved (Campaign v2): each archive row carries its
    # originating evolutionary seed.
    from arsitrad_evo.nsga2 import fast_nondominated_sort, assign_crowding
    union = [p for _, p in all_rank1]
    seed_of = [s for s, _ in all_rank1]
    if union:
        fronts = fast_nondominated_sort(union)
        for fr in fronts:
            assign_crowding(union, fr)
        archive = [p for p in union if p.rank == 0 and p.feasible]
        archive_seed = [s for s, p in zip(seed_of, union) if p.rank == 0 and p.feasible]
    else:
        archive, archive_seed = [], []
    print(f"[campaign] combined archive (nondominated across seeds): {len(archive)}")

    df_arch = pd.DataFrame([phenotype_row(p, {"seed": s,
                                              "selected_generation": base["generations"]})
                            for p, s in zip(archive, archive_seed)])
    df_arch.to_csv(os.path.join(datadir, "pareto_archive.csv"), index=False)
    with open(os.path.join(datadir, "pareto_genotypes.jsonl"), "w") as fh:
        for p, s in zip(archive, archive_seed):
            fh.write(json.dumps({
                "genotype_id": analyze.genotype_id(p),
                "genotype_vector": analyze.genotype_vector(p),
                "seed": s, "birth_generation": p.birth_generation,
                "selected_generation": base["generations"],
                "feasible": bool(p.feasible),
                "cv": round(float(p.cv), 6),
                "must_shortfall": round(float(p.must_shortfall), 6),
            }, separators=(",", ":")) + "\n")

    # per-seed generation histories -> dilution measured via rank-1 GROWTH (v2)
    with open(os.path.join(datadir, "histories.json"), "w") as f:
        json.dump({str(s): h for s, h in histories.items()}, f)

    # objective distributions across archive
    fig, axes = plt.subplots(3, 3, figsize=(12, 9))
    for m, ax in enumerate(axes.flat):
        vals = [np.asarray(p.objectives)[m] for p in archive]
        ax.hist(vals, bins=15, color="#7dd3fc", edgecolor="k")
        ax.set_title(OBJ_NAMES[m].split("_")[0], fontsize=9); ax.grid(alpha=0.2)
    fig.suptitle("Objective distributions — nondominated archive")
    fig.tight_layout(); fig.savefig(os.path.join(figdir, "objective_distributions.png"), dpi=140); plt.close(fig)

    if archive:
        viz.plot_pareto_pairs(archive, os.path.join(figdir, "pareto_archive.png"))

    # ---- STAGE 4: clustering ----------------------------------------------
    print("[campaign] K-means clustering")
    cl = cluster_pareto(archive, ClusterConfig())
    print(f"  k={cl.get('k')} (elbow {cl.get('k_elbow')})  silhouette={cl.get('silhouette')}")
    if cl.get("k", 0) > 0:
        viz.plot_k_analysis(cl["ks"], cl["inertias"], cl["silhouettes"],
                            cl["k"], cl["k_elbow"], os.path.join(figdir, "k_analysis.png"))
        viz.plot_clusters(cl["clustered"], cl["labels"], os.path.join(figdir, "clusters.png"))
        viz.plot_parallel_coordinates(cl["clustered"], os.path.join(figdir, "parallel_coords.png"),
                                      labels=cl["labels"])
        pd.DataFrame({
            "k": cl["ks"], "inertia": cl["inertias"], "silhouette": cl["silhouettes"]
        }).to_csv(os.path.join(datadir, "k_analysis.csv"), index=False)

    # ---- STAGE 5: representatives + traceability + graphics ---------------
    reps = cl.get("representatives", archive[:6])
    rep_roles = [("medoid+extreme" if ri in cl.get("medoids", []) and
                  ri in cl.get("extremes", []) else
                  "medoid" if ri in cl.get("medoids", []) else "extreme")
                 for ri in cl.get("rep_indices", [])]
    # assign cluster label to each rep where possible
    rep_cluster = {}
    if cl.get("k", 0) > 0:
        for ri, p in zip(cl.get("rep_indices", []), reps):
            rep_cluster[id(p)] = cl["labels"][ri]

    # SEED PROVENANCE for representatives (Campaign v2): map each rep phenotype
    # back to its originating evolutionary seed via the union ordering.
    seed_by_id = {id(p): s for p, s in zip(union, seed_of)}

    trace_records = []
    for i, p in enumerate(reps):
        role = rep_roles[i] if i < len(rep_roles) else "representative"
        rec = analyze.traceability_record(p, cluster=rep_cluster.get(id(p)),
                                          role=role,
                                          selected_generation=base["generations"])
        assert rec["seed"] == seed_by_id.get(id(p))
        rec["soft_cv"] = round(float(p.soft_cv), 3)  # legacy alias
        trace_records.append(rec)
        with open(os.path.join(datadir, f"phenotype_{i:02d}.json"), "w") as f:
            json.dump(rec, f, indent=2)
        tag = f"phenotype_{i:02d}"
        viz.plot_layout(p, os.path.join(figdir, f"{tag}_siteplan.png"))
        viz.plot_privacy_zoning(p, os.path.join(figdir, f"{tag}_privacy.png"))
        viz.plot_stacking(p, os.path.join(figdir, f"{tag}_stacking.png"))
        viz.plot_circulation(p, os.path.join(figdir, f"{tag}_circulation.png"))
        viz.plot_landscape_ratio(p, os.path.join(figdir, f"{tag}_landscape.png"))
        viz.plot_radar(p, os.path.join(figdir, f"{tag}_radar.png"))
    print(f"[campaign] {len(reps)} representative phenotypes exported")

    comp = analyze.comparison_matrix(reps)
    pd.DataFrame(comp).to_csv(os.path.join(datadir, "comparison_matrix.csv"), index=False)
    viz.plot_comparison_heatmap(comp, os.path.join(figdir, "comparison_matrix.png"))

    # normalized objective table for the archive
    if archive:
        Xn = analyze.normalize_objectives(archive)
        df_norm = pd.DataFrame(Xn, columns=[f"norm_{n}" for n in OBJ_NAMES])
        df_norm.to_csv(os.path.join(datadir, "pareto_archive_normalized.csv"), index=False)

    return {
        "out": out, "seeds": seeds, "base": base, "multiseed": df_ms,
        "sensitivity": df_sens, "archive_size": len(archive),
        "capacity_strata": capacity_strata,
        "cluster": {kk: cl.get(kk) for kk in ("k", "k_elbow", "silhouette")},
        "n_representatives": len(reps), "traces": trace_records, "comp": comp,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="campaign")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--capacity-strata", action="store_true")
    args = ap.parse_args()
    summary = run_campaign(args.out, quick=args.quick,
                           capacity_strata=args.capacity_strata)
    with open(os.path.join(args.out, "data", "campaign_summary.json"), "w") as f:
        json.dump({k: v for k, v in summary.items() if k not in ("multiseed", "sensitivity", "traces", "comp")},
                  f, indent=2, default=str)
    print(f"[campaign] done -> {args.out}/")


if __name__ == "__main__":
    main()
