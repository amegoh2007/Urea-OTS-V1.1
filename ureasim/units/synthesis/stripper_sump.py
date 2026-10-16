"""The 322E001 bottom sump — LT-322501, LIC-322501 and the LV-322501 letdown.

What this models
----------------
Below the falling-film tubes, 322E001 has a bottom head that holds a few tonnes of urea
solution. It is a buffer, a level measurement and a thermal residence volume all at once, and
everything the stripper makes leaves the synthesis loop through the one valve at the bottom
of it. That valve, LV-322501, lets 140 bar a of hot urea liquor down to the 4 bar a LP
recirculation section, which is the largest single pressure letdown on the plant.

Six pieces of behaviour follow, and this module is all six:

1. **LIC-322501**, a direct-acting velocity-form PID on the level, on the plant DCS's tuning.
2. **The LV-322501 letdown law**, driven by the LIVE synthesis pressure rather than a frozen
   design differential.
3. **The mushy-zone restriction**, which throttles the drain as the bottoms cool toward the
   urea melting point.
4. **The lost liquid seal**, which converts the drain from liquid to gas once the outlet
   nozzle uncovers.
5. **The bottoms transit**, a flow-dependent dead time between the tube exit and the sump.
6. **The sump energy balance**, which turns the film temperature into what TT-322004 reads.

Why the sump is a separate module from the stripper
----------------------------------------------------
Because it is a separate piece of equipment with its own state. `stripper.py` is a pure
function of its inputs — the same feed and the same steam give the same answer every time.
The sump integrates: it has a level, a controller with a memory, and a transport line with a
FIFO in it. Mixing the two would make the stripper's component split untestable without also
standing up a controller and a clock.

The sump's level does feed back into the stripper, through the liquid holdup the two reaction
rate laws see. That is a declared tear: the stripper is called with the level from the top of
the tick, exactly as V1 calls it.

Source
------
Ported from V1 ``backend/main.py`` ``step_sim``, the 322E001 bottom-sump block, and its
constant block. Findings D-8, D-20, A-3, L3-1, L3-6 and L3-7 are carried with it.

What is NOT here
----------------
The 180 s thermal lag V1 applies to the published TT-322004 is applied here, because
``STRIP_T_TAU_S`` is documented as the stripper's own liquid holdup plus HP shell metal — it
is process, not instrumentation, and it belongs with the equipment that produces the
temperature. V1 applies it in a later display block instead; nothing between the two points
reads the value, so the published number is the same either way.

The one consumer that reads it downstream is the 323C003 letdown-flash duty. V1 read it
through a store key that is never written; the port reads it live, by the process engineer's
decision (As-Built §XXVIII.6).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ureasim.control.process_loop import pv_ok
from ureasim.core.numeric import clamp
from ureasim.core.signal import dead_time, first_order_lag
from ureasim.core.transport import line_residence_time_s
from ureasim.control.valve import valve_liquid_anchored
from ureasim.data.unit_320 import SYN_P_DES_BARA
from ureasim.data.unit_321 import CO2_DES_KGH, FEED_TD_MAX_S
from ureasim.data.unit_322e001 import (
    BOTTOMS_DES_KGH,
    BOTTOMS_LINE_M3,
    LEVEL_SP_DES_PCT,
    LEVEL_SPAN_M,
    LIC_322501_KC,
    LIC_322501_TD_S,
    LIC_322501_TF_S,
    LIC_322501_TI,
    LV_322501_FL,
    LV_322501_OPEN_DES_PCT,
    LV_322501_P_DOWN_BARA,
    LV_322501_PV_CONVAL_BARA,
    LV_322501_T_CONVAL_C,
    P_DES_BARA,
    RHO_BOTTOM,
    STEAM_T_DES_C,
    SUMP_AREA_M2,
    SUMP_NTU_DES,
    T_BOTTOM_DES_C,
    T_CRYSTALLISATION_C,
    T_DOWNSTREAM_DES_C,
    T_STRIPPER_TAU_S,
    TT_323001_GAIN,
)
from ureasim.data.unit_323 import W_S208
from ureasim.thermo import iapws, real_gas, service
from ureasim.thermo.ammonia_water import K_RATIO_T_HI_C, K_RATIO_T_LO_C
from ureasim.thermo.urea_liquor import RIGOROUS_FAILURES
from ureasim.units.consequence.crystallisation import mushy_flow_factor
from ureasim.units.consequence.seal import (
    blowthrough_kgh,
    gas_density_ideal,
    seal_fraction,
)
from ureasim.units.synthesis.stripper import stripper_322e001

#: FIFO keys in the sump's own dead-time and lag stores.
BOTTOMS_LINE_KEY = "322E001_BOT_KGH_LAG"
TT_322004_KEY = "TT322004"

#: Design differential across LV-322501 as the letdown law and the blow-through law both
#: measure it [bar], 136.7. Written as the subtraction of the two pressures it is made of,
#: per handoff A-13: a check valve's or a letdown valve's design differential is a difference
#: between two data constants and must move when either of them is revised.
#:
#: Note that this is NOT `unit_322e001.LV_322501_DP_DES_BAR` (139.8). That constant is the
#: valve datasheet's own operating point, taken at the 144.0 bar a stripper shell and the
#: 4.2 bar a line downstream of the valve. This one is measured between PT-329201, which is
#: what the live drain head is read from, and the 4.0 bar a LP-loop reference the law is
#: anchored against — so the ratio is exactly 1.0 at design, which the datasheet pair would
#: not give. Both are real numbers about the same valve and neither may be substituted for
#: the other.
LV_322501_DP_ANCHOR_BAR = SYN_P_DES_BARA - LV_322501_P_DOWN_BARA

#: LV-322501's liquor on Uhde's CONVAL basis: the vendor's boiling pressure over the rigorous
#: surface's for PFD 208 at the vendor's 173 C, 1.094 — the level is the vendor's, the slope in
#: temperature and composition the model's (decided 2026-09-30, handoff B-46).
LV_322501_PV_SCALE = LV_322501_PV_CONVAL_BARA / service.bubble_p(W_S208, LV_322501_T_CONVAL_C)


def bottoms_pv_bara(bot_mass_pct: dict, t_bot_c: float) -> float:
    """The vapour pressure the stripper bottoms carry into LV-322501 [bar a].

    Process utility
    ---------------
    The Pv of the valve's IEC 60534 choke. The bottoms leave the stripper at 172 C with their
    ammonia, carbon dioxide and inerts still dissolved, and boil at about 99 bar a — far above the
    4 bar a the valve lets them down to — so the valve flashes, and its flow is set by the
    synthesis pressure and this vapour pressure, not by the LP section (Uhde's CONVAL sizing,
    "Flashing!" on every operating point). Poorer stripping leaves more ammonia and CO2 in the
    bottoms, lifts Pv, and chokes the drain harder.

    Equation
    --------
        Pv = 1.094 . P_bub,rigorous(w_bot, T_bot)                       inside [80.05, 209.95] C
        Pv = 1.094 . P_bub(w_bot, T_edge) . Psat_w(T_bot) / Psat_w(T_edge)   beyond, on water's line

    and 1.094 . Psat_w(T_bot) where the rigorous surface refuses the composition — the form
    `thermo.ammonia_water.liquor_pv_bara` gives unit 328's liquors.

    Source: the scale is Uhde's pv1 99.0 bar a over the rigorous surface's 90.49 at PFD 208 and
    173 C; the composition is the stripper's published bottoms.
    """
    w = {k: v / 100.0 for k, v in bot_mass_pct.items()}
    t_eval = min(max(t_bot_c, K_RATIO_T_LO_C), K_RATIO_T_HI_C)
    try:
        pb = service.bubble_p(w, t_eval)
    except RIGOROUS_FAILURES:
        return LV_322501_PV_SCALE * iapws.psat_bara(t_bot_c)
    if t_eval != t_bot_c:
        pb = pb * iapws.psat_bara(t_bot_c) / iapws.psat_bara(t_eval)
    return LV_322501_PV_SCALE * pb


#: The design bottoms' vapour pressure [bar a], ~101.4: `bottoms_pv_bara` at the stripper's own
#: design output, so the live call at the design state returns the identical float and the
#: letdown's ratio is exactly 1.0 there.
_BOTTOMS_DES = stripper_322e001(CO2_DES_KGH / 1000.0, STEAM_T_DES_C, P_DES_BARA)
LV_322501_PV_DES_BARA = bottoms_pv_bara(_BOTTOMS_DES.bot_mass_pct, _BOTTOMS_DES.t_bot)

#: Molecular weight the blow-through falls back to when the top-gas vector is empty [g/mol].
#: A cold, empty stripper has no composition to take one from, and a zero would divide.
#: Source: V1 `main.py`, the ``strip["top_MW"] or 30.0`` fallback.
TOP_GAS_MW_FALLBACK = 30.0


# ======================================================================================
# LIC-322501
# ======================================================================================

@dataclass
class BottomLevelLoop:
    """LIC-322501 — the bottom-solution level controller, in V1's form on the DCS's tuning.

    Process utility
    ---------------
    Direct acting on a fail-closed, air-to-open valve, which is correct negative feedback:
    the level rises, the output rises, LV-322501 opens, the drain rises and the level comes
    back. On a trip the air fails and the valve shuts, keeping the loop's inventory inside
    the loop rather than dumping 140 bar a of liquor into the LP section.

    Why it is proportional-dominant
    --------------------------------
    A level is an INTEGRATING process: the valve sets a flow, and a flow accumulates into a
    level. An integral-dominant controller on an integrating process is two integrators in
    series, and the loop limit-cycles.

    The tuning is the plant DCS's (decided 2026-10-08): gain 0.20, TI 280 s, and a 1.0 s
    derivative behind a 1.0 s filter, where V1 runs 2.5 and 90 s with none. The plant's loop is
    the slower one, and the trainee sees its latency.

    Why this is not a `control.process_loop.ProcessLoop`
    ----------------------------------------------------
    Because the proportional term acts on the ERROR, not on the PV:

        du = Kc . [ (e_k - e_{k-1}) + (dt/Ti) . e_k ] ,   e = PV - SP

    With a constant set point those are the same expression — ``e_k - e_{k-1}`` reduces to
    ``PV_k - PV_{k-1}`` and the whole thing is a direct-acting I-PD. They separate the moment
    an operator moves the set point: this form gives a proportional KICK out of the valve of
    ``-Kc . delta_SP``, and an I-PD form gives none. That kick is real DCS behaviour for this
    configuration and it is part of what a trainee is being taught, so the form is preserved.
    LIC-322501 is the only loop in V1 written this way.

    The derivative is on the measurement, filtered, by `ProcessLoop`'s own law: a set-point move
    kicks the proportional term only.

        du = Kc . [ (e_k - e_{k-1}) + (dt/Ti) . e_k + (G_k - G_{k-1}) ]
        G_k = Tf/(Tf+dt) . G_{k-1} + Td/(Tf+dt) . (L_k - L_{k-1})        [direct acting]

    Bad-PV handling, and the contrast with PIC-322203
    --------------------------------------------------
    On a non-finite level or set point this loop holds the last good error and skips the
    increment, so ``e_prev`` is re-assigned its own value and the output is genuinely frozen.
    That is what "freeze last good" means and it is implemented correctly here.

    V1's inline PIC-322203 carries the same comment and does NOT do this: it advances its
    history past the bad sample, so a single NaN latches the vent wide open one tick later.
    The rewrite installs PIC-322203 as a `ProcessLoop` instead, by the process engineer's
    decision (As-Built §XVII.5), so both loops now freeze on a bad sample.
    """

    #: Valve demand to LV-322501 [%].
    op: float = LV_322501_OPEN_DES_PCT
    #: Set point [% of level span].
    sp: float = LEVEL_SP_DES_PCT
    #: Measured level [%], written at the END of the previous tick from the settled level.
    pv: float = LEVEL_SP_DES_PCT
    #: Last good error [%], seeded at zero so the first design tick gives du = 0 exactly.
    e_prev: float = 0.0
    #: Last good level [%] — None until the first sample, which then takes no derivative — and
    #: the derivative's filtered state [%], so the first tick's derivative is exactly zero.
    level_prev: float | None = None
    d_filt: float = 0.0
    #: AUTO or MAN.
    mode: str = "AUTO"
    #: Whether the measurement or the set point is unusable.
    pv_bad: bool = False

    def step(self, level_pct: float, dt: float) -> float:
        """Advance one tick on the level at the TOP of the tick and return the stroke [%].

        The level passed in is the state before this tick's mass balance, which is the same
        tear convention every other loop in the flowsheet uses: a controller acts on what the
        transmitter had time to report, not on the result of its own action.
        """
        self.pv_bad = not pv_ok(level_pct, self.sp)
        if self.pv_bad:
            # Hold the last good error. The assignment below is then a no-op, which is what
            # actually freezes the output — see the class docstring.
            error = self.e_prev
        else:
            error = level_pct - self.sp          # DIRECT acting: level above SP opens the valve
            if self.mode == "AUTO":
                # The filtered derivative on the level, its sign the loop's (direct acting).
                prev = level_pct if self.level_prev is None else self.level_prev
                g_k = (LIC_322501_TF_S / (LIC_322501_TF_S + dt)) * self.d_filt + (
                    LIC_322501_TD_S / (LIC_322501_TF_S + dt)) * (level_pct - prev)
                derivative = g_k - self.d_filt
                self.d_filt = g_k
                self.op = clamp(
                    self.op + LIC_322501_KC * ((error - self.e_prev)
                                               + (dt / LIC_322501_TI) * error + derivative),
                    0.0, 100.0)
            self.level_prev = level_pct          # the history stays current in MAN
        self.e_prev = error                      # tracked for a bumpless MAN -> AUTO transfer
        return clamp(self.op, 0.0, 100.0)

    def publish(self, level_pct: float) -> None:
        """Write this tick's settled level as the faceplate PV for the next one."""
        self.pv = level_pct


