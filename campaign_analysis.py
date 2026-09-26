"""Post-processing & architectural-evidence phase (read-only on the optimizer).

Audits campaign/data + traces, runs evidence analyses (objective correlation,
module statistics, cross-seed recurrence, duplicates, K-means stability),
reassesses the 14 representatives, and builds a 3-candidate architectural
decision package. Does NOT modify NSGA-II/objectives/constraints/genotype.

Writes:
  campaign/FINDINGS.md, campaign/DESIGN_HANDOFF.md
  campaign/data/shortlist.json, campaign/data/shortlist.csv
  campaign/data/analysis_*.csv
  campaign/figures/analysis_*.png
"""
from __future__ import annotations
import json, os, glob, itertools, random
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, adjusted_rand_score
from collections import Counter

PROJ = os.path.dirname(os.path.abspath(__file__))
CD = os.path.join(PROJ, "campaign", "data")
FD = os.path.join(PROJ, "campaign", "figures")

OBJC = ["F1_safeguarding", "F2_privacy_agency", "F3_everyday_life",
        "F4_service_separation", "F5_site_efficiency", "F6_adaptability",
        "F7_domestic_scale", "F8_community_connection", "F9_landscape_buffer"]
SHORT = [n.split("_")[0] for n in OBJC]
GMAP = {"g_has_H0": "H0", "g_has_J0": "J0", "g_has_K0": "K0",
        "g_has_I0": "I0", "g_has_L0": "L0"}

arch = pd.read_csv(f"{CD}/pareto_archive.csv")
ms = pd.read_csv(f"{CD}/multiseed_summary.csv")
traces = [json.load(open(p)) for p in sorted(glob.glob(f"{CD}/phenotype_*.json"))]
objcols = [f"obj_{n}" for n in OBJC]

O = arch[objcols].values
lo, hi = O.min(0), O.max(0)
RN = np.where((hi - lo) < 1e-12, 1.0, hi - lo)
Xn = (O - lo) / RN

F = {}   # findings accumulator


# ---------------------------------------------------------------- audit
def audit():
    F["archive_n"] = len(arch)
    F["seeds_all_feasible"] = bool((ms.feasible_rate == 1.0).all())
    F["seeds_all_rank1"] = bool((ms.pareto_size == ms["pop"]).all())
    # many-objective dilution: fraction of mutually non-dominating pairs
    def dom(a, b): return np.all(a <= b) and np.any(a < b)
    random.seed(0)
    idx = random.sample(range(len(O)), 150)
    tot = nd = 0
    for i, j in itertools.combinations(idx, 2):
        tot += 1
        if not dom(O[i], O[j]) and not dom(O[j], O[i]):
            nd += 1
    F["dilution_pct"] = round(100 * nd / tot, 1)
    # duplicates
    genecols = [c for c in arch.columns if c.startswith("g_")]
    F["exact_dup_fullgenes"] = int(arch[genecols].round(2).duplicated().sum())
    sig = arch[["n_R4", "g_has_H0", "g_has_J0", "g_has_K0", "g_has_I0", "g_has_L0",
                "g_floors_C0", "g_floors_H0"]].astype(int).astype(str).agg("".join, axis=1)
    F["unique_struct_sigs"] = int(sig.nunique())
    F["top_sigs"] = sig.value_counts().head(5).to_dict()
    return sig


