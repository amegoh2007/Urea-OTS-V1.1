"""V1 <-> V1.1 equivalence for the CO2 feed line and 320K002.

What is being proved
--------------------
The same mixed standard as unit 321, and the mixture is better here: almost everything is
executed V1 code. The compressor map, the polytropic head, the check valve, the anchored
compressible vent valve, the vapour-space pressure equation, the transport-time law and the
dead-time FIFO are all V1's own modules — `machines.py` and `hydraulics.py` import cleanly, so
they are loaded rather than lifted. Only the roughly twenty assignment statements of
`step_sim` that wire them together are transcribed into `_v1_co2_block`.

Four properties are pinned beyond tick-for-tick equality, each because it is a behaviour the
algebraic form this replaced could not produce at all:

  * **the design fixed point is a literal zero imbalance.** Machine delivery, check-valve pass
    and vent flow close exactly at 144.2 bar a against a 140.7 bar a loop, so dP/dt is 0.0 and
    the node does not move.
  * **the tie-in SHUTS on reversal.** When the loop over-pressures past the line, the feed
    goes to exactly zero rather than to a small number.
  * **the node LAGS.** A step in the loop pressure does not move the line pressure
    instantaneously, which is the whole point of giving it a volume.
  * **PIC-322203 is installed as `ProcessLoop(act=-1)`**, and on every finite measurement it
    is V1's inline block to the bit. On a non-finite one it deliberately is not: V1 latches
    the vent wide open, the rewrite freezes it for one tick. The process engineer chose the
    rewrite's form (As-Built §XVII.5), and both sides of the divergence are asserted.

PV-322203 (handoff B-44, decided 2026-09-30). The port runs the vent on CCI's sheet: equal
percentage, anchored at the 79.33 % stroke where its rated Cv passes the design CO2, where V1
anchors the feed wide open on a linear trim. V1's own ``valve_gas_anchored`` takes both, so the
transcription's switch ``valves_decided`` (default True) only hands it the decided trim and
anchor stroke; ``valves_decided=False`` is V1 verbatim. Both sides are asserted below.

320K002 (decided 2026-10-08, As-Built §LXII.1). The machine is outside the simulator's scope: a
boundary feed whose hardwired governor delivers the demanded CO2 into the line, with no curve,
speed, surge or stonewall, the line floored on the PFD's 1.3 bar a suction. V1 ran a parabola
fitted to two representative numbers under an integral governor (tau 8 s, ceiling 1.15 of its
design speed) from an assumed 1.6 bar a. The transcription takes its machine as an argument:
``machine=None`` hands V1's block the boundary, so the rest of the block is proved against the
port; ``_v1_machine(v1)`` is V1 verbatim. Both are asserted below.
"""

from __future__ import annotations

import ast
import math
from types import SimpleNamespace

import pytest

from ureasim.data import control_valves as cvd
from ureasim.data import unit_320 as d
from ureasim.units.synthesis.co2_compressor import delivery_kgh
from ureasim.units.synthesis.co2_line import (
    CO2FeedLine,
    tie_in_flow_kgh,
    vent_flow_kgh,
    vent_pressure_loop,
)
from tests.equivalence import decided_valves as dv
from tests.equivalence.v1_loader import V1_BACKEND, load, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

DT = 0.1
CO2_DES_KGH = 54618.0
CO2_DES_TH = CO2_DES_KGH / 1000.0
SYN_DES_BARA = 140.7

#: PV-322203 as decided (B-44): CCI's equal-percentage trim, anchored at the stroke its rated Cv
#: gives for the design CO2 [fraction].
DECIDED_VENT = {"characteristic": "equal_pct",
                "h_des": dv.design_stroke_pct(cvd.PV_322203, CO2_DES_KGH) / 100.0}
V1_VENT = {"characteristic": "linear", "h_des": 1.0}


def _v1_module() -> dict:
    """Lift the four wiring helpers out of V1 `main.py`; load the rest as real modules."""
    text = (V1_BACKEND / "main.py").read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(text)
    wanted = {"clamp", "_pv_ok", "_delay", "_feed_transport_td_s"}
    ns: dict = {"math": math, "hydraulics": load("hydraulics"),
                "deque": __import__("collections").deque, "FEED_TD_MAX_S": 3600.0}
    for stmt in tree.body:
        if isinstance(stmt, ast.FunctionDef) and stmt.name in wanted:
            exec(compile(ast.Module([stmt], []), "<v1 main.py>", "exec"), ns)
    missing = wanted - set(ns)
    assert not missing, f"could not lift {sorted(missing)} out of V1 main.py"
    ns["machines"] = load("machines")
    return ns


@pytest.fixture(scope="module")
def v1():
    return _v1_module()


# --------------------------------------------------------------------------------------
# V1's constants, derived here the way V1 derives them
# --------------------------------------------------------------------------------------

