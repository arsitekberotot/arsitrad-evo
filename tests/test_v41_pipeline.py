"""Behavioral gates for the architectural V4.1 middle layer."""
from types import SimpleNamespace
import json

import numpy as np

from arsitrad_evo.constraints_v41 import evaluate_constraints_v41
from arsitrad_evo.campaign_v41 import STAGE_CODE, build_campaign, default_config
from arsitrad_evo.context_v41 import SiteContext, zoning_state
from arsitrad_evo.genotype_v4 import InstanceV4
from arsitrad_evo.modules_v4 import MODULE_LIBRARY_V4
from arsitrad_evo.nsga2_v4 import _fast_nondominated_sort
from arsitrad_evo.nsga2_v41 import GAConfigV41, run_v41
from arsitrad_evo.pipeline_v41 import (
    FAMILIES, HEADER, PER_SLOT, SLOT_POOL, collision_gate, decode_v41,
    random_genome_v41,
)
from arsitrad_evo.program_v41 import catalogue
from arsitrad_evo.selections_v41 import average_fitness_rank, relative_difference
from arsitrad_evo.site import load_canonical_site, distance_to_arrival, anchor_point
from arsitrad_evo.validate_v41 import validate_campaign


def _site():
    return load_canonical_site("data/site.geojson", "data/site.yaml")


def test_southern_arrival_is_segment_and_unknown_fields_disabled():
    site = _site()
    context = SiteContext.from_site(site)
    assert site.frontage_edges == [7]
    assert anchor_point(site, "public_entry") is None
    assert distance_to_arrival(site, site.edges[7].midpoint) == 0
    assert site.preferred_expansion_direction == ""
    assert context.sample("service_access_attraction", site.centroid) is None
    assert context.sample("environmental_exposure", site.centroid) is None
    assert context.sample("expansion_potential", site.centroid) is None
    assert context.sample("public_access_attraction", site.edges[7].midpoint) == 1


def test_module_records_have_distinct_program_variants():
    records = catalogue()
    assert set(records) == set(MODULE_LIBRARY_V4)
    for code, record in records.items():
        assert record["function"] and record["size"] and record["modularity_category"]
        assert record["program_composition"]
        assert all(component["count_provenance"] for component in record["program_composition"])
    for family in {r["function"] for r in records.values()}:
        variants = [r for r in records.values() if r["function"] == family]
        compositions = [tuple((x["component"], x["count"]) for x in r["program_composition"])
                        for r in variants]
        assert len(compositions) == len(set(compositions))
        assert len({r["size"] for r in variants}) == len(variants)


def test_population_and_seed_separate_from_occupancy():
    site = _site()
    g = random_genome_v41(np.random.default_rng(42), site)
    ph = decode_v41(g, site, concurrent_day_users=32)
    assert ph.generated_units == ph.retained_units + len(ph.filtered_units)
    assert ph.day_users == 32
    assert ph.nominal_day_capacity > ph.day_users
    assert sum(ph.occupancy_allocation["by_function"].values()) == ph.day_users
    assert ph.requested_unit_population["population_seed"] == ph.population_seed
    assert 0 <= ph.requested_unit_population["specialized_function_ratio"] <= 1
    assert abs(sum(ph.requested_unit_population["modularity_ratios"].values()) - 1) < 1e-9
    assert ph.unit_population["developmental_population"] + ph.unit_population["variational_population"] == ph.retained_units
    assert len(ph.stage_records) >= 10


def test_zone_scales_change_area_and_population_genes_change_program():
    site = _site()
    context = SiteContext.from_site(site)
    a = zoning_state(context, [1, 1, 1, 1, 1])
    b = zoning_state(context, [4, .1, .1, .1, .1])
    assert a["area_m2"]["public_civic"] < b["area_m2"]["public_civic"]
    assert a["type"] != b["type"]
    g = random_genome_v41(np.random.default_rng(1), site)
    changed = g.copy()
    r4_index = FAMILIES.index("R4")
    changed[r4_index] = min(8, int(g[r4_index]) + 1)
    if changed[r4_index] == g[r4_index]:
        changed[r4_index] -= 1
    assert decode_v41(g, site).requested_unit_population["by_function"] != decode_v41(changed, site).requested_unit_population["by_function"]


def test_illegal_overlap_fails_model_feasibility_even_when_area_ratio_small():
    site = _site()
    g = random_genome_v41(np.random.default_rng(42), site)
    ph = decode_v41(g, site)
    first = ph.instances[0]
    second = ph.instances[1]
    second.x, second.y = first.x, first.y
    ph.collision_report = collision_gate(ph.instances)
    report = evaluate_constraints_v41(ph, 32)
    assert ph.collision_report["illegal_overlap_count"] > 0
    assert not report.feasible
    assert any(c.name == "object_collision" and not c.passed for c in report.results)


def test_shared_edge_has_zero_collision_area():
    a = InstanceV4("R4-M", "R4", 10, 10, 8, 8, instance_id="a",
                   attachment_mode="shared_edge", connection_type="porch")
    b = InstanceV4("R4-M", "R4", 18, 10, 8, 8, instance_id="b",
                   attachment_mode="shared_edge", connection_type="porch")
    result = collision_gate([a, b])
    assert result["passed"]
    assert result["illegal_overlap_area_m2"] == 0
    assert result["shared_edges"][0]["intentional"]


