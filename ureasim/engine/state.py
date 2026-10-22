"""The plant state the engine owns: its clock and its recycle tears.

What this is
------------
V1 keeps the inter-section recycle flows in ``s.tlag``, a dictionary read as
``s.tlag.get("R328_748", R328_C002_M748_DES)`` — last tick's value, with the design flow as the
boot default, a recycle hidden inside a cache lookup (handoff A-10). Here each one is a named
field with its design seed and its producer, its consumer and its delay stated beside it; the
idiom does not survive.

The tears carry exactly one step of delay and are never iterated (decision 8, handoff A-10,
decided 2026-09-26): each feeds a capacitance — a liquid holdup or a vapour space — whose time
constant is three orders above the 0.1 s step, so the vessel damps the coupling; converging a
tear inside the tick would delete its delay and change every transient across it. The delay is
structural here: `TearState` is frozen, a consumer reads it during the tick, and the producers'
values replace it only when the tick is committed (`PlantState.end_tick`) — V1's tear-write
points, sections 25 and 32 of ``step_sim``.

The eleven, and where each lives
--------------------------------
=====  ===========  ======================  ==================  ===============================
tear   V1 key       from                    to                  here
=====  ===========  ======================  ==================  ===============================
702    R3232_702    323E011's vent          323C005             ``TearState.m_702_kgh``
756    R322_756     322C001's solvent       323C005             ``TearState.m_756_kgh``
708    R324_708     unit 324's vapour       323C005             ``TearState.m_708_kgh``
748    R328_748     328C003's overhead      328C002             ``TearState.m_748_kgh``
750    R328_750     328C004's overhead      328C002             ``TearState.m_750_kgh``
718A   R3232_718A   323D011, 323P008        328D001             ``TearState.m_718a_kgh``
718B   R3232_718B   323D011, FV-323418      323E003             ``TearState.m_718b_kgh``
739    R328_739     328C004's bottoms       328E007             ``TearState.m_739_kgh``
775    R328_775     328D001's reflux        328C002 (1)         ``RefluxDrum.m_775_prev_kgh``
931    R328_M931    FV-329401's steam       FFIC-329401's PV    ``SecondDesorber.m_931_prev_kgh``
744    R3232_744    322P002's wash          V1's FFIC-329401    retired (2)
=====  ===========  ======================  ==================  ===============================

(1) And the drum's own top lag: the producer reads it too, so it is the producer's state.
(2) Decision 25: FFIC-329401 ratios the steam to 735, which the tank draws on the same tick.

The other cross-tick flows
--------------------------
V1 keeps more of its recycles in ``s.tlag`` than the eleven (``docs/step_sim_dataflow.md`` §2), and
the port's decided divergences add the steam users' draws. Each is a named field here too, seeded
with its design value, written by its producer when the tick is committed:

=================  ==========================  ==============  =================================
tear               from                        to              here
=================  ==========================  ==============  =================================
R324_719 ... 759   unit 324's condensates      328D003 I       ``m_719_kgh`` ... ``m_759_kgh``
R324_706_INERT     324E002's vent inerts       323C005         ``inert_706_kmolh``
741                328C004 through FV-328406   328D003         ``m_741_kgh`` (decision 26)
R324_recyc         LV-324501B's melt recycle   323D002         ``m_recycle_324_kgh``, ``_t_c``,
                                                               ``w_recycle_324``
the steam users    every simulated user        the network     ``steam_users_lp_kgh``,
                                                               ``steam_users_9_kgh`` (B-68, B-73)
911                328C003's battery steam     FT-329403       ``m_911_kgh``
M308_KGH           323P001's 308 wash          322E003         ``m_308_kgh``
(port only)        308's composition and its   322E003         ``w_308``, ``t_308_c``
                   temperature (B-105)
(port only)        323E011's envelope          323C005         ``m_e011_over_kgh``,
                   overflow (A-20)                             ``t_e011_over_c``
(port only)        unit 324's condensers'      328D003 I       ``t_719_c`` ... ``t_759_c``
                   cold ends (B-31)
(port only)        324F002's discharge         323C005         ``t_708_c``
                   temperature (B-97)
=================  ==========================  ==============  =================================

The network steps before every user it supplies (V1 steps it in section 4, the users in sections
7 to 31), so each user's draw reaches its header a tick late, on its PFD row (decision 47).

Equation
--------
    tear(k) = producer output of tick k-1,        tear(0) = the design flow

Source: V1 ``backend/main.py`` 8835-8845 (the reads and their defaults) and 9666-9676 (the
writes); the seeds are the producing units' design flows in ``ureasim.data``.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, replace
from types import MappingProxyType
from typing import Mapping

from ureasim.data.desorption_train import (
    C002_M748_DES_KGH,
    C002_M750_DES_KGH,
    C004_M739_DES_KGH,
)
from ureasim.data.engine import DT_S
from ureasim.data.unit_323c005 import (
    C005_M702_DES_KGH,
    C005_M708_DES_KGH,
    C005_T708_C,
    C005_M756_DES_KGH,
    E002_INERT_DES_KMOLH,
)
from ureasim.data.unit_323e003 import E003_M308_DES_KGH, E003_T_C, W_308
from ureasim.data.unit_323e011 import E011_T_C, M718A_DES_KGH, M718B_DES_KGH
from ureasim.data.unit_324 import E003_T_DES_C, VACUUM_CONDENSERS, W_S402
from ureasim.data.unit_328d003 import (
    D003_M719_DES_KGH,
    D003_M720_DES_KGH,
    D003_M721_DES_KGH,
    D003_M759_DES_KGH,
)
from ureasim.data.unit_329 import (
    LP_USERS_LIVE,
    LP_USERS_PFD,
    MP9_USERS_LIVE,
    MP9_USERS_PFD,
    STEAM_PFD_KGH,
    design_users,
)

__all__ = ["TearState", "TEAR_NAMES", "PlantClock", "PlantState"]


@dataclass(frozen=True)
class TearState:
    """The recycle flows a tick reads, as their producers left them on the tick before [kg/h].

    Process utility
    ---------------
    These are the plant's recycles: the desorbers' overheads returning to 328C002, the
    condensate 323D011 sends back to the reflux drum and the LP carbamate condenser, the vent
    gases scrubbed in 323C005. Each is one tick late on its consumer, as in V1, and each is
    seeded with its design flow, so the first tick reads the PFD.
    """

    #: 323E011's vent through PV-323203 to 323C005 (V1 ``R3232_702``).
    m_702_kgh: float = C005_M702_DES_KGH
    #: 322C001's lean solvent to 323C005 (V1 ``R322_756``), LV-322502's draw.
    m_756_kgh: float = C005_M756_DES_KGH
    #: Unit 324's vapour to 323C005 (V1 ``R324_708``), what 324F002 discharges.
    m_708_kgh: float = C005_M708_DES_KGH
    #: 328C003's overhead, PV-328203's flow, to 328C002 (V1 ``R328_748``).
    m_748_kgh: float = C002_M748_DES_KGH
    #: 328C004's overhead line to 328C002 (V1 ``R328_750``).
    m_750_kgh: float = C002_M750_DES_KGH
    #: 323D011's condensate through 323P008 to 328D001 (V1 ``R3232_718A``).
    m_718a_kgh: float = M718A_DES_KGH
    #: 323D011's condensate through FV-323418 to 323E003 (V1 ``R3232_718B``).
    m_718b_kgh: float = M718B_DES_KGH
    #: 328C004's bottoms to 328E007's hot side (V1 ``R328_739``).
    m_739_kgh: float = C004_M739_DES_KGH
    #: Unit 324's condensates to 328D003's compartment I (V1 ``R324_719`` ... ``R324_759``).
    m_719_kgh: float = D003_M719_DES_KGH
    m_720_kgh: float = D003_M720_DES_KGH
    m_721_kgh: float = D003_M721_DES_KGH
    m_759_kgh: float = D003_M759_DES_KGH
    #: 324E002's vent inerts [kmol/h] to 323C005's vent (V1 ``R324_706_INERT``).
    inert_706_kmolh: Mapping = field(
        default_factory=lambda: MappingProxyType(dict(E002_INERT_DES_KMOLH)))
    #: 741, what FV-328406 recycles from 328C004's bottoms to 328D003 (decision 26); shut at design.
    m_741_kgh: float = 0.0
    #: LV-324501B's melt recycle to 323D002 [kg/h, deg C, mass fractions] (V1 ``R324_recyc``,
    #: ``R324_recyc_T``, ``R324_recyc_comp``); none at design, stage 2's melt in its seed.
    m_recycle_324_kgh: float = 0.0
    t_recycle_324_c: float = E003_T_DES_C
    w_recycle_324: Mapping = field(default_factory=lambda: MappingProxyType(dict(W_S402)))
    #: The steam users' draws on their headers [kg/h, by PFD stream], the simulated users live on
    #: their PFD rows (B-68, decision 47), the rest at their rows; the 9-bar header's likewise.
    steam_users_lp_kgh: Mapping = field(default_factory=lambda: MappingProxyType(
        design_users({**LP_USERS_LIVE, **LP_USERS_PFD})))
    steam_users_9_kgh: Mapping = field(default_factory=lambda: MappingProxyType(
        design_users({**MP9_USERS_LIVE, **MP9_USERS_PFD})))
    #: 328C003's battery-limit steam [kg/h], which FT-329403 reads (PFD 911).
    m_911_kgh: float = STEAM_PFD_KGH["911"]
    #: 323P001's carbamate wash, PFD 308, which 322E003 scrubs with on the next tick (V1
    #: ``M308_KGH``; 323E003 steps in section 23, the scrubber in section 5).
    m_308_kgh: float = E003_M308_DES_KGH
    #: The same wash's composition [mass fractions] and temperature, TT-323006 [deg C] (decided
    #: 2026-10-22, handoff B-105); PFD 308's at design.
    w_308: Mapping = field(default_factory=lambda: MappingProxyType(dict(W_308)))
    t_308_c: float = E003_T_C
    #: A full 323E011 / 323D011 envelope's overflow through PV-323203's vent line to 323C005
    #: [kg/h], and the condensate temperature it leaves at [deg C] (decided 2026-10-03, handoff
    #: A-20); none at design. 323C005 steps before 323E011, so it reads them a tick late.
    m_e011_over_kgh: float = 0.0
    t_e011_over_c: float = E011_T_C
    #: Unit 324's condensers' cold ends [deg C], the temperatures 719, 720, 721 and 759 reach
    #: 328D003 at (decided 2026-10-16, handoff B-31): the train steps after the tank. Seeded on the
    #: PFD's cold ends, the producers' designs.
    t_719_c: float = VACUUM_CONDENSERS["324E002"].hot_out_c
    t_720_c: float = VACUUM_CONDENSERS["324E005"].hot_out_c
    t_721_c: float = VACUUM_CONDENSERS["324E006"].hot_out_c
    t_759_c: float = VACUUM_CONDENSERS["324E007"].hot_out_c
    #: 708's temperature [deg C], 324F002's discharge (decided 2026-10-16, handoff B-97): the train
    #: steps after 323C005. Seeded on the PFD's 121 C.
    t_708_c: float = C005_T708_C

    def written(self, writes: Mapping[str, float]) -> TearState:
        """The tears for the next tick: these, with the producers' writes in place.

        A write to a name that is not a tear is a wiring defect, and is refused rather than
        silently creating a new recycle.
        """
        unknown = set(writes) - set(TEAR_NAMES)
        if unknown:
            raise KeyError(f"not a recycle tear: {sorted(unknown)}")
        return replace(self, **writes)


#: Every tear's field name, in declaration order.
TEAR_NAMES = tuple(f.name for f in fields(TearState))


@dataclass
class PlantClock:
    """Plant time, counted in whole physics steps.

    Process utility
    ---------------
    The exercise clock the trends, the trips and the instructor's events run on. Counting steps
    rather than summing 0.1 s keeps it exact: tick 36 000 is one hour to the bit, where a sum
    of 36 000 tenths is not.
    """

    tick: int = 0

    @property
    def time_s(self) -> float:
        """Plant time [s]: the step count times the fixed step."""
        return self.tick * DT_S


@dataclass
class PlantState:
    """What the engine owns between ticks: the clock, the recycle tears, the units and their
    controllers, what the operator holds and the boundary values.

    A unit's own state, read by a later unit at the top of the tick, is the second channel a tick
    passes state on (``project.md`` §3.6), and it is the unit's: ``units`` holds the unit objects
    by tag, ``loops`` their controllers, ``operator`` the hand valves, hand switches and set points
    the console moves, ``boundary`` the values the plant does not compute. Exercise save and
    restore are its serialisation; the snapshot is a read of it.
    """

    clock: PlantClock = field(default_factory=PlantClock)
    tears: TearState = field(default_factory=TearState)
    units: dict = field(default_factory=dict)
    loops: dict = field(default_factory=dict)
    operator: dict = field(default_factory=dict)
    boundary: dict = field(default_factory=dict)

    def end_tick(self, tear_writes: Mapping[str, float]) -> None:
        """Commit a tick: the producers' tear writes become what the next tick reads, and the
        clock advances one step. Nothing a consumer read during the tick changed under it."""
        self.tears = self.tears.written(tear_writes)
        self.clock.tick += 1
