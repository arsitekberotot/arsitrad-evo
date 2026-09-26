"""Plotting helpers for experiment results (matplotlib, no GUI required).

Graphics suite: convergence, Pareto, cluster, k-analysis (elbow/silhouette),
simplified site plan, module diagram, privacy zoning, floor/stacking diagram,
circulation & service-separation graph, landscape ratio, radar chart,
parallel-coordinates, comparison-matrix heatmap.
"""
from __future__ import annotations
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

from .genotype import Phenotype
from .objectives import OBJECTIVES
from .modules import relation, MUST, NEAR, PROHIBITED, AVOID
from . import config as C

OBJ_NAMES = [n for n, _ in OBJECTIVES]

_COLOR = {"A0": "#7dd3fc", "B0": "#c4b5fd", "C0": "#86efac", "R4": "#fcd34d",
          "E0": "#c4b5fd", "F0": "#cbd5e1", "M0": "#94a3b8", "H0": "#6ee7b7",
          "I0": "#a7f3d0", "J0": "#fdba74", "K0": "#f9a8d4", "L0": "#ddd6fe"}
# privacy -> colour (PUBLIC..PERSONAL)
_PRIV_COLOR = {0: "#38bdf8", 1: "#a78bfa", 2: "#4ade80", 3: "#fbbf24", 4: "#fb7185"}
_PRIV_NAME = {0: "PUBLIC", 1: "CONTROLLED", 2: "SHARED", 3: "DOMESTIC", 4: "PERSONAL"}


# --- evolution / population-level -------------------------------------------
def plot_convergence(history, path):
    g = [h["gen"] for h in history]; f = [h["feasible"] for h in history]
    r = [h["rank1"] for h in history]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(g, f, label="feasible"); ax.plot(g, r, label="rank-1")
    ax.set_xlabel("generation"); ax.set_ylabel("count")
    ax.set_title("NSGA-II convergence"); ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def plot_pareto_pairs(phenos, path, m1=4, m2=0):
    feas = [p for p in phenos if p.feasible]
    if not feas:
        return
    X = np.array([np.asarray(p.objectives) for p in feas])
    ranks = np.array([p.rank for p in feas])
    fig, ax = plt.subplots(figsize=(6, 5))
    sc = ax.scatter(X[:, m1], X[:, m2], c=ranks, cmap="viridis_r",
                    s=40, edgecolor="k", linewidth=0.4)
    ax.set_xlabel(OBJ_NAMES[m1]); ax.set_ylabel(OBJ_NAMES[m2])
    ax.set_title("Objective space (feasible, colour=rank)")
    fig.colorbar(sc, label="rank"); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def plot_clusters(phenos, labels, path, m1=4, m2=0):
    X = np.array([np.asarray(p.objectives) for p in phenos])
    fig, ax = plt.subplots(figsize=(6, 5))
    sc = ax.scatter(X[:, m1], X[:, m2], c=labels, cmap="tab10",
                    s=50, edgecolor="k", linewidth=0.4)
    ax.set_xlabel(OBJ_NAMES[m1]); ax.set_ylabel(OBJ_NAMES[m2])
    ax.set_title("K-means families on Pareto front")
    fig.colorbar(sc, label="cluster"); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def plot_k_analysis(ks, inertias, silhouettes, k_chosen, k_elbow, path):
    fig, ax1 = plt.subplots(figsize=(7, 4))
    ax1.plot(ks, inertias, "o-", color="#475569", label="inertia (elbow)")
    ax1.set_xlabel("k"); ax1.set_ylabel("inertia", color="#475569")
    ax1.axvline(k_elbow, color="#475569", ls="--", alpha=0.5)
    ax2 = ax1.twinx()
    ax2.plot(ks, silhouettes, "s-", color="#16a34a", label="silhouette")
    ax2.set_ylabel("silhouette", color="#16a34a")
    ax2.axvline(k_chosen, color="#16a34a", ls="--", alpha=0.6)
    ax1.set_title(f"K selection — silhouette k={k_chosen}, elbow k={k_elbow}")
    ax1.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def plot_parallel_coordinates(phenos, path, labels=None):
    X = np.array([np.asarray(p.objectives) for p in phenos])
    lo, hi = X.min(0), X.max(0); rng = np.where((hi - lo) < 1e-12, 1, hi - lo)
    Xn = (X - lo) / rng
    fig, ax = plt.subplots(figsize=(11, 5))
    colors = labels if labels is not None else np.zeros(len(Xn))
    cmap = plt.get_cmap("tab10")
    for i, row in enumerate(Xn):
        ax.plot(range(len(row)), row, color=cmap(int(colors[i]) % 10),
                alpha=0.4, linewidth=1)
    ax.set_xticks(range(len(OBJ_NAMES)))
    ax.set_xticklabels([n.split("_")[0] for n in OBJ_NAMES], rotation=0, fontsize=8)
    ax.set_ylabel("normalised objective (0=best)"); ax.set_ylim(-0.02, 1.02)
    ax.set_title("Parallel coordinates — Pareto phenotypes")
    ax.grid(alpha=0.2, axis="y")
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


