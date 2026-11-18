"""The HP synthesis loop's closing steps: 322E003, HV-322604, its indicators, the trips, PT-329201.

What this is
------------
The schedule's entries for V1's ``step_sim`` section 5 (322E003 with its tempered water, its sump
and HV-322604), section 6 (the loop's displayed indicators), section 34 (trips 21.2, 21.8 and 21.10,
as AC4 executes them) and section 37's loop pressure:

=========  =========================================================  ===========================
step       what it is                                                 the tick before it reads
=========  =========================================================  ===========================
322E003    FIC-329409 and TIC-329005 (`ccw_loop`), the scrubber on    PT-329201; 323P001's 308
           the reactor's off-gas and carryover, its sump              wash, its composition and
                                                                      temperature (B-105,
                                                                      ``TearState``); the
                                                                      backlog PT-329201
                                                                      recondensed (B-76); its
                                                                      sump liquor's bubble
                                                                      pressure (B-91)
HV-322604  the inert purge, its seat capped at what the shell would   PT-329201; 322C001's
           have vented, discharging against 322C001 (handoff A-17)    pressure
322-       the lags of ten displayed indications (`indicators`):      nothing
DISPLAY    what the consoles show, nothing in the plant reads
SYN-TRIPS  the trips' initiators on this tick's plant; their actions  nothing
           the units take from the next tick (`synthesis`)
PT-329201  the loop's pressure on this tick's boundary (`loop_pressure`)
=========  =========================================================  ===========================

V1 evaluates section 34 before I 22.1 (section 35); neither reads the other, so 21.x is one step,
before ``TRIPS``. V1's section 36, trip 22.2 on the loop's high-high pressure, is not built: no plant
document draws it, and the loop's pressure is limited by SV32251 / SV32252 (decision 189).
PT-329201 is the tick's last step, as V1's section 37 is.

Source: V1 ``backend/main.py`` ``step_sim`` 7989-8204, 10086-10133, 10150-10171, 10345-10445.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from ureasim.control.interlocks import Unit21TripInputs, Unit21Trips
from ureasim.core.stream import MW_COMP, atom_ratio
from ureasim.core.units_of_measure import NM3_PER_KMOL
from ureasim.data.engine import DT_S
from ureasim.data.operator_commands import TRIP_21_HAND_SWITCHES
from ureasim.data.unit_320 import CO2_FEED_MW, SYN_P_DES_BARA
from ureasim.data.unit_322e003 import HOLDUP_MAX_KG
from ureasim.data.unit_322_loop import (
    TRIP_21_2_FY_L2_NM3H,
    TRIP_21_2_FY_TD_S,
    TRIP_21_2_P001_TD_S,
    TRIP_21_2_PUMPS_TD_S,
    TRIP_21_8_PDY_L2_BAR,
    TRIP_21_8_RUN_TD_S,
    TRIP_21_8_STOP_TP_S,
)
from ureasim.data.unit_322r001 import C_ATOMS, N_ATOMS, NC_SPAN_MAX
from ureasim.data.unit_323e003 import E003_M308_DES_KGH, E003_T_C, W_308
from ureasim.engine.schedule import DeclaredTear, Operator, Result, State, Step, Tear
from ureasim.units.synthesis.ccw_loop import CcwLoop, CcwResult
from ureasim.units.synthesis.ejector import spindle_phi
from ureasim.units.synthesis.indicators import SynthesisIndicators
from ureasim.units.synthesis.liquor_saturation import saturation_fraction
from ureasim.units.synthesis.loop_pressure import LoopPressure, loop_mass_fraction
from ureasim.units.synthesis.purge_valve import (
    PurgeValveResult,
    purge_capacity_fraction,
    purge_valve_322604,
    seat_ceiling_kgh,
)
from ureasim.units.synthesis.scrubber import (
    LIQUOR_DP_DES_BAR,
    ScrubberResult,
    condensation_capacity,
    scrubber_322e003,
)
from ureasim.units.synthesis.scrubber_sump import ScrubberSump, ScrubberSumpResult

__all__ = ["ScrubberStep", "PurgeStep", "SynthesisTrips", "units", "steps", "tears"]


@dataclass(frozen=True)
class ScrubberStep:
    """322E003 on one tick: its tempered water, the scrubber and its sump."""

    ccw: CcwResult
    scrubber: ScrubberResult
    sump: ScrubberSumpResult
    #: The condensation capacity over its demand the shell ran on [-].
    rho_cond: float
    #: The sump liquor's saturation fraction the condensation took [-] (B-91, decided 2026-10-14).
    sat_frac: float = 1.0


@dataclass(frozen=True)
class PurgeStep:
    """HV-322604 on one tick, and its purge as 322C001 takes it."""

    valve: PurgeValveResult
    #: The purge's gas [kmol/h, positive species] and its mass [kg/h], and the carbamate liquor it
    #: condensed in the line, with any solid it laid down (B-79 (b)), or None when it did neither.
    gas_kmolh: dict
    gas_kgh: float
    liquor_kmolh: dict | None
    #: HV-322604's capacity against the design purge at the loop's pressure as the tick began
    #: [-], V1's published ``vent_frac`` (`purge_valve.purge_capacity_fraction`).
    vent_frac: float


def _unit21_trips() -> Unit21Trips:
    return Unit21Trips(TRIP_21_2_PUMPS_TD_S, TRIP_21_2_P001_TD_S, TRIP_21_2_FY_TD_S,
                       TRIP_21_8_RUN_TD_S, TRIP_21_8_STOP_TP_S)


@dataclass
class SynthesisTrips:
    """Trips 21.2, 21.8 and 21.10 — what the feeds act on from the next tick.

    Process utility
    ---------------
    The synthesis's protection. 21.2, 21.8 and 21.10 as Uhde's application software executes them
    (AC4 PC21, `control.interlocks.Unit21Trips`; decided 2026-10-09, handoff A-12): 21.2 while no
    HP ammonia pump, no carbamate pump or no CO2 reaches the stripper, unless its bypass is turned,
    or a trip hand switch is; each pump's flag on 21.2, its suction's sub-cooling, XV-321901 shut,
    and XV-322901 not open 5 min after it starts (decision 231). V1's 21.2 (321D003 below 5 % or a sub-cooling
    margin), 21.4 (the CO2 lost while synthesis runs; no flag in AC4) and 21.8 / 21.10 (a pump's
    equipment fault) are gone, and so is V1's 22.2, the loop's high-high pressure, which no plant
    document draws (decision 189). What each trip stops is the units'.
    """

    unit21: Unit21Trips = field(default_factory=_unit21_trips)

    @property
    def i_21_2(self):
        """TRIP_21_2_FLAG1, published as an interlock."""
        return self.unit21.flag_21_2

    @property
    def i_21_8(self):
        """TRIP_21_8_FLAG1, 321P002A's."""
        return self.unit21.flag_21_8

    @property
    def i_21_10(self):
        """TRIP_21_10_FLAG1, 321P002B's."""
        return self.unit21.flag_21_10

    @property
    def latched(self) -> dict:
        """Each trip's latch, or its flag lost, by trip."""
        return {i.tag: i.latched for i in (self.i_21_2, self.i_21_8, self.i_21_10)}

    @property
    def trip_21_2(self) -> bool:
        """Trip 21.2's flag lost, which forces PIC-329204 and HV-329601 in unit 329 too."""
        return self.i_21_2.latched

    def step(self, x: Unit21TripInputs, dt: float) -> dict:
        """Evaluate the flags on this tick's plant; return the trips."""
        self.unit21.step(x, dt)
        return self.latched


