"""322C001's vent line — PV-322201 to atmosphere, XV-322915's steam flood and TI-322015.

What this models
----------------
Line 150-GCB6-322254 carries 797 from PV-322201 to atmosphere through VE100. Just downstream of
PV-322201, XV-322915 (fail open, DN100/DN50, with FO-322457's DN15 bypass) admits LP steam from
line 100-STLS4-329722; further down the same line TI-322015 (SAHH, AH) reads the vent and
initiates I 22.1, beside HS-322915's OVERRIDE CLOSE. The purpose, in the datasheet reference's
words: on a breakthrough of hot ammonia and carbon dioxide the trip floods the line with steam,
so carbamate does not crystallise in it.

    322C001 top --797--+--> PV-322201 --+--> TI-322015 --> atmosphere (VE100)
                       ^                ^
           LP steam --> FO-329458       LP steam --> XV-322915, FO-322457 (its bypass)

Decided by the process engineer on 2026-10-01 (handoff B-55, option b). V1 adds the flood's
500 kW to 322C001's liquor, with no steam, and trips on the liquor's temperature; flooded, the
liquor held 56.24 C, above the trip's 55 C reset. The rewrite puts the flood in the vent line
as the steam that carries it, and trip 22.1 reads TI-322015 here (`trip_22_1`). The steam is the
valve's rated 1000 kg/h at 9.0 bar a and 175 C, Uhde's loop summary X 322915 (decided 2026-10-01,
handoff B-60, the Typo Rule); B-55 had carried V1's 500 kW as 854 kg/h at the LP header.

I 22.1 as the DCS executes it (decided 2026-10-01, handoff B-56): AC4's PC22.5.1 energises
XVY-322915 on NOT(TT-322015 > H2) OR HS-322915, and the valve, fail open, opens when its solenoid
drops out (`xv_322915_open`). There is no latch and no reset: the valve follows TT-322015's
high-high limit, and HS-322915, a control-room keyswitch, holds it shut whatever the limit says.
V1 latches the valve open and lets an operator's close stand for one tick only.

Equations
---------
The gas leaves the beds' top where the upper bed's counter-current exchange leaves it, the bed
taken as a perfect heat exchanger (its transfer units are many) between the 954 entering at its
own temperature and the gas from the lower bed at the liquor's (the temperature 322C001's heat
balance brings it to), the heat of absorption going to the wash:

    T_top = T_954                                      C_gas <= C_954
          = T_liq - (C_954 / C_gas) (T_liq - T_954)    C_gas >  C_954
    C_954 = m_954 cp_l / 3600,   C_gas = m_gas,mid cp_g / 3600            [packed_beds]

While the polish carries more heat capacity than the gas, the gas leaves at 954's temperature:
PFD 797's 46 C at design, and the temperature V1 saturates the vent's water at. A lost polish, or
a breakthrough whose gas outweighs it, carries the lower bed's temperature up the line.

The flood: XV-322915's rated normal flow, 1000 kg/h of saturated steam at 9.0 bar a and
175 C (the loop summary), off 329D009's 9-bar header (line 100-STLS4-329722). The valve is on/off;
what it passes follows the header's live pressure (handoff B-73, decided 2026-10-02, the Typo
Rule). The loop summary has the valve at 7.8 bar a out, so a restriction downstream holds it there
and the line as a whole lets 9 bar a down to the atmospheric vent, a ratio far past the choke: its
flow is the choked IEC gas law, in proportion to the header's pressure,

    m_s = 1000 . Phi(P_9, P_atm) / Phi(9.0, P_atm),   Phi on the IEC globe xT, T1 = T_sat(P_9)

anchored on the rated case at the header's 9.0 bar a design. The steam enters the line at its
rated 175 C.

The trace steam (decided by the process engineer 2026-10-07: "Model it ... Do not ignore known
mass inflows"): two DN15 restriction orifices put LP steam into the line continuously, FO-329458
between the column's top nozzle and PV-322201 and FO-322457 across XV-322915, 30 kg/h each at
9.0 bar a and 175 C (Uhde's loop summaries). Choked like the flood, they follow the same header:

    m_trace = 60 . Phi(P_9, P_atm) / Phi(9.0, P_atm)

PV-322201's law is a stroke gain on the column's gas, so the orifice upstream of it takes nothing
from the column's vent: the line is adiabatic and the valve isenthalpic, so where the steam joins
does not move TI-322015's reading, which is the mix of everything that joined. FO-329459, the third
orifice of the set, purges SV32253's discharge and does not reach the vent line
(`sv_purge_steam_kgh`).

TI-322015: the line's adiabatic mix at atmospheric pressure, every species an ideal gas on the
H0 datum, the steam entering at its rated temperature:

    sum_i n_i h_i(T) + n_s h_w(T) = sum_i n_i h_i(T_top) + n_s h_w(T_sat)

Below the mix's dew point the water condenses: its vapour held at psat(T) / (P - psat(T)) of the
dry gas, the rest liquid, priced at its latent heat.

Sources: P&ID UD-VT-322-FB-0003 (sheet 102, ``References/Merged_Searchable_PIDs.pdf`` page 3,
read from the page image); ``References/322P002 322E006 322C001 Datasheets.md``; Uhde's
application software AC4, UD-MR-G00-FF-0004 (PC22.5.1, PDF page 43, scanned, read from the page
image); the loop summaries UD-MR-322-EC-0001 (T 322015, X 322915, H 322915); V1
``backend/main.py`` 10135-10148 (trip 22.1) and ``A328_QFLOOD_KW``.
"""

