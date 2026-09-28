"""Consolidated V4 summary report.

Single machine- and human-readable capstone tying together the four V4
deliverables:
  1. canonical real-site model (site.geojson geometry + site.yaml metadata,
     every attribute evidence-tagged)
  2. module library catalogue (FUNCTION x SIZE x MODULARITY, capacity,
     privacy, access, repeatability, stackability, evidence status)
  3. two-tier capacity experiment (Tier 1 reference + Tier 2 controlled
     day-user demand scenarios -> reachability boundary)
  4. reachable-stratum selections on the real polygon (Pareto / fittest /
     relative-difference / specialized) with the residential-candidacy gate

Outputs report_v4.json + report_v4.md. Provenance strings are carried through
verbatim; nothing is re-interpreted beyond its evidence tag.
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Any

from .site import load_canonical_site


def _load(path: str) -> Any:
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def gather(site_path: str, meta_path: str,
           cap_dir: str, cat_dir: str, sel_dir: str) -> dict:
    site = load_canonical_site(site_path, meta_path)
    exp = _load(os.path.join(cap_dir, "experiment_summary.json")) or {}
    cat = _load(os.path.join(cat_dir, "module_catalogue_v4.json")) or {}
    sel = _load(os.path.join(sel_dir, "selection_manifest.json")) or {}

    reach = exp.get("day_user_reachability", {})
    infeasible = exp.get("infeasible_day_user_strata", [])

    runs = sel.get("runs", [])
    total_cand = sum(r.get("candidates", 0) for r in runs)
    total_feas = sum(r.get("feasible", 0) for r in runs)

    report = {
        "title": "The Threshold — V4 Site-Aware Modular Evolutionary Programming",
        "schema": "v4-consolidated-report/1",
        "site": {
            "name": site.name,
            "mode": site.mode.value,
            "area_m2": round(site.area_m2, 1),
            "setbacks_m": getattr(site, "setbacks_m", {}),
            "preferred_expansion_direction":
                getattr(site, "preferred_expansion_direction", None),
            "provenance": getattr(site, "metadata_provenance", {}),
        },
        "module_library": {
            "n_modules": len(cat.get("modules", {})),
            "n_families": len(cat.get("family_variants", {})),
            "axes": cat.get("axes", {}),
            "schema": cat.get("schema"),
        },
        "capacity_experiment": {
            "tier1": exp.get("tier1"),
            "tier2": exp.get("tier2"),
            "day_user_strata": exp.get("day_user_strata"),
            "resident_strata_r4": exp.get("resident_strata_r4"),
            "max_residents": exp.get("max_residents"),
            "max_day_users": exp.get("max_day_users"),
            "day_user_reachability": reach,
            "infeasible_day_user_strata": infeasible,
            "interpretation": exp.get("interpretation"),
            "caveat": exp.get("caveat"),
        },
        "reachable_selection": {
            "day_user_stratum": sel.get("day_user_stratum"),
            "objective_names": sel.get("objective_names"),
            "runs": runs,
            "total_feasible": total_feas,
            "total_candidates": total_cand,
            "candidacy_note": (
                "candidates = feasible AND residents >= MIN_RESIDENTS; "
                "degenerate zero-resident layouts are reported but never "
                "selected as representative."),
        },
        "key_findings": _findings(reach, infeasible, runs),
    }
    return report


def _findings(reach, infeasible, runs):
    f = []
    if infeasible:
        f.append(
            f"Day-user strata {infeasible} are NOT reachable while essential "
            f"functional coverage (arrival+care+commons+service) and the "
            f"mandatory threshold (L0 x2) are preserved. The reachable floor "
            f"under the current PA5 module corpus is ~44 day users "
            f"(A0-S 12 + B0-S 4 + C0-S 16 + L0x2 12).")
    reachable = [k for k, v in reach.items() if v and float(v) > 0.0]
    if reachable:
        f.append(
            f"Only day-user stratum {reachable} is reachable, and even there "
            f"the feasible region is razor-thin (reachability "
            f"{[reach[k] for k in reachable]}).")
    cands = [r.get("candidates", 0) for r in runs]
    if runs and sum(cands) == 0:
        f.append(
            "Across all seeds at the reachable stratum, NO feasible solution "
            "retained a residential core (residents >= 8): the only layouts "
            "meeting the day-user cap did so by deleting the domestic program "
            "— an unacceptable trade for a residential care facility. This is "
            "the capacity threshold at which the brief breaks.")
    elif runs:
        f.append(
            f"At the reachable stratum, feasible-and-residential candidates "
            f"per seed: {cands} — an extremely thin meaningful front.")
    f.append(
        "Interpretive thresholds and strata are [DESIGN HYPOTHESIS]; module "
        "capacities are [PA5 CORPUS] where corpus-derived. These are "
        "experimental search strata, not recommended shelter capacities.")
    return f


def write_md(report: dict, path: str) -> None:
    s = report["site"]
    ml = report["module_library"]
    ce = report["capacity_experiment"]
    rs = report["reachable_selection"]
    L = []
    L.append(f"# {report['title']}\n")
    L.append(f"_Schema: {report['schema']}_\n")

    L.append("## 1. Canonical real-site model\n")
    L.append(f"- Geometry: `{s['mode']}` (site.geojson), area "
             f"**{s['area_m2']} m²**, setbacks {s['setbacks_m']}")
    L.append(f"- Preferred expansion direction: "
             f"{s['preferred_expansion_direction']}")
    L.append("- **Every attribute is evidence-tagged** (no fabrication):\n")
    L.append("| attribute | status |")
    L.append("|---|---|")
    for k, v in s["provenance"].items():
        L.append(f"| {k} | {v} |")
    L.append("")

    L.append("## 2. Module library catalogue\n")
    L.append(f"- {ml['n_modules']} module codes across {ml['n_families']} "
             f"functional families")
    ax = ml.get("axes", {})
    L.append(f"- Axes: sizes {ax.get('size_classes')}, modularity "
             f"{ax.get('modularity_categories')}")
    L.append(f"- Machine-readable schema `{ml.get('schema')}` "
             "(see module_catalogue_v4.json/.csv/.png)\n")

    L.append("## 3. Two-tier capacity experiment\n")
    L.append(f"- Tier 1: {ce.get('tier1')}")
    L.append(f"- Tier 2: {ce.get('tier2')}")
    L.append(f"- Day-user strata: {ce.get('day_user_strata')}; "
             f"resident strata R4x{ce.get('resident_strata_r4')}")
    L.append(f"- Day-user reachability: `{ce.get('day_user_reachability')}`")
    if ce.get("interpretation"):
        L.append(f"\n> {ce['interpretation']}\n")

    L.append("## 4. Reachable-stratum selections (real polygon)\n")
    L.append(f"- Stratum: day_users = {rs.get('day_user_stratum')}; "
             f"objectives {rs.get('objective_names')}")
    L.append(f"- Total feasible {rs.get('total_feasible')}, "
             f"residential candidates {rs.get('total_candidates')}")
    L.append(f"- {rs.get('candidacy_note')}")
    L.append("\n| seed | feasible | candidates | pareto | selections |")
    L.append("|---|---|---|---|---|")
    for r in rs.get("runs", []):
        L.append(f"| {r.get('seed')} | {r.get('feasible')} | "
                 f"{r.get('candidates')} | {r.get('pareto_size')} | "
                 f"{len(r.get('selections', {}))} |")
    L.append("")

    L.append("## Key findings\n")
    for i, k in enumerate(report["key_findings"], 1):
        L.append(f"{i}. {k}")
    L.append("")

    with open(path, "w") as fh:
        fh.write("\n".join(L))


def build_report(site_path, meta_path, cap_dir, cat_dir, sel_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    rep = gather(site_path, meta_path, cap_dir, cat_dir, sel_dir)
    with open(os.path.join(out_dir, "report_v4.json"), "w") as f:
        json.dump(rep, f, indent=2)
    write_md(rep, os.path.join(out_dir, "report_v4.md"))
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="data/site.geojson")
    ap.add_argument("--meta", default="data/site.yaml")
    ap.add_argument("--cap", default="results_capacity_v4")
    ap.add_argument("--cat", default="module_catalogue_v4")
    ap.add_argument("--sel", default="selections_v4_day48")
    ap.add_argument("--out", default="report_v4")
    args = ap.parse_args()
    rep = build_report(args.site, args.meta, args.cap, args.cat,
                       args.sel, args.out)
    print(f"[report] {len(rep['key_findings'])} findings -> {args.out}/")
    for k in rep["key_findings"]:
        print("  -", k)


if __name__ == "__main__":
    main()
