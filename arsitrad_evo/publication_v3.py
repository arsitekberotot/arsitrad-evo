"""Coordinated architectural phenotype sheets and evolutionary boards.

All drawings use the schematic 90 x 61.5 m model frame. The +Y arrow is a
diagram orientation only; actual parcel north, access and code dimensions
remain [TO VERIFY]. Objective bars show bounded proxies, not measured outcomes.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from matplotlib.patches import Polygon, Rectangle
import numpy as np

from .phenotype_gen import Prototype, OBJ_NAMES


BG = "#f7f5ef"
INK = "#223330"
MUTED = "#526861"
LINE = "#c9d0c8"
MODULE_COLOR = {
    "A0": "#3c8d8c", "B0": "#80658c", "C0": "#80a273",
    "R4": "#d1a15d", "E0": "#95769a", "F0": "#81918d",
    "M0": "#6f807e", "H0": "#6c9e7c", "I0": "#9ab892",
    "J0": "#bc8c69", "K0": "#6eaaa5", "L0": "#b1917c",
}
ROUTE_COLOR = {"resident": "#bb7727", "care_staff": "#80608c",
               "visitor_community": "#178a93", "service": "#5b6f70",
               "emergency": "#c34e45"}
PRIVACY_COLOR = {0: "#318c91", 1: "#80658c", 2: "#74a077",
                 3: "#c3893a", 4: "#b95650"}


def _style():
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                         "text.color": INK, "axes.labelcolor": INK,
                         "axes.edgecolor": LINE, "xtick.color": MUTED,
                         "ytick.color": MUTED, "savefig.facecolor": BG})


def _shade(color: str, amount: float):
    rgb = np.asarray(to_rgb(color))
    return tuple(np.clip(rgb * amount + (1-amount) * np.ones(3), 0, 1))


def draw_site_plan(ax, proto: Prototype, *, routes=True, exposure=True,
                   space=True, detail=False, compact=False):
    ax.set_facecolor("#eef0e7")
    ax.add_patch(Rectangle((0, 0), proto.site_w, proto.site_h,
                           facecolor="#edf1e9", edgecolor=INK, lw=1.1,
                           zorder=0))
    if space:
        markers = {"COURTYARD": ("o", "#4f9b6a"),
                   "POCKET COURT / THRESHOLD EDGE": ("D", "#b68b4e")}
        for zone in proto.open_spaces:
            if zone.space_type not in markers or zone.area_m2 < 12:
                continue
            marker, color = markers[zone.space_type]
            ax.plot(zone.cx, zone.cy, marker=marker,
                    ms=3.5 if compact else 5.0, color=color,
                    markerfacecolor="none", mew=1, zorder=2)
    if routes:
        for net in proto.route_networks:
            if compact and net["kind"] not in {"resident", "visitor_community"}:
                continue
            for route in net["routes"]:
                if len(route["points"]) < 2 or route["status"] == "CONTROLLED_INTERNAL":
                    continue
                pts = np.asarray(route["points"])
                ax.plot(pts[:, 0], pts[:, 1], color=ROUTE_COLOR[net["kind"]],
                        lw=0.8 if compact else 1.15, alpha=.55,
                        zorder=3, solid_capstyle="round")
    for m in proto.modules:
        x0, y0 = m.x-m.w/2, m.y-m.d/2
        ax.add_patch(Rectangle((x0, y0), m.w, m.d,
                               facecolor=MODULE_COLOR[m.code],
                               edgecolor=PRIVACY_COLOR[m.privacy],
                               lw=1.1 if compact else 1.7, zorder=5))
        if detail:
            for part in m.parts:
                if part.floor == 1:
                    ax.add_patch(Rectangle((part.x, part.y), part.w, part.d,
                                           facecolor="#fffdf7", edgecolor=INK,
                                           lw=.25, alpha=.36, zorder=6))
        label = f"R4.{sum(x.code == 'R4' and x.inst_id <= m.inst_id for x in proto.modules)}" \
            if m.code == "R4" and not compact else m.code
        ax.text(m.x, m.y, label, ha="center", va="center",
                fontsize=5.2 if compact else 7.0, fontweight="bold",
                color="#102521", zorder=7)
        if not compact:
            for role, point in m.access_points.items():
                if role in {"resident", "visitor_community", "service"}:
                    ax.plot(point[0], point[1], marker="o", ms=2.5,
                            color=ROUTE_COLOR[role], zorder=8)
    if exposure and not compact:
        shown = sorted((s for s in proto.sightlines if s.exposed),
                       key=lambda s: -s.exposure_ratio)[:5]
        for sl in shown:
            a, b = proto.modules[sl.from_id], proto.modules[sl.to_id]
            ax.plot([a.x, b.x], [a.y, b.y], color="#c34e45",
                    lw=.85, ls=(0, (2, 2)), alpha=.48, zorder=4)
    ax.set_xlim(-4, proto.site_w+5)
    ax.set_ylim(-5, proto.site_h+4)
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    if not compact:
        ax.annotate("+Y", xy=(proto.site_w+2, proto.site_h-2),
                    xytext=(proto.site_w+2, proto.site_h-12),
                    ha="center", fontsize=7,
                    arrowprops={"arrowstyle": "-|>", "lw": 1, "color": INK})
        ax.plot([4, 24], [-2.8, -2.8], color=INK, lw=1.5, zorder=10)
        ax.plot([4, 4], [-3.7, -1.9], color=INK, lw=1)
        ax.plot([24, 24], [-3.7, -1.9], color=INK, lw=1)
        ax.text(14, -1.2, "20 m model scale", ha="center", fontsize=6.5)


def _iso(x, y, z=0.0):
    return (0.866 * (x-y), 0.5 * (x+y) + z)


def draw_exploded_axon(ax, proto: Prototype, compact=False):
    site = [_iso(0, 0), _iso(proto.site_w, 0),
            _iso(proto.site_w, proto.site_h), _iso(0, proto.site_h)]
    ax.add_patch(Polygon(site, closed=True, facecolor="#e8eee5",
                         edgecolor=LINE, lw=.8, zorder=0))
    for m in sorted(proto.modules, key=lambda x: x.x+x.y):
        x0, x1 = m.x-m.w/2, m.x+m.w/2
        y0, y1 = m.y-m.d/2, m.y+m.d/2
        color = MODULE_COLOR[m.code]
        for floor in range(m.floors):
            z0, z1 = floor*7.2, floor*7.2+5.2
            sw, se, ne, nw = [(_iso(x, y, z0)) for x, y in
                              ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
            swt, set_, net, nwt = [(_iso(x, y, z1)) for x, y in
                                  ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
            ax.add_patch(Polygon([sw, se, set_, swt], closed=True,
                                 facecolor=_shade(color, .77), edgecolor=INK,
                                 lw=.35, zorder=2+floor))
            ax.add_patch(Polygon([se, ne, net, set_], closed=True,
                                 facecolor=_shade(color, .65), edgecolor=INK,
                                 lw=.35, zorder=2+floor))
            ax.add_patch(Polygon([swt, set_, net, nwt], closed=True,
                                 facecolor=color, edgecolor=INK, lw=.45,
                                 zorder=3+floor))
        if not compact:
            tx, ty = _iso(m.x, m.y, (m.floors-1)*7.2+5.7)
            ax.text(tx, ty, m.code, ha="center", va="center",
                    fontsize=6, weight="bold", zorder=9)
    ax.set_xlim(-proto.site_h*.9-3, proto.site_w*.9+3)
    ax.set_ylim(-3, (proto.site_w+proto.site_h)*.5+20)
    ax.set_aspect("equal")
    ax.axis("off")


def _radar(ax, proto: Prototype):
    values = [1-float(proto.objectives[name]) for name in OBJ_NAMES]
    angles = np.linspace(0, 2*np.pi, len(values), endpoint=False)
    ax.plot(np.r_[angles, angles[0]], np.r_[values, values[0]],
            color="#247d7e", lw=1.6)
    ax.fill(np.r_[angles, angles[0]], np.r_[values, values[0]],
            color="#247d7e", alpha=.16)
    ax.set_xticks(angles)
    ax.set_xticklabels([f"F{i}" for i in range(1, 10)], fontsize=6.5)
    ax.set_ylim(0, 1); ax.set_yticks([.5, 1]); ax.set_yticklabels([])
    ax.grid(color=LINE, lw=.5)
    ax.spines["polar"].set_color(LINE)


def _budget(ax, proto: Prototype):
    b = proto.site_budget
    items = [("building", b["building_footprint_m2"], "#526760"),
             ("landscape", b["landscape_target_m2"], "#7ba77c"),
             ("reserve", b["expansion_reserve_m2"], "#d4aa6c"),
             ("other open / access", b["other_open_and_access_m2"], "#d6ddd2")]
    offset = 0
    for label, value, color in items:
        ax.barh(0, value, left=offset, color=color, height=.5,
                edgecolor=BG, linewidth=1)
        if value > 300:
            ax.text(offset+value/2, 0, f"{label}\n{value:,.0f}",
                    ha="center", va="center", fontsize=7,
                    color="#162b26")
        offset += value
    ax.set_xlim(0, b["site_area_m2"]); ax.set_ylim(-.5, .5)
    ax.axis("off")


def _detail(ax, proto: Prototype):
    m = next((m for m in proto.modules if m.code == "R4"), proto.modules[0])
    ax.add_patch(Rectangle((m.x-m.w/2, m.y-m.d/2), m.w, m.d,
                           facecolor=MODULE_COLOR[m.code], edgecolor=INK))
    for part in m.parts:
        if part.floor != 1:
            continue
        ax.add_patch(Rectangle((part.x, part.y), part.w, part.d,
                               facecolor=_shade(PRIVACY_COLOR[part.privacy], .55),
                               edgecolor=BG, lw=.5))
        ax.text(part.x+part.w/2, part.y+part.d/2,
                part.name.replace("personal territory", "personal").replace(
                    "connection point", "entry"), ha="center", va="center",
                fontsize=6.2, wrap=True)
    ax.set_xlim(m.x-m.w/2-1, m.x+m.w/2+1)
    ax.set_ylim(m.y-m.d/2-1, m.y+m.d/2+1)
    ax.set_aspect("equal"); ax.axis("off")


def _upper_floor(ax, proto: Prototype):
    ax.set_facecolor("#eef0e7")
    ax.add_patch(Rectangle((0, 0), proto.site_w, proto.site_h,
                           facecolor="#edf1e9", edgecolor=INK, lw=.8))
    for m in proto.modules:
        x0, y0 = m.x-m.w/2, m.y-m.d/2
        if m.floors < 2:
            ax.add_patch(Rectangle((x0, y0), m.w, m.d, facecolor="none",
                                   edgecolor=LINE, lw=.5, ls="--"))
            continue
        ax.add_patch(Rectangle((x0, y0), m.w, m.d,
                               facecolor=MODULE_COLOR[m.code], edgecolor=INK,
                               lw=.8))
        for part in m.parts:
            if part.floor == 2:
                ax.add_patch(Rectangle((part.x, part.y), part.w, part.d,
                                       facecolor="#fffdf7", edgecolor=INK,
                                       lw=.3, alpha=.5))
        ax.text(m.x, m.y, m.code, ha="center", va="center",
                fontsize=7, weight="bold")
    ax.set_xlim(-3, proto.site_w+3); ax.set_ylim(-3, proto.site_h+3)
    ax.set_aspect("equal"); ax.axis("off")


def render_phenotype_sheet(proto: Prototype, path: Path):
    _style()
    fig = plt.figure(figsize=(16, 9), facecolor=BG)
    fig.text(.035, .955, f"{proto.candidate}  /  ARCHITECTURAL PHENOTYPE",
             fontsize=20, weight="bold", color=INK)
    fig.text(.035, .913,
             f"ID {proto.genotype_id}   ·   seed {proto.seed}   ·   selected Gen {proto.selected_generation} "
             f"·   born Gen {proto.birth_generation}   ·   {proto.program}",
             fontsize=10.5, color=MUTED)
    fig.add_artist(plt.Line2D([.035, .965], [.895, .895], color=INK, lw=1))

    ax_plan = fig.add_axes([.035, .315, .53, .53])
    draw_site_plan(ax_plan, proto, routes=True, exposure=True, detail=True)
    fig.text(.04, .86, "01  GROUND ORGANIZATION + ROUTED ACCESS", fontsize=10,
             weight="bold")
    fig.text(.04, .299, "Diagram +Y; real north / street frontage [TO VERIFY]",
             fontsize=7.5, color=MUTED)
    fig.text(.04, .28,
             "Fill: A0 civic · B0/E0 care · C0 commons · R4 domestic · F0/M0 service  "
             "|  ○ court · ◇ pocket edge",
             fontsize=6.9, color=MUTED)
    fig.text(.04, .264,
             "Privacy outline: teal public · plum controlled · green shared · "
             "ochre domestic · red personal",
             fontsize=6.9, color=MUTED)
    fig.text(.04, .248,
             "Routes: resident ochre · care plum · visitor teal · service slate · "
             "emergency red  |  red dashed: sampled sightline exposure",
             fontsize=6.9, color=MUTED)

    ax_axon = fig.add_axes([.59, .51, .255, .345])
    draw_exploded_axon(ax_axon, proto)
    fig.text(.59, .86, "02  EXPLODED FLOOR ASSEMBLY", fontsize=10, weight="bold")
    fig.text(.59, .505, "Height is diagrammatic; stacked C0/H0 only where present.",
             fontsize=7.3, color=MUTED)

    fig.text(.865, .86, "03  PROGRAM + STATUS", fontsize=10, weight="bold")
    metrics = [("RESIDENTS", str(proto.residents)),
               ("DAY USERS", str(proto.day_users)),
               ("AREA PROXY", f"{proto.gfa:,.0f} m²"),
               ("FOOTPRINT", f"{proto.footprint:,.0f} m²"),
               ("LANDSCAPE", f"{proto.landscape_frac*100:.1f}%"),
               ("MUST DEFICIT", f"{proto.must_shortfall:.1f} m")]
    for i, (name, value) in enumerate(metrics):
        y = .822 - i*.055
        fig.text(.865, y, name, fontsize=7, color=MUTED)
        fig.text(.865, y-.025, value, fontsize=12, weight="bold")
    fig.text(.865, .46, proto.constraint_status, fontsize=8.5,
             color="#21725d", weight="bold")
    fig.text(.865, .435, proto.exposure_status, fontsize=7.5,
             color="#a33e3c" if proto.exposure_status.startswith("EXPOSED") else MUTED)

    fig.text(.59, .462, "04  PERFORMANCE / TRADE-OFF", fontsize=10, weight="bold")
    ax_radar = fig.add_axes([.62, .24, .18, .205], projection="polar")
    _radar(ax_radar, proto)
    fig.text(.60, .203, "1 − objective (outer = better); all F1–F9 are model proxies",
             fontsize=7.3, color=MUTED)
    exposed = [s for s in proto.sightlines if s.exposed]
    fig.text(.815, .38, "SIGHTLINE REVIEW", fontsize=8, weight="bold")
    fig.text(.815, .35, f"{len(exposed)} / {len(proto.sightlines)} sensitive pairs\n"
             "show sampled exposure.", fontsize=8, linespacing=1.5)
    if exposed:
        pairs = ", ".join(f"{s.from_code}–{s.to_code}"
                          for s in exposed[:3])
        fig.text(.815, .29, f"e.g. {pairs}", fontsize=7.4, color="#a33e3c")

    fig.text(.04, .228, "05  DOMESTIC KIT / PRIVATE TERRITORY", fontsize=9,
             weight="bold")
    ax_detail = fig.add_axes([.04, .075, .24, .14])
    _detail(ax_detail, proto)
    fig.text(.30, .228, "06  UPPER FLOOR", fontsize=9, weight="bold")
    ax_upper = fig.add_axes([.30, .075, .23, .14])
    upper = [m for m in proto.modules if m.floors > 1]
    if upper:
        _upper_floor(ax_upper, proto)
    else:
        ax_upper.text(.5, .5, "Single storey\nthroughout", ha="center",
                      va="center", transform=ax_upper.transAxes,
                      fontsize=11, color=MUTED)
        ax_upper.axis("off")

    fig.text(.59, .175, "07  SITE AREA BUDGET  /  5,533.85 m² [PA5 CORPUS]",
             fontsize=9, weight="bold")
    ax_budget = fig.add_axes([.59, .105, .37, .055])
    _budget(ax_budget, proto)
    modules = Counter(m.code for m in proto.modules)
    fig.text(.59, .092,
             f"Reserve {proto.site_budget['expansion_reserve_m2']:,.0f} m²  ·  Modules  "
             + "  ".join(f"{code}×{count}" for code, count in modules.items()),
             fontsize=7.6, color=MUTED)
    spaces = Counter(s.space_type for s in proto.open_spaces
                     if s.area_m2 >= 12)
    fig.text(.59, .071,
             "Diagrammed open zones: "
             f"{spaces['COURTYARD']} courtyard · "
             f"{spaces['POCKET COURT / THRESHOLD EDGE']} pocket edges · "
             f"{spaces['OPEN LANDSCAPE']} open landscape  |  "
             "threshold A0 → C0 → R4",
             fontsize=7.0, color=MUTED)
    fig.add_artist(plt.Line2D([.035, .965], [.055, .055], color=LINE, lw=.8))
    fig.text(.035, .027,
             "[PA5 CORPUS] program / capacities   ·   [DESIGN HYPOTHESIS] kit, routes, enclosure, massing   ·   "
             "[TO VERIFY] sightlines, parcel, access, egress, all dimensions. Schematic, not code-compliant design.",
             fontsize=7, color=MUTED)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def _mini(fig, proto: Prototype, box, title: str, note: str,
          show_profile=True):
    x, y, w, h = box
    fig.text(x, y+h-.016, title, fontsize=10, weight="bold")
    ax = fig.add_axes([x, y+.038, w*.63, h-.073])
    draw_site_plan(ax, proto, routes=False, exposure=False, space=False,
                   compact=True)
    fig.text(x+w*.65, y+h-.055,
             f"{proto.residents} residents\n{proto.gfa:,.0f} m² area proxy\n"
             f"{proto.landscape_frac*100:.0f}% landscape\n"
             f"{proto.constraint_status}", fontsize=8, linespacing=1.6)
    fig.text(x+w*.65, y+.105, note, fontsize=7.3, color=MUTED,
             wrap=True)
    if show_profile:
        axp = fig.add_axes([x+w*.65, y+.055, w*.32, .042])
        vals = [1-proto.objectives[n] for n in OBJ_NAMES]
        axp.plot(range(1, 10), vals, color="#247d7e", lw=1.3, marker="o",
                 markersize=2)
        axp.set_ylim(0, 1); axp.set_xlim(1, 9)
        axp.set_xticks([1, 3, 5, 7, 9]); axp.set_xticklabels(
            ["F1", "F3", "F5", "F7", "F9"], fontsize=6)
        axp.set_yticks([]); axp.spines[["top", "right", "left"]].set_visible(False)
    fig.text(x, y+.006,
             f"ID {proto.genotype_id}  ·  seed {proto.seed}  ·  Gen {proto.selected_generation} "
             f"(born {proto.birth_generation})", fontsize=7.1, color=MUTED)


def _board_frame(title: str, subtitle: str, figsize=(16, 9)):
    _style()
    fig = plt.figure(figsize=figsize, facecolor=BG)
    fig.text(.035, .955, title, fontsize=20, weight="bold")
    fig.text(.035, .914, subtitle, fontsize=9.5, color=MUTED)
    fig.add_artist(plt.Line2D([.035, .965], [.89, .89], color=INK, lw=1))
    return fig


def _board_footer(fig):
    keys = ((.035, "A0 civic", "A0"), (.145, "B0/E0 care", "B0"),
            (.285, "C0 commons", "C0"), (.425, "R4 domestic", "R4"),
            (.570, "F0/M0 service", "F0"))
    for x, label, code in keys:
        fig.add_artist(Rectangle((x, .073), .008, .012,
                                 transform=fig.transFigure,
                                 facecolor=MODULE_COLOR[code], edgecolor=INK,
                                 lw=.3, clip_on=False))
        fig.text(x+.012, .071, label, fontsize=7, color=MUTED)
    fig.text(.745, .071, "○ court  ·  ◇ pocket  ·  ochre resident route",
             fontsize=7, color=MUTED)
    fig.add_artist(plt.Line2D([.035, .965], [.055, .055], color=LINE, lw=.8))
    fig.text(.035, .025,
             "Consistent 90 × 61.5 m schematic frame  ·  +Y diagram orientation; real north [TO VERIFY]  "
             "·  F1–F9 are model proxies (higher mini profile = better)  ·  all sizes [DESIGN HYPOTHESIS]",
             fontsize=7.5, color=MUTED)


def render_population_board(generation: int, entries: list[tuple[str, Prototype]],
                            path: Path):
    fig = _board_frame(
        f"GEN {generation:02d}  /  POPULATION PHENOTYPES",
        "Four sampled layouts across the free, 12-resident and 16-resident searches. "
        "Model-infeasible early layouts are shown diagnostically with status.")
    boxes = [(.04, .49, .44, .37), (.52, .49, .44, .37),
             (.04, .095, .44, .37), (.52, .095, .44, .37)]
    for box, (lane, proto) in zip(boxes, entries):
        _mini(fig, proto, box,
              f"{lane}  /  {proto.program}",
              f"MUST {proto.must_shortfall:.1f} m\n{proto.exposure_status}")
    _board_footer(fig)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=190)
    plt.close(fig)
    return path


def render_rotation_study(base: Prototype, rotated: Prototype, path: Path):
    """Show an explicit post-optimization physical rotation variant [DH]."""
    fig = _board_frame(
        "PHYSICAL ROTATION  /  ARCHITECTURAL VARIANT",
        "A 90° module turn after optimization. The parent genotype is unchanged; "
        "constraints, routed access, objectives and sampled sightlines are recalculated.")
    for x, label, proto in ((.045, "ARCHIVED PARENT", base),
                            (.525, "ROTATED STUDY", rotated)):
        fig.text(x, .842, label, fontsize=12, weight="bold")
        ax = fig.add_axes([x, .20, .43, .61])
        draw_site_plan(ax, proto, routes=True, exposure=True, space=True,
                       detail=True)
        exposed = sum(s.exposed for s in proto.sightlines)
        fig.text(x, .156,
                 f"{proto.constraint_status}  ·  {proto.architectural_status}  "
                 f"·  {exposed}/{len(proto.sightlines)} exposed pairs",
                 fontsize=8.5)
        fig.text(x, .126,
                 f"Parent ID {proto.genotype_id}  ·  "
                 f"variant {proto.architectural_variant_id or 'none'}  ·  "
                 f"turns {proto.physical_rotations or 'none'}",
                 fontsize=8, color=MUTED)
    _board_footer(fig)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=190)
    plt.close(fig)
    return path


def render_selection_board(entries: list[tuple[str, Prototype, str]],
                           path: Path,
                           title="SELECTION  /  THREE ARCHITECTURAL STARTING POINTS",
                           subtitle="BALANCED minimax  ·  SPECIALIZED F3 in a distinct capacity  ·  "
                                    "CONTRASTING maximum relative difference. Exact archived genotypes."):
    fig = _board_frame(title, subtitle)
    boxes = [(.04, .12, .29, .72), (.355, .12, .29, .72),
             (.67, .12, .29, .72)]
    for box, (label, proto, rationale) in zip(boxes, entries):
        x, y, w, h = box
        fig.text(x, y+h-.02, label, fontsize=14, weight="bold")
        ax = fig.add_axes([x, y+.29, w, .43])
        draw_site_plan(ax, proto, routes=True, exposure=False, space=True,
                       compact=True)
        fig.text(x, y+.235,
                 f"{proto.residents} residents · {proto.day_users} day users · "
                 f"{proto.gfa:,.0f} m² area proxy · {proto.landscape_frac*100:.1f}% landscape",
                 fontsize=8)
        fig.text(x, y+.19, rationale, fontsize=8, color=MUTED, wrap=True)
        axp = fig.add_axes([x+.01, y+.065, w-.02, .085])
        values = [1-proto.objectives[n] for n in OBJ_NAMES]
        axp.plot(range(1, 10), values, color="#247d7e", lw=1.5,
                 marker="o", markersize=3)
        axp.set_ylim(0, 1); axp.set_xlim(1, 9)
        axp.set_xticks(range(1, 10)); axp.set_xticklabels(
            [f"F{i}" for i in range(1, 10)], fontsize=7)
        axp.set_yticks([0, .5, 1]); axp.tick_params(labelsize=7)
        axp.grid(axis="y", alpha=.2)
        axp.spines[["top", "right"]].set_visible(False)
        fig.text(x, y+.02,
                 f"{proto.genotype_id} · seed {proto.seed} · Gen {proto.selected_generation} "
                 f"· {proto.constraint_status} · {sum(s.exposed for s in proto.sightlines)} exposed pairs",
                 fontsize=7.1, color=MUTED)
    _board_footer(fig)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=190)
    plt.close(fig)
    return path


def render_objective_extremes(entries: list[tuple[str, Prototype]], path: Path):
    fig = _board_frame("OBJECTIVE EXTREMES  /  PARETO SELECTION",
                       "Best archive phenotype for each F1–F9 objective. A phenotype can appear more than once; "
                       "these are objective extremes, not nine independent types.")
    for index, (label, proto) in enumerate(entries):
        col, row = index % 3, index // 3
        x, y = .04+col*.315, .63-row*.265
        _mini(fig, proto, (x, y, .29, .24), label,
              f"{label} = {proto.objectives[OBJ_NAMES[index]]:.3f}",
              show_profile=False)
    _board_footer(fig)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=190)
    plt.close(fig)
    return path


def render_pareto_board(rows: list[tuple], shortlist: list[tuple[str, Prototype, str]],
                        path: Path):
    fig = _board_frame("PARETO FIELD  /  SPATIAL TRADE-OFF",
                       "F5 site efficiency versus F8 community connection; lower is better. "
                       "Capacity strata retain valid 8, 12 and 16 resident propositions.")
    ax = fig.add_axes([.08, .18, .51, .62])
    colors = {2: "#528e7c", 3: "#c58d50", 4: "#80658c"}
    for n in (2, 3, 4):
        pts = [p for _, p in rows if p.n_R4 == n]
        if pts:
            ax.scatter([p.objectives[4] for p in pts],
                       [p.objectives[7] for p in pts], s=14,
                       c=colors[n], alpha=.45, label=f"R4×{n} / {n*4} residents")
    for label, proto, _ in shortlist:
        ax.scatter(proto.objectives[OBJ_NAMES[4]],
                   proto.objectives[OBJ_NAMES[7]], s=120,
                   marker="*", color=INK, zorder=8)
        ax.annotate(label[0],
                    (proto.objectives[OBJ_NAMES[4]],
                     proto.objectives[OBJ_NAMES[7]]),
                    xytext=(5, 7), textcoords="offset points", fontsize=11,
                    weight="bold")
    ax.set_xlabel("F5  site efficiency proxy ↓")
    ax.set_ylabel("F8  community connection proxy ↓")
    ax.grid(alpha=.18); ax.legend(frameon=False, fontsize=8)
    fig.text(.64, .80, "HOW TO READ THIS FRONT", fontsize=11, weight="bold")
    fig.text(.64, .765,
             "Each point is a model-feasible, MUST-linked layout.\n"
             "Colors show resident capacity, not K-means types.\n"
             "Stars locate the three selected architectural studies.",
             fontsize=10, linespacing=1.7, va="top")
    fig.text(.64, .56, "SELECTION CHAIN", fontsize=11, weight="bold")
    fig.text(.64, .525,
             "Generation → genotype → program assembly\n"
             "→ routed spatial organization → phenotype\n"
             "→ F1–F9 trade-offs → shortlist",
             fontsize=10, linespacing=1.7, va="top")
    fig.text(.64, .30,
             "K-means remains a diagnostic only when the silhouette\n"
             "does not support discrete architectural families.",
             fontsize=9, color=MUTED, linespacing=1.6, va="top")
    _board_footer(fig)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=190)
    plt.close(fig)
    return path
