"""HV-322604 — the inert-purge letdown from 322E003 to the 322C001 LP absorber.

What this models
----------------
The one valve through which the synthesis loop purges its inerts. The 322E003 vent — about
89 mol % nitrogen, oxygen, methane and hydrogen, carrying the ammonia and carbon dioxide the
scrubber could not recover — is let down from the loop pressure to the LP absorber at 4 bar a.
Three things happen across the seat, and this module computes all three:

  1. **The flow is choked.** At a pressure ratio of 0.028 the gas reaches sonic velocity in the
     trim, so the flow depends on the opening and on the UPSTREAM state only. The downstream
     pressure could fall to zero and not one more kilogram would pass.
  2. **The seat has a ceiling.** When 322E003 loses its cooling, it hands back to the vapour
     everything it failed to condense — thirteen times the design purge at zero capacity. The
     valve does not vent that. It passes the purge the shell would have produced with full
     cooling, and the rest is retained in the loop, where it builds pressure. The retained
     vapour IS the event; a valve that vented it would make the excursion vanish from a
     boundary mass balance.
  3. **The gas cools isenthalpically**, and below its dew point it condenses. SRK real-gas
     enthalpy on the live composition, 94.8 C at the 322C001 inlet on the design vent. When
     322E003 loses its cooling the purge turns ammonia-rich and its dew point rises to 66-82 C:
     the letdown then condenses an ammonium-carbamate liquor, whose heat holds the outlet a few
     kelvin under the dew point (`thermo.condensing_letdown`).

Source
------
V1 ``backend/main.py`` ``hv_322604``, whose law is line for line that of
``backend/core/valve.py`` ``Valve322604.solve`` — the copy `step_sim` actually calls — plus two
`step_sim` statements that wire it: the seat ceiling (``main.py`` 8173) and the published
vent-capacity diagnostic (``main.py`` 8042). Reports D-2 (the choked law, and the hard zero at
zero travel) and D-4 (the isenthalpic outlet). `References/HV-322604 description.md` for the
process account.

The trim is the vendor's. The Uhde sizing, ``UD-MR-G00-DZ-0042-010`` (CONVAL, 21.06.2005), and
the instrument specification in ``UD-MR-G00-DZ-0042-001``, give an angle valve, DN 25
(catalogued DN-24), seat 8 mm, Kvs 2.1, an EQUAL-PERCENTAGE characteristic with
Kv0/Kvs = 2.0 % (rangeability 50), flow to open, fail open. `control.valve.EQUAL_PCT_RANGE` is
that 50, and the vendor's own Kv-versus-stroke table reproduces ``Kvs . 50^(h - 1)`` to four
figures.

Equations
---------
    f_valve = [IEC 60534 compressible, anchored at theta_des = 72 %, P1 = 140.7 bar a,
               P2 = 4.0 bar a, T1 = 114 C, M_des = 26.368; equal-percentage trim with a hard
               zero at zero travel]                                    (control.valve)
    pass    = min(1, w_cap / w_offered)
    n_i     = n_i,offered . f_valve . pass                  (the seat does not fractionate)
    H_SRK(T1, P1, y) = H_SRK(T2, P2, y_v) V/n + H_liquor(T2)/n  (thermo.condensing_letdown;
                                                               no liquor above the dew point)

Two things a reader should know
-------------------------------
**The upstream pressure is the live loop pressure.** `ScrubberResult.p_offgas_bara` is the
design pin, exactly as V1's ``scrub_322e003`` returns it, and V1's `step_sim` overwrites it with
the prior-step loop pressure before this valve is called (``main.py`` 8106). The caller
therefore passes the loop pressure, not the scrubber's published one.

**Where it departs from V1, decided by the process engineer on 2026-10-01.**

  * **The outlet below the dew point (handoff B-19).** V1's single-phase solve returns its
    bracket's floor, T_in - 150 K, when the enthalpy has no root inside it: -36 C on a cooling
    loss. The port flashes the purge onto the liquor it condenses, and the liquor rides the line
    to 322C001 (`liquor_kmolh`). Above the dew point, the design point included, it is V1's
    answer to the bit. L3-7's deposition flag now also fires while a carbamate liquor condenses
    in the line: at 66-78 C the outlet no longer reaches V1's 20 C, and the liquor is the
    deposit the flag warns of.
  * **The outlet pressure is an argument** (decision 29's class, handoff A-17): the receiver's,
    322C001's live pressure once the schedule hands it over; V1's fixed 4.0 bar a by default.
    The seat is choked down to 13.2 bar a upstream, so it moves the outlet temperature only.

**The anchor opening, decided 2026-10-10 (handoff B-18).** V1 anchors the characteristic at 50 %,
with no source. Sized on the vendor's own trim at the licensor's normal purge, the valve needs 72 %
stroke, and the port anchors it there (`data.unit_322e003.HIC604_DES_PCT`): the plant's 78.2 %
passes 1.27 times the design purge, where V1's anchor passes 3.01 times. 322E003's two vent-opening
terms read the same anchor. The law is V1's; only its anchor moves.
"""

