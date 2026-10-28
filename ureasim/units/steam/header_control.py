"""Unit 329's controllers — the three header pressures, HV-329601's forcing and the drum levels.

What this models
----------------
The DCS loops on the steam network, as V1 writes them and as Uhde's functional diagrams for unit
329 (UD-MR-329-FF-0002, read from the scans) draw them:

  * **PIC-329204** on 329D005, direct PI about the stroke that passes the design supply:
        e = SP - P,  i <- clamp(i + e dt, +-I_max),  op = clamp(bias + Kc e + Ki i, 0, 100)
    Trip 21.2 (the synthesis main trip) loads 10 bar g into its set point for 2 s (sheet 3);
    the operator may move it afterwards.
  * **HV-329601**, 329D005's vent to the silencer, on its hand controller — but with trip 21.2
    active it is forced fully open while PT-329204 is above 12 bar g, and forced shut for 3 s
    when the pressure falls back below it; the hand controller follows the forced value and the
    operator's command is blocked while forced (sheet 3).
  * **PIC-329205**'s split range on 329D009, proportional about PV-329205A's design stroke:
        s = bias - K (P - SP);  PV-329205A = clamp(s), PV-329205B = clamp(-s)
    — Uhde's two characteristics about OUTP 50 % (sheet 4), A closing first.
  * **the PIC-329207 trio** on the LP header, on one master set point (sheet 5): B on it,
    trimming the turbine export about its bias (two-sided integral); A venting at master + 0.1
    bar and C admitting supply steam at master - 0.1 (one-sided integrals, A on P - SP, C on
    SP - P). Sheet 5's 3 % cut-off on A's and C's valves is not wired: measured, it chatters
    (`ureasim.data.unit_329_network`).
  * **the level loops** LIC-329502 / 503 / 504, velocity-form PI on per cent of level:
        e = L - SP (a drain) or SP - L (a make-up);  op <- clamp(op + Kc ((e - e_prev) + dt e / Ti))

Every loop in MAN holds its output and its integral, so a return to AUTO is bumpless.

Source
------
V1 ``backend/steam_system.py`` ``step_steam`` (the loops' equations) and ``_level_loop``; the
tunings of `ureasim.data.unit_329_network` (decisions 10 and 21); Uhde's functional diagrams for
trip 21.2's logic (decisions 26, 27, 39's classes). As-Built Part LIV.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ureasim.data.unit_329 import P_HP_BARA, P_LP_BARA, P_SUP_BARA, STEAM_PFD_KGH
from ureasim.data.unit_329_network import (
    BIAS_207B_PCT,
    DB_LP_BAR,
    HV601_FORCE_BARA,
    HV601_SHUT_PULSE_S,
    K_902,
    K_PIC_9,
    LEVEL_SP_DES_PCT,
    LIC_TUNING,
    P_9_SP_BARA,
    PIC_329204_I_AUTHORITY_PCT,
    PIC_329204_KC,
    PIC_329204_KI,
    PIC_329205_KC,
    PIC_329205_TI_S,
    PIC_329207_KC,
    PIC_329207_KI,
    PV205A_OP_DES_PCT,
    PV204_OP_DES_PCT,
    PV207B_OP_DES_PCT,
    TRIP_212_SP_BARA,
)

#: How long trip 21.2 loads PIC-329204's set point [s] (sheet 3's MONO 2 s).
TRIP_212_SP_PULSE_S = 2.0


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def supply_seed_pct() -> float:
    """PV-329204's stroke that passes the design supply at 25 -> 19.7 bar a [%] (V1
    ``_seed_supply_pct``, on PFD 902 — decision 47)."""
    return min(100.0, (STEAM_PFD_KGH["902"] / 3600.0) / (K_902 * (P_SUP_BARA - P_HP_BARA) ** 0.5)
               * 100.0)


#: PIC-329204's bias: the seed stroke, so the design point holds with no error and no integral —
#: V1's, on K_902, which the equivalence harness keeps. The port's is PV-329204's design stroke on
#: Metso's trim, ``PV204_OP_DES_PCT`` (decided 2026-10-15).
SUPPLY_BIAS_PCT = supply_seed_pct()


@dataclass
class Pic329204:
    """PIC-329204 and PV-329204: 329D005's pressure on the supply valve."""

    mode: str = "AUTO"
    sp_bara: float = P_HP_BARA
    i_bar_s: float = 0.0
    op_pct: float = PV204_OP_DES_PCT
    #: The PI's bias [%]: PV-329204's design stroke on its trim; V1's ``SUPPLY_BIAS_PCT``.
    bias_pct: float = PV204_OP_DES_PCT
    #: Trip 21.2 on the tick before, and the time left on its set-point pulse [s].
    trip_prev: bool = False
    sp_pulse_s: float = 0.0

    def step(self, p_bara: float, trip_21_2: bool, dt: float) -> float:
        """One tick: trip 21.2's set point, then the PI. Returns PV-329204's stroke [%]."""
        if trip_21_2 and not self.trip_prev:
            self.sp_pulse_s = TRIP_212_SP_PULSE_S
        self.trip_prev = trip_21_2
        if self.sp_pulse_s > 0.0:
            self.sp_bara = TRIP_212_SP_BARA
            self.sp_pulse_s = max(self.sp_pulse_s - dt, 0.0)
        if self.mode == "AUTO":
            e = self.sp_bara - p_bara
            i_max = PIC_329204_I_AUTHORITY_PCT / PIC_329204_KI
            self.i_bar_s = _clamp(self.i_bar_s + e * dt, -i_max, i_max)
            self.op_pct = _clamp(self.bias_pct + PIC_329204_KC * e
                                 + PIC_329204_KI * self.i_bar_s, 0.0, 100.0)
        return self.op_pct


