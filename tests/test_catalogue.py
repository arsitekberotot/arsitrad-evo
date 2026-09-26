"""Regression test for the Evolutionary Catalogue."""
import os, sys, tempfile
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from arsitrad_evo.config import GAConfig
from arsitrad_evo.catalogue import capture_catalogue, _select_diverse, _genotype_summary


def test_catalogue_produces_thumbnails_and_boards(tmp_path):
    cfg = GAConfig(pop_size=40, generations=20, seed=7)
    m = capture_catalogue(cfg, str(tmp_path), tag="t")
    # snapshots captured at the representative generations (clamped to <= generations)
    assert m["snap_gens"] == [0, 10, 20]
    assert m["thumbnails"], "no thumbnails"
    for t in m["thumbnails"]:
        assert os.path.exists(os.path.join(str(tmp_path), t["image"]))
        # each thumbnail links seed + generation + genotype
        assert t["seed"] == 7 and "gen" in t and "genotype" in t
        assert "n_R4" in t["genotype"]
        assert t["module_population"]  # module population recorded
    for key in ("population_evolution", "pareto_representative", "objective_extremes",
                "balanced", "final_shortlist", "convergence"):
        assert key in m["boards"], f"missing board {key}"
        assert os.path.exists(os.path.join(str(tmp_path), m["boards"][key]))


def test_select_diverse_returns_distinct_not_only_winners():
    class P:  # minimal stand-in
        def __init__(self, o): self.objectives = np.array(o, float)
    pop = [P([0, 0, 0]), P([0.01, 0.01, 0.01]), P([1, 0, 0]), P([0, 1, 1]), P([0, 0, 1])]
    sel = _select_diverse(pop, k=3)
    assert len(sel) == 3
    objs = np.array([s.objectives for s in sel])
    # max-min spread: the chosen set should span more than the two near-duplicates
    assert not (np.allclose(objs[1], objs[0]) and np.allclose(objs[2], objs[0]))


def test_genotype_summary_has_programme():
    from arsitrad_evo.genotype import random_genotype
    from arsitrad_evo.nsga2 import evaluate
    ph = evaluate(random_genotype(np.random.default_rng(0)))
    g = _genotype_summary(ph)
    assert "n_R4" in g and 2 <= g["n_R4"] <= 4


if __name__ == "__main__":
    import pathlib
    test_catalogue_produces_thumbnails_and_boards(pathlib.Path(tempfile.mkdtemp()))
    test_select_diverse_returns_distinct_not_only_winners()
    test_genotype_summary_has_programme()
    print("catalogue tests OK")