V1_MW_COMP = {"CO2": 44.0098, "H2O": 18.0152, "N2": 28.0134, "O2": 31.9988}
V1_MOLFRAC = {"CO2": 0.9524, "H2O": 0.0061, "N2": 0.0355, "O2": 0.0060}
V1_FEED_MW = sum(V1_MOLFRAC[k] * V1_MW_COMP[k] for k in V1_MOLFRAC)
V1_P_DES_BARA = 144.2
V1_T_FEED_C = 120.0
V1_VENT_T_DES_K = V1_T_FEED_C + 273.15
V1_VENT_P_BARA = 5.0
V1_SUCT_P_BARA = 1.6
V1_SUCT_T_K = 40.0 + 273.15
#: The PFD's suction (stream 105), the decided line's floor (2026-10-08).
DECIDED_SUCT_P_BARA = 1.3
V1_GAMMA = 1.29
V1_ETA_POLY = 0.78
V1_STAGES = 4
V1_GOV_TAU_S = 8.0
V1_SPEED_MAX = 1.15
V1_PIC_KC = 1.0
V1_PIC_TI = 2.0
#  Transcribed, not lifted: V1 writes the set-point span as literals inside `handle_cmd`,
#  the "pic_set" branch, which clamps the operator's set point and the bumpless
#  set-point-to-PV transfer alike.
V1_PIC_SP_LO = 120.0
V1_PIC_SP_HI = 175.0
V1_DP_HP_DES = V1_P_DES_BARA - SYN_DES_BARA
V1_CRACK_BAR = 0.02 * V1_DP_HP_DES
V1_LINE_KG = CO2_DES_KGH / 3600.0 * 345.0
V1_LINE_RHO = 242.70
V1_LINE_V_M3 = V1_LINE_KG / V1_LINE_RHO
V1_NM3_PER_KMOL = 22.414
V1_PSV_SET = 160.0 + 1.013
V1_PIC_SP = V1_PSV_SET + 2.0 * (V1_P_DES_BARA - SYN_DES_BARA)
#: SV-32201's set and PIC-322203's set point on the standard atmosphere (handoff B-6, decided
#: 2026-10-07); `_v1_state` seeds V1's controller on them unless asked for V1 verbatim.
DECIDED_PSV_SET = 160.0 + 1.01325
DECIDED_PIC_SP = DECIDED_PSV_SET + 2.0 * (V1_P_DES_BARA - SYN_DES_BARA)


def test_every_constant_the_rewrite_carries_is_v1s_own_number():
    assert d.CO2_FEED_MOLFRAC == V1_MOLFRAC
    assert d.CO2_FEED_MW == V1_FEED_MW
    assert d.CO2_P_DES_BARA == V1_P_DES_BARA
    assert d.CO2_T_FEED_C == V1_T_FEED_C
    assert d.CO2_VENT_T_DES_K == V1_VENT_T_DES_K
    assert d.CO2_VENT_P_BARA == V1_VENT_P_BARA
    assert d.CO2_VENT_MW_DES == V1_FEED_MW
    # 320K002 a boundary feed (decided 2026-10-08): the PFD's suction floors the line; V1's
    # governor constants have no counterpart.
    assert (d.CO2_K_SUCT_P_BARA, V1_SUCT_P_BARA) == (DECIDED_SUCT_P_BARA, 1.6)
    assert not hasattr(d, "CO2_K_SPEED_MAX") and not hasattr(d, "CO2_K_GOV_TAU_S")
    assert d.CO2_K_GAMMA == V1_GAMMA
    assert d.PIC_322203_KC == V1_PIC_KC
    assert d.PIC_322203_TI == V1_PIC_TI
    assert (d.PIC_322203_SP_LO_BARA, d.PIC_322203_SP_HI_BARA) == (V1_PIC_SP_LO, V1_PIC_SP_HI)
    assert d.SYN_P_DES_BARA == SYN_DES_BARA
    # SV-32201's set on the standard atmosphere (handoff B-6, decided): V1's 161.013 on 1.013.
    assert (d.SYN_PSV_SET_BARA, V1_PSV_SET) == (160.0 + 1.01325, 161.013)
    assert d.CO2_DP_HP_DES == V1_DP_HP_DES
    assert d.CO2_CHECK_CRACK_BAR == V1_CRACK_BAR
    assert d.FEED_CO2_LINE_KG == V1_LINE_KG
    assert d.CO2_LINE_RHO_DES == V1_LINE_RHO
    assert d.CO2_LINE_V_M3 == V1_LINE_V_M3


def test_the_tie_in_design_differential_is_a_subtraction_not_a_rounded_decimal():
    """Handoff A-13's rule, at the first check valve on the plant.

    V1 already writes `CO2_P_DES_BARA - SYN_P_DES_BARA`, so this site satisfies the rule by
    inheritance. The assertion is here so the next site cannot quietly stop doing it: the
    check valve's anchor is bit-exact only when the live differential evaluates to the same
    float as the design one.
    """
    assert d.CO2_DP_HP_DES == d.CO2_P_DES_BARA - d.SYN_P_DES_BARA
    assert tie_in_flow_kgh(d.CO2_P_DES_BARA, d.SYN_P_DES_BARA, 1.0) == pytest.approx(
        CO2_DES_KGH, rel=1e-12)


def test_both_machines_deliver_the_design_duty(v1):
    """V1's at its speed 1.0 delivers the design CO2 into 144.2 bar a to a part in 1e9; the
    boundary delivers the demand, exactly."""
    assert _v1_machine(v1).delivery(V1_P_DES_BARA, 1.0)["kgh"] == pytest.approx(
        CO2_DES_KGH, rel=1e-9)
    assert delivery_kgh(CO2_DES_KGH) == CO2_DES_KGH


# --------------------------------------------------------------------------------------
# The branches, against V1's own hydraulics
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("p_node", [1.6, 60.0, 140.0, 140.77, 144.2, 150.0, 170.0])
@pytest.mark.parametrize("p_syn", [120.0, 140.7, 150.0, 165.0])
def test_the_tie_in_matches_v1(p_node, p_syn, v1):
    a = v1["hydraulics"].check_valve_kgh(CO2_DES_KGH, p_node, p_syn, V1_DP_HP_DES,
                                         V1_CRACK_BAR)
    assert tie_in_flow_kgh(p_node, p_syn, 1.0) == a
    assert tie_in_flow_kgh(p_node, p_syn, 0.0) == 0.0


