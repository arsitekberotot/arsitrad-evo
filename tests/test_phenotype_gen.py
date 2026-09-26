"""Regression tests for the Spatial Phenotype Generator semantics gate.

Covers: sightline exposure, open-space (enclosure) classification, circulation
typing (A0-R4 must not be public), module anchors, stacking, privacy
transitions, and deterministic rendering. No optimization features here.
"""
from __future__ import annotations
import numpy as np
import pytest

from arsitrad_evo.phenotype_gen import (
    build_prototype, _circulation_for, _check_sightlines, _classify_open_spaces,
    _seg_intersects_rect, _rect_of, _orientation, _interface,
    PRIVATE, PUBLIC_MOD, CARE_MOD, SVC_MOD, PROHIBITED, SCREENED, MUST, NEAR,
    CORPUS, HYP, VERIFY)
from arsitrad_evo.genotype import Phenotype, Instance
from arsitrad_evo.modules import MODULES, PRIVACY, PUB, CTRL, SHR, DOM, PER


def mk_inst(code, x, y, floors=1, priv=DOM):
    mt = MODULES[code]
    return Instance(code=code, x=x, y=y, w=mt.w, d=mt.d,
                    area=mt.area * floors, floors=floors, privacy=priv)


def mk_pheno(insts, n_R4=1):
    ph = Phenotype(genes=np.zeros(60))
    ph.instances = insts
    ph.n_R4 = n_R4
    ph.residents = 4 * n_R4
    ph.day_users = 8
    ph.gfa = sum(i.area for i in insts)
    ph.footprint = sum(i.w * i.d for i in insts)
    ph.landscape_frac = 0.45
    ph.landscape_area = 1000.0
    ph.reserve_area = 100.0
    ph.objectives = np.zeros(9)
    return ph


# --------------------------------------------------------------- circulation
def test_circulation_a0_r4_not_public():
    """A0-R4 (SCREENED/controlled) must NOT be labelled public circulation."""
    circ = _circulation_for("A0", "R4", SCREENED)
    assert "public" not in circ
    assert "resident" in circ or "care" in circ
    assert "controlled" in circ           # screened -> controlled crossing


def test_circulation_private_never_public():
    """Any connection touching R4 (private residential) is never public."""
    for other in ["A0", "K0", "C0", "H0", "J0", "B0"]:
        circ = _circulation_for(other, "R4", "")
        assert "public" not in circ, f"{other}-R4 wrongly public: {circ}"


def test_circulation_public_pair_is_public():
    """A0-K0 (both public-facing, no private) may be public circulation."""
    circ = _circulation_for("A0", "K0", "")
    assert "public" in circ


def test_circulation_care_and_service():
    assert "care" in _circulation_for("B0", "R4", MUST)
    assert "service" in _circulation_for("F0", "M0", MUST)
    assert "care" in _circulation_for("E0", "R4", "")


# --------------------------------------------------------------- segment/rect
def test_seg_intersects_rect():
    rect = (0, 0, 10, 10)
    assert _seg_intersects_rect((-5, 5), (15, 5), rect)      # crosses
    assert not _seg_intersects_rect((-5, 20), (15, 20), rect)  # above
    assert not _seg_intersects_rect((-5, -5), (-2, -2), rect)  # outside


def test_rect_of():
    inst = mk_inst("R4", 50, 50)
    x0, y0, x1, y1 = _rect_of(inst)
    assert x0 == 50 - inst.w / 2 and x1 == 50 + inst.w / 2


# --------------------------------------------------------------- sightlines
def test_sightline_exposed_when_clear():
    """R4 and A0 far apart with no intervening mass -> EXPOSED."""
    r4 = mk_inst("R4", 10, 10, priv=DOM)
    a0 = mk_inst("A0", 90, 90, priv=PUB)
    sls = _check_sightlines([r4, a0])
    assert len(sls) == 1
    assert sls[0].exposed is True
    assert sls[0].screened_by == []


