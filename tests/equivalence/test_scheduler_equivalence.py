"""V1 <-> V1.1 for the scheduler: unit 323's liquor train stepped through the engine's tick.

What is being proved
--------------------
``project.md`` §3.6's second proof. The four 323 stages are stepped by `engine.scheduler`, each on
its plant wiring (`engine.plant.recirc`) — 323C003's drain to 323F004 and on to 323F010 and
323D002 as same-tick ``Result`` reads, 323F004's and 323F010's pressures read back a tick late as
declared ``State`` tears — and compared on every tick, every field, with V1's stages 1 to 4 run in
V1's order: the chained transcription `test_solution_tank_equivalence.py` already proves against the
ported units called by hand. The boundaries that test holds are ``Boundary`` values here, the
train's plant wiring rewired onto them: the stripper's bottoms (cut 15 % at tick 20) at PFD 208's
composition, 119 C and 172 C, no gas blowing through LV-322501 (handoff A-16), 323D001 and 323E011
at their design pressures, stage 1's vacuum, the LP header and LV-324501B shut. So the scheduler's resolution of the five source kinds, its order and
its one-tick tears are the hand-wired chain's, bit for bit. In the plant the four stages take the
live stripper's (`engine.plant.synthesis`), whose seed hands them the chained test's design.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_323 as d
from ureasim.data import unit_322e001 as s1
from ureasim.data.design_point import R323_FEED_DES_KGH as FEED_DES
from ureasim.data.unit_329 import P_LP_BARA
from ureasim.engine.plant import build_plant, recirc
from ureasim.engine.schedule import Boundary, DeclaredTear, Schedule, State, Step
from ureasim.engine.scheduler import Scheduler
from ureasim.engine.state import PlantState
from ureasim.units.recirc import pre_evaporator as pe
from ureasim.units.recirc import rectifying_column as rc
from tests.equivalence import test_solution_tank_equivalence as stage4
from tests.equivalence.test_solution_tank_equivalence import stage1, stage2, stage3
from tests.equivalence.v1_loader import v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

v1 = stage4.v1

TRAIN = ("323C003", "323F004", "323F010", "323D002")


def _rewired(step: Step, **wiring) -> Step:
    return Step(step.unit, step.name, step.section, step.v1_section,
                {**step.wiring, **wiring}, step.run)


def _train_schedule() -> Schedule:
    """The four stages on their plant wiring, the chained test's boundaries as Boundary values."""
    s = recirc.steps()
    lp = Boundary("lp")
    steps = (
        _rewired(s["323C003"], p_lp_bara=lp, p_d001_bara=Boundary("p_d001"),
                 drain_kgh=Boundary("drain"), tt_323001_c=Boundary("tt_323001"),
                 bottoms_mass_pct=Boundary("bottoms"), tt_322004_c=Boundary("tt_322004"),
                 blow_in_kgh=Boundary("blow"), blow_mw=Boundary("blow_mw")),
        _rewired(s["323F004"], p_e011_bara=Boundary("p_e011")),
        _rewired(s["323F010"], p_lp_bara=lp, p_324e002_bara=Boundary("p_324e002")),
        _rewired(s["323D002"], recycle_kgh=Boundary("rec_kgh"), recycle_t_c=Boundary("rec_t"),
                 recycle_w=Boundary("rec_w")),
    )
    tears = (DeclaredTear(State("323F004", "p_bara"), "323C003", "LV-323501's outlet"),
             DeclaredTear(State("323F010", "p_bara"), "323F004", "LV-323505's outlet"))
    return Schedule(steps=steps, tears=tears)