# ======================================================================================
# The letdown law
# ======================================================================================

def letdown_kgh(opening_pct: float, syn_bara: float, pv_bara: float) -> float:
    """Liquid through LV-322501 before any restriction [kg/h].

    Process utility
    ---------------
    This is the plant's main product outlet, and the reason it is written against the LIVE
    synthesis pressure is a start-up lesson. LV-322501 is a pressure letdown, not a gravity
    drain: what pushes liquor through it is the loop's own pressure, so on a black start,
    with the loop at atmospheric, the valve can be wide open and pass nothing.

    The bottoms flash in the valve, as Uhde sized it ("Flashing!", pv1 99 bar a): the flow is
    the IEC 60534-2-1 liquid law, choked on FL^2 (P_syn - FF . Pv), so it answers the synthesis
    pressure and the bottoms' own vapour pressure, ``pv_bara``, and not the LP section downstream
    (decided 2026-09-30, handoff B-46). V1 runs an incompressible orifice law on the full
    differential, which cannot choke.

    Equation
    --------
        m = m_des . (Op / Op_des) . sqrt(dP_eff / dP_eff,des),
        dP_eff = min(P_syn - P_down, FL^2 (P_syn - FF . Pv))

    Linear in the stroke because the trim is linear. Exactly 1.0 at the design state, so the
    PFD bottoms flow is reproduced bit-exact.

    ``P_syn`` is PT-329201, the 322E003 overflow line, read from the PREVIOUS tick — the same
    loop-break convention the rest of the HP loop uses.
    """
    return valve_liquid_anchored(
        BOTTOMS_DES_KGH, opening_pct / 100.0, syn_bara, LV_322501_P_DOWN_BARA, RHO_BOTTOM,
        LV_322501_OPEN_DES_PCT / 100.0, SYN_P_DES_BARA, LV_322501_P_DOWN_BARA, RHO_BOTTOM,
        characteristic="linear", fl=LV_322501_FL, pv_bara=pv_bara,
        pv_des_bara=LV_322501_PV_DES_BARA)


