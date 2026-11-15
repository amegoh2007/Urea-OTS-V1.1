"""V1 vs V1.1 — the 322F001 HP carbamate ejector and the jet-pump closure beneath it.

Evidence standard
-----------------
Execution, on both halves, with no transcription anywhere.

`backend/jet_pump.py` imports cleanly, so V1's own module object is compared against
`ureasim.control.jet_pump` function by function. `ejector_322f001` is a module-level function
in `main.py`, which cannot be imported, so it comes through `v1_loader.lift` — V1's own bytes,
executed. Every assertion below therefore compares code against code.

The design constants are lifted as well, so the twenty-odd numbers in
`ureasim/data/unit_322f001.py` are checked against V1's rather than re-read from the same PFD
by eye. That matters most for the two that are DERIVED: the back-solved nozzle and throat
areas are the output of a 200-step bisection, and a one-ulp difference in any input to it
moves the entrainment everywhere.
"""

from __future__ import annotations

import math

import pytest

from ureasim.control import jet_pump as new_pump
from ureasim.data import unit_322f001 as d
from ureasim.units.synthesis.ejector import ejector_322f001, spindle_phi

from . import b6_switch
from .v1_loader import lift, load, v1_available

pytestmark = pytest.mark.skipif(not v1_available(),
                                reason="V1 reference tree not present on this machine")


@pytest.fixture(scope="module")
def v1_pump():
    """V1's `jet_pump` module, imported whole."""
    return load("jet_pump")


@pytest.fixture(scope="module")
def v1():
    """`ejector_322f001` and its design constants, lifted out of `main.py`, on the standard
    atmosphere and gravity (handoffs B-6, B-7, decided; `b6_switch`)."""
    return lift(
        ["ejector_322f001", "ej_spindle_phi",
         "EJ_MOTIVE_NH3_DES", "EJ_MOTIVE_T_DES_C", "EJ_OPEN_DES", "EJ_MOTIVE_W",
         "EJ_SUCTION_KGH", "EJ_SUC_TOT_DES", "EJ_CARB_FRAC", "EJ_T_SUCTION_C",
         "EJ_P_MOTIVE_BARA", "EJ_P_SUCTION_BARA", "EJ_P_DISCH_BARA",
         "EJ_RHO_SUCT", "EJ_RHO_DISCH", "EJ_A_T_DES", "EJ_A_M", "EJ_GEOM",
         "EJ_SHUTOFF_DES_BAR", "EJ_STALL_PHI_M", "EJ_SPINDLE_A_FULL",
         "EJ_HYD_FRAC_MAX", "EJ_CP_N", "EJ_CP_C", "EJ_CP_D"],
        seed=b6_switch.seed({"math": math,
                             "jet_pump": load("jet_pump"),
                             "h0_enthalpy": load("gap_g6_h0_enthalpy")}))


# ======================================================================================
# 1. The closure's loss coefficients and its monotonicity bound
# ======================================================================================

@pytest.mark.parametrize("name", ["K_NOZZLE", "K_ENTRY", "K_THROAT", "ETA_DIFF"])
def test_loss_coefficients_match_v1(v1_pump, name):
    """The four open-literature coefficients the geometry is back-solved through."""
    assert getattr(new_pump, name) == getattr(v1_pump, name)


@pytest.mark.parametrize("rho_s,rho_m", [(1133.0, 877.9), (1000.0, 1000.0), (800.0, 1200.0),
                                         (1.0, 1.0), (0.0, 877.9), (1133.0, 0.0)])
def test_monotonicity_margin_matches_v1(v1_pump, rho_s, rho_m):
    """Including both degenerate inputs, which return 0.0 rather than raising."""
    assert new_pump.monotonicity_margin(rho_s, rho_m) \
        == v1_pump.monotonicity_margin(rho_s, rho_m)


