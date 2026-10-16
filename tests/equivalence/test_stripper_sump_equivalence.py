"""V1 vs V1.1 — the 322E001 bottom sump, LIC-322501 and the LV-322501 letdown.

Evidence standard
-----------------
Mixed, and the mixture is deliberate.

Every CONSTANT and every HELPER below is V1's own object, lifted out of `main.py` by
`v1_loader.lift` or imported from `backend/consequence.py` and `backend/hydraulics.py` and
then executed. So `clamp`, `_pv_ok`, `_f_flow`, `_delay`, `_lag1`, `seal_fraction`,
`gas_density_ideal`, `blowthrough_kgh`, `transport_time_s`, `z_factor` and all sixteen design
constants are compared as code, not as text.

The WIRING — the order in which those objects are called and what is passed between them —
is TRANSCRIBED from `main.py` lines 7590-7685, because it lives inside `step_sim`, a
4100-line function that cannot be lifted statement by statement. That is the weaker evidence
standard recorded as handoff **A-12**, and it is the same standard unit 321 and the CO2 line
were held to. It is stated here rather than implied: a transcription error in
`v1_sump_step` below would make this file agree with itself.

What that still catches, and it is most of the risk: every constant, every helper, every
guard inside a helper, and the arithmetic of the six relations the sump is made of.

Source lines transcribed
------------------------
V1 `backend/main.py` 7590-7685.

LV-322501 flashes (handoff B-46, decided 2026-09-30)
----------------------------------------------------
The port runs the letdown on the IEC 60534 liquid law, choked on FL^2 (P - FF . Pv), with Uhde's
CONVAL FL and the bottoms' vapour pressure — the rigorous bubble point of the stripper's bottoms
at their temperature, scaled to CONVAL's 99.0 bar a. V1 runs an incompressible orifice law on the
full differential. ``v1_sump_step`` carries the switch ``flash`` (default True): the port's lines,
executed on V1's own ``hydraulics.valve_liquid_anchored`` and V1's own thermo service;
``flash=False`` is V1 verbatim.

LIC-322501 on the plant DCS's tuning (decided 2026-10-08)
--------------------------------------------------------
The port runs the table's 0.20 and 280 s with a 1.0 s derivative behind a 1.0 s filter, read
from the faceplate photograph; V1 runs 2.5 and 90 s with none. ``v1_sump_step`` carries the
switch ``table`` (default True): the port's tuning and derivative in V1's lines; ``table=False``
is V1 verbatim.
"""

from __future__ import annotations

import math
from collections import deque

import pytest

from ureasim.units.synthesis import stripper_sump as ss
from ureasim.units.synthesis.stripper_sump import BottomLevelLoop, StripperSump

from .v1_loader import lift, load, v1_available, v1_service

pytestmark = pytest.mark.skipif(not v1_available(),
                                reason="V1 reference tree not present on this machine")

#: Every V1 name the transcribed block reads.
V1_NAMES = [
    "clamp", "_pv_ok", "_f_flow", "_delay", "_lag1",
    "STRIP_BOT_DES_KGH", "LV322501_OPEN_DES", "LV322501_P_DOWN_BARA", "SYN_P_DES_BARA",
    "STRIP_RHO_BOTTOM", "STRIP_BOT_LINE_M3", "STRIP_SUMP_AREA_M2", "STRIP_LEVEL_SPAN_M",
    "STRIP_SUMP_NTU_DES", "STRIP_BOT_T_CRYST_C", "STRIP_T_DOWN_DES_C",
    "STRIP_T_BOTTOM_DES_C", "STRIP_T_TAU_S", "LIC_322501_KC", "LIC_322501_TI",
    "FEED_TD_MAX_S", "STRIP_LEVEL_SP_DES", "W_S208", "_w_norm",
]

#: LV-322501 as decided (B-46), written from Uhde's CONVAL sizing, UD-MR-G00-DZ-0042-032: FL^2
#: 0.845 at the mean flow, the bottoms boiling at 99.0 bar a at 173 C.
DECIDED_LV322501_FL = math.sqrt(0.845)
CONVAL_PV_BARA, CONVAL_T_C = 99.0, 173.0


