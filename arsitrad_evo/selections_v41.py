"""Paper-aligned selection modes over final and all-generation Pareto sets."""
from __future__ import annotations

import math
import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage

from .objectives_v41 import OBJECTIVE_NAMES


def candidates(population):
    return [p for p in population if p.feasible and p.residents >= 8
            and p.collision_report.get("illegal_overlap_count", 0) == 0]


def unique_candidates(population):
    seen = {}
    for p in candidates(population):
        seen.setdefault(p.genotype_id, p)
    return list(seen.values())


def pareto_set(population):
    eligible = unique_candidates(population)
    if not eligible:
        return []
    X = np.asarray([p.objectives for p in eligible], dtype=float)
    front = []
    for i, p in enumerate(eligible):
        dominated = np.any(np.all(X <= X[i], axis=1)
                           & np.any(X < X[i], axis=1))
        if not dominated:
            front.append(p)
    return front


def _ranks(population):
    """Normalize per-objective fitness ranks; zero is best, one worst."""
    X = np.asarray([p.objectives for p in population], dtype=float)
    n, dimensions = X.shape
    ranks = np.zeros_like(X)
    for dimension in range(dimensions):
        order = np.argsort(X[:, dimension], kind="stable")
        for start, value in enumerate(order):
            # Stable rank; ties are corrected to their average position.
            ranks[value, dimension] = start
        for value in np.unique(X[:, dimension]):
            tied = np.flatnonzero(X[:, dimension] == value)
            ranks[tied, dimension] = np.mean(ranks[tied, dimension])
    return ranks / max(1, n - 1)


def relative_difference(population):
    """Smallest mean pairwise difference of normalized fitness ranks."""
    if not population:
        return None, {}
    ranks = _ranks(population)
    dispersion = np.mean(np.abs(ranks[:, :, None] - ranks[:, None, :]), axis=(1, 2))
    i = int(np.argmin(dispersion))
    return population[i], {"relative_rank_difference": float(dispersion[i]),
                           "normalized_fitness_ranks": dict(zip(OBJECTIVE_NAMES, ranks[i].tolist()))}


def average_fitness_rank(population):
    """Best average normalized fitness ranking, independent of dispersion."""
    if not population:
        return None, {}
    ranks = _ranks(population)
    averages = ranks.mean(axis=1)
    i = int(np.argmin(averages))
    return population[i], {"average_normalized_fitness_rank": float(averages[i]),
                           "normalized_fitness_ranks": dict(zip(OBJECTIVE_NAMES, ranks[i].tolist()))}


def _normalized_objectives(population):
    X = np.asarray([p.objectives for p in population], dtype=float)
    minimum = X.min(axis=0)
    span = X.max(axis=0) - minimum
    span[span == 0] = 1.0
    return (X - minimum) / span


def cluster_all_pareto(population, k: int | None = None):
    """Average-linkage representatives; K-means remains a separate V3 diagnostic."""
    if not population:
        return {"method": "hierarchical_average_linkage", "clusters": [],
                "comparison_to_v3_kmeans": "Different method; V3 K-means is retained as a separate diagnostic."}
    if len(population) == 1:
        return {"method": "hierarchical_average_linkage", "k": 1,
                "clusters": [{"label": 1, "size": 1, "representative": population[0].genotype_id}],
                "comparison_to_v3_kmeans": "Different method; V3 K-means is retained as a separate diagnostic."}
    X = _normalized_objectives(population)
    k = min(len(population), k or max(2, round(math.sqrt(len(population)))))
    tree = linkage(X, method="average", metric="euclidean")
    labels = fcluster(tree, t=k, criterion="maxclust")
    clusters = []
    for label in sorted(set(labels)):
        indices = np.flatnonzero(labels == label)
        center = X[indices].mean(axis=0)
        medoid = indices[int(np.argmin(np.linalg.norm(X[indices] - center, axis=1)))]
        clusters.append({"label": int(label), "size": len(indices),
                         "representative": population[int(medoid)].genotype_id})
    comparison = {"method": "V3 K-means secondary diagnostic",
                  "note": "K-means partitions around centroids; it is not equivalent to paper average-linkage clustering."}
    try:
        from sklearn.cluster import KMeans
        from sklearn.metrics import adjusted_rand_score
        unique_points = len(np.unique(X, axis=0))
        if unique_points >= len(clusters):
            km = KMeans(n_clusters=len(clusters), n_init=10, random_state=0).fit(X)
            km_reps = []
            for label in range(len(clusters)):
                indices = np.flatnonzero(km.labels_ == label)
                nearest = indices[int(np.argmin(np.linalg.norm(X[indices] - km.cluster_centers_[label], axis=1)))]
                km_reps.append(population[int(nearest)].genotype_id)
            comparison.update({"adjusted_rand_index": float(adjusted_rand_score(labels, km.labels_)),
                               "representative_overlap": len(set(km_reps) &
                                                             {x["representative"] for x in clusters}),
                               "kmeans_representatives": km_reps})
        else:
            comparison["note"] += " Too few distinct objective vectors for the same K."
    except ImportError:
        comparison["note"] += " scikit-learn unavailable."
    return {"method": "hierarchical_average_linkage", "k": len(clusters),
            "clusters": clusters, "comparison_to_v3_kmeans": comparison}


def select_v41(final_population, archive) -> dict:
    all_eligible = unique_candidates(archive)
    all_front = pareto_set(all_eligible)
    final_front = pareto_set(final_population)
    chosen = {}
    rank_details = {}
    for j, name in enumerate(OBJECTIVE_NAMES):
        if all_eligible:
            chosen[f"fittest_{name}"] = min(all_eligible, key=lambda p: p.objectives[j])
    rel, rel_detail = relative_difference(all_front)
    avg, avg_detail = average_fitness_rank(all_front)
    if rel:
        chosen["relative_difference"] = rel
        rank_details["relative_difference"] = rel_detail
    if avg:
        chosen["average_fitness_rank"] = avg
        rank_details["average_fitness_rank"] = avg_detail
    if all_front:
        chosen["architectural_balanced"] = max(all_front,
                                                key=lambda p: p.objective_vector.weighted_sum)
        chosen["all_population_pareto_representative"] = all_front[0]
    if final_front:
        chosen["final_generation_pareto_representative"] = final_front[0]
    signatures = {(tuple(sorted(p.unit_population.get("by_function", {}).items())),
                   p.packing_pattern, p.zone_state.get("type")) for p in all_eligible}
    ranks = _ranks(all_eligible) if all_eligible else np.zeros((0, len(OBJECTIVE_NAMES)))
    fitness_ranks = {ph.genotype_id: dict(zip(OBJECTIVE_NAMES, row.tolist()))
                     for ph, row in zip(all_eligible, ranks)}
    return {
        "all_population_pareto_ids": [p.genotype_id for p in all_front],
        "final_generation_pareto_ids": [p.genotype_id for p in final_front],
        "selected": {name: ph.genotype_id for name, ph in chosen.items()},
        "rank_details": rank_details,
        "fitness_ranks": fitness_ranks,
        "clustering": cluster_all_pareto(all_front),
        "eligible_count": len(all_eligible),
        "distinct_architectural_signatures": len(signatures),
        "search_space_collapse": len(signatures) < 2,
        "definition": "A signature combines function populations, grouping pattern and zone type; selected candidates must be feasible with >=8 residents and zero illegal overlap.",
    }