def _v1_vent(v1, p_node, opening, vent):
    """V1's ``valve_gas_anchored`` on the vent, on V1's trim and anchor or the decided ones."""
    return v1["hydraulics"].valve_gas_anchored(
        CO2_DES_KGH, opening / 100.0, p_node, V1_VENT_P_BARA, V1_VENT_T_DES_K,
        vent["h_des"], V1_P_DES_BARA, V1_VENT_P_BARA, V1_VENT_T_DES_K, V1_FEED_MW,
        gamma=V1_GAMMA, characteristic=vent["characteristic"], mw_des=V1_FEED_MW)


@pytest.mark.parametrize("p_node", [5.0, 20.0, 100.0, 144.2, 170.0])
@pytest.mark.parametrize("opening", [0.0, 5.0, 14.0, 50.0, 100.0])
def test_the_vent_matches_v1(p_node, opening, v1):
    """V1's own law, handed the decided trim and anchor stroke."""
    assert vent_flow_kgh(p_node, opening) == _v1_vent(v1, p_node, opening, DECIDED_VENT)


def test_a_shut_vent_passes_exactly_zero():
    """A commanded zero really is zero — not the 2 % an equal-% trim's exponential implies."""
    assert vent_flow_kgh(144.2, 0.0) == 0.0


def test_the_vent_on_ccis_sheet_decided_divergence(v1):
    """B-44, both sides. The design CO2 at the design line pressure: V1's vent wide open, the
    port's at 79.33 %. Wide open the port's passes 2.2 times the feed, choked; half open V1's
    linear trim passes half the feed and the port's equal percentage 31.7 %."""
    assert DECIDED_VENT["h_des"] == pytest.approx(0.7933, abs=1e-4)
    assert _v1_vent(v1, 144.2, 100.0, V1_VENT) == pytest.approx(CO2_DES_KGH, rel=1e-12)
    assert vent_flow_kgh(144.2, 79.33039186000349) == pytest.approx(CO2_DES_KGH, rel=1e-9)
    assert vent_flow_kgh(144.2, 100.0) / CO2_DES_KGH == pytest.approx(2.245, abs=1e-3)
    assert _v1_vent(v1, 144.2, 50.0, V1_VENT) / CO2_DES_KGH == pytest.approx(0.5, rel=1e-9)
    assert vent_flow_kgh(144.2, 50.0) / CO2_DES_KGH == pytest.approx(0.317, abs=1e-3)


def test_the_tie_in_shuts_on_reversal_rather_than_passing_a_small_number():
    """A synthesis over-pressure must stop the CO2 feed, not reverse it into the machine."""
    assert tie_in_flow_kgh(144.2, 150.0, 1.0) == 0.0
    assert tie_in_flow_kgh(144.2, 144.2, 1.0) == 0.0
    assert tie_in_flow_kgh(144.2, 144.15, 1.0) == 0.0      # inside the crack band
    assert tie_in_flow_kgh(144.2, 144.0, 1.0) > 0.0


def test_the_tie_in_is_not_capped_at_the_design_flow():
    """The defect the delivery fraction had: a line pushing harder than design passes more."""
    assert tie_in_flow_kgh(160.0, 140.7, 1.0) > CO2_DES_KGH


# --------------------------------------------------------------------------------------
# V1's CO2-line block, transcribed
# --------------------------------------------------------------------------------------
#  Copied line for line from `backend/main.py` step_sim, from "PV-322203 effective opening"
#  through `pic["pv"] = P_line_bara`. Every correlation it calls is V1's own module.

def _v1_state(v1, atm_decided: bool = True, machine=None):
    return SimpleNamespace(
        PIC_322203={"mode": "AUTO", "op": 0.0,
                    "sp": DECIDED_PIC_SP if atm_decided else V1_PIC_SP,
                    "pv": V1_P_DES_BARA, "pv_prev": V1_P_DES_BARA},
        HIC_322203=0.0,
        XV_322902=True,
        co2_line_bara=V1_P_DES_BARA,
        k002_speed=machine.speed0 if machine else None,
        k002_deliv_kgh=CO2_DES_KGH,
        F_CO2_th=CO2_DES_TH,
        F_CO2_vent_th=0.0,
        tlag={},
        flags={},
    )


def _v1_machine(v1):
    """V1's 320K002 verbatim: its fitted map, its suction floor, its ceiling and boot speed."""
    m = v1["machines"]
    n_poly = m.polytropic_exponent(V1_GAMMA, V1_ETA_POLY)
    rho = m.rho_in_des_from_state(V1_SUCT_P_BARA, V1_SUCT_T_K, V1_FEED_MW)
    machine = m.CentrifugalCompressor(
        CO2_DES_KGH / rho,
        m.polytropic_head_staged_kjkg(V1_SUCT_P_BARA, V1_P_DES_BARA, V1_SUCT_T_K,
                                      V1_FEED_MW, n_poly, V1_STAGES),
        rho, n_poly, m.CentrifugalMap(0.68, 0.12, 1.20), n_stages=V1_STAGES)
    return SimpleNamespace(
        suct=V1_SUCT_P_BARA, speed_max=V1_SPEED_MAX, speed0=1.0,
        delivery=lambda p_node, spd: machine.delivery_kgh(
            V1_SUCT_P_BARA, max(p_node, V1_SUCT_P_BARA + 1e-6), V1_SUCT_T_K, V1_FEED_MW, spd))