# --- per-phenotype architectural diagrams ------------------------------------
def plot_layout(ph: Phenotype, path, title=""):
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.add_patch(Rectangle((0, 0), C.SITE_W, C.SITE_H, fill=False, edgecolor="k", linewidth=1.5))
    for i in ph.instances:
        ax.add_patch(Rectangle((i.x - i.w/2, i.y - i.d/2), i.w, i.d,
                               facecolor=_COLOR.get(i.code, "#eee"), edgecolor="k", alpha=0.85))
        ax.text(i.x, i.y, i.code, ha="center", va="center", fontsize=7, weight="bold")
    ax.set_xlim(-2, C.SITE_W+2); ax.set_ylim(-2, C.SITE_H+2); ax.set_aspect("equal")
    ax.set_title(title or f"site plan | R4x{ph.n_R4} res={ph.residents} fp={ph.footprint:.0f} GFA={ph.gfa:.0f}")
    ax.set_xticks([]); ax.set_yticks([])
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def plot_privacy_zoning(ph: Phenotype, path):
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.add_patch(Rectangle((0, 0), C.SITE_W, C.SITE_H, fill=False, edgecolor="k", linewidth=1.2))
    for i in ph.instances:
        ax.add_patch(Rectangle((i.x - i.w/2, i.y - i.d/2), i.w, i.d,
                               facecolor=_PRIV_COLOR[i.privacy], edgecolor="k", alpha=0.8))
        ax.text(i.x, i.y, f"{i.code}\n{_PRIV_NAME[i.privacy][:4]}", ha="center",
                va="center", fontsize=6, weight="bold")
    handles = [Rectangle((0, 0), 1, 1, facecolor=_PRIV_COLOR[k]) for k in sorted(_PRIV_COLOR)]
    ax.legend(handles, [_PRIV_NAME[k] for k in sorted(_PRIV_NAME)],
              loc="upper right", fontsize=7, title="privacy")
    ax.set_xlim(-2, C.SITE_W+2); ax.set_ylim(-2, C.SITE_H+2); ax.set_aspect("equal")
    ax.set_title(f"privacy zoning | R4x{ph.n_R4}")
    ax.set_xticks([]); ax.set_yticks([])
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def plot_stacking(ph: Phenotype, path):
    """Floor/stacking diagram: bar of floors per module instance."""
    codes = [f"{i.code}{n}" for n, i in enumerate(ph.instances)]
    floors = [i.floors for i in ph.instances]
    cols = [_COLOR.get(i.code, "#eee") for i in ph.instances]
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(range(len(floors)), floors, color=cols, edgecolor="k")
    ax.set_xticks(range(len(codes))); ax.set_xticklabels(codes, rotation=90, fontsize=7)
    ax.set_ylabel("floors"); ax.set_ylim(0, max(floors) + 1)
    ax.axhline(1, color="k", lw=0.5, alpha=0.4)
    ax.set_title(f"floor / stacking diagram | GFA={ph.gfa:.0f} footprint={ph.footprint:.0f}")
    ax.grid(alpha=0.2, axis="y")
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def plot_circulation(ph: Phenotype, path):
    """Circulation & service-separation graph: nodes=modules, edges=MUST/NEAR
    (circulation) in green, PROHIBITED/service conflicts in red."""
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.add_patch(Rectangle((0, 0), C.SITE_W, C.SITE_H, fill=False, edgecolor="k", linewidth=1))
    inst = ph.instances
    for a in range(len(inst)):
        for b in range(a+1, len(inst)):
            ia, ib = inst[a], inst[b]
            rel = relation(ia.code, ib.code)
            if rel in (MUST, NEAR):
                ax.plot([ia.x, ib.x], [ia.y, ib.y], color="#16a34a",
                        lw=1.4 if rel == MUST else 0.7, alpha=0.6, zorder=1)
            elif rel == PROHIBITED:
                ax.plot([ia.x, ib.x], [ia.y, ib.y], color="#dc2626",
                        lw=1.2, ls="--", alpha=0.6, zorder=1)
    for i in inst:
        ax.add_patch(Rectangle((i.x - i.w/2, i.y - i.d/2), i.w, i.d,
                               facecolor=_COLOR.get(i.code, "#eee"), edgecolor="k",
                               alpha=0.9, zorder=2))
        ax.text(i.x, i.y, i.code, ha="center", va="center", fontsize=6, weight="bold", zorder=3)
    ax.plot([], [], color="#16a34a", label="MUST/NEAR circulation")
    ax.plot([], [], color="#dc2626", ls="--", label="PROHIBITED (keep separated)")
    ax.legend(loc="upper right", fontsize=7)
    ax.set_xlim(-2, C.SITE_W+2); ax.set_ylim(-2, C.SITE_H+2); ax.set_aspect("equal")
    ax.set_title("circulation & service-separation graph")
    ax.set_xticks([]); ax.set_yticks([])
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def plot_landscape_ratio(ph: Phenotype, path):
    built = ph.footprint; reserve = ph.reserve_area
    landscape = ph.landscape_area
    other = max(0.0, C.SITE_AREA - built - reserve - landscape)
    vals = [built, landscape, reserve, other]
    labs = [f"built {built:.0f}", f"landscape {landscape:.0f}",
            f"reserve {reserve:.0f}", f"other/circ {other:.0f}"]
    cols = ["#fbbf24", "#4ade80", "#cbd5e1", "#e2e8f0"]
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(vals, labels=labs, colors=cols, autopct="%1.0f%%", startangle=90,
           textprops={"fontsize": 8}, wedgeprops={"edgecolor": "k"})
    ax.set_title(f"site area budget (total {C.SITE_AREA:.0f} m²)\nlandscape {ph.landscape_frac*100:.0f}%")
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def plot_radar(ph: Phenotype, path, title=""):
    objs = np.asarray(ph.objectives)
    perf = 1.0 - objs                       # higher = better for radar
    M = len(perf)
    ang = np.linspace(0, 2*np.pi, M, endpoint=False).tolist()
    perf_c = np.concatenate([perf, [perf[0]]]); ang_c = ang + [ang[0]]
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={"polar": True})
    ax.plot(ang_c, perf_c, color="#0284c7", lw=2)
    ax.fill(ang_c, perf_c, color="#0284c7", alpha=0.25)
    ax.set_xticks(ang); ax.set_xticklabels([n.split("_")[0] for n in OBJ_NAMES], fontsize=8)
    ax.set_ylim(0, 1); ax.set_yticks([0.25, 0.5, 0.75, 1.0]); ax.set_yticklabels([])
    ax.set_title(title or f"performance radar | R4x{ph.n_R4} res={ph.residents}", pad=18)
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def plot_comparison_heatmap(rows: list[dict], path):
    """rows from analyze.comparison_matrix — heatmap of objectives per rep."""
    if not rows:
        return
    reps = [f"rep{r['rep']}" for r in rows]
    M = len(OBJ_NAMES)
    Z = np.array([[r[OBJ_NAMES[m]] for m in range(M)] for r in rows], dtype=float)
    fig, ax = plt.subplots(figsize=(11, max(3, 0.5*len(rows)+1)))
    im = ax.imshow(Z, aspect="auto", cmap="RdYlGn_r", vmin=0, vmax=1)
    ax.set_xticks(range(M)); ax.set_xticklabels([n.split("_")[0] for n in OBJ_NAMES], fontsize=8)
    ax.set_yticks(range(len(reps))); ax.set_yticklabels(reps, fontsize=8)
    for i in range(len(rows)):
        for j in range(M):
            ax.text(j, i, f"{Z[i,j]:.2f}", ha="center", va="center", fontsize=6)
    ax.set_title("comparison matrix — objective values (lower=better, green=good)")
    fig.colorbar(im, label="objective (min)")
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)