def test_sightline_screened_by_intervening_module():
    """A module on the R4-A0 line screens the sightline -> NOT exposed."""
    r4 = mk_inst("R4", 10, 10, priv=DOM)
    a0 = mk_inst("A0", 90, 90, priv=PUB)
    block = mk_inst("C0", 50, 50, priv=SHR)   # sits on the diagonal
    sls = _check_sightlines([r4, a0, block])
    pair = [s for s in sls if {s.from_code, s.to_code} == {"R4", "A0"}]
    assert len(pair) == 1
    assert pair[0].exposed is False
    assert "C0" in pair[0].screened_by


def test_sightline_only_sensitive_pairs():
    """Non-sensitive pairs (e.g. R4-B0 care, not public) produce no PROHIBITED entry
    unless private<->public. R4-B0 is not public-facing, so not flagged."""
    r4 = mk_inst("R4", 10, 10, priv=DOM)
    b0 = mk_inst("B0", 30, 30, priv=CTRL)
    sls = _check_sightlines([r4, b0])
    # B0 is not a public-facing module and R4-B0 is not PROHIBITED -> no sightline
    assert all(not (s.from_code == "R4" and s.to_code == "B0") for s in sls)


# --------------------------------------------------------------- open space
def _dense_courtyard_pheno():
    """Four R4 modules in a ring around a centre -> centre should be COURTYARD."""
    mts = []
    W = MODULES["R4"].w; D = MODULES["R4"].d
    cx, cy = 50, 50
    off = 14
    for (dx, dy) in [(-off, 0), (off, 0), (0, -off), (0, off)]:
        mts.append(mk_inst("R4", cx + dx, cy + dy, priv=DOM))
    return mts


def test_open_space_courtyard_enclosed():
    insts = _dense_courtyard_pheno()
    zones = _classify_open_spaces(insts)
    types = {z.space_type for z in zones}
    # a ring of 4 modules should yield at least one highly-enclosed courtyard
    assert any(z.space_type == "COURTYARD" for z in zones), f"no courtyard in {types}"


def test_open_space_open_landscape_present():
    """A single isolated module leaves most of the site OPEN LANDSCAPE."""
    insts = [mk_inst("R4", 10, 10, priv=DOM)]
    zones = _classify_open_spaces(insts)
    assert any(z.space_type == "OPEN LANDSCAPE" for z in zones)


def test_open_space_classification_thresholds():
    """Enclosure -> type mapping is exactly as specified."""
    # build a fake 'built' grid path via two modules forming an L (2-sided pocket)
    a = mk_inst("R4", 40, 50, priv=DOM)
    b = mk_inst("R4", 60, 50, priv=DOM)
    c = mk_inst("R4", 50, 62, priv=DOM)
    zones = _classify_open_spaces([a, b, c])
    # every zone's space_type is one of the three allowed labels
    allowed = {"COURTYARD", "POCKET COURT / THRESHOLD EDGE", "OPEN LANDSCAPE"}
    assert all(z.space_type in allowed for z in zones)
    # enclosure matches the type
    for z in zones:
        if z.space_type == "COURTYARD":
            assert z.enclosure >= 3
        elif z.space_type == "POCKET COURT / THRESHOLD EDGE":
            assert z.enclosure == 2


# --------------------------------------------------------------- anchors
def test_module_anchors_present_and_valid():
    insts = [mk_inst("R4", 30, 30, priv=DOM), mk_inst("C0", 60, 30, priv=SHR)]
    ph = mk_pheno(insts)
    proto = build_prototype(ph, candidate_label="T", rep_index=0, seed=1)
    for m in proto.modules:
        ex, ey = m.entrance_anchor
        # entrance anchor lies on the module boundary
        assert abs(abs(ex - m.x) - m.w / 2) < 1e-6 or abs(abs(ey - m.y) - m.d / 2) < 1e-6
        assert len(m.connection_anchors) == 3


def test_orientation():
    inst = mk_inst("R4", 0, 0)
    assert _orientation(inst) in ("EW", "NS")
    assert _orientation(inst) == ("EW" if inst.w >= inst.d else "NS")