from __future__ import annotations

from dataclasses import dataclass

from ureasim.control.interlocks import HystereticInterlock
from ureasim.control.valve import XT_GLOBE, compressible_shape
from ureasim.core.stream import MW_COMP
from ureasim.core.units_of_measure import ABSOLUTE_ZERO_C, ATM_BARA
from ureasim.data.unit_322c001 import (
    BED_CP_GAS,
    BED_CP_LIQ,
    C001_FLOOD_STEAM_KGH,
    C001_FLOOD_STEAM_P_BARA,
    C001_FLOOD_STEAM_T_C,
    C001_SV_PURGE_STEAM_KGH,
    C001_TRACE_STEAM_KGH,
    TRIP_22_1_CLEAR_C,
    TRIP_22_1_HIGH_C,
)
from ureasim.data.unit_329 import STEAM_GAMMA, STEAM_MW
from ureasim.thermo import enthalpy as h0
from ureasim.thermo import iapws
from ureasim.units.absorption.packed_beds import BedsResult

#: The flood's steam: its temperature at XV-322915 [deg C] and the valve's rated flow [kg/h]
#: (loop summary X 322915; handoff B-60).
FLOOD_STEAM_T_C = C001_FLOOD_STEAM_T_C
FLOOD_STEAM_KGH = C001_FLOOD_STEAM_KGH

#: The line's pressure [bar a]: it discharges to atmosphere, the standard one (handoff B-6).
VENT_LINE_P_BARA = ATM_BARA

#: The 9-bar header's pressure the flood is rated on [bar a] (loop summary X 322915; B-73).
FLOOD_STEAM_P_BARA = C001_FLOOD_STEAM_P_BARA


def _flood_shape(p_9_bara: float) -> float:
    return compressible_shape(1.0, p_9_bara, VENT_LINE_P_BARA,
                              iapws.tsat_c(max(p_9_bara, 1e-6)) + ABSOLUTE_ZERO_C, STEAM_MW,
                              STEAM_GAMMA, 1.0, "linear", XT_GLOBE)


def flood_steam_kgh(p_9_bara: float) -> float:
    """What XV-322915 passes open off the 9-bar header [kg/h] (handoff B-73).

    Process utility
    ---------------
    The flood's steam follows 329D009's header: its rated 1000 kg/h at the header's 9.0 bar a,
    proportionally less as the header falls, nothing once it is at the vent's pressure — and
    every kilogram is drawn off that header. Equation in the module docstring.
    """
    return FLOOD_STEAM_KGH * (_flood_shape(p_9_bara) / _flood_shape(FLOOD_STEAM_P_BARA))


def trace_steam_kgh(p_9_bara: float) -> float:
    """What FO-329458 and FO-322457 put into the vent line off the 9-bar header [kg/h].

    Process utility
    ---------------
    The line's continuous steam: it keeps carbamate from laying down in the line between floods,
    and it is what TI-322015 reads on top of the column's vent. 60 kg/h at the header's 9.0 bar a,
    choked through the orifices, so in proportion to the header as the flood is.
    """
    return C001_TRACE_STEAM_KGH * (_flood_shape(p_9_bara) / _flood_shape(FLOOD_STEAM_P_BARA))


def sv_purge_steam_kgh(p_9_bara: float) -> float:
    """What FO-329459 puts into SV32253's discharge line off the 9-bar header [kg/h].

    Process utility
    ---------------
    Keeps the relief path to the safe location clear of carbamate. It leaves to atmosphere with
    the relief line and changes no reading; it is a draw on the 9-bar header.
    """
    return C001_SV_PURGE_STEAM_KGH * (_flood_shape(p_9_bara) / _flood_shape(FLOOD_STEAM_P_BARA))

#: The mix's bisection: iterations, below 1e-12 K on a 200 K bracket.
MIX_BISECTIONS = 60

#: A capacity flow that counts [kW/K], and the bracket margin [K] below the coldest inlet.
CAPACITY_FLOOR_KWK = 1e-12
BRACKET_MARGIN_K = 1.0