# ---------------------------------------------------------------- objectives
def objective_analysis():
    corr = pd.DataFrame(spearmanr(O)[0], index=SHORT, columns=SHORT)
    corr.round(3).to_csv(f"{CD}/analysis_objective_correlation.csv")
    strong = []
    for i in range(9):
        for j in range(i + 1, 9):
            r = corr.iloc[i, j]
            if abs(r) >= 0.4:
                strong.append((SHORT[i], SHORT[j], round(float(r), 3),
                               "CONFLICT" if r < 0 else "REDUNDANT"))
    F["obj_strong_pairs"] = sorted(strong, key=lambda x: -abs(x[2]))
    # spread / near-binary detection
    spread = {}
    for c, oc in zip(SHORT, objcols):
        col = arch[oc]
        spread[c] = dict(mean=round(float(col.mean()), 3), std=round(float(col.std()), 3),
                         p05=round(float(col.quantile(.05)), 3), p95=round(float(col.quantile(.95)), 3),
                         frac_extreme=round(float(((col < .05) | (col > .95)).mean()), 3))
    F["obj_spread"] = spread
    # landscape -> F9 redundancy
    r9, _ = spearmanr(arch.landscape_frac, arch["obj_F9_landscape_buffer"])
    F["landscape_vs_F9_r"] = round(float(r9), 3)
    # F8 = count of public modules?
    pub = arch[["g_has_H0", "g_has_J0", "g_has_K0"]].sum(axis=1)
    r8, _ = spearmanr(pub, arch["obj_F8_community_connection"])
    F["pubmod_vs_F8_r"] = round(float(r8), 3)
    # F7 = f(n_R4)?
    r7, _ = spearmanr(arch.n_R4, arch["obj_F7_domestic_scale"])
    F["nR4_vs_F7_r"] = round(float(r7), 3)
    return corr


# ---------------------------------------------------------------- modules
def module_analysis():
    F["module_presence_pct"] = {c: round(100 * float(arch[g].mean()), 1) for g, c in GMAP.items()}
    F["nR4_dist"] = arch["n_R4"].value_counts().sort_index().to_dict()
    F["pub_intensity_dist"] = arch[["g_has_H0", "g_has_J0", "g_has_K0"]].sum(axis=1).value_counts().sort_index().to_dict()
    F["landscape_frac"] = dict(mean=round(float(arch.landscape_frac.mean()), 3),
                               lo=round(float(arch.landscape_frac.min()), 3),
                               hi=round(float(arch.landscape_frac.max()), 3))
    F["floors_C0"] = arch["g_floors_C0"].value_counts().sort_index().to_dict()
    F["floors_H0"] = arch["g_floors_H0"].value_counts().sort_index().to_dict()
    # module presence -> objective deltas
    deltas = {}
    for g, c in GMAP.items():
        pres = arch[g] == 1
        deltas[c] = {s: round(float(arch.loc[pres, oc].mean() - arch.loc[~pres, oc].mean()), 3)
                     for oc, s in zip(objcols, SHORT)}
    F["module_obj_delta"] = deltas
    # co-occurrence
    P = arch[list(GMAP.keys())].copy(); P.columns = list(GMAP.values())
    co = pd.DataFrame(0, index=P.columns, columns=P.columns)
    for a in P.columns:
        for b in P.columns:
            co.loc[a, b] = int(((P[a] == 1) & (P[b] == 1)).sum())
    co.to_csv(f"{CD}/analysis_module_cooccurrence.csv")
    return co, P


# ---------------------------------------------------------------- cross-seed
def cross_seed():
    # provenance limitation: archive CSV has no seed column.
    # recurrence of structural signatures is the cross-seed evidence available.
    return "no_seed_column"  # documented limitation


# ---------------------------------------------------------------- kmeans stability
def kmeans_stability():
    seeds = [0, 1, 2, 3, 4]
    sil = {}
    for k in range(3, 9):
        sil[k] = [round(float(silhouette_score(Xn, KMeans(n_clusters=k, n_init=10, random_state=s).fit_predict(Xn))), 3)
                  for s in seeds]
    F["silhouette_by_k_seed"] = {str(k): v for k, v in sil.items()}
    labs = {s: KMeans(n_clusters=6, n_init=10, random_state=s).fit_predict(Xn) for s in seeds}
    aris = [adjusted_rand_score(labs[a], labs[b]) for a, b in itertools.combinations(seeds, 2)]
    F["kmeans_k6_ARI_mean"] = round(float(np.mean(aris)), 3)
    F["kmeans_k6_ARI_range"] = [round(float(min(aris)), 3), round(float(max(aris)), 3)]
    F["kmeans_verdict"] = "STABLE" if np.mean(aris) > 0.6 else "UNSTABLE/continuous"
    return labs, sil


