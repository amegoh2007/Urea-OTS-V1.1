"""Unit 321 — the NH3 pumping station, assembled.

What this models
----------------
One tick of the feed section: the N/C ratio controllers trim each machine's speed set point on
the measured ratio, the two 321P002 machines deliver it, the 321D003 drum's inventory and
temperature follow, and the motive stream leaves for the 322F001 ejector after its battery-limit
transit.

Source
------
Ported from V1 ``backend/main.py``, the unit-321 block of `step_sim` (lines 7406-7534),
together with `_feed_transport_td_s` and the `ratio_PV` validity gate. FFIC-321404A / B from
Uhde's functional diagram UD-MR-321-FF-0002 pages 2-4 and the loop summaries UD-MR-321-EC-0001
(F 321404A / B, PDF pages 8-9), decided 2026-10-09 (handoff B-85).

Decided divergence (B-85)
-------------------------
V1 sets each running machine's speed set point open loop: the ratio set point times the live CO2
feed, as a volume, split over the machines running, as an opening. On the plant each machine has
its own PI ratio controller, FFIC-321404A / B, on the measured N/C, FY-321404; its output, per cent
of the speed controller's maximum, is the SIC's external set point, and while the SIC is not in
CAS its balance follows the SIC's working set point, so the switch into CAS is bumpless. Built as
drawn, on the DCS table's tuning (1.00 and 100 s, 1.00 and 90 s), the PV and set point per cent of
FY-321404's 0-4 range. The validity gate that holds the published ratio below 5 % of the design
CO2 now also holds the controllers' outputs: the cascade freezes rather than integrating on a
held measurement.

Where the section's boundaries are
----------------------------------
IN  — the live CO2 feed to the loop (t/h), from the 320K002 discharge node in `synthesis`;
      the operator's N/C set point; the two isolation valve positions.
OUT — the motive ammonia stream to the ejector, already delayed by its line transit, plus the
      `phi_m` and `phi_fwd` fractions the synthesis loop's hydraulics are anchored on.

The ejector itself is 322F001 and belongs to `synthesis`. This module stops at the stream it
hands over, which is where the plant's own unit boundary is.

Equations implemented
---------------------
    e        = ((N/C)_sp - (N/C)_PV) / 4 . 100                  FFIC-321404A / B error [% span]
    dOUT     = Kc (de + dt / Ti . e)                            PI, velocity form
    open_cas = OUT . N_max / N_rated                            the SIC's external set point
    dT_pump  = dP/(rho cp) . [beta T + (1-eta_h)/eta_h]         TI-321020
    td       = line_kg / m_dot . 3600                           BL transit
    N/C      = (m_NH3 / m_CO2) . (M_CO2/M_NH3)                  the published ratio PV
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ureasim.control.controller import Controller
from ureasim.core.numeric import clamp
from ureasim.core.signal import dead_time
from ureasim.core.transport import line_residence_time_s
from ureasim.core.units_of_measure import ABSOLUTE_ZERO_C, ATM_BARA
from ureasim.data.unit_321 import (
    BETA_NH3,
    CO2_DES_KGH,
    CP_NH3,
    EJ_MOTIVE_NH3_DES,
    ETA_PUMP_HYD,
    FEED_NH3_LINE_KG,
    FEED_TD_MAX_S,
    FFIC_321404A_KC,
    FFIC_321404A_TI_S,
    FFIC_321404B_KC,
    FFIC_321404B_TI_S,
    FY_321404_SPAN,
    NC_FACTOR,
    NH3_RHO,
    PUMP_OPEN_DES_PCT,
    PUMP_RATED_RPM,
    P_SYN_DOWN_BAR,
    RATIO_PV_MIN_LOAD_FRAC,
    RATIO_SP_DES,
    SI_321950_SPAN_RPM,
)
from ureasim.units.feed.feed_drum import FeedDrum
from ureasim.units.feed.pump import ReciprocatingPump

#: Upper limit on the motive-flow fraction the synthesis hydraulics are anchored on.
#: Source: V1 `main.py`, `phi_m = clamp(motive / EJ_MOTIVE_NH3_DES, 0.0, 1.5)`. The
#: affinity-law head curve it feeds is not credible far above design, so the clamp is part of
#: the correlation's stated envelope rather than a safety net.
PHI_MOTIVE_MAX = 1.5

#: Key the battery-limit ammonia line's dead-time FIFO is stored under.
#: Source: V1 `main.py`, `_delay(s.tlag, "FEED_NH3", ...)`.
NH3_LINE_KEY = "FEED_NH3"

#: One per cent of a ratio controller's output in the speed controllers' opening, per cent of the
#: rated 152 rpm: the output is per cent of SIC-321950 / 951's maximum, 180 rpm
#: (UD-MR-321-FF-0002 pages 2-3, ``I1 / I2 . SIC:MAX``).
FFIC_OUT_TO_OPENING = SI_321950_SPAN_RPM / PUMP_RATED_RPM


def ratio_controller(tag: str, kc: float, ti_s: float, opening_pct: float,
                     cascade: bool) -> Controller:
    """FFIC-321404A or B, seeded on its machine's opening.

    Process utility
    ---------------
    The N/C controller of one 321P002 machine. Seeded on the opening its speed controller holds,
    in AUTO when that SIC is on cascade, so a plant built at the design point starts with the
    ratio controller already asking for the opening the machine is at.
    """
    ctrl = Controller(tag, Kc=kc, Ti=ti_s, sp=RATIO_SP_DES / FY_321404_SPAN * 100.0,
                      mv=opening_pct / FFIC_OUT_TO_OPENING)
    if cascade:
        ctrl.set_mode("AUTO")
        ctrl.set_sp(RATIO_SP_DES / FY_321404_SPAN * 100.0)
    return ctrl


def pump_discharge_temperature_c(suction_t_c: float, suction_barg: float) -> float:
    """TI-321020, the common discharge temperature [C].

    Process utility
    ---------------
    Liquid ammonia arrives at the ejector hotter than it left the drum, and the rise is not
    negligible: across roughly 152 bar of differential it is several kelvin, and it sets the
    motive enthalpy the HP carbamate condenser receives. Two effects contribute and both are
    in the bracket — the reversible work of compressing an expansible liquid, and the
    irreversible dissipation of whatever the hydraulic efficiency does not convert.

    Equation
    --------
        dT = dP / (rho cp) . [ beta T + (1 - eta_h)/eta_h ]

    The first term vanishes for an incompressible liquid and the second for a perfect pump;
    neither is true, so both are carried.
    """
    dp_pa = max(0.0, P_SYN_DOWN_BAR - (suction_barg + ATM_BARA)) * 1e5
    t_k = suction_t_c + ABSOLUTE_ZERO_C
    rise = dp_pa / (NH3_RHO * CP_NH3) * (BETA_NH3 * t_k + (1.0 - ETA_PUMP_HYD) / ETA_PUMP_HYD)
    return suction_t_c + rise


@dataclass(frozen=True)
class FeedResult:
    """One tick of unit 321, as every downstream consumer reads it.

    Every field here is named because a coupling in `docs/coupling_resolution.md` asked for
    it: the synthesis loop needs the motive stream and its two anchoring fractions, the trips
    need the sub-cooling margins, and the screens need the rest.
    """

    #: Delivered ammonia, pump A and pump B and their total [t/h].
    flow_a_th: float
    flow_b_th: float
    flow_total_th: float
    #: Motive ammonia arriving at the 322F001 ejector [kg/h] — AFTER the line transit.
    motive_nh3_kgh: float
    #: Battery-limit transit time currently applied to that stream [s].
    motive_dead_time_s: float
    #: Motive-flow fraction against design, and its square — the affinity-law head fraction
    #: the synthesis hydraulics are anchored on.
    phi_motive: float
    phi_forward: float
    #: TI-321020 common discharge temperature [C].
    discharge_t_c: float
    #: Real static pressure at the pump suction [bar g] — physics and trips, not the screens.
    suction_barg: float
    #: PT-321201 / PT-321202 as the transmitters read them [bar g].
    feed_pressure_barg: float
    #: PY-321201 / PY-321202 ammonia saturation pressure [bar a].
    vapour_pressure_bara: float
    #: PDYI-321203 / PDYI-321204 sub-cooling margin [bar]. A trip 21.2 initiator.
    subcooling_a_bar: float
    subcooling_b_bar: float
    #: The published molar N/C, its per-machine split, and whether it is trustworthy.
    ratio_pv: float
    ratio_nc_a: float
    ratio_nc_b: float
    ratio_pv_bad: bool
    #: Battery-limit ammonia import LIC-321501 commanded [t/h].
    makeup_th: float
    #: The opening FFIC-321404A / B asked each machine's speed controller for [%].
    cascade_opening_a_pct: float
    cascade_opening_b_pct: float


@dataclass
class FeedStation:
    """Unit 321 as one object: two machines, one drum, one ratio block.

    Process utility
    ---------------
    The section an operator drives to set plant rate. Everything downstream of the synthesis
    loop follows the ammonia this station delivers, so its own dynamics — the ratio controllers'
    90 to 100 s integral, a one-minute drum, a two-second scoop and a 345 s line transit at design
    — are what an operator actually feels when they move the N/C set point.
    """

    pump_a: ReciprocatingPump
    pump_b: ReciprocatingPump
    sic_a: Controller
    sic_b: Controller
    drum: FeedDrum
    #: Operator's molar N/C set point.
    ratio_sp: float = RATIO_SP_DES
    #: Last good published molar N/C. Held, not recomputed, while the measurement is invalid.
    ratio_pv: float = RATIO_SP_DES
    #: XV-321901, the ammonia quick-closing valve on the suction.
    xv_321901_open: bool = True
    #: XV-322901, the ammonia shut-off on the discharge to the loop.
    xv_322901_open: bool = True
    #: Dead-time FIFO for the battery-limit ammonia line.
    line_state: dict = field(default_factory=dict)
    #: FFIC-321404A / B, the machines' N/C ratio controllers (B-85). By default seeded as the
    #: design plant has them: 321P002A's on its stopped machine, 321P002B's on the design opening.
    ffic_a: Controller = field(default_factory=lambda: ratio_controller(
        "FFIC_321404A", FFIC_321404A_KC, FFIC_321404A_TI_S, 0.0, cascade=False))
    ffic_b: Controller = field(default_factory=lambda: ratio_controller(
        "FFIC_321404B", FFIC_321404B_KC, FFIC_321404B_TI_S, PUMP_OPEN_DES_PCT, cascade=True))

    def step(self, co2_feed_th: float, dt: float) -> FeedResult:
        """Advance the whole section one tick.

        The order below is the plant's own causal order and is not interchangeable: the
        ratio controllers read the N/C the machines delivered last tick before they move, the
        drum's balance reads the draw the machines just made, and the discharge temperature
        reads the drum state after that balance — because the ammonia leaving now is the
        ammonia whose temperature the drum just set.
        """
        suction_open = self.drum.suction_available(self.xv_321901_open)
        discharge_open = bool(self.xv_322901_open)

        pv_valid = co2_feed_th >= RATIO_PV_MIN_LOAD_FRAC * (CO2_DES_KGH / 1000.0)
        cas_a = self._ratio_loop(self.ffic_a, self.sic_a, self.pump_a.opening_pct, pv_valid, dt)
        cas_b = self._ratio_loop(self.ffic_b, self.sic_b, self.pump_b.opening_pct, pv_valid, dt)

        q_a_m3h = self.pump_a.step(self.sic_a, dt, suction_open=suction_open,
                                   discharge_open=discharge_open, cas_sp=cas_a)
        q_b_m3h = self.pump_b.step(self.sic_b, dt, suction_open=suction_open,
                                   discharge_open=discharge_open, cas_sp=cas_b)

        flow_a_th = q_a_m3h * NH3_RHO / 1000.0
        flow_b_th = q_b_m3h * NH3_RHO / 1000.0
        flow_total_th = flow_a_th + flow_b_th

        self.drum.step(flow_total_th, dt)

        suction_barg = self.drum.suction_pressure_barg(suction_open)
        feed_barg = self.drum.feed_pressure_barg()
        vapour_bara = self.drum.vapour_pressure_bara()
        subcooling = (feed_barg + ATM_BARA) - vapour_bara

        running = self.pump_a.running or self.pump_b.running
        discharge_t_c = (pump_discharge_temperature_c(self.drum.temperature_c, suction_barg)
                         if (running and discharge_open) else self.drum.temperature_c)

        # The motive stream, and its battery-limit transit. The tank and pump balances above
        # debited the LIVE flow; the difference between that and what arrives is line pack in
        # transit, so this is pure re-timing and conserves mass exactly.
        motive_live_kgh = (flow_total_th * 1000.0) if discharge_open else 0.0
        td_s = line_residence_time_s(FEED_NH3_LINE_KG, 1.0, motive_live_kgh,
                                     t_max_s=FEED_TD_MAX_S)
        motive_kgh = dead_time(self.line_state, NH3_LINE_KEY, motive_live_kgh, td_s, dt)

        phi_motive = clamp(motive_kgh / EJ_MOTIVE_NH3_DES, 0.0, PHI_MOTIVE_MAX)
        phi_forward = phi_motive * phi_motive

        nc_a, nc_b, ratio_bad = self._ratio_pv(flow_a_th, flow_b_th, co2_feed_th)

        return FeedResult(
            flow_a_th=flow_a_th, flow_b_th=flow_b_th, flow_total_th=flow_total_th,
            motive_nh3_kgh=motive_kgh, motive_dead_time_s=td_s,
            phi_motive=phi_motive, phi_forward=phi_forward,
            discharge_t_c=discharge_t_c, suction_barg=suction_barg,
            feed_pressure_barg=feed_barg, vapour_pressure_bara=vapour_bara,
            subcooling_a_bar=subcooling, subcooling_b_bar=subcooling,
            ratio_pv=self.ratio_pv, ratio_nc_a=nc_a, ratio_nc_b=nc_b,
            ratio_pv_bad=ratio_bad, makeup_th=self.drum.makeup_th,
            cascade_opening_a_pct=cas_a, cascade_opening_b_pct=cas_b)

    def _ratio_loop(self, ffic: Controller, sic: Controller, opening_pct: float,
                    pv_valid: bool, dt: float) -> float:
        """One machine's FFIC-321404, and the external set point it hands its SIC [% opening].

        Process utility
        ---------------
        Holds the loop's N/C where the operator set it, whatever the CO2 feed does: the error
        between the operator's ratio and the measured FY-321404, per cent of its 0-4 range,
        moves the machine's speed set point through a PI controller. It is what makes a CO2 rate
        change a ratio disturbance the controller corrects over its integral time, where V1's
        open-loop demand followed the CO2 at once and never saw the ratio it produced.

        Uhde draws two things around the controller (UD-MR-321-FF-0002 pages 2-3):

          * **the balance.** While the speed controller is not on cascade the ratio controller's
            output follows the SIC's working set point — its set point in AUTO, the machine's
            opening, the SIC's PV, in MAN — so putting the SIC on cascade moves nothing.
          * **the output scale.** The output is per cent of the SIC's maximum, 180 rpm, so 100 %
            asks the machine for 118.4 % of its rated 152 rpm, which the SIC's own set-point range
            clamps.

        Below 5 % of the design CO2 the measured N/C means nothing and the published value is
        held (`_ratio_pv`); the controller's output is held with it, so it does not integrate
        an error that is not being measured.
        """
        if sic.mode != "CAS":
            track = sic.sp if sic.mode == "AUTO" else opening_pct
            if ffic.mode != "MAN":
                ffic.set_mode("MAN")
            ffic.set_op(track / FFIC_OUT_TO_OPENING)
            return ffic.mv * FFIC_OUT_TO_OPENING
        if ffic.mode != "AUTO":
            ffic.set_mode("AUTO")
        ffic.set_sp(self.ratio_sp / FY_321404_SPAN * 100.0)
        if pv_valid:
            ffic.step(self.ratio_pv / FY_321404_SPAN * 100.0, dt)
        return ffic.mv * FFIC_OUT_TO_OPENING

    def _ratio_pv(self, flow_a_th: float, flow_b_th: float,
                  co2_feed_th: float) -> tuple[float, float, bool]:
        """The published molar N/C, with its measurement-validity gate.

        Process utility
        ---------------
        Below 5 % of design CO2 feed the divisor collapses and a molar N/C is numerically
        meaningless — an arbitrarily large number that says nothing about the plant. So the
        last good value is HELD and the bad flag is raised, which freezes the cascade rather
        than propagating garbage into a set point. That is the behaviour on a black start and
        on a CO2-feed loss, and it is the reason an operator sees the ratio go bad rather than
        go wild.

        The per-machine split reported while the measurement is bad is half the held ratio
        each: not a measurement, and it is labelled as such by the same flag.
        """
        if co2_feed_th < RATIO_PV_MIN_LOAD_FRAC * (CO2_DES_KGH / 1000.0):
            held = 0.5 * self.ratio_pv
            return held, held, True

        m_co2 = max(co2_feed_th, 1e-6)
        nc_a = (flow_a_th / m_co2) * NC_FACTOR
        nc_b = (flow_b_th / m_co2) * NC_FACTOR
        self.ratio_pv = nc_a + nc_b
        return nc_a, nc_b, False


__all__ = [
    "PHI_MOTIVE_MAX",
    "NH3_LINE_KEY",
    "FFIC_OUT_TO_OPENING",
    "ratio_controller",
    "pump_discharge_temperature_c",
    "FeedResult",
    "FeedStation",
]
