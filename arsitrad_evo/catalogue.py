"""Evolutionary Catalogue: shows how SPATIAL PHENOTYPES evolve, not just objectives.

Captures population snapshots at selected generations, renders miniature
phenotype thumbnails (reusing visualize.plot_layout), and assembles boards:
  - population-evolution board (one representative phenotype per generation)
  - Pareto / representative board (final front, diverse feasible individuals)
  - objective-extreme selections (best per objective)
  - relative-difference / balanced selections
  - final shortlist board (plan/axon imagery + radar profile)

Chain shown: GENERATION -> GENOTYPE -> SPATIAL PHENOTYPE -> PERFORMANCE -> SELECTION.
Diagrammatic only; reuses the frozen Phenotype Schema v1 for any prototype detail.
"""
from __future__ import annotations
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from .config import GAConfig
from .nsga2 import run
from .genotype import Phenotype, STRUCT_GENES
from .phenotype_gen import OBJ_NAMES
from . import visualize as viz

SNAP_GENS = [0, 10, 20, 40, 60]          # representative snapshots
# 80 requested but GAConfig.generations defaults to 60; clamp to available gens.


def _module_population(ph: Phenotype) -> dict:
    from collections import Counter
    return dict(Counter(i.code for i in ph.instances))


def _genotype_summary(ph: Phenotype) -> dict:
    sg = {}
    names = [g[0] for g in STRUCT_GENES]
    for k, name in enumerate(names):
        if name == "n_R4":
            sg["n_R4"] = int(ph.genes[k])
        elif name.startswith("has_") or name.startswith("n_"):
            sg[name] = int(ph.genes[k])
    return sg


def _select_diverse(feasible: list[Phenotype], k: int = 4) -> list[Phenotype]:
    """Pick k diverse feasible individuals (max-min spread in objective space),
    not only final winners."""
    if len(feasible) <= k:
        return list(feasible)
    O = np.array([p.objectives for p in feasible])
    sel = [int(np.argmin(O.sum(axis=1)))]            # anchor: most balanced
    while len(sel) < k:
        d = np.min(np.linalg.norm(O[None, sel, :] - O[:, None, :], axis=2), axis=1)
        d[sel] = -1
        sel.append(int(np.argmax(d)))
    return [feasible[i] for i in sel]


def capture_catalogue(cfg: GAConfig, outdir: str, tag: str = "cat"):
    """Run NSGA-II capturing snapshots; render thumbnails + boards. Returns manifest."""
    os.makedirs(outdir, exist_ok=True)
    snaps: dict[int, list[Phenotype]] = {}
    gens = [g for g in SNAP_GENS if g <= cfg.generations]

    def _snap(gen, pop):
        snaps[gen] = [p for p in pop]

    pop, fronts, history = run(cfg, verbose=False,
                               snapshot_at=set(gens), on_snapshot=_snap)

    manifest = {"seed": cfg.seed, "generations": cfg.generations,
                "snap_gens": gens, "thumbnails": [], "boards": {}}

    # --- thumbnails: one diverse set per snapshot generation ---
    for gen in gens:
        pop_g = snaps[gen]
        feas = [p for p in pop_g if p.feasible]
        pick_from = feas if feas else pop_g
        reps = _select_diverse(pick_from, k=4)
        for r, ph in enumerate(reps):
            th = os.path.join(outdir, f"{tag}_g{gen:02d}_rep{r}.png")
            title = (f"Gen {gen} · rep{r} · seed {cfg.seed} · "
                     f"{'FEASIBLE' if ph.feasible else f'cv={ph.cv:.2f}'}")
            viz.plot_layout(ph, th, title=title)
            manifest["thumbnails"].append({
                "gen": gen, "rep": r, "seed": cfg.seed,
                "genotype": _genotype_summary(ph),
                "module_population": _module_population(ph),
                "objectives": {n: round(float(v), 4) for n, v in zip(OBJ_NAMES, ph.objectives)},
                "feasible": bool(ph.feasible), "cv": round(float(ph.cv), 4),
                "soft_cv": round(float(ph.soft_cv), 4), "image": os.path.basename(th)})

    # --- board 1: population evolution (grid of representative thumbnails) ---
    manifest["boards"]["population_evolution"] = _board_population(
        manifest["thumbnails"], outdir, tag)

    # --- board 2: Pareto / representative final front ---
    front0 = [pop[i] for i in fronts[0]]
    feas0 = [p for p in front0 if p.feasible] or front0
    manifest["boards"]["pareto_representative"] = _board_pareto(
        feas0, outdir, tag, cfg)

    # --- board 3: objective extremes (best per objective) ---
    manifest["boards"]["objective_extremes"] = _board_extremes(feas0, outdir, tag)

    # --- board 4: balanced / relative-difference selections ---
    manifest["boards"]["balanced"] = _board_balanced(feas0, outdir, tag)

    # --- board 5: final shortlist (plan + radar) ---
    manifest["boards"]["final_shortlist"] = _board_shortlist(feas0, outdir, tag)

    # convergence (reuse) for the GENERATION->PERFORMANCE chain
    conv = os.path.join(outdir, f"{tag}_convergence.png")
    viz.plot_convergence(history, conv)
    manifest["boards"]["convergence"] = os.path.basename(conv)

    mp = os.path.join(outdir, f"{tag}_manifest.json")
    with open(mp, "w") as f:
        json.dump(manifest, f, indent=2)
    manifest["manifest_path"] = mp
    return manifest