def _v1_co2_block(s, v1, machine, raw_demand_th: float, syn_bara: float, dt: float,
                  valves_decided: bool = True) -> dict:
    """V1's CO2-line block, transcribed. See the note above this function. `valves_decided`
    hands V1's vent law PV-322203's decided trim and anchor (B-44); ``machine=None`` replaces
    V1's governor and map with the decided boundary feed and its floor (2026-10-08)."""
    vent = DECIDED_VENT if valves_decided else V1_VENT
    clamp = v1["clamp"]
    hyd = v1["hydraulics"]

    pic = s.PIC_322203
    pic["pv_bad"] = not v1["_pv_ok"](pic["pv"], pic["sp"])
    if pic["mode"] == "AUTO" and not pic["pv_bad"]:
        du = V1_PIC_KC * ((pic["pv"] - pic["pv_prev"])
                          + (dt / V1_PIC_TI) * (pic["pv"] - pic["sp"]))
        pic["op"] = clamp(pic["op"] + du, 0.0, 100.0)
    pic["pv_prev"] = pic["pv"]
    pv_open = clamp(max(s.HIC_322203, pic["op"]), 0.0, 100.0)
    feed_factor = 1.0 if s.XV_322902 else 0.0

    _co2_demand_kgh = raw_demand_th * 1000.0
    if machine is None:             # decided 2026-10-08: the boundary delivers the demand
        speed_frac = None
        suct = DECIDED_SUCT_P_BARA

        def _k002_delivery(p_node, spd):
            return {"kgh": delivery_kgh(_co2_demand_kgh), "surge": False, "stonewall": False}
    else:
        s.k002_speed = clamp(
            s.k002_speed + (dt / V1_GOV_TAU_S) * (_co2_demand_kgh - s.k002_deliv_kgh)
            / CO2_DES_KGH, 0.0, machine.speed_max)
        speed_frac = s.k002_speed
        suct = machine.suct

        def _k002_delivery(p_node, spd):
            return machine.delivery(p_node, spd)

    def _branch_hp(p_node):
        return feed_factor * hyd.check_valve_kgh(
            CO2_DES_KGH, p_node, syn_bara, V1_DP_HP_DES, V1_CRACK_BAR)

    def _branch_vent(p_node):
        return hyd.valve_gas_anchored(
            CO2_DES_KGH, pv_open / 100.0, p_node, V1_VENT_P_BARA, V1_VENT_T_DES_K,
            vent["h_des"], V1_P_DES_BARA, V1_VENT_P_BARA, V1_VENT_T_DES_K, V1_FEED_MW,
            gamma=V1_GAMMA, characteristic=vent["characteristic"], mw_des=V1_FEED_MW)

    P_line_prev = s.co2_line_bara
    _k002 = _k002_delivery(P_line_prev, speed_frac)
    s.k002_deliv_kgh = _k002["kgh"]
    _co2_in_kgh = _k002["kgh"]
    _co2_out_kgh = _branch_hp(P_line_prev) + _branch_vent(P_line_prev)
    s.co2_line_bara = max(
        P_line_prev + hyd.vessel_dpdt(
            P_line_prev, V1_VENT_T_DES_K, V1_LINE_V_M3, V1_FEED_MW,
            _co2_in_kgh / V1_FEED_MW, _co2_out_kgh / V1_FEED_MW) * dt,
        suct)
    P_line_bara = s.co2_line_bara
    dP_HP = max(P_line_bara - syn_bara, 0.0)
    dP_vent = max(P_line_bara - V1_VENT_P_BARA, 0.0)
    F_CO2_feed_kgh = _branch_hp(P_line_bara)
    F_CO2_vent_kgh = _branch_vent(P_line_bara)
    s.F_CO2_th = F_CO2_feed_kgh / 1000.0
    s.F_CO2_vent_th = F_CO2_vent_kgh / 1000.0
    CO2_feed_kmolh = F_CO2_feed_kgh / V1_FEED_MW
    FT_322403 = CO2_feed_kmolh * V1_NM3_PER_KMOL
    FY_322403 = s.F_CO2_th
    F_CO2_syn_th = v1["_delay"](s.tlag, "FEED_CO2", s.F_CO2_th,
                                v1["_feed_transport_td_s"](V1_LINE_KG, F_CO2_feed_kgh), dt)
    Load_pct = s.F_CO2_th / (CO2_DES_KGH / 1000.0) * 100.0
    pic["pv"] = P_line_bara

    return {"line_bara": P_line_bara, "deliv": _k002["kgh"], "feed_th": s.F_CO2_th,
            "vent_th": s.F_CO2_vent_th, "feed_to_loop_th": F_CO2_syn_th,
            "FT": FT_322403, "FY": FY_322403, "load": Load_pct, "pv_open": pv_open,
            "speed": speed_frac, "surge": bool(_k002["surge"]),
            "stonewall": bool(_k002["stonewall"]), "dP_HP": dP_HP, "dP_vent": dP_vent}


def _v11_line():
    return CO2FeedLine(), vent_pressure_loop()