from __future__ import annotations

from dataclasses import dataclass

from ureasim.control.valve import valve_gas_anchored
from ureasim.core.stream import MW_COMP
from ureasim.core.units_of_measure import ABSOLUTE_ZERO_C
from ureasim.data.unit_322e003 import (
    CARBAMATE_DEPOSITION_T_C,
    HIC604_DES_PCT,
    HV604_GAMMA,
    HV604_MW_DES,
    HV604_P_OUT_BARA,
    OFFGAS_DES_KMOLH,
    OFFGAS_P_BARA,
    OFFGAS_T_DES_C,
)
from ureasim.thermo import condensing_letdown

#: Total molar flow below which the purge is treated as empty and its molar mass falls back
#: to the design value [kmol/h]. V1's own guard in ``hv_322604``.
EMPTY_PURGE_KMOLH = 1e-12

#: Decimal places V1 rounds the outlet temperature to AT SOURCE. The rounded value is what
#: V1's step_sim consumes downstream — the TT-322011 lag, the carbamate-deposition flag and
#: the 322C001 absorber's gas inlet — so the rounding is part of the relation, not of the
#: display. Source: V1 `main.py` `hv_322604` and `core/valve.py`, ``round(T_out, 1)``.
T_OUT_DECIMALS = 1


@dataclass(frozen=True)
class PurgeValveResult:
    """What HV-322604 publishes on one call — V1's ``hv604`` diagnostics dictionary, typed."""

    #: Purge to 322C001, per species [kmol/h] — PFD stream 204 downstream of the seat.
    comp_kmolh: dict
    #: The purge as it reaches 322C001: the gas, and the ammonium-carbamate liquor condensed in
    #: the line [kmol/h] (NH3, CO2, H2O; zero above the dew point). They add up to ``comp_kmolh``.
    vapour_kmolh: dict
    liquor_kmolh: dict
    #: True while the line condenses a liquor.
    condensing: bool
    #: Outlet temperature [deg C], rounded to 0.1 C at source, as V1 publishes and consumes it.
    t_out_c: float
    #: Outlet and inlet pressures [bar a]. The inlet is the live loop pressure it was given.
    p_out_bara: float
    p_in_bara: float
    #: HIC-322604 opening the call was made at [%].
    open_pct: float
    #: Purge mass flow [kg/h].
    mass_kgh: float
    #: The anchored IEC 60534 factor [-], 1.0 at the design opening and design state.
    valve_frac: float
    #: Pressure difference across the seat [bar], floored at zero.
    dp_bar: float
    #: Fraction of the offered gas the seat ceiling lets through [-], 1.0 without a ceiling.
    pass_frac: float
    #: L3-7: carbamate deposits in the line — the outlet below 20 C, or a liquor condensing.
    carbamate_deposition: bool
    #: Solid ammonium carbamate the line lays down [kmol/h of carbamate] (B-79 (b)); carried on to
    #: 322C001 in ``liquor_kmolh`` as its NH3 and CO2, where the beds' liquor takes it up.
    solid_kmolh: float = 0.0


def purge_mw(comp_kmolh: dict) -> float:
    """Molar mass of the purge gas [kg/kmol], falling back to the design value when empty.

    Process utility
    ---------------
    The live molar mass is passed to the valve law separately from the design one, so a
    heavier purge — one carrying more of the ammonia and carbon dioxide the scrubber failed to
    recover — puts more kilograms through the same trim, w ~ sqrt(M). With nothing offered
    there is no composition to average, and the design value keeps the law finite.
    """
    n = sum(comp_kmolh.get(k, 0.0) for k in MW_COMP)
    if n > EMPTY_PURGE_KMOLH:
        return sum(comp_kmolh.get(k, 0.0) * MW_COMP[k] for k in MW_COMP) / n
    return HV604_MW_DES