# ---------------------------------------------------------------------------
def _board_population(thumbs, outdir, tag):
    gens = sorted({t["gen"] for t in thumbs})
    reps = max(t["rep"] for t in thumbs) + 1
    fig, axes = plt.subplots(reps, len(gens), figsize=(3.0 * len(gens), 3.0 * reps))
    axes = np.atleast_2d(axes)
    if reps == 1:
        axes = axes.reshape(1, -1)
    imgs = {(t["gen"], t["rep"]): t for t in thumbs}
    for ci, gen in enumerate(gens):
        for ri in range(reps):
            ax = axes[ri][ci] if reps > 1 else axes[0][ci]
            t = imgs.get((gen, ri))
            if t is None:
                ax.axis("off"); continue
            img = plt.imread(os.path.join(outdir, t["image"]))
            ax.imshow(img); ax.axis("off")
            if ri == 0:
                ax.set_title(f"Gen {gen}", fontsize=10, weight="bold")
            ax.text(0.02, 0.02, f"nR4={t['genotype'].get('n_R4','?')} "
                    f"{'F' if t['feasible'] else 'cv'+str(t['cv'])}",
                    transform=ax.transAxes, fontsize=6,
                    bbox=dict(fc="white", alpha=0.7, pad=1))
    fig.suptitle("Population evolution — representative feasible phenotypes "
                 "(GENERATION -> SPATIAL PHENOTYPE)", fontsize=12)
    fig.tight_layout()
    p = os.path.join(outdir, f"{tag}_board_population.png")
    fig.savefig(p, dpi=130); plt.close(fig)
    return os.path.basename(p)


def _pareto_objective_pair(feas0, outdir, tag, ai=0, bi=1):
    """Simple 2-objective Pareto scatter of the final front."""
    O = np.array([p.objectives for p in feas0])
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(O[:, ai], O[:, bi], c="#0284c7", edgecolor="k", s=40)
    for i, p in enumerate(feas0):
        ax.annotate(str(i), (O[i, ai], O[i, bi]), fontsize=6)
    ax.set_xlabel(OBJ_NAMES[ai]); ax.set_ylabel(OBJ_NAMES[bi])
    ax.set_title("Final front (feasible)")
    fig.tight_layout()
    p = os.path.join(outdir, f"{tag}_pareto_pair.png")
    fig.savefig(p, dpi=130); plt.close(fig)
    return os.path.basename(p)


def _board_pareto(feas0, outdir, tag, cfg):
    reps = _select_diverse(feas0, k=min(6, len(feas0)))
    imgs = []
    for r, ph in enumerate(reps):
        th = os.path.join(outdir, f"{tag}_pareto_rep{r}.png")
        viz.plot_layout(ph, th, title=f"front rep{r} · nR4={int(ph.genes[0])}")
        imgs.append(th)
    pp = _pareto_objective_pair(feas0, outdir, tag)
    fig, axes = plt.subplots(2, 3, figsize=(13, 8))
    for ax, th in zip(axes.ravel(), imgs):
        ax.imshow(plt.imread(th)); ax.axis("off")
    fig.suptitle(f"Pareto / representative phenotypes — seed {cfg.seed} "
                 f"({len(feas0)} feasible in final front)", fontsize=12)
    fig.tight_layout()
    p = os.path.join(outdir, f"{tag}_board_pareto.png")
    fig.savefig(p, dpi=130); plt.close(fig)
    return os.path.basename(p)