@pytest.mark.parametrize("k_entry", [0.0, 0.10, 0.5, 0.999, 1.0, 1.5])
def test_monotonicity_margin_matches_v1_off_default(v1_pump, k_entry):
    """The `k_entry >= 1.0` guard is the only branch, and both must take it identically."""
    assert new_pump.monotonicity_margin(1133.0, 877.9, k_entry) \
        == v1_pump.monotonicity_margin(1133.0, 877.9, k_entry)


# ======================================================================================
# 2. The closure itself
# ======================================================================================

#: The 322F001 anchors, as the geometry back-solve and the running model both see them.
DESIGN_PUMP = dict(rho_p=604.8, rho_s=1133.0, rho_m=877.9)

#: Nozzle and throat areas across the whole DDS spindle band, so the closure is compared at
#: every geometry the plant can actually put it in.
AREAS = [(d.A_T_DES_M2 * (40.0 + 0.6 * theta) / d.SPINDLE_A_FULL_PCT, d.A_M_M2)
         for theta in (10.0, 25.0, 50.0, 74.0, 90.0, 100.0)]


@pytest.mark.parametrize("a_t,a_m", AREAS)
@pytest.mark.parametrize("m_s_kgh", [0.0, 10_000.0, 57_561.0, 120_000.0, 400_000.0])
def test_discharge_rise_matches_v1(v1_pump, a_t, a_m, m_s_kgh):
    """The machine's characteristic, at every spindle position and over its whole curve."""
    assert new_pump.discharge_rise_bar(42_762.0, m_s_kgh, a_t, a_m, **DESIGN_PUMP) \
        == v1_pump.discharge_rise_bar(42_762.0, m_s_kgh, a_t, a_m, **DESIGN_PUMP)


@pytest.mark.parametrize("a_t,a_m", [(0.0, 0.002), (0.002, 0.002), (0.003, 0.002),
                                     (0.0002, 0.0002)])
def test_discharge_rise_degenerate_geometry_matches_v1(v1_pump, a_t, a_m):
    """A zero nozzle or a non-positive annulus returns 0.0 in both, rather than raising."""
    assert new_pump.discharge_rise_bar(42_762.0, 50_000.0, a_t, a_m, **DESIGN_PUMP) \
        == v1_pump.discharge_rise_bar(42_762.0, 50_000.0, a_t, a_m, **DESIGN_PUMP)


#: Motive flows from a dead pump to well over nameplate, and the lifts the loop can present.
MOTIVE_SWEEP = [0.0, 1.0, 4_276.0, 21_381.0, 38_486.0, 42_762.05427809782, 47_038.0, 64_143.0]
LIFT_SWEEP = [(140.0, 144.2), (140.0, 140.0), (140.0, 141.0), (140.0, 150.0),
              (140.0, 200.0), (144.2, 140.0), (0.5, 4.7), (0.0, 4.2)]


@pytest.mark.parametrize("m_p", MOTIVE_SWEEP)
@pytest.mark.parametrize("p_s,p_d", LIFT_SWEEP)
def test_entrainment_matches_v1(v1_pump, m_p, p_s, p_d):
    """Every field, including both bound flags and the two closure coefficients.

    The sweep deliberately includes a dead pump, a zero lift, a lift far above the machine's
    shutoff head, a REVERSED lift, and a suction so low that the cavitation ceiling binds.
    """
    ours = new_pump.entrainment_kgh(m_p, p_s, p_d, d.A_T_DES_M2, d.A_M_M2, **DESIGN_PUMP)
    theirs = v1_pump.entrainment_kgh(m_p, p_s, p_d, d.A_T_DES_M2, d.A_M_M2, **DESIGN_PUMP)
    assert ours == theirs