@pytest.fixture(scope="module")
def v1():
    """V1's constants and helpers, with the three modules the block calls into."""
    # `deque` is seeded because V1's `_delay` builds its FIFO from it and the lifter
    # resolves only module-level V1 names, never `main.py`'s own imports.
    ns = lift(V1_NAMES, seed={"math": math, "deque": deque,
                              "consequence": load("consequence"),
                              "hydraulics": load("hydraulics"),
                              "real_gas": load("real_gas")})
    ns["thermo_service"] = v1_service()
    ns["iapws_if97"] = load("iapws_if97")
    return ns


def _v1_bottoms_pv(v1, bot_mass_pct: dict, t_bot_c: float) -> float:
    """B-46, the port's line written on V1's thermo service: the bottoms' rigorous bubble
    pressure at their temperature, on CONVAL's scale (99.0 bar a for PFD 208 at 173 C)."""
    svc, psat = v1["thermo_service"], v1["iapws_if97"].psat_bara
    scale = CONVAL_PV_BARA / svc.bubble_p(v1["W_S208"], CONVAL_T_C)
    t_eval = min(max(t_bot_c, 80.05), 209.95)
    try:
        pb = svc.bubble_p({k: v / 100.0 for k, v in bot_mass_pct.items()}, t_eval)
    except Exception:  # noqa: BLE001 — V1's own OutOfDomain, ValueError, ZeroDivisionError
        return scale * psat(t_bot_c)
    if t_eval != t_bot_c:
        pb = pb * psat(t_bot_c) / psat(t_eval)
    return scale * pb


# ======================================================================================
# The transcribed V1 block
# ======================================================================================