@dataclass(frozen=True)
class VentLineResult:
    """What the vent line publishes on one tick."""

    #: The beds' top: the gas leaving 322C001 for PV-322201 [deg C].
    t_top_c: float
    #: XV-322915's steam into the line [kg/h], zero while it is shut.
    m_steam_kgh: float
    #: FO-329458's and FO-322457's trace steam into the line [kg/h].
    m_trace_kgh: float
    #: TI-322015 [deg C], the line after the injection — trip 22.1's process value.
    t_ti_322015_c: float
    #: What the line carries to atmosphere [kg/h], and the water condensed in it [kg/h].
    m_out_kgh: float
    m_condensed_kgh: float


def column_top_c(beds: BedsResult, gas_kmolh: dict, m_cpl_kgh: float, t_cpl_c: float,
                 t_liq_c: float) -> float:
    """The gas leaving 322C001's top [deg C].

    Process utility
    ---------------
    What PV-322201 vents and TI-322015 sees before any steam: 954's temperature while the
    polish holds the gas, the lower bed's when the polish is lost or a breakthrough outweighs it
    — the reading that tells an operator the top bed no longer holds the gas.

    Equation in the module docstring. The gas into the upper bed is the purge less the lower
    bed's uptake: the vent's non-water species, plus the upper bed's uptake, plus the purge's
    water, which the lower bed does not move (`packed_beds.solve`).
    """
    n_mid = {k: v for k, v in beds.vent_kmolh.items() if k != "H2O"}
    n_mid["NH3"] = n_mid.get("NH3", 0.0) + beds.abs_up["NH3"]
    n_mid["CO2"] = n_mid.get("CO2", 0.0) + beds.abs_up["CO2"]
    n_mid["H2O"] = max(gas_kmolh.get("H2O", 0.0), 0.0)
    c_gas = sum(v * MW_COMP.get(k, 0.0) for k, v in n_mid.items()) * BED_CP_GAS / 3600.0
    c_cpl = max(m_cpl_kgh, 0.0) * BED_CP_LIQ / 3600.0
    if c_gas <= CAPACITY_FLOOR_KWK and c_cpl <= CAPACITY_FLOOR_KWK:
        return t_liq_c
    if c_gas <= c_cpl:
        return t_cpl_c
    return t_liq_c - c_cpl / c_gas * (t_liq_c - t_cpl_c)


def _h_kj_h(n_kmolh: dict, t_c: float) -> float:
    """The ideal-gas enthalpy of a vapour [kJ/h], on the H0 datum."""
    t_k = t_c + ABSOLUTE_ZERO_C
    return sum(n * h0.h_species(k, h0.reference_phase(k, "vapour"), t_k)
               for k, n in n_kmolh.items() if n > 0.0)