def test_the_live_stripper_hands_the_train_the_chained_tests_design():
    """The plant's first tick: the synthesis loop's seed sends 323C003 the design the chained test
    drives stage 1 with — LV-322501's 130 482 kg/h at TT-323001 119 C and TT-322004 172 C, the
    bottoms within 0.02 points of PFD 208's composition (the stripper's own split: urea 55.838
    against 55.85, CO2 10.295 against 10.28)."""
    sch, plant = build_plant()
    r = Scheduler(sch, plant).tick().results["322E001"]
    assert (r.sump.drain_kgh, r.sump.tt_323001_c, r.sump.tt_322004_c) == (
        FEED_DES, s1.T_DOWNSTREAM_DES_C, s1.T_BOTTOM_DES_C) == (FEED_DES, 119.0, 172.0)
    for k, v in stage1.BOTTOMS_PCT.items():
        assert r.stripper.bot_mass_pct[k] == pytest.approx(v, abs=0.02), k


def test_the_liquor_train_through_the_scheduler_is_v1s_chain(v1):
    """V1's stages 1 to 4 against the four ported stages stepped by the scheduler, through a
    15 % cut of the stripper's bottoms at tick 20: every field, every tick, ``==``."""
    units, loops = recirc.units()
    # V1's linear chest valves: PV-329202's and PV-329208's trims have their own tests.
    units["323C003"].chest, units["323F010"].chest = rc.V1_CHEST, pe.V1_CHEST
    # V1's bubble point on the design vacuum: the live PT-323204 (B-22) has its own tests.
    units["323F010"].live_bubble = False
    loops["323C003"] = (loops["323C003"][0], rc.pic_329202(rc.V1_CHEST), loops["323C003"][2])
    loops["323F010"] = (loops["323F010"][0], pe.pic_329208(pe.V1_CHEST))
    boundary = dict(drain=FEED_DES, tt_323001=119.0, tt_322004=172.0,
                    bottoms=dict(stage1.BOTTOMS_PCT), blow=0.0, blow_mw=30.0)
    boundary.update(lp=P_LP_BARA, p_d001=d.E003_P_DES_BARA, p_e011=d.F004_P_BARA,
                    p_324e002=d.P_324E002_DES_BARA, rec_kgh=stage4.NO_RECYCLE[0],
                    rec_t=stage4.NO_RECYCLE[1], rec_w=stage4.NO_RECYCLE[2])
    plant = PlantState(units={u: units[u] for u in TRAIN}, loops={u: loops[u] for u in TRAIN},
                       operator={"HIC-323605": d.HIC_323605_DES_PCT, "HV-323D002-TIE": False},
                       boundary=boundary)
    sch = Scheduler(_train_schedule(), plant)
    s = stage4._v1_state(v1)
    U, L = plant.units, plant.loops
    for k in range(500):
        drain = FEED_DES * (0.85 if k >= 20 else 1.0)
        plant.boundary["drain"] = drain
        s.tlag["R324_recyc"], s.tlag["R324_recyc_T"], s.tlag["R324_recyc_comp"] = (
            stage4.NO_RECYCLE)
        a1 = stage1._v1_stage1(v1, s, drain, 119.0, stage1.BOTTOMS_PCT, stage4.DT)
        a2 = stage2._v1_stage2(v1, s, a1["m314"], a1["dep314"][0], a1["dep314"][1], stage4.DT)
        a3 = stage3._v1_stage3(v1, s, a2["m319"], a2["dep319"][0], a2["dep319"][1], a2["blow"],
                               stage4.DT)
        a4 = stage4._v1_stage4(v1, s, a3["m317"], a3["dep317"][0], a3["dep317"][1], stage4.DT)
        r = sch.tick().results
        assert r.keys() == set(TRAIN)
        stage1._assert_tick(a1, r["323C003"], s, U["323C003"], L["323C003"], f"stage 1, tick {k}")
        stage2._assert_tick(a2, r["323F004"], s, U["323F004"], L["323F004"][0],
                            f"stage 2, tick {k}")
        stage3._assert_tick(a3, r["323F010"], s, U["323F010"], *L["323F010"],
                            f"stage 3, tick {k}")
        stage4._assert_tick(a4, r["323D002"], s, U["323D002"], *L["323D002"],
                            f"stage 4, tick {k}")