def _board_extremes(feas0, outdir, tag):
    """Best individual per objective (plan thumbnail + which objective it wins)."""
    O = np.array([p.objectives for p in feas0])
    fig, axes = plt.subplots(3, 3, figsize=(13, 12))
    for k, name in enumerate(OBJ_NAMES):
        idx = int(np.argmin(O[:, k]))
        ph = feas0[idx]
        th = os.path.join(outdir, f"{tag}_ext_{k}.png")
        viz.plot_layout(ph, th, title=f"best {name.split('_')[0]}={O[idx,k]:.2f}")
        ax = axes.ravel()[k]
        ax.imshow(plt.imread(th)); ax.axis("off")
    fig.suptitle("Objective-extreme selections (best plan per objective)", fontsize=12)
    fig.tight_layout()
    p = os.path.join(outdir, f"{tag}_board_extremes.png")
    fig.savefig(p, dpi=130); plt.close(fig)
    return os.path.basename(p)


def _board_balanced(feas0, outdir, tag):
    """Balanced selections: lowest objective-spread + parallel-coordinate profile."""
    O = np.array([p.objectives for p in feas0])
    spread = O.max(axis=1) - O.min(axis=1)      # relative difference across objectives
    order = np.argsort(spread)
    picks = [feas0[i] for i in order[:3]]
    pc = os.path.join(outdir, f"{tag}_balanced_pc.png")
    viz.plot_parallel_coordinates(picks, pc, labels=list(range(len(picks))))
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))
    for r, (ax, ph) in enumerate(zip(axes, picks)):
        th = os.path.join(outdir, f"{tag}_bal_{r}.png")
        viz.plot_layout(ph, th, title=f"balanced r{r} spread={spread[order[r]]:.2f}")
        ax.imshow(plt.imread(th)); ax.axis("off")
    fig.suptitle("Relative-difference / balanced selections (min objective spread)",
                 fontsize=12)
    fig.tight_layout()
    p = os.path.join(outdir, f"{tag}_board_balanced.png")
    fig.savefig(p, dpi=130); plt.close(fig)
    return os.path.basename(p)


def _board_shortlist(feas0, outdir, tag, k=3):
    """Final shortlist: plan + radar profile per candidate."""
    reps = _select_diverse(feas0, k=min(k, len(feas0)))
    fig = plt.figure(figsize=(13, 4.5 * len(reps)))
    gs = fig.add_gridspec(len(reps), 2, width_ratios=[1.4, 1])
    for r, ph in enumerate(reps):
        th = os.path.join(outdir, f"{tag}_short_{r}_plan.png")
        viz.plot_layout(ph, th, title=f"shortlist {chr(65+r)}")
        axp = fig.add_subplot(gs[r, 0])
        axp.imshow(plt.imread(th)); axp.axis("off")
        axp.set_title(f"Candidate {chr(65+r)} · plan", fontsize=10)
        # radar inline
        axr = fig.add_subplot(gs[r, 1], polar=True)
        vals = [1 - float(v) for v in ph.objectives]
        ang = np.linspace(0, 2 * np.pi, 9, endpoint=False).tolist()
        v2 = vals + vals[:1]; a2 = ang + ang[:1]
        axr.plot(a2, v2, color="#0284c7", lw=1.6)
        axr.fill(a2, v2, color="#0284c7", alpha=0.15)
        axr.set_xticks(ang); axr.set_xticklabels([n.split("_")[0] for n in OBJ_NAMES], fontsize=6)
        axr.set_yticklabels([]); axr.set_ylim(0, 1)
        axr.set_title(f"radar (1−objective)", fontsize=8)
    fig.suptitle("Final shortlist — plan + performance radar", fontsize=12)
    fig.tight_layout()
    p = os.path.join(outdir, f"{tag}_board_shortlist.png")
    fig.savefig(p, dpi=130); plt.close(fig)
    return os.path.basename(p)


if __name__ == "__main__":  # runnable self-check
    cfg = GAConfig(pop_size=40, generations=20, seed=7)
    m = capture_catalogue(cfg, "/tmp/evo_catalogue_test", tag="t")
    assert m["thumbnails"], "no thumbnails"
    assert all(os.path.exists(os.path.join("/tmp/evo_catalogue_test", t["image"]))
               for t in m["thumbnails"])
    for k, b in m["boards"].items():
        assert os.path.exists(os.path.join("/tmp/evo_catalogue_test", b)), f"missing {k}"
    print("catalogue self-check OK:",
          len(m["thumbnails"]), "thumbnails,", len(m["boards"]), "boards")