def units() -> tuple[dict, dict]:
    """322E003's sump and tempered water, the indicators, the trips and PT-329201, seeded on the
    design (the indicators' lags start on their first tick's process values)."""
    return ({"322E003": ScrubberSump(), "322-DISPLAY": SynthesisIndicators(),
             "SYN-TRIPS": SynthesisTrips(), "PT-329201": LoopPressure()},
            {"322E003": (CcwLoop(),)})


def _wash_departures(plant, a, dt) -> dict:
    """The wash's composition and temperature as 323D001 delivered them on the tick before, each
    as its departure from PFD 308 (decided 2026-10-22, handoff B-105), a line residence after they
    left 323P001 (handoff B-110); none where the LPCC carries no species, V1's."""
    if not plant.units["323E003"].track_species:
        return {}
    t_c, w = plant.units["322E003"].wash_arrival(a["m_308_kgh"], a["t_308_c"], a["w_308"], dt)
    return {"wash_dw": {k: w[k] - W_308[k] for k in W_308}, "wash_dt_c": t_c - E003_T_C}


def _322e003(plant, a, dt):
    sump, (ccw,) = plant.units["322E003"], plant.loops["322E003"]
    react = a["reaction"]
    c = ccw.step(react.co2_scale, react.delta_x, dt)
    p = a["p_syn_bara"]
    # The shell's capacity on its effectiveness at the live circulation (B-99 (b1), decided
    # 2026-10-17); the sump's switch keeps V1's linear flow law.
    rho_cond = condensation_capacity(c.m_ccw_kgh, c.pump_frac, c.t_ccw_in_c, p, react.co2_scale,
                                     effectiveness=sump.effectiveness_capacity)
    # The sump's liquor above its bubble point condenses no more than its saturation fraction,
    # whatever the shell could: its own liquor's bubble pressure of the tick before (handoff B-91,
    # decided 2026-10-10 and, on 322E003's own liquor, 2026-10-14).
    sat = saturation_fraction(sump.p_bub_bara, p, LIQUOR_DP_DES_BAR)
    cool = rho_cond if sat >= 1.0 else min(rho_cond, sat)
    # What the sump can take this tick: what drains from it less the backlog it recondenses, and
    # its room up to full over the tick (B-91, decided 2026-10-14).
    room = (a["suction_kgh"] + a["pulse_kgh"] - a["recond_kgh"]
            + (HOLDUP_MAX_KG - sump.holdup_kg - sump.held_kg) * (3600.0 / dt))
    sc = scrubber_322e003(
        react.offgas_kmolh, react.co2_scale, c.t_ccw_in_c, c.m_ccw_kgh, p_loop_bara=p,
        vent_ratio=p / SYN_P_DES_BARA,
        nc_act=atom_ratio(react.overflow_kmolh, N_ATOMS, C_ATOMS, NC_SPAN_MAX),
        hic604_pct=a["hic_322604_pct"], liq_carry_kmolh=a["carry_kmolh"],
        t_carry_c=a["t_overflow_c"], choke_level_pct=sump.level_pct,
        spindle_phi=max(spindle_phi(a["hic_322602_pct"]), 1e-6), cool_frac=cool,
        wash_ratio=a["m_308_kgh"] / E003_M308_DES_KGH, sump_room_kgh=room,
        capacity_frac=rho_cond if sump.effectiveness_capacity else None,
        **_wash_departures(plant, a, dt))
    # The overflow and off-gas lines ride the live loop pressure: PT-329201 sits on the overflow line,
    # where the scrubber's own result carries the two lines' design pins (V1 `main.py` 8105-8106).
    sc = replace(sc, p_overflow_bara=p, p_offgas_bara=p)
    # V1's plant clock steps at the top of its tick, so the sump's LT-329501 reads the tick's end.
    sim_t = (plant.clock.tick + 1) * DT_S
    sr = sump.step(sc.overflow_kmolh, sc.t_overflow_c, a["suction_kgh"], sc.cool_frac, sim_t, dt,
                   recond_kgh=a["recond_kgh"], pulse_kgh=a["pulse_kgh"])
    return ScrubberStep(ccw=c, scrubber=sc, sump=sr, rho_cond=rho_cond, sat_frac=sat)