# --------------------------------------------------------------- stacking
def test_stacking_relationships():
    insts = [mk_inst("C0", 30, 30, floors=2, priv=SHR),
             mk_inst("R4", 60, 30, floors=1, priv=DOM)]
    ph = mk_pheno(insts)
    proto = build_prototype(ph, candidate_label="T", rep_index=0, seed=1)
    stacked_codes = {s["code"] for s in proto.stacking}
    assert "C0" in stacked_codes
    assert "R4" not in stacked_codes            # R4 always single-storey


# --------------------------------------------------------------- privacy
def test_privacy_gradient_is_ordered():
    insts = [mk_inst("A0", 10, 10, priv=PUB), mk_inst("C0", 30, 10, priv=SHR),
             mk_inst("R4", 50, 10, priv=DOM)]
    ph = mk_pheno(insts)
    proto = build_prototype(ph, candidate_label="T", rep_index=0, seed=1)
    order = [PRIVACY.index(g["privacy"]) for g in proto.privacy_gradient]
    assert order == sorted(order)               # PUBLIC -> PERSONAL ordering


def test_internal_kit_parts_tagged():
    insts = [mk_inst("R4", 30, 30, priv=DOM)]
    ph = mk_pheno(insts)
    proto = build_prototype(ph, candidate_label="T", rep_index=0, seed=1)
    node = proto.modules[0]
    assert len(node.parts) > 0
    for p in node.parts:
        assert p.provenance in (CORPUS, HYP, VERIFY)
    # at least one PERSONAL part in a domestic cluster
    assert any(p.privacy == PER for p in node.parts)


# --------------------------------------------------------------- determinism
def test_deterministic_build():
    insts = [mk_inst("R4", 30, 30, priv=DOM), mk_inst("A0", 90, 90, priv=PUB),
             mk_inst("C0", 60, 30, floors=2, priv=SHR)]
    ph = mk_pheno(insts)
    p1 = build_prototype(ph, candidate_label="T", rep_index=0, seed=1)
    p2 = build_prototype(ph, candidate_label="T", rep_index=0, seed=1)
    d1, d2 = p1.to_dict(), p2.to_dict()
    # exclude nothing; full structural dict must be identical
    assert d1 == d2


def test_deterministic_rendering(tmp_path):
    """render_suite writes the same set of files and identical JSON on repeat."""
    insts = [mk_inst("R4", 30, 30, priv=DOM), mk_inst("A0", 90, 90, priv=PUB),
             mk_inst("C0", 60, 30, floors=2, priv=SHR)]
    ph = mk_pheno(insts)
    proto = build_prototype(ph, candidate_label="T", rep_index=0, seed=1)
    from arsitrad_evo.phenotype_gen import render_suite, RENDERERS
    import json, os
    o1 = render_suite(proto, str(tmp_path), "t")
    assert set(RENDERERS and [n for n, _ in RENDERERS]) | {"json"} == set(
        k for k in o1)
    # json stable across two renders
    j1 = open(o1["json"]).read()
    o2 = render_suite(proto, str(tmp_path), "t2")
    assert open(o2["json"]).read() == j1


# --------------------------------------------------------------- integration
def test_no_public_circulation_to_private_in_full_build():
    """End-to-end: in a built prototype, no connection touching R4 is 'public'."""
    insts = [mk_inst("R4", 30, 30, priv=DOM), mk_inst("A0", 90, 90, priv=PUB),
             mk_inst("K0", 90, 20, priv=PUB), mk_inst("C0", 60, 60, priv=SHR)]
    ph = mk_pheno(insts)
    proto = build_prototype(ph, candidate_label="T", rep_index=0, seed=1)
    for cn in proto.connections:
        if "R4" in (cn.a_code, cn.b_code):
            assert "public" not in cn.circulations, \
                f"{cn.a_code}-{cn.b_code} wrongly public: {cn.circulations}"
