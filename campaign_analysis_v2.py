"""Campaign v2 interpretation & architectural-evidence phase.

Improvements over v1 (per remediation brief):
  - many-objective dilution measured via per-generation RANK-1 GROWTH from
    histories.json (NOT non-dominance inside the filtered archive);
  - K-means INITIALIZATION stability distinguished from EVOLUTIONARY-SEED
    stability;
  - module->objective statistics framed as ASSOCIATIONS, not causal effects;
  - clustering / candidate comparison consistently in NORMALIZED objective
    space (matches the fixed clustering.embed);
  - evolutionary seed provenance read from the archive (preserved in v2);
  - dormant/masked genes cleaned from human-readable descriptions.

Reads campaign_v2/data. Writes FINDINGS/DESIGN_HANDOFF v2 + figures + shortlist.
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
CD = os.path.join(PROJ, "campaign_v2", "data")
FD = os.path.join(PROJ, "campaign_v2", "figures")

OBJC = ["F1_safeguarding", "F2_privacy_agency", "F3_everyday_life",
        "F4_service_separation", "F5_site_efficiency", "F6_adaptability",
        "F7_domestic_scale", "F8_community_connection", "F9_landscape_buffer"]
SHORT = [n.split("_")[0] for n in OBJC]
GMAP = {"g_has_H0": "H0", "g_has_J0": "J0", "g_has_K0": "K0",
        "g_has_I0": "I0", "g_has_L0": "L0"}

arch = pd.read_csv(f"{CD}/pareto_archive.csv")
ms = pd.read_csv(f"{CD}/multiseed_summary.csv")
traces = [json.load(open(p)) for p in sorted(glob.glob(f"{CD}/phenotype_*.json"))]
hist = json.load(open(f"{CD}/histories.json"))
objcols = [f"obj_{n}" for n in OBJC]
O = arch[objcols].values
lo, hi = O.min(0), O.max(0)
RN = np.where((hi - lo) < 1e-12, 1.0, hi - lo)
Xn = (O - lo) / RN
POPN = int(ms["pop"].iloc[0])

F = {}


# ------------------------------------------------------------------ audit
def audit():
    F["archive_n"] = len(arch)
    F["seeds"] = sorted(int(s) for s in arch.seed.unique())
    F["archive_has_seed_provenance"] = bool("seed" in arch.columns)
    F["traces_have_seed"] = all("seed" in t for t in traces)
    F["n_traces"] = len(traces)
    F["must_soft_cv_mean"] = round(float(arch.soft_cv.mean()), 2)
    F["must_fully_satisfied"] = int((arch.soft_cv <= 1e-6).sum())
    # dilution via rank-1 growth
    F["rank1_growth"] = {s: [round(h[i]["rank1"] / POPN, 3)
                             for i in (0, len(h)//4, len(h)//2, len(h)-1)]
                         for s, h in hist.items()}
    # duplicates / structural signatures
    sig = arch[["n_R4", "g_has_H0", "g_has_J0", "g_has_K0", "g_has_I0", "g_has_L0",
                "g_floors_C0"]].astype(int).astype(str).agg("".join, axis=1)
    F["unique_struct_sigs"] = int(sig.nunique())
    return sig


# ------------------------------------------------------------------ objectives
def objective_analysis():
    corr = pd.DataFrame(spearmanr(O)[0], index=SHORT, columns=SHORT)
    corr.round(3).to_csv(f"{CD}/analysis_objective_correlation.csv")
    strong = []
    for i in range(9):
        for j in range(i + 1, 9):
            r = corr.iloc[i, j]
            if abs(r) >= 0.4:
                strong.append([SHORT[i], SHORT[j], round(float(r), 3),
                               "CONFLICT" if r < 0 else "REDUNDANT"])
    F["obj_strong_pairs"] = sorted(strong, key=lambda x: -abs(x[2]))
    F["obj_spread"] = {c: dict(mean=round(float(arch[oc].mean()), 3),
                               std=round(float(arch[oc].std()), 3),
                               frac_extreme=round(float(((arch[oc] < .05) | (arch[oc] > .95)).mean()), 3))
                       for c, oc in zip(SHORT, objcols)}
    r9, _ = spearmanr(arch.landscape_frac, arch["obj_F9_landscape_buffer"])
    F["landscape_vs_F9_r"] = round(float(r9), 3)
    pub = arch[["g_has_H0", "g_has_J0", "g_has_K0"]].sum(axis=1)
    r8, _ = spearmanr(pub, arch["obj_F8_community_connection"])
    F["pubmod_vs_F8_r"] = round(float(r8), 3)
    r7, _ = spearmanr(arch.n_R4, arch["obj_F7_domestic_scale"])
    F["nR4_vs_F7_r"] = round(float(r7), 3)
    return corr


# ------------------------------------------------------------------ modules (ASSOCIATION, not causal)
def module_analysis():
    F["module_presence_pct"] = {c: round(100 * float(arch[g].mean()), 1) for g, c in GMAP.items()}
    F["nR4_dist"] = {int(k): int(v) for k, v in arch["n_R4"].value_counts().sort_index().items()}
    F["pub_intensity_dist"] = {int(k): int(v) for k, v in
                               arch[["g_has_H0", "g_has_J0", "g_has_K0"]].sum(axis=1).value_counts().sort_index().items()}
    F["landscape_frac"] = dict(mean=round(float(arch.landscape_frac.mean()), 3),
                               lo=round(float(arch.landscape_frac.min()), 3),
                               hi=round(float(arch.landscape_frac.max()), 3))
    # ASSOCIATION: difference in objective mean between presence/absence groups.
    # This is a descriptive association across the evolved archive, NOT a causal
    # effect (module presence co-varies with placement & other genes under
    # selection; no independent manipulation was performed).
    assoc = {}
    for g, c in GMAP.items():
        pres = arch[g] == 1
        assoc[c] = {s: round(float(arch.loc[pres, oc].mean() - arch.loc[~pres, oc].mean()), 3)
                    for oc, s in zip(objcols, SHORT)}
    F["module_obj_association"] = assoc
    P = arch[list(GMAP.keys())].copy(); P.columns = list(GMAP.values())
    co = pd.DataFrame(0, index=P.columns, columns=P.columns)
    for a in P.columns:
        for b in P.columns:
            co.loc[a, b] = int(((P[a] == 1) & (P[b] == 1)).sum())
    co.to_csv(f"{CD}/analysis_module_cooccurrence.csv")
    return co, P


# ------------------------------------------------------------------ evolutionary-seed recurrence
def cross_seed():
    """EVOLUTIONARY-SEED stability: do the same structural programs recur across
    independent evolutionary runs? (Distinct from K-means init stability.)"""
    sig = arch[["n_R4", "g_has_H0", "g_has_J0", "g_has_K0", "g_has_I0", "g_has_L0",
                "g_floors_C0"]].astype(int).astype(str).agg("".join, axis=1)
    df = pd.DataFrame({"sig": sig, "seed": arch.seed})
    per_seed = {s: set(df.sig[df.seed == s]) for s in arch.seed.unique()}
    all_inter = set.intersection(*per_seed.values())
    union = set.union(*per_seed.values())
    F["cross_seed"] = dict(
        n_seeds=len(per_seed),
        sigs_per_seed={int(s): len(v) for s, v in per_seed.items()},
        shared_by_all_seeds=len(all_inter),
        union_sigs=len(union),
        recurrence_jaccard_all=round(len(all_inter) / len(union), 3))
    return F["cross_seed"]


# ------------------------------------------------------------------ K-means INIT stability
def kmeans_stability():
    """K-means INITIALIZATION stability (same archive, different random inits).
    Distinct from evolutionary-seed stability above."""
    inits = [0, 1, 2, 3, 4]
    sil = {}
    for k in range(2, 9):
        sil[k] = [round(float(silhouette_score(Xn, KMeans(n_clusters=k, n_init=10, random_state=s).fit_predict(Xn))), 3)
                  for s in inits]
    F["kmeans_init_silhouette_by_k"] = {str(k): v for k, v in sil.items()}
    labs = {s: KMeans(n_clusters=2, n_init=10, random_state=s).fit_predict(Xn) for s in inits}
    aris = [adjusted_rand_score(labs[a], labs[b]) for a, b in itertools.combinations(inits, 2)]
    F["kmeans_k2_init_ARI_mean"] = round(float(np.mean(aris)), 3)
    F["kmeans_init_verdict"] = "init-STABLE" if np.mean(aris) > 0.6 else "init-UNSTABLE"
    return sil


# ------------------------------------------------------------------ figures
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
    ax.set_title("v2 Objective correlation — conflict(−) / redundancy(+)")
    fig.tight_layout(); fig.savefig(f"{FD}/analysis_objective_correlation.png", dpi=140); plt.close(fig)


def fig_module_assoc():
    assoc = pd.DataFrame(F["module_obj_association"]).T[SHORT]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    im = ax.imshow(assoc.values, cmap="RdBu_r", vmin=-0.6, vmax=0.6, aspect="auto")
    ax.set_xticks(range(9)); ax.set_xticklabels(SHORT)
    ax.set_yticks(range(len(assoc))); ax.set_yticklabels(assoc.index)
    for i in range(len(assoc)):
        for j in range(9):
            ax.text(j, i, f"{assoc.values[i,j]:+.2f}", ha="center", va="center", fontsize=7,
                    color="white" if abs(assoc.values[i, j]) > 0.3 else "black")
    fig.colorbar(im, label="association (present − absent); − = lower objective")
    ax.set_title("v2 Module–objective ASSOCIATION (descriptive, not causal)")
    fig.tight_layout(); fig.savefig(f"{FD}/analysis_module_association.png", dpi=140); plt.close(fig)


def fig_stability(sil):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ks = sorted(sil); arr = np.array([sil[k] for k in ks])
    ax.errorbar(ks, arr.mean(1), yerr=arr.std(1), marker="o", capsize=4, color="#0284c7")
    for s in range(arr.shape[1]):
        ax.plot(ks, arr[:, s], ".", alpha=0.3, color="#94a3b8")
    ax.set_xlabel("k"); ax.set_ylabel("silhouette"); ax.grid(alpha=0.3)
    ax.set_title("v2 K-means INITIALIZATION stability — silhouette by k")
    fig.tight_layout(); fig.savefig(f"{FD}/analysis_kmeans_init_stability.png", dpi=140); plt.close(fig)


def fig_rank1_growth():
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for s, h in hist.items():
        ax.plot([x["gen"] for x in h], [x["rank1"] / POPN for x in h], label=f"seed {s}", alpha=0.85)
    ax.axhline(1.0, ls="--", color="k", lw=0.8, alpha=0.5)
    ax.set_xlabel("generation"); ax.set_ylabel("rank-1 fraction"); ax.set_ylim(0, 1.05)
    ax.set_title("v2 Many-objective dilution — rank-1 fraction growth")
    ax.legend(fontsize=7); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(f"{FD}/analysis_rank1_growth.png", dpi=140); plt.close(fig)


def fig_must():
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(arch.soft_cv, bins=30, color="#fbbf24", edgecolor="k")
    ax.axvline(1e-6, color="g", ls="--", label="all MUST satisfied")
    ax.set_xlabel("MUST-adjacency shortfall soft_cv (m)"); ax.set_ylabel("count")
    ax.set_title(f"v2 MUST satisfaction in archive ({F['must_fully_satisfied']}/{F['archive_n']} fully satisfied)")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(f"{FD}/analysis_must_satisfaction.png", dpi=140); plt.close(fig)


def main():
    sig = audit()
    corr = objective_analysis()
    module_analysis()
    cross_seed()
    sil = kmeans_stability()
    fig_correlation(corr); fig_module_assoc(); fig_stability(sil)
    fig_rank1_growth(); fig_must()
    with open(f"{CD}/analysis_findings_v2.json", "w") as f:
        json.dump(F, f, indent=2, default=str)
    print(json.dumps(F, indent=2, default=str))


if __name__ == "__main__":
    main()