def v1_sump_step(v1, state: dict, lic: dict, strip: dict, p_syn_bara: float,
                 dt: float, flash: bool = True, table: bool = True) -> dict:
    """V1 `main.py` 7590-7685, transcribed, with V1's own constants and helpers; `flash` puts
    the port's letdown law in V1's (B-46), `table` LIC-322501's DCS tuning (2026-10-08).

    `state` stands in for the fields of V1's `State` that this block touches —
    `s.strip_level` and `s.tlag` — and `lic` for `s.LIC_322501`, which V1 already keeps as a
    plain dict. `strip` is the `stripper_322e001` return dict.
    """
    consequence = load("consequence")
    hydraulics = load("hydraulics")
    real_gas = load("real_gas")
    clamp = v1["clamp"]

    lic["pv_bad"] = not v1["_pv_ok"](state["strip_level"], lic["sp"])
    if lic["pv_bad"]:
        e_lvl = lic["e_prev"]
    else:
        e_lvl = state["strip_level"] - lic["sp"]
        if lic["mode"] == "AUTO" and table:  # ---- the DCS's tuning and filtered derivative ----
            level, prev = state["strip_level"], lic.get("level_prev")
            prev = level if prev is None else prev
            tf, td = ss.LIC_322501_TF_S, ss.LIC_322501_TD_S
            g_prev = lic.get("d_filt", 0.0)
            lic["d_filt"] = (tf / (tf + dt)) * g_prev + (td / (tf + dt)) * (level - prev)
            lic["op"] = clamp(
                lic["op"] + ss.LIC_322501_KC * ((e_lvl - lic["e_prev"])
                                                + (dt / ss.LIC_322501_TI) * e_lvl
                                                + (lic["d_filt"] - g_prev)),
                0.0, 100.0)
        elif lic["mode"] == "AUTO":
            lic["op"] = clamp(
                lic["op"] + v1["LIC_322501_KC"] * ((e_lvl - lic["e_prev"])
                                                   + (dt / v1["LIC_322501_TI"]) * e_lvl),
                0.0, 100.0)
        if table:
            lic["level_prev"] = state["strip_level"]
    lic["e_prev"] = e_lvl
    lv_open = clamp(lic["op"], 0.0, 100.0)

    dP_lv = max(p_syn_bara - v1["LV322501_P_DOWN_BARA"], 0.0)
    drain_kgh = v1["STRIP_BOT_DES_KGH"] * (lv_open / v1["LV322501_OPEN_DES"]) \
        * (dP_lv / max(v1["SYN_P_DES_BARA"] - v1["LV322501_P_DOWN_BARA"], 1e-6)) ** 0.5
    if flash:  # ---- B-46: the flashing letdown (the port's lines, V1's own IEC law) ----
        drain_kgh = hydraulics.valve_liquid_anchored(
            v1["STRIP_BOT_DES_KGH"], lv_open / 100.0, p_syn_bara, v1["LV322501_P_DOWN_BARA"],
            v1["STRIP_RHO_BOTTOM"], v1["LV322501_OPEN_DES"] / 100.0, v1["SYN_P_DES_BARA"],
            v1["LV322501_P_DOWN_BARA"], v1["STRIP_RHO_BOTTOM"], characteristic="linear",
            fl=DECIDED_LV322501_FL,
            pv_bara=min(_v1_bottoms_pv(v1, strip["bot_mass_pct"], strip["T_bot"]), p_syn_bara),
            pv_des_bara=_v1_bottoms_pv(v1, DESIGN_STRIP["bot_mass_pct"], DESIGN_STRIP["T_bot"]))
    f_drain = v1["_f_flow"](strip["T_bot"], 132.7)
    drain_kgh *= f_drain
    flag_solid = (f_drain < 1.0)

    seal_322501 = consequence.seal_fraction(state["strip_level"])
    drain_kgh *= seal_322501
    blow_322501_kgh = 0.0
    if seal_322501 < 1.0:
        rho_g_322501 = (consequence.gas_density_ideal(p_syn_bara, strip["T_bot"],
                                                      strip["top_MW"] or 30.0)
                        / real_gas.z_factor(strip["top_kmolh"], strip["T_bot"], p_syn_bara))
        blow_322501_kgh = consequence.blowthrough_kgh(
            v1["STRIP_BOT_DES_KGH"], v1["STRIP_RHO_BOTTOM"],
            v1["SYN_P_DES_BARA"] - v1["LV322501_P_DOWN_BARA"],
            lv_open / v1["LV322501_OPEN_DES"], rho_g_322501, p_syn_bara, dP_lv, seal_322501)
    flag_erosion = blow_322501_kgh > 0.0

    td_s = hydraulics.transport_time_s(v1["STRIP_BOT_LINE_M3"], v1["STRIP_RHO_BOTTOM"],
                                       strip["bot_kgh"], t_max_s=v1["FEED_TD_MAX_S"])
    delayed_bot_kgh = v1["_delay"](state["tlag"], "322E001_BOT_KGH_LAG", strip["bot_kgh"],
                                   td_s, dt)

    m_span_kg = v1["STRIP_SUMP_AREA_M2"] * v1["STRIP_LEVEL_SPAN_M"] * v1["STRIP_RHO_BOTTOM"]
    state["strip_level"] = clamp(
        state["strip_level"] + (delayed_bot_kgh - drain_kgh) / 3600.0 * dt / m_span_kg * 100.0,
        0.0, 100.0)
    lic["pv"] = state["strip_level"]

    T_amb_sump = v1["STRIP_BOT_T_CRYST_C"]
    if strip["T_bot"] > T_amb_sump:
        r_drain = drain_kgh / v1["STRIP_BOT_DES_KGH"]
        tau_sump = v1["STRIP_SUMP_NTU_DES"]
        T_bot_disp = (r_drain * (1.0 + tau_sump) * strip["T_bot"]
                      + tau_sump * (1.0 - r_drain) * T_amb_sump) / (r_drain + tau_sump)
        T_bot_disp = min(T_bot_disp, strip["T_steam"])
    else:
        T_bot_disp = strip["T_bot"]
    TT_323001 = v1["STRIP_T_DOWN_DES_C"] \
        + 0.7 * (T_bot_disp - v1["STRIP_T_BOTTOM_DES_C"])
    d_TT322004 = v1["_lag1"](state["tlag"], "TT322004", T_bot_disp, v1["STRIP_T_TAU_S"], dt)

    return {
        "level_pct": state["strip_level"],
        "lv_opening_pct": lv_open,
        "drain_kgh": drain_kgh,
        "blowthrough_kgh": blow_322501_kgh,
        "bottoms_in_kgh": delayed_bot_kgh,
        "bottoms_dead_time_s": td_s,
        "mushy_factor": f_drain,
        "seal_fraction": seal_322501,
        "t_out_c": T_bot_disp,
        "tt_322004_c": d_TT322004,
        "tt_323001_c": TT_323001,
        "dp_lv_bar": dP_lv,
        "solidification": flag_solid,
        "lv_erosion": flag_erosion,
    }


