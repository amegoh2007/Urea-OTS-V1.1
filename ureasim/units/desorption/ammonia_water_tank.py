"""328D003 — the ammonia water tank: three communicating bays and the five draws on them.

What this models
----------------
328D003 is an atmospheric tank of 490 m3 of liquid in three bays whose baffles have openings,
so the three levels stand together:

  * compartment I (18 m3) takes the vacuum train's condensates 719, 720, 721 and 759, and
    322P002 draws 744 from it to the LP absorber — while one of 322P002 A/B runs;
  * compartment II (43 m3) takes 323C005's bottoms 343 through 328V001 and the normally closed
    recycle 741, which 328C004 draws through FV-328406 (FIC-328406 is stepped with 328C004,
    handoff B-50); 328P003 draws 735 to 328E007 and the desorbers through FIC-328402, 734
    (FIC-323401), 791 to 323E011 (FIC-323402) and the spare 793 (FIC-328405);
  * compartment III (429 m3) has no stream of its own: it is the surge volume the other two
    level into.

    719 + 720 + 721 + 759 --> I --744--> 322P002
                              |
                             III
                              |
                343 + 741 --> II --735 / 734 / 791 / 793--> 328P003

The two active bays
-------------------
Each advances on its own streams first, semi-implicit in the inflows' heat-capacity rates:

    M_I cp dT_I/dt  = sum m_k cp (T_k - T_I) + (m_719 + m_720 + m_721 + m_759) . lambda_I
    M_II cp dT_II/dt = m_343 cp (T_343 - T_II) + m_741 cp (40 - T_II)
    dM_I/dt  = m_719 + m_720 + m_721 + m_759 - 1 - m_744
    dM_II/dt = m_343 + m_741 + 2 - (m_735 + m_734 + m_791 + m_793)

cp is ``aqueous_cp`` on 4.0 at each bay's design temperature; lambda_I = -1.593 kJ/kg is
back-solved so compartment I holds PFD 744's 44 C on condensates that arrive 0.40 K warmer (V1
names it the carbamate-formation exotherm; its sign is a sink); the -1 and +2 kg/h are the PFD's
rounding, booked so each bay closes at design. FIC-328402 sets 735; 744 is what 322P002
delivers (below).

The openings (V1's parameter-free reduced model)
------------------------------------------------
With no opening areas or elevations, the three bays are brought to the one level their total
fills — the communicating-vessel limit — after the streams. Each transfer crosses compartment
III at the donor's temperature: donors are mixed into III first, then receivers are supplied
from that mix, so neither mass nor sensible energy is created. 429/490 of any net disturbance
therefore settles in compartment III.

Where this unit departs from V1 — decided 2026-09-27 (decision 11, extended to this tank)
----------------------------------------------------------------------------------------
V1 floors each active bay's holdup at 1 kg and lets 322P002 and 328P003 draw their full flow
whatever the tank holds, so an empty tank delivers its pumps' flow indefinitely, the floor
making up the difference; and it has no overflow, so the bays level above their capacity
without limit. The process engineer's rule for tank boundaries, decided for 323D002 and
323D001 (decision 11) and extended to this tank, is applied:

  * **A pump never drains the tank's heel.** Because the bays level together, the heel is one
    level: the level at which compartment I, the smallest, holds V1's 1 kg floor. Each bay's
    heel is its share of it, h_I = 1 kg and h_II = 1 . 43/18 = 2.39 kg, and each bay's draws
    are capped at the liquid above its heel plus what arrives on the tick:

        m_744 <= (M_I - h_I) / dt + in_I
        m_735 + m_734 + m_791 + m_793 <= (M_II - h_II) / dt + in_II      (pro rata)

    A per-bay 1 kg heel would not be enough: the levelling carries the bays back below 1 kg into
    compartment III, and V1's floor would restore them every tick. With the heel a level, the
    total never falls below the heel level times the tank, so the levelled bays never fall
    below their floors. 328P003's four legs lose their share of the suction alike. Each loss of
    suction is flagged, and each flow transmitter reads the flow delivered on the next tick.
  * **A full tank overflows.** Above the 490 m3 of approved liquid capacity, the excess at the
    common level leaves through the overflow at each bay's temperature, published as a stream.
    Its destination is outside this model: nozzle N12, DN200, in compartment III at 4552 mm
    above the bottom plate (EL +5352; the site's nozzle record, UDS-BM-328-QC-0001 page 50),
    through seal pot Z2801Z and line 200-AW3-328079 to drain system 30 and pit 329F001 (P&ID
    116), so it leaves the plant here. The 490 m3 is the shell to N12's centre within 0.3 %.

Both are inert while the tank stands between its heel and full.

Each inlet at its producer's live temperature — decided 2026-10-16 (handoff B-31). V1 charges 343
at 56 C, 328V001's, which it holds at compartment II's design whatever 323C005's liquor does, and
the condensates 719, 720, 721 and 759 at 45, 40, 41 and 55 C whatever unit 324 delivers. The port
charges each as its departure from its producer's design,

    T_k = T_k,des + (T_producer - T_producer,des)

343 on 323C005's liquor of this tick (V1's 55 C its design), each condensate on its condenser's
cold end of the tick before (the train steps after this tank; the PFD's cold ends their designs).
At the design seed every inlet is V1's to the bit; ``live_inlets=False`` is V1's, which the
plant-level harness keeps. 741 stays at 40 C: it leaves 328E001, the recycle cooler, which is not
modelled.

FIC-328402 meters 735, as the plant does — decided 2026-10-09 (handoff B-39, and B-87's option c).
Every plant source puts FT-328402 and FV-328402 on 328P003's discharge, line 100-AW3-328062: Uhde's
loop summary F 328402 (56 C, 31.4 m3/h on FV-328402's sheet), the DCS tuning table's "328062,AW",
and P&ID 104. V1 hangs the loop on 744 and draws 735 in proportion to compartment II's holdup,

    m_735 = 31 114 . M_II / M_II,des                    (V1: no controller sets it)

a level-following draw the plant does not have: LT-328507 and LT-328508 are open-loop indicators
(the owner's mapping in ``References/323D003 Datasheets.md``), so the tank's level is the
operator's to hold on FIC-328402's set point. In Phase 7's cold start that law doubled 735 when
compartment I filled (handoff B-87). 744 has no control valve on the plant: P&ID 102 draws
322P002 A/B through 322E006 to 322C001 with FI-322402 alone, and Uhde's Operating Manual III sets
the flow by hand in the field, read on FI-322402 (pp. 1-58, 4-8, 4-14, 4-19). 322P002 delivers the
field-set flow while either pump runs, against the heel cap: the instructor's field action, seeded
at PFD 744, where V1 delivers PFD 744 always (decision 212, a decided divergence).

Two departures on FIC-328402, decided 2026-09-27 (handoff B-38), ride with it onto 735: FT-328402
reads the flow delivered on the previous tick when 328P003 loses suction, the form the heel caps
use, and the loop carries the DCS table's 0.75 read per cent of FT-328402's 0-70 m3/h span, not
V1's 0.06 per kg/h.

Decided 2026-09-30 (handoff B-44): the four valves run their vendor trims, Valtek's modified
equal percentage, where V1 runs them linear — FV-323401, FV-323402 and FV-328402 from the
strokes at which their Kvs pass the design flows (49.26, 38.23 and 58.79 %, V1's 50), FV-328405
anchored on what it passes wide open (3206 kg/h, where V1 took one branch's 1534). FV-328406, V1's
fifth loop here, is 328C004's since the recycle became a draw on that column (B-50).
Each is inert while its valve holds its loop's set point.

The boundaries this unit reads, and when
----------------------------------------
  * 343 from 323C005 — THIS tick's (`AtmosphericAbsorberResult.m_343_kgh`): V1 steps the absorber
    immediately before this tank, and the hand-off is same-tick, not a tear;
  * 719, 720, 721 and 759 from unit 324, last tick's (V1 ``R324_719`` ... ``R324_759``), tears,
    and their condensers' cold ends, likewise (B-31), with 323C005's liquor temperature of this
    tick;
  * 741 from 328C004, last tick's, a tear: 328C004 steps FIC-328406 after this tank (B-50);
  * whether 322P002 A or B runs, and its field-set delivery (decision 212).

It publishes 744 (V1 aliases 755 to it) for 322C001's circuit, 791 for 323E011 and 793 for
328D001 on the same tick, 735 and compartment II's temperature for 328E007 on the same tick, and
734 for 323E003 on the same tick (decided 2026-10-10, handoff B-37; no V1 unit receives it).

Source
------
V1 ``backend/main.py`` step_sim, "Stage 2 : 328D003 active bays I/II + communicating
accumulation bay III" (lines 8883-8950) and the cp lines before it (8832-8833);
``redistribute_communicating_compartments`` and ``d003_level_telemetry`` (3717-3783); the seeds in
``State.__init__`` (6879-6884, 6947-6980, 7107-7127). The design data are in
`ureasim.data.unit_328d003`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ureasim.control.process_loop import FlowLoop, ProcessLoop
from ureasim.data.unit_328d003 import (
    D003_CP,
    D003_LAM_I_KJKG,
    D003_M_FLOOR_KG,
    D003_MI_DES_KG,
    D003_MI_FULL_KG,
    D003_MII_DES_KG,
    D003_MII_FULL_KG,
    D003_MIII_DES_KG,
    D003_MIII_FULL_KG,
    D003_ROUNDING_I_KGH,
    D003_ROUNDING_II_KGH,
    D003_T343_C,
    D003_T719_C,
    D003_T720_C,
    D003_T721_C,
    D003_T759_C,
    D003_TI_C,
    D003_TII_C,
    D003_TIII_C,
    FIC_323401_KC,
    FIC_323401_OP_DES_PCT,
    FIC_323401_SP_HI_M3H,
    FIC_323401_TI_S,
    FIC_323402_KC,
    FIC_323402_OP_DES_PCT,
    FIC_323402_SP_HI_M3H,
    FIC_323402_TI_S,
    FIC_328402_KC,
    FIC_328402_OP_DES_PCT,
    FIC_328402_SP_HI_M3H,
    FIC_328402_TI_S,
    FIC_328405_KC,
    FIC_328405_OP_DES_PCT,
    FIC_328405_OP_FULL_PCT,
    FIC_328405_SP_HI_M3H,
    FIC_328405_TI_S,
    FIC_TD_S,
    FT_TAU_S,
    FV_323401_CHAR,
    FV_323402_CHAR,
    FV_328402_CHAR,
    FV_328405_CHAR,
    M401_DES_KGH,
    M402_DES_KGH,
    M735_DES_KGH,
    M744_DES_KGH,
    RHO_401_KGM3,
    RHO_735_KGM3,
    RHO_791_KGM3,
    S793_CAP_KGH,
    S793_M_DES_KGH,
    T741_C,
)
from ureasim.data.unit_323c005 import C005_T_C
from ureasim.data.unit_324 import VACUUM_CONDENSERS
from ureasim.thermo.empirical import aqueous_cp

#: Numerical floor on a bay's temperature integration heat capacity [kJ/K], V1's literal.
HEAT_CAPACITY_FLOOR_KJK = 1e-6

#: Floor on the step in the heel caps' rate [s]: dt is never zero on the engine's fixed step.
DT_FLOOR_S = 1e-9

#: The tank's heel as a level [-]: where compartment I, the smallest bay, holds V1's 1 kg floor
#: — and each active bay's share of it [kg], 1 and 2.39 (decided divergence, see the module).
HEEL_LEVEL = D003_M_FLOOR_KG / D003_MI_FULL_KG
HEEL_I_KG = D003_M_FLOOR_KG
HEEL_II_KG = D003_M_FLOOR_KG * D003_MII_FULL_KG / D003_MI_FULL_KG

#: The three bays full [kg]: the approved liquid capacity, above which the tank overflows.
FULL_KG = (D003_MI_FULL_KG, D003_MII_FULL_KG, D003_MIII_FULL_KG)

#: The vacuum condensers' design cold ends [deg C], by tag: the PFD's 45, 40, 41 and 55 C, the
#: producers' designs the condensates' departures are taken from (handoff B-31).
T_COLD_END_DES_C = {tag: r.hot_out_c for tag, r in VACUUM_CONDENSERS.items()}


# ======================================================================================
# The openings
# ======================================================================================

def redistribute_communicating_compartments(
        masses_kg: tuple[float, float, float], temperatures_c: tuple[float, float, float],
        full_masses_kg: tuple[float, float, float],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Bring the three bays to one level without creating mass or sensible energy.

    Process utility
    ---------------
    The baffle openings of 328D003: with no opening areas or elevations in the sources, the
    bays are levelled at once — the communicating-vessel limit. Compartment III is the common
    accumulation bay, so every transfer between I and II passes through it at the donor's
    temperature: the donors are mixed into III first, then the receivers are supplied from that
    mix, which stops an almost empty III exporting more liquid at its old temperature than it
    held.

    Equation
    --------
        L = sum M_i / sum M_i,full,     M_i' = L . M_i,full
        donors (M_i' < M_i) give M_i - M_i' at T_i to III; receivers take M_i' - M_i at III's mix

    Refuses anything but three bays, a non-finite input, a negative mass or a non-positive
    capacity.

    Source: V1 `main.py` ``redistribute_communicating_compartments``.
    """
    if not (len(masses_kg) == len(temperatures_c) == len(full_masses_kg) == 3):
        raise ValueError("the 328D003 communicating model requires exactly three compartments")
    if any(not math.isfinite(value) for value in (*masses_kg, *temperatures_c, *full_masses_kg)):
        raise ValueError("compartment inventory inputs must be finite")
    if any(mass < 0.0 for mass in masses_kg):
        raise ValueError("compartment masses cannot be negative")
    if any(full <= 0.0 for full in full_masses_kg):
        raise ValueError("compartment full masses must be positive")

    total_mass = sum(masses_kg)
    if total_mass == 0.0:
        return tuple(0.0 for _ in masses_kg), tuple(temperatures_c)

    # The one level the total fills, and each bay at it.
    common_level = total_mass / sum(full_masses_kg)
    target_masses = tuple(common_level * full for full in full_masses_kg)
    energies = [mass * temp for mass, temp in zip(masses_kg, temperatures_c)]
    buffer_mass = masses_kg[2]
    buffer_energy = energies[2]

    # The donors among I and II give their excess to III at their own temperature.
    deltas = tuple(target_masses[index] - masses_kg[index] for index in (0, 1))
    for index, delta in enumerate(deltas):
        if delta < 0.0:
            donated_mass = -delta
            donated_energy = donated_mass * temperatures_c[index]
            energies[index] -= donated_energy
            buffer_mass += donated_mass
            buffer_energy += donated_energy

    # The receivers take what they lack from III's mix.
    buffer_temperature = buffer_energy / buffer_mass if buffer_mass > 0.0 else temperatures_c[2]
    for index, delta in enumerate(deltas):
        if delta > 0.0:
            received_energy = delta * buffer_temperature
            energies[index] += received_energy
            buffer_mass -= delta
            buffer_energy -= received_energy
    energies[2] = buffer_energy

    target_temperatures = tuple(
        energy / mass if mass > 0.0 else temperatures_c[index]
        for index, (energy, mass) in enumerate(zip(energies, target_masses))
    )
    return target_masses, target_temperatures


