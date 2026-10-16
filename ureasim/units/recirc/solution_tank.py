"""323D002 — the urea solution tank, stage 4 of unit 323.

What this models
----------------
The 80 % urea product of the 323F010 separator falls down its barometric leg into an
atmospheric tank whose shell is divided by an internal baffle into two compartments:

    323F010 --barometric leg--> Compartment I (80 m3) --323P003A/B, FV-324401--> 324E001
                                     |  spills over the baffle
                                     v
                                Compartment II (300 m3, no nozzle of its own)
                                     ^
                         HV-323D002-TIE, a field spool between the two

    LIC-323507 (Compartment I level)  ->  FIC-324401 (product flow)  ->  FV-324401
    LI-323504 (Compartment II level)      indication and alarms only

Compartment I is the active zone: every feed and discharge nozzle lands in it, including the
LV-324501B melt recycle from unit 324. Compartment II is dry in normal operation and fills
only when Compartment I overtops the baffle. The tie-in spool is a hand valve in the field,
not a DCS device, and it is modelled as the boolean the operator actually has.

How the tank mixes, and where its residence times come from
-----------------------------------------------------------
There is no residence-time parameter anywhere in this unit. Each compartment is a holdup
ODE, and its residence time is whatever its holdup divided by its through-flow happens to be:

  * **Compartment I is perfectly mixed.** One temperature (TI-323008) and one composition,
    both the outlet's. At the 10 % design level it holds 9208 kg against 92.8 t/h — a 357 s
    residence that LIC-323507's set point decides, not a constant. There is no plug-flow
    element inside the tank; the plug flow of this train is in its lines, which the
    receiving unit owns (`liquor_line`).
  * **The baffle is an ideal sharp weir** at Compartment I's full volume. Whatever the tick
    would put above 80 m3 — on the LIVE density — spills into Compartment II in the same tick,
    at Compartment I's composition before the tick. There is no crest equation and no spill
    limit; the flow over the baffle is exactly the excess.
  * **Compartment II is a perfectly mixed dead end** while the tie is shut: a blend of the
    spills it has received, with no outlet, so its residence time is unbounded. It carries a
    composition and a temperature of its own, each spill charged at Compartment I's state
    before the tick.
  * **Opening the tie makes one vessel.** The two compartments equalise to a common level
    fraction — they share the shell, so an equal fraction is an equal head — in the same tick,
    with no spool hydraulics, and from then on they carry one pooled composition and one
    temperature, drawn by 323P003 together. The pool starts from the two compartments'
    enthalpy balance. Opening it against a dry Compartment II drops a 10 % Compartment I level
    to 2.1 % at once; that is the scenario the spool exists for.

    dM_I/dt            = m_317 + m_recycle - m_324 - m_spill           (tie shut)
    dM_II/dt           = m_spill - m_overflow
    d(M_I + M_II)/dt   = m_317 + m_recycle - m_324 - m_overflow         (tie open)
    M cp dT/dt         = m_317 cp_317 (T_317 - T) + m_rec cp_rec (T_rec - T)
    T_II               <- the cp-weighted blend of T_II and each spill at T_I
    d(M w)/dt          = the species balance of `units.liquor_stage`, with no vapour and
                         no reaction

M in the energy balance is Compartment I alone with the tie shut, and the pool with it open.
The tank has no duty, no heat loss and no biuret formation: V1's "well-mixed species blender"
(AUDIT F-8). The design residence of Compartment I is low precisely to limit biuret
formation, and the model carries none — handoff B-25.

Where this unit departs from V1 — decided 2026-09-27 (handoffs B-26, B-27)
-------------------------------------------------------------------------
The process engineer decided that the tank's books must close. Each change is inert at every
state where V1's tank did not create or destroy liquor, so V1's transients are reproduced
bit for bit until one of these limits is reached:

  * **323P003 delivers only what the tank holds** (B-26). The discharge is FV-324401's flow,
    capped at the liquid above the heel plus what arrives on the tick. The heel is V1's 1 kg
    floor on Compartment I, and the same 1 kg in Compartment I's share of the pool with the
    tie open. When the cap binds, the flow is flagged as a loss of suction for the trip
    logic, and FT-324401 reads the flow delivered, not the valve's. V1 floored the holdup
    and kept pumping, so an empty Compartment I created liquor.
  * **A full tank overflows** (B-27). What V1 clamped away above 300 m3 in Compartment II, or
    above 380 m3 in the pool, leaves as a published overflow stream at the overflowing
    liquor's temperature and composition. Its destination, traced 2026-10-16, is 335D004, the
    recycle tank: nozzle N12 to seal pot Z2301Z and the underground drain to unit 335
    (UD-VT-322-FB-0004, P&ID 116), which this model does not hold, so it leaves the plant here.
  * **Compartment II's blend divides by what it holds before the overflow** (B-27): the spill
    mixes in, then the overflow leaves at the mixture's composition, so the fractions sum to
    one. V1 divided by the clamped holdup.
  * **Compartment II has a temperature** (B-27), as above. V1 forgot a spill's temperature
    and pooled at Compartment I's.

When the tie opens on a Compartment I at its 1 kg heel with a dry Compartment II, the pooled
heel is made up once — at most 3.75 kg in all. Nothing else is created or destroyed.

One more, decided 2026-09-30 (handoff B-44): FV-324401 runs its vendor trim, Valtek's modified
equal percentage, from the 72.36 % stroke at which its Kvs passes PFD 324 (`fv_324401_th`);
V1 runs it linear from 50 %. At the design stroke it passes the design flow either way.

What the level instrument reads
-------------------------------
A level gauge measures volume, so both spans are the steel volumes times the liquor's LIVE
density, anchored on the PFD's 1151 kg/m3 (V1 AUDIT C10). With the tie open LIC-323507 reads
the pool on the pooled span.

The boundaries this stage reads, and when
-----------------------------------------
  * the 323F010 drain, carried down the 323F010 -> 323D002 line, which this stage owns;
  * the LV-324501B melt recycle from unit 324 — a one-tick tear, unit 324 advancing later in
    the tick. At zero recycle its temperature and composition cannot move any output;
  * HV-323D002-TIE.

What it publishes for unit 324 is the pump discharge, m_324, and the tank's state AFTER the
tick: unit 324 reads the tank later in the same tick, when it has already advanced. The
overflow stream is published beside it and goes nowhere yet.

Source
------
V1 ``backend/main.py`` step_sim, "Stage 4: Urea Solution Tank 323D002" (lines 8656-8810) and
the 323F010 -> 323D002 line transport (8564-8572); the telemetry block for the published
levels and inventories (10660-10671); reports TD-013 (the tie-in spool and the removed
composition pin), AUDIT C10 (the live density) and F-8 (the species layer).
`References/323D002.md` for the topology. The design data are in `ureasim.data.unit_323`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ureasim.control.process_loop import ProcessLoop
from ureasim.control.valve import cv_fraction
from ureasim.core.numeric import clamp
from ureasim.core.signal import first_order_lag
from ureasim.data.design_point import R323_D002_RHO, R323_M324_DES, R324_W_EV2, R324_W_IN
from ureasim.data.unit_323 import (
    CP_F010_DES,
    D002_LVL_SP_PCT,
    D002_M_I_DES_KG,
    D002_M_I_FLOOR_KG,
    D002_VOL_I_M3,
    D002_VOL_II_M3,
    F010_T_SP_C,
    FIC_324401_KC,
    FIC_324401_SP_HI_TH,
    FIC_324401_TD_S,
    FIC_324401_TI_S,
    FT_324401_TAU_S,
    FV401_CHAR,
    FV401_OP_DES_PCT,
    LIC_323507_KC,
    LIC_323507_OP_HI_TH,
    LIC_323507_TI_S,
    W_S317,
)
from ureasim.thermo.empirical import urea_soln_cp, urea_soln_rho
from ureasim.thermo.urea_liquor import SOLUTION_SPECIES
from ureasim.units import liquor_stage
from ureasim.units.recirc.liquor_line import receive_liquor

#: The 323F010 -> 323D002 line, which this unit owns as the receiving vessel. Source: V1
#: `main.py`, ``_transport_process(s, "323F010_TO_323D002", ...)``.
INLET_ROUTE = "323F010_TO_323D002"

#: Key the FT-324401 lag is stored under. Source: V1 `main.py`, ``_lag1(s.tlag,
#: "R323_FIC324", ...)``.
FT_324401_LAG_KEY = "R323_FIC324"


def fv_324401_th(stroke_pct: float) -> float:
    """FV-324401's flow at a stroke [t/h]: FIC-324401's plant.

    Process utility
    ---------------
    The pure-gain flow element FIC-324401 closes around, through the valve's trim and anchored
    so the design stroke passes PFD 324 exactly. V1 writes it linear, ``stroke / 100 .
    flow_span_324`` with the span the design flow over the design stroke; the port runs the
    vendor's modified equal-percentage trim from the stroke its Kvs gives (handoff B-44,
    decided 2026-09-30).

    Equation
    --------
        m = m_324,des . f(h) / f(h_des)          f = `control.valve.cv_fraction`
    """
    return R323_M324_DES / 1000.0 * (cv_fraction(stroke_pct / 100.0, FV401_CHAR)
                                     / cv_fraction(FV401_OP_DES_PCT / 100.0, FV401_CHAR))


#: Numerical floors, V1's own literals at this stage: the temperature integration's heat
#: capacity [kJ/K], the pooled inventory below which there is nothing to blend [kg], and the
#: time step the spill rate divides by [s].
HEAT_CAPACITY_FLOOR_KJK = 1e-6
BLEND_FLOOR_KG = 1e-9
DT_FLOOR_S = 1e-9


# ======================================================================================
# The two controllers, seeded exactly as V1 seeds them
# ======================================================================================

def lic_323507() -> ProcessLoop:
    """LIC-323507, the Compartment I level master. DIRECT acting: a rising level raises its
    output, the product-flow DEMAND [t/h] handed to FIC-324401 as a remote set point."""
    return ProcessLoop(
        tag="LIC-323507", Kc=LIC_323507_KC, Ti=LIC_323507_TI_S, Td=0.0, act=-1.0,
        op=R323_M324_DES / 1000.0, sp=D002_LVL_SP_PCT,
        pv=D002_LVL_SP_PCT, pv1=D002_LVL_SP_PCT, pv2=D002_LVL_SP_PCT,
        op_lo=0.0, op_hi=LIC_323507_OP_HI_TH, sp_lo=0.0, sp_hi=100.0)


def fic_324401() -> ProcessLoop:
    """FIC-324401, the product-flow slave, in CASCADE under LIC-323507. Its output is the
    FV-324401 stroke [%]."""
    return ProcessLoop(
        tag="FIC-324401", Kc=FIC_324401_KC, Ti=FIC_324401_TI_S, Td=FIC_324401_TD_S, act=+1.0,
        mode="CAS", op=FV401_OP_DES_PCT, sp=R323_M324_DES / 1000.0,
        pv=R323_M324_DES / 1000.0, pv1=R323_M324_DES / 1000.0, pv2=R323_M324_DES / 1000.0,
        op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=FIC_324401_SP_HI_TH)


# ======================================================================================
# The unit
# ======================================================================================

@dataclass(frozen=True)
class SolutionTankResult:
    """Everything stage 4 publishes on one tick."""

    #: The 323F010 drain as it arrived through the 323F010 -> 323D002 line [kg/h], [deg C],
    #: [-], and the specific heat the tank's energy balance charges it at [kJ/(kg.K)] — the
    #: liquor correlation itself, which is what V1 uses at this stage.
    feed_kgh: float
    feed_t_c: float
    feed_w: dict
    feed_cp: float
    #: The LV-324501B melt recycle as the tank takes it — never negative [kg/h].
    recycle_kgh: float
    #: The live liquor density both level spans are taken on [kg/m3].
    rho_kgm3: float
    #: LIC-323507's PV [%] — the level the loop acted on, before this tick — and its output,
    #: the product-flow demand [t/h].
    lic_pv_pct: float
    lic_op_th: float
    #: FT-324401, the lagged measured flow [t/h], and the FV-324401 stroke [%].
    fic_pv_th: float
    fic_op_pct: float
    #: The 323P003A/B discharge to unit 324 [kg/h], and whether the liquid in the tank rather
    #: than FV-324401 set it on this tick — the loss of suction the trip logic reads (B-26).
    m_324_kgh: float
    suction_lost: bool
    #: What spilled over the baffle into Compartment II on this tick [kg].
    spill_kg: float
    #: The overflow of a full tank [kg/h], at the temperature [deg C] and composition of the
    #: liquor it leaves (B-27): Compartment II's with the tie shut, the pool's with it open.
    overflow_kgh: float
    overflow_t_c: float
    overflow_w: dict
    #: LI-323504 [%], and the two inventories [m3], on the holdups after this tick and the
    #: density before it, as V1 publishes them.
    li_323504_pct: float
    comp_i_m3: float
    comp_ii_m3: float
    #: The state after this tick — also what unit 324's feed line departs with.
    m_i_kg: float
    m_ii_kg: float
    t_c: float
    t_ii_c: float
    w: dict
    w_ii: dict


@dataclass
class SolutionTank:
    """323D002 as one object: the two compartments' state and the tank's step."""

    #: Compartment I and II holdups [kg]. Compartment II seeds dry, as it runs.
    m_i_kg: float = D002_M_I_DES_KG
    m_ii_kg: float = 0.0
    #: TI-323008, the Compartment I bulk temperature [deg C], seeded on the separator's 99 C.
    t_c: float = F010_T_SP_C
    #: Compartment II's temperature [deg C]: the enthalpy of the spills it holds, since it has
    #: no heat input and no outlet of its own (B-27). Seeded on the separator's 99 C; it moves
    #: nothing while Compartment II is dry.
    t_ii_c: float = F010_T_SP_C
    #: Compartment I and Compartment II compositions [mass fractions].
    w: dict = field(default_factory=lambda: dict(W_S317))
    w_ii: dict = field(default_factory=lambda: dict(W_S317))
    #: The flow 323P003 delivered on the last tick when the tank's liquid limited it [t/h];
    #: None while FV-324401 set it (B-26).
    suction_cap_th: float | None = None
    #: The inlet line's packet FIFO and the FT-324401 lag.
    line_state: dict = field(default_factory=dict)
    lag_state: dict = field(default_factory=dict)

    def step(self, lic: ProcessLoop, fic: ProcessLoop,
             drain_kgh: float, drain_t_c: float, drain_w: dict,
             recycle_kgh: float, recycle_t_c: float, recycle_w: dict,
             tie_open: bool, dt: float) -> SolutionTankResult:
        """Advance stage 4 by one tick.

        Arguments
        ---------
        drain_kgh, drain_t_c, drain_w
            323F010's barometric-leg drain as it departed on this tick: the flow [kg/h] and
            the separator's temperature [deg C] and composition before the separator
            advanced (`PreEvaporatorResult.m_317_kgh`, `.drain_t_c`, `.drain_w`).
        recycle_kgh, recycle_t_c, recycle_w
            The LV-324501B melt recycle written by unit 324 on the previous tick — a
            one-tick tear.
        tie_open
            HV-323D002-TIE, the Compartment I / II field spool.

        The order is V1's: the level the controllers act on and the density both spans use
        are taken on the state at the top of the tick; the holdups advance; the temperature
        advances on the OLD holdup; the compositions advance last, the spill carrying
        Compartment I's composition and temperature from before the tick.
        """
        recycle = max(recycle_kgh, 0.0)
        # ----- the inlet: one closed packet down the 323F010 -> 323D002 line -----------
        feed = receive_liquor(self.line_state, INLET_ROUTE, drain_kgh, drain_t_c, drain_w,
                              CP_F010_DES, dt)
        m_i_pre, m_ii_pre, t_i_pre = self.m_i_kg, self.m_ii_kg, self.t_c

        # ----- the level: volume, on the live density (AUDIT C10) -----------------------
        rho = urea_soln_rho(self.w.get("Urea", R324_W_IN), self.t_c, R323_D002_RHO)
        v_i_full = D002_VOL_I_M3 * rho
        v_ii_full = D002_VOL_II_M3 * rho
        v_tie_full = v_i_full + v_ii_full
        # Connected vessels share a head, not a mass: both compartments are cut from the same
        # shell, so an equal level fraction is an equal head and the pooled span is the sum.
        level = clamp(((m_i_pre + m_ii_pre) / v_tie_full if tie_open
                       else m_i_pre / v_i_full) * 100.0, 0.0, 100.0)

        # ----- LIC-323507 -> FIC-324401 -> FV-324401 ------------------------------------
        lic_op = lic.step(level, dt)
        # FT-324401 reads the flow the pump delivered last tick, lagged: on a pure-gain valve an
        # unlagged PV gives the velocity-form loop a pole at -Kc . G, which rings tick to tick.
        # That is the valve's flow unless the tank's liquid limited it (B-26).
        prior_flow = fv_324401_th(fic.op)
        if self.suction_cap_th is not None:
            prior_flow = min(prior_flow, self.suction_cap_th)
        fic_pv = first_order_lag(self.lag_state, FT_324401_LAG_KEY, prior_flow,
                                 FT_324401_TAU_S, dt)
        fic_op = fic.step(fic_pv, dt, cas_sp=lic_op)
        m_324 = max(fv_324401_th(fic_op), 0.0) * 1000.0
        # 323P003 can deliver only the liquid above the heel plus what arrives on the tick
        # (decided divergence, handoff B-26). The heel keeps the 1 kg Compartment I floor out
        # of the pump's reach — with the tie open, as Compartment I's share of the pool — so
        # the floor never makes up what the pump took. Inert at every normal state.
        heel = D002_M_I_FLOOR_KG * v_tie_full / v_i_full if tie_open else D002_M_I_FLOOR_KG
        m_pumpable = (m_i_pre + m_ii_pre if tie_open else m_i_pre) - heel
        m_324_avail = (max(m_pumpable, 0.0) / max(dt, DT_FLOOR_S) * 3600.0
                       + feed.m_kgh + recycle)
        suction_lost = m_324 > m_324_avail
        if suction_lost:
            m_324 = m_324_avail
        self.suction_cap_th = m_324 / 1000.0 if suction_lost else None

        # ----- the holdups -------------------------------------------------------------
        spill = 0.0
        if tie_open:
            # One pooled inventory at a common level fraction; Compartment II now drains
            # through the spool into Compartment I's suction. A full pool overflows (B-27).
            m_tot = m_i_pre + m_ii_pre + (feed.m_kgh + recycle - m_324) / 3600.0 * dt
            overflow = max(m_tot - v_tie_full, 0.0)
            m_tot = clamp(m_tot, D002_M_I_FLOOR_KG, v_tie_full)
            frac = m_tot / v_tie_full
            m_i_new = frac * v_i_full
            m_ii_new = frac * v_ii_full
        else:
            m_i_new = m_i_pre + (feed.m_kgh + recycle - m_324) / 3600.0 * dt
            if m_i_new > v_i_full:
                # The baffle: everything above Compartment I's full volume goes over.
                spill = m_i_new - v_i_full
                m_i_new = v_i_full
            # Everything above Compartment II's full volume overflows (B-27).
            overflow = max(m_ii_pre + spill - v_ii_full, 0.0)
            m_ii_new = clamp(m_ii_pre + spill, 0.0, v_ii_full)
        self.m_i_kg = max(m_i_new, D002_M_I_FLOOR_KG)
        self.m_ii_kg = max(m_ii_new, 0.0)

        # ----- TI-323008: no duty, no reaction, two T-dependent inlets ------------------
        # The low-temperature alarm on TI-323008 is the crystallisation warning, so the tank
        # needs its own thermal inertia. At design T_in == T and the bracket is 0.0.
        cp_in = urea_soln_cp(feed.w.get("Urea", R324_W_IN), feed.t_c)
        cp_rec = urea_soln_cp(recycle_w.get("Urea", R324_W_EV2), recycle_t_c)
        cp_tank = urea_soln_cp(self.w.get("Urea", R324_W_IN), t_i_pre)
        cp_ii = urea_soln_cp(self.w_ii.get("Urea", R324_W_IN), self.t_ii_c)
        m_thermal = (m_i_pre + m_ii_pre) if tie_open else m_i_pre
        t_start = t_i_pre
        if tie_open:
            # The spool mixes two liquors at their own temperatures, so the pool starts from
            # their enthalpy balance (B-27). Exactly zero with Compartment II dry or pooled.
            t_start = t_i_pre + m_ii_pre * cp_ii * (self.t_ii_c - t_i_pre) / max(
                m_i_pre * cp_tank + m_ii_pre * cp_ii, HEAT_CAPACITY_FLOOR_KJK)
        # SEMI-IMPLICIT in both inlets, whose heat-capacity rates belong to flows.
        k_cap = feed.m_kgh / 3600.0 * cp_in + recycle / 3600.0 * cp_rec
        self.t_c = t_start + (
            feed.m_kgh / 3600.0 * cp_in * (feed.t_c - t_start)
            + recycle / 3600.0 * cp_rec * (recycle_t_c - t_start)
        ) * dt / max(m_thermal * cp_tank + k_cap * dt, HEAT_CAPACITY_FLOOR_KJK)
        if tie_open:
            self.t_ii_c = self.t_c
        elif spill > 0.0:
            # Compartment II takes each spill at Compartment I's temperature before the tick,
            # on the same cp-weighted balance (B-27).
            self.t_ii_c = self.t_ii_c + spill * cp_tank * (t_i_pre - self.t_ii_c) / max(
                m_ii_pre * cp_ii + spill * cp_tank, HEAT_CAPACITY_FLOOR_KJK)

        # ----- the compositions: a blender, no vapour, no reaction ----------------------
        if tie_open:
            # One well-mixed volume carries one composition: blend the two inventories, then
            # advance the pool on the flows the holdup balance used.
            m_pool_pre = m_i_pre + m_ii_pre
            w_pool = ({k: (m_i_pre * self.w.get(k, 0.0) + m_ii_pre * self.w_ii.get(k, 0.0))
                       / m_pool_pre for k in SOLUTION_SPECIES}
                      if m_pool_pre > BLEND_FLOOR_KG else dict(self.w))
            # The overflow leaves at the pool's composition beside the pump.
            w_pool = liquor_stage.advance_species(w_pool, m_pool_pre, self.m_i_kg + self.m_ii_kg,
                                                  feed.m_kgh, feed.w, 0.0, w_pool,
                                                  m_324 + overflow * 3600.0 / max(dt, DT_FLOOR_S),
                                                  0.0, dt, m_in2_kgh=recycle, w_in2=recycle_w)
            self.w = w_pool
            self.w_ii = dict(w_pool)
        else:
            # Compartment I loses mass through both outlets, the pump and the baffle. The spill
            # leaves at the bulk composition, so it cannot move w by itself; passing it keeps
            # the species books closed.
            w_i_new = liquor_stage.advance_species(
                self.w, m_i_pre, self.m_i_kg, feed.m_kgh, feed.w, 0.0, self.w,
                m_324 + spill * 3600.0 / max(dt, DT_FLOOR_S), 0.0, dt,
                m_in2_kgh=recycle, w_in2=recycle_w)
            m_ii_mix = m_ii_pre + spill
            if spill > 0.0 and m_ii_mix > BLEND_FLOOR_KG:
                # The spill carries Compartment I's liquor from before the tick. The blend
                # divides by what Compartment II holds BEFORE any overflow, which then leaves
                # at the blend's composition (B-27); below full the two holdups are the same.
                self.w_ii = {k: (m_ii_pre * self.w_ii.get(k, 0.0) + spill * self.w.get(k, 0.0))
                             / m_ii_mix for k in SOLUTION_SPECIES}
            self.w = w_i_new

        return SolutionTankResult(
            feed_kgh=feed.m_kgh, feed_t_c=feed.t_c, feed_w=feed.w, feed_cp=cp_in,
            recycle_kgh=recycle, rho_kgm3=rho,
            lic_pv_pct=level, lic_op_th=lic_op, fic_pv_th=fic_pv, fic_op_pct=fic_op,
            m_324_kgh=m_324, suction_lost=suction_lost, spill_kg=spill,
            overflow_kgh=overflow * 3600.0 / max(dt, DT_FLOOR_S),
            overflow_t_c=self.t_c if tie_open else self.t_ii_c,
            overflow_w=self.w if tie_open else self.w_ii,
            li_323504_pct=self.m_ii_kg / v_ii_full * 100.0,
            comp_i_m3=self.m_i_kg / rho, comp_ii_m3=self.m_ii_kg / rho,
            m_i_kg=self.m_i_kg, m_ii_kg=self.m_ii_kg, t_c=self.t_c, t_ii_c=self.t_ii_c,
            w=self.w, w_ii=self.w_ii,
        )


__all__ = [
    "INLET_ROUTE", "FT_324401_LAG_KEY", "fv_324401_th",
    "HEAT_CAPACITY_FLOOR_KJK", "BLEND_FLOOR_KG", "DT_FLOOR_S",
    "lic_323507", "fic_324401",
    "SolutionTankResult", "SolutionTank",
]
