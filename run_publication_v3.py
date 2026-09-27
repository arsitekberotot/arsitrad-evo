"""Render the coordinated v3 architectural publication package.

Level 1 diagnostics are emitted by run_campaign.py and run_phenotype_gen.py.
This driver emits Level 2 phenotype sheets and Level 3 evolutionary boards.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from arsitrad_evo.config import GAConfig
from arsitrad_evo.nsga2 import run
from arsitrad_evo.phenotype_gen import build_prototype
from arsitrad_evo.publication_v3 import (
    render_phenotype_sheet, render_population_board,
    render_selection_board, render_objective_extremes, render_pareto_board,
    render_rotation_study,
)
from select_v3 import architectural_gate, fingerprint, replay


ROOT = Path(__file__).resolve().parent
GENERATIONS = (0, 10, 20, 40, 60, 80)


def _load_archive(campaign: Path):
    out = []
    with (campaign / "data" / "pareto_genotypes.jsonl").open(encoding="utf-8") as fh:
        for index, line in enumerate(fh):
            row = json.loads(line)
            row["archive_index"] = index
            out.append((row, replay(row)))
    return out


def _snapshot_tracks():
    tracks = {}
    for fixed, lane in ((None, "FREE SEARCH"), (3, "R4×3 STRATUM"),
                        (4, "R4×4 STRATUM")):
        snapshots = {}

        def record(generation, population):
            snapshots[generation] = list(population)

        run(GAConfig(pop_size=100, generations=80, seed=42,
                     n_R4_fixed=fixed), verbose=False,
            snapshot_at=set(GENERATIONS), on_snapshot=record)
        tracks[lane] = snapshots
    return tracks


def _snapshot_pick(population, count: int):
    feasible = [p for p in population if p.feasible]
    pool = feasible if feasible else sorted(population, key=lambda p: p.cv)[:20]
    if len(pool) <= count:
        return pool
    objectives = np.asarray([p.objectives for p in pool])
    start = int(np.argmin(np.max(objectives, axis=1)))
    selected = [start]
    while len(selected) < count:
        d = np.min(np.linalg.norm(
            objectives[:, None, :] - objectives[None, selected, :], axis=2),
            axis=1)
        d[selected] = -1
        selected.append(int(np.argmax(d)))
    return [pool[i] for i in selected]


def generate(campaign: Path):
    expected = json.loads((campaign / "data" / "freeze_manifest_v3.json").read_text())
    actual = fingerprint(campaign)
    if actual["sha256"] != expected["sha256"]:
        raise ValueError("campaign or computational source changed after freeze")
    shortlist = json.loads((campaign / "data" / "shortlist_v3.json").read_text())
    archive = _load_archive(campaign)
    out = campaign / "publication"
    sheets = out / "phenotype_sheets"
    boards = out / "boards"
    sheets.mkdir(parents=True, exist_ok=True)
    boards.mkdir(parents=True, exist_ok=True)
    manifest = {"freeze_sha256": expected["sha256"],
                "diagnostics": ["figures/", "phenotypes/"],
                "phenotype_sheets": [], "boards": []}

    chosen = []
    for item in shortlist:
        trace = item["trace"]
        ph = replay(trace)
        proto = build_prototype(
            ph, candidate_label=item["label"],
            rep_index=item["archive_index"],
            selected_generation=trace["selected_generation"])
        if proto.genotype_id != trace["genotype_id"] or \
                proto.architectural_status == "ROUTE_UNRESOLVED":
            raise ValueError(f"{item['label']}: shortlist replay failed")
        path = sheets / f"{item['label'].lower()}_{proto.genotype_id}.png"
        render_phenotype_sheet(proto, path)
        manifest["phenotype_sheets"].append(path.relative_to(campaign).as_posix())
        chosen.append((item["label"], proto, item["selection_rationale"]))
        print(f"[publication] sheet {item['label']} {proto.genotype_id}")

    path = boards / "final_shortlist.png"
    render_selection_board(
        chosen, path,
        subtitle="Minimum sampled exposure at each resident capacity, then balanced / "
                 "F3 specialist / objective contrast. Exact archived genotypes.")
    manifest["boards"].append(path.relative_to(campaign).as_posix())
    path = boards / "pareto_spatial_tradeoff.png"
    render_pareto_board(archive, chosen, path)
    manifest["boards"].append(path.relative_to(campaign).as_posix())

    balanced_ph = replay(shortlist[0]["trace"])
    base = chosen[0][1]
    for module in base.modules:
        if module.code != "R4" or not module.quarter_turn_feasible:
            continue
        rotated = build_prototype(
            balanced_ph, candidate_label="BALANCED ROTATED STUDY",
            selected_generation=shortlist[0]["trace"]["selected_generation"],
            rotations={module.inst_id: 90})
        if rotated.constraint_status != "MODEL_FEASIBLE" or \
                rotated.architectural_status == "ROUTE_UNRESOLVED" or \
                sum(s.exposed for s in rotated.sightlines) > \
                sum(s.exposed for s in base.sightlines):
            continue
        path = boards / "physical_rotation_study.png"
        render_rotation_study(base, rotated, path)
        manifest["boards"].append(path.relative_to(campaign).as_posix())
        break
    else:
        raise RuntimeError("BALANCED: no connected model-feasible R4 quarter turn")

    prototype_cache = {}

    def valid_proto(row, ph):
        key = row["genotype_id"]
        if key not in prototype_cache:
            proto, reasons = architectural_gate(ph, row["selected_generation"])
            prototype_cache[key] = None if reasons else proto
        return prototype_cache[key]

    extremes = []
    for m in range(9):
        for row, ph in sorted(archive, key=lambda pair: (
                pair[1].objectives[m], pair[0]["genotype_id"])):
            proto = valid_proto(row, ph)
            if proto is not None:
                extremes.append((f"F{m+1}  /  MINIMUM", proto))
                break
        else:
            raise RuntimeError(f"F{m+1}: no architectural phenotype passed")
    path = boards / "objective_extremes.png"
    render_objective_extremes(extremes, path)
    manifest["boards"].append(path.relative_to(campaign).as_posix())

    relative = []
    for capacity in (2, 3, 4):
        options = ((row, ph) for row, ph in archive if ph.n_R4 == capacity)
        for row, ph in sorted(options, key=lambda pair: (
                float(np.ptp(pair[1].objectives)),
                float(np.max(pair[1].objectives)), pair[0]["genotype_id"])):
            proto = valid_proto(row, ph)
            if proto is not None:
                relative.append((f"R4×{capacity}  /  RELATIVE BALANCE", proto,
                                 f"F1–F9 spread {np.ptp(ph.objectives):.3f}; "
                                 "lowest spread in this capacity stratum"))
                break
        else:
            raise RuntimeError(f"R4x{capacity}: no relative-balance phenotype passed")
    path = boards / "relative_difference.png"
    render_selection_board(relative, path,
                           title="RELATIVE DIFFERENCE  /  BALANCE BY CAPACITY",
                           subtitle="Lowest F1–F9 spread in each capacity stratum, "
                                    "after the spatial and provenance gate. Lower objectives are better.")
    manifest["boards"].append(path.relative_to(campaign).as_posix())

    tracks = _snapshot_tracks()
    for generation in GENERATIONS:
        free = _snapshot_pick(tracks["FREE SEARCH"][generation], 2)
        three = _snapshot_pick(tracks["R4×3 STRATUM"][generation], 1)
        four = _snapshot_pick(tracks["R4×4 STRATUM"][generation], 1)
        entries = []
        for lane, ph in (("FREE / 1", free[0]), ("FREE / 2", free[1]),
                         ("12 RESIDENTS", three[0]),
                         ("16 RESIDENTS", four[0])):
            proto = build_prototype(ph, candidate_label=lane,
                                    selected_generation=generation)
            entries.append((lane, proto))
        path = boards / f"population_gen_{generation:02d}.png"
        render_population_board(generation, entries, path)
        manifest["boards"].append(path.relative_to(campaign).as_posix())
        print(f"[publication] population Gen {generation}")

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2),
                                         encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", default="campaign_v3_full")
    args = parser.parse_args()
    generate((ROOT / args.campaign).resolve())


if __name__ == "__main__":
    main()
