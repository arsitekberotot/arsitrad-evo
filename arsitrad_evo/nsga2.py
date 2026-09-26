"""Constrained NSGA-II (Deb, Pratap, Agarwal & Meyarivan, 2002).

Faithful, transparent implementation [PAPER METHOD]:
  - fast nondominated sort (constrained domination)
  - crowding distance (boundary = inf)
  - crowded comparison operator
  - binary tournament selection
  - SBX crossover (real) + uniform crossover (int)
  - polynomial mutation (real) + random-reset mutation (int)
  - (mu + lambda) elitist survival
Hard constraints handled by CONSTRAINED DOMINATION: feasible always dominates
infeasible; among infeasible, smaller constraint violation wins.
"""
from __future__ import annotations
import numpy as np

from .genotype import Phenotype, decode, random_genotype, gene_bounds, N_GENES
from .objectives import evaluate_objectives, N_OBJECTIVES
from .constraints import evaluate_constraints
from .config import GAConfig


# ---------------------------------------------------------------------------
# Constrained domination (Deb 2002, Definition 1 / constrained approach)
# ---------------------------------------------------------------------------
def constrained_dominates(a: Phenotype, b: Phenotype) -> bool:
    """True if a constrained-dominates b."""
    if a.feasible and not b.feasible:
        return True
    if not a.feasible and not b.feasible:
        return a.cv < b.cv
    if not a.feasible and b.feasible:
        return False
    # both feasible: standard Pareto dominance on (minimised) objectives
    oa = np.asarray(a.objectives)
    ob = np.asarray(b.objectives)
    return bool(np.all(oa <= ob) and np.any(oa < ob))


# ---------------------------------------------------------------------------
# Fast nondominated sort  [PAPER METHOD]
# ---------------------------------------------------------------------------
def fast_nondominated_sort(pop: list[Phenotype]) -> list[list[int]]:
    n = len(pop)
    S = [[] for _ in range(n)]      # solutions dominated by p
    dom_count = np.zeros(n, int)    # number dominating p
    fronts = [[]]
    for p in range(n):
        for q in range(n):
            if p == q:
                continue
            if constrained_dominates(pop[p], pop[q]):
                S[p].append(q)
            elif constrained_dominates(pop[q], pop[p]):
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


# ---------------------------------------------------------------------------
# Crowding distance  [PAPER METHOD]
# ---------------------------------------------------------------------------
def assign_crowding(pop: list[Phenotype], front: list[int]) -> None:
    if not front:
        return
    for idx in front:
        pop[idx].crowding = 0.0
    M = N_OBJECTIVES
    objs = {i: np.asarray(pop[i].objectives) for i in front}
    for m in range(M):
        front_sorted = sorted(front, key=lambda i: objs[i][m])
        pop[front_sorted[0]].crowding = np.inf
        pop[front_sorted[-1]].crowding = np.inf
        fmin = objs[front_sorted[0]][m]
        fmax = objs[front_sorted[-1]][m]
        rng = (fmax - fmin) or 1e-12
        for k in range(1, len(front_sorted) - 1):
            prev_o = objs[front_sorted[k - 1]][m]
            next_o = objs[front_sorted[k + 1]][m]
            pop[front_sorted[k]].crowding += (next_o - prev_o) / rng


def crowded_better(a: Phenotype, b: Phenotype) -> bool:
    """Crowded comparison operator: lower rank; tie -> larger crowding distance;
    final tie -> smaller soft_cv (MUST-adjacency) so satisfied MUST relations
    break ties among otherwise-equivalent feasible solutions (Campaign v2)."""
    if a.rank != b.rank:
        return a.rank < b.rank
    if a.crowding != b.crowding:
        return a.crowding > b.crowding
    return a.soft_cv < b.soft_cv


# ---------------------------------------------------------------------------
# Variation operators (mixed real/integer)
# ---------------------------------------------------------------------------
def binary_tournament(pop, rng) -> Phenotype:
    i, j = rng.integers(0, len(pop), 2)
    a, b = pop[i], pop[j]
    if a.feasible != b.feasible:
        return a if a.feasible else b
    if not a.feasible:
        return a if a.cv < b.cv else b
    # both feasible: neither dominates in 9-objective space (dilution makes this
    # the common case). Use soft MUST-adjacency as the feasibility-preserving
    # discriminator so satisfied MUST relations genuinely influence selection
    # (Campaign v2 fix). Only when soft_cv is ~equal do we fall back to crowded
    # comparison (rank/crowding) to preserve diversity.
    if abs(a.soft_cv - b.soft_cv) > 1e-6:
        return a if a.soft_cv < b.soft_cv else b
    return a if crowded_better(a, b) else b


def sbx(p1, p2, lo, hi, eta, pc, rng):
    """Simulated Binary Crossover for real genes."""
    c1, c2 = p1.copy(), p2.copy()
    for k in range(len(p1)):
        if rng.random() > pc:
            continue
        y1, y2 = min(p1[k], p2[k]), max(p1[k], p2[k])
        if abs(y1 - y2) < 1e-14:
            continue
        rand = rng.random()
        beta = 1.0 + 2.0 * (y1 - lo[k]) / (y2 - y1)
        alpha = 2.0 - beta ** -(eta + 1)
        betaq = (rand * alpha) ** (1 / (eta + 1)) if rand <= 1 / alpha \
            else (1 / (2 - rand * alpha)) ** (1 / (eta + 1))
        child1 = 0.5 * ((y1 + y2) - betaq * (y2 - y1))
        beta = 1.0 + 2.0 * (hi[k] - y2) / (y2 - y1)
        alpha = 2.0 - beta ** -(eta + 1)
        betaq = (rand * alpha) ** (1 / (eta + 1)) if rand <= 1 / alpha \
            else (1 / (2 - rand * alpha)) ** (1 / (eta + 1))
        child2 = 0.5 * ((y1 + y2) + betaq * (y2 - y1))
        if rng.random() < 0.5:
            c1[k], c2[k] = child2, child1
        else:
            c1[k], c2[k] = child1, child2
    return c1, c2


