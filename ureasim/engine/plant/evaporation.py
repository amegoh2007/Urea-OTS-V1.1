"""Unit 324's four steps — the motive valves, stage 1, stage 2 and the vacuum train — and unit
335's UF85 dosing, wired as V1 steps them.

What this is
------------
The schedule's entries for V1's ``step_sim`` sections 26 to 31. UF85 (section 30) doses on stage 2's
drain of this tick, on LV-324501A's forward melt (decided 2026-10-16, decision 123: V1 calls its
cascade with the recycle permissive forced). Stage 2 drains to the computed melt header, its header
valves and HIC-335602 the operator's (decision 224).
HV-329605 and HV-329606 pass the LP header's steam to the ejectors' nozzles at the header the
network left this tick (handoff B-73). Stage 1 takes 323D002's discharge of this tick down its own
line and the pre-evaporator's overhead through HV-323605; stage 2 takes stage 1's melt of this
tick; both read the cold ends their condensers settled at, lagged, and stage 2 324E006's shell, as
the train left them on the tick before; the train takes both stages' overheads of this tick.

Source: V1 ``backend/main.py`` ``step_sim`` 9695-10065; the units' modules (`ureasim.units.
evaporation`) and their equivalence tests.
"""

from __future__ import annotations

from ureasim.core.numeric import clamp
from ureasim.data.faceplates import GRANULATION_HEADERS_TAG
from ureasim.data.unit_324 import P2_DES_KGH
from ureasim.data.unit_335 import HEADER_P_DES_BARG, HEADER_VALVES_DES, HEADER_VALVES_MAX
from ureasim.engine.schedule import Boundary, DeclaredTear, Operator, Result, State, Step
from ureasim.units.evaporation import ejector_map as em
from ureasim.units.evaporation import first_evaporator as fe
from ureasim.units.evaporation import second_evaporator as se
from ureasim.units.evaporation import vacuum_train as vt
from ureasim.units.evaporation.melt_route import selector_drain
from ureasim.units.finishing import melt_header as mh
from ureasim.units.finishing import uf85_dosing as uf

__all__ = ["MOTIVE", "TRAIN", "DOSING", "PUMP_PAIR", "units", "steps", "tears"]

#: The two motive valves' step, and the vacuum train's, by the names the schedule gives them.
MOTIVE = "HV-329605/6"
TRAIN = "324E002-E007"
DOSING = "335"
#: 335P001A / B's run state, True while either runs (decision 227): the header's pumps.
PUMP_PAIR = "335P001"


def units() -> tuple[dict, dict]:
    """The two stages and their controllers, the train, and the UF85 dosing's two loops, seeded on
    the design."""
    return ({"324E001": fe.FirstEvaporator(), "324E003": se.SecondEvaporator(),
             TRAIN: vt.VacuumTrain()},
            {"324E001": (fe.FirstEvaporatorLoops(),), "324E003": (se.SecondEvaporatorLoops(),),
             DOSING: (uf.ffic_335406(), uf.fic_335405())})


def adopt_boundary_header(plant, p_335201_barg: float) -> None:
    """Hand a save's battery-limit melt header over to the computed one (decision 226).

    Process utility
    ---------------
    An exercise saved before the header was computed (decision 224) held PIC-335201 as a boundary
    value and LIC-324501's output as LV-324501's stroke. On restore the save's load is its drain on
    V1's selector over the design drain, and the header valves online are the number whose header,
    passing that drain, stands nearest the design's 3.5 bar g without rising above E1's 3.8 bar g
    ceiling (I-3: the valves proportional to the load, to hold 3.2 to 3.8 bar g; ten at design). A
    header above the ceiling would leave LIC-324501 at full E1 and the excess on LV-324501B. The
    header starts at that pressure, with PIC-335201's history on it, and LIC-324501's output becomes
    the X whose E1 is that header. PIC-335201's output and LV-324501A's position stand at the stroke
    that passes the save's drain at that header (decision 238, which replaced decision 226's save's
    stroke: on the header's law that stroke passes less, and the header opened with a dip), so the
    header balances on the first tick. A save draining nothing keeps the seeded valves and its
    header, LV-324501A shut; a drain no number of valves can hold under the ceiling takes all twelve.

    Equation: P(N) = P_des (N_des L / N)^2, N = argmin |P(N) - P_des| over the N in 1 to 12 with
    P(N) <= E1(100 %); h_A = `passing_stroke_pct`(L, beta(X), P(N)).
    """
    loops, unit = plant.loops["324E003"][0], plant.units["324E003"]
    p = max(float(p_335201_barg), 0.0)
    stroke = clamp(loops.level.op, 0.0, 100.0)
    drain, _recycle, _lv_a, _lv_b = selector_drain(stroke, p, unit.vendor_drain, float("inf"))
    load = drain / P2_DES_KGH
    if load > 0.0:
        def header(k: int) -> float:
            return HEADER_P_DES_BARG * (load * HEADER_VALVES_DES / k) ** 2
        held = [k for k in range(1, HEADER_VALVES_MAX + 1) if header(k) <= mh.e1_setpoint_barg(100.0)]
        n = min(held, key=lambda k: abs(header(k) - HEADER_P_DES_BARG)) if held else HEADER_VALVES_MAX
        plant.operator[GRANULATION_HEADERS_TAG] = n
        p = header(n)
    loops.level.op = mh.x_for_setpoint(p)
    loops.header.op = unit.header.lv_a_position_pct = mh.passing_stroke_pct(
        load, _recycle_phi(plant, loops.level.op), p)
    loops.header.pv = loops.header.pv1 = loops.header.pv2 = p
    loops.header.sp = mh.e1_setpoint_barg(loops.level.op)
    unit.header.p_barg = p


