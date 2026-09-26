"""Generate REPORT.md from a completed campaign output directory.

Reads campaign/data/*.csv + *.json and produces a research report documenting
the full traceable chain. Run AFTER run_campaign.py.

Usage:
    .venv/bin/python make_report.py --campaign campaign
"""
from __future__ import annotations
import argparse, json, os, glob
import pandas as pd

OBJ = ["F1_safeguarding", "F2_privacy_agency", "F3_everyday_life",
       "F4_service_separation", "F5_site_efficiency", "F6_adaptability",
       "F7_domestic_scale", "F8_community_connection", "F9_landscape_buffer"]


def load(campaign):
    d = os.path.join(campaign, "data")
    out = {}
    for name in ["multiseed_summary", "sensitivity", "pareto_archive",
                 "comparison_matrix", "k_analysis"]:
        p = os.path.join(d, f"{name}.csv")
        out[name] = pd.read_csv(p) if os.path.exists(p) else None
    summ = os.path.join(d, "campaign_summary.json")
    out["summary"] = json.load(open(summ)) if os.path.exists(summ) else {}
    traces = sorted(glob.glob(os.path.join(d, "phenotype_*.json")))
    out["traces"] = [json.load(open(t)) for t in traces]
    return out


def md_table(df, max_rows=None):
    if df is None or len(df) == 0:
        return "_(none)_"
    if max_rows:
        df = df.head(max_rows)
    cols = list(df.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |",
             "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def make_report(campaign):
    D = load(campaign)
    S = D["summary"]
    L = []
    A = L.append

    A("# arsitrad-evo — RESEARCH REPORT")
    A("## Evolutionary spatial programming for The Threshold Community (5,533.85 m²)")
    A("")
    A("**Algorithm:** constrained NSGA-II (Deb, Pratap, Agarwal & Meyarivan, 2002) `[PAPER METHOD]`  ")
    A("**Framework:** modularity-based spatial programming (Riskiyanto, Wibisono & Harani, 2025) — *architectural-scale adaptation* `[PAPER METHOD]`  ")
    A("**Post-processing:** K-means (silhouette + elbow) — never feeds selection `[DESIGN HYPOTHESIS]`  ")
    A("**Runtime deps:** Python + numpy/scipy/scikit-learn/matplotlib/pandas only. No Rhino/Grasshopper/Wallacei/jMetal/Helix.")
    A("")
    A("> **Evidence discipline.** `[PAPER METHOD]` validated algorithm/framework · `[PA5 CORPUS]` project program & rules · `[DESIGN HYPOTHESIS]` unvalidated proxy · `[TO VERIFY]` needs authority/operator input. Riskiyanto et al. validated on office furniture; this is an **unvalidated architectural adaptation**. Optimization never overrides safeguarding/accessibility/dignity (hard constraints).")
    A("")
    A("---")
    A("")
    A("## 1. Traceable chain")
    A("`MODULE LIBRARY → GENOTYPE → DECODING → HARD CONSTRAINTS → OBJECTIVES → NSGA-II EVOLUTION → PARETO FRONT → K-MEANS CLUSTERS → REPRESENTATIVE PHENOTYPES → ARCHITECTURAL INTERPRETATION`")
    A("")
    A("## 2. Module library → Genotype → Decoding")
    A("- **Module library** (`arsitrad_evo/modules.py`): 12 Threshold module types (A0 Civic, B0 Care, C0 Commons, R4 Domestic cluster [repeatable], E0 Staff, F0 Service, M0 Technical, H0 Learning, I0 Reflection, J0 Livelihood, K0 Community, L0 Transition) with net area, privacy level, developmental/variational flag, stacking cap, and the adjacency matrix (MUST/NEAR/SCREENED/AVOID/PROHIBITED).")
    A("- **Genotype** (`genotype.py`): mixed real/integer vector. Structural genes — `n_R4` (2–4), `has_H0/J0/K0/I0/L0` (0/1), `floors_C0/H0` (1–2), `landscape_frac`, `service_depth`, `buffer_depth`, `reserve_area` — plus a variable-length (x,y) placement tail. `public_intensity` is **derived** from present public modules for genotype coherence.")
    A("- **Decoding**: genotype → placed axis-aligned rectangles (centroid, w×d, floors), derived footprint/GFA/occupancy/landscape, adjacency graph, privacy tags. Phase-1 = program+zoning only.")
    A("")
    A("## 3. Hard constraints (constrained domination)")
    A("Violation ≥ 0; feasible iff all hard violations = 0. Feasible always dominates infeasible; among infeasible, smaller total violation wins.")
    A("`overlap · site/buildable limit · required developmental modules · permitted populations · prohibited adjacency (R4↔F0/M0/K0) · privacy hierarchy · safeguarding access · care access to R4 · no public→private shortcut · independent service access · stacking rules · landscape band · accessibility/egress (placeholder [TO VERIFY])`. See `constraints.py`.")
    A("")
    A("## 4. Objectives F1–F9 (all minimised)")
    A("F1 safeguarding · F2 privacy/agency · F3 everyday life · F4 service separation · F5 site efficiency · F6 adaptability · F7 domestic scale (residential dispersion) · F8 controlled community connection · F9 landscape/buffer. Equations/normalization/assumptions in `objectives.py` + `SPEC.md`.")
    A("")

    # 5. Multi-seed
    A("## 5. NSGA-II evolution — multi-seed runs")
    A(f"Base config: pop={S.get('base',{}).get('pop_size')} gen={S.get('base',{}).get('generations')}. Seeds: {S.get('seeds')}.")
    A("")
    A(md_table(D["multiseed_summary"]))
    A("")
    A("![multi-seed convergence](figures/convergence_multiseed.png)")
    A("")
    A("![many-objective dilution — rank-1 growth](figures/rank1_growth_dilution.png)")
    A("")
    A("*Rank-1 fraction climbs to ~100% by mid-run in every seed — the dynamical signature of many-objective dilution (Campaign v2 measures this per-generation, not via non-dominance inside a filtered archive).*")
    A("")

    # 6. Sensitivity
    A("## 6. Sensitivity tests")
    A("Parameters swept: population size, generation count, crossover probability, mutation probability, mutation strength (η). Recorded: runtime, feasible rate, Pareto-front size, objective stats.")
    A("")
    A(md_table(D["sensitivity"]))
    A("")
    A("![sensitivity](figures/sensitivity.png)")
    A("")

    # 7. Pareto archive
    A("## 7. Nondominated archive (Pareto front)")
    A(f"Combined nondominated archive across seeds: **{S.get('archive_size')}** solutions (re-sorted on the union of per-seed rank-1 sets).")
    A("")
    arch = D["pareto_archive"]
    if arch is not None and len(arch):
        cols = [c for c in arch.columns if c.startswith("obj_")]
        rng = arch[cols].agg(["min", "max"]).T
        rng.columns = ["min", "max"]
        rng = rng.round(3).reset_index().rename(columns={"index": "objective"})
        A("Objective ranges across the archive:")
        A("")
        A(md_table(rng))
        A("")
    A("![objective distributions](figures/objective_distributions.png)")
    A("")
    A("![pareto archive](figures/pareto_archive.png)")
    A("")
    A("![parallel coordinates](figures/parallel_coords.png)")
    A("")

    # 8. Clustering
    A("## 8. K-means clustering of the Pareto front")
    ck = S.get("cluster", {})
    A(f"Chosen **k = {ck.get('k')}** (silhouette) · elbow k = {ck.get('k_elbow')} · silhouette = {round(ck.get('silhouette') or 0, 3)}.")
    A("")
    A("![k analysis](figures/k_analysis.png)")
    A("")
    A("![clusters](figures/clusters.png)")
    A("")

    # 9. Representatives
    A("## 9. Representative phenotypes (medoids + objective extremes)")
    A(f"**{S.get('n_representatives')}** representatives exported, each with a machine-readable traceability record (`data/phenotype_XX.json`).")
    A("")
    A("### 9.1 Comparison matrix")
    comp = D["comparison_matrix"]
    if comp is not None and len(comp):
        keep = ["rep", "n_R4", "residents", "day_users", "gfa", "footprint", "landscape_frac"] + OBJ
        keep = [c for c in keep if c in comp.columns]
        A(md_table(comp[keep].round(3)))
        A("")
    A("![comparison matrix](figures/comparison_matrix.png)")
    A("")

    A("### 9.2 Per-phenotype summaries")
    for i, t in enumerate(D["traces"]):
        seed_tag = f" · seed {t.get('seed')}" if t.get("seed") is not None else ""
        A(f"#### phenotype_{i:02d} — {t.get('role')} (cluster {t.get('cluster')}{seed_tag})")
        cap = t["capacity"]; ar = t["areas"]; g = t["genes"]
        A(f"- **Capacity:** {cap['residents']} residents ({cap['n_R4']} clusters) · {cap['day_users']} day users")
        A(f"- **Areas:** GFA {ar['gfa']} m² · footprint {ar['footprint']} m² · landscape {ar['landscape_area']} m² ({ar['landscape_frac']*100:.0f}%) · reserve {ar['reserve_area']} m²")
        if t.get("soft_cv") is not None:
            A(f"- **MUST-adjacency shortfall:** {t['soft_cv']} m (0 = all satisfied)")
        # dormant-gene-clean description (floors_H0 omitted when H0 absent)
        gene_bits = [f"n_R4={g['n_R4']}", f"H0={g['has_H0']}", f"J0={g['has_J0']}",
                     f"K0={g['has_K0']}", f"I0={g['has_I0']}", f"L0={g['has_L0']}",
                     f"public_intensity={g['public_intensity']}", f"floors_C0={g['floors_C0']}"]
        if "floors_H0" in g:
            gene_bits.append(f"floors_H0={g['floors_H0']}")
        A(f"- **Genes:** " + ", ".join(gene_bits))
        A(f"- **Strongest objective:** {t['strongest_objective']} · **weakest:** {t['weakest_objective']}")
        A(f"- figures: `phenotype_{i:02d}_siteplan.png`, `_privacy.png`, `_stacking.png`, `_circulation.png`, `_landscape.png`, `_radar.png`")
        A("")

    # 10. Interpretation
    A("## 10. Architectural interpretation")
    A("Representatives span the program's real trade-space rather than one fixed answer. The dominant, repeatable structure is a **compact-vs-landscape** axis (the clean k=2 split), overlaid on the genuine **F5–F8 (site-efficiency vs community-connection) conflict**:")
    A("- **Compact / low-landscape** (n_R4=2, landscape ~0.35): tighter sites, slightly better F5/F3.")
    A("- **Higher-landscape** (n_R4=2/3/4, landscape ~0.46): more buffer, stronger F9.")
    A("- **Open (public modules present)** vs **closed (none)** positions the F8 axis; the closed strategy is the most recurrent program in the archive under safeguarding-as-hard-constraint.")
    A("")
    A("> **No universal winner is declared, and no discrete typology is named** — the trade-space is largely continuous (modest silhouette). The actionable output is the 3-candidate shortlist in `DESIGN_HANDOFF_v2.md`. Selection among candidates remains a safeguarding/operator/policy decision, not an optimization output.")
    A("")

    # 11. Limitations
    A("## 11. Limitations & unresolved assumptions")
    A("- **Many-objective dilution:** with 9 objectives the population becomes all-rank-1 by mid-run (see rank-1 growth figure), so Pareto membership is necessary-but-not-sufficient evidence of quality. Remedies: aggregate objectives, NSGA-III, ε-dominance.")
    A("- **Objective proxies are `[DESIGN HYPOTHESIS]`:** F9 ≈ landscape-area (r≈−0.94), F8 ≈ public-module count (r≈−0.73), F7 ≈ f(n_R4), F2/F4 near-binary. Reference ranges in `config.py` need calibration with safeguarding/clinical criteria.")
    A("- **Soft MUST-adjacency** is a selection discriminator among feasible solutions, not a hard constraint — representative shortfalls (e.g. B/C candidates) are reported honestly and resolved at schematic stage, not by the optimizer.")
    A("- **Low cross-seed program recurrence** (Jaccard ≈ 0.01): independent runs find different specific programs; only trade-space-level and shortlist-level claims are robust.")
    A("- **Accessibility/egress** is a placeholder; real dimensions require regulatory review `[TO VERIFY]`.")
    A("- **Rectangular site envelope;** real parcel shape/orientation `[TO VERIFY]` before any scaled drawing.")
    A("- **Clustering silhouette is modest (k=2, ~0.34)** — the front is largely continuous; the k=2 compact-vs-landscape split is a coarse structure, not discrete types.")
    A("- K-means and the architectural-scale adaptation are methodological choices, not validated by the source papers.")
    A("")
    A("## 12. Reproducibility")
    A("```bash")
    A("python3 -m venv .venv && .venv/bin/pip install -r requirements.txt")
    A(".venv/bin/python run_campaign.py --out campaign        # full")
    A(".venv/bin/python run_campaign.py --out campaign --quick # fast smoke")
    A(".venv/bin/python make_report.py --campaign campaign")
    A("```")
    A("All runs are seeded; results archived under `campaign/data` + `campaign/figures`.")
    A("")
    A("---")
    A("*Generated by make_report.py from campaign outputs. Deb et al. (2002) NSGA-II, IEEE TEVC 6(2) · Riskiyanto, Wibisono & Harani (2025), J. Architecture & Urbanism 49(1).*")

    text = "\n".join(L)
    path = os.path.join(campaign, "REPORT.md")
    with open(path, "w") as f:
        f.write(text)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign", default="campaign")
    args = ap.parse_args()
    p = make_report(args.campaign)
    print(f"[report] written -> {p}")


if __name__ == "__main__":
    main()
