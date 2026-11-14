"""The urea melt main header, 80-US12-335114 — PIC-335201, LV-324501A / B, the twelve header valves,
HV-335602 and 335P001A / B: where LIC-324501's drain goes on the granulation side.

What this models
----------------
324F003's melt, PFD 402, leaves down its barometric leg to 335P001A / B, which deliver it through
LV-324501A up the main header to the granulator's twelve header valves (P&ID 130, UD-VT-335-FB-0004,
"12x2 HEADERS"), and through LV-324501B back to 323D002. The operator brings header valves online with
the plant's load to hold the header at 3.2 to 3.8 bar g and 323D002's small compartment level constant
(the process engineer's instruction I-3, 2026-11-14). The controls are AC4 PC35.2 as configured
(UD-MR-G00-FF-0004; decided 2026-11-14, decision 224):

    LIC-324501 (X) -- PC35.2.2 .3/.9/.10 --> E1 = 2.8 + min(X / 50, 1) --> PIC-335201 (CAS) --> LV-324501A
                   -- PC35.2.2 .6 -------> LV-324501B = 2 (X - 50) on X 50 to 100

so LV-324501A and LV-324501B may both pass melt: above X = 50 the header rides E1's 3.8 bar g ceiling
and LV-324501B returns the excess to 323D002, where V1's selector sends the melt one way only.
HV-335602, at the header's far end, drains to 335D004, outside the simulated plant: operable from
HIC-335602, opening in 3 s and closing in 25 s, its flow a boundary outflow (decision 225).

Equations (every factor exactly 1.0 at the design seed; each flow a fraction of the design drain,
PFD 402, so the design is reproduced by construction — decision 23's anchoring)
---------
    phi_noz = (N / N_des) sqrt(P / P_des)                                      the header valves online
    phi_hv  = (m_hv,full / m_des) cv(h_hv) sqrt((P + p_atm - p_335D004) / dP_case)   HV-335602, Pos. 150
    phi_B   = m_B,full cv(h_B) / m_des                       LV-324501B on its own law (decision 150)
    phi_A   LV-324501A on 335P001's head curve H = H0 - c (Q / Q_ref)^2, its inlet the design's moved
            by the head the pumps' total flow costs; with r = cv(h_A) / cv(h_A,des) and beta = phi_B:
              (1 / r^2 + kappa) phi_A^2 + 2 kappa beta phi_A - (1 + delta + kappa - kappa beta^2) = 0
              delta = (P_des - P) / dP_A,des,     kappa = rho g c Q_des^2 / (Q_ref^2 1e5 dP_A,des)
    h_A     = u(P), PIC-335201's step on PV = P
    g(P)    = phi_A(u(P), P) - phi_noz(P) - phi_hv(P) = 0

The last relation is solved for the header P inside the tick, PIC-335201 evaluated on each trial
header: read a tick late, the loop's proportional gain of 1.8 on the header rings it at its stroke
limits; evaluated inside the solve it settles (As-Built §CXX.4). The last committed header is tried
first — exact at the seed and at a parked header — and otherwise the root is bracketed on
[0, P_dead] (P_dead the pumps' dead head through LV-324501A) and found by the Illinois false
position. PIC-335201 is committed once, at the root. With 335P001A and B both stopped neither valve
passes melt and the header drains to 0 bar g. Trips 35.1 and 35.4 are not built (handoff).

Source: P&ID 130; AC4 UD-MR-G00-FF-0004 PC35.2 (pages 249 to 252); the DCS tuning table; the loop
summaries UD-MR-324-EC-0001 (L 324501) and UD-MR-335-EC-0001 (P 335201, F 335401, H 335602);
Flowserve UD-MR-G00-DZ-0048-003 Pos. 148 to 150; KSB UD-AU-335-EC-0039. The design data are in
`ureasim.data.unit_335` and `ureasim.data.unit_324`, each with its source.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass

from ureasim.control.process_loop import ProcessLoop
from ureasim.control.valve import cv_fraction
from ureasim.core.numeric import clamp
from ureasim.core.units_of_measure import ATM_BARA, G_ACC, PA_PER_BAR
from ureasim.data.control_valves import HV_335602
from ureasim.data.unit_324 import (
    LV_324501A_OP_DES_PCT,
    LV_324501B_FULL_KGH,
    LV_324501_CHAR,
    LV_324501_RHO_KGM3,
    P2_DES_KGH,
)
from ureasim.data.unit_335 import (
    HEADER_P_DES_BARG,
    HEADER_Q_DES_M3H,
    HEADER_VALVES_DES,
    HEADER_VALVES_MAX,
    HV_335602_CLOSE_S,
    HV_335602_DP_CASE_BAR,
    HV_335602_FULL_KGH,
    HV_335602_OPEN_S,
    HV_335602_P_DOWN_BARA,
    LIC_324501_X_DES_PCT,
    LV_324501A_DP_DES_BAR,
    P001_DROOP_M,
    P001_Q_REF_M3H,
    PC35_E1_BIAS_BARG,
    PC35_E1_DIVISOR,
    PC35_E1_YTAB,
    PC35_LVB_YTAB,
    PC35_XTAB,
    PIC_335201_DZ_BAR,
    PIC_335201_KC,
    PIC_335201_TD_S,
    PIC_335201_TI_S,
    PT_335201_SPAN_BAR,
)

__all__ = [
    "KAPPA", "SOLVE_TOL_BAR", "SOLVE_RESID_TOL", "SOLVE_MAXIT", "characteriser", "e1_setpoint_barg",
    "x_for_setpoint", "lv_b_stroke_pct", "nozzle_fraction", "hv_fraction", "recycle_fraction", "forward_fraction",
    "dead_head_barg", "pic_335201", "MeltHeaderResult", "MeltHeader",
]

#: 335P001's droop on LV-324501A's design differential [-]: what the curve's head costs between no
#: flow and the design flow, as a fraction of the 3.2 bar the valve takes at design (0.113).
KAPPA = (LV_324501_RHO_KGM3 * G_ACC * P001_DROOP_M * HEADER_Q_DES_M3H ** 2
         / (P001_Q_REF_M3H ** 2 * PA_PER_BAR * LV_324501A_DP_DES_BAR))

#: The header solve's tolerances, on the bracket [bar] and on the residual [-, of PFD 402: 1e-14 is
#: under a microgram an hour], and its iteration ceiling: the Illinois false position halves the
#: stale end's residual, so it converges superlinearly; 100 is far beyond need.
SOLVE_TOL_BAR = 1.0e-12
SOLVE_RESID_TOL = 1.0e-14
SOLVE_MAXIT = 100


# ======================================================================================
# AC4 PC35.2.2: LIC-324501's output split into PIC-335201's set point and LV-324501B's stroke
# ======================================================================================

def characteriser(x: float, xtab: tuple, ytab: tuple) -> float:
    """AC4's FUNG-1V function generator: piecewise linear in its table, flat beyond its ends.

    Process utility
    ---------------
    The DCS's split of one controller output into two actions. On PC35.2 it lets LIC-324501 first
    raise the header's set point (the granulator takes more melt) and only past half its range open
    the recycle, so the level is held by the granulator while it can be.

    Equation
    --------
        y = y_i-1 + (x - x_i-1) / (x_i - x_i-1) (y_i - y_i-1)     on the first segment holding x
    a repeated abscissa (PC35's last point) is a vertical segment and returns its own ordinate.
    """
    if x <= xtab[0]:
        return ytab[0]
    for i in range(1, len(xtab)):
        if x <= xtab[i]:
            x0, x1 = xtab[i - 1], xtab[i]
            if x1 <= x0:
                return ytab[i]
            return ytab[i - 1] + (x - x0) / (x1 - x0) * (ytab[i] - ytab[i - 1])
    return ytab[-1]


def e1_setpoint_barg(x_pct: float) -> float:
    """PIC-335201's external set point E1 [bar g] from LIC-324501's output X [%].

    Process utility
    ---------------
    The level's first lever: a rising 324F003 asks the header for more pressure, so the online
    header valves pass more melt to the granulator, from 2.8 bar g at X = 0 to 3.8 bar g at X = 50.

    Equation (PC35.2.2 .3, .9, .10): E1 = f3(X) / 100 + 2.8 = 2.8 + min(X / 50, 1).
    """
    return characteriser(x_pct, PC35_XTAB, PC35_E1_YTAB) / PC35_E1_DIVISOR + PC35_E1_BIAS_BARG


def lv_b_stroke_pct(x_pct: float) -> float:
    """LV-324501B's stroke [%] from LIC-324501's output X [%].

    Process utility
    ---------------
    The level's second lever: once the header rides E1's 3.8 bar g ceiling, the recycle opens and
    returns the excess melt to 323D002's Compartment I.

    Equation (PC35.2.2 .6): h_B = 0 on X 0 to 50, 2 (X - 50) on X 50 to 100.
    """
    return characteriser(x_pct, PC35_XTAB, PC35_LVB_YTAB)


def x_for_setpoint(p_barg: float) -> float:
    """The LIC-324501 output X [%] at which E1 is ``p_barg``, on E1's rising segment.

    Process utility
    ---------------
    Hands a header pressure over to the level loop: an exercise saved while the header was a
    battery-limit value restores with LIC-324501's output where AC4 would ask for that header
    (decision 226). Pressures beyond E1's range take its ends, 2.8 and 3.8 bar g.

    Equation: X = x0 + (y - y0) (x1 - x0) / (y1 - y0), y = (p - 2.8) 100 clamped to [y0, y1],
    rounded to 1e-9 % as the seed is.
    """
    x0, x1, y0, y1 = PC35_XTAB[0], PC35_XTAB[1], PC35_E1_YTAB[0], PC35_E1_YTAB[1]
    y = min(max((p_barg - PC35_E1_BIAS_BARG) * PC35_E1_DIVISOR, y0), y1)
    return round(x0 + (y - y0) * (x1 - x0) / (y1 - y0), 9)


if e1_setpoint_barg(LIC_324501_X_DES_PCT) != HEADER_P_DES_BARG:
    raise ValueError("LIC-324501's seed output does not set PIC-335201 on the design header")


# ======================================================================================
# The header's flows, each a fraction of the design drain
# ======================================================================================

def nozzle_fraction(headers_online: int, p_barg: float) -> float:
    """What the header valves online pass at the header P [-, of PFD 402].

    Process utility
    ---------------
    The granulator's demand on the header: each online valve feeds two injection headers of
    spray nozzles, which pass melt as the square root of the header's gauge pressure. The operator
    sets the count; the pressure follows the melt sent.

    Equation: phi_noz = (N / N_des) sqrt(P / P_des), the design's ten valves at 3.5 bar g 1.0.
    """
    return (headers_online / HEADER_VALVES_DES) * math.sqrt(max(p_barg, 0.0) / HEADER_P_DES_BARG)


def hv_fraction(stroke_pct: float, p_barg: float) -> float:
    """What HV-335602 drains from the header's end to 335D004 at the header P [-, of PFD 402].

    Process utility
    ---------------
    The header's drain at start-up and on I 35.4: open, it empties the header to the recycle tank
    and the header's pressure falls.

    Equation: phi_hv = (m_full / m_des) cv(h) sqrt((P + p_atm - p_down) / dP_case), Flowserve's
    Pos. 150 on its one case moved to the melt's density; exactly zero shut.
    """
    dp = max(p_barg + ATM_BARA - HV_335602_P_DOWN_BARA, 0.0)
    return (HV_335602_FULL_KGH / P2_DES_KGH * cv_fraction(stroke_pct / 100.0,
                                                          HV_335602.characteristic)
            * math.sqrt(dp / HV_335602_DP_CASE_BAR))


def recycle_fraction(stroke_pct: float) -> float:
    """What LV-324501B returns to 323D002 [-, of PFD 402].

    Process utility
    ---------------
    The excess the granulator cannot take: shut at design, and on its full-stroke capacity on its
    own sizing case, the engine's law (decision 150), with no pressure in it.

    Equation: phi_B = m_B,full cv(h_B) / m_des.
    """
    return LV_324501B_FULL_KGH * cv_fraction(stroke_pct / 100.0, LV_324501_CHAR) / P2_DES_KGH


def forward_fraction(stroke_pct: float, recycle_phi: float, p_barg: float) -> float:
    """What LV-324501A passes up the header [-, of PFD 402] at its stroke, beside the recycle.

    Process utility
    ---------------
    The header's supply. LV-324501A takes what is left of 335P001's head after the header, and the
    pumps' head falls with their total flow, so a recycle opening beside it, or a header falling,
    moves the forward flow even at a held stroke.

    Equation (quadratic in phi_A, the positive root; module docstring):
        a phi_A^2 + 2 b phi_A - c = 0,  a = 1 / r^2 + kappa,  b = kappa beta,
        c = 1 + delta + kappa - kappa beta^2;   phi_A = sqrt(c / a) at beta = 0
    exactly 1.0 at the design stroke and header with LV-324501B shut. No flow where c <= 0, the
    pumps' dead head reached, or with the valve shut.
    """
    r = (cv_fraction(stroke_pct / 100.0, LV_324501_CHAR)
         / cv_fraction(LV_324501A_OP_DES_PCT / 100.0, LV_324501_CHAR))
    if r <= 0.0:
        return 0.0
    delta = (HEADER_P_DES_BARG - p_barg) / LV_324501A_DP_DES_BAR
    a = 1.0 / (r * r) + KAPPA
    c = 1.0 + delta + KAPPA - KAPPA * recycle_phi * recycle_phi
    if c <= 0.0:
        return 0.0
    if recycle_phi == 0.0:
        return math.sqrt(c / a)
    b = KAPPA * recycle_phi
    return (-b + math.sqrt(b * b + a * c)) / a


def dead_head_barg(recycle_phi: float) -> float:
    """The header P at which LV-324501A passes nothing, whatever its stroke [bar g].

    Process utility
    ---------------
    The top of the header's bracket: 335P001's shut-off head on the header, less what the recycle's
    flow costs it. With no header valve online and HV-335602 shut the header rises to it.

    Equation: c = 0 in `forward_fraction`: P_dead = P_des + dP_A,des (1 + kappa - kappa beta^2).
    """
    return HEADER_P_DES_BARG + LV_324501A_DP_DES_BAR * (1.0 + KAPPA
                                                        - KAPPA * recycle_phi * recycle_phi)


# ======================================================================================
# PIC-335201 and the unit
# ======================================================================================

def pic_335201() -> ProcessLoop:
    """PIC-335201, the header's pressure: reverse acting, in CAS on E1, its output LV-324501A's
    stroke [%], seeded at the valve's design stroke on its vendor trim (decision 150)."""
    p = HEADER_P_DES_BARG
    return ProcessLoop(
        tag="PIC-335201", Kc=PIC_335201_KC, Ti=PIC_335201_TI_S, Td=PIC_335201_TD_S, act=+1.0,
        mode="CAS", op=LV_324501A_OP_DES_PCT, sp=p, pv=p, pv1=p, pv2=p,
        op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=PT_335201_SPAN_BAR, Dz=PIC_335201_DZ_BAR)


@dataclass(frozen=True)
class MeltHeaderResult:
    """The header on one tick."""

    #: PT-335201 [bar g], the header valves online, LIC-324501's output X [%] and E1 [bar g].
    p_barg: float
    headers_online: int
    x_pct: float
    e1_barg: float
    #: LV-324501A's stroke (PIC-335201's output), LV-324501B's (PC35.2.2 .6) and HV-335602's [%].
    lv_a_pct: float
    lv_b_pct: float
    hv_pct: float
    #: The flows as fractions of PFD 402 [-]: forward (LV-324501A, FT-335401's), recycle
    #: (LV-324501B), the header valves', HV-335602's.
    phi_forward: float
    phi_recycle: float
    phi_nozzles: float
    phi_hv: float
    #: LV-324501A's and LV-324501B's flows [kg/h] after the drain's heel limit, and HV-335602's share
    #: of the forward flow [-].
    forward_kgh: float
    recycle_kgh: float
    hv_share: float
    #: The root: its residual [-], the residual evaluations, and whether the heel limited the drain.
    residual: float
    iterations: int
    pump_running: bool
    capped: bool = False


@dataclass
class MeltHeader:
    """The header's state: its pressure the tick before and HV-335602's position."""

    p_barg: float = HEADER_P_DES_BARG
    hv_pct: float = 0.0

    def step(self, pic: ProcessLoop, x_pct: float, headers_online: int, hic_335602_pct: float,
             pump_running: bool, avail_kgh: float, dt: float) -> MeltHeaderResult:
        """Advance the header one tick.

        Arguments
        ---------
        pic
            PIC-335201, committed once at the header's root.
        x_pct
            LIC-324501's output this tick [%].
        headers_online
            The header valves online, 0 to 12 (the GRANULATION panel).
        hic_335602_pct
            HIC-335602's demand on HV-335602 [%].
        pump_running
            335P001A or B running.
        avail_kgh
            What 324F003 can drain this tick above its heel [kg/h] (decision 11's class).
        """
        n = int(clamp(headers_online, 0, HEADER_VALVES_MAX))
        # HV-335602 travels toward HIC-335602: fast open, slow close (H 335602).
        move = hic_335602_pct - self.hv_pct
        self.hv_pct = clamp(self.hv_pct + clamp(move, -100.0 / HV_335602_CLOSE_S * dt,
                                                100.0 / HV_335602_OPEN_S * dt), 0.0, 100.0)
        e1 = e1_setpoint_barg(x_pct)
        h_b = lv_b_stroke_pct(x_pct)
        beta = recycle_fraction(h_b) if pump_running else 0.0
        hv = self.hv_pct

        def forward(p: float) -> float:
            # LV-324501A on PIC-335201's trial step at the header p (the loop not committed).
            if not pump_running:
                return 0.0
            return forward_fraction(copy.copy(pic).step(p, dt, cas_sp=e1), beta, p)

        def g(p: float) -> float:
            return forward(p) - nozzle_fraction(n, p) - hv_fraction(hv, p)

        p, evals = self._root(g, dead_head_barg(beta))
        phi_a = forward(p)
        # The drain above 324F003's heel: both valves cut in proportion, the header then on what
        # LV-324501A delivers (the pumps losing suction).
        capped = False
        total = (phi_a + beta) * P2_DES_KGH
        if total > avail_kgh and total > 0.0:
            scale = max(avail_kgh, 0.0) / total
            phi_a, beta = phi_a * scale, beta * scale
            p, more = self._root(lambda q: phi_a - nozzle_fraction(n, q) - hv_fraction(hv, q),
                                 dead_head_barg(0.0))
            evals += more
            capped = True
        lv_a = pic.step(p, dt, cas_sp=e1)
        phi_noz, phi_hv = nozzle_fraction(n, p), hv_fraction(hv, p)
        out = phi_noz + phi_hv
        self.p_barg = p
        return MeltHeaderResult(
            p_barg=p, headers_online=n, x_pct=x_pct, e1_barg=e1, lv_a_pct=lv_a, lv_b_pct=h_b,
            hv_pct=hv, phi_forward=phi_a, phi_recycle=beta, phi_nozzles=phi_noz, phi_hv=phi_hv,
            forward_kgh=phi_a * P2_DES_KGH, recycle_kgh=beta * P2_DES_KGH,
            hv_share=min(phi_hv / out, 1.0) if out > 0.0 else 0.0,
            residual=phi_a - out if p > 0.0 else 0.0, iterations=evals,
            pump_running=pump_running, capped=capped)

    def _root(self, g, p_hi: float) -> tuple[float, int]:
        """The header P where ``g`` (decreasing in P) is zero, on [0, ``p_hi``]: the last committed
        header first, then the Illinois false position on the bracket. 0 where even an empty header
        sends more than arrives; ``p_hi`` where nothing leaves."""
        g0 = g(self.p_barg)
        if g0 == 0.0:
            return self.p_barg, 1
        lo, hi = 0.0, p_hi
        g_lo, g_hi = g(lo), g(hi)
        evals = 3
        if g_lo <= 0.0:
            return 0.0, evals
        if g_hi >= 0.0:
            return hi, evals
        if lo < self.p_barg < hi:
            if g0 > 0.0:
                lo, g_lo = self.p_barg, g0
            else:
                hi, g_hi = self.p_barg, g0
        side, p = 0, lo
        for _ in range(SOLVE_MAXIT):
            p = (lo * g_hi - hi * g_lo) / (g_hi - g_lo)
            gp = g(p)
            evals += 1
            if abs(gp) <= SOLVE_RESID_TOL or hi - lo <= SOLVE_TOL_BAR:
                break
            if gp > 0.0:
                lo, g_lo = p, gp
                if side > 0:
                    g_hi *= 0.5
                side = 1
            else:
                hi, g_hi = p, gp
                if side < 0:
                    g_lo *= 0.5
                side = -1
        return p, evals