def _hv322604(plant, a, dt):
    sc = a["scrubber"]
    pv = purge_valve_322604(sc.offgas_kmolh, sc.t_offgas_c, a["hic_322604_pct"], a["p_syn_bara"],
                            vent_cap_kgh=seat_ceiling_kgh(sc.offgas_kmolh, sc.uncond_kgh),
                            p_out_bara=a["p_c001_bara"])
    gas = {k: v for k, v in pv.vapour_kmolh.items() if v > 0.0}
    return PurgeStep(valve=pv, gas_kmolh=gas, gas_kgh=sum(v * MW_COMP[k] for k, v in gas.items()),
                     liquor_kmolh=(dict(pv.liquor_kmolh) if pv.condensing or pv.solid_kmolh > 0.0
                                   else None),
                     vent_frac=purge_capacity_fraction(a["hic_322604_pct"], a["p_syn_bara"]))


def _indicators(plant, a, dt):
    return plant.units["322-DISPLAY"].step(
        a["t_ejector_c"], a["t_top_c"], a["tt_323001_c"], a["t_prod_c"], a["p_bub_bara"],
        a["t_overflow_c"], a["t_offgas_c"], a["t_purge_c"], a["t_ccw_out_c"],
        a["overflow_kmolh"], dt)


def _trips(plant, a, dt):
    x = Unit21TripInputs(
        p002a_running=a["a_on"], p002b_running=a["b_on"],
        p001_running=a["p001a"]["on"] or a["p001b"]["on"], xv_322902_open=a["xv_322902_open"],
        xv_321901_closed=not a["xv_321901_open"], xv_322901_open=a["xv_322901_open"],
        fy_322403_low=a["co2_feed_th"] * 1000.0 / CO2_FEED_MW * NM3_PER_KMOL < TRIP_21_2_FY_L2_NM3H,
        pdy_321203_low=a["pdy_a_bar"] < TRIP_21_8_PDY_L2_BAR,
        pdy_321204_low=a["pdy_b_bar"] < TRIP_21_8_PDY_L2_BAR,
        hs_321634=a["hs_321634"], hs_323604=a["hs_323604"], hs_322606=a["hs_322606"],
        hs_321603=a["hs_321603"], hs_321604=a["hs_321604"])
    return plant.units["SYN-TRIPS"].step(x, dt)


