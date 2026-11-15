"""V1 <-> V1.1 equivalence for unit 324's vacuum condensers.

What is being proved
--------------------
Wholly by execution. V1's ``backend/vacuum_condenser.py`` is loaded as a real module (with the
``packed_absorber``, ``gap_g6_h0_enthalpy`` and ``iapws_if97`` it imports), and V1's four design
specs, ``VACUUM_CONDENSER_SPECS``, are lifted out of ``main.py`` with the rows and ratings they are
built on. Against them: the ratings and rows of `ureasim.data.unit_324`; every field of every
design spec; and `solve`, `vent_kgh`, `vent_kgh_at`, `condensate_back_pressure`, `bp_bracket` and
`bp_at` over shell pressures, cooling-water flows and temperatures, inlet loads, an ammonia-rich
inlet and a re-centred bracket — all ``==``.

V1's module runs with handoff B-67's and B-71's switch (decided 2026-10-02): its ``vent_moles`` is
V1's function transcribed with the NH3 and CO2 departures added, not multiplied, to the PFD's
partial pressures where the design back-pressure is at most that partial pressure
(`tests.equivalence.b67_switch`); everything else it runs is V1's. The departure both
ways is `test_vacuum_condenser_decided_equivalence.py`'s.
"""

from __future__ import annotations

import math

import pytest

from ureasim.data import unit_324 as d
from ureasim.thermo import saturated_vent as sv
from ureasim.units.evaporation import vacuum_condenser as vc
from tests.equivalence.b67_switch import switched_module
from tests.equivalence.v1_loader import lift, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

TAGS = ("324E002", "324E005", "324E006", "324E007")
RESULT_FIELDS = ("t_vent_c", "q_kw", "q_ua_kw", "cw_in_c", "cw_out_c", "cw_flow_kgh",
                 "vent_kmolh", "vent_model_kgh", "inlet_model_kgh", "condensate_model_kgh",
                 "lmtd_k")
SPEC_FIELDS = ("tag", "p_des", "t_in_des", "t_v_des", "y_des", "split", "psat_v_des",
               "cw_flow_kgh", "cw_in_c", "cw_cp", "n_in_des", "inlet_kgh", "vent_kgh", "bp_des",
               "ua_kw_k", "q_des_kw", "vent_model_des_kgh", "t_v_solved_des")


@pytest.fixture(scope="module")
def v1():
    module = switched_module()
    ns = lift(["VACUUM_CONDENSER_SPECS", "VACUUM_CONDENSERS", "CW_CP_KJKG_K",
               "PFD_324_MASS_PCT", "_VAC_PFD_KMOLH", "_VAC_AIR_MW", "_VAC_AIR_FRAC",
               "R324_F001_P_BARA", "R324_F003_P_BARA", "lmtd_countercurrent"],
              seed={"math": math, "vacuum_condenser": module})
    ns["module"] = module
    return ns


def _inlet(v1, tag, scale=1.0, nh3=1.0):
    n = dict(v1["VACUUM_CONDENSER_SPECS"][tag]["n_in_des"])
    return {k: v * scale * (nh3 if k == "NH3" else 1.0) for k, v in n.items()}


def test_the_ratings_rows_and_constants_are_v1s(v1):
    assert d.CW_CP_KJKG_K == v1["CW_CP_KJKG_K"]
    assert (d.F001_P_DES_BARA, d.F003_P_DES_BARA) == (v1["R324_F001_P_BARA"],
                                                      v1["R324_F003_P_BARA"])
    assert (d.VAC_AIR_MW, d.VAC_AIR_FRAC) == (v1["_VAC_AIR_MW"], v1["_VAC_AIR_FRAC"])
    assert d.VAC_PFD_KMOLH == v1["_VAC_PFD_KMOLH"]
    for row, pct in d.PFD_324_MOL_PCT.items():
        assert pct == v1["PFD_324_MASS_PCT"][row], row
    for tag in TAGS:
        theirs, mine = v1["VACUUM_CONDENSERS"][tag], d.VACUUM_CONDENSERS[tag]
        for key, value in theirs.items():
            assert getattr(mine, key) == value, (tag, key)
    for args in ((116.0, 45.0, 30.0, 40.0), (40.0, 40.0, 30.0, 40.0), (50.0, 41.0, 30.0, 39.0)):
        assert d.lmtd_countercurrent(*args) == v1["lmtd_countercurrent"](*args)