def _compare(v1, script, ticks: int):
    """Drive both through `script(k) -> (raw_demand_th, syn_bara)` and compare every field."""
    s = _v1_state(v1)
    line, pic = _v11_line()
    for k in range(ticks):
        demand, syn = script(k)
        a = _v1_co2_block(s, v1, None, demand, syn, DT)
        b = line.step(pic, demand, syn, DT)
        assert a["line_bara"] == b.line_bara, f"tick {k}"
        assert a["deliv"] == b.delivered_kgh, f"tick {k}"
        assert a["feed_th"] == b.feed_th, f"tick {k}"
        assert a["vent_th"] == b.vent_th, f"tick {k}"
        assert a["feed_to_loop_th"] == b.feed_to_loop_th, f"tick {k}"
        assert a["FT"] == b.ft_322403_nm3h, f"tick {k}"
        assert a["FY"] == b.fy_322403_th, f"tick {k}"
        assert a["load"] == b.load_pct, f"tick {k}"
        assert a["pv_open"] == b.vent_opening_pct, f"tick {k}"
        assert a["dP_HP"] == b.dp_tie_in_bar, f"tick {k}"
        assert a["dP_vent"] == b.dp_vent_bar, f"tick {k}"
        assert s.PIC_322203["op"] == pic.op, f"tick {k}"
        assert s.PIC_322203["pv"] == pic.pv, f"tick {k}"
        assert s.PIC_322203["pv_prev"] == pic.pv1, f"tick {k}"
    return s, line, pic


# --------------------------------------------------------------------------------------
# Whole-block equivalence
# --------------------------------------------------------------------------------------

def test_the_line_holds_its_design_point_and_matches_v1(v1):
    s, line, pic = _compare(v1, lambda k: (CO2_DES_TH, SYN_DES_BARA), ticks=900)
    assert line.pressure_bara == d.CO2_P_DES_BARA


def test_the_design_node_imbalance_is_a_literal_zero():
    """The boot pin for this node, asserted on the rewrite alone.

    The boundary delivers the design demand; the check valve at exactly the design differential
    has a ratio of literally 1.0 and passes the same; the vent at zero opening passes exactly 0.
    So dP/dt is 0.0 and the node cannot drift.
    """
    line, pic = _v11_line()
    before = line.pressure_bara
    result = line.step(pic, CO2_DES_TH, SYN_DES_BARA, DT)
    assert line.pressure_bara == before
    assert result.delivered_kgh == pytest.approx(CO2_DES_KGH, rel=1e-12)
    assert result.feed_th == pytest.approx(CO2_DES_TH, rel=1e-12)
    assert result.vent_th == 0.0
    assert result.load_pct == pytest.approx(100.0, rel=1e-12)
    assert result.delivered_kgh == CO2_DES_KGH


def test_a_moving_loop_pressure_tracks_v1(v1):
    """The synthesis loop breathes and the line has to follow it through the check valve."""
    def script(k):
        return CO2_DES_TH, SYN_DES_BARA + 6.0 * math.sin(k * 0.004)
    _compare(v1, script, ticks=1200)


def test_a_moving_rate_demand_tracks_v1(v1):
    """The boundary delivers whatever CO2 rate the instructor sets."""
    def script(k):
        return CO2_DES_TH * (1.0 + 0.3 * math.sin(k * 0.003)), SYN_DES_BARA
    _compare(v1, script, ticks=1200)


def test_opening_the_vent_tracks_v1(v1):
    """HIC-322203 forces the vent open; the line sags because mass leaves the node."""
    s = _v1_state(v1)
    line, pic = _v11_line()
    for k in range(1200):
        if k == 300:
            s.HIC_322203 = 20.0
            line.hic_min_pct = 20.0
        a = _v1_co2_block(s, v1, None, CO2_DES_TH, SYN_DES_BARA, DT)
        b = line.step(pic, CO2_DES_TH, SYN_DES_BARA, DT)
        assert a["line_bara"] == b.line_bara, f"tick {k}"
        assert a["vent_th"] == b.vent_th, f"tick {k}"
        assert a["feed_th"] == b.feed_th, f"tick {k}"
    assert line.pressure_bara < d.CO2_P_DES_BARA
    assert b.vent_th > 0.0


def test_shutting_the_isolation_tracks_v1(v1):
    """XV-322902 shut: no draw, so the line packs up — bit-exact with V1 until SV32064 lifts at
    its 161.013 bar a set, 31.7 s after the shut (handoff B-83, decided 2026-10-09); V1 has no
    relief and packs on towards PIC-322203's set point."""
    s = _v1_state(v1)
    line, pic = _v11_line()
    lifted_at = None
    for k in range(1500):
        if k == 200:
            s.XV_322902 = False
            line.xv_322902_open = False
        a = _v1_co2_block(s, v1, None, CO2_DES_TH, SYN_DES_BARA, DT)
        b = line.step(pic, CO2_DES_TH, SYN_DES_BARA, DT)
        if lifted_at is None and b.relief_lifted:
            lifted_at = k
        if lifted_at is None:
            assert a["line_bara"] == b.line_bara, f"tick {k}"
            assert b.relief_kgh == 0.0, f"tick {k}"
        assert a["feed_th"] == b.feed_th, f"tick {k}"
        if k >= 200:
            assert b.feed_th == 0.0, f"tick {k}"
    assert lifted_at == 516
    assert a["line_bara"] > d.SV32064_SET_BARA > line.pressure_bara > d.SV32064_RESEAT_BARA


def test_a_synthesis_overpressure_shuts_the_tie_in_and_matches_v1(v1):
    """The loss-of-condensation chain, and what happens next.

    The loop climbs past the line, the disc seats, and the feed goes to EXACTLY zero on the
    tick it happens. It does not stay there: the boundary keeps pushing into a line with no
    draw, so the line packs up until it can push past 155 bar a again and the feed resumes.
    Both halves are the model working — the first is the diode, the second is the
    capacitance — and neither is available to a delivery fraction.
    """
    s = _v1_state(v1)
    line, pic = _v11_line()
    just_shut = None
    for k in range(3000):
        syn = SYN_DES_BARA if k < 300 else 155.0
        a = _v1_co2_block(s, v1, None, CO2_DES_TH, syn, DT)
        b = line.step(pic, CO2_DES_TH, syn, DT)
        assert a["feed_th"] == b.feed_th, f"tick {k}"
        assert a["line_bara"] == b.line_bara, f"tick {k}"
        if k == 300:
            just_shut = b.feed_th
    assert just_shut == 0.0                       # the disc seated, exactly
    assert line.pressure_bara > 155.0             # and the line packed past the loop
    assert s.F_CO2_th > 0.0                       # so the feed came back


