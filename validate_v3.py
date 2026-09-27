"""Independent final validation of the frozen v3 archive and publication package."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

from arsitrad_evo.constraints import c_site_boundary
from arsitrad_evo.objectives import OBJECTIVES
from select_v3 import (architectural_gate, fingerprint, replay,
                       _baseline_evidence, _screened_pool)


ROOT = Path(__file__).resolve().parent
RENDER_SOURCES = (
    "arsitrad_evo/phenotype_gen.py", "arsitrad_evo/publication_v3.py",
    "select_v3.py", "run_phenotype_gen.py", "run_publication_v3.py",
    "validate_v3.py",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as fh:
        head = fh.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        raise ValueError(f"not a PNG: {path}")
    return struct.unpack(">II", head[16:24])


def validate(campaign: Path) -> dict:
    frozen = json.loads((campaign / "data/freeze_manifest_v3.json").read_text())
    assert fingerprint(campaign) == frozen, "computational freeze changed"
    gate = json.loads((campaign / "data/validation_gate_v3.json").read_text())
    assert gate["baseline_v2"] == _baseline_evidence()

    table_path = campaign / "data/pareto_archive.csv"
    with table_path.open(newline="", encoding="utf-8") as fh:
        table = list(csv.DictReader(fh))
    rows = [json.loads(line) for line in
            (campaign / "data/pareto_genotypes.jsonl").open(encoding="utf-8")]
    assert len(rows) == len(table)
    capacities = Counter()
    unique = set()
    replayed = []
    for index, (row, csv_row) in enumerate(zip(rows, table)):
        ph = replay(row)
        replayed.append((row, ph))
        assert row["genotype_id"] == csv_row["genotype_id"], index
        assert c_site_boundary(ph) <= 1e-6
        assert all(abs(float(csv_row[f"obj_{name}"]) - float(value)) <= 0.000051
                   for (name, _), value in zip(OBJECTIVES, ph.objectives))
        if row["genotype_id"] not in unique:
            unique.add(row["genotype_id"])
            capacities[ph.n_R4] += 1
    assert len(unique) == gate["v3_archive_size"]
    assert dict(sorted(capacities.items())) == {
        int(k): v for k, v in gate["v3_capacity_distribution"].items()}
    assert gate["v3_all_must_satisfied"] == len(unique)
    assert gate["v3_all_site_contained"] == len(unique)
    _, exposure_floors = _screened_pool(replayed)
    assert gate["shortlist_screen"]["minimum_sampled_exposure_by_R4"] == {
        str(capacity): {"pairs": score[0], "visible_rays": score[1]}
        for capacity, score in exposure_floors.items()}

    shortlist = json.loads((campaign / "data/shortlist_v3.json").read_text())
    assert len(shortlist) == 3
    assert [r["label"] for r in shortlist] == [
        "BALANCED", "SPECIALIZED", "CONTRASTING"]
    assert [r["trace"]["genotype_id"] for r in shortlist] == gate["shortlist_ids"]
    phenotype_manifest = json.loads((campaign / "phenotypes/manifest.json").read_text())
    assert len(phenotype_manifest) == 3
    candidate_evidence = []
    for item, manifest_row in zip(shortlist, phenotype_manifest):
        trace = item["trace"]
        ph = replay(trace)
        proto, reasons = architectural_gate(ph, trace["selected_generation"])
        assert not reasons, (item["label"], reasons)
        proto.candidate = item["label"]
        proto.rep_index = item["archive_index"]
        assert manifest_row["candidate"] == item["label"]
        assert manifest_row["genotype_id"] == proto.genotype_id
        assert manifest_row["seed"] == proto.seed == trace["seed"]
        assert manifest_row["gfa_m2"] == proto.gfa == trace["areas"]["gfa"]
        assert len(proto.safeguarding_actions) == sum(s.exposed for s in proto.sightlines)
        assert (sum(s.exposed for s in proto.sightlines),
                sum(s.visible_rays for s in proto.sightlines)) == \
            exposure_floors[ph.n_R4]
        assert all(path["status"] == "CONNECTED" for path in proto.threshold_paths)
        assert all(not n["unresolved"] for n in proto.route_networks)
        for filename in manifest_row["files"].values():
            path = campaign / "phenotypes" / filename
            assert path.is_file() and path.stat().st_size > 100, path
            if path.suffix == ".png":
                assert min(_png_size(path)) >= 600
        saved = json.loads((campaign / "phenotypes" /
                            manifest_row["files"]["json"]).read_text())
        assert saved == json.loads(json.dumps(proto.to_dict())), \
            f"prototype JSON differs: {item['label']}"
        candidate_evidence.append({
            "label": item["label"], "genotype_id": proto.genotype_id,
            "seed": proto.seed, "birth_generation": proto.birth_generation,
            "selected_generation": proto.selected_generation,
            "residents": proto.residents,
            "model_floor_area_proxy_m2": proto.gfa,
            "must_shortfall_m": proto.must_shortfall,
            "unresolved_routes": 0,
            "exposed_sensitive_pairs": sum(s.exposed for s in proto.sightlines),
            "visible_sampled_rays": sum(s.visible_rays for s in proto.sightlines),
            "tested_sensitive_pairs": len(proto.sightlines),
            "exposure_status": proto.exposure_status,
        })

    publication = json.loads((campaign / "publication/manifest.json").read_text())
    assert publication["freeze_sha256"] == frozen["sha256"]
    assert len(publication["phenotype_sheets"]) == 3
    expected_boards = {"final_shortlist.png", "pareto_spatial_tradeoff.png",
                       "objective_extremes.png", "relative_difference.png",
                       "physical_rotation_study.png"}
    expected_boards |= {f"population_gen_{g:02d}.png"
                        for g in (0, 10, 20, 40, 60, 80)}
    assert {Path(p).name for p in publication["boards"]} == expected_boards
    rendered = publication["phenotype_sheets"] + publication["boards"]
    image_hashes = {}
    for name in rendered:
        path = campaign / name
        assert path.is_file() and path.stat().st_size > 1000, path
        w, h = _png_size(path)
        assert w >= 1600 and h >= 900, (path, w, h)
        image_hashes[name] = _sha(path)

    env = dict(os.environ)
    env.setdefault("MPLCONFIGDIR", str(ROOT / ".venv" / "mplconfig"))
    Path(env["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
    tests = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q"],
                           cwd=ROOT, env=env, text=True,
                           capture_output=True, check=False)
    if tests.returncode:
        raise RuntimeError(tests.stdout + "\n" + tests.stderr)

    result = {
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "freeze_sha256": frozen["sha256"],
        "archive_rows": len(rows), "unique_replayed_genotypes": len(unique),
        "capacity_distribution": dict(sorted(capacities.items())),
        "shortlist": candidate_evidence,
        "candidate_diagnostic_pngs": sum(
            len([p for p in item["files"].values() if p.endswith(".png")])
            for item in phenotype_manifest),
        "phenotype_sheets": len(publication["phenotype_sheets"]),
        "comparative_boards": len(publication["boards"]),
        "tests": tests.stdout.strip(),
        "renderer_source_sha256": {
            name: _sha(ROOT / name) for name in RENDER_SOURCES},
        "publication_png_sha256": image_hashes,
        "status": "PASS",
    }
    target = campaign / "data/verification_v3.json"
    target.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", default="campaign_v3_full")
    args = parser.parse_args()
    result = validate((ROOT / args.campaign).resolve())
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("renderer_source_sha256",
                                   "publication_png_sha256")}, indent=2))


if __name__ == "__main__":
    main()