@dataclass
class Hv329601:
    """HIC-329601 and HV-329601: 329D005's vent, the operator's, forced by trip 21.2."""

    hic_pct: float = 0.0
    shut_pulse_s: float = 0.0
    #: Whether the shut-forcing condition held on the tick before; whether the operator is blocked.
    low_prev: bool = False
    blocked: bool = False

    def step(self, p_bara: float, trip_21_2: bool, dt: float) -> float:
        """One tick of sheet 3's logic. Returns HV-329601's stroke [%]."""
        high = p_bara > HV601_FORCE_BARA
        low = trip_21_2 and not high
        if low and not self.low_prev:
            self.shut_pulse_s = HV601_SHUT_PULSE_S
        self.low_prev = low
        if trip_21_2 and high:
            self.hic_pct, self.blocked = 100.0, True
        elif self.shut_pulse_s > 0.0:
            self.hic_pct, self.blocked = 0.0, True
            self.shut_pulse_s = max(self.shut_pulse_s - dt, 0.0)
        else:
            self.blocked = False
        return self.hic_pct


@dataclass
class Pic329205:
    """PIC-329205's split range: PV-329205A admitting, PV-329205B letting down."""

    mode: str = "AUTO"
    sp_bara: float = P_9_SP_BARA
    op_a_pct: float = PV205A_OP_DES_PCT
    op_b_pct: float = 0.0
    #: The plant DCS's PI on PT-329205's span, 3.00 and 50 s (decided 2026-10-28); False is V1's
    #: proportional split about PV-329205A's design stroke.
    table: bool = True
    #: The PI's split [% of a stroke]: PV-329205A's above zero, PV-329205B's below it.
    split_pct: float = PV205A_OP_DES_PCT
    #: The error of the tick before [bar], set point less pressure: reverse acting.
    e_prev: float = 0.0

    def step(self, p_bara: float, dt: float) -> tuple[float, float]:
        """One tick. Returns (PV-329205A, PV-329205B) strokes [%]; MAN holds both, and the PI's
        split tracks them so AUTO takes over bumplessly."""
        e = self.sp_bara - p_bara
        if self.mode == "AUTO":
            if self.table:
                self.split_pct = _clamp(self.split_pct + PIC_329205_KC * (
                    (e - self.e_prev) + (dt / PIC_329205_TI_S) * e), -100.0, 100.0)
                split = self.split_pct
            else:
                split = PV205A_OP_DES_PCT - K_PIC_9 * (p_bara - self.sp_bara)
            if split >= 0.0:
                self.op_a_pct, self.op_b_pct = min(100.0, split), 0.0
            else:
                self.op_a_pct, self.op_b_pct = 0.0, min(100.0, -split)
        else:
            self.split_pct = self.op_a_pct if self.op_a_pct > 0.0 else -self.op_b_pct
        self.e_prev = e
        return self.op_a_pct, self.op_b_pct


@dataclass
class TrioLeg:
    """One leg of the PIC-329207 trio: its mode, set point, integral and output."""

    name: str
    mode: str = "AUTO"
    sp_bara: float = P_LP_BARA
    i_bar_s: float = 0.0
    op_pct: float = 0.0


