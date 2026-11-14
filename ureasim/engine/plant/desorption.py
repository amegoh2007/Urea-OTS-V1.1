"""Unit 328's seven steps: 323C005 -> 328D003 -> 328E007 -> 328C002 -> 328C003 -> 328C004 ->
328D001, wired as V1 steps them.

What this is
------------
The schedule's entries for V1's ``step_sim`` sections 14 to 20. 323C005 steps first in V1's block,
so every stream into it is a tear (702, 756, 708, 324E002's vent inerts and, decided 2026-10-03
(handoff A-20), 323E011's envelope overflow) and 322C001's liquor temperature its state of the
tick before; 328D003 takes 323C005's 343 the same tick and unit 324's
condensates and 328C004's 741 a tick late; 328E007 the tank's 735 the same tick and 328C004's
bottoms a tick late; 328C002 its feed the same tick and the hydrolyser's and 328C004's overheads,
328D001's reflux and both their pressures a tick late; the hydrolyser and 328C004 take their feeds
the same tick; the reflux drum takes 328C002's overhead the same tick and 323D011's 718A a tick
late. FV-329401 draws on the LP header after the network's step this tick (handoff B-73).

The inlets take their producers' live temperatures (handoff B-31, decided 2026-10-16): 323C005
756's and 702's from the solvent temperature and the envelope's condensate it already reads;
328D003 343's from 323C005 the same tick and the condensates' from their condensers' cold ends a
tick late (tears); 328C002 775's, 748's and 750's from 328D001, 328C003 and 328C004 a tick late.

Source: V1 ``backend/main.py`` ``step_sim`` 8835-9348; the units' modules (`ureasim.units.
desorption`) and their equivalence tests, which carry V1's call sites line for line.
"""

from __future__ import annotations

from ureasim.engine.schedule import DeclaredTear, Operator, Result, State, Step, Tear
from ureasim.units.desorption import ammonia_water_tank as awt
from ureasim.units.desorption import atmospheric_absorber as aa
from ureasim.units.desorption import first_desorber as fd
from ureasim.units.desorption import hydrolyser as hy
from ureasim.units.desorption import reflux_drum as rd
from ureasim.units.desorption import second_desorber as sd
from ureasim.units.desorption.feed_effluent_interchanger import desorber_heat_exchanger

__all__ = ["units", "steps", "tears"]


def units() -> tuple[dict, dict]:
    """The units with state and their controllers, seeded on the design (328E007 has none)."""
    return ({"323C005": aa.AtmosphericAbsorber(), "328D003": awt.AmmoniaWaterTank(),
             "328C002": fd.FirstDesorber(), "328C003": hy.Hydrolyser(),
             "328C004": sd.SecondDesorber(), "328D001": rd.RefluxDrum()},
            {"328D003": (awt.TankLoops(),), "328C002": (fd.lic_328503(),),
             "328C003": (hy.HydrolyserLoops(),), "328C004": (sd.SecondDesorberLoops(),),
             "328D001": (rd.RefluxDrumLoops(),)})


def _323c005(plant, a, dt):
    return plant.units["323C005"].step(a["m_702_kgh"], a["m_756_kgh"], a["m_708_kgh"],
                                       dict(a["inert_706_kmolh"]), a["t_solvent_c"], dt,
                                       m_e011_over_kgh=a["m_e011_over_kgh"],
                                       t_e011_over_c=a["t_e011_over_c"], t_708_c=a["t_708_c"])


def _328d003(plant, a, dt):
    ends = {"324E002": a["t_719_c"], "324E005": a["t_720_c"], "324E006": a["t_721_c"],
            "324E007": a["t_759_c"]}
    return plant.units["328D003"].step(
        *plant.loops["328D003"], a["m_343_kgh"], a["m_719_kgh"], a["m_720_kgh"],
        a["m_721_kgh"], a["m_759_kgh"], a["m_741_kgh"], a["p002_running"], dt,
        t_c005_c=a["t_c005_c"], t_cold_ends_c=ends)


def _328e007(plant, a, dt):
    return desorber_heat_exchanger(a["m_735_kgh"], a["t_735_c"], a["m_739_kgh"], a["t_739_c"])


def _328c002(plant, a, dt):
    return plant.units["328C002"].step(
        *plant.loops["328C002"], a["m_738_kgh"], a["t_738_c"], a["m_748_kgh"], dict(a["y_748"]),
        a["m_750_kgh"], dict(a["y_750"]), a["m_775_kgh"], a["p_c003_bara"], a["p_d001_bara"], dt,
        t_d001_c=a["t_d001_c"], t_c003_c=a["t_c003_c"], t_c004_c=a["t_c004_c"],
        pump_running=bool(a["p006_running"]))