# ======================================================================================
# The sump energy balance
# ======================================================================================

def sump_outlet_temperature_c(t_film_c: float, t_steam_c: float, drain_kgh: float) -> float:
    """Temperature of the solution leaving the sump [deg C] — what TT-322004 measures.

    Process utility
    ---------------
    The sump is a stirred buffer below the steam-heated tubes, and it loses heat. How much it
    loses depends on how long the liquor sits in it, which depends on how far LV-322501 is
    open. So opening the valve does not only move more product — it moves HOTTER product,
    because the residence time falls and there is less time to lose heat. Closing it cools the
    bottoms toward the crystallisation floor, which is the physical mechanism behind a
    plugged stripper bottom: throttle the outlet, the liquor cools, the mushy-zone factor
    throttles it further, and the operator has a runaway in the closing direction.

    Equations
    ---------
    Steady-state sump energy balance — film enthalpy in equals drain enthalpy out plus the
    loss to surroundings::

        m.cp.T_film = m.cp.T_out + UA.(T_out - T_amb)

    `stripper.py` already reports the DESIGN-drain sump outlet as its bottoms temperature,
    because that is what the licensor balance is anchored on, so the film above it is

        T_film_actual = T_bot.(1 + tau) - tau.T_amb ,   tau = UA/(m_des.cp) = SUMP_NTU_DES

    Eliminating the film and writing ``r = m_drain / m_des`` gives the closed form::

        T_out = [ r.(1 + tau).T_bot + tau.(1 - r).T_amb ] / (r + tau)

    At r = 1 this returns T_bot exactly, so the design heat and mass balance is untouched.
    Its derivative is ``tau.(1 + tau).(T_bot - T_amb) / (r + tau)^2``, which is positive
    whenever the bottoms are above the floor — so the sign is guaranteed, not tuned: more
    drain is always hotter.

    Limits and guards
    -----------------
    Capped at the condensing shell, because a bottoms stream cannot out-heat the steam that
    heats it. Below the crystallisation floor the relation is bypassed entirely and the film
    temperature is passed straight through: on a cold start or a solidified bottom there is no
    hot-film residence effect to model, and the closed form would be extrapolating a heat loss
    against a temperature difference of the wrong sign.

    ``T_amb`` here is the 132.7 deg C urea melting point rather than a plant ambient. That is
    deliberate: it is the floor a throttled sump asymptotes to, and it is the temperature at
    which the consequence of getting there actually occurs.
    """
    if t_film_c <= T_CRYSTALLISATION_C:
        return t_film_c
    r_drain = drain_kgh / BOTTOMS_DES_KGH
    t_out = (r_drain * (1.0 + SUMP_NTU_DES) * t_film_c
             + SUMP_NTU_DES * (1.0 - r_drain) * T_CRYSTALLISATION_C) \
        / (r_drain + SUMP_NTU_DES)
    return min(t_out, t_steam_c)