def _pt329201(plant, a, dt):
    frac = loop_mass_fraction(a["reactor_level_pct"], a["condenser_level_pct"],
                              a["sump_level_pct"])
    return plant.units["PT-329201"].step(
        a["nh3_th"] * 1000.0, a["co2_kgh"], a["m_308_kgh"], a["drain_kgh"], a["purge_kgh"],
        a["blow_kgh"], a["uncond_kgh"], a["cool_frac"], frac, a["offgas_kmolh"],
        a["t_offgas_c"], dt, load_ratio=a["load_ratio"], m_leak_kgh=a["leak_kgh"],
        m_reactor_kg=a["m_reactor_kg"], m_scrubber_kg=a["m_scrubber_kg"] + a["scrub_held_kg"],
        condenser_level_pct=a["condenser_level_pct"], sump_level_pct=a["sump_level_pct"],
        dm_liquid=(a["dm_reactor_kgh"], a["dm_scrubber_kgh"], a["dm_condenser_kgh"],
                   a["dm_sump_kgh"]), sat_frac=a["sat_frac"])


def steps() -> dict:
    """The five steps by unit; `ureasim.engine.plant` puts them in V1's order."""
    p_syn = State("PT-329201", "p_syn_bara")
    return {
        "322E003": Step("322E003", "HP scrubber, its tempered water and its sump", "322", 5, {
            "reaction": Result("322R001", "reaction"),
            "carry_kmolh": Result("322R001", "carry_kmolh"),
            "t_overflow_c": Result("322R001", "t_overflow_c"),
            "suction_kgh": Result("322F001", "suction_kgh"),
            "pulse_kgh": Result("322R001", "m_fwd_kgh"),
            "recond_kgh": State("PT-329201", "m_recond_kgh"),
            "hic_322604_pct": Operator("HIC-322604"), "hic_322602_pct": Operator("HIC-322602"),
            "m_308_kgh": Tear("m_308_kgh"), "w_308": Tear("w_308"),
            "t_308_c": Tear("t_308_c"), "p_syn_bara": p_syn}, _322e003),
        "HV-322604": Step("HV-322604", "inert purge to 322C001", "322", 5, {
            "scrubber": Result("322E003", "scrubber"), "hic_322604_pct": Operator("HIC-322604"),
            "p_syn_bara": p_syn, "p_c001_bara": State("322C001", "p_bara")}, _hv322604),
        "322-DISPLAY": Step("322-DISPLAY", "the loop's displayed indicators", "322", 6, {
            "t_ejector_c": Result("322F001", "t_c"),
            "t_top_c": Result("322E001", "stripper.t_top"),
            "tt_323001_c": Result("322E001", "sump.tt_323001_c"),
            "t_prod_c": Result("322E002", "holdup.condenser.t_prod"),
            "p_bub_bara": Result("322E002", "holdup.condenser.p_bub_bara"),
            "t_overflow_c": Result("322E003", "scrubber.t_overflow_c"),
            "t_offgas_c": Result("322E003", "scrubber.t_offgas_c"),
            "t_purge_c": Result("HV-322604", "valve.t_out_c"),
            "t_ccw_out_c": Result("322E003", "scrubber.t_ccw_out_c"),
            "overflow_kmolh": Result("322R001", "reaction.overflow_kmolh")}, _indicators),
        "SYN-TRIPS": Step("SYN-TRIPS", "synthesis trips", "321", 34, {
            "pdy_a_bar": Result("321", "subcooling_a_bar"),
            "pdy_b_bar": Result("321", "subcooling_b_bar"),
            "a_on": State("321", "pump_a.running"), "b_on": State("321", "pump_b.running"),
            "p001a": Operator("323P001A"), "p001b": Operator("323P001B"),
            "co2_feed_th": Result("320K002", "feed_th"),
            "xv_322902_open": State("320K002", "xv_322902_open"),
            "xv_321901_open": State("321", "xv_321901_open"),
            "xv_322901_open": State("321", "xv_322901_open"),
            **{f"hs_{t}": Operator(f"HS-{t}") for t in TRIP_21_HAND_SWITCHES}}, _trips),
        "PT-329201": Step("PT-329201", "synthesis loop pressure", "322", 37, {
            "nh3_th": Result("321", "flow_total_th"), "co2_kgh": Result("320K002", "feed_kgh"),
            "m_308_kgh": Result("323E003", "m_308_kgh"),
            "drain_kgh": Result("322E001", "sump.drain_kgh"),
            "purge_kgh": Result("HV-322604", "valve.mass_kgh"),
            "blow_kgh": Result("322E001", "sump.blowthrough_kgh"),
            "leak_kgh": Result("322E002", "holdup.leak.m_kgh"),
            "uncond_kgh": Result("322E003", "scrubber.uncond_kgh"),
            "cool_frac": Result("322E003", "scrubber.cool_frac"),
            "reactor_level_pct": Result("322R001", "level_pct"),
            "m_reactor_kg": Result("322R001", "m_liq_kg"),
            "m_scrubber_kg": State("322E003", "holdup_kg"),
            "scrub_held_kg": State("322E003", "held_kg"),
            "dm_reactor_kgh": Result("322R001", "dm_liq_kgh"),
            "dm_scrubber_kgh": Result("322E003", "sump.dm_kgh"),
            "dm_condenser_kgh": Result("322E002", "holdup.dm_kgh"),
            "dm_sump_kgh": Result("322E001", "sump.dm_kgh"),
            "condenser_level_pct": Result("322E002", "holdup.level_pct"),
            "sat_frac": Result("322E002", "holdup.sat_frac"),
            "sump_level_pct": Result("322E001", "sump.level_pct"),
            "offgas_kmolh": Result("322R001", "reaction.offgas_kmolh"),
            "load_ratio": Result("322R001", "reaction.co2_scale"),
            "t_offgas_c": Result("322R001", "t_offgas_c")}, _pt329201),
    }


def tears() -> tuple[DeclaredTear, ...]:
    """The closing steps' one-tick reads."""
    loop = "PT-329201 is integrated at the foot of V1's tick, section 37"
    return (
        DeclaredTear(State("PT-329201", "p_syn_bara"), "322E003", loop),
        DeclaredTear(State("PT-329201", "p_syn_bara"), "HV-322604", loop),
        DeclaredTear(Tear("m_308_kgh"), "322E003",
                     "322E003 washes with 323P001's 308 of the tick before (V1 M308_KGH)"),
        DeclaredTear(Tear("w_308"), "322E003",
                     "the wash's composition as 323D001 left it on the tick before (B-105)"),
        DeclaredTear(Tear("t_308_c"), "322E003",
                     "the wash's temperature as 323D001 left it on the tick before (B-105)"),
        DeclaredTear(State("PT-329201", "m_recond_kgh"), "322E003",
                     "the backlog PT-329201 recondensed at the foot of the tick before returns to "
                     "322E003's sump (handoff B-76)"),
        DeclaredTear(State("322C001", "p_bara"), "HV-322604",
                     "HV-322604 discharges against 322C001 as it stood (handoff A-17)"),
    )