def vent_line(vent_kgh: float, y_vent: dict | None, t_top_c: float,
              xv_322915_open: bool, p_9_bara: float = FLOOD_STEAM_P_BARA) -> VentLineResult:
    """The vent line on one tick: 797 at the beds' top, XV-322915's steam, TI-322015.

    Process utility
    ---------------
    Trip 22.1's process value. Shut, TI-322015 reads the vent as it leaves the column with the
    trace steam on it. Open, the steam it admits carries the line well above the limit's reset —
    so once 22.1 has fired it holds the steam on until HS-322915 shuts the valve
    (`xv_322915_open`).

    Arguments
    ---------
    vent_kgh, y_vent
        797 through PV-322201 [kg/h] and its mass fractions (None when the column vents nothing).
    t_top_c
        The beds' top [deg C], `column_top_c`.
    xv_322915_open
        XV-322915, as I 22.1 left it at the end of the tick before (`xv_322915_open`).
    p_9_bara
        329D009's header the flood draws from (B-73), at the top of the tick; its default the
        header's design.
    """
    m_s = flood_steam_kgh(p_9_bara) if xv_322915_open else 0.0
    m_t = trace_steam_kgh(p_9_bara)
    gas = ({k: vent_kgh * y_vent[k] / MW_COMP[k] for k in MW_COMP if y_vent.get(k, 0.0) > 0.0}
           if (y_vent and vent_kgh > 0.0) else {})
    n_s = (m_s + m_t) / MW_COMP["H2O"]
    if n_s <= 0.0:
        # No steam: the line carries the vent as it left the column. Saturated with water at
        # 3.9 bar a at most, it is drier still at atmospheric pressure, and condenses nothing.
        return VentLineResult(t_top_c=t_top_c, m_steam_kgh=0.0, m_trace_kgh=0.0,
                              t_ti_322015_c=t_top_c, m_out_kgh=vent_kgh if gas else 0.0,
                              m_condensed_kgh=0.0)
    h_in = _h_kj_h(gas, t_top_c) + _h_kj_h({"H2O": n_s}, FLOOD_STEAM_T_C)
    mix = dict(gas)
    mix["H2O"] = mix.get("H2O", 0.0) + n_s
    temps = ([t_top_c] if gas else []) + ([FLOOD_STEAM_T_C] if n_s > 0.0 else [])
    lo, hi = min(temps) - BRACKET_MARGIN_K, max(temps)

    # ----- the dry mix ------------------------------------------------------------------
    a, b = lo, hi
    for _ in range(MIX_BISECTIONS):
        mid = 0.5 * (a + b)
        if _h_kj_h(mix, mid) < h_in:
            a = mid
        else:
            b = mid
    t_mix = 0.5 * (a + b)
    n_dry = sum(v for k, v in mix.items() if k != "H2O")
    n_w = mix.get("H2O", 0.0)
    m_cond = 0.0

    # ----- below the mix's dew point the water condenses, at its latent heat ------------------
    def water_vapour(t_c: float) -> float:
        p_sat = iapws.psat_bara(max(t_c, 0.01))
        if p_sat >= VENT_LINE_P_BARA:
            return n_w
        return min(n_w, p_sat / (VENT_LINE_P_BARA - p_sat) * n_dry)

    if water_vapour(t_mix) < n_w:
        def h_wet(t_c: float) -> float:
            n_wv = water_vapour(t_c)
            dry = {k: v for k, v in mix.items() if k != "H2O"}
            dry["H2O"] = n_wv
            t_k = t_c + ABSOLUTE_ZERO_C
            return (_h_kj_h(dry, t_c)
                    + (n_w - n_wv) * h0.h_species("H2O", "liquid", t_k))

        a, b = t_mix, hi
        for _ in range(MIX_BISECTIONS):
            mid = 0.5 * (a + b)
            if h_wet(mid) < h_in:
                a = mid
            else:
                b = mid
        t_mix = 0.5 * (a + b)
        m_cond = (n_w - water_vapour(t_mix)) * MW_COMP["H2O"]

    return VentLineResult(t_top_c=t_top_c, m_steam_kgh=m_s, m_trace_kgh=m_t,
                          t_ti_322015_c=t_mix,
                          m_out_kgh=(vent_kgh if gas else 0.0) + m_s + m_t - m_cond,
                          m_condensed_kgh=m_cond)


def trip_22_1() -> HystereticInterlock:
    """Trip 22.1's initiator: TT-322015's high-high limit, set above 57 C and cleared below
    55 C, its process value the vent line's temperature (decided 2026-10-01, handoff B-55).

    Process utility
    ---------------
    The H2 limit of TT-322015's analogue input that AC4's PC22.5.1 reads. The DCS evaluates it
    with the input's own limit hysteresis and holds nothing: it clears itself when the line has
    cooled. The limit and its hysteresis are database values the archive does not hold; the
    thresholds are V1's (``main.py`` 10142-10146), an open data gap.
    """
    return HystereticInterlock("22_1", "322C001 vent over-temperature steam flood",
                               trip_above=TRIP_22_1_HIGH_C, clear_below=TRIP_22_1_CLEAR_C)


def xv_322915_open(h2_limit: bool, hs_322915: bool) -> bool:
    """XV-322915 as I 22.1 drives it: open while TT-322015 is over its limit and HS-322915 is
    not set.

    Process utility
    ---------------
    The steam flood and the operator's one way to end it. AC4's PC22.5.1 (decided 2026-10-01,
    handoff B-56) energises the solenoid while TT-322015 is under its high-high limit OR the
    control-room keyswitch HS-322915 is set, and XV-322915 fails open, so

        XVY-322915 = NOT(TT-322015 > H2) OR HS-322915,     XV-322915 open = NOT XVY-322915

    TRIP_22_1_FLAG1 is the same signal. There is no latch and no reset: with the injection
    upstream of TI-322015 the flood holds its own reading over the limit, and the keyswitch,
    maintained, holds the valve shut while the line cools below the limit's reset; released,
    the valve stays shut. The DCS has no command that opens the valve.

    Arguments
    ---------
    h2_limit
        TT-322015's high-high limit flag (`trip_22_1`'s ``latched``).
    hs_322915
        HS-322915, the OVERRIDE CLOSE keyswitch, as the operator left it.
    """
    xvy_energised = (not h2_limit) or hs_322915
    return not xvy_energised


__all__ = [
    "FLOOD_STEAM_T_C", "FLOOD_STEAM_KGH", "FLOOD_STEAM_P_BARA", "flood_steam_kgh",
    "trace_steam_kgh", "sv_purge_steam_kgh",
    "VENT_LINE_P_BARA", "MIX_BISECTIONS",
    "CAPACITY_FLOOR_KWK", "BRACKET_MARGIN_K", "VentLineResult", "column_top_c", "vent_line",
    "trip_22_1", "xv_322915_open",
]