def _recycle_phi(plant, x_pct: float) -> float:
    # LV-324501B's share on LIC-324501's output X, as the header's step takes it: none with both
    # 335P001 pumps stopped.
    if not plant.operator.get(PUMP_PAIR, True):
        return 0.0
    return mh.recycle_fraction(mh.lv_b_stroke_pct(x_pct))


def adopt_header_position(plant) -> None:
    """Open LV-324501A on a save made before it had a positioner (decisions 236 and 238).

    Process utility
    ---------------
    An exercise saved on decision 224's header held PIC-335201's output, which was then the valve's
    stroke, on the inlet decision 237 has since moved: at that stroke the valve now passes less and
    the header would open with a dip. The save holds no drain, but its header was balanced, so the
    drain is what the header valves online and HV-335602 took at the saved header (their laws are
    unchanged). PIC-335201's output and the valve's position stand at the stroke that passes it, so
    the header balances on the first tick. With PIC-335201 in MAN, or both 335P001 pumps stopped,
    the output is the operator's hand value or the loop's wind-up, not a drain, and the valve stands
    on it as saved.

    Equation: h_A = `passing_stroke_pct`(phi_noz(N, P) + phi_hv(h_hv, P), beta(X), P).
    """
    unit, loops = plant.units["324E003"], plant.loops["324E003"][0]
    header, pic = unit.header, loops.header
    if pic.mode != "MAN" and plant.operator.get(PUMP_PAIR, True) and header.p_barg > 0.0:
        n = int(clamp(plant.operator.get(GRANULATION_HEADERS_TAG, HEADER_VALVES_DES), 0,
                      HEADER_VALVES_MAX))
        drain = mh.nozzle_fraction(n, header.p_barg) + mh.hv_fraction(header.hv_pct, header.p_barg)
        pic.op = mh.passing_stroke_pct(drain, _recycle_phi(plant, loops.level.op), header.p_barg)
    header.lv_a_position_pct = pic.op


def _motive(plant, a, dt):
    return vt.motive_steam(a["hic_329605_pct"], a["hic_329606_pct"], a["p_lp_bara"])


def _324e001(plant, a, dt):
    return plant.units["324E001"].step(
        *plant.loops["324E001"], a["drain_kgh"], a["drain_t_c"], dict(a["drain_w"]),
        a["p_lp_bara"], em.nozzle_pressure_bara("324F002", a["m_924_kgh"]),
        a["p_discharge_bara"], a["f010_vapour_kgh"], a["sub_703"], a["t_vent_324e002_c"], dt)


def _324e003(plant, a, dt):
    unit = plant.units["324E003"]
    return unit.step(
        *plant.loops["324E003"], a["feed_kgh"], a["feed_t_c"], dict(a["feed_w"]), a["p_mp_bara"],
        em.nozzle_pressure_bara("324F004", a["m_927_kgh"]), a["p_discharge_bara"],
        a["t_vent_324e005_c"], unit.header.p_barg, dt,
        headers_online=int(clamp(a["headers_online"], 0, HEADER_VALVES_MAX)),
        hic_335602_pct=a["hic_335602_pct"], pump_running=bool(a["p001_running"]))


