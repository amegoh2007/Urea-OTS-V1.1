"""The condensing-steam chest of an LP-steam heater — shared by 323E002, 323E010, 324E001, 324E003.

What this models
----------------
The shell side of a steam-heated exchanger. Steam is admitted through a control valve from the
header and condenses on the tube wall. The chest pressure is whatever makes the two agree: the
latent heat the valve admits equals the heat the wall takes. A hotter process pulls less
through the wall, so the chest rises toward the header; a valve pinched down starves the chest
toward the process's own saturation pressure. Every PIC on these chests controls that number.

Equations
---------
    m_valve / m_des = Phi_gas(h, P_hdr, P_chest, Tsat(P_hdr)) / Phi_gas(design)     (IEC 60534)
    R(P_chest)      = Q_des . (m_valve / m_des) . lambda(P_chest) / lambda(P_des)
                      - UA . (Tsat(P_chest) - T_process)
    P_chest         : R(P_chest) = 0

R is strictly decreasing in P_chest — the valve passes less and the wall condenses more — so
the root is unique. A shut valve lands the chest on the process saturation pressure (Q = 0);
a process hotter than the header's saturation drives it to the header.

Quasi-steady by construction. The chest vapour inventory is about 10 m3 x 2.2 kg/m3 against
about 2.8 kg/s through the valve, a few seconds of residence, and the shell volumes that
would size a dynamic state are not legible in the image-only exchanger datasheets. The
inventory limit is the right one while the chest is this much faster than the liquor it heats.

Source
------
V1 ``backend/main.py`` ``_steam_chest_residual_kw`` and ``steam_chest_pressure`` (report A-5).
The valve is V1's linear law by default; the steam properties are `data.unit_329`'s. A chest whose
valve has a vendor sheet runs on its trim (`ChestValve`; decision 23's class): PV-329203 and
PV-329212, Metso's Neldisc butterflies on 324E001 and 324E003 (decided 2026-10-14).

V1 also derives ``_chest_slave_kc_scale``, a multiplier on each chest PIC's gain that held the
loop gain V1 had tuned against its earlier chest, PV = stroke / 100 . P_header. The port runs
the chest PICs on the DCS table's gain per cent of the transmitter's span, and drops the
multiplier (decided 2026-09-30, As-Built §XL.2), so it is not ported.
"""

from __future__ import annotations

from dataclasses import dataclass

from ureasim.control.valve import XT_GLOBE, valve_gas_anchored
from ureasim.core.numeric import clamp
from ureasim.core.units_of_measure import ABSOLUTE_ZERO_C
from ureasim.data.unit_329 import STEAM_GAMMA, STEAM_MW
from ureasim.thermo import iapws

#: Lower bracket of the chest solve [bar a] — Tsat 17.5 C, below any process these chests heat.
#: Source: V1 `main.py` STEAM_CHEST_P_MIN_BARA.
STEAM_CHEST_P_MIN_BARA = 0.02

#: Iteration budget and tolerances of the bracketed Newton, all V1's own.
CHEST_ITERS = 60
CHEST_TOL_REL = 1.0e-9          # of the design duty [-]
CHEST_BRACKET_BAR = 1.0e-12     # bracket collapse [bar]
CHEST_FD_STEP_REL = 1.0e-7      # finite-difference step, relative and absolute [-, bar]


@dataclass(frozen=True)
class ChestValve:
    """A steam valve as its anchored law reads it — a chest's, or a stripping-steam valve's: the
    design stroke [%], the trim and its xT."""

    op_des_pct: float
    characteristic: str | tuple = "linear"
    xt: float = XT_GLOBE


def chest_residual_kw(p_chest: float, valve_open_pct: float, p_hdr: float, op_des: float,
                      p_chest_des: float, p_hdr_des: float, ua_kw: float, t_process_c: float,
                      q_des_kw: float, characteristic: str | tuple = "linear",
                      xt: float = XT_GLOBE) -> float:
    """Latent heat the valve admits minus the heat the wall takes [kW], at a trial chest pressure.

    Process utility
    ---------------
    The balance whose root IS the chest pressure. Written unfloored on purpose, so it is
    strictly decreasing and the root is unique; the heater's duty is floored at zero by the
    caller, because a condensing chest can only add heat.
    """
    m_ratio = valve_gas_anchored(
        1.0, valve_open_pct / 100.0, p_hdr, p_chest, iapws.tsat_c(p_hdr) + ABSOLUTE_ZERO_C,
        op_des / 100.0, p_hdr_des, p_chest_des, iapws.tsat_c(p_hdr_des) + ABSOLUTE_ZERO_C,
        STEAM_MW, gamma=STEAM_GAMMA, characteristic=characteristic, xt=xt)
    ts = iapws.tsat_c(p_chest)
    lam_ratio = iapws.hvap_kjkg(ts) / iapws.hvap_kjkg(iapws.tsat_c(p_chest_des))
    return q_des_kw * m_ratio * lam_ratio - ua_kw * (ts - t_process_c)


def steam_chest_pressure(valve_open_pct: float, header_pressure_bara: float, op_des: float,
                         p_chest_des: float, ua_kw: float, t_process_c: float, q_des_kw: float,
                         header_pressure_des_bara: float, p_prev: float = None,
                         characteristic: str | tuple = "linear",
                         xt: float = XT_GLOBE) -> float:
    """The chest pressure [bar a] at which the steam admitted equals the steam condensed.

    Process utility
    ---------------
    The PV of the chest pressure controller (PIC-329202 on 323E002, PIC-329208 on 323E010) and
    the saturation temperature that drives the heater duty. It replaced V1's
    ``opening / 100 . P_header``, under which a half-open valve halved the chest pressure
    whatever the tube wall was doing, so each PIC controlled a number computed from its own
    output.

    Method
    ------
    Bracketed Newton on [0.02, P_header], started from the previous tick's pressure; at an
    unchanged operating point the first residual is already zero and the previous value comes
    straight back. ``characteristic`` and ``xt`` are the valve's trim, V1's linear law and the
    globe's xT by default.
    """
    p_lo = STEAM_CHEST_P_MIN_BARA
    p_hi = max(header_pressure_bara, p_lo)
    args = (valve_open_pct, header_pressure_bara, op_des, p_chest_des, header_pressure_des_bara,
            ua_kw, t_process_c, q_des_kw, characteristic, xt)
    tol_kw = CHEST_TOL_REL * max(q_des_kw, 1.0)
    lo, hi = p_lo, p_hi
    p = clamp(p_chest_des if p_prev is None else p_prev, p_lo, p_hi)
    for _ in range(CHEST_ITERS):
        r = chest_residual_kw(p, *args)
        if abs(r) <= tol_kw:
            return p
        if r > 0.0:
            lo = p            # admitting more than the wall takes: the root is higher
        else:
            hi = p
        if hi - lo <= CHEST_BRACKET_BAR:
            return p
        h = max(CHEST_FD_STEP_REL, CHEST_FD_STEP_REL * p)
        p2 = p - h if p - h > p_lo else p + h
        slope = (chest_residual_kw(p2, *args) - r) / (p2 - p)
        p_new = p - r / slope if slope < 0.0 else 0.5 * (lo + hi)
        p = p_new if lo < p_new < hi else 0.5 * (lo + hi)
    return p


__all__ = [
    "ChestValve", "STEAM_CHEST_P_MIN_BARA", "CHEST_ITERS", "CHEST_TOL_REL", "CHEST_BRACKET_BAR",
    "CHEST_FD_STEP_REL",
    "chest_residual_kw", "steam_chest_pressure",
]