def valve_factor(hic_pct: float, p_up_bara: float, t_in_c: float, mw: float,
                 p_out_bara: float = HV604_P_OUT_BARA) -> float:
    """HV-322604's flow relative to its design duty [-], on the anchored IEC 60534 law.

    Process utility
    ---------------
    The whole hydraulic behaviour of the seat in one number. It is 1.0 at the design opening
    and design state, a hard 0.0 at zero travel — so a HIC-322604 set to 0 really isolates the
    loop, where V1's earlier incompressible form still passed 14 % of the design purge — and,
    because the seat is choked, it follows the upstream pressure, temperature and molar mass
    and not the absorber pressure.

    Equation
    --------
        f = phi(h, P1, P2, T1, M) / phi(h_des, P1_des, P2_des, T1_des, M_des)
        phi : IEC 60534 compressible, equal-percentage, choked at x >= F_gamma . xT
    """
    return valve_gas_anchored(
        1.0, hic_pct / 100.0, p_up_bara, p_out_bara, t_in_c + ABSOLUTE_ZERO_C,
        HIC604_DES_PCT / 100.0, OFFGAS_P_BARA, HV604_P_OUT_BARA,
        OFFGAS_T_DES_C + ABSOLUTE_ZERO_C, mw, gamma=HV604_GAMMA,
        characteristic="equal_pct", mw_des=HV604_MW_DES)


def seat_ceiling_kgh(offgas_kmolh: dict, uncond_kgh: float) -> float:
    """The most purge the seat will pass on this tick [kg/h of OFFERED gas].

    Process utility
    ---------------
    A DN-24 / Kvs 2.1 trim is sized for the inert purge, not for the loop's vapour. When
    322E003 under-condenses, what it hands back to the vapour is retained upstream and shows
    up in the loop pressure. The ceiling is the offered total less that uncondensed part —
    the purge mass the shell would have produced with full cooling. At design nothing is
    uncondensed, the ceiling equals the offer, and the pass fraction is exactly 1.0.

    Equation
    --------
        w_cap = max( sum_i n_i . M_i  -  w_uncond , 0 )

    Source: V1 `main.py` step_sim, ``_valve_unit.vent_cap_kgh`` (line 8173).
    """
    return max(sum(offgas_kmolh[k] * MW_COMP[k] for k in MW_COMP) - uncond_kgh, 0.0)


def purge_capacity_fraction(hic_pct: float, p_loop_bara: float) -> float:
    """HV-322604's vent capacity against the design purge [-] — V1's ``vent_frac``.

    Process utility
    ---------------
    The number an engineer reads to see whether the purge valve can keep up: below 1 it
    passes less than the design inert purge, and inerts accumulate in the loop. It is the
    same anchored law as `valve_factor`, evaluated at the design temperature and molar mass
    and the live loop pressure, so the published capacity and the actual purge can never
    disagree about the seat. V1 publishes it and nothing in V1 reads it back.

    Source: V1 `main.py` step_sim, ``vent_frac`` (line 8042), report D-2.
    """
    return valve_factor(hic_pct, p_loop_bara, OFFGAS_T_DES_C, HV604_MW_DES)


