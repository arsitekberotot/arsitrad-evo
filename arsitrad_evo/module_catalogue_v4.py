"""Module Library Catalogue (V4).

Renders and exports the rebuilt architectural module library organised by
FUNCTION (family) x SIZE (S/M/L) x MODULARITY CATEGORY (developmental /
variational / repeatable), supplemented with capacity, privacy, access type,
repeatability, stackability and evidence status.

Adapts Riskiyanto et al.'s modularity methodology to building/campus scale:
a module is a typed, dimensioned, capacity-bearing unit whose FUNCTION, SIZE,
MODULARITY, CAPACITY and PRIVACY jointly define its place in the gene pool.
The catalogue is the machine-readable contract between the module library and
the evolutionary genotype.

Outputs:
  - module_catalogue_v4.json : full machine-readable library (per-module fields)
  - module_catalogue_v4.csv  : flat table, one row per module code
  - module_catalogue_v4.png  : visual FUNCTION x SIZE x MODULARITY grid

Every capacity/area is the module's own evidence-tagged value ([PA5 CORPUS] /
[DESIGN HYPOTHESIS]); nothing is fabricated. Family names are display labels
[DESIGN HYPOTHESIS] unless drawn from the corpus.
"""
from __future__ import annotations

import csv
import json
import os
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Patch, Rectangle
from matplotlib.lines import Line2D

from .modules_v4 import (
    MODULE_LIBRARY_V4, FAMILY_VARIANTS,
    SizeClass, ModularityCategory, RotationPolicy,
)

# Display labels for the functional families [DESIGN HYPOTHESIS].
FAMILY_LABELS = {
    "R4": "Domestic",
    "A0": "Arrival",
    "B0": "Care",
    "C0": "Commons",
    "H0": "Learning",
    "J0": "Livelihood",
    "K0": "Community",
    "I0": "Reflection",
    "L0": "Transition",
    "F0": "Service",
    "M0": "Maintenance",
}

MODULARITY_COLORS = {
    ModularityCategory.DEVELOPMENTAL: "#2f6f4f",   # core identity (green)
    ModularityCategory.VARIATIONAL: "#b07a2a",     # program-altering (amber)
    ModularityCategory.REPEATABLE: "#3a5f8a",      # replicable unit (blue)
}
SIZE_ORDER = [SizeClass.SMALL, SizeClass.MEDIUM, SizeClass.LARGE]


def _access_type(m) -> str:
    """Human-readable access type from access/service faces [DESIGN HYPOTHESIS]."""
    a, s = set(m.access_faces), set(m.service_faces)
    if s and not a:
        return "service-only"
    if a and s:
        return "public+service"
    if a:
        return "public"
    return "internal"


def module_record(code: str) -> dict:
    """Flat machine-readable record for one module code."""
    m = MODULE_LIBRARY_V4[code]
    return {
        "code": m.code,
        "name": m.name,
        "function_family": m.family,
        "function_label": FAMILY_LABELS.get(m.family, m.family),
        "size_class": m.size_class.value,
        "modularity_category": m.modularity.value,
        "width_m": m.w, "depth_m": m.d, "area_m2": m.area,
        "max_floors": m.max_floors,
        "capacity_residents": m.capacity_residents,
        "capacity_day_users": m.capacity_day_users,
        "capacity_staff": m.capacity_staff,
        "privacy_level": m.privacy_level,
        "access_type": _access_type(m),
        "access_faces": list(m.access_faces),
        "service_faces": list(m.service_faces),
        "repeatable": m.repeatable,
        "min_count": m.min_count, "max_count": m.max_count,
        "ground_required": m.ground_required,
        "stackable_above": m.stackable_above,
        "stackable_below": m.stackable_below,
        "rotation_policy": m.rotation_policy.value,
        "allowed_rotations": list(m.allowed_rotations),
        "evidence_status": m.provenance,
        "description": m.description,
    }


def export_json(out_path: str) -> dict:
    lib = {
        "schema": "module-library-catalogue/v4",
        "methodology": ("FUNCTION + SIZE + MODULARITY + CAPACITY + PRIVACY "
                        "-> MODULE LIBRARY (Riskiyanto et al. adapted to "
                        "building/campus scale)"),
        "axes": {"function_families": list(FAMILY_VARIANTS.keys()),
                 "size_classes": [s.value for s in SIZE_ORDER],
                 "modularity_categories":
                     [c.value for c in ModularityCategory]},
        "family_labels": FAMILY_LABELS,
        "family_variants": {k: list(v) for k, v in FAMILY_VARIANTS.items()},
        "modules": {code: module_record(code) for code in MODULE_LIBRARY_V4},
    }
    with open(out_path, "w") as f:
        json.dump(lib, f, indent=2)
    return lib


def export_csv(out_path: str) -> None:
    codes = sorted(MODULE_LIBRARY_V4.keys())
    recs = [module_record(c) for c in codes]
    if not recs:
        return
    cols = ["code", "function_label", "size_class", "modularity_category",
            "area_m2", "max_floors", "capacity_residents", "capacity_day_users",
            "capacity_staff", "privacy_level", "access_type", "repeatable",
            "stackable_above", "stackable_below", "rotation_policy",
            "evidence_status"]
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in recs:
            w.writerow({c: r[c] for c in cols})