def test_a_variable_substep_changes_nothing_about_the_agreement(v1):
    s = _v1_state(v1)
    line, pic = _v11_line()
    steps = [0.1, 0.05, 0.25, 1e-8, 0.2, 0.1, 1e-8, 0.15]
    for k in range(500):
        dt = steps[k % len(steps)]
        a = _v1_co2_block(s, v1, None, CO2_DES_TH, SYN_DES_BARA, dt)
        b = line.step(pic, CO2_DES_TH, SYN_DES_BARA, dt)
        assert a["line_bara"] == b.line_bara, f"tick {k}"
        assert a["feed_to_loop_th"] == b.feed_to_loop_th, f"tick {k}"


# --------------------------------------------------------------------------------------
# What the capacitance buys
# --------------------------------------------------------------------------------------

def test_the_node_lags_instead_of_answering_instantly():
    """The whole point of giving the line a volume.

    A step in the loop pressure changes the check valve's draw immediately, but the line
    pressure has 5234 kg of inventory to work through first. An algebraic node would jump.
    """
    line, pic = _v11_line()
    for _ in range(50):
        line.step(pic, CO2_DES_TH, SYN_DES_BARA, DT)
    before = line.pressure_bara
    line.step(pic, CO2_DES_TH, SYN_DES_BARA - 4.0, DT)
    one_tick = line.pressure_bara
    for _ in range(600):
        line.step(pic, CO2_DES_TH, SYN_DES_BARA - 4.0, DT)
    settled = line.pressure_bara

    #  In one tick the node moves a fortieth of a bar; in the end it moves four. An
    #  algebraic node would have done the whole move on the first tick.
    assert abs(one_tick - before) < 0.05
    assert settled < before - 2.0
    assert abs(settled - before) > 50.0 * abs(one_tick - before)


def test_the_settled_differential_returns_to_the_design_one():
    """The statement the algebraic float used to ASSERT, now an outcome of a mass balance."""
    line, pic = _v11_line()
    for _ in range(4000):
        line.step(pic, CO2_DES_TH, 136.0, DT)
    assert line.pressure_bara - 136.0 == pytest.approx(d.CO2_DP_HP_DES, abs=0.05)


def test_the_boundary_holds_the_node_where_an_open_loop_map_runs_away():
    """Open loop this flowsheet diverges; V1 measured 140.7 -> 134.7 bar a in 16,000 s.

    The boundary's hardwired governor holds the demand, so the node settles instead. The test
    holds a depressed loop pressure for 1,000 s and asserts the line is stationary at the end,
    passing the demand, which an open-loop map does not.
    """
    line, pic = _v11_line()
    for _ in range(10000):
        line.step(pic, CO2_DES_TH, 138.0, DT)
    settled = line.pressure_bara
    for _ in range(2000):
        r = line.step(pic, CO2_DES_TH, 138.0, DT)
    assert line.pressure_bara == pytest.approx(settled, abs=1e-3)
    assert r.delivered_kgh == CO2_DES_KGH
    assert r.feed_kgh == pytest.approx(CO2_DES_KGH, rel=1e-3)


def test_packing_the_line_against_a_shut_tie_in_is_caught_by_sv32064_decided_divergence(v1):
    """With XV-322902 shut the boundary has nowhere to push (handoff B-83, decided 2026-10-09).

    V1's block packs the line past the PSV set point until PIC-322203 opens the vent, which ends
    up taking the WHOLE feed, the line just above the PIC's 168.01 bar a. The port's SV32064
    lifts at its 161.013 bar a set first and stays lifted: the line settles at 147.55 bar a, where
    its orifice passes the whole feed, above its 145.013 bar a reseat; the PIC, its set point
    above the valve's set, never opens the vent.
    """
    s = _v1_state(v1)
    s.XV_322902 = False
    for _ in range(20000):
        a = _v1_co2_block(s, v1, None, CO2_DES_TH, SYN_DES_BARA, DT)
    assert a["feed_th"] == 0.0
    assert a["vent_th"] == pytest.approx(CO2_DES_TH, rel=1e-3)
    assert a["line_bara"] == pytest.approx(s.PIC_322203["sp"], abs=0.1)
    assert a["line_bara"] > d.SV32064_SET_BARA
    line, pic = _v11_line()
    line.xv_322902_open = False
    for _ in range(20000):
        result = line.step(pic, CO2_DES_TH, SYN_DES_BARA, DT)
    assert result.feed_th == 0.0 and result.vent_th == 0.0 and pic.op == 0.0
    assert result.relief_lifted is True
    assert result.relief_kgh == pytest.approx(CO2_DES_KGH, rel=1e-3)
    assert line.pressure_bara == pytest.approx(147.55, abs=0.01)
    assert d.SV32064_RESEAT_BARA < line.pressure_bara < d.SV32064_SET_BARA