@pytest.mark.parametrize("pv", [0.0, 5.0, 40.0, 139.9, 140.0, 200.0])
def test_entrainment_cavitation_ceiling_matches_v1(v1_pump, pv):
    """The suction vapour pressure is the real ceiling, and both must clip at the same flow."""
    ours = new_pump.entrainment_kgh(42_762.0, 140.0, 144.2, d.A_T_DES_M2, d.A_M_M2,
                                    pv_suct_bara=pv, **DESIGN_PUMP)
    theirs = v1_pump.entrainment_kgh(42_762.0, 140.0, 144.2, d.A_T_DES_M2, d.A_M_M2,
                                     pv_suct_bara=pv, **DESIGN_PUMP)
    assert ours == theirs


@pytest.mark.parametrize("a_t,a_m", [(0.0, 0.002), (0.002, 0.002), (0.003, 0.002)])
def test_entrainment_degenerate_geometry_matches_v1(v1_pump, a_t, a_m):
    """A geometry the closure cannot be assembled from reports a stall in both."""
    assert new_pump.entrainment_kgh(42_762.0, 140.0, 144.2, a_t, a_m, **DESIGN_PUMP) \
        == v1_pump.entrainment_kgh(42_762.0, 140.0, 144.2, a_t, a_m, **DESIGN_PUMP)


# ======================================================================================
# 3. The geometry back-solve
# ======================================================================================

@pytest.mark.parametrize("dp_bar", [0.0, -1.0, 1.0, 25.0, 152.8, 400.0])
def test_nozzle_area_matches_v1(v1_pump, dp_bar):
    """Including the non-positive-differential guard."""
    assert new_pump.nozzle_area_m2(42_762.0, dp_bar, 604.8) \
        == v1_pump.nozzle_area_m2(42_762.0, dp_bar, 604.8)


def test_geometry_back_solve_matches_v1(v1_pump, v1):
    """Every field of the back-solve, at the 322F001 design duty.

    A 200-step bisection over a fixed-point inner solve — the place a port is most likely to
    drift, and the place where drift is least visible, because the areas then multiply
    through every entrainment the model ever computes.
    """
    ours = new_pump.solve_geometry(
        v1["EJ_MOTIVE_NH3_DES"], v1["EJ_SUC_TOT_DES"], v1["EJ_P_MOTIVE_BARA"],
        v1["EJ_P_SUCTION_BARA"], v1["EJ_P_DISCH_BARA"], 604.8,
        v1["EJ_RHO_SUCT"], v1["EJ_RHO_DISCH"])
    assert ours == v1["EJ_GEOM"]


def test_geometry_back_solve_refuses_an_unbracketed_duty(v1_pump):
    """Both raise rather than returning a geometry off the wrong root."""
    args = (42_762.0, 57_561.0, 165.0, 140.0, 400.0, 604.8, 1133.0, 877.9)
    with pytest.raises(ValueError):
        new_pump.solve_geometry(*args)
    with pytest.raises(ValueError):
        v1_pump.solve_geometry(*args)


# ======================================================================================
# 4. The design constants
# ======================================================================================

CONSTANTS = [
    ("MOTIVE_DES_KGH", "EJ_MOTIVE_NH3_DES"),
    ("MOTIVE_T_DES_C", "EJ_MOTIVE_T_DES_C"),
    ("OPEN_DES_PCT", "EJ_OPEN_DES"),
    ("SUCTION_DES_TOTAL_KGH", "EJ_SUC_TOT_DES"),
    ("T_SUCTION_DES_C", "EJ_T_SUCTION_C"),
    ("P_MOTIVE_DES_BARA", "EJ_P_MOTIVE_BARA"),
    ("P_SUCTION_DES_BARA", "EJ_P_SUCTION_BARA"),
    ("P_DISCHARGE_DES_BARA", "EJ_P_DISCH_BARA"),
    ("RHO_SUCTION", "EJ_RHO_SUCT"),
    ("RHO_DISCHARGE", "EJ_RHO_DISCH"),
    ("A_T_DES_M2", "EJ_A_T_DES"),
    ("A_M_M2", "EJ_A_M"),
    ("SHUTOFF_DES_BAR", "EJ_SHUTOFF_DES_BAR"),
    ("STALL_PHI_MOTIVE", "EJ_STALL_PHI_M"),
    ("SPINDLE_A_FULL_PCT", "EJ_SPINDLE_A_FULL"),
    ("HYDRAULIC_FRAC_MAX", "EJ_HYD_FRAC_MAX"),
    ("CP_MOTIVE", "EJ_CP_N"),
    ("CP_CARBAMATE", "EJ_CP_C"),
    ("CP_DISCHARGE", "EJ_CP_D"),
]


