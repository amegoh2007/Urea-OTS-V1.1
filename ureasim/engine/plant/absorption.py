"""322E006 and 322C001, the LP absorber's circuit, and the trips that act from the next tick.

What this is
------------
The schedule's entries for V1's ``step_sim`` section 22 (322C001, its 755 through 322E006 — decision
36 — and its vent line with XV-322915's flood) and section 35 (trip 22.1). 322E006 cools 328D003's
744 of this tick; 322C001 takes it as 755, HV-322604's purge of this tick (section 5: its gas and
the liquor its line condensed), FT-322404's 954, and XV-322915 as I 22.1 left it
on the tick before; the flood draws 329D009's header as the network left it this tick (B-73).

The trips are the tick's last step (``project.md`` §3.6, step 4): they read the advanced plant and
act from the next tick. I 22.1 is AC4's PC22.5.1 (decision 39): TT-322015's high-high limit with
its own hysteresis, and HS-322915, the maintained OVERRIDE CLOSE keyswitch.

Source: V1 ``backend/main.py`` ``step_sim`` 9405-9512 and 10135-10148; the units' modules
(`ureasim.units.absorption`).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ureasim.control.interlocks import HystereticInterlock
from ureasim.engine.schedule import Boundary, DeclaredTear, Operator, Result, State, Step
from ureasim.units.absorption import lp_absorber as la
from ureasim.units.absorption.feed_cooler import feed_cooler_322e006
from ureasim.units.absorption.vent_line import trip_22_1, xv_322915_open

__all__ = ["TripsResult", "PlantTrips", "units", "steps", "tears"]


@dataclass(frozen=True)
class TripsResult:
    """The trips on one tick: I 22.1's limit and XV-322915 as it drives it."""

    i_22_1: bool
    xv_322915_open: bool


@dataclass
class PlantTrips:
    """The interlocks the tick evaluates last, with what they drive into the next tick.

    Process utility
    ---------------
    What the DCS's application software decides from the plant's measurements once the units
    have stepped, acting on the plant from the next tick, as V1's sections 34 to 36 act. I 22.1
    floods 322C001's vent line with steam while TT-322015 is over its limit and HS-322915 is not
    set (`vent_line.xv_322915_open`).
    """

    i_22_1: HystereticInterlock = field(default_factory=trip_22_1)
    #: XV-322915 as I 22.1 left it [open]: shut at the design seed.
    xv_322915_open: bool = False

    def step(self, ti_322015_c: float, hs_322915: bool) -> TripsResult:
        """Evaluate the trips on this tick's measurements."""
        limit = self.i_22_1.update_from_pv(ti_322015_c)
        self.xv_322915_open = xv_322915_open(limit, hs_322915)
        return TripsResult(i_22_1=limit, xv_322915_open=self.xv_322915_open)


def units() -> tuple[dict, dict]:
    """322C001 and its controllers, and the trips, seeded on the design (322E006 has no state)."""
    return ({"322C001": la.LpAbsorber(), "TRIPS": PlantTrips()},
            {"322C001": (la.LpAbsorberLoops(),)})


def _322e006(plant, a, dt):
    return feed_cooler_322e006(a["m_744_kgh"], a["t_744_c"], a["m_cw_kgh"])


def _322c001(plant, a, dt):
    liquor = a["liquor_kmolh"]
    return plant.units["322C001"].step(
        *plant.loops["322C001"], dict(a["gas_kmolh"]), a["m_gas_kgh"], a["t_gas_c"],
        a["m_755_kgh"], a["t_755_c"], a["m_cpl_kgh"], a["xv_322915_open"], dt,
        liquor_kmolh=dict(liquor) if liquor else None, p_9_bara=a["p_9_bara"])


def _trips(plant, a, dt):
    return plant.units["TRIPS"].step(a["ti_322015_c"], a["hs_322915"])


def steps() -> dict:
    """The three steps by unit; `ureasim.engine.plant` puts them in V1's order."""
    return {
        "322E006": Step("322E006", "absorber feed cooler", "322", 22, {
            "m_744_kgh": Result("328D003", "m_744_kgh"),
            "t_744_c": Result("328D003", "t_i_c"),
            "m_cw_kgh": Boundary("322E006.cw_kgh")}, _322e006),
        "322C001": Step("322C001", "LP absorber", "322", 22, {
            "gas_kmolh": Result("HV-322604", "gas_kmolh"),
            "m_gas_kgh": Result("HV-322604", "gas_kgh"),
            "t_gas_c": Result("HV-322604", "valve.t_out_c"),
            "liquor_kmolh": Result("HV-322604", "liquor_kmolh"),
            "m_755_kgh": Result("322E006", "m_744_kgh"),
            "t_755_c": Result("322E006", "t_755_c"),
            "m_cpl_kgh": Operator("FIC-322404"),
            "xv_322915_open": State("TRIPS", "xv_322915_open"),
            "p_9_bara": State("329", "p_9_bara")}, _322c001),
        "TRIPS": Step("TRIPS", "interlocks", "322", 35, {
            "ti_322015_c": Result("322C001", "t_ti_322015_c"),
            "hs_322915": Operator("HS-322915")}, _trips),
    }


def tears() -> tuple[DeclaredTear, ...]:
    """The one-tick read the absorber makes: the trips act from the next tick."""
    return (
        DeclaredTear(State("TRIPS", "xv_322915_open"), "322C001",
                     "I 22.1 drives XV-322915 from the advanced plant, V1 section 35"),
    )