def _328c003(plant, a, dt):
    return plant.units["328C003"].step(
        *plant.loops["328C003"], a["m_746_kgh"], a["w_746"], a["t_c002_c"], a["p_c002_bara"],
        a["p_c004_bara"], dt)


def _328c004(plant, a, dt):
    return plant.units["328C004"].step(
        *plant.loops["328C004"], a["m_749_kgh"], a["t_749_c"], a["w_749"], a["m_735_kgh"],
        a["p_c002_bara"], a["t_740_c"], dt, p_lp_bara=a["p_lp_bara"],
        pump_running=bool(a["p007_running"]))


def _328d001(plant, a, dt):
    return plant.units["328D001"].step(
        *plant.loops["328D001"], a["m_737_kgh"], a["t_c002_c"], a["p_c002_bara"],
        a["m_c002_kg"], a["in_c002_kgh"], a["m_c002_over_kgh"], a["m_718a_kgh"], a["m_793_kgh"],
        a["t_793_c"], a["p_e011_bara"], dt)


def steps() -> dict:
    """The seven steps by unit; `ureasim.engine.plant` puts them in V1's order."""
    c002, c003, c004, d003 = "328C002", "328C003", "328C004", "328D003"
    return {
        "323C005": Step("323C005", "atmospheric absorber and 328V001", "323", 14, {
            "m_702_kgh": Tear("m_702_kgh"), "m_756_kgh": Tear("m_756_kgh"),
            "m_708_kgh": Tear("m_708_kgh"), "inert_706_kmolh": Tear("inert_706_kmolh"),
            "t_solvent_c": State("322C001", "t_c"),
            "m_e011_over_kgh": Tear("m_e011_over_kgh"),
            "t_e011_over_c": Tear("t_e011_over_c"), "t_708_c": Tear("t_708_c")}, _323c005),
        d003: Step(d003, "ammonia water tank", "328", 15, {
            "m_343_kgh": Result("323C005", "m_343_kgh"),
            "m_719_kgh": Tear("m_719_kgh"), "m_720_kgh": Tear("m_720_kgh"),
            "m_721_kgh": Tear("m_721_kgh"), "m_759_kgh": Tear("m_759_kgh"),
            "m_741_kgh": Tear("m_741_kgh"),
            "p002_running": Operator("322P002"),
            "t_c005_c": Result("323C005", "t_c"),
            "t_719_c": Tear("t_719_c"), "t_720_c": Tear("t_720_c"),
            "t_721_c": Tear("t_721_c"), "t_759_c": Tear("t_759_c")}, _328d003),
        "328E007": Step("328E007", "desorber heat exchanger", "328", 16, {
            "m_735_kgh": Result(d003, "m_735_kgh"), "t_735_c": Result(d003, "t_ii_c"),
            "m_739_kgh": Tear("m_739_kgh"), "t_739_c": State(c004, "t_c")}, _328e007),
        c002: Step(c002, "desorber I", "328", 17, {
            "m_738_kgh": Result("328E007", "m_738_kgh"),
            "t_738_c": Result("328E007", "t_738_c"),
            "m_748_kgh": Tear("m_748_kgh"), "y_748": State(c003, "y_748"),
            "m_750_kgh": Tear("m_750_kgh"), "y_750": State(c004, "y_750"),
            "m_775_kgh": State("328D001", "m_775_prev_kgh"),
            "p_c003_bara": State(c003, "p_bara"),
            "p_d001_bara": State("328D001", "p_bara"),
            "t_d001_c": State("328D001", "t_c"), "t_c003_c": State(c003, "t_c"),
            "t_c004_c": State(c004, "t_c"), "p006_running": Operator("328P006")}, _328c002),
        c003: Step(c003, "hydrolyser and 328E021", "328", 18, {
            "m_746_kgh": Result(c002, "m_743_kgh"), "w_746": Result(c002, "w"),
            "t_c002_c": Result(c002, "t_c"), "p_c002_bara": Result(c002, "p_bara"),
            "p_c004_bara": State(c004, "p_bara")}, _328c003),
        c004: Step(c004, "desorber II", "328", 19, {
            "m_749_kgh": Result(c003, "m_747_kgh"), "t_749_c": Result(c003, "t_749_c"),
            "w_749": Result(c003, "w"), "m_735_kgh": Result(d003, "m_735_kgh"),
            "p_c002_bara": Result(c002, "p_bara"), "t_740_c": Result("328E007", "t_740_c"),
            "p_lp_bara": State("329", "p_lp_bara"), "p007_running": Operator("328P007")},
            _328c004),
        "328D001": Step("328D001", "reflux drum and 328E004", "328", 20, {
            "m_737_kgh": Result(c002, "m_737_kgh"), "t_c002_c": Result(c002, "t_c"),
            "p_c002_bara": Result(c002, "p_bara"), "m_c002_kg": Result(c002, "m_kg"),
            "in_c002_kgh": Result(c002, "in_kgh"),
            "m_c002_over_kgh": Result(c002, "m_overflow_kgh"),
            "m_718a_kgh": Tear("m_718a_kgh"), "m_793_kgh": Result(d003, "m_793_kgh"),
            "t_793_c": Result(d003, "t_ii_c"),
            "p_e011_bara": State("323E011", "p_bara")}, _328d001),
    }


