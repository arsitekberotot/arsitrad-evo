"""v4 visualization — real-site polygon layouts.

Draws the actual irregular parcel boundary from site.geojson (not the legacy
rectangle) plus decoded module footprints, anchors, and privacy zones.

Provenance: rendering [DESIGN HYPOTHESIS]; geometry [VERIFIED via site].
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon as MplPolygon
from matplotlib.lines import Line2D

from .genotype_v4 import PhenotypeV4
from .site import Site, SiteMode, buildable_polygon, anchor_point

_FAMILY_COLOR = {
    "sleeping":  "#60a5fa",
    "care":      "#a78bfa",
    "living":    "#4ade80",
    "service":   "#fbbf24",
    "civic":     "#fb7185",
    "climate":   "#34d399",
    "communal":  "#f472b6",
    "support":   "#94a3b8",
}
_PRIV_COLOR = {0: "#38bdf8", 1: "#a78bfa", 2: "#4ade80", 3: "#fbbf24", 4: "#fb7185"}


def _draw_site(ax, site: Site, show_buildable: bool = True):
    poly = site.boundary_polygon
    if poly:
        ax.add_patch(MplPolygon(poly, closed=True, fill=True,
                                facecolor="#f8fafc", edgecolor="#0f172a",
                                linewidth=2.0, zorder=0))
        if show_buildable:
            bp = buildable_polygon(site)
            if bp:
                ax.add_patch(MplPolygon(bp, closed=True, fill=False,
                                        edgecolor="#64748b", linewidth=1.0,
                                        linestyle="--", zorder=1))
    # frontage edges highlighted
    for ei in getattr(site, "frontage_edges", []):
        if 0 <= ei < len(site.edges):
            e = site.edges[ei]
            ax.plot([e.start[0], e.end[0]], [e.start[1], e.end[1]],
                    color="#16a34a", linewidth=3.5, zorder=2, solid_capstyle="round")
    # An exact public gate appears only if a coordinate has been verified.
    pe = anchor_point(site, "public_entry")
    if pe:
        ax.plot([pe[0]], [pe[1]], marker="*", markersize=18, color="#16a34a",
                zorder=6, markeredgecolor="#0f172a")
    ax.set_aspect("equal")
    ax.autoscale_view()


def _draw_instances(ax, ph: PhenotypeV4, color_by: str = "family"):
    for inst in ph.instances:
        x0, y0 = inst.x - inst.w / 2, inst.y - inst.d / 2
        if color_by == "privacy":
            face = _PRIV_COLOR.get(getattr(inst, "privacy_level", 2), "#cbd5e1")
        else:
            face = _FAMILY_COLOR.get(inst.family, "#cbd5e1")
        zorder = 3 if inst.floor == 0 else 4
        alpha = 0.9 if inst.floor == 0 else 0.55
        ax.add_patch(Rectangle((x0, y0), inst.w, inst.d, facecolor=face,
                               edgecolor="#0f172a", linewidth=1.0, alpha=alpha,
                               zorder=zorder))
        lbl = inst.code + (f"·F{inst.floor}" if inst.floor > 0 else "")
        ax.text(inst.x, inst.y, lbl, ha="center", va="center", fontsize=6,
                color="#0f172a", zorder=5)


def plot_layout_real(ph: PhenotypeV4, site: Site, path, title: str = ""):
    """Plan layout of a v4 phenotype on the REAL site polygon."""
    fig, ax = plt.subplots(figsize=(9, 8))
    _draw_site(ax, site)
    _draw_instances(ax, ph, color_by="family")
    handles = [Line2D([0], [0], marker="s", color="w", markerfacecolor=c,
                      markersize=10, label=fam)
               for fam, c in _FAMILY_COLOR.items()]
    handles.append(Line2D([0], [0], color="#16a34a", linewidth=3, label="arrival zone"))
    if anchor_point(site, "public_entry") is not None:
        handles.append(Line2D([0], [0], marker="*", color="w", markerfacecolor="#16a34a",
                              markersize=14, label="verified public gate"))
    ax.legend(handles=handles, loc="upper right", fontsize=7, framealpha=0.9)
    cap = (f"{title}\nGFA {ph.gfa:.0f} m² · residents {ph.residents} · "
           f"day-users {ph.day_users} · feasible={ph.feasible}")
    ax.set_title(cap, fontsize=10)
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_privacy_real(ph: PhenotypeV4, site: Site, path):
    """Privacy-gradient zoning on the REAL site."""
    fig, ax = plt.subplots(figsize=(9, 8))
    _draw_site(ax, site)
    _draw_instances(ax, ph, color_by="privacy")
    handles = [Rectangle((0, 0), 1, 1, facecolor=_PRIV_COLOR[k],
                         label=f"P{k}") for k in sorted(_PRIV_COLOR)]
    ax.legend(handles=handles, loc="upper right", fontsize=8)
    ax.set_title("Privacy gradient (P0 public → P4 private)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_pareto_front(pop, path):
    """2-D projection of the Pareto front (minimization-form objectives)."""
    fig, ax = plt.subplots(figsize=(7, 6))
    feas = [p for p in pop if p.feasible]
    if not feas:
        feas = pop
    X = np.array([p.objectives for p in feas])
    ax.scatter(X[:, 0], X[:, 1], s=40, c="#3b82f6", alpha=0.7,
               edgecolor="#0f172a")
    ax.set_xlabel("obj[0] (site response, min)")
    ax.set_ylabel("obj[1] (access clarity, min)")
    ax.set_title(f"Pareto projection — {len(feas)} solutions")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_convergence_v4(history, path):
    gens = [g["gen"] for g in history["generations"]]
    feas = [g["feasible_ratio"] for g in history["generations"]]
    psize = [g["pareto_size"] for g in history["generations"]]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(gens, feas, "o-", color="#16a34a", label="feasible ratio")
    ax2 = ax.twinx()
    ax2.plot(gens, psize, "s-", color="#3b82f6", label="Pareto size")
    ax.set_xlabel("generation"); ax.set_ylabel("feasible ratio")
    ax2.set_ylabel("Pareto front size")
    ax.set_ylim(0, 1.05)
    ax.set_title("NSGA-II v4 convergence on real site")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