@pytest.mark.parametrize("tag", TAGS)
def test_the_design_specs_are_v1s(v1, tag):
    theirs, mine = v1["VACUUM_CONDENSER_SPECS"][tag], vc.design_specs()[tag]
    for name in SPEC_FIELDS:
        assert getattr(mine, name) == theirs[name], (tag, name)
    assert set(theirs) == set(SPEC_FIELDS)
    m = sv.moles_from_mole_pct(d.VAC_PFD_KMOLH[d.CONDENSER_ROWS[tag][0]],
                               d.PFD_324_MOL_PCT[d.CONDENSER_ROWS[tag][0]])
    assert m == v1["module"].moles_from_mole_pct(
        v1["_VAC_PFD_KMOLH"][d.CONDENSER_ROWS[tag][0]],
        v1["PFD_324_MASS_PCT"][d.CONDENSER_ROWS[tag][0]])


CASES = [(p, cw, scale, nh3, prev)
         for p in (0.8, 1.0, 1.25)
         for cw in (0.0, 0.5, 1.0, 1.3)
         for scale, nh3 in ((1.0, 1.0), (0.6, 1.0), (1.4, 1.0), (1.0, 2.5))
         for prev in (None, 3.0)]


@pytest.mark.parametrize("tag", TAGS)
@pytest.mark.parametrize("p, cw, scale, nh3, prev", CASES)
def test_solve_and_the_anchored_vent_are_v1s(v1, tag, p, cw, scale, nh3, prev):
    theirs_spec, mine_spec = v1["VACUUM_CONDENSER_SPECS"][tag], vc.design_specs()[tag]
    n_in = _inlet(v1, tag, scale, nh3)
    p_bara = theirs_spec["p_des"] * p
    cw_flow = theirs_spec["cw_flow_kgh"] * cw
    t_prev = None if prev is None else theirs_spec["t_v_des"] + prev
    theirs = v1["module"].solve(theirs_spec, p_bara, n_in, theirs_spec["t_in_des"], cw_flow,
                                theirs_spec["cw_in_c"], t_v_prev=t_prev)
    mine = vc.solve(mine_spec, p_bara, n_in, mine_spec.t_in_des, cw_flow, mine_spec.cw_in_c,
                    t_v_prev=t_prev)
    for name in RESULT_FIELDS:
        assert getattr(mine, name) == theirs[name], (tag, name)
    if theirs["vent_model_kgh"] > 0.0:
        assert vc.vent_kgh(mine_spec, mine) == v1["module"].vent_kgh(theirs_spec, theirs)
    t_v = theirs["t_vent_c"]
    bp = v1["module"].condensate_back_pressure(n_in, t_v)
    assert vc.condensate_back_pressure(n_in, t_v) == bp
    assert vc.vent_kgh_at(mine_spec, p_bara, t_v, n_in, bp) == v1["module"].vent_kgh_at(
        theirs_spec, p_bara, t_v, n_in, bp)


@pytest.mark.parametrize("tag", TAGS)
def test_warmer_water_and_a_fouled_surface_are_v1s(v1, tag):
    theirs_spec, mine_spec = v1["VACUUM_CONDENSER_SPECS"][tag], vc.design_specs()[tag]
    n_in = _inlet(v1, tag)
    for cw_in, ua_f in ((35.0, 1.0), (30.0, 0.6), (38.0, 0.8)):
        ua = theirs_spec["ua_kw_k"] * ua_f
        theirs = v1["module"].solve(theirs_spec, theirs_spec["p_des"], n_in,
                                    theirs_spec["t_in_des"], theirs_spec["cw_flow_kgh"], cw_in,
                                    ua_kw_k=ua)
        mine = vc.solve(mine_spec, mine_spec.p_des, n_in, mine_spec.t_in_des,
                        mine_spec.cw_flow_kgh, cw_in, ua_kw_k=ua)
        for name in RESULT_FIELDS:
            assert getattr(mine, name) == theirs[name], (tag, cw_in, ua_f, name)


def test_the_back_pressure_bracket_is_v1s(v1):
    w = vc.condensate_fractions(_inlet(v1, "324E005"))
    assert w == v1["module"].condensate_fractions(_inlet(v1, "324E005"))
    br = vc.bp_bracket(w, 40.0)
    assert br == v1["module"].bp_bracket(w, 40.0)
    for t in (40.0, 38.7, 41.3, 35.0, 46.0):
        assert vc.bp_at(br, t) == v1["module"].bp_at(br, t)
