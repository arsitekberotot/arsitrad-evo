"""Constrained NSGA-II driver for the site-aware v4 genotype.

Reuses the v3 operators (SBX, polynomial/reset mutation, fast nondominated
sort, crowding, constrained tournament) but runs them on the REAL site via
decode_v4 + constraints_v4 + objectives_v4. The legacy rectangle is kept only
as a regression fixture (create_legacy_site).

Provenance: algorithm [PAPER METHOD] (Deb et al. 2002); genotype→site mapping
[DESIGN HYPOTHESIS]; objective formulations [DESIGN HYPOTHESIS].
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .genotype_v4 import (
    PhenotypeV4, gene_bounds_v4, random_genome_v4, decode_v4, N_GENES_V4,
)
from .constraints_v4 import evaluate_constraints as evaluate_constraints_v4
from .objectives_v4 import evaluate_objectives as evaluate_objectives_v4
from . import nsga2
from .site import Site


@dataclass
class GAConfigV4:
    """v4 GA configuration (mirrors v3 GAConfig plus site awareness)."""
    pop_size: int = 60
    generations: int = 60
    crossover_prob: float = 0.9
    mutation_prob: float = 1.0 / N_GENES_V4
    eta_c: float = 20.0       # SBX distribution index
    eta_m: float = 20.0       # mutation distribution index
    seed: int = 42
    # capacity strata (informational; bounds already allow R4x2..R4x8)
    target_residents: Optional[int] = None
    # Experiment tier:
    #   target_day_users=None  -> Tier 1 default/reference run: full corpus
    #       program fixed present, nominal day-user capacity reported.
    #   target_day_users=int   -> Tier 2 controlled day-user scenario: public
    #       program counts become evolvable, the run is hard-capped at this
    #       stratum, and min_coverage stops the GA deleting essential program.
    target_day_users: Optional[int] = None
    min_coverage: Optional[dict] = None
    # Tier 2: seed the initial population with feasible genomes so low
    # strata are reachable (random sampling rarely lands under a low cap).
    seed_feasible: bool = False
    seed_feasible_attempts: int = 400


def evaluate_v4(genes: np.ndarray, site: Site, origin_seed: Optional[int] = None,
                birth_generation: Optional[int] = None,
                target_day_users: Optional[int] = None,
                min_coverage: Optional[dict] = None) -> PhenotypeV4:
    """Decode + evaluate a v4 genotype on the real site."""
    gid = f"s{origin_seed}" if origin_seed is not None else "g0"
    ph = decode_v4(genes, site, genotype_id=gid,
                   generation=birth_generation or 0)
    ph.origin_seed = origin_seed
    ph.birth_generation = birth_generation or 0
    ph.genes = np.asarray(genes, dtype=float).copy()

    # --- constraints (feasible / cv) -------------------------------------
    report = evaluate_constraints_v4(ph, target_day_users=target_day_users,
                                     min_coverage=min_coverage)
    ph.feasible = report.feasible
    ph.cv = float(report.total_shortfall)
    ph.constraint_report = report

    # --- objectives (store minimization-form array for NSGA-II) ----------
    ov = evaluate_objectives_v4(ph)
    ph.objective_vector = ov
    # NSGA-II minimizes: negate maximization objectives so ALL are minimized.
    arr = ov.to_array()          # value if minimize else -value
    ph.objectives = np.asarray(arr, dtype=float)
    return ph


def _constrained_dominates(a: PhenotypeV4, b: PhenotypeV4) -> bool:
    if a.feasible and not b.feasible:
        return True
    if not a.feasible and not b.feasible:
        return a.cv < b.cv
    if not a.feasible and b.feasible:
        return False
    oa = np.asarray(a.objectives)
    ob = np.asarray(b.objectives)
    return bool(np.all(oa <= ob) and np.any(oa < ob))


def _fast_nondominated_sort(pop: list[PhenotypeV4]) -> list[list[int]]:
    n = len(pop)
    S = [[] for _ in range(n)]
    dom_count = np.zeros(n, int)
    fronts = [[]]
    for p in range(n):
        for q in range(n):
            if p == q:
                continue
            if _constrained_dominates(pop[p], pop[q]):
                S[p].append(q)
            elif _constrained_dominates(pop[q], pop[p]):
                dom_count[p] += 1
        if dom_count[p] == 0:
            pop[p].rank = 0
            fronts[0].append(p)
    i = 0
    while fronts[i]:
        nxt = []
        for p in fronts[i]:
            for q in S[p]:
                dom_count[q] -= 1
                if dom_count[q] == 0:
                    pop[q].rank = i + 1
                    nxt.append(q)
        i += 1
        fronts.append(nxt)
    return fronts[:-1]


def _assign_crowding(pop: list[PhenotypeV4], front: list[int]) -> None:
    n_obj = len(pop[front[0]].objectives)
    for idx in front:
        pop[idx].crowding = 0.0
    for m in range(n_obj):
        front_sorted = sorted(front, key=lambda i: pop[i].objectives[m])
        pop[front_sorted[0]].crowding = pop[front_sorted[-1]].crowding = math.inf
        fmin = pop[front_sorted[0]].objectives[m]
        fmax = pop[front_sorted[-1]].objectives[m]
        span = (fmax - fmin) or 1e-9
        for k in range(1, len(front_sorted) - 1):
            prev_o = pop[front_sorted[k - 1]].objectives[m]
            next_o = pop[front_sorted[k + 1]].objectives[m]
            pop[front_sorted[k]].crowding += (next_o - prev_o) / span


def _crowded_better(a: PhenotypeV4, b: PhenotypeV4) -> bool:
    if a.rank != b.rank:
        return a.rank < b.rank
    return a.crowding > b.crowding


def _tournament(pop, rng) -> PhenotypeV4:
    i, j = rng.integers(0, len(pop), 2)
    a, b = pop[i], pop[j]
    if a.feasible != b.feasible:
        return a if a.feasible else b
    if not a.feasible:
        return a if a.cv < b.cv else b
    return a if _crowded_better(a, b) else b


def run_v4(site: Site, cfg: GAConfigV4 | None = None, verbose: bool = True):
    """Run constrained NSGA-II on the REAL site. Returns (pop, fronts, history)."""
    cfg = cfg or GAConfigV4()
    rng = np.random.default_rng(cfg.seed)
    # Tier 1 (target_day_users=None): fixed full corpus program.
    # Tier 2 (target_day_users=int): public program counts evolvable.
    tier2 = cfg.target_day_users is not None
    fixed_program = not tier2
    min_coverage = cfg.min_coverage
    if tier2 and min_coverage is None:
        from .constraints_v4 import MIN_FUNCTIONAL_COVERAGE
        min_coverage = MIN_FUNCTIONAL_COVERAGE

    lo, hi, is_int = gene_bounds_v4(site, fixed_program=fixed_program)
    history = {"runtime_s": 0.0, "seed": cfg.seed, "generations": [],
               "site_area_m2": site.area_m2, "site_mode": site.mode.value,
               "tier": 2 if tier2 else 1,
               "target_day_users": cfg.target_day_users}
    t0 = time.time()

    def make_genes():
        g = random_genome_v4(rng, site, fixed_program=fixed_program)
        return np.clip(g, lo, hi)

    def _ev(genes, gen):
        return evaluate_v4(genes, site, cfg.seed, gen,
                           target_day_users=cfg.target_day_users,
                           min_coverage=min_coverage)

    # --- initial population ------------------------------------------------
    # Tier 2 low strata are rarely hit by random sampling, so seed part of the
    # population with genomes that already satisfy the day-user cap. Because
    # low demand is reachable mainly through SMALL module variants, the seeding
    # biases variant-choice genes toward lower-capacity variants [DESIGN
    # HYPOTHESIS] — the GA then discovers that low strata imply compact public
    # modules, which is the architectural finding.
    def _bias_variants_low(g: np.ndarray) -> np.ndarray:
        from .genotype_v4 import (SLOT_POOL, N_GENE_STRUCT, N_V4_STRUCT,
                                  N_GENES_PER_MODULE)
        from .modules_v4 import FAMILY_VARIANTS, MODULE_LIBRARY_V4
        idx = N_GENE_STRUCT + N_V4_STRUCT
        for fam, _ord in SLOT_POOL:
            variants = FAMILY_VARIANTS.get(fam, [])
            if len(variants) > 1:
                # rank variants by day-user capacity, pick among the smaller half
                ranked = sorted(range(len(variants)),
                                key=lambda i: MODULE_LIBRARY_V4[variants[i]].capacity_day_users)
                pick = ranked[rng.integers(0, max(1, (len(ranked) + 1) // 2))]
                g[idx] = pick
            idx += N_GENES_PER_MODULE
        return g

    genes_pool: list[np.ndarray] = []
    if cfg.seed_feasible and tier2:
        seeded = 0
        for _ in range(cfg.seed_feasible_attempts):
            if seeded >= cfg.pop_size // 2:
                break
            g = _bias_variants_low(make_genes())
            ph = _ev(g, 0)
            if ph.feasible:
                genes_pool.append(g)
                seeded += 1
        if verbose:
            print(f"  [tier2 seed] {seeded} feasible seed genomes for "
                  f"day-user stratum {cfg.target_day_users}")
    while len(genes_pool) < cfg.pop_size:
        genes_pool.append(make_genes())

    pop = [_ev(genes_pool[i], 0) for i in range(cfg.pop_size)]
    for p in pop:
        p.rank = 0
        p.crowding = 0.0

    for gen in range(cfg.generations):
        fronts = _fast_nondominated_sort(pop)
        for fr in fronts:
            _assign_crowding(pop, fr)
        nfeas = sum(1 for p in pop if p.feasible)
        history["generations"].append({
            "gen": gen, "feasible": nfeas,
            "feasible_ratio": round(nfeas / len(pop), 3),
            "pareto_size": len(fronts[0]),
        })
        if verbose and gen % 10 == 0:
            print(f"  gen {gen:3d}: feasible {nfeas}/{len(pop)}  "
                  f"Pareto {len(fronts[0])}")

        offspring = []
        while len(offspring) < cfg.pop_size:
            p1 = _tournament(pop, rng)
            p2 = _tournament(pop, rng)
            c1g, c2g = nsga2.sbx(p1.genes, p2.genes, lo, hi, cfg.eta_c,
                                 cfg.crossover_prob, rng)
            c1g = nsga2.polynomial_mutation(c1g, lo, hi, cfg.eta_m,
                                            cfg.mutation_prob, rng, ~is_int)
            c2g = nsga2.polynomial_mutation(c2g, lo, hi, cfg.eta_m,
                                            cfg.mutation_prob, rng, ~is_int)
            c1g = nsga2.int_reset_mutation(c1g, lo, hi, cfg.mutation_prob,
                                           rng, is_int)
            c2g = nsga2.int_reset_mutation(c2g, lo, hi, cfg.mutation_prob,
                                           rng, is_int)
            for g in (c1g, c2g):
                g[is_int] = np.round(g[is_int])
            offspring.append(_ev(c1g, gen + 1))
            if len(offspring) < cfg.pop_size:
                offspring.append(_ev(c2g, gen + 1))

        combined = pop + offspring
        fronts = _fast_nondominated_sort(combined)
        newpop: list[PhenotypeV4] = []
        for fr in fronts:
            _assign_crowding(combined, fr)
            if len(newpop) + len(fr) <= cfg.pop_size:
                newpop.extend(combined[i] for i in fr)
            else:
                fr_sorted = sorted(fr, key=lambda i: combined[i].crowding,
                                   reverse=True)
                for i in fr_sorted:
                    if len(newpop) < cfg.pop_size:
                        newpop.append(combined[i])
                break
        pop = newpop

    history["runtime_s"] = round(time.time() - t0, 2)
    fronts = _fast_nondominated_sort(pop)
    for fr in fronts:
        _assign_crowding(pop, fr)
    return pop, fronts, history
