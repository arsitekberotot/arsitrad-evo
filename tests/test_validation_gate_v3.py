"""Regression checks for spatial validity and candidate traceability."""
import numpy as np

from arsitrad_evo import analyze, config as C
from arsitrad_evo.constraints import (c_must_adjacency, c_site_boundary,
                                      evaluate_constraints)
from arsitrad_evo.genotype import Instance, Phenotype, decode, random_genotype
from arsitrad_evo.modules import MODULES
from arsitrad_evo.nsga2 import binary_tournament, evaluate, run
from arsitrad_evo.config import GAConfig
from select_v3 import _baseline_evidence


def _instance(code, x, y):
    mt = MODULES[code]
    return Instance(code, x, y, mt.w, mt.d, mt.area, 1, mt.privacy)


def test_decoder_keeps_every_active_footprint_inside_site():
    rng = np.random.default_rng(19)
    for _ in range(100):
        ph = decode(random_genotype(rng))
        assert c_site_boundary(ph) == 0
        for inst in ph.instances:
            assert 0 <= inst.x - inst.w / 2
            assert inst.x + inst.w / 2 <= C.SITE_W
            assert 0 <= inst.y - inst.d / 2
            assert inst.y + inst.d / 2 <= C.SITE_H


def test_manual_overhang_is_a_hard_boundary_violation():
    ph = Phenotype(genes=np.zeros(43), instances=[_instance("R4", 1, 10)])
    assert c_site_boundary(ph) > 0


def test_must_adjacency_checks_each_residential_cluster():
    near = Phenotype(genes=np.zeros(43), instances=[
        _instance("B0", 25, 25), _instance("R4", 35, 25)])
    with_disconnected_cluster = Phenotype(genes=np.zeros(43), instances=[
        _instance("B0", 25, 25), _instance("R4", 35, 25),
        _instance("R4", 80, 50)])
    assert c_must_adjacency(near) == 0
    assert c_must_adjacency(with_disconnected_cluster) > 0
    hard_v, feasible, detail = evaluate_constraints(with_disconnected_cluster)
    assert not feasible
    assert hard_v >= detail["must_adjacency"] > 0
    assert with_disconnected_cluster.must_shortfall == detail["must_adjacency"]


class _PairRng:
    def integers(self, *_):
        return np.array([0, 1])


def test_tournament_keeps_rank_before_crowding_or_legacy_soft_value():
    better_rank = Phenotype(genes=np.zeros(43), rank=0, soft_cv=30,
                            crowding=0, feasible=True)
    worse_rank = Phenotype(genes=np.zeros(43), rank=1, soft_cv=0,
                           crowding=float("inf"), feasible=True)
    assert binary_tournament([better_rank, worse_rank], _PairRng()) is better_rank
    worse_rank.rank = 0
    assert binary_tournament([better_rank, worse_rank], _PairRng()) is worse_rank


def test_seed_birth_generation_and_exact_genotype_replay():
    cfg = GAConfig(pop_size=20, generations=4, seed=37)
    pop, _, _ = run(cfg, verbose=False)
    assert all(p.origin_seed == 37 and 0 <= p.birth_generation <= 4 for p in pop)
    for ph in pop[:5]:
        replay = evaluate(np.array(analyze.genotype_vector(ph)))
        assert analyze.genotype_id(replay) == analyze.genotype_id(ph)
        assert np.allclose(replay.objectives, ph.objectives)
        assert np.isclose(replay.cv, ph.cv)
        assert np.isclose(replay.soft_cv, ph.soft_cv)


def test_capacity_stratum_keeps_repeatable_module_count():
    pop, _, _ = run(GAConfig(pop_size=20, generations=4, seed=8,
                             n_R4_fixed=4), verbose=False)
    assert all(p.n_R4 == 4 and len(p.by_code("R4")) == 4 for p in pop)


def test_v2_baseline_matches_each_label_to_its_rendered_manifest_record():
    rows = {r["candidate"]: r for r in _baseline_evidence()}
    assert rows["BALANCED"]["saved_gfa_m2"] == 1485
    assert rows["BALANCED"]["rendered_gfa_m2"] == 1377
    assert rows["SPECIALIZED"]["rendered_gfa_m2"] == 1055
    assert rows["CONTRASTING"]["rendered_gfa_m2"] == 1017
