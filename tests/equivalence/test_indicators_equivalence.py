"""V1 <-> V1.1 equivalence for the synthesis loop's displayed indicators — V1's section 6.

What is being proved
--------------------
V1 relaxes ten published indications every physics step (``main.py`` 8188-8204, less TT-322004,
which 322E001's sump carries and `test_stripper_sump_equivalence.py` proves). Those ten lines are
statements inside `step_sim`, so they are TRANSCRIBED below (declared); everything they call —
``_lag1``, ``react_nc_ratio``, the eight time constants and ``SYN_P_MAX_BARA`` — is lifted out of
``main.py`` and executed. The port's `SynthesisIndicators` and the transcription are fed the same
process values tick by tick, through a design hold, a step on every input and a ramp back, and
agree with ``==`` on every indicator on every tick. The constants are V1's to the bit.
"""

from __future__ import annotations

import pytest

from ureasim.data import indicator_lags as lags
from ureasim.data.unit_322r001 import OVERFLOW_DES_KMOLH
from ureasim.units.synthesis.indicators import SynthesisIndicators
from tests.equivalence.v1_loader import lift, load, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

TAUS = ["EJ_T_TAU_S", "STRIP_T_TAU_S", "HPCC_T_TAU_S", "HPCC_P_TAU_S", "SCRUB_T_TAU_S",
        "OFFGAS_T_TAU_S", "CCW_T_TAU_S", "AT_322701_TAU_S"]


@pytest.fixture(scope="module")
def v1():
    return lift(["_lag1", "react_nc_ratio", "SYN_P_MAX_BARA", *TAUS],
                seed={"iapws_if97": load("iapws_if97")})


def _section_6(v1, store, x, dt):
    """``main.py`` 8188-8204, transcribed (TT-322004 left to 322E001's sump)."""
    lag = v1["_lag1"]
    return (
        lag(store, "TT322012", x["t_ejector_c"], v1["EJ_T_TAU_S"], dt),
        lag(store, "TT322013", x["t_top_c"], v1["STRIP_T_TAU_S"], dt),
        lag(store, "TT323001", x["tt_323001_c"], v1["STRIP_T_TAU_S"], dt),
        lag(store, "TT322010", x["t_prod_c"], v1["HPCC_T_TAU_S"], dt),
        min(lag(store, "HPCCP", x["p_bub_bara"], v1["HPCC_P_TAU_S"], dt), v1["SYN_P_MAX_BARA"]),
        lag(store, "TT322002", x["t_overflow_c"], v1["SCRUB_T_TAU_S"], dt),
        lag(store, "TT322011", x["t_offgas_c"], v1["OFFGAS_T_TAU_S"], dt),
        lag(store, "TT322011l", x["t_purge_c"], v1["OFFGAS_T_TAU_S"], dt),
        lag(store, "TT329125", x["t_ccw_out_c"], v1["CCW_T_TAU_S"], dt),
        lag(store, "AT322701", v1["react_nc_ratio"](x["overflow_kmolh"]),
            v1["AT_322701_TAU_S"], dt),
    )


def test_the_time_constants_are_v1s(v1):
    for name in TAUS:
        assert getattr(lags, name) == v1[name], name
    assert lags.HPCC_P_DISPLAY_MAX_BARA == v1["SYN_P_MAX_BARA"]


def _inputs(k: int) -> dict:
    """Design for 50 ticks, every input stepped for 1500, then ramped back over 1500."""
    design = dict(t_ejector_c=107.56, t_top_c=187.0, tt_323001_c=119.0, t_prod_c=170.0,
                  p_bub_bara=144.2, t_overflow_c=178.8, t_offgas_c=114.0, t_purge_c=94.8,
                  t_ccw_out_c=95.0)
    if k < 50:
        f = 0.0
    elif k < 1550:
        f = 1.0
    else:
        f = max(0.0, 1.0 - (k - 1550) / 1500.0)
    x = {key: v + f * (7.3 if key != "p_bub_bara" else 41.0) for key, v in design.items()}
    comp = dict(OVERFLOW_DES_KMOLH)
    comp["CO2"] = comp["CO2"] * (1.0 - 0.2 * f)
    x["overflow_kmolh"] = comp
    return x


def test_the_ten_lags_are_v1s_on_every_tick(v1):
    """3100 ticks of hold, step and ramp: every indicator ``==`` V1's on every tick, the
    PI-322E002 cap binding through the step."""
    port, store = SynthesisIndicators(), {}
    capped = 0
    for k in range(3100):
        x = _inputs(k)
        r = port.step(**x, dt=0.1)
        got = (r.tt_322012_c, r.tt_322013_c, r.tt_323001_c, r.tt_322010_c, r.pi_322e002_bara,
               r.tt_322002_c, r.tt_322011_c, r.tt_322011_lp_c, r.tt_329125_c, r.at_322701)
        assert got == _section_6(v1, store, x, 0.1), k
        capped += r.pi_322e002_bara == lags.HPCC_P_DISPLAY_MAX_BARA
    assert capped > 1000
