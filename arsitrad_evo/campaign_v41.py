"""Run the V4.1 research campaigns and publish hash-linked evidence."""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import asdict, replace
from pathlib import Path

from .archive_v41 import append_jsonl, phenotype_record, write_json
from .context_v41 import SiteContext
from .nsga2_v41 import GAConfigV41, run_v41
from .objectives_v41 import OBJECTIVE_NAMES
from .program_v41 import catalogue
from .provenance_v41 import ROOT, make_identity, sha256_file, sha256_json
from .selections_v41 import select_v41, candidates, _ranks
from .site import load_canonical_site
from .visualize_v41 import (render_module_catalogue, render_pipeline_board,
                            render_population_selection, render_phenotype_sheet)


STAGE_CODE = {
    "function_size_modularity": "arsitrad_evo/program_v41.py:catalogue",
    "module_unit": "arsitrad_evo/program_v41.py:module_record",
    "initial_unit_population": "arsitrad_evo/pipeline_v41.py:decode_v41",
    "population_seed": "arsitrad_evo/pipeline_v41.py:decode_v41",
    "modularity_ratios": "arsitrad_evo/program_v41.py:population_summary",
    "architectural_packing_grouping": "arsitrad_evo/pipeline_v41.py:_place",
    "dynamic_zoning": "arsitrad_evo/context_v41.py:zoning_state",
    "object_collision": "arsitrad_evo/pipeline_v41.py:collision_gate",
    "unit_filtration": "arsitrad_evo/pipeline_v41.py:decode_v41",
    "site_external_references": "arsitrad_evo/context_v41.py:SiteContext",
    "architectural_phenotype": "arsitrad_evo/pipeline_v41.py:decode_v41",
    "fitness_evaluation": "arsitrad_evo/objectives_v41.py:evaluate_objectives_v41",
    "constraint_evaluation": "arsitrad_evo/constraints_v41.py:evaluate_constraints_v41",
    "nsga2_reproduction": "arsitrad_evo/nsga2_v41.py:run_v41",
    "all_generation_archive": "arsitrad_evo/archive_v41.py:phenotype_record",
    "pareto_front_selection": "arsitrad_evo/selections_v41.py:pareto_set",
    "fittest_selection": "arsitrad_evo/selections_v41.py:select_v41",
    "relative_difference_selection": "arsitrad_evo/selections_v41.py:relative_difference",
    "average_fitness_selection": "arsitrad_evo/selections_v41.py:average_fitness_rank",
    "store_distribution": "arsitrad_evo/campaign_v41.py:build_campaign",
    "post_analysis_comparison": "arsitrad_evo/campaign_v41.py:_report",
}


def _stage_file(out: Path, stage: str) -> Path:
    return out / "stages" / f"{stage}.jsonl"


def _write_stage(out: Path, stage: str, identity: dict, data: dict, run_id: str | None = None):
    data = {"provenance": "[DESIGN HYPOTHESIS]", **data}
    append_jsonl(_stage_file(out, stage), {"schema": "pipeline-stage/v4.1",
                                            "identity": identity, "stage": stage,
                                            "run_id": run_id, "data": data})


def _write_csv(path: Path, rows: list[dict], identity: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        write_json(path.with_suffix(".json"), {"identity": identity, "rows": []})
        return
    keys = list(rows[0]) + list(identity)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, **identity})


def _plan(config: dict):
    for seed in config["main_seeds"]:
        yield (f"main_s{seed}", "main", GAConfigV41(config["main_pop"],
                config["main_gen"], seed, config["main_day_users"]))
    for seed in config["day48_seeds"]:
        yield (f"day48_s{seed}", "day48", GAConfigV41(config["day48_pop"],
                config["day48_gen"], seed, 48))
    for day in config["capacity_day_strata"]:
        for residents in config["capacity_resident_strata"]:
            seed = config["capacity_seed"]
            yield (f"capacity_d{day}_r{residents}_s{seed}", "capacity",
                   GAConfigV41(config["capacity_pop"], config["capacity_gen"],
                               seed, day, residents))


