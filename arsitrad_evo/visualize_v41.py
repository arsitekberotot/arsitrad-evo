"""Four coordinated, data-backed V4.1 publication figures."""
from __future__ import annotations

import json
import math
import os
from collections import Counter
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent.parent / ".mplcache"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon, Rectangle
import numpy as np

from .context_v41 import ZONE_ORDER
from .pipeline_v41 import FAMILIES
from .program_v41 import catalogue


ZONE_COLORS = {"public_civic": "#cc6f4a", "controlled_care": "#ad8a45",
               "shared_everyday": "#7e9d63", "domestic": "#567f91",
               "personal": "#79678f", "service": "#817c72"}
INK = "#24323b"
PAPER = "#f7f4eb"


def _save(fig, path, identity, phenotype_id=None):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    metadata = {"Software": "arsitrad-evo V4.1",
                "Description": json.dumps({"identity": identity,
                                           "phenotype_id": phenotype_id}, sort_keys=True)}
    fig.savefig(path, dpi=160, facecolor=PAPER, bbox_inches="tight", metadata=metadata)
    plt.close(fig)


def render_module_catalogue(path, identity):
    records = catalogue()
    fig, ax = plt.subplots(figsize=(15, 12), facecolor=PAPER)
    ax.set_facecolor(PAPER)
    ax.set_xlim(-1.5, 3.15)
    ax.set_ylim(-1.15, len(FAMILIES) + 0.8)
    ax.axis("off")
    ax.text(-1.5, len(FAMILIES) + 0.45, "MODULE LIBRARY  /  V4.1", size=19,
            weight="bold", color=INK)
    ax.text(-1.5, len(FAMILIES) + 0.08,
            "Function rows. Size columns. Each cell lists its program difference.",
            size=9, color=INK)
    for x, size in enumerate(("S", "M", "L")):
        ax.text(x + 0.42, len(FAMILIES) - 0.33, f"SIZE {size}", weight="bold",
                ha="center", size=10, color=INK)
    for row, family in enumerate(FAMILIES):
        y = len(FAMILIES) - 1.45 - row
        ax.text(-1.45, y + 0.30, family, size=13, weight="bold", color=INK)
        variants = [r for r in records.values() if r["function"] == family]
        for x, size in enumerate(("S", "M", "L")):
            match = [r for r in variants if r["size"] == size]
            if not match:
                ax.add_patch(Rectangle((x, y - 0.05), .87, .77,
                                       facecolor="#eeeae1", edgecolor="#d5d0c5", lw=.5))
                continue
            r = match[0]
            color = "#557a71" if r["modularity_category"] == "developmental" else "#ac7950"
            ax.add_patch(Rectangle((x, y - 0.05), .87, .77,
                                   facecolor=color, edgecolor="#38454b", lw=.5))
            components = " · ".join(f"{c['count']} {c['component'].split('_')[0]}"
                                    for c in r["program_composition"][:2])
            capacity = (f"{r['resident_capacity']} residents" if r["resident_capacity"]
                        else f"{r['nominal_room_capacity']} room places" if r["nominal_room_capacity"]
                        else f"{r['nominal_staff_capacity']} staff places")
            ax.text(x + .04, y + .54, r["code"], size=10, weight="bold", color="white")
            ax.text(x + .04, y + .34, f"{r['area_m2']:.0f} m²  ·  {capacity}",
                    size=7.5, color="white")
            ax.text(x + .04, y + .09, components, size=7.0, color="white")
    ax.text(-1.45, -0.98,
            "Green: developmental. Ochre: variational. Empty cells are unproposed variants. "
            "Component counts are design hypotheses.", size=8.5, color=INK)
    _save(fig, path, identity)


def render_pipeline_board(nodes, path, identity):
    fig, ax = plt.subplots(figsize=(17, 11), facecolor=PAPER)
    ax.set_facecolor(PAPER)
    ax.set_xlim(0, 4)
    rows = math.ceil(len(nodes) / 4)
    ax.set_ylim(-0.5, rows + 0.8)
    ax.axis("off")
    ax.text(0, rows + 0.38, "ADAPTED DATA FLOW  /  ACTUAL RUNNING STAGES",
            size=17, weight="bold", color=INK)
    for index, node in enumerate(nodes):
        row, col = divmod(index, 4)
        x, y = col + .03, rows - row - .87
        ax.add_patch(Rectangle((x, y), .92, .70, facecolor="#e6e4db",
                               edgecolor="#6e7775", lw=.8))
        ax.text(x + .04, y + .53, f"{index + 1:02d}  {node['stage'].replace('_', ' ').upper()}",
                size=8.3, weight="bold", color=INK)
        ax.text(x + .04, y + .31, node["code"].replace("arsitrad_evo/", ""),
                size=7.4, color=INK)
        ax.text(x + .04, y + .11, Path(node["dataset"]).name,
                size=6.0, color="#4f625e")
        ax.text(x + .88, y + .11, str(node["records"]), ha="right",
                size=6.0, color="#4f625e")
        if index < len(nodes) - 1 and col < 3:
            ax.annotate("", xy=(x + 1.0, y + .35), xytext=(x + .93, y + .35),
                        arrowprops={"arrowstyle": "->", "color": "#a16448", "lw": 1.2})
        if col == 3 and index < len(nodes) - 1:
            ax.text(x + .02, y - .11, f"CONTINUES AT {index + 2:02d} ↓",
                    size=6.5, color="#a16448", weight="bold")
    ax.text(0, -.32,
            "Dataset names are under stages/; right-hand numbers are record counts. "
            "Circle packing is adapted as architectural grouping.", size=8, color=INK)
    _save(fig, path, identity)


