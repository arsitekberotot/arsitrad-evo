"""Cross-artifact and exact-genotype publication gate for V4.1."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

from .archive_v41 import load_jsonl, write_json
from .nsga2_v41 import GAConfigV41, evaluate_v41
from .objectives_v41 import OBJECTIVE_NAMES
from .provenance_v41 import ROOT, assert_current_identity, sha256_file
from .site import load_canonical_site


def validate_campaign(out: str | Path, replay: bool = True) -> dict:
    out = Path(out)
    errors = []
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    identity = manifest["identity"]
    config = manifest["config"]
    try:
        assert_current_identity(identity, config)
    except ValueError as exc:
        errors.append(str(exc))
    for relative, expected in manifest["artifacts"].items():
        path = out / relative
        if not path.exists():
            errors.append(f"Missing artifact {relative}")
        elif sha256_file(path) != expected:
            errors.append(f"Artifact hash mismatch {relative}")
    selection_path = out / "data/selection_manifest.json"
    if sha256_file(selection_path) != manifest["selection_manifest_hash"]:
        errors.append("Selection-manifest hash mismatch")
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    if selection["identity"] != identity:
        errors.append("Selection identity mismatch")
    report = json.loads((out / "report_v41.json").read_text(encoding="utf-8"))
    if report["identity"] != identity:
        errors.append("Report identity mismatch")
    if report["source_manifest_hash"] != sha256_file(out / "manifest.json"):
        errors.append("Report references an outdated manifest")
    if report["source_selection_manifest_hash"] != sha256_file(selection_path):
        errors.append("Report references outdated selections")
    if report["selected_phenotype_count"] != sum(len(r["selected"]) for r in selection["runs"]):
        errors.append("Report selected-phenotype count differs from selection manifest")
    if report["objectives"] != list(OBJECTIVE_NAMES):
        errors.append("Report objective names differ from current evaluation")
    if report["site"]["arrival_edge"] != 7 or report["site"]["exact_gate"] is not None:
        errors.append("Report misstates arrival-zone evidence")
    md = (out / "report_v41.md").read_text(encoding="utf-8")
    if "edge 7" not in md:
        errors.append("Human-readable report omits corrected arrival edge")
    archive = list(load_jsonl(out / "data/archive.jsonl"))
    by_run = defaultdict(list)
    for row in archive:
        by_run[row["run_id"]].append(row)
        if row["identity"] != identity:
            errors.append(f"Archive identity mismatch: {row['phenotype_id']}")
        if row["generated_units"] != row["retained_units"] + len(row["filtered_units"]):
            errors.append(f"Unit filtration mismatch: {row['phenotype_id']}")
        if row["feasible"] and row["collision_report"]["illegal_overlap_count"]:
            errors.append(f"Feasible phenotype has illegal overlap: {row['phenotype_id']}")
        if row["feasible"] and row["collision_report"]["unpermitted_shared_edge_count"]:
            errors.append(f"Feasible phenotype has unpermitted shared edge: {row['phenotype_id']}")
        if row["concurrent_day_users"] > row["nominal_room_capacity"]:
            errors.append(f"Occupancy exceeds nominal room capacity: {row['phenotype_id']}")
    if len(archive) != manifest["archive_records"]:
        errors.append("Archive record count differs from manifest")
    site = load_canonical_site(ROOT / "data/site.geojson", ROOT / "data/site.yaml")
    run_rows = [json.loads(path.read_text(encoding="utf-8"))["run"]
                for path in sorted((out / "runs").glob("*.json"))]
    if {r["run_id"]: r for r in report["main_runs"]} != {
            r["run_id"]: r for r in run_rows if r["kind"] == "main"}:
        errors.append("Report main-run claims differ from run data")
    if {r["run_id"]: r for r in report["day48_runs"]} != {
            r["run_id"]: r for r in run_rows if r["kind"] == "day48"}:
        errors.append("Report day48-run claims differ from run data")
    capacity_ids = [r["run_id"] for r in run_rows if r["kind"] == "capacity"]
    capacity_found = sum(any(row["feasible"] for row in by_run[run_id])
                         for run_id in capacity_ids)
    if report["capacity_scenarios"] != {
            "tested": len(capacity_ids), "feasible_found": capacity_found,
            "not_found_under_budget": len(capacity_ids) - capacity_found}:
        errors.append("Report capacity claims differ from archive")
    expected_selections = [{"run_id": r["run_id"],
                            "candidate_ids": r["final_candidate_ids"],
                            "selected_ids": r["selected"]} for r in selection["runs"]]
    if report["selection_runs"] != expected_selections:
        errors.append("Report selection claims differ from selection manifest")
    for run in selection["runs"]:
        run_id = run["run_id"]
        metadata = json.loads((out / "runs" / f"{run_id}.json").read_text(encoding="utf-8"))
        generations = metadata["config"]["generations"]
        recomputed = sorted({r["phenotype_id"] for r in by_run[run_id]
                             if r["selected_generation"] == generations
                             and r["feasible"] and r["residents"] >= 8
                             and r["collision_report"]["illegal_overlap_count"] == 0})
        if recomputed != run["final_candidate_ids"] or recomputed != metadata["final_candidate_ids"]:
            errors.append(f"Candidate IDs do not match current archive: {run_id}")
        present = {r["phenotype_id"] for r in by_run[run_id]}
        for mode, gid in run["selected"].items():
            if gid not in present:
                errors.append(f"Selection {mode} absent from current archive: {gid}")
                continue
            path = out / "phenotypes" / run_id / f"{gid}.json"
            image_path = out / "phenotypes" / run_id / f"{gid}.png"
            if not path.exists() or not image_path.exists():
                errors.append(f"Selected phenotype or image missing: {run_id}/{gid}")
                continue
            phenotype = json.loads(path.read_text(encoding="utf-8"))
            if phenotype["phenotype_id"] != gid or phenotype["identity"] != identity:
                errors.append(f"Selected phenotype ID/identity mismatch: {run_id}/{gid}")
            facts = run["selected_facts"][mode]
            for field in ("phenotype_id", "residents", "concurrent_day_users",
                          "nominal_room_capacity", "feasible"):
                if facts[field] != phenotype[field]:
                    errors.append(f"Selection facts differ from phenotype {field}: {run_id}/{gid}")
            if facts["collision_count"] != phenotype["collision_report"]["illegal_overlap_count"]:
                errors.append(f"Selection collision claim differs from phenotype: {run_id}/{gid}")
            if facts["zone_type"] != phenotype["zone_state"]["type"]:
                errors.append(f"Selection zone claim differs from phenotype: {run_id}/{gid}")
            if abs(facts["gfa_m2"] - phenotype["gfa_m2"]) > 1e-9:
                errors.append(f"Selection GFA differs from phenotype: {run_id}/{gid}")
            if phenotype.get("fitness_ranks") != run["fitness_ranks"].get(gid):
                errors.append(f"Fitness ranks differ from selection manifest: {run_id}/{gid}")
            if phenotype["residents"] < 8 or not phenotype["feasible"]:
                errors.append(f"Ineligible selected residential-care phenotype: {run_id}/{gid}")
            if phenotype["collision_report"]["illegal_overlap_count"]:
                errors.append(f"Selected phenotype has illegal overlap: {run_id}/{gid}")
            if phenotype["collision_report"]["unpermitted_shared_edge_count"]:
                errors.append(f"Selected phenotype has unpermitted shared edge: {run_id}/{gid}")
            with Image.open(image_path) as image:
                description = json.loads(image.info.get("Description", "{}"))
            if description.get("phenotype_id") != gid or description.get("identity") != identity:
                errors.append(f"PNG phenotype ID/identity mismatch: {run_id}/{gid}")
            if gid not in md:
                errors.append(f"Human-readable report omits selected ID: {run_id}/{gid}")
            if replay:
                cfg = GAConfigV41(**metadata["config"])
                again = evaluate_v41(np.asarray(phenotype["genotype"], float), site, cfg,
                                     phenotype["birth_generation"])
                fields = {
                    "phenotype_id": again.genotype_id,
                    "residents": again.residents,
                    "concurrent_day_users": again.day_users,
                    "nominal_room_capacity": again.nominal_day_capacity,
                    "generated_units": again.generated_units,
                    "retained_units": again.retained_units,
                    "feasible": again.feasible,
                }
                for field, value in fields.items():
                    if phenotype[field] != value:
                        errors.append(f"Replay mismatch {field}: {run_id}/{gid}")
                for name, value in phenotype["objective_vector"].items():
                    actual = next(r.value for r in again.objective_vector.results if r.name == name)
                    if abs(actual - value) > 1e-9:
                        errors.append(f"Replay objective mismatch {name}: {run_id}/{gid}")
    for path in out.rglob("*.png"):
        with Image.open(path) as image:
            description = json.loads(image.info.get("Description", "{}"))
        if description.get("identity") != identity:
            errors.append(f"PNG source identity mismatch: {path.relative_to(out)}")
    parity = json.loads((out / "PAPER_PIPELINE_PARITY.json").read_text(encoding="utf-8"))
    if not parity["passed"]:
        errors.append("Paper-pipeline parity report failed")
    for stage in parity["stages"]:
        path = out / stage["dataset"]
        if not path.exists():
            errors.append(f"Parity stage has no dataset: {stage['stage']}")
        elif sum(1 for _ in load_jsonl(path)) != stage["records"]:
            errors.append(f"Parity stage record count mismatch: {stage['stage']}")
    gate = {"schema": "v4.1-publication-gate/1", "identity": identity,
            "passed": not errors, "errors": errors,
            "archive_records": len(archive),
            "selected_records": sum(len(r["selected"]) for r in selection["runs"]),
            "replay_checked": replay}
    write_json(out / "validation_gate.json", gate)
    return gate