# ======================================================================================
# The four flow loops
# ======================================================================================

def _flow_loop(tag: str, kc: float, ti_s: float, sp_hi: float, op: float, sp_m3h: float,
               design_kgh: float, op_des: float, rho: float, characteristic: str,
               mode: str = "AUTO") -> FlowLoop:
    """A volumetric FIC seeded on its design flow: pv == sp, so the first tick holds."""
    loop = ProcessLoop(tag=tag, Kc=kc, Ti=ti_s, Td=FIC_TD_S, act=+1.0, op=op, sp=sp_m3h,
                       pv=sp_m3h, pv1=sp_m3h, pv2=sp_m3h, op_lo=0.0, op_hi=100.0, sp_lo=0.0,
                       sp_hi=sp_hi, mode=mode)
    return FlowLoop(loop=loop, design_flow=design_kgh, op_des=op_des, tau_s=FT_TAU_S,
                    rho_kgm3=rho, characteristic=characteristic)


def fic_323401() -> FlowLoop:
    """FIC-323401, PFD 734 off compartment II's header — a VOLUMETRIC loop in m3/h."""
    return _flow_loop("FIC-323401", FIC_323401_KC, FIC_323401_TI_S, FIC_323401_SP_HI_M3H,
                      FIC_323401_OP_DES_PCT, M401_DES_KGH / RHO_401_KGM3, M401_DES_KGH,
                      FIC_323401_OP_DES_PCT, RHO_401_KGM3, FV_323401_CHAR)