def render_population_selection(archive_records, selections, path, identity):
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), facecolor=PAPER)
    for ax in axes.flat:
        ax.set_facecolor(PAPER)
        ax.spines[["top", "right"]].set_visible(False)
    feasible = [row for row in archive_records if row["feasible"]]
    residents = [row["residents"] for row in feasible]
    axes[0, 0].hist(residents, bins=range(0, 37, 4), color="#557a71", edgecolor=PAPER)
    axes[0, 0].set_title("Feasible resident populations")
    axes[0, 0].set_xlabel("Residents")
    axes[0, 0].set_ylabel("Archived phenotypes")
    modularity = [row["unit_population"]["variational_ratio"] for row in feasible]
    axes[0, 1].hist(modularity, bins=12, color="#ac7950", edgecolor=PAPER)
    axes[0, 1].set_title("Variational unit share")
    axes[0, 1].set_xlabel("Fraction of retained units")
    patterns = Counter(row["packing_pattern"] for row in feasible)
    axes[1, 0].bar(patterns.keys(), patterns.values(), color="#567f91")
    axes[1, 0].tick_params(axis="x", rotation=30)
    axes[1, 0].set_title("Grouping patterns in feasible archive")
    selected = selections["selected"]
    axes[1, 1].axis("off")
    lines = ["SELECTION MODES  /  all-generation archive", ""]
    lines.extend(f"{name.replace('_', ' ')}  →  {gid}" for name, gid in selected.items())
    lines.append("")
    lines.append(f"All-population Pareto: {len(selections['all_population_pareto_ids'])}")
    lines.append(f"Final-generation Pareto: {len(selections['final_generation_pareto_ids'])}")
    lines.append(f"Distinct architectural signatures: {selections['distinct_architectural_signatures']}")
    axes[1, 1].text(0, 1, "\n".join(lines), va="top", size=8.4, color=INK,
                    family="monospace", linespacing=1.35)
    fig.suptitle("EVOLUTIONARY POPULATION + SELECTION CATALOGUE  /  V4.1",
                 size=16, weight="bold", color=INK)
    fig.tight_layout(rect=[0, 0, 1, .96])
    _save(fig, path, identity)