def test_unpermitted_touch_is_not_model_feasible():
    site = _site()
    ph = decode_v41(random_genome_v41(np.random.default_rng(42), site), site)
    a = InstanceV4("R4-M", "R4", 10, 10, 8, 8, instance_id="a",
                   group_id=1, attachment_mode="detached", connection_type="porch")
    b = InstanceV4("R4-M", "R4", 18, 10, 8, 8, instance_id="b",
                   group_id=2, attachment_mode="detached", connection_type="porch")
    ph.instances = [a, b]
    ph.collision_report = collision_gate(ph.instances)
    result = evaluate_constraints_v41(ph, 32)
    assert ph.collision_report["illegal_overlap_count"] == 0
    assert ph.collision_report["unpermitted_shared_edge_count"] > 0
    assert any(c.name == "attachment_grammar" and not c.passed for c in result.results)
    assert not result.feasible


def test_stacked_footprints_are_recorded_separately_from_illegal_overlap():
    lower = InstanceV4("H0", "H0", 10, 10, 8, 8, floor=0, instance_id="lower")
    upper = InstanceV4("I0-S", "I0", 10, 10, 4, 4, floor=1, instance_id="upper")
    result = collision_gate([lower, upper])
    assert result["passed"]
    assert result["illegal_overlap_count"] == 0
    assert result["stacked_footprint_pairs"][0]["overlap_m2"] == 16


def test_grouping_pattern_changes_actual_geometry():
    site = _site()
    genes = random_genome_v41(np.random.default_rng(6), site)
    genes[len(FAMILIES) + 6] = 1  # linear
    linear = decode_v41(genes, site)
    genes[len(FAMILIES) + 6] = 0  # detached
    detached = decode_v41(genes, site)
    assert linear.requested_unit_population["by_variant"] == detached.requested_unit_population["by_variant"]
    assert [(i.code, round(i.x, 3), round(i.y, 3)) for i in linear.instances] != [
        (i.code, round(i.x, 3), round(i.y, 3)) for i in detached.instances]


def test_relative_difference_and_average_rank_can_select_different_solutions():
    items = [SimpleNamespace(genotype_id=label, objectives=np.array(values, float))
             for label, values in (("extreme", [0, 0, 2]),
                                   ("balanced", [1, 1, 1]),
                                   ("opposite", [2, 2, 0]))]
    assert relative_difference(items)[0].genotype_id == "balanced"
    assert average_fitness_rank(items)[0].genotype_id == "extreme"


def test_v4_nondominated_sort_partitions_population():
    items = [SimpleNamespace(feasible=True, cv=0, rank=-1,
                             objectives=np.array(values, float))
             for values in ([0, 0], [1, 0], [0, 1], [1, 1], [2, 2])]
    fronts = _fast_nondominated_sort(items)
    assert sum(map(len, fronts)) == len(items)
    assert set(fronts[0]) == {0}


def test_evolution_keeps_population_and_archives_every_birth():
    site = _site()
    cfg = GAConfigV41(pop_size=8, generations=2, seed=42, concurrent_day_users=32)
    pop, fronts, history, archive = run_v41(site, cfg)
    assert len(pop) == cfg.pop_size
    assert len(archive) == cfg.pop_size * (cfg.generations + 1)
    assert all(p.genotype_id and len(p.genes) > 0 for p in archive)
    assert all(p.selected_generation is None or p.selected_generation >= p.birth_generation for p in archive)
    assert len(fronts[0]) > 0
    assert any(p.feasible and p.residents >= 8 for p in archive)


def test_construction_stages_expose_inputs_outputs_and_provenance():
    site = _site()
    ph = decode_v41(random_genome_v41(np.random.default_rng(13), site), site)
    expected = set(STAGE_CODE) - {
        "function_size_modularity", "constraint_evaluation", "fitness_evaluation",
        "nsga2_reproduction", "all_generation_archive", "pareto_front_selection",
        "fittest_selection", "relative_difference_selection",
        "average_fitness_selection", "store_distribution", "post_analysis_comparison"}
    stages = {stage["stage"]: stage for stage in ph.stage_records}
    assert expected <= stages.keys()
    for name in expected:
        assert stages[name]["inputs"], name
        assert stages[name]["outputs"], name
        assert stages[name]["provenance"], name


def test_publication_gate_links_stages_and_rejects_report_drift(tmp_path):
    config = default_config(smoke=True)
    config.update(main_pop=4, main_gen=1, day48_seeds=[], capacity_day_strata=[])
    out = tmp_path / "v41_publication"
    build_campaign(out, config, verbose=False)
    gate = validate_campaign(out, replay=True)
    assert gate["passed"], gate["errors"]
    parity = json.loads((out / "PAPER_PIPELINE_PARITY.json").read_text(encoding="utf-8"))
    assert {stage["stage"] for stage in parity["stages"]} == set(STAGE_CODE)
    assert all(stage["inputs"] and stage["outputs"] and stage["records"] > 0
               for stage in parity["stages"])
    for stage in parity["stages"]:
        first = json.loads((out / stage["dataset"]).read_text(encoding="utf-8").splitlines()[0])
        assert first["data"]["provenance"]
    report_path = out / "report_v41.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["main_runs"][0]["feasible_final"] += 1
    report_path.write_text(json.dumps(report), encoding="utf-8")
    failed = validate_campaign(out, replay=False)
    assert not failed["passed"]
    assert "Report main-run claims differ from run data" in failed["errors"]