# ======================================================================================
# The published result
# ======================================================================================

@dataclass(frozen=True)
class StripperSumpResult:
    """One tick of the 322E001 bottom sump, as every downstream consumer and screen reads it."""

    # ---- level and the loop ------------------------------------------------------------
    #: LT-322501 bottom-sump level [%]. The state this module exists for.
    level_pct: float
    #: LV-322501 stroke [%] — LIC-322501's output after its own limits.
    lv_opening_pct: float

    # ---- what leaves ---------------------------------------------------------------------
    #: Liquid through LV-322501 after the mushy-zone and seal factors [kg/h]. The feed to
    #: 323C003.
    drain_kgh: float
    #: The same stream as the letdown law gives it, before either factor [kg/h]. Published so
    #: a screen can show how much of the shortfall is thermal and how much is hydraulic.
    letdown_raw_kgh: float
    #: Gas escaping through the same trim once the outlet nozzle uncovers [kg/h]. Exactly 0.0
    #: at any normal level.
    blowthrough_kgh: float

    # ---- what arrives --------------------------------------------------------------------
    #: Bottoms reaching the sump this tick [kg/h], delayed by the line transit.
    bottoms_in_kgh: float
    #: Transit time currently applied to that stream [s].
    bottoms_dead_time_s: float

    # ---- the two restrictions ------------------------------------------------------------
    #: Mushy-zone flow factor [-]. 1.0 fully molten.
    mushy_factor: float
    #: Fraction of the outlet nozzle still covered [-]. 1.0 sealed.
    seal_fraction: float

    # ---- temperatures [deg C] ------------------------------------------------------------
    #: Sump outlet temperature, instantaneous.
    t_out_c: float
    #: TT-322004 as the operator sees it — the same temperature through the 180 s thermal lag.
    tt_322004_c: float
    #: TT-323001, the post-letdown flash temperature handed to 323C003.
    tt_323001_c: float

    # ---- differentials [bar] --------------------------------------------------------------
    #: Live head across LV-322501.
    dp_lv_bar: float

    # ---- flags ----------------------------------------------------------------------------
    #: The bottoms are inside the mushy zone and the drain is restricted.
    solidification: bool
    #: Gas is passing through a trim sized for liquid, which erodes the seat.
    lv_erosion: bool

    # ---- the holdup ------------------------------------------------------------------------
    #: What the sump between LT-322501's taps gained this tick [kg/h] (B-77 (b)).
    dm_kgh: float = 0.0


