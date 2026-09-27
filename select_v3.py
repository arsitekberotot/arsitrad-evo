"""Freeze a validated v3 archive and select three exact architectural genotypes.

The selection is editorial but reproducible: minimize sampled exposure within
each capacity among solutions without an extreme objective penalty, then choose
balanced minimax, an F3 specialist, and a maximin contrast.
Every candidate is replayed from its complete archived vector before any sheet
is produced. Exposed sampled sightlines remain visible design review items.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from arsitrad_evo import analyze, config as C
from arsitrad_evo.constraints import c_site_boundary
from arsitrad_evo.genotype import N_GENES
from arsitrad_evo.nsga2 import evaluate
from arsitrad_evo.objectives import OBJECTIVES
from arsitrad_evo.phenotype_gen import (
    build_prototype, _check_sightlines, CORPUS, HYP, VERIFY,
)


ROOT = Path(__file__).resolve().parent
# Editorial screening of normalized model proxies, not a regulatory criterion.
# A value of 1 is the weakest proxy outcome; retain candidates below 0.75 on
# every objective before comparing their sampled visual exposure. [DESIGN HYPOTHESIS]
MAX_OBJECTIVE_FOR_SHORTLIST = 0.75
FROZEN_FILES = [
    "data/pareto_archive.csv", "data/pareto_genotypes.jsonl",
    "data/multiseed_summary.csv", "data/histories.json",
    "data/campaign_summary.json",
]
SOURCE_FILES = [
    "requirements-lock.txt", "arsitrad_evo/config.py",
    "arsitrad_evo/genotype.py", "arsitrad_evo/modules.py",
    "arsitrad_evo/constraints.py", "arsitrad_evo/objectives.py",
    "arsitrad_evo/nsga2.py", "arsitrad_evo/clustering.py",
    "run_campaign.py",
]


def fingerprint(campaign: Path) -> dict:
    paths = [campaign / name for name in FROZEN_FILES]
    paths += sorted((campaign / "data").glob("phenotype_*.json"))
    paths += [ROOT / name for name in SOURCE_FILES]
    hashes = {}
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        key = str(path.relative_to(campaign if campaign in path.parents else ROOT))
        hashes[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    payload = json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()
    return {"sha256": hashlib.sha256(payload).hexdigest(), "files": hashes}


def replay(row: dict):
    vector = row.get("genotype_vector")
    if not isinstance(vector, list) or len(vector) != N_GENES:
        raise ValueError("missing or wrong-length full genotype vector")
    if row.get("seed") is None or row.get("birth_generation") is None:
        raise ValueError("missing evolutionary seed or birth generation")
    if row.get("selected_generation") is None:
        raise ValueError("missing selected generation")
    ph = evaluate(np.asarray(vector, dtype=float), row["seed"],
                  row["birth_generation"])
    if analyze.genotype_id(ph) != row.get("genotype_id"):
        raise ValueError("genotype fingerprint differs on replay")
    if not ph.feasible or ph.cv > 1e-6 or ph.must_shortfall > 1e-6:
        raise ValueError("candidate fails hard constraints on replay")
    if c_site_boundary(ph) > 1e-6:
        raise ValueError("candidate overhangs schematic site")
    if ph.n_R4 != int(round(vector[0])):
        raise ValueError("capacity differs from vector")
    genes = analyze.genes_dict(ph)
    if not genes.get("has_H0") and "floors_H0" in genes:
        raise ValueError("dormant H0 floor gene appears in description")
    return ph


def architectural_gate(ph, selected_generation: int):
    proto = build_prototype(ph, selected_generation=selected_generation)
    reasons = []
    if proto.constraint_status != "MODEL_FEASIBLE":
        reasons.append("model constraints unresolved")
    if proto.architectural_status == "ROUTE_UNRESOLVED":
        reasons.append("routed circulation or threshold unresolved")
    if proto.site_budget["other_open_and_access_m2"] < 0:
        reasons.append("site area budget overdrawn")
    if proto.exposure_status == "UNASSESSED":
        reasons.append("sightline exposure unassessed")
    if not proto.floor_plans or not proto.threshold_paths:
        reasons.append("floor or threshold model missing")
    if any(p.provenance not in (CORPUS, HYP, VERIFY)
           for m in proto.modules for p in m.parts):
        reasons.append("internal part lacks evidence tag")
    return proto, reasons


def _baseline_evidence() -> list[dict]:
    old = ROOT / "campaign_v2" / "data" / "shortlist_v2.json"
    manifest = ROOT / "campaign_v2" / "phenotypes" / "manifest.json"
    if not old.is_file():
        return []
    old_rows = json.loads(old.read_text(encoding="utf-8"))
    rendered = {r["candidate"].split("_", 1)[-1]: r for r in
                json.loads(manifest.read_text(encoding="utf-8"))} if manifest.is_file() else {}
    out = []
    for row in old_rows:
        overhang = sum(m["x"]-m["w"]/2 < 0 or m["x"]+m["w"]/2 > C.SITE_W
                       or m["y"]-m["d"]/2 < 0 or m["y"]+m["d"]/2 > C.SITE_H
                       for m in row["modules"])
        r = rendered.get(row["label"])
        out.append({"candidate": row["label"], "site_overhang_modules": overhang,
                    "saved_gfa_m2": row["gfa"],
                    "rendered_gfa_m2": r["gfa"] if r else None,
                    "must_shortfall_m": row["must_soft_cv"]})
    return out


def _pick(rows, selected, sort_key):
    for row, ph, _ in sorted(rows, key=sort_key):
        if any(ph.n_R4 == old_ph.n_R4 for _, old_ph, _ in selected):
            continue
        proto, reasons = architectural_gate(ph, row["selected_generation"])
        if not reasons:
            return row, ph, proto
    raise RuntimeError("no candidate in the required capacity stratum passed the gate")


def _screened_pool(rows):
    """Preserve the lowest exposure available at each capacity after quality screening.

    Exposure is a sampled diagrammatic check and still needs architectural
    verification. This pool avoids silently favouring objective scores that
    leave readily avoidable public-to-domestic views open.
    """
    eligible = [(row, ph,
                 (sum(s.exposed for s in checks),
                  sum(s.visible_rays for s in checks)))
                for row, ph in rows
                for checks in [_check_sightlines(ph.instances)]
                if float(np.max(ph.objectives)) <= MAX_OBJECTIVE_FOR_SHORTLIST]
    if not eligible:
        raise RuntimeError("no archive entries pass the shortlist objective screen")
    floors = {capacity: min(exposure for _, ph, exposure in eligible
                            if ph.n_R4 == capacity)
              for capacity in {ph.n_R4 for _, ph, _ in eligible}}
    return [item for item in eligible if item[2] == floors[item[1].n_R4]], floors


def select(campaign: Path) -> dict:
    summary = json.loads((campaign / "data" / "campaign_summary.json").read_text())
    if not summary.get("capacity_strata"):
        raise ValueError("shortlist requires the capacity-stratified v3 campaign")
    freeze = fingerprint(campaign)
    rows = []
    seen = set()
    with (campaign / "data" / "pareto_archive.csv").open(newline="", encoding="utf-8") as fh:
        table = list(csv.DictReader(fh))
    total = 0
    with (campaign / "data" / "pareto_genotypes.jsonl").open(encoding="utf-8") as fh:
        for index, line in enumerate(fh):
            total += 1
            row = json.loads(line)
            ph = replay(row)
            if index >= len(table) or table[index]["genotype_id"] != row["genotype_id"]:
                raise ValueError(f"archive CSV / full vector mismatch at {index}")
            if any(abs(float(table[index][f"obj_{name}"]) - float(value)) > 0.000051
                   for (name, _), value in zip(OBJECTIVES, ph.objectives)):
                raise ValueError(f"archived objective mismatch at {index}")
            if row["genotype_id"] in seen:
                continue
            seen.add(row["genotype_id"])
            row["archive_index"] = index
            rows.append((row, ph))
    if len(table) != total:
        raise ValueError("archive CSV and full vector row counts differ")
    capacities = Counter(ph.n_R4 for _, ph in rows)
    if len(capacities) < 3:
        raise RuntimeError(f"archive lacks capacity diversity: {dict(capacities)}")
    screened, exposure_floors = _screened_pool(rows)
    if len(exposure_floors) < 3:
        raise RuntimeError("screened pool lacks capacity diversity")
    # Objective values are already bounded to [0, 1]; lower is better.
    balanced = _pick(screened, [], lambda item: (
        float(np.max(item[1].objectives)),
        float(np.mean(item[1].objectives)), item[0]["genotype_id"]))
    b_ph = balanced[1]
    remaining_capacities = sorted(set(capacities) - {b_ph.n_R4})
    specialist_capacity = remaining_capacities[0]
    specialist = _pick([item for item in screened if item[1].n_R4 == specialist_capacity],
                       [balanced], lambda item: (
                           float(item[1].objectives[2]),
                           float(np.max(item[1].objectives)),
                           item[0]["genotype_id"]))
    contrast_capacity = remaining_capacities[-1]
    contrast = _pick([item for item in screened if item[1].n_R4 == contrast_capacity],
                     [balanced, specialist], lambda item: (
                         -min(float(np.linalg.norm(item[1].objectives - b_ph.objectives)),
                              float(np.linalg.norm(item[1].objectives -
                                                   specialist[1].objectives))),
                         item[0]["genotype_id"]))
    labels = ["BALANCED", "SPECIALIZED", "CONTRASTING"]
    rationales = [
        "lowest worst objective among minimum-exposure screened phenotypes",
        f"lowest F3 among minimum-exposure R4x{specialist_capacity} phenotypes",
        f"largest objective-space distance from A/B among minimum-exposure R4x{contrast_capacity}",
    ]
    chosen = []
    for label, rationale, (row, ph, proto) in zip(
            labels, rationales, (balanced, specialist, contrast)):
        trace = analyze.traceability_record(
            ph, role=f"v3_{label.lower()}",
            selected_generation=row["selected_generation"])
        chosen.append({"label": label, "selection_rationale": rationale,
                       "archive_index": row["archive_index"],
                       "trace": trace,
                       "architectural_status": proto.architectural_status,
                       "exposure_status": proto.exposure_status,
                       "exposed_sensitive_pairs": sum(s.exposed for s in proto.sightlines),
                       "sensitive_pair_count": len(proto.sightlines),
                       "route_counts": {n["kind"]: len(n["routes"])
                                        for n in proto.route_networks},
                       "unresolved_routes": sum(len(n["unresolved"])
                                                for n in proto.route_networks)})
    gate = {
        "baseline_v2": _baseline_evidence(),
        "v3_archive_size": len(rows),
        "v3_capacity_distribution": dict(sorted(capacities.items())),
        "v3_model_feasible": len(rows),
        "v3_all_must_satisfied": len(rows),
        "v3_all_site_contained": len(rows),
        "shortlist_screen": {
            "max_single_normalized_objective": MAX_OBJECTIVE_FOR_SHORTLIST,
            "minimum_sampled_exposure_by_R4": {
                capacity: {"pairs": exposure[0], "visible_rays": exposure[1]}
                for capacity, exposure in exposure_floors.items()},
            "provenance": HYP,
        },
        "tests_at_freeze": "run pytest separately; see VALIDATION_GATE_v3.md",
        "cluster_silhouette": summary["cluster"]["silhouette"],
        "cluster_for_typology": ("NOT DEFENSIBLE" if summary["cluster"]["silhouette"] < 0.25
                                 else "EXPLORATORY"),
        "shortlist_ids": [x["trace"]["genotype_id"] for x in chosen],
        "review_status": "sightlines sampled; exposed pairs are explicit TO VERIFY items",
    }
    (campaign / "data" / "freeze_manifest_v3.json").write_text(
        json.dumps(freeze, indent=2), encoding="utf-8")
    (campaign / "data" / "shortlist_v3.json").write_text(
        json.dumps(chosen, indent=2), encoding="utf-8")
    (campaign / "data" / "validation_gate_v3.json").write_text(
        json.dumps(gate, indent=2), encoding="utf-8")
    return gate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", default="campaign_v3_full")
    args = parser.parse_args()
    gate = select((ROOT / args.campaign).resolve())
    print(json.dumps(gate, indent=2))


if __name__ == "__main__":
    main()
