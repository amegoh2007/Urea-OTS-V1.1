"""Unit 324's four steps — the motive valves, stage 1, stage 2 and the vacuum train — and unit
335's UF85 dosing, wired as V1 steps them.

What this is
------------
The schedule's entries for V1's ``step_sim`` sections 26 to 31. UF85 (section 30) doses on stage 2's
drain of this tick and joins it at LV-324501's selector (decided 2026-10-16, decision 123: V1 calls
its cascade with the recycle permissive forced).
HV-329605 and HV-329606 pass the LP header's steam to the ejectors' nozzles at the header the
network left this tick (handoff B-73). Stage 1 takes 323D002's discharge of this tick down its own
line and the pre-evaporator's overhead through HV-323605; stage 2 takes stage 1's melt of this
tick; both read the cold ends their condensers settled at, lagged, and stage 2 324E006's shell, as
the train left them on the tick before; the train takes both stages' overheads of this tick.

Source: V1 ``backend/main.py`` ``step_sim`` 9695-10065; the units' modules (`ureasim.units.
evaporation`) and their equivalence tests.
"""

from __future__ import annotations

from ureasim.engine.schedule import Boundary, DeclaredTear, Operator, Result, State, Step
from ureasim.units.evaporation import ejector_map as em
from ureasim.units.evaporation import first_evaporator as fe
from ureasim.units.evaporation import second_evaporator as se
from ureasim.units.evaporation import vacuum_train as vt
from ureasim.units.finishing import uf85_dosing as uf

__all__ = ["MOTIVE", "TRAIN", "DOSING", "units", "steps", "tears"]

#: The two motive valves' step, and the vacuum train's, by the names the schedule gives them.
MOTIVE = "HV-329605/6"
TRAIN = "324E002-E007"
DOSING = "335"


def units() -> tuple[dict, dict]:
    """The two stages and their controllers, the train, and the UF85 dosing's two loops, seeded on
    the design."""
    return ({"324E001": fe.FirstEvaporator(), "324E003": se.SecondEvaporator(),
             TRAIN: vt.VacuumTrain()},
            {"324E001": (fe.FirstEvaporatorLoops(),), "324E003": (se.SecondEvaporatorLoops(),),
             DOSING: (uf.ffic_335406(), uf.fic_335405())})


def _motive(plant, a, dt):
    return vt.motive_steam(a["hic_329605_pct"], a["hic_329606_pct"], a["p_lp_bara"])


def _324e001(plant, a, dt):
    return plant.units["324E001"].step(
        *plant.loops["324E001"], a["drain_kgh"], a["drain_t_c"], dict(a["drain_w"]),
        a["p_lp_bara"], em.nozzle_pressure_bara("324F002", a["m_924_kgh"]),
        a["p_discharge_bara"], a["f010_vapour_kgh"], a["sub_703"], a["t_vent_324e002_c"], dt)


def _324e003(plant, a, dt):
    return plant.units["324E003"].step(
        *plant.loops["324E003"], a["feed_kgh"], a["feed_t_c"], dict(a["feed_w"]), a["p_mp_bara"],
        em.nozzle_pressure_bara("324F004", a["m_927_kgh"]), a["p_discharge_bara"],
        a["t_vent_324e005_c"], a["p_335201_barg"], dt)


def _uf85(plant, a, dt):
    route = a["route"]
    return uf.uf85_step(*plant.loops[DOSING], a["m_402_kgh"], route.recycle_w,
                        route.recycle_t_c, a["recycle"], dt)


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
            "p_335201_barg": Boundary("PIC-335201.barg")}, _324e003),
        DOSING: Step(DOSING, "UF85 dosing, FFIC-335406 and FIC-335405", "335", 30, {
            "m_402_kgh": Result(e003, "m_402_kgh"), "route": Result(e003, "route"),
            "recycle": Result(e003, "recycle_selected")}, _uf85),
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
