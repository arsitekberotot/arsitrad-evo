"""Lossless V4.1 genotype/phenotype archive serialization."""
from __future__ import annotations

import json
import math
from dataclasses import asdict
from pathlib import Path

import numpy as np


def json_safe(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def phenotype_record(ph, identity: dict, run_id: str) -> dict:
    return json_safe({
        "schema": "architectural-phenotype/v4.1",
        "identity": identity,
        "run_id": run_id,
        "archive_index": getattr(ph, "archive_index", None),
        "phenotype_id": ph.genotype_id,
        "genotype": ph.genes.tolist(),
        "seed": ph.origin_seed,
        "population_seed": ph.population_seed,
        "birth_generation": ph.birth_generation,
        "selected_generation": ph.selected_generation,
        "rank": ph.rank,
        "crowding": ph.crowding,
        "feasible": ph.feasible,
        "constraint_violation": ph.cv,
        "residents": ph.residents,
        "concurrent_day_users": ph.day_users,
        "nominal_room_capacity": ph.nominal_day_capacity,
        "staff": ph.staff,
        "nominal_staff_capacity": ph.nominal_staff_capacity,
        "occupancy_allocation": ph.occupancy_allocation,
        "gfa_m2": ph.gfa,
        "footprint_m2": ph.footprint,
        "landscape_area_m2": ph.landscape_area,
        "reserve_area_m2": ph.reserve_area,
        "landscape_fraction": ph.landscape_frac,
        "floor_count": ph.floor_count,
        "stacked_pairs": ph.stacked_pairs,
        "packing_pattern": ph.packing_pattern,
        "packing_utilization": ph.packing_utilization,
        "requested_unit_population": ph.requested_unit_population,
        "unit_population": ph.unit_population,
        "zone_state": ph.zone_state,
        "zone_population": ph.zone_population,
        "generated_units": ph.generated_units,
        "retained_units": ph.retained_units,
        "filtered_units": ph.filtered_units,
        "collision_report": ph.collision_report,
        "instances": [asdict(i) for i in ph.instances],
        "phases": ph.phases,
        "objective_vector": {r.name: r.value for r in ph.objective_vector.results},
        "objective_submetrics": ph.objective_submetrics,
        "constraint_report": asdict(ph.constraint_report),
        "stage_records": ph.stage_records,
    })


def write_json(path: str | Path, data) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        json.dump(json_safe(data), stream, indent=2, ensure_ascii=False,
                  allow_nan=False)
        stream.write("\n")


def append_jsonl(path: str | Path, data) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(json_safe(data), ensure_ascii=False,
                                allow_nan=False, separators=(",", ":")))
        stream.write("\n")


def load_jsonl(path: str | Path):
    with Path(path).open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)
