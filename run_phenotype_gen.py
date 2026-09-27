"""Replay the frozen v3 shortlist and export architectural prototype diagnostics.

Each candidate is loaded from the exact saved genotype vector, checked against
its fingerprint and model constraints, then converted to the spatial schema.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from arsitrad_evo.phenotype_gen import build_prototype, render_suite
from select_v3 import replay


ROOT = Path(__file__).resolve().parent


def generate(campaign: Path) -> list[dict]:
    shortlist_path = campaign / "data" / "shortlist_v3.json"
    shortlist = json.loads(shortlist_path.read_text(encoding="utf-8"))
    out = campaign / "phenotypes"
    out.mkdir(exist_ok=True)
    manifest = []
    for item in shortlist:
        trace = item["trace"]
        ph = replay(trace)
        label = item["label"]
        proto = build_prototype(
            ph, candidate_label=label, rep_index=item["archive_index"],
            selected_generation=trace["selected_generation"])
        if proto.genotype_id != trace["genotype_id"]:
            raise ValueError(f"{label}: prototype differs from frozen genotype")
        if proto.constraint_status != "MODEL_FEASIBLE" or \
                proto.architectural_status == "ROUTE_UNRESOLVED":
            raise ValueError(f"{label}: architectural validation gate failed")
        if proto.gfa != trace["areas"]["gfa"]:
            raise ValueError(f"{label}: GFA differs from frozen trace")
        stem = f"{label.lower()}_{proto.genotype_id}"
        files = render_suite(proto, str(out), stem)
        manifest.append({
            "candidate": label, "genotype_id": proto.genotype_id,
            "seed": proto.seed, "birth_generation": proto.birth_generation,
            "selected_generation": proto.selected_generation,
            "archive_index": item["archive_index"],
            "residents": proto.residents, "day_users": proto.day_users,
            "gfa_m2": proto.gfa, "constraint_status": proto.constraint_status,
            "architectural_status": proto.architectural_status,
            "exposure_status": proto.exposure_status,
            "exposed_sensitive_pairs": item["exposed_sensitive_pairs"],
            "files": {key: Path(path).name for key, path in files.items()},
        })
        print(f"[phenotype] {label} {proto.genotype_id}: {proto.gfa} m2, "
              f"{proto.residents} residents, {proto.exposure_status}")
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
