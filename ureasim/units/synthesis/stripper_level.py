"""LIC-322501 — the 322E001 bottom-solution level controller, on the plant DCS's tuning.

What this models
----------------
The controller that holds LT-322501's sump at its set point by stroking LV-322501, the HP loop's
main product outlet: a direct-acting velocity-form PID on the level whose proportional term acts
on the error, so a set-point move kicks the valve as the plant's DCS does (the class docstring).
`stripper_sump.StripperSump` steps it on the level at the top of each tick.

Source: V1 ``backend/main.py`` ``step_sim``, the 322E001 bottom-sump block; the tuning is the
plant DCS's (`References/Master_PID_Tuning_Constants.md`, decided 2026-10-08). Moved here from
`stripper_sump` unchanged (2026-10-22, session 64) to keep that module inside its line target.
"""

from __future__ import annotations

from dataclasses import dataclass

from ureasim.control.process_loop import pv_ok
from ureasim.core.numeric import clamp
from ureasim.data.unit_322e001 import (
    LEVEL_SP_DES_PCT,
    LIC_322501_KC,
    LIC_322501_TD_S,
    LIC_322501_TF_S,
    LIC_322501_TI,
    LV_322501_OPEN_DES_PCT,
)

__all__ = ["BottomLevelLoop"]


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
