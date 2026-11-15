"""V1 <-> V1.1 equivalence for HV-322604, the inert-purge letdown.

What is being proved
--------------------
Wholly by execution, against BOTH of V1's copies of the law:

  * ``hv_322604``, lifted out of ``main.py`` by `lift()`;
  * ``core/valve.py`` ``Valve322604.solve``, the copy `step_sim` actually steps, loaded as a
    real module and run on V1's own `Stream` objects.

V1 once let these two drift apart (report D-2: the class kept the incompressible form after
the function had moved on), so the test does not assume they agree — it runs both against
`purge_valve_322604` and asserts every published field with ``==``.

`Valve322604.solve` imports its constants with ``from main import ...``, and ``main.py``
cannot be imported. The `v1_main` fixture installs a stand-in ``main`` module in
`sys.modules` for the duration of each test only, built from the values `lift()` executed out
of the real ``main.py``.

Two `step_sim` statements wire the valve, and each is one expression inside `step_sim`, so
they are TRANSCRIBED (declared): the seat ceiling (``main.py`` 8173) and the published
vent-capacity diagnostic ``vent_frac`` (``main.py`` 8042). Everything they call is executed
V1 code.

V1 publishes ``P_in`` and ``dP`` rounded to 0.1 for display, and nothing reads them back; the
rewrite keeps them unrounded and the test compares them rounded. ``T_out`` is rounded at
source in both, because V1's downstream physics consumes the rounded value.

The decided divergence (handoff B-19, 2026-10-01)
--------------------------------------------------
Below the purge's dew point V1's single-phase solve answers with its bracket's floor or a
temperature the gas cannot reach dry; the port flashes the purge onto the carbamate liquor it
condenses. Where the port's line is dry every field is ``==`` V1's; where it condenses, V1's
``T_out`` is asserted ``==`` the port's single-phase answer (V1's own relation, which the port
keeps), the port's outlet above it, the gas and the liquor adding up to V1's purge, and the
deposition flag raised.
"""

from __future__ import annotations

import math
import sys
from types import ModuleType, SimpleNamespace

import pytest

from ureasim.control.valve import EQUAL_PCT_RANGE
from ureasim.data import unit_322e003 as d
from ureasim.units.synthesis.purge_valve import (
    DESIGN,
    purge_capacity_fraction,
    purge_valve_322604,
    seat_ceiling_kgh,
)
from ureasim.thermo import real_gas
from ureasim.units.synthesis.scrubber import scrubber_322e003
from tests.equivalence import b18_switch
from tests.equivalence.v1_loader import lift, load, v1_available, v1_service

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

V1_NAMES = [
    "hv_322604", "scrub_322e003", "MW_COMP", "REACT_OFFGAS_DES",
    "SCRUB_HV604_P_OUT", "SCRUB_HV604_DP_DES", "SCRUB_HV604_RANGE", "SCRUB_HV604_GAMMA",
    "SCRUB_HV604_MW_DES", "SCRUB_HIC604_DES_PCT", "SCRUB_OFFGAS_P_BARA", "SCRUB_OFFGAS_T_C",
    "SCRUB_OFFGAS_KMOLH_DES", "SCRUB_OFFGAS_KGH_DES",
    "SCRUB_CCW_T_IN_DES", "SCRUB_CCW_KGH_DES",
]

#: What `Valve322604.solve` and `__init__` import from ``main``.
STUB_NAMES = [
    "MW_COMP", "SCRUB_HV604_P_OUT", "SCRUB_HIC604_DES_PCT", "SCRUB_HV604_DP_DES",
    "SCRUB_HV604_GAMMA", "SCRUB_HV604_MW_DES", "SCRUB_OFFGAS_P_BARA", "SCRUB_OFFGAS_T_C",
]

#: Transcribed: the L3-7 flag threshold is a literal inside `step_sim` (``main.py`` 8179).
V1_DEPOSITION_T_C = 20.0


def _seed() -> dict:
    return {
        "math": math,
        "hydraulics": load("hydraulics"),
        "real_gas": load("real_gas"),
        "reactor": load("reactor"),
        "jet_pump": load("jet_pump"),
        "h0_enthalpy": load("gap_g6_h0_enthalpy"),
        "thermo_service": v1_service(),
        "iapws_if97": load("iapws_if97"),
        "state": SimpleNamespace(p_syn_bara=140.7),
    }