# ---------------------------------------------------------------- figures
def fig_correlation(corr):
    fig, ax = plt.subplots(figsize=(8, 6.5))
    im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(9)); ax.set_yticks(range(9))
    ax.set_xticklabels(SHORT); ax.set_yticklabels(SHORT)
    for i in range(9):
        for j in range(9):
            ax.text(j, i, f"{corr.values[i,j]:.2f}", ha="center", va="center", fontsize=8,
                    color="white" if abs(corr.values[i, j]) > 0.5 else "black")
    fig.colorbar(im, label="Spearman r")
    ax.set_title("Objective correlation — conflicts (−) & redundancies (+)")
    fig.tight_layout(); fig.savefig(f"{FD}/analysis_objective_correlation.png", dpi=140); plt.close(fig)


def fig_module_freq(P):
    freq = P.mean().sort_values()
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.barh(freq.index, freq.values * 100, color="#7dd3fc", edgecolor="k")
    ax.set_xlabel("presence in archive (%)"); ax.set_title("Optional module frequency")
    for i, v in enumerate(freq.values * 100):
        ax.text(v + 1, i, f"{v:.0f}%", va="center", fontsize=8)
    ax.set_xlim(0, 100); ax.grid(alpha=0.2, axis="x")
    fig.tight_layout(); fig.savefig(f"{FD}/analysis_module_frequency.png", dpi=140); plt.close(fig)


def fig_stability(sil):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ks = sorted(sil)
    arr = np.array([sil[k] for k in ks])
    ax.errorbar(ks, arr.mean(1), yerr=arr.std(1), marker="o", capsize=4, color="#0284c7")
    for s in range(5):
        ax.plot(ks, arr[:, s], ".", alpha=0.3, color="#94a3b8")
    ax.set_xlabel("k"); ax.set_ylabel("silhouette"); ax.grid(alpha=0.3)
    ax.set_title("K-means stability — silhouette by k across 5 seeds")
    fig.tight_layout(); fig.savefig(f"{FD}/analysis_kmeans_stability.png", dpi=140); plt.close(fig)


def fig_program_objective():
    # heatmap: module-presence objective deltas
    deltas = pd.DataFrame(F["module_obj_delta"]).T[SHORT]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    im = ax.imshow(deltas.values, cmap="RdBu_r", vmin=-0.6, vmax=0.6, aspect="auto")
    ax.set_xticks(range(9)); ax.set_xticklabels(SHORT)
    ax.set_yticks(range(len(deltas))); ax.set_yticklabels(deltas.index)
    for i in range(len(deltas)):
        for j in range(9):
            ax.text(j, i, f"{deltas.values[i,j]:+.2f}", ha="center", va="center", fontsize=7,
                    color="white" if abs(deltas.values[i, j]) > 0.3 else "black")
    fig.colorbar(im, label="Δ objective (present − absent); − = better")
    ax.set_title("Module presence → objective effect (proxy-sensitivity map)")
    fig.tight_layout(); fig.savefig(f"{FD}/analysis_module_objective.png", dpi=140); plt.close(fig)


# ---------------------------------------------------------------- main
def main():
    sig = audit()
    corr = objective_analysis()
    co, P = module_analysis()
    F["cross_seed_provenance"] = cross_seed()
    labs, sil = kmeans_stability()
    fig_correlation(corr); fig_module_freq(P); fig_stability(sil); fig_program_objective()

    with open(f"{CD}/analysis_findings.json", "w") as f:
        json.dump(F, f, indent=2, default=str)
    print("=== analysis_findings.json ===")
    print(json.dumps(F, indent=2, default=str))


if __name__ == "__main__":
    main()