def fic_323402() -> FlowLoop:
    """FIC-323402, PFD 791, compartment II's wash to 323E011 — VOLUMETRIC, m3/h."""
    return _flow_loop("FIC-323402", FIC_323402_KC, FIC_323402_TI_S, FIC_323402_SP_HI_M3H,
                      FIC_323402_OP_DES_PCT, M402_DES_KGH / RHO_791_KGM3, M402_DES_KGH,
                      FIC_323402_OP_DES_PCT, RHO_791_KGM3, FV_323402_CHAR)


def fic_328405() -> FlowLoop:
    """FIC-328405, PFD 793, the normally closed spare: shut at design — VOLUMETRIC, m3/h."""
    return _flow_loop("FIC-328405", FIC_328405_KC, FIC_328405_TI_S, FIC_328405_SP_HI_M3H,
                      FIC_328405_OP_DES_PCT, S793_M_DES_KGH / RHO_401_KGM3, S793_CAP_KGH,
                      FIC_328405_OP_FULL_PCT, RHO_401_KGM3, FV_328405_CHAR)


def fic_328402() -> FlowLoop:
    """FIC-328402, PFD 735, 328P003's feed to 328E007 and the desorbers (B-39) — VOLUMETRIC,
    m3/h."""
    return _flow_loop("FIC-328402", FIC_328402_KC, FIC_328402_TI_S, FIC_328402_SP_HI_M3H,
                      FIC_328402_OP_DES_PCT, M735_DES_KGH / RHO_735_KGM3, M735_DES_KGH,
                      FIC_328402_OP_DES_PCT, RHO_735_KGM3, FV_328402_CHAR)