@pytest.fixture(scope="module")
def v1():
    """V1 `main.py`'s HV-322604 block and the 322E003 function that feeds it, executed, on B-18's
    72 % anchor (decided 2026-10-10)."""
    return lift(b18_switch.names(V1_NAMES), seed=b18_switch.seed(_seed()))


@pytest.fixture(scope="module")
def v1_verbatim():
    """V1's block untouched, on its 50 % anchor, for B-18 both ways."""
    return lift(V1_NAMES, seed=_seed())


@pytest.fixture
def v1_main(v1, monkeypatch):
    """A stand-in ``main`` module, so `Valve322604` can import its constants."""
    stub = ModuleType("main")
    for name in STUB_NAMES:
        setattr(stub, name, v1[name])
    monkeypatch.setitem(sys.modules, "main", stub)
    return stub


@pytest.fixture(scope="module")
def v1_valve():
    return load("core.valve")


def _v1_class(v1_valve, offgas, t_in, hic, p_up, cap):
    """V1's live path: `Valve322604` on its own streams, as `step_sim` 8161-8175 drives it."""
    og = v1_valve.Stream("Valve_Offgas_In")
    out = v1_valve.Stream("Valve_Purge_Out")
    unit = v1_valve.Valve322604("HV_322604", og, out)
    og.comp = offgas
    og.set_state(T=t_in, P=p_up)
    unit.hic_pct = hic
    unit.vent_cap_kgh = cap
    unit.solve()
    return unit.diagnostics


def _v1_ceiling(v1, scrub: dict) -> float:
    """``main.py`` 8173, transcribed."""
    mw = v1["MW_COMP"]
    return max(sum(scrub["offgas_kmolh"][k] * mw[k] for k in mw) - scrub["uncond_kgh"], 0.0)


def _v1_vent_frac(v1, hic: float, p_syn: float) -> float:
    """``main.py`` 8042-8047, transcribed."""
    return v1["hydraulics"].valve_gas_anchored(
        1.0, hic / 100.0, p_syn, v1["SCRUB_HV604_P_OUT"], v1["SCRUB_OFFGAS_T_C"] + 273.15,
        v1["SCRUB_HIC604_DES_PCT"] / 100.0, v1["SCRUB_OFFGAS_P_BARA"], v1["SCRUB_HV604_P_OUT"],
        v1["SCRUB_OFFGAS_T_C"] + 273.15, v1["SCRUB_HV604_MW_DES"],
        gamma=v1["SCRUB_HV604_GAMMA"], characteristic="equal_pct",
        mw_des=v1["SCRUB_HV604_MW_DES"])


def _assert_same(mine, theirs, label, t_in, p_up):
    assert mine.comp_kmolh == theirs["comp_kmolh"], label
    if mine.condensing:  # ---- B-19: below the dew point the port flashes ----
        t1 = real_gas.isenthalpic_letdown(mine.comp_kmolh, t_in, p_up, mine.p_out_bara)
        assert round(t1["t_out_c"], 1) == theirs["T_out"], label
        assert mine.t_out_c > theirs["T_out"], label
        assert mine.carbamate_deposition is True, label
        assert all(mine.vapour_kmolh[k] + mine.liquor_kmolh[k] == pytest.approx(
            mine.comp_kmolh[k], rel=1e-12, abs=1e-15) for k in mine.comp_kmolh), label
    else:
        assert mine.t_out_c == theirs["T_out"], label
        assert mine.carbamate_deposition is (theirs["T_out"] < V1_DEPOSITION_T_C), label
        assert mine.vapour_kmolh == mine.comp_kmolh, label
    assert mine.p_out_bara == theirs["P_out"], label
    assert round(mine.p_in_bara, 1) == theirs["P_in"], label
    assert mine.open_pct == theirs["open_pct"], label
    assert mine.mass_kgh == theirs["mass_kgh"], label
    assert mine.valve_frac == theirs["valve_frac"], label
    assert round(mine.dp_bar, 1) == theirs["dP"], label
    assert mine.pass_frac == theirs["pass_frac"], label