def tears() -> tuple[DeclaredTear, ...]:
    """The one-tick reads unit 328's steps make, each with the reason V1's order gives it."""
    return (
        DeclaredTear(Tear("m_702_kgh"), "323C005",
                     "323E011's vent through PV-323203; V1 steps 323C005 first (R3232_702)"),
        DeclaredTear(Tear("m_756_kgh"), "323C005",
                     "322C001's solvent through LV-322502, section 22 (R322_756)"),
        DeclaredTear(Tear("m_708_kgh"), "323C005",
                     "unit 324's vapour through 324F002, section 31 (R324_708)"),
        DeclaredTear(Tear("inert_706_kmolh"), "323C005",
                     "324E002's vent inerts, section 31 (R324_706_INERT)"),
        DeclaredTear(State("322C001", "t_c"), "323C005",
                     "the lean solvent's temperature, 322C001 stepping in section 22"),
        DeclaredTear(Tear("m_e011_over_kgh"), "323C005",
                     "323E011's envelope overflow through PV-323203's vent line (A-20)"),
        DeclaredTear(Tear("t_e011_over_c"), "323C005", "its temperature, likewise"),
        DeclaredTear(Tear("t_708_c"), "323C005",
                     "708's temperature, 324F002's discharge, section 31 (B-97)"),
        DeclaredTear(Tear("m_719_kgh"), "328D003", "324E002's condensate, section 31 (R324_719)"),
        DeclaredTear(Tear("m_720_kgh"), "328D003", "324E005's condensate, section 31 (R324_720)"),
        DeclaredTear(Tear("m_721_kgh"), "328D003", "324E006's condensate, section 31 (R324_721)"),
        DeclaredTear(Tear("m_759_kgh"), "328D003", "324E007's condensate, section 31 (R324_759)"),
        DeclaredTear(Tear("t_719_c"), "328D003", "324E002's cold end, 719's temperature (B-31)"),
        DeclaredTear(Tear("t_720_c"), "328D003", "324E005's cold end, 720's temperature (B-31)"),
        DeclaredTear(Tear("t_721_c"), "328D003", "324E006's cold end, 721's temperature (B-31)"),
        DeclaredTear(Tear("t_759_c"), "328D003", "324E007's cold end, 759's temperature (B-31)"),
        DeclaredTear(Tear("m_741_kgh"), "328D003",
                     "328C004 steps FIC-328406 after the tank (decision 26)"),
        DeclaredTear(Tear("m_739_kgh"), "328E007",
                     "328C004's bottoms, 328C004 stepping after 328C002 (R328_739)"),
        DeclaredTear(State("328C004", "t_c"), "328E007", "328C004's temperature, likewise"),
        DeclaredTear(Tear("m_748_kgh"), "328C002", "the hydrolyser's overhead (R328_748)"),
        DeclaredTear(State("328C003", "y_748"), "328C002", "its vapour, likewise"),
        DeclaredTear(Tear("m_750_kgh"), "328C002", "328C004's overhead (R328_750)"),
        DeclaredTear(State("328C004", "y_750"), "328C002", "its vapour, likewise"),
        DeclaredTear(State("328D001", "m_775_prev_kgh"), "328C002",
                     "328D001's reflux, the drum stepping after the columns (R328_775)"),
        DeclaredTear(State("328C003", "p_bara"), "328C002",
                     "the hydrolyser's pressure, 748's outlet's inlet"),
        DeclaredTear(State("328D001", "p_bara"), "328C002",
                     "328D001's pressure, 737's outlet"),
        DeclaredTear(State("328D001", "t_c"), "328C002", "the reflux's temperature (B-31)"),
        DeclaredTear(State("328C003", "t_c"), "328C002",
                     "the hydrolyser's temperature, 748's (B-31)"),
        DeclaredTear(State("328C004", "t_c"), "328C002", "328C004's temperature, 750's (B-31)"),
        DeclaredTear(State("328C004", "p_bara"), "328C003",
                     "LV-328504 lets the hydrolyser down into 328C004, which steps after it"),
        DeclaredTear(Tear("m_718a_kgh"), "328D001",
                     "323D011's condensate through 323P008, 323E011 stepping in section 24 "
                     "(R3232_718A)"),
        DeclaredTear(State("323E011", "p_bara"), "328D001",
                     "PV-328202 vents the drum to 323E011 (decision 29)"),
    )