def _legs(bias_b_pct: float = PV207B_OP_DES_PCT) -> dict:
    """The three legs at design, leg B seeded on its bias."""
    return {"A": TrioLeg("A", sp_bara=P_LP_BARA + DB_LP_BAR),
            "B": TrioLeg("B", sp_bara=P_LP_BARA, op_pct=bias_b_pct),
            "C": TrioLeg("C", sp_bara=P_LP_BARA - DB_LP_BAR)}


@dataclass
class Pic329207:
    """The PIC-329207 trio on its master set point."""

    master_on: bool = True
    master_sp_bara: float = P_LP_BARA
    legs: dict = field(default_factory=_legs)
    #: Leg B's bias [%]: PV-329207B's design stroke on its trim (decided 2026-10-15); V1's
    #: ``BIAS_207B_PCT``, which the equivalence harness keeps.
    bias_b_pct: float = PV207B_OP_DES_PCT

    def step(self, p_bara: float, dt: float) -> tuple[float, float, float]:
        """One tick. Returns the valves' strokes (PV-329207A, PV-329207B, PV-329207C) [%]."""
        a, b, c = self.legs["A"], self.legs["B"], self.legs["C"]
        if self.master_on:
            a.sp_bara = self.master_sp_bara + DB_LP_BAR
            b.sp_bara = self.master_sp_bara
            c.sp_bara = self.master_sp_bara - DB_LP_BAR
            a.mode = b.mode = c.mode = "AUTO"
        if a.mode == "AUTO":
            e = p_bara - a.sp_bara
            a.i_bar_s = _clamp(a.i_bar_s + e * dt, 0.0, 100.0 / PIC_329207_KI["A"])
            a.op_pct = _clamp(PIC_329207_KC["A"] * e + PIC_329207_KI["A"] * a.i_bar_s, 0.0, 100.0)
        if b.mode == "AUTO":
            e = p_bara - b.sp_bara
            i_max = 100.0 / PIC_329207_KI["B"]
            b.i_bar_s = _clamp(b.i_bar_s + e * dt, -i_max, i_max)
            b.op_pct = _clamp(self.bias_b_pct + PIC_329207_KC["B"] * e
                              + PIC_329207_KI["B"] * b.i_bar_s, 0.0, 100.0)
        if c.mode == "AUTO":
            e = c.sp_bara - p_bara
            c.i_bar_s = _clamp(c.i_bar_s + e * dt, 0.0, 100.0 / PIC_329207_KI["C"])
            c.op_pct = _clamp(PIC_329207_KC["C"] * e + PIC_329207_KI["C"] * c.i_bar_s, 0.0, 100.0)
        return a.op_pct, b.op_pct, c.op_pct


@dataclass
class LevelLoop:
    """A drum level loop, velocity-form PI on per cent of level (V1 ``_level_loop``'s control)."""

    tag: str
    direct: bool
    op_pct: float
    mode: str = "AUTO"
    sp_pct: float = LEVEL_SP_DES_PCT
    e_prev: float = 0.0
    #: (gain, integral time [s]) where a harness keeps a tuning the loop no longer runs — V1's for
    #: LIC-329502 (decision 156); None is the loop's row in ``LIC_TUNING``.
    tuning: tuple | None = None

    def step(self, level_pct: float, dt: float) -> float:
        """One tick on the level the transmitter reads. Returns the valve's stroke [%]."""
        kc, ti = self.tuning or LIC_TUNING[self.tag]
        e = (level_pct - self.sp_pct) if self.direct else (self.sp_pct - level_pct)
        if self.mode == "AUTO":
            self.op_pct = _clamp(self.op_pct + kc * ((e - self.e_prev) + (dt / ti) * e),
                                 0.0, 100.0)
        self.e_prev = e
        return self.op_pct


def v1_pic_329204() -> Pic329204:
    """PIC-329204 as V1 seeds it, on V1's PV-329204 (the equivalence harness's)."""
    return Pic329204(op_pct=SUPPLY_BIAS_PCT, bias_pct=SUPPLY_BIAS_PCT)


def v1_pic_329207() -> Pic329207:
    """The PIC-329207 trio as V1 seeds it, on V1's PV-329207B (the equivalence harness's)."""
    return Pic329207(legs=_legs(BIAS_207B_PCT), bias_b_pct=BIAS_207B_PCT)


__all__ = [
    "TRIP_212_SP_PULSE_S", "supply_seed_pct", "SUPPLY_BIAS_PCT", "Pic329204", "Hv329601",
    "Pic329205", "TrioLeg", "Pic329207", "LevelLoop", "v1_pic_329204", "v1_pic_329207",
]