# --------------------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("ours, theirs", [
    ("HV604_P_OUT_BARA", "SCRUB_HV604_P_OUT"),
    ("HV604_GAMMA", "SCRUB_HV604_GAMMA"),
    ("HV604_MW_DES", "SCRUB_HV604_MW_DES"),
    ("HIC604_DES_PCT", "SCRUB_HIC604_DES_PCT"),
    ("OFFGAS_P_BARA", "SCRUB_OFFGAS_P_BARA"),
    ("OFFGAS_T_DES_C", "SCRUB_OFFGAS_T_C"),
])
def test_scalar_constants(v1, ours, theirs):
    assert getattr(d, ours) == v1[theirs]


def test_the_deposition_threshold_is_v1s():
    assert d.CARBAMATE_DEPOSITION_T_C == V1_DEPOSITION_T_C


def test_the_unported_rangeability_is_the_trims_own(v1):
    """``SCRUB_HV604_RANGE`` is read only by the dead ``_eq_pct``; the live trim's is the same 50."""
    assert v1["SCRUB_HV604_RANGE"] == EQUAL_PCT_RANGE


def test_the_design_purge_is_pfd_204_to_the_bit(v1):
    assert DESIGN.comp_kmolh == v1["SCRUB_OFFGAS_KMOLH_DES"]
    assert DESIGN.mass_kgh == v1["SCRUB_OFFGAS_KGH_DES"]
    assert DESIGN.valve_frac == 1.0 and DESIGN.pass_frac == 1.0


# --------------------------------------------------------------------------------------
# The valve on its own, against both V1 copies
# --------------------------------------------------------------------------------------

#: Offered vents. Most are 322E003's own, taken from V1's scrubber at an operating point;
#: two are built by hand to reach what the scrubber cannot: an ammonia-rich purge, a gas cold
#: enough to trip the deposition flag, and nothing at all.
OFFERS = ["design", "cooling lost", "half cooling", "turndown", "overload",
          "ammonia rich", "cold", "empty"]
HICS = [0.0, 5.0, 24.0, 50.0, 78.188, 100.0]
#: Reversed, level, near the un-choking point, choked, design and high.
P_UPS = [2.0, 4.0, 12.0, 42.0, 100.0, 140.7, 151.0]


@pytest.fixture(scope="module")
def offers(v1):
    def vent(**kw):
        s = kw.pop("co2_scale", 1.0)
        r = v1["scrub_322e003"](v1["REACT_OFFGAS_DES"], s, v1["SCRUB_CCW_T_IN_DES"],
                                v1["SCRUB_CCW_KGH_DES"], **kw)
        return r["offgas_kmolh"], r["T_offgas"]

    v1["state"].p_syn_bara = 140.7
    design = vent()
    rich = {k: v + {"NH3": 200.0, "CO2": 50.0, "H2O": 5.0}.get(k, 0.0)
            for k, v in design[0].items()}
    return {
        "design": design,
        "cooling lost": vent(cool_frac=0.0),
        "half cooling": vent(cool_frac=0.5),
        "turndown": vent(co2_scale=0.7),
        "overload": vent(co2_scale=1.15),
        "ammonia rich": (rich, 130.3),
        "cold": (design[0], 30.0),
        "empty": ({k: 0.0 for k in v1["MW_COMP"]}, 114.0),
    }


@pytest.mark.parametrize("p_up", P_UPS)
@pytest.mark.parametrize("hic", HICS)
@pytest.mark.parametrize("offer", OFFERS)
def test_valve_against_both_v1_copies(v1, v1_main, v1_valve, offers, offer, hic, p_up):
    offgas, t_in = offers[offer]
    off_kgh = sum(offgas[k] * v1["MW_COMP"][k] for k in v1["MW_COMP"])
    for cap in (None, 0.0, 0.5 * off_kgh, off_kgh, 2.0 * off_kgh):
        mine = purge_valve_322604(offgas, t_in, hic, p_up, cap)
        label = f"{offer}, HIC {hic}, P {p_up}, cap {cap}"
        _assert_same(mine, v1["hv_322604"](offgas, t_in, hic, p_up, cap), label, t_in, p_up)
        _assert_same(mine, _v1_class(v1_valve, offgas, t_in, hic, p_up, cap), label, t_in,
                     p_up)