def render_phenotype_sheet(ph, site, ranks, path, identity):
    fig = plt.figure(figsize=(15, 9), facecolor=PAPER)
    grid = fig.add_gridspec(2, 3, width_ratios=[1.9, 1, 1], height_ratios=[1, 1],
                           left=.04, right=.97, top=.88, bottom=.07, wspace=.18, hspace=.15)
    ax = fig.add_subplot(grid[:, 0])
    ax.set_facecolor(PAPER)
    ax.add_patch(MplPolygon(site.boundary_polygon, closed=True,
                            facecolor="#ede8dc", edgecolor=INK, lw=1.6))
    for i in site.frontage_edges:
        edge = site.edges[i]
        ax.plot([edge.start[0], edge.end[0]], [edge.start[1], edge.end[1]],
                color="#c15f3f", lw=4, solid_capstyle="round")
    for inst in ph.instances:
        color = ZONE_COLORS[inst.target_zone]
        ax.add_patch(Rectangle((inst.x - inst.w / 2, inst.y - inst.d / 2),
                               inst.w, inst.d, facecolor=color, edgecolor=INK,
                               alpha=.80 if inst.floor == 0 else .45, lw=.8))
        ax.text(inst.x, inst.y, inst.code + ("↑" if inst.floor else ""), ha="center",
                va="center", size=6.5, color="white" if inst.floor == 0 else INK,
                weight="bold")
    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.set_xlabel("local x  /  m")
    ax.set_ylabel("local y  /  m")
    ax.set_title("REAL PARCEL PLAN  ·  orange edge = arrival zone", size=10, color=INK)

    radar = fig.add_subplot(grid[0, 1:], projection="polar")
    values = [r.value for r in ph.objective_vector.results]
    labels = [r.name.replace("_", "\n") for r in ph.objective_vector.results]
    theta = np.linspace(0, 2 * np.pi, len(values), endpoint=False)
    radar.plot(np.r_[theta, theta[0]], np.r_[values, values[0]], color="#ad684c", lw=2)
    radar.fill(np.r_[theta, theta[0]], np.r_[values, values[0]], color="#ad684c", alpha=.22)
    radar.set_xticks(theta)
    radar.set_xticklabels(labels, size=7)
    radar.set_ylim(0, 1)
    radar.set_yticks([.25, .5, .75, 1.0])
    radar.set_yticklabels([".25", ".5", ".75", "1"], size=6)
    radar.set_title("DECISION DIAMOND  /  outer is better", size=10, color=INK, pad=18)

    axdata = fig.add_subplot(grid[1, 1:])
    axdata.axis("off")
    m = ph.objective_submetrics
    up = ph.unit_population
    def fmt(value):
        return "—" if value is None else f"{value:.1f}"
    module_parts = [f"{family}×{count}" for family, count in up.get("by_function", {}).items()]
    module_lines = [" ".join(module_parts[:5]), " ".join(module_parts[5:])]
    zone_parts = [f"{name.split('_')[0]}:{count}" for name, count in ph.zone_population.items()]
    zone_lines = [" ".join(zone_parts[:3]), " ".join(zone_parts[3:])]
    left = [
        "PROGRAM + FORM",
        f"{ph.residents} residents · {ph.day_users} concurrent day users · {ph.staff} staff",
        f"Room cap {ph.nominal_day_capacity} · staff cap {ph.nominal_staff_capacity}",
        "Units " + module_lines[0],
        "      " + module_lines[1],
        f"Developmental {up.get('developmental_population')} · variational {up.get('variational_population')}",
        f"Zone {ph.zone_state['type']}",
        "      " + zone_lines[0],
        "      " + zone_lines[1],
        f"GFA {ph.gfa:.0f} · footprint {ph.footprint:.0f} · landscape {ph.landscape_area:.0f} m²",
        f"{ph.floor_count} floor(s) · {ph.stacked_pairs} stacked pairs · {ph.packing_utilization:.0%} utilization",
        f"{ph.generated_units} generated → {ph.retained_units} retained → {len(ph.filtered_units)} filtered",
        f"Collision {ph.collision_report['illegal_overlap_count']} illegal / {ph.collision_report['illegal_overlap_area_m2']:.2f} m²",
        f"Seed {ph.origin_seed} · birth G{ph.birth_generation} · "
        + (f"survived through G{ph.selected_generation}"
           if ph.selected_generation is not None else "archive-only birth"),
    ]
    right = [
        "SPATIAL + FITNESS EVIDENCE",
        f"Care response {fmt(m.get('care_response_distance_m'))} m",
        f"Resident route {fmt(m.get('resident_route_length_m'))} m",
        f"Visitor route {fmt(m.get('visitor_route_length_m'))} m",
        f"Service route {fmt(m.get('service_route_length_m'))} m",
        f"Sensitive sightlines {m.get('sensitive_sightline_exposure_count')}",
        f"Privacy violations {m.get('privacy_transition_violations')}",
        f"Arrival relationship {fmt(m.get('entry_relationship_distance_m'))} m",
        f"Environmental exposure {fmt(m.get('environmental_exposure'))}",
        "Fitness " + " · ".join(f"F{j+1} {r.value:.2f}" for j, r in enumerate(ph.objective_vector.results[:3])),
        "         " + " · ".join(f"F{j+4} {r.value:.2f}" for j, r in enumerate(ph.objective_vector.results[3:])),
        "Rank  " + " · ".join(f"F{j+1} {float(ranks.get(r.name, 0)):.2f}"
                               for j, r in enumerate(ph.objective_vector.results[:3])) if isinstance(ranks, dict) else "Rank  see archive",
        "         " + " · ".join(f"F{j+4} {float(ranks.get(r.name, 0)):.2f}"
                               for j, r in enumerate(ph.objective_vector.results[3:])) if isinstance(ranks, dict) else "",
    ]
    axdata.text(0, 1, "\n".join(left), va="top", size=7.3, color=INK,
                linespacing=1.28, family="monospace")
    axdata.text(.57, 1, "\n".join(right), va="top", size=7.3, color=INK,
                linespacing=1.28, family="monospace")
    fig.text(.04, .97, f"ARCHITECTURAL PHENOTYPE  /  {ph.genotype_id}", size=17,
             weight="bold", color=INK, va="top")
    fig.text(.04, .927, "Schematic research output. Program, site and geometry require architectural development.",
             size=8.5, color=INK)
    _save(fig, path, identity, ph.genotype_id)