# ======================================================================================
# The stripper outputs the sump consumes
# ======================================================================================

#: The design tick, as `stripper.stripper_322e001` reports it at the licensor balance.
DESIGN_STRIP = {
    "bot_kgh": 130480.0,
    "T_bot": 172.0,
    "T_steam": 211.62164907088414,
    "top_MW": 25.963686431610723,
    "top_kmolh": {"NH3": 3571.6015782, "CO2": 1734.0, "H2O": 483.8, "Urea": 0.0,
                  "Biuret": 0.0, "N2": 0.0, "O2": 0.0},
    # The stripper's design bottoms, as it publishes them (B-46: their vapour pressure).
    "bot_mass_pct": dict(ss._BOTTOMS_DES.bot_mass_pct),
    "T_bot_des": ss._BOTTOMS_DES.t_bot,
}


def strip_at(**overrides) -> dict:
    """The design stripper tick with named fields replaced."""
    out = dict(DESIGN_STRIP)
    out["top_kmolh"] = dict(DESIGN_STRIP["top_kmolh"])
    out["bot_mass_pct"] = dict(DESIGN_STRIP["bot_mass_pct"])
    out.update(overrides)
    return out


#: Fields compared on every tick, with the tolerance each is compared to. Exact equality is
#: the default; the two that integrate are given a relative floor because the two
#: implementations reach them through a different number of float operations.
FIELDS = ("level_pct", "lv_opening_pct", "drain_kgh", "blowthrough_kgh", "bottoms_in_kgh",
          "bottoms_dead_time_s", "mushy_factor", "seal_fraction", "t_out_c",
          "tt_322004_c", "tt_323001_c", "dp_lv_bar", "solidification", "lv_erosion")


def assert_same(ours, theirs: dict, where: str) -> None:
    """Compare one tick field by field, naming the field and the state on a failure."""
    for name in FIELDS:
        a = getattr(ours, name)
        b = theirs[name]
        if isinstance(b, bool):
            assert a == b, f"{where}: {name} {a} != {b}"
        else:
            assert a == pytest.approx(b, rel=1e-12, abs=1e-12), \
                f"{where}: {name} {a!r} != {b!r}"


def drive(v1, ticks, dt: float = 1.0, level0: float = 50.0, mode: str = "AUTO",
          sp: float = 50.0, op0: float = 46.1, flash: bool = True):
    """Drive both implementations through the same tick sequence and compare each one.

    `ticks` is a sequence of ``(strip_dict, p_syn_bara)``. Both sides start from the same
    seeded state, which is the design state unless a test says otherwise. Tests reach this
    through the `run_both` fixture, which binds the lifted V1 namespace to it.
    """
    sump = StripperSump(level_pct=level0)
    lic_new = BottomLevelLoop(op=op0, sp=sp, pv=level0, e_prev=0.0, mode=mode)

    state = {"strip_level": level0, "tlag": {}}
    lic_old = {"op": op0, "sp": sp, "pv": level0, "e_prev": 0.0, "mode": mode,
               "pv_bad": False}

    for i, (strip, p_syn) in enumerate(ticks):
        ours = sump.step(lic_new, strip["bot_kgh"], strip["T_bot"], strip["T_steam"],
                         strip["top_kmolh"], strip["top_MW"], p_syn, strip["bot_mass_pct"], dt)
        theirs = v1_sump_step(v1, state, lic_old, strip, p_syn, dt, flash)
        assert_same(ours, theirs, f"tick {i}")
        assert lic_new.op == pytest.approx(lic_old["op"], rel=1e-12, abs=1e-12)
        assert lic_new.e_prev == pytest.approx(lic_old["e_prev"], rel=1e-12, abs=1e-12)
        assert lic_new.pv_bad == lic_old["pv_bad"]
    return sump, lic_new


