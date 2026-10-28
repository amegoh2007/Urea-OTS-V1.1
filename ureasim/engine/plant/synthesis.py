"""The HP synthesis loop's steps: the feeds, 322F001, 322E001, 322E002 and 322R001.

What this is
------------
The schedule's entries for V1's ``step_sim`` sections 1 to 3 and the reactor's and condenser's
inventories of section 4, in V1's order:

=========  =====================================================  ===================================
step       what it is                                             the tick before it reads
=========  =====================================================  ===================================
320K002    the CO2 machine, its governor, the discharge line,     PT-329201; 21.2's and 22.2's
           PV-322203 under PIC-322203 (`co2_line`)                XV-322902, 22.2's demand to zero
321        unit 321: the ratio cascade, 321P002 A/B, 321D003,     trips 21.2, 21.8, 21.10, 22.2
           the motive's line transit (`feed.station`)
322F001    the ejector on the live loop's suction and discharge   PT-329201; 322E003's sump level,
                                                                  its overflow's composition and
                                                                  mushy zone
322E001    the stripper on the live loop and 329D005's            PT-329201; 329D005; 322R001's
           saturation, and its bottom sump (`stripper_sump`)      overflow, TT-322014, its feed N/C, H/C
322E002    the condenser on 322D001A/B's saturation, LT-322E002   PT-329201; 322D001A/B
322R001    the reaction, the node profile, the holdup             PT-329201; 322E003's sump, which
                                                                  the forward pulse is drawn from
=========  =====================================================  ===================================

The steam network steps next (section 4): it takes the stripper's condensing and the HPCC's raising
of this tick, on the PFD's basis (decision 47's class) — 322D001A/B's water boiled in 322E002's
shell is the raising, and the drums' steam space feeds the LP header (`units.steam.steam_network`).
The scrubber, HV-322604, the trips and PT-329201 are `synthesis_loop`'s.

A trip acts on the next tick: V1 sets its actions at the foot of the tick (sections 34 and 36), so
the units read the latches the trips left and apply them before they step.

Source: V1 ``backend/main.py`` ``step_sim`` 7269-7987, 10086-10181; the units' modules.
"""

from __future__ import annotations

from dataclasses import dataclass

from ureasim.control.controller import Controller
from ureasim.core.stream import MW_COMP
from ureasim.data import unit_321 as d321
from ureasim.data.unit_322e001 import DUTY_DES_KW as STRIP_DUTY_DES_KW
from ureasim.data.unit_322e002 import LATENT_4BAR
from ureasim.data.unit_329 import RAISE_DES_KGH, STRIP_DES_KGH
from ureasim.data.synthesis_pin import HPCC_RAISE_DES_LIVE_KGS
from ureasim.engine.schedule import DeclaredTear, Operator, Result, State, Step
from ureasim.units.feed.feed_drum import FeedDrum
from ureasim.units.feed.pump import ReciprocatingPump, current_a
from ureasim.units.feed.station import FeedStation
from ureasim.units.steam.steam_network import pfd_basis_kgh
from ureasim.units.synthesis.co2_line import CO2FeedLine, vent_pressure_loop
from ureasim.units.synthesis.condenser_holdup import CondenserHoldup, CondenserStepResult
from ureasim.units.synthesis.ejector import ejector_322f001
from ureasim.units.synthesis.loop_hydraulics import (
    ejector_pressures_bara,
    stripper_feed_t_c,
    stripper_tube_bara,
)
from ureasim.units.synthesis.reactor_inventory import ReactorInventory
from ureasim.units.synthesis.stripper import DUTY_RAW_DES_KW, StripperResult, stripper_322e001
from ureasim.units.synthesis.stripper_level import BottomLevelLoop
from ureasim.units.synthesis.stripper_sump import StripperSump, StripperSumpResult
from ureasim.data.unit_322e003 import LEVEL_NLL_PCT as SCRUB_LEVEL_NLL_PCT

__all__ = ["StripperStep", "CondenserStep", "design_feed_station", "units", "steps", "tears",
           "TRIP_LATCHES"]

#: The trips the feeds read, by trip: AC4's flags 21.2, 21.8 and 21.10 lost, 22.2's latch.
TRIP_LATCHES = ("21_2", "21_8", "21_10", "22_2")


@dataclass(frozen=True)
class StripperStep:
    """322E001 on one tick: the stripper, its sump, and its draw on 329D005 on the PFD's basis."""

    stripper: StripperResult
    sump: StripperSumpResult
    #: The MP steam the shell condenses, the stripper's duty ratio on its PFD row [kg/h].
    strip_kgh: float
    #: The shell's duty, the same ratio on the licensor's 39 400 kW [kW] (V1's ``Q_strip_kjh``).
    duty_kw: float
    #: The tube side's pressure this tick [bar a].
    p_tube_bara: float
    #: The reactor's liquor the stripper took this tick [kg/h], 322R001's discharge of the tick
    #: before: with the bottoms it made, what turns the tubes' room into HV-322605's cap (B-104).
    liquor_in_kgh: float = 0.0


