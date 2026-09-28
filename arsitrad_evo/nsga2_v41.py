"""Constrained NSGA-II with a persistent all-generation V4.1 archive."""
from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

from . import nsga2
from .constraints_v41 import evaluate_constraints_v41
from .objectives_v41 import evaluate_objectives_v41
from .pipeline_v41 import (N_GENES_V41, HEADER, PER_SLOT, SLOT_POOL, FAMILIES,
                           decode_v41, gene_bounds_v41, random_genome_v41)
from .nsga2_v4 import _fast_nondominated_sort, _assign_crowding, _tournament
from .site import Site


@dataclass(frozen=True)
class GAConfigV41:
    pop_size: int = 36
    generations: int = 20
    seed: int = 42
    concurrent_day_users: int = 32
    target_residents: int | None = None
    crossover_prob: float = 0.9
    mutation_prob: float = 0.025
    eta_c: float = 20.0
    eta_m: float = 20.0


def evaluate_v41(genes, site: Site, cfg: GAConfigV41,
                 birth_generation: int = 0):
    ph = decode_v41(genes, site, cfg.concurrent_day_users, birth_generation, cfg.seed)
    ph.selected_generation = 0 if birth_generation == 0 else None
    report = evaluate_constraints_v41(ph, cfg.concurrent_day_users, cfg.target_residents)
    ph.constraint_report = report
    ph.feasible = report.feasible
    ph.cv = report.total_shortfall
    vector = evaluate_objectives_v41(ph)
    ph.objective_vector = vector
    ph.objectives = vector.to_array()
    ph.stage_records.append({"stage": "constraint_evaluation",
                             "inputs": ["phenotype", "collision_state", "occupancy_scenario"],
                             "outputs": ["feasible", "constraint_report"],
                             "provenance": "[DESIGN HYPOTHESIS]",
                             "data": {"feasible": ph.feasible, "hard_violations": report.hard_violations}})
    return ph


def run_v41(site: Site, cfg: GAConfigV41 = GAConfigV41(), verbose: bool = False):
    """Return (final population, fronts, history, every evaluated phenotype)."""
    if cfg.pop_size < 4 or cfg.generations < 1:
        raise ValueError("At least four individuals and one generation are required")
    rng = np.random.default_rng(cfg.seed)
    lo, hi, is_int = gene_bounds_v41(site)
    archive = []
    started = time.time()

    def evaluate(genes, generation):
        ph = evaluate_v41(genes, site, cfg, generation)
        ph.archive_index = len(archive)
        archive.append(ph)
        return ph

    def initial_genes():
        genes = random_genome_v41(rng, site)
        if cfg.target_residents is not None and cfg.target_residents % 4 == 0:
            genes[FAMILIES.index("R4")] = cfg.target_residents // 4
            # Seed a known-capacity path. Mutation can still introduce the
            # six-resident R4 variant and test the stratum boundary.
            from .modules_v4 import FAMILY_VARIANTS, MODULE_LIBRARY_V4
            r4_variants = FAMILY_VARIANTS["R4"]
            four_person = [j for j, code in enumerate(r4_variants)
                           if MODULE_LIBRARY_V4[code].capacity_residents == 4]
            for slot, (family, _) in enumerate(SLOT_POOL):
                if family == "R4":
                    genes[HEADER + slot * PER_SLOT] = int(rng.choice(four_person))
        return genes

    pop = [evaluate(initial_genes(), 0) for _ in range(cfg.pop_size)]
    history = {"seed": cfg.seed, "pop_size": cfg.pop_size,
               "generations_requested": cfg.generations,
               "concurrent_day_users": cfg.concurrent_day_users,
               "target_residents": cfg.target_residents,
               "generation_rows": [], "runtime_s": 0.0}
    for generation in range(cfg.generations):
        fronts = _fast_nondominated_sort(pop)
        for front in fronts:
            _assign_crowding(pop, front)
        feasible = [p for p in pop if p.feasible]
        signatures = {(tuple(sorted(p.unit_population.get("by_function", {}).items())),
                       p.packing_pattern, p.zone_state.get("type")) for p in feasible}
        history["generation_rows"].append({
            "generation": generation,
            "feasible": len(feasible),
            "feasible_ratio": len(feasible) / cfg.pop_size,
            "final_front_size": len(fronts[0]),
            "distinct_architectural_signatures": len(signatures),
            "mean_residents": float(np.mean([p.residents for p in pop])),
        })
        if verbose and generation % 5 == 0:
            print(f"  gen {generation:2d}: feasible {len(feasible)}/{cfg.pop_size}, "
                  f"distinct {len(signatures)}, front {len(fronts[0])}")
        offspring = []
        while len(offspring) < cfg.pop_size:
            p1 = _tournament(pop, rng)
            p2 = _tournament(pop, rng)
            g1, g2 = nsga2.sbx(p1.genes, p2.genes, lo, hi, cfg.eta_c,
                               cfg.crossover_prob, rng)
            for genes in (g1, g2):
                genes = nsga2.polynomial_mutation(genes, lo, hi, cfg.eta_m,
                                                   cfg.mutation_prob, rng, ~is_int)
                genes = nsga2.int_reset_mutation(genes, lo, hi,
                                                 cfg.mutation_prob, rng, is_int)
                genes[is_int] = np.round(genes[is_int])
                offspring.append(evaluate(genes, generation + 1))
                if len(offspring) == cfg.pop_size:
                    break
        combined = pop + offspring
        fronts = _fast_nondominated_sort(combined)
        new_pop = []
        for front in fronts:
            _assign_crowding(combined, front)
            if len(new_pop) + len(front) <= cfg.pop_size:
                new_pop.extend(combined[i] for i in front)
            else:
                front = sorted(front, key=lambda i: combined[i].crowding, reverse=True)
                new_pop.extend(combined[i] for i in front[:cfg.pop_size - len(new_pop)])
                break
        pop = new_pop
        for individual in pop:
            individual.selected_generation = generation + 1
    fronts = _fast_nondominated_sort(pop)
    for front in fronts:
        _assign_crowding(pop, front)
    history["runtime_s"] = round(time.time() - started, 2)
    history["archive_count"] = len(archive)
    history["final_feasible"] = sum(p.feasible for p in pop)
    return pop, fronts, history, archive