def _uf85(plant, a, dt):
    # 335P002A and B both stopped stop the dosing (decision 227).
    return uf.uf85_split_step(*plant.loops[DOSING], a["route"], not a["p002_running"], dt)


def _train(plant, a, dt):
    motive = vt.MotiveSteam(a["m_924_kgh"], a["m_927_kgh"], a["m_929_kgh"])
    return plant.units[TRAIN].step(
        a["m_790_kgh"], a["vap1_kgh"] + a["boil1_kgh"], a["vap2_kgh"] + a["boil2_kgh"],
        a["false_air1_kgh"], a["false_air2_kgh"], motive, a["p_324e002_bara"],
        a["p_324e005_bara"], dt, sub_703=a["sub_703"], p_lp_bara=a["p_lp_bara"])


def steps() -> dict:
    """The five steps by unit; `ureasim.engine.plant` puts them in V1's order."""
    e001, e003 = "324E001", "324E003"
    return {
        MOTIVE: Step(MOTIVE, "motive steam hand valves", "329", 26, {
            "hic_329605_pct": Operator("HIC-329605"), "hic_329606_pct": Operator("HIC-329606"),
            "p_lp_bara": State("329", "p_lp_bara")}, _motive),
        e001: Step(e001, "evaporator I and 324F001", "324", 26, {
            "drain_kgh": Result("323D002", "m_324_kgh"), "drain_t_c": Result("323D002", "t_c"),
            "drain_w": Result("323D002", "w"), "p_lp_bara": State("329", "p_lp_bara"),
            "m_924_kgh": Result(MOTIVE, "m_924_kgh"),
            "p_discharge_bara": Boundary("323C005.p_bara"),
            "f010_vapour_kgh": Result("323F010", "pull_kgh"),
            "sub_703": Result("323F010", "blowthrough_share"),
            "t_vent_324e002_c": State(TRAIN, "lag_state.324E002")}, _324e001),
        e003: Step(e003, "evaporator II and 324F003", "324", 29, {
            "feed_kgh": Result(e001, "m_401_kgh"), "feed_t_c": Result(e001, "t_c"),
            "feed_w": Result(e001, "w"), "p_mp_bara": State("329", "p_9_bara"),
            "m_927_kgh": Result(MOTIVE, "m_927_kgh"),
            "p_discharge_bara": State(TRAIN, "p_324e006_bara"),
            "t_vent_324e005_c": State(TRAIN, "lag_state.324E005"),
            "headers_online": Operator("GRANULATION-HEADERS"),
            "hic_335602_pct": Operator("HIC-335602"), "p001_running": Operator(PUMP_PAIR)},
            _324e003),
        DOSING: Step(DOSING, "UF85 dosing, FFIC-335406 and FIC-335405", "335", 30, {
            "route": Result(e003, "route"), "p002_running": Operator("335P002")}, _uf85),
        TRAIN: Step(TRAIN, "vacuum train", "324", 31, {
            "m_790_kgh": Result("323F010", "pull_kgh"),
            "sub_703": Result("323F010", "blowthrough_share"),
            "vap1_kgh": Result(e001, "m_vap_kgh"), "boil1_kgh": Result(e001, "m_boil_kgh"),
            "vap2_kgh": Result(e003, "m_vap_kgh"), "boil2_kgh": Result(e003, "m_boil_kgh"),
            "false_air1_kgh": Result(e001, "false_air_kgh"),
            "false_air2_kgh": Result(e003, "air_in_kgh"),
            "m_924_kgh": Result(MOTIVE, "m_924_kgh"), "m_927_kgh": Result(MOTIVE, "m_927_kgh"),
            "m_929_kgh": Result(MOTIVE, "m_929_kgh"),
            "p_324e002_bara": Result(e001, "p_bara"),
            "p_324e005_bara": Result(e003, "p_bara"),
            "p_lp_bara": State("329", "p_lp_bara")}, _train),
    }


def tears() -> tuple[DeclaredTear, ...]:
    """The one-tick reads unit 324's stages make of the train (handoffs B-65, B-66)."""
    return (
        DeclaredTear(State(TRAIN, "lag_state.324E002"), "324E001",
                     "324E002's cold end, lagged on its tubes' water (B-65), the train "
                     "stepping after the stages"),
        DeclaredTear(State(TRAIN, "lag_state.324E005"), "324E003",
                     "324E005's cold end, likewise"),
        DeclaredTear(State(TRAIN, "p_324e006_bara"), "324E003",
                     "324F004 discharges against 324E006's shell, a live node (B-66)"),
    )