@dataclass
class TankLoops:
    """The four flow controllers on 328D003's draws, each seeded as V1 seeds it."""

    fic_323401: FlowLoop = field(default_factory=fic_323401)
    fic_323402: FlowLoop = field(default_factory=fic_323402)
    fic_328405: FlowLoop = field(default_factory=fic_328405)
    fic_328402: FlowLoop = field(default_factory=fic_328402)


# ======================================================================================
# The unit
# ======================================================================================

@dataclass(frozen=True)
class AmmoniaWaterTankResult:
    """Everything 328D003 publishes on one tick."""

    #: Compartment II's draws: PFD 735 to 328E007, 734 (FIC-323401), 791 to 323E011
    #: (FIC-323402) and the spare 793 to 328D001 (FIC-328405) [kg/h].
    m_735_kgh: float
    m_734_kgh: float
    m_791_kgh: float
    m_793_kgh: float
    #: The recycle 741 328C004 sent through FV-328406 last tick, into compartment II [kg/h].
    m_741_kgh: float
    #: PFD 744 from compartment I to 322P002, and on as 755 to the LP absorber [kg/h].
    m_744_kgh: float
    #: Each active bay's streams in and out [kg/h], the PFD rounding included in the inflow.
    in_i_kgh: float
    out_i_kgh: float
    in_ii_kgh: float
    out_ii_kgh: float
    #: 322P002 (compartment I) or 328P003 (compartment II) reached the tank's heel on this tick.
    suction_lost_i: bool
    suction_lost_ii: bool
    #: What the full tank lets go through its overflow [kg/h], and at what temperature [deg C].
    m_overflow_kgh: float
    t_overflow_c: float
    #: The state after the tick: each bay's holdup [kg], temperature [deg C] and level [%].
    m_i_kg: float
    m_ii_kg: float
    m_iii_kg: float
    t_i_c: float
    t_ii_c: float
    t_iii_c: float
    level_i_pct: float
    level_ii_pct: float
    level_iii_pct: float