@pytest.fixture
def run_both(v1):
    """`drive`, with the lifted V1 namespace already bound."""
    def _run(ticks, **kwargs):
        return drive(v1, ticks, **kwargs)
    return _run


# ======================================================================================
# 1. The design point
# ======================================================================================

def test_design_tick_agrees(run_both):
    """One tick at the licensor balance, every published field."""
    run_both([(strip_at(), 140.7)])


def test_design_holds_for_a_long_run(run_both):
    """Six hundred ticks at design. Any drift between the two integrators shows up here."""
    run_both([(strip_at(), 140.7)] * 600)


# ======================================================================================
# 2. Level excursions and the controller
# ======================================================================================

@pytest.mark.parametrize("level0", [0.0, 0.5, 1.5, 2.9, 3.0, 10.0, 35.0, 50.0, 65.0,
                                    90.0, 100.0])
def test_level_excursions_agree(level0, run_both):
    """Across the seal ramp, the design band and the top of the span."""
    run_both([(strip_at(), 140.7)] * 40, level0=level0)


@pytest.mark.parametrize("sp", [20.0, 45.0, 50.0, 55.0, 80.0])
def test_set_point_moves_agree(sp, run_both):
    """A set-point change gives a proportional kick in this form; both must give the same one."""
    run_both([(strip_at(), 140.7)] * 60, sp=sp)


def test_manual_mode_agrees(run_both):
    """In MAN the output is frozen but the error is still tracked for a bumpless return."""
    run_both([(strip_at(), 140.7)] * 30, mode="MAN", level0=70.0)


@pytest.mark.parametrize("op0", [0.0, 10.0, 46.1, 80.0, 100.0])
def test_initial_stroke_agrees(op0, run_both):
    """Including both output rails, where the clamp is what decides the answer."""
    run_both([(strip_at(), 140.7)] * 30, op0=op0)


def test_a_bad_level_freezes_both_loops_identically(v1):
    """A non-finite level holds the last good error and skips the increment in both.

    The contrast with V1's PIC-322203 is the point: there the history advances past the bad
    sample and the output latches (As-Built §XVII.5). Here it does not, in V1 and in the
    rewrite alike.
    """
    good = (strip_at(), 140.7)
    ticks = [good] * 5
    sump = StripperSump(level_pct=62.0)
    lic_new = BottomLevelLoop(op=46.1, sp=50.0, pv=62.0, e_prev=0.0, mode="AUTO")
    state = {"strip_level": 62.0, "tlag": {}}
    lic_old = {"op": 46.1, "sp": 50.0, "pv": 62.0, "e_prev": 0.0, "mode": "AUTO",
               "pv_bad": False}

    for strip, p_syn in ticks:
        sump.step(lic_new, strip["bot_kgh"], strip["T_bot"], strip["T_steam"],
                  strip["top_kmolh"], strip["top_MW"], p_syn, strip["bot_mass_pct"], 1.0)
        v1_sump_step(v1, state, lic_old, strip, p_syn, 1.0)

    # Inject a NaN level into both, without touching anything else.
    sump.level_pct = float("nan")
    state["strip_level"] = float("nan")
    op_before, e_before = lic_new.op, lic_new.e_prev
    sump.step(lic_new, DESIGN_STRIP["bot_kgh"], DESIGN_STRIP["T_bot"],
              DESIGN_STRIP["T_steam"], DESIGN_STRIP["top_kmolh"], DESIGN_STRIP["top_MW"],
              140.7, DESIGN_STRIP["bot_mass_pct"], 1.0)
    v1_sump_step(v1, state, lic_old, strip_at(), 140.7, 1.0)

    assert lic_new.pv_bad is True and lic_old["pv_bad"] is True
    assert lic_new.op == op_before == lic_old["op"]
    assert lic_new.e_prev == e_before == lic_old["e_prev"]


