"""The plant as the engine steps it: every scheduled unit in V1's section order, and its tears.

What this is
------------
`build_plant` returns the plant's `Schedule` and a `PlantState` seeded on the design. The schedule
is V1's ``step_sim`` order (``docs/step_sim_dataflow.md`` §1), each unit's wiring in its section's
module:

=====  ====================  ======================================================================
V1     unit                  module
=====  ====================  ======================================================================
1-3    320K002 ... 322R001   `synthesis` — the feeds, 322F001, 322E001, 322E002, 322R001
4      329                   `steam` — the network, its users' draws a tick late
5      322E003, HV-322604    `synthesis_loop` — the scrubber, its sump and water, the purge
6      322-DISPLAY           `synthesis_loop` — the lags of the loop's displayed indicators
7-13   323C003 ... 323D002   `recirc` — the liquor train
14-20  323C005 ... 328D001   `desorption` — 323C005, 328D003, 328E007, the three columns, 328D001
22     322E006, 322C001      `absorption` — the LP absorber's circuit
23-24  323E003, 323E011      `recirc` — the two LP condensers
26-31  HV-329605/6 ... train `evaporation` — the motive steam, both stages, the UF85 dosing (335),
                            the vacuum train
31     329-USERS             `steam` — every user's draw on the headers' PFD basis
33     SIC-323902            `recirc` — 323P001B's standby faceplate, stepped on its own output
34-36  SYN-TRIPS             `synthesis_loop` — 21.2, 21.8, 21.10 (AC4), 22.2, acting next tick
35     TRIPS                 `absorption` — I 22.1, acting from the next tick
37     PT-329201             `synthesis_loop` — the loop's pressure, the tick's last step
=====  ====================  ======================================================================

V1's section 6, the synthesis loop's display lags, is a step: V1 advances the lags once per physics
step, and the console packet (`ureasim.engine.packet`) publishes them. UF85 (unit 335, section 30)
doses live on LV-324501A's route (decided 2026-10-16, decision 123).

The recycle tears are written at the end of the tick from the producers' results (`TEAR_WRITES`):
V1's eleven (handoff A-10) and the cross-tick flows `engine.state` lists beside them.
"""

from __future__ import annotations

from ureasim.engine.plant import (
    absorption,
    desorption,
    evaporation,
    recirc,
    steam,
    synthesis,
    synthesis_loop,
)
from ureasim.engine.plant.boundary import boundary_values, operator_seeds
from ureasim.engine.plant.evaporation import DOSING, MOTIVE, TRAIN
from ureasim.engine.plant.steam import USERS
from ureasim.engine.schedule import Result, Schedule
from ureasim.engine.state import PlantState

__all__ = ["ORDER", "TEAR_WRITES", "LIVE_INLET_UNITS", "schedule", "build_plant"]

#: The units in V1's ``step_sim`` order.
ORDER = ("320K002", "321", "322F001", "322E001", "322E002", "322R001", "329", "322E003",
         "HV-322604", "322-DISPLAY", "323C003", "323F004", "323F010", "323D002", "323C005",
         "328D003", "328E007", "328C002", "328C003", "328C004", "328D001", "322E006", "322C001",
         "323E003", "323E011", MOTIVE, "324E001", "324E003", DOSING, TRAIN, USERS, "SIC-323902",
         "SYN-TRIPS", "TRIPS", "PT-329201")

#: Each recycle tear and the producer output written into it when the tick is committed.
TEAR_WRITES = {
    "m_702_kgh": Result("323E011", "m_702_kgh"),
    "m_756_kgh": Result("322C001", "m_756_kgh"),
    "m_708_kgh": Result(TRAIN, "streams_kgh.708"),
    "m_748_kgh": Result("328C003", "m_748_kgh"),
    "m_750_kgh": Result("328C004", "m_750_kgh"),
    "m_718a_kgh": Result("323E011", "m_718a_kgh"),
    "m_718b_kgh": Result("323E011", "m_718b_kgh"),
    "m_739_kgh": Result("328C004", "m_739_kgh"),
    "m_719_kgh": Result(TRAIN, "streams_kgh.719"),
    "m_720_kgh": Result(TRAIN, "streams_kgh.720"),
    "m_721_kgh": Result(TRAIN, "streams_kgh.721"),
    "m_759_kgh": Result(TRAIN, "streams_kgh.759"),
    "inert_706_kmolh": Result(TRAIN, "inert_706_kmolh"),
    "m_741_kgh": Result("328C004", "m_741_kgh"),
    "m_recycle_324_kgh": Result("324E003", "route.recycle_kgh"),
    "t_recycle_324_c": Result("324E003", "route.recycle_t_c"),
    "w_recycle_324": Result("324E003", "route.recycle_w"),
    "steam_users_lp_kgh": Result(USERS, "users_lp_kgh"),
    "steam_users_9_kgh": Result(USERS, "users_9_kgh"),
    "m_911_kgh": Result(USERS, "m_911_kgh"),
    "m_308_kgh": Result("323E003", "m_308_kgh"),
    "w_308": Result("323E003", "w_308"),
    "t_308_c": Result("323E003", "t_c"),
    "m_e011_over_kgh": Result("323E011", "m_overflow_kgh"),
    "t_e011_over_c": Result("323E011", "t_c"),
    "t_719_c": Result(TRAIN, "nodes.324E002.hot_out_c"),
    "t_720_c": Result(TRAIN, "nodes.324E005.hot_out_c"),
    "t_721_c": Result(TRAIN, "nodes.324E006.hot_out_c"),
    "t_759_c": Result(TRAIN, "nodes.324E007.hot_out_c"),
    "t_708_c": Result(TRAIN, "t_708_c"),
}

#: The units that charge their inlets at their producers' live temperatures, each as its
#: departure from the producer's design (handoff B-31, decided 2026-10-16). A unit's
#: ``live_inlets = False`` is V1's design temperatures, which the plant-level harnesses keep.
LIVE_INLET_UNITS = ("323C005", "328D003", "328C002", "323E003", "323E011")

_SECTIONS = (synthesis, steam, synthesis_loop, recirc, desorption, absorption, evaporation)


def schedule() -> Schedule:
    """The plant's schedule, in V1's order, with every one-tick read declared."""
    steps: dict = {}
    for module in _SECTIONS:
        steps.update(module.steps())
    tears = tuple(t for module in _SECTIONS for t in module.tears())
    return Schedule(steps=tuple(steps[u] for u in ORDER), tears=tears, tear_writes=TEAR_WRITES)


def build_plant() -> tuple[Schedule, PlantState]:
    """The plant's schedule and its state, every unit and controller seeded on the design."""
    plant = PlantState(operator=operator_seeds(), boundary=boundary_values())
    for module in _SECTIONS:
        units, loops = module.units()
        plant.units.update(units)
        plant.loops.update(loops)
    return schedule(), plant