def test_sv32064_cycles_between_its_reseat_and_set_at_a_part_feed():
    """At 30 t/h the lifted valve passes more than the feed down to its reseat, so it shuts there
    and the line packs back to its set: the saw-tooth a persisting cause draws (B-83)."""
    line, pic = _v11_line()
    line.xv_322902_open = False
    trace = []
    for _ in range(20000):
        r = line.step(pic, 30.0, SYN_DES_BARA, DT)
        trace.append((r.line_bara, r.relief_lifted))
    lifts = sum(1 for (_, a), (_, b) in zip(trace, trace[1:]) if b and not a)
    assert lifts == 17
    tail = [p for p, _ in trace[5000:]]
    assert min(tail) == pytest.approx(d.SV32064_RESEAT_BARA, abs=1e-6)
    assert max(tail) == pytest.approx(d.SV32064_SET_BARA, abs=0.05)


def test_with_the_vent_in_manual_the_line_packs_decided_divergence(v1):
    """XV-322902 shut and PIC-322203 held shut in MAN: no path out of the line at all.

    Neither machine stops the line. V1's governor runs its machine to the 1.15 speed ceiling and
    up its fitted curve; past the head rise it surges, and V1's convention — a surging machine
    delivers its surge-line flow — keeps 42.7 t/h going in: 676 bar a at 1,000 s, 1,114 at
    2,000 s with the surge flag up. V1's block on the boundary keeps delivering the demand: 676
    and 1,209 bar a. The port relieves through the line's certified valve, SV32064 on 320R001 at
    the machine's discharge (handoff B-83, decided 2026-10-09): lifted at its 161.013 bar a set,
    it holds the line at 147.55 bar a, venting the whole feed.
    """
    runs = {}
    for name, machine in (("v1", _v1_machine(v1)), ("port", None)):
        s = _v1_state(v1, machine=machine)
        s.XV_322902 = False
        s.PIC_322203["mode"] = "MAN"
        for k in range(20000):
            a = _v1_co2_block(s, v1, machine, CO2_DES_TH, SYN_DES_BARA, DT)
            if k == 9999:
                runs[name, 1000] = a
        runs[name, 2000] = a
    assert runs["v1", 1000]["line_bara"] == pytest.approx(675.7, abs=0.1)
    assert runs["v1", 1000]["surge"] is False
    assert runs["v1", 2000]["line_bara"] == pytest.approx(1113.6, abs=0.1)
    assert runs["v1", 2000]["surge"] is True and runs["v1", 2000]["speed"] == V1_SPEED_MAX
    assert runs["v1", 2000]["deliv"] == pytest.approx(42711.0, abs=1.0)
    assert runs["port", 1000]["line_bara"] == pytest.approx(676.4, abs=0.1)
    assert runs["port", 2000]["line_bara"] == pytest.approx(1208.5, abs=0.1)
    assert runs["port", 2000]["deliv"] == CO2_DES_KGH and runs["port", 2000]["vent_th"] == 0.0
    line, pic = _v11_line()
    line.xv_322902_open = False
    pic.mode = "MAN"
    for _ in range(20000):
        result = line.step(pic, CO2_DES_TH, SYN_DES_BARA, DT)
    assert result.vent_th == 0.0 and result.relief_lifted is True
    assert result.relief_kgh == pytest.approx(CO2_DES_KGH, rel=1e-3)
    assert line.pressure_bara == pytest.approx(147.55, abs=0.01)


# --------------------------------------------------------------------------------------
# PIC-322203
# --------------------------------------------------------------------------------------

def _v1_pic_tick(v1, p: dict, measured: float) -> float:
    """V1 `main.py` 7285-7294, transcribed, then the end-of-tick PV write."""
    p["pv_bad"] = not v1["_pv_ok"](p["pv"], p["sp"])
    if p["mode"] == "AUTO" and not p["pv_bad"]:
        du = V1_PIC_KC * ((p["pv"] - p["pv_prev"])
                          + (DT / V1_PIC_TI) * (p["pv"] - p["sp"]))
        p["op"] = v1["clamp"](p["op"] + du, 0.0, 100.0)
    p["pv_prev"] = p["pv"]
    p["pv"] = measured
    return p["op"]


def _v11_pic_tick(pic, measured: float) -> float:
    """The same tick on the installed loop, in the order `CO2FeedLine.step` uses."""
    pic.step(pic.pv, DT)
    op = pic.op
    pic.pv = measured
    return op


def test_the_vent_controller_matches_v1_on_every_finite_measurement(v1):
    """The installed `ProcessLoop` is V1's inline block to the bit while the PV is finite.

    The trace swings across the set point, then holds far above it and far below it, so the
    increment changes sign and the stroke is driven onto both rails and off them again.
    """
    s = _v1_state(v1)
    pic = vent_pressure_loop()
    trace = ([V1_PIC_SP + 12.0 * math.sin(k * 0.05) for k in range(200)]
             + [200.0] * 150 + [100.0] * 150)
    strokes = []
    for k, measured in enumerate(trace):
        a = _v1_pic_tick(v1, s.PIC_322203, measured)
        b = _v11_pic_tick(pic, measured)
        assert a == b, f"tick {k}"
        assert s.PIC_322203["pv_prev"] == pic.pv1, f"tick {k}"
        strokes.append(b)
    assert max(strokes) == 100.0 and min(strokes) == 0.0
    assert any(0.0 < u < 100.0 for u in strokes)


def test_the_vent_controller_opens_on_a_rising_line_pressure():
    """DIRECT acting. Getting the sign wrong here would vent on a FALLING pressure."""
    pic = vent_pressure_loop()
    for _ in range(200):
        _v11_pic_tick(pic, 200.0)       # well above the set point
    assert pic.op > 0.0
    shut = vent_pressure_loop()
    for _ in range(200):
        _v11_pic_tick(shut, 100.0)      # well below it
    assert shut.op == 0.0