@dataclass(frozen=True)
class CondenserStep:
    """322E002 on one tick, and the LP steam it raises on the PFD's basis [kg/h]."""

    holdup: CondenserStepResult
    raise_kgh: float
    #: The LP header's saturation the shell boiled against this tick [deg C] (V1's
    #: ``T_shell_lp``, the header as it stood at the top of the tick).
    t_shell_c: float


def design_feed_station() -> FeedStation:
    """Unit 321 as V1's ``State`` seeds it: 321P002B running on the ratio cascade's design opening
    under SIC-321951 in CAS, 321P002A the stopped standby in MAN, 321D003 at 65 %. The SICs run
    the plant DCS's tuning (decided 2026-10-08), where V1 seeds 2.0 and 8 s."""
    open_des = d321.PUMP_OPEN_DES_PCT
    speed = open_des / 100.0 * d321.PUMP_RATED_RPM
    sic_b = Controller("SIC_321951", Kc=d321.SIC_321951_KC, Ti=d321.SIC_321951_TI_S,
                       Td=d321.SIC_TD_S, sp=open_des, mv=open_des)
    sic_b.set_mode("CAS")
    return FeedStation(
        pump_a=ReciprocatingPump("321P002A", running=False, opening_pct=0.0, speed_rpm=0.0,
                                 current=d321.PUMP_IDLE_I),
        pump_b=ReciprocatingPump("321P002B", running=True, opening_pct=open_des, speed_rpm=speed,
                                 current=current_a(speed, True)),
        sic_a=Controller("SIC_321950", Kc=d321.SIC_321950_KC, Ti=d321.SIC_321950_TI_S,
                         Td=d321.SIC_TD_S, sp=80.0, mv=0.0),
        sic_b=sic_b,
        drum=FeedDrum(level_frac=0.65, temperature_c=25.0, top_pressure_barg=12.3,
                      makeup_th=42.762, totalizer_t=0.0))


def units() -> tuple[dict, dict]:
    """The loop's units and controllers, seeded on the design (V1 ``State``)."""
    return ({"320K002": CO2FeedLine(), "321": design_feed_station(),
             "322E001": StripperSump(), "322E002": CondenserHoldup(),
             "322R001": ReactorInventory()},
            {"320K002": (vent_pressure_loop(),),
             "322E001": (BottomLevelLoop(),)})


def _stop_machines(st: FeedStation, which: str = "AB") -> None:
    """321P002 A and / or B stopped and their SICs forced to MAN at 0 %."""
    for pid, pump, sic in (("A", st.pump_a, st.sic_a), ("B", st.pump_b, st.sic_b)):
        if pid in which:
            pump.running = False
            sic.set_mode("MAN")
            sic.set_op(0.0)


def _320k002(plant, a, dt):
    line = plant.units["320K002"]
    demand_th = a["raw_demand_th"]
    # Trip 22.2, and 21.2's flag lost — which resets AC4's XVY_322902 flip-flop (PC21.5.1 .14),
    # ANDed by the Safeguard SG1 into XV-322902's command (UD-MR-G00-FF-0006 PC20.1.1 .32; decided
    # 2026-10-16): XV-322902 shut ...
    if a["trip_21_2"] or a["trip_22_2"]:
        line.xv_322902_open = False
        # ... and the boundary's demand to zero, which the instructor restores once the trip is
        # reset or the flag is back (handoff B-88, decided 2026-10-09, decision 83's class).
        plant.operator["320K002-CO2"] = demand_th = 0.0
    return line.step(*plant.loops["320K002"], demand_th, a["p_syn_bara"], dt)


def _321(plant, a, dt):
    st = plant.units["321"]
    trips = {t: a[f"trip_{t}"] for t in TRIP_LATCHES}
    if trips["21_2"]:   # AC4 PC21.5.1: the flag resets XVY-321901, -322901 and -322903's flip-flops
        st.xv_321901_open = st.xv_322901_open = False
        plant.operator["XV-322903"] = False
    if trips["21_8"]:   # PC21.1.1: 321P002A's motor control stops it, its SIC's output clamped
        _stop_machines(st, "A")
    if trips["21_10"]:  # PC21.1.2: 321P002B's
        _stop_machines(st, "B")
    if trips["22_2"]:
        _stop_machines(st)
    for pump in (st.pump_a, st.pump_b):     # a machine's own protection stops it on its fault
        if pump.fault:
            pump.running = False
    return st.step(a["co2_feed_th"], dt)