#: LT-322501's sump over its span [kg]: the bottom head's cross-section over the transmitter's
#: 1.5 m at the bottoms' density.
SUMP_SPAN_KG = SUMP_AREA_M2 * LEVEL_SPAN_M * RHO_BOTTOM


# ======================================================================================
# The sump
# ======================================================================================

@dataclass
class StripperSump:
    """The 322E001 bottom head as one object: level, transit line, drain and thermal lag."""

    #: LT-322501 level [%]. Seeded at the design set point, so the boot is the PFD state.
    level_pct: float = LEVEL_SP_DES_PCT
    #: Dead-time FIFO for the bottoms run between the tube exit and the sump.
    line_state: dict = field(default_factory=dict)
    #: First-order lag state for the published TT-322004.
    lag_state: dict = field(default_factory=dict)

    def step(self, lic: BottomLevelLoop, bottoms_kgh: float, t_bot_c: float,
             t_steam_c: float, top_kmolh: dict, top_mw: float,
             syn_bara: float, bot_mass_pct: dict, dt: float) -> StripperSumpResult:
        """Advance the controller, the drain, the level and the sump temperature by one tick.

        Parameters
        ----------
        lic
            LIC-322501. Passed in rather than owned, because the engine holds every faceplate
            in one place and a station has to be able to write to this one.
        bottoms_kgh, t_bot_c, t_steam_c, top_kmolh, top_mw, bot_mass_pct
            This tick's `stripper.StripperResult`, in the pieces the sump needs; the bottoms'
            composition sets their vapour pressure at LV-322501 (B-46).
        syn_bara
            PT-329201 from the PREVIOUS tick — the declared loop tear.

        Order of operations
        -------------------
        The order below is the plant's own and is not interchangeable. In particular the
        controller acts on the level at the TOP of the tick and the faceplate PV is written
        from the level at the BOTTOM of it, and the drain that enters the mass balance is the
        drain AFTER both restrictions, because a throttled valve leaves its mass in the sump —
        which is what makes a cooling bottom show up as a RISING level.
        """
        # ----- LIC-322501 -------------------------------------------------------------------
        lv_opening = lic.step(self.level_pct, dt)

        # ----- LV-322501, before any restriction --------------------------------------------
        dp_lv_bar = max(syn_bara - LV_322501_P_DOWN_BARA, 0.0)
        # The bottoms reach the valve as liquid, so at most saturated at the loop's pressure: a
        # bubble pressure above it has boiled down to it in the stripper (B-46).
        letdown_raw = letdown_kgh(lv_opening, syn_bara,
                                  min(bottoms_pv_bara(bot_mass_pct, t_bot_c), syn_bara))

        # ----- L3-6, the mushy zone ---------------------------------------------------------
        # A cooling bottom throttles its own outlet. The mass that does not leave stays in the
        # level ODE below, so the level rises while the drain falls — which is the signature
        # the operator gets, minutes before anything stops moving.
        mushy = mushy_flow_factor(t_bot_c, T_CRYSTALLISATION_C)
        drain = letdown_raw * mushy

        # ----- D-20, the liquid seal --------------------------------------------------------
        # LV-322501 is a pressure letdown, not a gravity drain: its 137 bar differential does
        # not vanish when the sump empties. The valve keeps flowing and starts passing the
        # stripper's own gas. The liquid fraction therefore goes to zero WITH the level,
        # rather than a guard clipping the drain to the inflow, and what the trim passes past
        # that point is compressible flow on the valve's own liquid design duty.
        #
        # The gas is the stripper's top vapour at the sump temperature and the loop pressure.
        # At 140 bar a it is far from ideal — Z is 0.685 at the design state, so the true
        # density is 1.46 times the ideal-gas value — and the correction comes from an SRK
        # compressibility in the thermo layer rather than from a factor written in here.
        #
        # At any normal level the seal is exactly 1.0 and the gas is exactly 0.0, so the
        # design seed is untouched.
        seal = seal_fraction(self.level_pct)
        drain *= seal
        blowthrough = 0.0
        if seal < 1.0:
            rho_gas = (gas_density_ideal(syn_bara, t_bot_c, top_mw or TOP_GAS_MW_FALLBACK)
                       / real_gas.z_factor(top_kmolh, t_bot_c, syn_bara))
            blowthrough = blowthrough_kgh(
                BOTTOMS_DES_KGH, RHO_BOTTOM, LV_322501_DP_ANCHOR_BAR,
                lv_opening / LV_322501_OPEN_DES_PCT, rho_gas, syn_bara, dp_lv_bar, seal)

        # ----- D-8, the bottoms transit ------------------------------------------------------
        # V1 carried a flat 60 s FIFO here, labelled empirical and motionless from turndown to
        # trip. The 60 s is kept as the DESIGN transit, the line inventory is back-solved from
        # it at the design flow, and the live dead time is rho.V/m_dot — so a stripper running
        # at half rate takes twice as long to deliver its bottoms to the sump, which is what
        # actually happens.
        td_s = line_residence_time_s(BOTTOMS_LINE_M3, RHO_BOTTOM, bottoms_kgh,
                                     t_max_s=FEED_TD_MAX_S)
        bottoms_in = dead_time(self.line_state, BOTTOMS_LINE_KEY, bottoms_kgh, td_s, dt)

        # ----- A-3, the LT-322501 mass balance ------------------------------------------------
        # The holdup integrates its REAL net flow. V1 originally multiplied every net inflow
        # by a fitted fill gate that deleted 94 % of it at low loop inventory, i.e. deleted
        # mass; at the design state that gate was exactly 1, so removing it leaves the design
        # seed untouched and makes the cold-start fill time an emergent property.
        #
        # The empty-sump guard that used to clip the drain to the inflow is gone too: the seal
        # ramp above takes the liquid to zero as the level reaches the nozzle, and what the
        # valve passes past that point is the blow-through gas, which leaves the loop as gas.
        level_0 = self.level_pct
        self.level_pct = clamp(
            self.level_pct + (bottoms_in - drain) / 3600.0 * dt / SUMP_SPAN_KG * 100.0,
            0.0, 100.0)
        lic.publish(self.level_pct)

        # ----- L3-7, the sump energy balance ---------------------------------------------------
        t_out = sump_outlet_temperature_c(t_bot_c, t_steam_c, drain)
        tt_322004 = first_order_lag(self.lag_state, TT_322004_KEY, t_out,
                                    T_STRIPPER_TAU_S, dt)

        # TT-323001, downstream of the letdown flash. The flash ripples the same bottoms
        # temperature at an anchored gain, so at design it returns 119.0 exactly.
        tt_323001 = T_DOWNSTREAM_DES_C + TT_323001_GAIN * (t_out - T_BOTTOM_DES_C)

        return StripperSumpResult(
            level_pct=self.level_pct,
            lv_opening_pct=lv_opening,
            drain_kgh=drain,
            letdown_raw_kgh=letdown_raw,
            blowthrough_kgh=blowthrough,
            bottoms_in_kgh=bottoms_in,
            bottoms_dead_time_s=td_s,
            mushy_factor=mushy,
            seal_fraction=seal,
            t_out_c=t_out,
            tt_322004_c=tt_322004,
            tt_323001_c=tt_323001,
            dp_lv_bar=dp_lv_bar,
            solidification=bool(mushy < 1.0),
            lv_erosion=bool(blowthrough > 0.0),
            dm_kgh=(self.level_pct - level_0) / 100.0 * SUMP_SPAN_KG * (3600.0 / dt),
        )


__all__ = [
    "SUMP_SPAN_KG",
    "BOTTOMS_LINE_KEY",
    "TT_322004_KEY",
    "LV_322501_DP_ANCHOR_BAR",
    "TOP_GAS_MW_FALLBACK",
    "BottomLevelLoop",
    "letdown_kgh", "bottoms_pv_bara", "LV_322501_PV_SCALE", "LV_322501_PV_DES_BARA",
    "sump_outlet_temperature_c",
    "StripperSumpResult",
    "StripperSump",
]