@pytest.mark.parametrize("ours,theirs", CONSTANTS)
def test_design_constants_match_v1(v1, ours, theirs):
    """Every scalar, to the bit."""
    assert getattr(d, ours) == v1[theirs]


@pytest.mark.parametrize("ours,theirs", [("MOTIVE_W", "EJ_MOTIVE_W"),
                                         ("SUCTION_DES_KGH", "EJ_SUCTION_KGH"),
                                         ("CARBAMATE_FRAC", "EJ_CARB_FRAC")])
def test_design_vectors_match_v1(v1, ours, theirs):
    """And the three component vectors, key for key."""
    assert getattr(d, ours) == v1[theirs]


def test_the_motive_temperature_agrees_with_the_pump_that_produces_it():
    """`data.unit_322f001` and `units.feed.station` must not drift apart.

    The data module cannot import the pump path — `data` sits below `units` — so it repeats
    the arithmetic. This is the assertion that keeps the two copies one number.
    """
    from ureasim.units.feed.station import pump_discharge_temperature_c
    from ureasim.data.unit_321 import T_BL_FEED_C

    assert pump_discharge_temperature_c(T_BL_FEED_C, d.P_SUCTION_DES_BARG) \
        == d.MOTIVE_T_DES_C


# ======================================================================================
# 5. The ejector
# ======================================================================================

FIELDS = [("comp", "comp_kgh"), ("total_kgh", "total_kgh"), ("suction_kgh", "suction_kgh"),
          ("mol_kmolh", "mol_kmolh"), ("MW", "mw"), ("T_C", "t_c"), ("P_bara", "p_bara"),
          ("rho", "rho"), ("vol_m3h", "vol_m3h"), ("mu", "mu"), ("phi_sp", "phi_spindle"),
          ("stalled", "stalled"), ("cavitating", "cavitating")]


def assert_same(v1, where, *args, **kwargs) -> None:
    """Drive both implementations with the same arguments and compare every field."""
    theirs = v1["ejector_322f001"](*args, **kwargs)
    ours = ejector_322f001(*args, **kwargs)
    for old_key, new_key in FIELDS:
        a, b = theirs[old_key], getattr(ours, new_key)
        assert a == b, f"{where}: {old_key} {a!r} != {b!r}"


def test_design_call_agrees(v1):
    """The licensor design point, every published field, bit for bit."""
    assert_same(v1, "design", v1["EJ_MOTIVE_NH3_DES"], v1["EJ_MOTIVE_T_DES_C"],
                v1["EJ_OPEN_DES"])


@pytest.mark.parametrize("motive", [0.0, 1e-7, 1e-6, 1.1e-6, 1.0, 100.0, 4276.0, 21381.0,
                                    34209.0, 38486.0, 42762.05427809782, 47038.0, 53452.0,
                                    64143.0])
def test_motive_sweep_agrees(v1, motive):
    """From a tripped pump through the stall point to well over nameplate.

    The 1e-6 triple brackets the no-flow branch's boundary exactly, because that branch
    returns a different temperature rather than a smaller flow.
    """
    assert_same(v1, f"motive={motive}", motive, v1["EJ_MOTIVE_T_DES_C"], v1["EJ_OPEN_DES"])


@pytest.mark.parametrize("opening", [-10.0, 0.0, 9.9, 10.0, 10.1, 25.0, 50.0, 74.0, 90.0,
                                     100.0, 120.0])