def test_the_vent_is_shut_at_the_design_line_pressure():
    """The set point sits above the PSV set, so the vent acts only on a real over-pressure."""
    pic = vent_pressure_loop()
    for _ in range(600):
        _v11_pic_tick(pic, d.CO2_P_DES_BARA)
    assert pic.op == 0.0
    assert pic.sp > d.SYN_PSV_SET_BARA


def test_the_set_point_span_is_v1s():
    """The operator's set point is clamped to V1's [120, 175] bar a, and the design set point
    the loop is seeded with sits inside it."""
    pic = vent_pressure_loop()
    assert V1_PIC_SP_LO < pic.sp == DECIDED_PIC_SP < V1_PIC_SP_HI
    pic.set_sp(200.0)
    assert pic.sp == V1_PIC_SP_HI
    pic.set_sp(90.0)
    assert pic.sp == V1_PIC_SP_LO


def test_a_non_finite_line_pressure_no_longer_latches_the_vent_open(v1):
    """The one deliberate divergence from V1 in this unit — As-Built §XVII.5.

    V1 advances `pv_prev` past a bad sample, so the recovered measurement meets a NaN in the
    proportional term and V1's limiter turns it into the upper rail: the vent latches wide
    open. The installed `ProcessLoop` freezes the output and the history on the bad sample,
    so the recovered measurement is compared with the last GOOD one and nothing happens.

    V1's side is still driven and asserted, so the test records what the divergence is, not
    only that the rewrite is well behaved.
    """
    s = _v1_state(v1)
    pic = vent_pressure_loop()
    sequence = [144.2, 144.2, float("nan"), 144.2, 144.2, 144.2]
    v1_strokes = [_v1_pic_tick(v1, s.PIC_322203, m) for m in sequence]
    v11_strokes = [_v11_pic_tick(pic, m) for m in sequence]

    #  V1: shut through the bad tick, straight to the rail on the recovered measurement, then
    #  a slow walk back down — a single spike to fully open that is easy to miss on a trend.
    assert v1_strokes[:4] == [0.0, 0.0, 0.0, 0.0]
    assert v1_strokes[4] == 100.0
    assert 98.0 < v1_strokes[5] < 100.0
    #  The rewrite: shut throughout, because the line is far below the set point and the bad
    #  sample left no trace in the history. The loop stays in AUTO.
    assert v11_strokes == [0.0] * 6
    assert pic.mode == "AUTO"


def test_a_bad_sample_costs_one_tick_of_control_action_and_nothing_else():
    """Frozen for the one tick that consumes the bad sample; afterwards the loop is, to the
    bit, the loop that never saw it."""
    rising = [150.0 + 0.5 * k for k in range(60)]       # crosses the set point near k = 36
    j = 45
    with_bad = rising[:j] + [float("nan")] + rising[j + 1:]
    without = rising[:j] + rising[j + 1:]
    a_loop, b_loop = vent_pressure_loop(), vent_pressure_loop()
    a = [_v11_pic_tick(a_loop, m) for m in with_bad]
    b = [_v11_pic_tick(b_loop, m) for m in without]
    #  The sample published at the end of tick j is consumed at the top of tick j + 1.
    assert a[:j + 1] == b[:j + 1]
    assert a[j + 1] == a[j] > 0.0           # frozen, and frozen OPEN: the loop was acting
    assert a[j + 2:] == b[j + 1:]


def test_pic_322203_on_the_standard_atmosphere_decided_divergence(v1):
    """PIC-322203's set point is SV-32201's set plus twice the design differential. On V1's
    1.013 bar atmosphere it is 168.013 bar a; on the standard one 0.25 mbar higher (handoff B-6,
    decided 2026-10-07). Bit-exact while the line holds below it; above it, the vent opens on a
    set point 0.25 mbar apart."""
    from ureasim.units.synthesis.co2_line import PIC_322203_SP_DES_BARA
    assert _v1_state(v1, atm_decided=False).PIC_322203["sp"] == V1_PIC_SP
    assert PIC_322203_SP_DES_BARA == DECIDED_PIC_SP
    assert DECIDED_PIC_SP - V1_PIC_SP == pytest.approx(0.00025, abs=1e-9)


def test_a_part_load_is_the_demand_at_once_decided_divergence(v1):
    """320K002 asked for 80 % of the design CO2, the whole block both ways.

    V1's governor walks its machine down its fitted curve on an 8 s integral: on the first tick
    it still delivers 54.1 t/h, 99 % of the design, and after ten minutes it sits at 0.956 of its
    design speed delivering the 80 %. The boundary delivers the 80 % on the first tick. Settled, the
    line and the feed are the same numbers on both sides; only the path differs.
    """
    runs, first = {}, {}
    for name, machine in (("v1", _v1_machine(v1)), ("port", None)):
        s = _v1_state(v1, machine=machine)
        for k in range(6000):
            a = _v1_co2_block(s, v1, machine, 0.8 * CO2_DES_TH, SYN_DES_BARA, DT)
            if k == 0:
                first[name] = a["deliv"]
        runs[name] = a
    assert first["v1"] == pytest.approx(54113.0, abs=1.0)
    assert first["port"] == 0.8 * CO2_DES_KGH
    assert runs["v1"]["surge"] is False
    assert runs["v1"]["speed"] == pytest.approx(0.9562, abs=1e-4)
    assert runs["port"]["speed"] is None and runs["port"]["surge"] is False
    for key in ("line_bara", "feed_th"):
        assert runs["port"][key] == pytest.approx(runs["v1"][key], rel=1e-6)
    assert runs["port"]["deliv"] == 0.8 * CO2_DES_KGH