def uniform_crossover(p1, p2, mask_int, rng):
    c1, c2 = p1.copy(), p2.copy()
    swap = (rng.random(len(p1)) < 0.5) & mask_int
    c1[swap], c2[swap] = p2[swap], p1[swap]
    return c1, c2


def polynomial_mutation(x, lo, hi, eta, pm, rng, mask_real):
    y = x.copy()
    for k in np.where(mask_real)[0]:
        if rng.random() >= pm:
            continue
        d1 = (x[k] - lo[k]) / (hi[k] - lo[k])
        d2 = (hi[k] - x[k]) / (hi[k] - lo[k])
        rand = rng.random()
        mut_pow = 1.0 / (eta + 1.0)
        if rand < 0.5:
            xy = 1.0 - d1
            val = 2.0 * rand + (1.0 - 2.0 * rand) * (xy ** (eta + 1))
            dq = val ** mut_pow - 1.0
        else:
            xy = 1.0 - d2
            val = 2.0 * (1.0 - rand) + 2.0 * (rand - 0.5) * (xy ** (eta + 1))
            dq = 1.0 - val ** mut_pow
        y[k] = np.clip(x[k] + dq * (hi[k] - lo[k]), lo[k], hi[k])
    return y


def int_reset_mutation(x, lo, hi, pm, rng, mask_int):
    y = x.copy()
    for k in np.where(mask_int)[0]:
        if rng.random() < pm:
            y[k] = np.round(lo[k] + (hi[k] - lo[k]) * rng.random())
    return y


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------
def evaluate(genes: np.ndarray) -> Phenotype:
    ph = decode(genes)
    evaluate_constraints(ph)
    evaluate_objectives(ph)
    return ph


# ---------------------------------------------------------------------------
# Main NSGA-II loop  [PAPER METHOD]
# ---------------------------------------------------------------------------
def run(cfg: GAConfig | None = None, verbose: bool = True):
    cfg = cfg or GAConfig()
    rng = np.random.default_rng(cfg.seed)
    lo, hi, is_int = gene_bounds()
    mask_int = is_int
    mask_real = ~is_int
    pm = cfg.mutation_prob if cfg.mutation_prob is not None else 1.0 / N_GENES

    # 1. randomized initial population
    pop = [evaluate(random_genotype(rng)) for _ in range(cfg.pop_size)]
    history = []

    for gen in range(cfg.generations):
        fronts = fast_nondominated_sort(pop)
        for fr in fronts:
            assign_crowding(pop, fr)

        # offspring
        offspring = []
        while len(offspring) < cfg.pop_size:
            p1 = binary_tournament(pop, rng)
            p2 = binary_tournament(pop, rng)
            if rng.random() < cfg.crossover_prob:
                # real genes: SBX ; int genes: uniform
                r1, r2 = sbx(p1.genes, p2.genes, lo, hi, cfg.sbx_eta, 0.5, rng)
                i1, i2 = uniform_crossover(p1.genes, p2.genes, mask_int, rng)
                c1 = np.where(mask_int, i1, r1)
                c2 = np.where(mask_int, i2, r2)
            else:
                c1, c2 = p1.genes.copy(), p2.genes.copy()
            c1 = int_reset_mutation(polynomial_mutation(c1, lo, hi, cfg.poly_eta, pm, rng, mask_real),
                                    lo, hi, pm, rng, mask_int)
            c2 = int_reset_mutation(polynomial_mutation(c2, lo, hi, cfg.poly_eta, pm, rng, mask_real),
                                    lo, hi, pm, rng, mask_int)
            c1 = np.clip(c1, lo, hi); c2 = np.clip(c2, lo, hi)
            offspring.append(evaluate(c1))
            if len(offspring) < cfg.pop_size:
                offspring.append(evaluate(c2))

        # (mu + lambda) elitist survival
        combined = pop + offspring
        fronts = fast_nondominated_sort(combined)
        newpop, fi = [], 0
        while fi < len(fronts) and len(newpop) + len(fronts[fi]) <= cfg.pop_size:
            assign_crowding(combined, fronts[fi])
            newpop += [combined[i] for i in fronts[fi]]
            fi += 1
        if len(newpop) < cfg.pop_size and fi < len(fronts):
            assign_crowding(combined, fronts[fi])
            # crowding primary, soft MUST-adjacency secondary (Campaign v2) so
            # satisfied MUST relations survive truncation of the last front.
            rest = sorted(fronts[fi],
                          key=lambda i: (combined[i].crowding, -combined[i].soft_cv),
                          reverse=True)
            newpop += [combined[i] for i in rest[: cfg.pop_size - len(newpop)]]
        pop = newpop

        feas = sum(1 for p in pop if p.feasible)
        rank1 = sum(1 for p in pop if p.rank == 0)
        soft = float(np.mean([p.soft_cv for p in pop])) if pop else 0.0
        history.append({"gen": gen, "feasible": feas, "rank1": rank1,
                        "soft_cv_mean": round(soft, 4)})
        if verbose and (gen % 10 == 0 or gen == cfg.generations - 1):
            print(f"gen {gen:3d} | feasible {feas:3d}/{len(pop)} | rank1 {rank1:3d}")

    # final sort for output
    fronts = fast_nondominated_sort(pop)
    for fr in fronts:
        assign_crowding(pop, fr)
    return pop, fronts, history