def test_spindle_sweep_agrees(v1, opening):
    """Across the whole HV-322602 band and both sides of the 10 % effective floor."""
    assert_same(v1, f"open={opening}", v1["EJ_MOTIVE_NH3_DES"], v1["EJ_MOTIVE_T_DES_C"],
                opening)


@pytest.mark.parametrize("level", [0.0, -0.5, 0.25, 0.5, 0.9, 1.0, 1.1, 1.249, 1.25, 1.26,
                                   2.0, 5.0])
def test_scrubber_level_sweep_agrees(v1, level):
    """Including both sides of the throat-choke ceiling and a negative level."""
    assert_same(v1, f"level={level}", v1["EJ_MOTIVE_NH3_DES"], v1["EJ_MOTIVE_T_DES_C"],
                v1["EJ_OPEN_DES"], level)


@pytest.mark.parametrize("xv_open", [True, False])
def test_block_valve_agrees(v1, xv_open):
    """XV-322903 shut leaves the motive alone and takes the suction to exactly zero."""
    assert_same(v1, f"xv={xv_open}", v1["EJ_MOTIVE_NH3_DES"], v1["EJ_MOTIVE_T_DES_C"],
                v1["EJ_OPEN_DES"], 1.0, xv_open)


@pytest.mark.parametrize("t_motive", [-30.0, 0.0, 28.933651556215118, 60.0, 120.0, 178.8])
def test_motive_temperature_sweep_agrees(v1, t_motive):
    """The discharge heat balance is linear in it, which is easy to get subtly wrong."""
    assert_same(v1, f"T={t_motive}", v1["EJ_MOTIVE_NH3_DES"], t_motive, v1["EJ_OPEN_DES"])


@pytest.mark.parametrize("p_s,p_d", [(140.0, 144.2), (135.0, 144.2), (140.0, 148.0),
                                     (120.0, 124.2), (140.0, 145.1), (140.0, 140.0),
                                     (1.0, 5.2)])
def test_live_loop_pressures_agree(v1, p_s, p_d):
    """The lift the jet has to make is what its capacity is most sensitive to."""
    assert_same(v1, f"p=({p_s},{p_d})", v1["EJ_MOTIVE_NH3_DES"], v1["EJ_MOTIVE_T_DES_C"],
                v1["EJ_OPEN_DES"], 1.0, True, None, p_s, p_d)


def test_a_live_carbamate_composition_agrees(v1):
    """The entrained split is the previous tick's scrubber overflow, not a frozen vector."""
    leaner = {"CO2": 0.30, "NH3": 0.52, "H2O": 0.17, "Urea": 0.01,
              "CH4": 0.0, "H2": 0.0, "N2": 0.0, "O2": 0.0, "Biuret": 0.0}
    assert_same(v1, "live carb_frac", v1["EJ_MOTIVE_NH3_DES"], v1["EJ_MOTIVE_T_DES_C"],
                v1["EJ_OPEN_DES"], 1.0, True, leaner)


def test_a_full_upset_state_agrees(v1):
    """Everything off design at once: half motive, spindle shut in, flooded sump, low loop."""
    assert_same(v1, "upset", 0.5 * v1["EJ_MOTIVE_NH3_DES"], 35.0, 20.0, 1.8, True, None,
                132.0, 140.0)


@pytest.mark.parametrize("hic", [0.0, 10.0, 35.5, 60.0, 74.0, 90.0, 100.0, 120.0])
def test_the_spindle_characteristic_is_v1s(v1, hic):
    """HV-322602's own capacity ratio, ``==`` V1's ``ej_spindle_phi``; 1.0 at the design 74 %."""
    assert spindle_phi(hic) == v1["ej_spindle_phi"](hic)
    if hic == v1["EJ_OPEN_DES"]:
        assert spindle_phi(hic) == 1.0
