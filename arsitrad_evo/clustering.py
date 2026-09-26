"""K-means post-processing: cluster Pareto-optimal phenotypes into families.

POST-PROCESSING ONLY — clustering never feeds back into NSGA-II selection.
Determines k by BOTH silhouette and elbow (inertia) analysis, then selects
representative phenotypes as cluster medoids PLUS preserved objective-extreme
solutions.
"""
from __future__ import annotations
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from .genotype import Phenotype
from .config import ClusterConfig
from .objectives import OBJECTIVES

OBJ_NAMES = [n for n, _ in OBJECTIVES]


def embed(phenos: list[Phenotype], use_genes: bool = False) -> np.ndarray:
    X = np.array([np.asarray(p.objectives) for p in phenos], dtype=float)
    if use_genes:
        G = np.array([p.genes for p in phenos], dtype=float)
        G = (G - G.mean(0)) / (G.std(0) + 1e-9)
        X = np.hstack([X, G])
    return X


def k_analysis(X: np.ndarray, k_min: int, k_max: int, seed: int):
    """Run KMeans over k range; return per-k inertia (elbow) and silhouette."""
    ks, inertias, sils = [], [], []
    for k in range(max(2, k_min), min(k_max, len(X) - 1) + 1):
        km = KMeans(n_clusters=k, n_init="auto", random_state=seed)
        lab = km.fit_predict(X)
        ks.append(k)
        inertias.append(float(km.inertia_))
        sils.append(float(silhouette_score(X, lab)) if len(set(lab.tolist())) > 1 else 0.0)
    return ks, inertias, sils


def choose_k(ks, inertias, sils):
    """Pick k = argmax silhouette; report elbow k as secondary evidence."""
    if not ks:
        return 1, 1
    best_sil = ks[int(np.argmax(sils))]
    x = np.array(ks, float); y = np.array(inertias, float)
    p1, p2 = np.array([x[0], y[0]]), np.array([x[-1], y[-1]])
    v = p2 - p1
    denom = np.linalg.norm(v) or 1e-9
    dists = []
    for xi, yi in zip(x, y):
        w = np.array([xi, yi]) - p1
        cross2d = abs(v[0] * w[1] - v[1] * w[0])   # 2D cross product magnitude
        dists.append(cross2d / denom)
    elbow = ks[int(np.argmax(dists))]
    return best_sil, elbow


def cluster_pareto(phenos: list[Phenotype], cfg: ClusterConfig | None = None):
    """Cluster feasible rank-1 phenotypes.

    Returns dict: k (silhouette), k_elbow, labels, medoid indices, extreme
    indices, representative Phenotypes (medoids + extremes), analysis curves.
    """
    cfg = cfg or ClusterConfig()
    feas = [p for p in phenos if p.feasible and p.rank == 0]
    if len(feas) < 3:
        return {"k": 0, "representatives": feas, "clustered": feas,
                "note": "too few feasible Pareto solutions", "labels": [],
                "ks": [], "inertias": [], "silhouettes": []}

    X = embed(feas, cfg.use_genes)
    ks, inertias, sils = k_analysis(X, cfg.k_min, cfg.k_max, cfg.random_state)
    k, k_elbow = choose_k(ks, inertias, sils)

    km = KMeans(n_clusters=k, n_init="auto", random_state=cfg.random_state)
    labels = np.asarray(km.fit_predict(X))
    centres = np.asarray(km.cluster_centers_)

    medoids = []
    for c in range(k):
        idxs = np.where(labels == c)[0]
        centre = centres[c]
        med = idxs[int(np.argmin(np.linalg.norm(X[idxs] - centre, axis=1)))]
        medoids.append(int(med))

    extremes = sorted({int(np.argmin(X[:, m])) for m in range(X.shape[1])})

    rep_idx = sorted(set(medoids) | set(extremes))
    reps = [feas[i] for i in rep_idx]
    return {
        "k": int(k), "k_elbow": int(k_elbow),
        "silhouette": float(max(sils) if sils else 0.0),
        "labels": labels.tolist(), "medoids": medoids, "extremes": extremes,
        "rep_indices": rep_idx, "representatives": reps, "clustered": feas,
        "ks": ks, "inertias": inertias, "silhouettes": sils,
    }