def _322f001(plant, a, dt):
    p_suct, p_disch = ejector_pressures_bara(a["p_syn_bara"])
    return ejector_322f001(a["motive_kgh"], a["t_motive_c"], a["hic_322602_pct"],
                           scrub_level_frac=a["scrub_level_pct"] / SCRUB_LEVEL_NLL_PCT,
                           xv_322903_open=a["xv_322903_open"], carb_frac=dict(a["carb_frac"]),
                           p_suct_bara=p_suct, p_disch_bara=p_disch,
                           outflow_frac=a["scrub_mushy"])


def _322e001(plant, a, dt):
    t_feed = stripper_feed_t_c(a["t_overflow_c"])
    overflow = dict(a["overflow_kmolh"])
    p_tube = stripper_tube_bara(a["p_syn_bara"], overflow, t_feed)
    # The split's duty bounded by the shell's capacity (B-102, decided 2026-10-21), and by the
    # share of its tubes standing full above a full sump, of the tick before (B-104, decided
    # 2026-10-22); the sump's switches keep V1's unbounded split.
    sump_state = plant.units["322E001"]
    strip = stripper_322e001(a["co2_feed_th"], a["t_steam_c"], p_tube, overflow_kmolh=overflow,
                             feed_nc=a["feed_nc"], feed_hc=a["feed_hc"], t_feed_c=t_feed,
                             level_pct=sump_state.level_pct, shell_bound=sump_state.shell_bound,
                             held_kg=sump_state.held_kg if sump_state.tube_ceiling else 0.0,
                             bundle=sump_state.bundle)
    sump = plant.units["322E001"].step(
        *plant.loops["322E001"], strip.bot_kgh, strip.t_bot, strip.t_steam, strip.top_kmolh,
        strip.top_mw, a["p_syn_bara"], strip.bot_mass_pct, dt)
    duty_ratio = max(strip.duty_raw_kw / DUTY_RAW_DES_KW, 0.0)
    return StripperStep(stripper=strip, sump=sump, strip_kgh=STRIP_DES_KGH * duty_ratio,
                        duty_kw=STRIP_DUTY_DES_KW * duty_ratio, p_tube_bara=p_tube,
                        liquor_in_kgh=sum(overflow.get(k, 0.0) * MW_COMP[k] for k in MW_COMP))


def _322e002(plant, a, dt):
    holdup = plant.units["322E002"].step(
        a["top_kmolh"], a["t_top_c"], a["ej_comp_kgh"], a["ej_t_c"], a["t_shell_c"],
        a["p_syn_bara"], a["phi_fwd"], dt, p_shell_bara=a["p_shell_bara"])
    m_raise_kgs = holdup.condenser.q_steam_kw / LATENT_4BAR
    return CondenserStep(holdup=holdup, raise_kgh=pfd_basis_kgh(
        RAISE_DES_KGH, m_raise_kgs, HPCC_RAISE_DES_LIVE_KGS), t_shell_c=a["t_shell_c"])


def _322r001(plant, a, dt):
    # 322E001's tubes standing full take only what they pass (B-104, decided 2026-10-22): HV-322605
    # discharges at most the bottoms they can take this tick, on this tick's bottoms per kilogram
    # of the reactor's liquor the stripper took.
    take, bot = a["strip_take_kgh"], a["strip_bot_kgh"]
    cap = take * a["strip_liquor_kgh"] / bot if (take is not None and bot > 1e-9) else None
    return plant.units["322R001"].step(
        a["hpcc"], a["co2_feed_th"], a["ratio_pv"], a["hic_322605_pct"], a["hic_322602_pct"],
        a["suction_kgh"], a["p_syn_bara"], dt, sump_holdup_kg=a["scrub_holdup_kg"],
        m_out_cap_kgh=cap, backup_kgh=a["strip_backup_kgh"])