def purge_valve_322604(offgas_kmolh: dict, t_in_c: float, hic_pct: float,
                       p_up_bara: float, vent_cap_kgh: float = None,
                       p_out_bara: float = HV604_P_OUT_BARA) -> PurgeValveResult:
    """HV-322604 on one tick: the choked flow, the seat ceiling and the isenthalpic outlet.

    Process utility
    ---------------
    The loop's only inert exit. The flow it passes decides how fast the loop can shed the
    inerts the CO2 feed brings in, and therefore the loop pressure and the condensing
    duty of 322E002; its composition and outlet temperature are the 322C001 absorber's gas
    feed. At the design opening and state it reproduces PFD stream 204 exactly.

    Arguments
    ---------
    offgas_kmolh
        What 322E003 offers at its top [kmol/h], `ScrubberResult.offgas_kmolh`.
    t_in_c
        The vent-top temperature [deg C], TT-322011, `ScrubberResult.t_offgas_c`.
    hic_pct
        HIC-322604 [%].
    p_up_bara
        The LIVE loop pressure [bar a] — see the module docstring.
    vent_cap_kgh
        The seat ceiling from `seat_ceiling_kgh`, or None for no ceiling.
    p_out_bara
        What the seat discharges against [bar a]: 322C001's live pressure (handoff A-17), V1's
        fixed 4.0 bar a by default.

    Equations
    ---------
        n_i  = n_i,offered . f_valve . min(1, w_cap / w_offered)
        T2   : isenthalpic letdown from (T1, P1) to P2, flashing onto the liquor it condenses

    The composition is held: the seat passes the live mixture, it does not fractionate.
    """
    dp_bar = max(p_up_bara - p_out_bara, 0.0)
    valve = valve_factor(hic_pct, p_up_bara, t_in_c, purge_mw(offgas_kmolh), p_out_bara)

    # The ceiling is on the OFFERED mass, before the valve factor.
    off_kgh = sum(offgas_kmolh.get(k, 0.0) * MW_COMP[k] for k in MW_COMP)
    pass_frac = (1.0 if (vent_cap_kgh is None or off_kgh <= 0.0)
                 else min(1.0, max(vent_cap_kgh, 0.0) / off_kgh))
    comp = {k: offgas_kmolh.get(k, 0.0) * valve * pass_frac for k in MW_COMP}

    # Report D-4: a letdown valve is isenthalpic, on the live composition. It replaced a
    # 0.55 C/bar coefficient for an NH3/CO2-rich gas applied to a gas that is 69 mol % N2,
    # which gave 38.8 C at design against the real 94.8 C. Below the dew point the purge
    # condenses a carbamate liquor (handoff B-19, decided 2026-10-01).
    flash = condensing_letdown.letdown(comp, t_in_c, p_up_bara, p_out_bara)
    t_out_c = round(flash.t_out_c, T_OUT_DECIMALS)
    mass_kgh = sum(comp.get(k, 0.0) * MW_COMP[k] for k in MW_COMP)
    liquor = {k: flash.liquor_kmolh.get(k, 0.0) for k in MW_COMP}
    # The solid a dry purge lays down (handoff B-79 (b), decided 2026-10-14) leaves the gas; it is
    # carried on to 322C001 as the NH3 and CO2 it holds, where the beds' liquor dissolves it, so
    # the purge's mass reaches the absorber whole.
    if flash.solid_kmolh > 0.0:
        liquor["NH3"] += 2.0 * flash.solid_kmolh
        liquor["CO2"] += flash.solid_kmolh
    vapour = {k: comp[k] - liquor[k] for k in MW_COMP}

    return PurgeValveResult(
        comp_kmolh=comp,
        vapour_kmolh=vapour,
        liquor_kmolh=liquor,
        condensing=flash.condensing,
        t_out_c=t_out_c,
        p_out_bara=p_out_bara,
        p_in_bara=p_up_bara,
        open_pct=hic_pct,
        mass_kgh=mass_kgh,
        valve_frac=valve,
        dp_bar=dp_bar,
        pass_frac=pass_frac,
        # L3-7: the steam tracing holds a 60 C baseline, so this fires only when
        # Joule-Thomson cooling overwhelms it, or when the line condenses a carbamate liquor
        # (B-19), or while it lays solid carbamate (B-79 (b)). A fouling warning; the gas still
        # flows.
        carbamate_deposition=bool(t_out_c < CARBAMATE_DEPOSITION_T_C or flash.condensing
                                  or flash.solid_kmolh > 0.0),
        solid_kmolh=flash.solid_kmolh,
    )


#: HV-322604 at the design opening, the design vent and the design state — PFD stream 204 as
#: it enters 322C001.
DESIGN = purge_valve_322604(OFFGAS_DES_KMOLH, OFFGAS_T_DES_C, HIC604_DES_PCT, OFFGAS_P_BARA)


__all__ = [
    "EMPTY_PURGE_KMOLH",
    "T_OUT_DECIMALS",
    "PurgeValveResult",
    "purge_mw",
    "valve_factor",
    "seat_ceiling_kgh",
    "purge_capacity_fraction",
    "purge_valve_322604",
    "DESIGN",
]