def render_grid(out_path: str) -> None:
    """Visual FUNCTION x SIZE x MODULARITY grid.

    Rows = functional families; columns = S/M/L size classes. Each present
    cell is a chip coloured by modularity category and annotated with code,
    capacity and privacy. Absent cells are left blank (no fabricated variants).
    """
    fams = [f for f in FAMILY_VARIANTS.keys() if f in FAMILY_LABELS]
    fams.sort(key=lambda f: (f != "R4", f))  # R4 (domestic) first
    nrows, ncols = len(fams), len(SIZE_ORDER)

    fig, ax = plt.subplots(figsize=(11, 0.95 * nrows + 2.4))
    ax.set_xlim(0, ncols)
    ax.set_ylim(0, nrows + 1)
    ax.axis("off")

    # column headers
    for j, sc in enumerate(SIZE_ORDER):
        ax.text(j + 0.5, nrows + 0.55, f"SIZE {sc.value}",
                ha="center", va="center", fontsize=11, weight="bold")

    for i, fam in enumerate(fams):
        y = nrows - 1 - i
        ax.text(-0.08, y + 0.5,
                f"{FAMILY_LABELS[fam]}  ({fam})",
                ha="right", va="center", fontsize=10, weight="bold")
        variants = FAMILY_VARIANTS.get(fam, [])
        # map size_class -> module code (first variant of that size)
        by_size = {}
        for code in variants:
            sc = MODULE_LIBRARY_V4[code].size_class
            by_size.setdefault(sc, code)
        for j, sc in enumerate(SIZE_ORDER):
            code = by_size.get(sc)
            cx, cy = j + 0.5, y + 0.5
            if code is None:
                ax.add_patch(Rectangle((j + 0.04, y + 0.12), 0.92, 0.76,
                                       facecolor="#f2f2f2",
                                       edgecolor="#dddddd", lw=0.6))
                ax.text(cx, cy, "—", ha="center", va="center",
                        color="#bbbbbb", fontsize=12)
                continue
            m = MODULE_LIBRARY_V4[code]
            color = MODULARITY_COLORS[m.modularity]
            ax.add_patch(FancyBboxPatch((j + 0.05, y + 0.10), 0.90, 0.80,
                                        boxstyle="round,pad=0.02,rounding_size=0.05",
                                        facecolor=color, edgecolor="#222222",
                                        lw=0.8, alpha=0.92))
            cap = []
            if m.capacity_residents:
                cap.append(f"{m.capacity_residents}R")
            if m.capacity_day_users:
                cap.append(f"{m.capacity_day_users}D")
            if m.capacity_staff:
                cap.append(f"{m.capacity_staff}S")
            cap_s = " ".join(cap) if cap else "—"
            flags = []
            if m.repeatable:
                flags.append("rep")
            if m.stackable_above or m.stackable_below or m.max_floors > 1:
                flags.append("stk")
            if m.ground_required:
                flags.append("gnd")
            ax.text(cx, cy + 0.18, code, ha="center", va="center",
                    color="white", fontsize=10, weight="bold")
            ax.text(cx, cy - 0.02,
                    f"{m.area:.0f}m²  P{m.privacy_level}",
                    ha="center", va="center", color="white", fontsize=7.5)
            ax.text(cx, cy - 0.20, f"{cap_s}  {'/'.join(flags)}",
                    ha="center", va="center", color="white", fontsize=7)

    # legend
    handles: list = [Patch(facecolor=MODULARITY_COLORS[c], edgecolor="#222222",
                           label=c.value) for c in ModularityCategory]
    handles.append(Line2D([0], [0], marker="", color="none",
                          label="R=residents D=day-users S=staff  P=privacy"))
    handles.append(Line2D([0], [0], marker="", color="none",
                          label="rep=repeatable stk=stackable gnd=ground-only"))
    ax.legend(handles=handles, loc="lower center", ncol=3,
              bbox_to_anchor=(0.5, -0.10), frameon=False, fontsize=8)

    ax.set_title("The Threshold — Module Library Catalogue (V4)\n"
                 "FUNCTION × SIZE × MODULARITY  ·  capacity / privacy / access",
                 fontsize=12, weight="bold", pad=18)
    fig.tight_layout()
    fig.savefig(out_path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def build_catalogue(out_dir: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    lib = export_json(os.path.join(out_dir, "module_catalogue_v4.json"))
    export_csv(os.path.join(out_dir, "module_catalogue_v4.csv"))
    render_grid(os.path.join(out_dir, "module_catalogue_v4.png"))
    return lib


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="module_catalogue_v4")
    args = ap.parse_args()
    lib = build_catalogue(args.out)
    print(f"[catalogue] {len(lib['modules'])} modules, "
          f"{len(lib['family_variants'])} families -> {args.out}/")