# ======================================================================================
# 3. The letdown head
# ======================================================================================

@pytest.mark.parametrize("p_syn", [0.0, 1.013, 3.9, 4.0, 4.1, 40.0, 100.0, 140.7, 144.0,
                                   170.0])
def test_synthesis_pressure_sweep_agrees(p_syn, run_both):
    """From a black start through the design loop pressure to a relief-valve lift."""
    run_both([(strip_at(), p_syn)] * 30)


def test_a_depressurised_loop_drains_nothing_in_either_version(run_both):
    """The head collapses to zero at the downstream reference and the letdown stops."""
    run_both([(strip_at(), 4.0)] * 10, level0=80.0)
    run_both([(strip_at(), 2.0)] * 10, level0=80.0)


# ======================================================================================
# 4. The mushy zone
# ======================================================================================

@pytest.mark.parametrize("t_bot", [200.0, 180.0, 172.0, 140.0, 137.71, 137.7, 135.0,
                                   132.71, 132.7, 132.69, 120.0, 25.0])
def test_bottoms_temperature_sweep_agrees(t_bot, run_both):
    """Through the whole mushy band and past the bypass at the crystallisation floor."""
    run_both([(strip_at(T_bot=t_bot), 140.7)] * 30)


def test_the_energy_balance_bypass_boundary_agrees(run_both):
    """The `T_bot > T_cryst` branch is a strict inequality in both implementations."""
    run_both([(strip_at(T_bot=132.7), 140.7)] * 5)
    run_both([(strip_at(T_bot=132.7000000001), 140.7)] * 5)


# ======================================================================================
# 5. The lost seal and the blow-through
# ======================================================================================

@pytest.mark.parametrize("level0", [0.0, 0.3, 1.0, 1.5, 2.0, 2.99, 2.999999])
def test_blowthrough_agrees_across_the_seal_ramp(level0, run_both):
    """Including the SRK compressibility correction, which is a real-gas call in both."""
    run_both([(strip_at(), 144.0)] * 20, level0=level0)


def test_an_empty_top_gas_vector_takes_the_same_fallback(run_both):
    """A cold stripper has no composition; both fall back to MW = 30 rather than dividing."""
    empty = strip_at(top_MW=0.0, top_kmolh={"NH3": 0.0, "CO2": 0.0, "H2O": 0.0})
    run_both([(empty, 140.7)] * 5, level0=1.0)


# ======================================================================================
# 6. The bottoms transit and the thermal lag
# ======================================================================================

@pytest.mark.parametrize("bot_kgh", [0.0, 1.0, 13048.0, 65241.0, 130480.0, 200000.0])
def test_bottoms_flow_sweep_agrees(bot_kgh, run_both):
    """The transit time is rho.V/m_dot, so a turned-down stripper delays for longer."""
    run_both([(strip_at(bot_kgh=bot_kgh), 140.7)] * 120)


@pytest.mark.parametrize("dt", [0.05, 0.25, 1.0, 2.0, 5.0])
def test_sub_step_sizes_agree(dt, run_both):
    """Both the FIFO and the first-order lag must be stable against a variable sub-step.

    V1's scheduler advances each tick in bounded sub-steps whose remainder is often a tiny
    numerical crumb, so this is the case the two stateful helpers were written for.
    """
    run_both([(strip_at(), 140.7)] * 200, dt=dt)