@dataclass
class AmmoniaWaterTank:
    """328D003 as one object: the three bays' holdups and temperatures, and the step."""

    m_i_kg: float = D003_MI_DES_KG
    m_ii_kg: float = D003_MII_DES_KG
    m_iii_kg: float = D003_MIII_DES_KG
    t_i_c: float = D003_TI_C
    t_ii_c: float = D003_TII_C
    t_iii_c: float = D003_TIII_C
    #: The flow each capped leg delivered on the last tick 328P003 lost suction, which its
    #: transmitter reads on the next — None otherwise.
    cap_735_kgh: float | None = None
    cap_734_kgh: float | None = None
    cap_791_kgh: float | None = None
    cap_793_kgh: float | None = None
    #: Each inlet at its producer's live temperature, as its departure from the producer's design
    #: (decided 2026-10-16, handoff B-31); False is V1's design temperatures.
    live_inlets: bool = True

    def step(self, loops: TankLoops, m_343_kgh: float, m_719_kgh: float, m_720_kgh: float,
             m_721_kgh: float, m_759_kgh: float, m_741_kgh: float, p002_running: bool,
             dt: float, *, t_c005_c: float = C005_T_C,
             t_cold_ends_c: dict | None = None,
             m_744_set_kgh: float = M744_DES_KGH) -> AmmoniaWaterTankResult:
        """Advance 328D003 by one tick.

        Arguments
        ---------
        loops
            The four flow controllers on the tank's draws.
        m_343_kgh
            323C005's bottoms on THIS tick (`AtmosphericAbsorberResult.m_343_kgh`).
        m_719_kgh, m_720_kgh, m_721_kgh, m_759_kgh
            The vacuum train's condensates, last tick's, tears.
        m_741_kgh
            The recycle 328C004 sent through FV-328406, last tick's, a tear.
        p002_running
            Whether 322P002 A or B runs: 744 flows only then.
        t_c005_c, t_cold_ends_c
            323C005's liquor temperature of this tick, 343's producer, and the four vacuum
            condensers' cold ends by tag, last tick's (decided 2026-10-16, handoff B-31). The
            defaults, 323C005's design and None, the PFD's cold ends, are V1's inlets.
        m_744_set_kgh
            322P002's delivery as the field operator set it at FI-322402 [kg/h] (decision 212);
            the default, PFD 744, is V1's.

        The order is V1's: the four loops on their transmitters, the draws, each active bay on
        its own streams, then the openings level the three.
        """
        t_i, t_ii = self.t_i_c, self.t_ii_c
        cp_i = aqueous_cp(D003_CP, D003_TI_C, t_i)
        cp_ii = aqueous_cp(D003_CP, D003_TII_C, t_ii)

        # ----- the draws: four legs on the 328P003 header, 744 on 322P002 ---------------
        m_734 = loops.fic_323401.step(dt, flow_cap=self.cap_734_kgh)
        m_791 = loops.fic_323402.step(dt, flow_cap=self.cap_791_kgh)
        m_793 = loops.fic_328405.step(dt, flow_cap=self.cap_793_kgh)
        m_741 = m_741_kgh
        m_735 = loops.fic_328402.step(dt, flow_cap=self.cap_735_kgh)          # B-39
        # 744 has no control valve (P&ID 102: FI-322402 only): 322P002 delivers what the field
        # operator set at FI-322402 while it runs (decision 212; V1's PFD 744 at the seed).
        m_744 = m_744_set_kgh if p002_running else 0.0

        m_cond = m_719_kgh + m_720_kgh + m_721_kgh + m_759_kgh
        in_i = m_cond - D003_ROUNDING_I_KGH
        in_ii = m_343_kgh + m_741 + D003_ROUNDING_II_KGH

        # ----- neither pump draws below the tank's heel (decided divergence) -------------
        rate = 3600.0 / max(dt, DT_FLOOR_S)
        avail_i = max(max(self.m_i_kg - HEEL_I_KG, 0.0) * rate + in_i, 0.0)
        suction_lost_i = m_744 > avail_i
        if suction_lost_i:
            m_744 = avail_i
        avail_ii = max(max(self.m_ii_kg - HEEL_II_KG, 0.0) * rate + in_ii, 0.0)
        header = m_735 + m_734 + m_791 + m_793
        suction_lost_ii = header > avail_ii
        if suction_lost_ii:
            # Every leg on 328P003's discharge loses its share of the suction alike.
            share = avail_ii / header
            m_735, m_734, m_791, m_793 = (m_735 * share, m_734 * share, m_791 * share,
                                          m_793 * share)
        # Each transmitter on the header reads what its leg delivered (decided, B-38).
        self.cap_735_kgh, self.cap_734_kgh, self.cap_791_kgh, self.cap_793_kgh = (
            (m_735, m_734, m_791, m_793) if suction_lost_ii else (None, None, None, None))
        out_i = m_744
        out_ii = m_735 + m_734 + m_791 + m_793

        # ----- each inlet at its producer's live temperature, as its departure from the
        # producer's design: zero at design, so V1's to the bit there (B-31, 2026-10-16) -----
        if self.live_inlets:
            ends = T_COLD_END_DES_C if t_cold_ends_c is None else t_cold_ends_c
            t_343 = D003_T343_C + (t_c005_c - C005_T_C)
            t_719, t_720, t_721, t_759 = (
                t_des + (ends[tag] - T_COLD_END_DES_C[tag]) for t_des, tag in (
                    (D003_T719_C, "324E002"), (D003_T720_C, "324E005"),
                    (D003_T721_C, "324E006"), (D003_T759_C, "324E007")))
        else:
            t_343, t_719, t_720, t_721, t_759 = (D003_T343_C, D003_T719_C, D003_T720_C,
                                                 D003_T721_C, D003_T759_C)

        # ----- compartment I: the condensates' sensible heat and the carbamate heat ------
        p_i = ((m_719_kgh * (t_719 - t_i)
                + m_720_kgh * (t_720 - t_i)
                + m_721_kgh * (t_721 - t_i)
                + m_759_kgh * (t_759 - t_i)) / 3600.0 * cp_i
               + m_cond / 3600.0 * D003_LAM_I_KJKG)
        # SEMI-IMPLICIT in the four condensates, the temperature-dependent load.
        k_cap_i = m_cond / 3600.0 * cp_i
        t_i_raw = t_i + p_i * dt / max(self.m_i_kg * cp_i + k_cap_i * dt,
                                       HEAT_CAPACITY_FLOOR_KJK)
        m_i_raw = max(self.m_i_kg + (in_i - out_i) / 3600.0 * dt, D003_M_FLOOR_KG)

        # ----- compartment II: 343 at 328V001's temperature, 741 at its own ---------------
        p_ii = ((m_343_kgh * (t_343 - t_ii)
                 + m_741 * (T741_C - t_ii)) / 3600.0 * cp_ii)
        k_cap_ii = (m_343_kgh + m_741) / 3600.0 * cp_ii
        t_ii_raw = t_ii + p_ii * dt / max(self.m_ii_kg * cp_ii + k_cap_ii * dt,
                                          HEAT_CAPACITY_FLOOR_KJK)
        m_ii_raw = max(self.m_ii_kg + (in_ii - out_ii) / 3600.0 * dt, D003_M_FLOOR_KG)

        # ----- the openings level the three bays ------------------------------------------
        masses, temps = redistribute_communicating_compartments(
            (m_i_raw, m_ii_raw, self.m_iii_kg), (t_i_raw, t_ii_raw, self.t_iii_c), FULL_KG)

        # ----- a full tank overflows (decided divergence) ---------------------------------
        excess = [max(m - full, 0.0) for m, full in zip(masses, FULL_KG)]
        spilt = sum(excess)
        if spilt > 0.0:
            masses = tuple(m - x for m, x in zip(masses, excess))
            t_over = sum(x * t for x, t in zip(excess, temps)) / spilt
        else:
            t_over = sum(m * t for m, t in zip(masses, temps)) / sum(masses)
        self.m_i_kg, self.m_ii_kg, self.m_iii_kg = masses
        self.t_i_c, self.t_ii_c, self.t_iii_c = temps

        return AmmoniaWaterTankResult(
            m_735_kgh=m_735, m_734_kgh=m_734, m_791_kgh=m_791, m_793_kgh=m_793,
            m_741_kgh=m_741, m_744_kgh=m_744, in_i_kgh=in_i, out_i_kgh=out_i,
            in_ii_kgh=in_ii, out_ii_kgh=out_ii, suction_lost_i=suction_lost_i,
            suction_lost_ii=suction_lost_ii, m_overflow_kgh=spilt * 3600.0 / dt,
            t_overflow_c=t_over, m_i_kg=self.m_i_kg, m_ii_kg=self.m_ii_kg,
            m_iii_kg=self.m_iii_kg, t_i_c=self.t_i_c, t_ii_c=self.t_ii_c,
            t_iii_c=self.t_iii_c,
            level_i_pct=self.m_i_kg / D003_MI_FULL_KG * 100.0,
            level_ii_pct=self.m_ii_kg / D003_MII_FULL_KG * 100.0,
            level_iii_pct=self.m_iii_kg / D003_MIII_FULL_KG * 100.0,
        )


__all__ = [
    "HEAT_CAPACITY_FLOOR_KJK", "DT_FLOOR_S", "HEEL_LEVEL", "HEEL_I_KG", "HEEL_II_KG", "FULL_KG",
    "T_COLD_END_DES_C",
    "redistribute_communicating_compartments", "fic_323401", "fic_323402", "fic_328405",
    "fic_328402", "TankLoops", "AmmoniaWaterTankResult", "AmmoniaWaterTank",
]
