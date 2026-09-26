"""Run the Threshold evolutionary spatial-programming experiment end-to-end.

Usage:
    python run_experiment.py [--pop N] [--gen G] [--seed S] [--out DIR]

Outputs to results/ (or --out):
    pareto_front.csv      objective values + key genes of feasible rank-1 set
    history.csv           per-generation feasible/rank1 counts
    clusters.csv          K-means cluster assignment for Pareto phenotypes
    convergence.png, pareto.png, clusters.png, layout_family_*.png
    summary.txt           human-readable run summary
"""
from __future__ import annotations
import argparse, os
import numpy as np
import pandas as pd

from arsitrad_evo.config import GAConfig, ClusterConfig
from arsitrad_evo.nsga2 import run
from arsitrad_evo.clustering import cluster_pareto
from arsitrad_evo.objectives import OBJECTIVES
from arsitrad_evo.genotype import STRUCT_GENES
from arsitrad_evo import visualize as viz


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pop", type=int, default=80)
    ap.add_argument("--gen", type=int, default=60)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=str, default="results")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    cfg = GAConfig(pop_size=args.pop, generations=args.gen, seed=args.seed)

    print(f"[run] NSGA-II pop={cfg.pop_size} gen={cfg.generations} seed={cfg.seed}")
    pop, fronts, history = run(cfg, verbose=True)

    feas_rank1 = [p for p in pop if p.feasible and p.rank == 0]
    feas_all = [p for p in pop if p.feasible]
    print(f"[done] feasible={len(feas_all)}  pareto(rank1,feasible)={len(feas_rank1)}")

    # ---- Pareto front table ----
    obj_names = [n for n, _ in OBJECTIVES]
    gene_names = [n for n, _, _, _ in STRUCT_GENES]
    rows = []
    for p in feas_rank1:
        row = {**{f"obj_{n}": v for n, v in zip(obj_names, np.asarray(p.objectives))},
               **{f"g_{n}": p.genes[i] for i, n in enumerate(gene_names)},
               "n_R4": p.n_R4, "residents": p.residents, "day_users": p.day_users,
               "gfa": round(p.gfa, 1), "footprint": round(p.footprint, 1),
               "landscape_frac": round(p.landscape_frac, 3)}
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(args.out, "pareto_front.csv"), index=False)

    pd.DataFrame(history).to_csv(os.path.join(args.out, "history.csv"), index=False)

    # ---- plots ----
    viz.plot_convergence(history, os.path.join(args.out, "convergence.png"))
    viz.plot_pareto_pairs(pop, os.path.join(args.out, "pareto.png"))

    # ---- K-means post-processing ----
    cl = cluster_pareto(pop, ClusterConfig())
    summary = [
        "arsitrad-evo — Threshold evolutionary experiment",
        f"NSGA-II pop={cfg.pop_size} gen={cfg.generations} seed={cfg.seed}",
        f"final feasible={len(feas_all)}  pareto_rank1_feasible={len(feas_rank1)}",
        f"k-means families k={cl.get('k')} silhouette={cl.get('silhouette', 'n/a')}",
        "",
        "Representative families (cluster medoids):",
    ]
    if cl.get("k", 0) > 0:
        labels = cl["labels"]
        clustered = cl["clustered"]
        dfc = pd.DataFrame(
            [{**{f"obj_{n}": v for n, v in zip(obj_names, np.asarray(p.objectives))},
              "cluster": lab, "n_R4": p.n_R4, "residents": p.residents}
             for p, lab in zip(clustered, labels)])
        dfc.to_csv(os.path.join(args.out, "clusters.csv"), index=False)
        viz.plot_clusters(clustered, labels, os.path.join(args.out, "clusters.png"))
        for ci, rep in enumerate(cl["representatives"]):
            viz.plot_layout(rep, os.path.join(args.out, f"layout_family_{ci}.png"),
                            title=f"family {ci} | R4x{rep.n_R4} res={rep.residents} "
                                  f"fp={rep.footprint:.0f} GFA={rep.gfa:.0f}")
            objs = np.asarray(rep.objectives)
            best = obj_names[int(np.argmin(objs))]
            summary.append(
                f"  family {ci}: R4x{rep.n_R4} res={rep.residents} "
                f"day={rep.day_users} GFA={rep.gfa:.0f} fp={rep.footprint:.0f} "
                f"land={rep.landscape_frac:.2f} strongest={best}")
    else:
        summary.append(f"  {cl.get('note', 'no clusters')}")

    with open(os.path.join(args.out, "summary.txt"), "w") as f:
        f.write("\n".join(summary))
    print("\n".join(summary))
    print(f"[out] results written to {args.out}/")


if __name__ == "__main__":
    main()