def steps() -> dict:
    """The six steps by unit; `ureasim.engine.plant` puts them in V1's order."""
    p_syn = State("PT-329201", "p_syn_bara")
    return {
        "320K002": Step("320K002", "CO2 machine and its discharge line", "320", 2, {
            "raw_demand_th": Operator("320K002-CO2"), "p_syn_bara": p_syn,
            "trip_21_2": State("SYN-TRIPS", "latched.21_2"),
            "trip_22_2": State("SYN-TRIPS", "latched.22_2")}, _320k002),
        "321": Step("321", "NH3 pumping station", "321", 2, {
            "co2_feed_th": Result("320K002", "feed_th"),
            **{f"trip_{t}": State("SYN-TRIPS", f"latched.{t}") for t in TRIP_LATCHES}}, _321),
        "322F001": Step("322F001", "HP carbamate ejector", "322", 2, {
            "motive_kgh": Result("321", "motive_nh3_kgh"),
            "t_motive_c": Result("321", "discharge_t_c"),
            "hic_322602_pct": Operator("HIC-322602"), "xv_322903_open": Operator("XV-322903"),
            "scrub_level_pct": State("322E003", "level_pct"),
            "carb_frac": State("322E003", "y_overflow"),
            "scrub_mushy": State("322E003", "mushy_factor"), "p_syn_bara": p_syn}, _322f001),
        "322E001": Step("322E001", "HP stripper and its bottom sump", "322", 3, {
            "co2_feed_th": Result("320K002", "feed_to_loop_th"),
            "t_steam_c": State("329", "t_hp_c"), "p_syn_bara": p_syn,
            "overflow_kmolh": State("322R001", "overflow_kmolh"),
            "t_overflow_c": State("322R001", "t_overflow_c"),
            "feed_nc": State("322R001", "l_feed"), "feed_hc": State("322R001", "w_feed")},
            _322e001),
        "322E002": Step("322E002", "HP carbamate condenser", "322", 3, {
            "top_kmolh": Result("322E001", "stripper.top_kmolh"),
            "t_top_c": Result("322E001", "stripper.t_top"),
            "ej_comp_kgh": Result("322F001", "comp_kgh"), "ej_t_c": Result("322F001", "t_c"),
            "t_shell_c": State("329", "t_lp_c"), "p_shell_bara": State("329", "p_lp_bara"),
            "p_syn_bara": p_syn, "phi_fwd": Result("321", "phi_forward")}, _322e002),
        "322R001": Step("322R001", "HP urea reactor", "322", 3, {
            "hpcc": Result("322E002", "holdup.condenser"),
            "co2_feed_th": Result("320K002", "feed_to_loop_th"),
            "ratio_pv": Result("321", "ratio_pv"),
            "hic_322605_pct": Operator("HIC-322605"), "hic_322602_pct": Operator("HIC-322602"),
            "suction_kgh": Result("322F001", "suction_kgh"),
            "scrub_holdup_kg": State("322E003", "holdup_kg"), "p_syn_bara": p_syn,
            "strip_take_kgh": Result("322E001", "sump.take_kgh"),
            "strip_backup_kgh": Result("322E001", "sump.backup_kgh"),
            "strip_bot_kgh": Result("322E001", "stripper.bot_kgh"),
            "strip_liquor_kgh": Result("322E001", "liquor_in_kgh")}, _322r001),
    }


def tears() -> tuple[DeclaredTear, ...]:
    """The loop's one-tick reads: V1 integrates PT-329201, the scrubber, the reactor and the steam
    network after the units that read them, and acts on the trips at the foot of the tick."""
    loop = "PT-329201 is integrated at the foot of V1's tick, section 37"
    out = [DeclaredTear(State("PT-329201", "p_syn_bara"), u, loop)
           for u in ("320K002", "322F001", "322E001", "322E002", "322R001")]
    trips = "V1 sets the trips' actions at the foot of the tick, sections 34 and 36"
    out += [DeclaredTear(State("SYN-TRIPS", f"latched.{t}"), "320K002", trips)
            for t in ("21_2", "22_2")]
    out += [DeclaredTear(State("SYN-TRIPS", f"latched.{t}"), "321", trips) for t in TRIP_LATCHES]
    sump = "322F001 entrains the sump 322E003 fills later in the tick, section 5 (report D-6)"
    out += [DeclaredTear(State("322E003", "level_pct"), "322F001", sump),
            DeclaredTear(State("322E003", "y_overflow"), "322F001", sump),
            DeclaredTear(State("322E003", "mushy_factor"), "322F001",
                         "the overflow's mushy zone throttles the line to 322F001 (handoff B-78)"),
            DeclaredTear(State("322E003", "holdup_kg"), "322R001",
                         "the forward-carbamate pulse is drawn from the sump 322E003 integrates "
                         "later in the tick (handoff B-78)")]
    rec = "322E001 is fed the reactor's overflow of the tick before (the synthesis recycle)"
    out += [DeclaredTear(State("322R001", f), "322E001", rec)
            for f in ("overflow_kmolh", "t_overflow_c", "l_feed", "w_feed")]
    steam = "V1 steps the steam network in section 4, after the shells it heats"
    out += [DeclaredTear(State("329", "t_hp_c"), "322E001", steam),
            DeclaredTear(State("329", "t_lp_c"), "322E002", steam),
            DeclaredTear(State("329", "p_lp_bara"), "322E002",
                         "a tube leak discharges against the shell as the network left it (B-82)")]
    return tuple(out)