def test_a_load_ramp_agrees_tick_for_tick(run_both):
    """The transient case: a feed ramp moves the transit, the level and the temperature."""
    ticks = []
    for i in range(300):
        scale = 1.0 - 0.6 * min(i / 150.0, 1.0)
        ticks.append((strip_at(bot_kgh=130480.0 * scale,
                               T_bot=172.0 - 12.0 * (1.0 - scale)), 140.7))
    run_both(ticks)


# ======================================================================================
# 7. The decided divergence: LV-322501 flashes (handoff B-46), both sides
# ======================================================================================

def test_the_flashing_letdown_decided_divergence(v1):
    """B-46, decided 2026-09-30. The bottoms 8 C hotter boil at 115.0 bar a, and the port's
    LV-322501 chokes harder on FL^2 (P - FF . Pv): at the design stroke it passes 92.5 % of the
    PFD bottoms; V1's orifice law, with no vapour pressure, passes all of them. A loop 3 bar low:
    V1 1.1 % less, on the full differential; the port 2.4 %, on the choked one."""
    def lic():
        return {"op": 46.1, "sp": 50.0, "pv": 50.0, "e_prev": 0.0, "mode": "MAN",
                "pv_bad": False}
    for strip, p_syn, port, verbatim in ((strip_at(T_bot=180.0), 140.7, 0.9248, 1.0),
                                         (strip_at(), 137.7, 0.9757, 0.9890)):
        drive(v1, [(strip, p_syn)], mode="MAN")       # the port is V1 on the port's lines
        a = v1_sump_step(v1, {"strip_level": 50.0, "tlag": {}}, lic(), strip, p_syn, 1.0,
                         flash=False)
        b = v1_sump_step(v1, {"strip_level": 50.0, "tlag": {}}, lic(), strip, p_syn, 1.0)
        assert a["drain_kgh"] / ss.BOTTOMS_DES_KGH == pytest.approx(verbatim, abs=1e-4)
        assert b["drain_kgh"] / ss.BOTTOMS_DES_KGH == pytest.approx(port, abs=1e-4)



# ======================================================================================
# 8. The decided divergence: LIC-322501 on the plant DCS's tuning (2026-10-08), both sides
# ======================================================================================

def test_lic_322501_on_the_dcs_tuning_decided_divergence(v1):
    """The level 15 % above its set point, ten minutes in AUTO. V1's 2.5 and 90 s strike the
    valve to 84.0 % on the first tick and hold the level at its set point after ten minutes
    (50.005 %); the plant DCS's 0.20 and 280 s, with its 1 s filtered derivative, open it to
    49.1 %, and the slower loop swings the level through its set point to 47.4 % at ten minutes.
    The port is V1's lines on the DCS's tuning, to the bit."""
    ticks = [(strip_at(), 140.7)] * 600
    sump, lic = drive(v1, ticks, level0=65.0)          # the port, against the switched lines
    runs = {}
    for table in (False, True):
        state = {"strip_level": 65.0, "tlag": {}}
        lic_old = {"op": 46.1, "sp": 50.0, "pv": 65.0, "e_prev": 0.0, "mode": "AUTO",
                   "pv_bad": False}
        first = None
        for strip, p_syn in ticks:
            v1_sump_step(v1, state, lic_old, strip, p_syn, 1.0, table=table)
            first = lic_old["op"] if first is None else first
        runs[table] = (first, lic_old["op"], state["strip_level"])
    assert v1["LIC_322501_KC"] == 2.5 and v1["LIC_322501_TI"] == 90.0
    assert (ss.LIC_322501_KC, ss.LIC_322501_TI, ss.LIC_322501_TD_S, ss.LIC_322501_TF_S) == (
        0.20, 280.0, 1.0, 1.0)
    assert runs[False][0] == pytest.approx(84.017, abs=1e-3)
    assert runs[False][2] == pytest.approx(50.005, abs=1e-3)
    assert runs[True][0] == pytest.approx(49.111, abs=1e-3)
    assert runs[True][2] == pytest.approx(47.393, abs=1e-3)
    assert runs[True][1:] == (lic.op, sump.level_pct)
