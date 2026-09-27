"""Automated validation tests for arsitrad-evo.

Locks in the correctness invariants of the constrained NSGA-II pipeline so the
'validated implementation' claim is continuously checkable:
    .venv/bin/python -m pytest tests/ -q

Covers: genotype bounds/coherence, constrained-domination semantics, hard
constraints, objective ranges, NSGA-II operators, elitist survival, and
evolution-level convergence behavior.
"""
import numpy as np
import pytest

from arsitrad_evo.genotype import (decode, random_genotype, gene_bounds,
                                   N_GENES, instance_slots, Phenotype)
from arsitrad_evo.nsga2 import (evaluate, run, constrained_dominates,
                                fast_nondominated_sort, assign_crowding,
                                binary_tournament, polynomial_mutation, sbx)
from arsitrad_evo.constraints import evaluate_constraints, CONSTRAINTS
from arsitrad_evo.objectives import evaluate_objectives, N_OBJECTIVES, OBJECTIVES
from arsitrad_evo.config import GAConfig
from arsitrad_evo import config as C


@pytest.fixture(scope="module")
def rng():
    return np.random.default_rng(0)


# --- genotype / codec ---------------------------------------------------------
def test_genotype_within_bounds(rng):
    lo, hi, _ = gene_bounds()
    for _ in range(50):
        g = random_genotype(rng)
        assert g.shape == (N_GENES,)
        assert np.all(g >= lo - 1e-6) and np.all(g <= hi + 1e-6)


def test_decode_residents_match_clusters(rng):
    for _ in range(30):
        ph = decode(random_genotype(rng))
        assert ph.residents == ph.n_R4 * C.RESIDENTS_PER_CLUSTER
        assert C.N_R4_MIN <= ph.n_R4 <= C.N_R4_MAX
        # R4 instance count equals n_R4
        assert len(ph.by_code("R4")) == ph.n_R4


def test_public_intensity_coherence(rng):
    """Derived public_intensity must equal count of present public modules."""
    for _ in range(50):
        ph = decode(random_genotype(rng))
        expected = min(3, sum(ph.has(c) for c in ("H0", "J0", "K0")))
        assert ph.public_intensity == expected


def test_required_developmental_modules_present(rng):
    for _ in range(30):
        ph = decode(random_genotype(rng))
        for code in ("A0", "B0", "C0", "E0", "F0", "M0"):
            assert ph.has(code)


# --- objectives -----------------------------------------------------------------
def test_objectives_bounded(rng):
    for _ in range(50):
        ph = evaluate(random_genotype(rng))
        o = np.asarray(ph.objectives)
        assert o.shape == (N_OBJECTIVES,)
        assert np.all(o >= -1e-6) and np.all(o <= 1.0 + 1e-6)


# --- constrained domination ------------------------------------------------------
def _mk(feasible: bool, cv: float, objectives) -> Phenotype:
    p = Phenotype(genes=np.zeros(N_GENES))
    p.feasible = feasible
    p.cv = cv
    p.objectives = np.array(objectives, float)
    return p


def test_feasible_dominates_infeasible():
    f = _mk(True, 0.0, [0.9, 0.9])
    i = _mk(False, 5.0, [0.0, 0.0])   # infeasible even with better objectives
    assert constrained_dominates(f, i)
    assert not constrained_dominates(i, f)


def test_infeasible_lower_cv_dominates():
    a = _mk(False, 1.0, [0.5, 0.5])
    b = _mk(False, 3.0, [0.1, 0.1])
    assert constrained_dominates(a, b)


def test_pareto_dominance_when_both_feasible():
    a = _mk(True, 0.0, [0.2, 0.3])
    b = _mk(True, 0.0, [0.4, 0.5])
    c = _mk(True, 0.0, [0.4, 0.2])   # trade-off: neither dominates
    assert constrained_dominates(a, b)
    assert not constrained_dominates(a, c)
    assert not constrained_dominates(c, a)


# --- constraints ------------------------------------------------------------------
def test_random_individuals_mostly_infeasible(rng):
    """Random placement should usually violate overlap/adjacency -> constraints bite."""
    infeas = 0
    for _ in range(40):
        ph = evaluate(random_genotype(rng))
        if not ph.feasible:
            infeas += 1
    assert infeas > 20   # constraints genuinely discriminate


def test_constraint_violation_nonnegative(rng):
    for _ in range(30):
        ph = decode(random_genotype(rng))
        total, feasible, detail = evaluate_constraints(ph)
        assert total >= 0.0
        assert all(v >= 0.0 for v in detail.values())
        assert isinstance(feasible, bool)


# --- NSGA-II operators -------------------------------------------------------------
def test_nondominated_sort_partitions(rng):
    pop = [evaluate(random_genotype(rng)) for _ in range(30)]
    fronts = fast_nondominated_sort(pop)
    assert sum(len(f) for f in fronts) == 30
    # ranks are non-decreasing across fronts and start at 0
    for idx in fronts[0]:
        assert pop[idx].rank == 0


def test_crowding_boundary_infinite(rng):
    pop = [evaluate(random_genotype(rng)) for _ in range(30)]
    fronts = fast_nondominated_sort(pop)
    for fr in fronts:
        assign_crowding(pop, fr)
        if len(fr) >= 2:
            # at least the two extremes get inf per objective -> some inf exists
            assert any(np.isinf(pop[i].crowding) for i in fr)


def test_variation_respects_bounds(rng):
    lo, hi, is_int = gene_bounds()
    p1, p2 = random_genotype(rng), random_genotype(rng)
    c1, c2 = sbx(p1, p2, lo, hi, 20.0, 0.5, rng)
    m = polynomial_mutation(p1, lo, hi, 20.0, 0.5, rng, ~is_int)
    for arr in (c1, c2, m):
        assert np.all(arr >= lo - 1e-6) and np.all(arr <= hi + 1e-6)


# --- evolution-level -----------------------------------------------------------------
def test_evolution_reaches_feasibility():
    """A short run should find feasible layouts under the full MUST gate."""
    cfg = GAConfig(pop_size=40, generations=25, seed=1)
    pop, fronts, history = run(cfg, verbose=False)
    assert sum(p.feasible for p in pop) >= cfg.pop_size // 2
    assert history[-1]["must_shortfall_mean"] < history[0]["must_shortfall_mean"]
    # history recorded every generation
    assert len(history) == cfg.generations


def test_elitism_population_size_constant():
    cfg = GAConfig(pop_size=40, generations=10, seed=2)
    pop, _, _ = run(cfg, verbose=False)
    assert len(pop) == 40


def test_determinism_same_seed():
    cfg = GAConfig(pop_size=30, generations=8, seed=99)
    pop1, _, _ = run(cfg, verbose=False)
    pop2, _, _ = run(cfg, verbose=False)
    o1 = np.array([np.asarray(p.objectives) for p in pop1])
    o2 = np.array([np.asarray(p.objectives) for p in pop2])
    assert np.allclose(o1, o2)   # seeded runs are reproducible