@pytest.mark.parametrize("p_syn", [100.0, 128.0, 139.603, 140.7, 151.0, 175.0])
@pytest.mark.parametrize("hic", HICS)
def test_the_published_vent_capacity(v1, hic, p_syn):
    assert purge_capacity_fraction(hic, p_syn) == _v1_vent_frac(v1, hic, p_syn)


# --------------------------------------------------------------------------------------
# The wiring: 322E003 -> ceiling -> HV-322604, as step_sim runs it
# --------------------------------------------------------------------------------------

#: (loop pressure, HIC-322604, scrubber arguments). The HIC reaches the scrubber too, because
#: the vent-top temperature correlation reads it, and the valve then lets that gas down.
WIRING_CASES = {
    "design": (140.7, 50.0, {}),
    "plant means": (139.603, 78.188, {"t_ccw_in": 84.459, "nc_act": 3.236}),
    "cooling lost": (140.7, 50.0, {"cool_frac": 0.0}),
    "half cooling": (140.7, 50.0, {"cool_frac": 0.5}),
    "CCW halved": (140.7, 50.0, {"m_ccw_kgh": 153000.0}),
    "purge shut": (140.7, 0.0, {}),
    "purge wide": (140.7, 100.0, {}),
    "overload": (151.0, 50.0, {"co2_scale": 1.15}),
    "turndown": (128.0, 50.0, {"co2_scale": 0.7}),
    "flooded sump": (140.7, 50.0, {"choke_level_pct": 100.0}),
}


@pytest.mark.parametrize("case", list(WIRING_CASES))
def test_the_scrubber_to_valve_wiring(v1, case):
    p_loop, hic, kwargs = WIRING_CASES[case]
    kw = dict(kwargs)
    s = kw.pop("co2_scale", 1.0)
    t_in = kw.pop("t_ccw_in", v1["SCRUB_CCW_T_IN_DES"])
    m_ccw = kw.pop("m_ccw_kgh", v1["SCRUB_CCW_KGH_DES"])

    v1["state"].p_syn_bara = p_loop
    scrub = v1["scrub_322e003"](v1["REACT_OFFGAS_DES"], s, t_in, m_ccw,
                                hic604_pct=hic, **kw)
    cap_v1 = _v1_ceiling(v1, scrub)
    #  main.py 8106: the valve's upstream pressure is the live loop pressure.
    theirs = v1["hv_322604"](scrub["offgas_kmolh"], scrub["T_offgas"], hic, p_loop, cap_v1)

    res = scrubber_322e003(v1["REACT_OFFGAS_DES"], s, t_in, m_ccw, p_loop_bara=p_loop,
                           hic604_pct=hic, **kw)
    cap = seat_ceiling_kgh(res.offgas_kmolh, res.uncond_kgh)
    assert cap == cap_v1
    _assert_same(purge_valve_322604(res.offgas_kmolh, res.t_offgas_c, hic, p_loop, cap),
                 theirs, case, res.t_offgas_c, p_loop)


def test_the_72_percent_anchor_decided_divergence(v1, v1_verbatim):
    """Handoff B-18, decided 2026-10-10: HV-322604's characteristic anchored at the 72 % its
    vendor's trim passes the design purge at, where V1 anchors it at 50 % with no source. The same
    law on each anchor: at the plant's own 78.188 % V1 passes 3.0124 times the design purge, the
    port 1.2739 times; at its own anchor each passes the design purge exactly."""
    assert v1_verbatim["SCRUB_HIC604_DES_PCT"] == 50.0 and d.HIC604_DES_PCT == 72.0
    for ns, hic_des, at_plant in ((v1_verbatim, 50.0, 3.0124), (v1, 72.0, 1.2739)):
        assert _v1_vent_frac(ns, hic_des, ns["SCRUB_OFFGAS_P_BARA"]) == 1.0
        assert _v1_vent_frac(ns, 78.188, ns["SCRUB_OFFGAS_P_BARA"]) == pytest.approx(at_plant,
                                                                                      abs=1e-4)
    assert purge_capacity_fraction(78.188, 140.7) == _v1_vent_frac(v1, 78.188, 140.7)