def default_config(smoke: bool = False) -> dict:
    if smoke:
        return {"schema": "v4.1-campaign-config/1", "main_seeds": [42],
                "main_pop": 8, "main_gen": 2, "main_day_users": 32,
                "day48_seeds": [7], "day48_pop": 8, "day48_gen": 2,
                "capacity_day_strata": [8, 48],
                "capacity_resident_strata": [8, 32], "capacity_seed": 123,
                "capacity_pop": 8, "capacity_gen": 2, "smoke": True}
    return {"schema": "v4.1-campaign-config/1", "main_seeds": [42, 7, 123],
            "main_pop": 32, "main_gen": 16, "main_day_users": 32,
            "day48_seeds": [42, 7], "day48_pop": 32, "day48_gen": 16,
            "capacity_day_strata": [8, 16, 24, 32, 40, 48],
            "capacity_resident_strata": [8, 16, 24, 32], "capacity_seed": 123,
            "capacity_pop": 12, "capacity_gen": 6, "smoke": False}


def _parity_report(out: Path, identity: dict, stage_counts: Counter):
    from .archive_v41 import load_jsonl
    paper = {
        "function_size_modularity": "Figure 1 module-library axes",
        "module_unit": "Figure 1 furniture module unit",
        "initial_unit_population": "Figure 4 initial population / Method 3.3",
        "population_seed": "Figure 4 population seed / Method 3.3",
        "modularity_ratios": "Figure 4 specialized and general modularity ratios",
        "architectural_packing_grouping": "Figure 4 circle packing, architecturally adapted",
        "dynamic_zoning": "Figure 4 dynamic scaling and zoning",
        "object_collision": "Figure 4 object collision",
        "unit_filtration": "Figure 4 unit filtration",
        "site_external_references": "Figure 4 external references",
        "architectural_phenotype": "Figure 4 phenotype",
        "fitness_evaluation": "Figure 4 evaluation and fitness assignment",
        "constraint_evaluation": "Architectural extension: model-feasibility gate",
        "nsga2_reproduction": "Figure 4 Wallacei reproduction, Python NSGA-II equivalent",
        "all_generation_archive": "Figure 4 Archive X",
        "pareto_front_selection": "Figure 4 Pareto front selection",
        "fittest_selection": "Figure 4 fittest solution selection",
        "relative_difference_selection": "Figure 4 relative-difference selection",
        "average_fitness_selection": "Figure 4 average-fitness selection",
        "store_distribution": "Figure 4 store and distribution",
        "post_analysis_comparison": "Figure 4 post-analysis and comparison",
    }
    stages = []
    for name, code in STAGE_CODE.items():
        records = stage_counts[name]
        stages.append({"stage": name, "paper_mechanism": paper[name],
                       "architectural_equivalent": name.replace("_", " "),
                       "status": "adapted_present" if name in {
                           "architectural_packing_grouping", "dynamic_zoning", "nsga2_reproduction",
                           "site_external_references", "architectural_phenotype"} else "present",
                       "inputs": (next(iter(load_jsonl(_stage_file(out, name))))["data"].get("inputs", [])
                                  if records else []),
                       "outputs": (next(iter(load_jsonl(_stage_file(out, name))))["data"].get("outputs", [])
                                   if records else []),
                       "code": code, "dataset": _stage_file(out, name).relative_to(out).as_posix(),
                       "records": records, "test": "tests/test_v41_pipeline.py",
                       "provenance": "[DESIGN HYPOTHESIS]"})
    report = {"schema": "PAPER_PIPELINE_PARITY/v4.1", "identity": identity,
              "paper": "Riskiyanto et al. (2025), Figures 1 and 4; Methods 3.2-3.4",
              "stages": stages, "passed": all(s["records"] > 0 for s in stages),
              "adaptation_note": "Furniture circle packing becomes architectural grouping; dynamic office zoning becomes ordered care-campus depth with parallel service; Wallacei reproduction becomes constrained Python NSGA-II."}
    write_json(out / "PAPER_PIPELINE_PARITY.json", report)
    lines = ["# PAPER_PIPELINE_PARITY — V4.1", "",
             f"Campaign `{identity['campaign_id']}`. All stage datasets are persisted under `stages/`.", "",
             "| Stage | Paper mechanism | Architectural equivalent | Records | Code / dataset |",
             "|---|---|---|---:|---|"]
    for s in stages:
        lines.append(f"| {s['stage']} | {s['paper_mechanism']} | {s['architectural_equivalent']} | {s['records']} | `{s['code']}` / `{s['dataset']}` |")
    lines += ["", report["adaptation_note"], "",
              "Unknown service access, TPST exposure, wind, noise, odour, dust, drainage, vegetation and directional expansion remain disabled and [TO VERIFY]."]
    (out / "PAPER_PIPELINE_PARITY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def _report(out: Path, identity: dict, config: dict, run_rows: list[dict],
            selection_manifest: dict, capacity_rows: list[dict], manifest_hash: str):
    selected = selection_manifest["runs"]
    total_selected = sum(len(r["selected"]) for r in selected)
    main = [r for r in run_rows if r["kind"] == "main"]
    day48 = [r for r in run_rows if r["kind"] == "day48"]
    capacity_found = sum(r["feasible_archive"] > 0 for r in capacity_rows)
    report = {
        "schema": "v4.1-consolidated-report/1", "identity": identity,
        "source_manifest_hash": manifest_hash,
        "source_selection_manifest_hash": sha256_file(out / "data/selection_manifest.json"),
        "site": {"arrival_edge": 7, "arrival_segment_lonlat": [
            [107.0082724, -6.3505665], [107.008038, -6.350512]],
            "exact_gate": None, "preferred_expansion_direction": None},
        "objectives": list(OBJECTIVE_NAMES),
        "main_runs": main, "day48_runs": day48,
        "capacity_scenarios": {"tested": len(capacity_rows),
                               "feasible_found": capacity_found,
                               "not_found_under_budget": len(capacity_rows) - capacity_found},
        "selected_phenotype_count": total_selected,
        "selection_runs": [{"run_id": r["run_id"],
                            "candidate_ids": r["final_candidate_ids"],
                            "selected_ids": r["selected"]} for r in selected],
        "findings": [
            "The south edge 7 is the public arrival segment; no exact gate or expansion direction is asserted.",
            "Concurrent day users are allocated across available rooms; nominal room-capacity sums remain a separate metric.",
            "Model feasibility requires zero unintended same-floor overlap and the essential residential-care program.",
            "Capacity cells with no feasible candidate are search-budget findings, not proof of physical impossibility.",
        ],
        "limitations": ["Site nuisance, service road, wind, flooding, vegetation and expansion direction await evidence.",
                        "Route, sightline, solar and phasing metrics are schematic design proxies, not code compliance or the architect's decision."],
    }
    write_json(out / "report_v41.json", report)
    lines = ["# The Threshold — V4.1 paper-aligned modular evolution", "",
             f"Campaign `{identity['campaign_id']}`; source manifest SHA-256 `{manifest_hash}`.", "",
             "## Site and program", "",
             "The verified public arrival zone is the complete southern GeoJSON edge 7. The exact gate and preferred growth direction remain [TO VERIFY]. Concurrent day users are allocated among available functions; nominal room capacities are reported separately.", "",
             "## Campaign results", "",
             "| Run | Feasible final | Residential candidates | All-generation Pareto | Distinct signatures |",
             "|---|---:|---:|---:|---:|"]
    for row in main + day48:
        lines.append(f"| {row['run_id']} | {row['feasible_final']} | {row['final_candidates']} | {row['all_pareto_size']} | {row['distinct_signatures']} |")
    lines += ["", f"Capacity scenarios with an observed feasible candidate: {capacity_found}/{len(capacity_rows)}. Empty cells mean no candidate found under this recorded search budget.",
              "", "## Selections and architectural reading", ""]
    for run in selected:
        lines.append(f"### {run['run_id']}")
        lines.append("")
        lines.append(f"Final residential candidate IDs: {', '.join(run['final_candidate_ids']) or 'none'}.")
        for mode, gid in run["selected"].items():
            facts = run["selected_facts"][mode]
            lines.append(f"- {mode}: `{gid}` — {facts['residents']} residents, "
                         f"{facts['concurrent_day_users']} concurrent day users, "
                         f"{facts['nominal_room_capacity']} nominal room places, "
                         f"{facts['gfa_m2']:.0f} m² GFA, {facts['zone_type']}, "
                         f"{facts['collision_count']} illegal overlaps. "
                         f"See `phenotypes/{run['run_id']}/{gid}.json` and `.png`.")
        lines.append("")
    lines += ["## Method and limits", "",
              "See `PAPER_PIPELINE_PARITY.md` for each Figure 1/Figure 4 stage and its inspectable dataset. "
              "The six optimization objectives group richer architectural measurements. Outer values in the Decision Diamond are consistently better. "
              "The archive records exact genes, seeds, generation, population, zoning, collisions, objectives, constraints and source hashes.", "",
              "This model supports PA5 schematic development. It does not establish building-code, operational safeguarding or environmental performance compliance."]
    (out / "report_v41.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def build_campaign(out: str | Path = "campaign_v41_verified", config: dict | None = None,
                   verbose: bool = True) -> dict:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    config = config or default_config()
    identity = make_identity(config).asdict()
    site = load_canonical_site(ROOT / "data/site.geojson", ROOT / "data/site.yaml")
    context = SiteContext.from_site(site)
    # A reused output directory must belong to this exact source/config state.
    existing = out / "campaign_identity.json"
    if existing.exists() and json.loads(existing.read_text(encoding="utf-8")) != identity:
        raise ValueError(f"Output {out} belongs to a different code/config/site identity; choose a new directory")
    if (out / "data/archive.jsonl").exists():
        raise ValueError(f"Output {out} already has a campaign archive; choose a new directory")
    write_json(existing, identity)
    write_json(out / "data/config.json", {"identity": identity, "config": config})
    write_json(out / "data/site_context.json", {"identity": identity,
                                              "arrival_edge": site.frontage_edges,
                                              "layers": context.layers,
                                              "fields": context.field_manifest(),
                                              "preferred_expansion_direction": None})
    modules = catalogue()
    write_json(out / "data/module_library.json", {"identity": identity,
                                                  "schema": "module-library/v4.1",
                                                  "modules": modules})
    _write_csv(out / "data/module_library.csv",
               [{"code": r["code"], "function": r["function"], "size": r["size"],
                 "modularity_category": r["modularity_category"],
                 "area_m2": r["area_m2"],
                 "program_composition": json.dumps(r["program_composition"], ensure_ascii=False)}
                for r in modules.values()], identity)
    render_module_catalogue(out / "boards/module_library_catalogue.png", identity)
    for record in modules.values():
        _write_stage(out, "function_size_modularity", identity,
                     {"inputs": ["PA5_program", "module_size", "modularity_role"],
                      "outputs": ["module_library_record"], "state": record,
                      "provenance": record["provenance"]})
    stage_counts = Counter({"function_size_modularity": len(modules)})
    archive_records = []
    run_rows = []
    capacity_rows = []
    selection_runs = []
    selected_phs = {}
    for run_id, kind, cfg in _plan(config):
        if verbose:
            print(f"[v41] {run_id}: pop {cfg.pop_size}, gen {cfg.generations}, day {cfg.concurrent_day_users}, residents {cfg.target_residents}")
        final, fronts, history, archive = run_v41(site, cfg, verbose=False)
        selection = select_v41(final, archive)
        final_candidates = sorted({p.genotype_id for p in candidates(final)})
        run_row = {"run_id": run_id, "kind": kind, "seed": cfg.seed,
                   "concurrent_day_users": cfg.concurrent_day_users,
                   "target_residents": cfg.target_residents,
                   "pop_size": cfg.pop_size, "generations": cfg.generations,
                   "feasible_final": sum(p.feasible for p in final),
                   "final_candidates": len(final_candidates),
                   "archive_count": len(archive),
                   "all_pareto_size": len(selection["all_population_pareto_ids"]),
                   "final_pareto_size": len(selection["final_generation_pareto_ids"]),
                   "distinct_signatures": selection["distinct_architectural_signatures"],
                   "search_space_collapse": selection["search_space_collapse"],
                   "runtime_s": history["runtime_s"]}
        run_rows.append(run_row)
        for ph in archive:
            row = phenotype_record(ph, identity, run_id)
            archive_records.append(row)
            append_jsonl(out / "data/archive.jsonl", row)
            for stage in ph.stage_records:
                _write_stage(out, stage["stage"], identity,
                             {"phenotype_id": ph.genotype_id,
                              "inputs": stage["inputs"], "outputs": stage["outputs"],
                              "provenance": stage["provenance"], "state": stage["data"]},
                             run_id)
                stage_counts[stage["stage"]] += 1
        _write_stage(out, "nsga2_reproduction", identity,
                     {"inputs": ["evaluated_population", "fitness", "seed"],
                      "outputs": ["offspring", "final_population"],
                      "archive_count": len(archive), "history": history}, run_id)
        stage_counts["nsga2_reproduction"] += 1
        _write_stage(out, "all_generation_archive", identity,
                     {"inputs": ["every_genotype", "every_phenotype"],
                      "outputs": ["data/archive.jsonl"],
                      "births": len(archive), "final_ids": [p.genotype_id for p in final]}, run_id)
        stage_counts["all_generation_archive"] += 1
        write_json(out / "runs" / f"{run_id}.json",
                   {"identity": identity, "run": run_row, "config": asdict(cfg),
                    "history": history, "final_population_ids": [p.genotype_id for p in final],
                    "final_candidate_ids": final_candidates,
                    "selection": selection})
        if kind == "capacity":
            capacity_rows.append({"run_id": run_id, "day_users": cfg.concurrent_day_users,
                                  "target_residents": cfg.target_residents,
                                  "feasible_archive": sum(p.feasible for p in archive),
                                  "feasible_final": run_row["feasible_final"],
                                  "observed_status": "feasible_found" if any(p.feasible for p in archive)
                                  else "not_found_under_budget",
                                  "pop_size": cfg.pop_size, "generations": cfg.generations})
            continue
        by_id = {p.genotype_id: p for p in archive}
        selected_facts = {mode: {"phenotype_id": gid,
                                 "residents": by_id[gid].residents,
                                 "concurrent_day_users": by_id[gid].day_users,
                                 "nominal_room_capacity": by_id[gid].nominal_day_capacity,
                                 "gfa_m2": by_id[gid].gfa,
                                 "zone_type": by_id[gid].zone_state["type"],
                                 "collision_count": by_id[gid].collision_report["illegal_overlap_count"],
                                 "feasible": by_id[gid].feasible}
                          for mode, gid in selection["selected"].items()}
        selection_run = {"run_id": run_id, "seed": cfg.seed,
                         "concurrent_day_users": cfg.concurrent_day_users,
                         "final_candidate_ids": final_candidates,
                         "selected_facts": selected_facts,
                         **selection}
        selection_runs.append(selection_run)
        _write_stage(out, "pareto_front_selection", identity,
                     {"inputs": ["all_generation_archive", "final_population"],
                      "outputs": ["all_population_pareto_ids", "final_generation_pareto_ids"],
                      "all": selection["all_population_pareto_ids"],
                      "final": selection["final_generation_pareto_ids"]}, run_id)
        stage_counts["pareto_front_selection"] += 1
        for name in ("fittest_selection", "relative_difference_selection", "average_fitness_selection"):
            prefix = {"fittest_selection": "fittest_", "relative_difference_selection": "relative_difference",
                      "average_fitness_selection": "average_fitness_rank"}[name]
            subset = {k: v for k, v in selection["selected"].items() if k.startswith(prefix)}
            _write_stage(out, name, identity,
                         {"inputs": ["all_population_pareto_ids", "objective_rankings"],
                          "outputs": ["selected_phenotype_ids"], "selected": subset}, run_id)
            stage_counts[name] += 1
        for gid in set(selection["selected"].values()):
            selected_phs[(run_id, gid)] = by_id[gid]
    _write_csv(out / "data/capacity_scenarios.csv", capacity_rows, identity)
    _write_csv(out / "data/run_summary.csv", run_rows, identity)
    selection_manifest = {"schema": "selection-manifest/v4.1", "identity": identity,
                          "objective_names": list(OBJECTIVE_NAMES), "runs": selection_runs}
    write_json(out / "data/selection_manifest.json", selection_manifest)
    for (run_id, gid), ph in selected_phs.items():
        result_dir = out / "phenotypes" / run_id
        record = phenotype_record(ph, identity, run_id)
        run = next(r for r in selection_runs if r["run_id"] == run_id)
        rank_info = run["fitness_ranks"].get(gid, {})
        record["fitness_ranks"] = rank_info
        write_json(result_dir / f"{gid}.json", record)
        render_phenotype_sheet(ph, site, rank_info, result_dir / f"{gid}.png", identity)
    render_population_selection(archive_records, selection_runs[0] if selection_runs else {
        "selected": {}, "all_population_pareto_ids": [],
        "final_generation_pareto_ids": [], "distinct_architectural_signatures": 0},
        out / "boards/evolutionary_population_selection.png", identity)
    _write_stage(out, "store_distribution", identity,
                 {"inputs": ["selected_phenotypes", "archive"],
                  "outputs": ["phenotypes/", "boards/", "data/selection_manifest.json"],
                  "selected_sheets": len(selected_phs)})
    stage_counts["store_distribution"] += 1
    _write_stage(out, "post_analysis_comparison", identity,
                 {"inputs": ["capacity_scenarios", "selection_manifest", "objective_submetrics"],
                  "outputs": ["report_v41.json", "report_v41.md"],
                  "runs": len(run_rows), "capacity_scenarios": len(capacity_rows),
                  "selected_sheets": len(selected_phs)})
    stage_counts["post_analysis_comparison"] += 1
    parity = _parity_report(out, identity, stage_counts)
    nodes = [{"stage": stage, "code": code,
              "dataset": _stage_file(out, stage).relative_to(out).as_posix(),
              "records": stage_counts[stage]} for stage, code in STAGE_CODE.items()]
    write_json(out / "data/pipeline_board.json",
               {"identity": identity, "schema": "pipeline-board/v4.1", "nodes": nodes})
    render_pipeline_board(nodes, out / "boards/adapted_data_flow.png", identity)
    artifacts = {}
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name not in {"manifest.json", "report_v41.json", "report_v41.md", "validation_gate.json"}:
            artifacts[str(path.relative_to(out)).replace("\\", "/")] = sha256_file(path)
    manifest = {"schema": "publication-manifest/v4.1", "identity": identity,
                "config": config, "artifacts": artifacts,
                "selection_manifest_hash": sha256_file(out / "data/selection_manifest.json"),
                "selected_phenotype_ids": sorted({gid for _, gid in selected_phs}),
                "archive_records": len(archive_records),
                "stage_record_counts": dict(stage_counts),
                "parity_passed": parity["passed"]}
    write_json(out / "manifest.json", manifest)
    manifest_hash = sha256_file(out / "manifest.json")
    _report(out, identity, config, run_rows, selection_manifest, capacity_rows, manifest_hash)
    return manifest
