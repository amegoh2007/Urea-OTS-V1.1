"""Regulatory DCS controller — velocity-form I-PD with MAN / AUTO / CAS / OOS modes.

What this models
----------------
Every single-loop controller on the plant's DCS: the flow, level, pressure and temperature
controllers the trainee drives from a faceplate. One instance per tag (FIC-322401,
LIC-323501, PIC-324203, ...). The controller decides the valve DEMAND in per cent; what the
valve then passes is :mod:`ureasim.control.valve`'s answer, and whether the plant accepts it
is the engine's.

Source
------
Ported verbatim from V1 ``backend/controllers.py``. Tuning constants for each tag live in
``ureasim.data``, sourced per tag, never invented here.

Equations implemented
---------------------
Velocity I-PD increment, before direction, slew limit and output clamp::

    du_k = Kc . [ -(PV_k - PV_{k-1})
                  + (dt/Ti).(SP_k - PV_k)
                  - Td.(PV_k - 2.PV_{k-1} + PV_{k-2})/dt ]

applied in :meth:`Controller.step` as::

    du_k <- clamp(sigma . du_k, -rate.dt, +rate.dt)      slew limit
    u_k  <- clamp(u_{k-1} + du_k, u_lo, u_hi)            output clamp / anti-windup

with sigma = +1 for REVERSE action and -1 for DIRECT action; Kc is always positive.

Why the velocity form, and why I-PD
-----------------------------------
Two properties matter for a training simulator and both come from this structure:

  * **Velocity form.** The controller stores only the last two PV samples, never an integral
    accumulator. There is therefore nothing to wind up: when the output clamps at 0 % or
    100 %, the increment that would have pushed it further is simply discarded, and the
    controller resumes the instant the error reverses. An operator who has been taught to
    "wait for the integral to unwind" on a simulator that does accumulate would wait for
    something this plant's DCS does not do.
  * **I-PD (proportional and derivative on PV, integral on error).** A set-point change
    moves only the integral term, so the valve does not kick. That is what makes a set-point
    step on a real faceplate look gentle and a load disturbance look sharp — the distinction
    a trainee is being taught to read.

Neither is a modelling preference. Both are what the installed DCS does.
"""

from __future__ import annotations

import math

from ureasim.core.numeric import clamp

#: Below this the PV is declared bad/failed [%]. Source: V1 `backend/controllers.py`.
BAD_PV_LO = -5.0

#: Above this the PV is declared bad/failed [%]. Source: V1 `backend/controllers.py`.
BAD_PV_HI = 105.0

#: Maximum magnitude of the cascade bias [%] — a full set-point-span offset. This is the
#: anti-saturation clamp of V1 finding P1-1: without it a primary controller that has run
#: away can bias a secondary's set point outside its own range and the loop never recovers.
CAS_BIAS_LIM = 100.0

#: The modes a faceplate may select. OOS ("out of service") is the maintenance state: the
#: controller drives its output to the configured fail position and stops regulating.
MODES = ("MAN", "AUTO", "CAS", "OOS")

#: Fail actions. FC drives the output to its low limit (fail-closed), FO to its high limit
#: (fail-open), FL freezes it where it stands (fail-last).
FAIL_ACTIONS = ("FC", "FO", "FL")


class PID:
    """The velocity I-PD increment generator. P and D act on PV, I acts on error.

    Process utility
    ---------------
    This class is the arithmetic only: it returns a delta-u before direction (sigma), before
    the slew limit and before the output clamp. Everything that makes a controller behave
    like an INSTRUMENT rather than an equation — modes, bumpless transfer, bad-PV handling,
    output limits — belongs to :class:`Controller`. Keeping the two apart is what lets the
    increment be tested against V1 sample by sample.

    It stores only PV_{k-1} and PV_{k-2}. There is no integral accumulator, so there is
    nothing to wind up.
    """

    def __init__(self, Kc: float, Ti: float, Td: float = 0.0,
                 Tf: float = 0.0, Dz: float = 0.0):
        """Tuning, in the DCS's own symbols.

        Parameters
        ----------
        Kc
            Proportional gain [% output / % input]. Always positive; the direction of action
            is sigma, applied by :class:`Controller`.
        Ti
            Integral time [s]. Smaller is more aggressive.
        Td
            Derivative time [s]. Zero on every flow loop on this plant — derivative on a
            noisy flow measurement amplifies the noise into the valve.
        Tf
            Derivative first-order filter time [s]. Zero leaves the classic unfiltered
            second-difference form, which is inert by default.
        Dz
            Error deadzone half-width, in engineering units of the PV. Zero disables it. A
            deadzone stops a controller hunting on a measurement that is quantised or noisy
            at the last digit, at the price of a permanent offset inside the band.
        """
        self.Kc = Kc
        self.Ti = Ti
        self.Td = Td
        self.Tf = Tf
        self.Dz = Dz
        self._pv1: float | None = None      # PV_{k-1}
        self._pv2: float | None = None      # PV_{k-2}
        self._dfilt: float = 0.0            # G_{k-1}: filtered position-derivative, per unit Kc

    def reset(self) -> None:
        """Clear the PV history so the next step behaves like a fresh start.

        Process utility
        ---------------
        Called on every bumpless mode transfer. Without it the first increment after a
        transfer would be computed against a PV sample from before the operator intervened,
        which shows up on the plant as a kick out of the valve at the moment of handover.
        """
        self._pv1 = None
        self._pv2 = None
        self._dfilt = 0.0

    def step(self, sp: float, pv: float, dt: float) -> float:
        """One increment, delta-u = Kc.(P + I + D).

        The first call seeds PV_{k-1} = PV_{k-2} = PV so that P and D are both zero and the
        controller starts on pure integral action — a warm-up, not a kick.
        """
        if self._pv1 is None:
            self._pv1 = pv
        if self._pv2 is None:
            self._pv2 = pv

        # Proportional on PV: a set-point change does not appear here, which is the whole
        # point of the I-PD arrangement.
        p = -(pv - self._pv1)

        # Integral on error, with the optional deadzone. Dz = 0 makes `abs(err) < 0` never
        # true, so the default is inert rather than a special case.
        err = sp - pv
        i = 0.0 if abs(err) < self.Dz else (dt / max(self.Ti, 1e-9)) * err

        # Derivative on PV. Tf <= 0 gives the unfiltered second-difference velocity form.
        # Tf > 0 gives a first-order-filtered position-derivative G_k whose velocity
        # increment is G_k - G_{k-1}; it collapses exactly to the unfiltered term as Tf -> 0.
        #     G_k = Tf/(Tf+dt).G_{k-1} - Td/(Tf+dt).(PV_k - PV_{k-1})
        # Kc is applied on return, so G is carried per unit of gain and a tuning change does
        # not disturb the filter state.
        if dt <= 0:
            d = 0.0
        elif self.Tf <= 0.0:
            d = -self.Td * (pv - 2.0 * self._pv1 + self._pv2) / dt
        else:
            g_prev = self._dfilt
            g_k = ((self.Tf / (self.Tf + dt)) * g_prev
                   - (self.Td / (self.Tf + dt)) * (pv - self._pv1))
            d = g_k - g_prev
            self._dfilt = g_k

        self._pv2 = self._pv1
        self._pv1 = pv
        return self.Kc * (p + i + d)


class Controller:
    """A regulatory loop as the operator sees it: a faceplate with modes and limits.

    Process utility
    ---------------
    This is the object a trainee manipulates. Its behaviour on a mode change, on a failed
    transmitter and at its output limits is as much of the training content as the tuning
    is — arguably more, because those are the situations in which an operator has to decide
    something.

    Operator writes
        :meth:`set_mode`, :meth:`set_sp`, :meth:`set_op`, :meth:`set_bias`,
        :meth:`set_tuning`.
    Engine writes
        :meth:`step`, once per simulation tick.

    Which of those a given station may call is decided by ``ureasim.net``, on the station's
    role. Whether the plant then honours the result is decided by the engine. This class
    enforces neither — it is the instrument, not the permission system and not the process.
    """

    def __init__(
        self,
        tag: str,
        *,
        Kc: float = 2.0,
        Ti: float = 8.0,
        Td: float = 0.0,
        Tf: float = 0.0,
        Dz: float = 0.0,
        action: str = "REVERSE",     # "REVERSE" -> sigma = +1 | "DIRECT" -> sigma = -1
        op_lo: float = 0.0,
        op_hi: float = 100.0,
        sp_lo: float = 0.0,
        sp_hi: float = 100.0,
        rate: float = 10.0,          # maximum output slew rate [%/s]
        fail_action: str = "FC",
        sp: float | None = None,     # initial SP, defaulting to midrange
        mv: float | None = None,     # initial MV, defaulting to the low output limit
    ):
        """Configure one loop.

        ``action`` is the sign of the loop, not of the gain: a level controller on a
        discharge valve is DIRECT (rising level opens the valve) while the same controller on
        a feed valve is REVERSE. Getting it wrong does not detune the loop, it makes it
        diverge, which is why it is configuration and never inferred.

        ``rate`` is the output slew limit in per cent per second. It is what stops a
        large increment slamming a valve, and it is also what makes a controller look
        sluggish if it is set too low — both are real plant behaviours.
        """
        self.tag = tag
        self.action = action
        self.op_lo, self.op_hi = op_lo, op_hi
        self.sp_lo, self.sp_hi = sp_lo, sp_hi
        self.rate = rate
        self.fail_action = fail_action
        self._pid = PID(Kc=Kc, Ti=Ti, Td=Td, Tf=Tf, Dz=Dz)

        self.mode: str = "MAN"
        self.sp: float = sp if sp is not None else (sp_lo + sp_hi) / 2.0
        self.mv: float = mv if mv is not None else op_lo
        self.pv: float = 0.0
        self.bias: float = 0.0
        self.cas_sp: float | None = None

        self._pv_bad: bool = False
        self._mv_hi_clamp: bool = False
        self._mv_lo_clamp: bool = False

    # -- tuning read-back ---------------------------------------------------------------
    # The faceplate displays the tuning; it does not own it. These are read-only views onto
    # the PID so there is exactly one copy of each constant.

    @property
    def Kc(self) -> float:
        return self._pid.Kc

    @property
    def Ti(self) -> float:
        return self._pid.Ti

    @property
    def Td(self) -> float:
        return self._pid.Td

    @property
    def Tf(self) -> float:
        return self._pid.Tf

    @property
    def Dz(self) -> float:
        return self._pid.Dz

    def _sigma(self) -> float:
        """Direction of action: +1 REVERSE, -1 DIRECT."""
        return 1.0 if self.action == "REVERSE" else -1.0

    def _fail_target(self) -> float:
        """Where the output goes when the loop is taken out of service."""
        if self.fail_action == "FC":
            return self.op_lo
        if self.fail_action == "FO":
            return self.op_hi
        return self.mv          # FL: freeze at the current MV

    # -- operator commands --------------------------------------------------------------

    def set_mode(self, mode: str) -> None:
        """Select MAN, AUTO, CAS or OOS, bumplessly.

        Process utility
        ---------------
        Both transfers below are bumpless, and each is bumpless in a different way:

          * **into AUTO**, the set point adopts the current PV, so the controller starts with
            zero error and holds the plant where the operator left it. A faceplate that
            jumped to a stored set point would move the plant at the moment of handover.
          * **into CAS**, the bias is zeroed, so the secondary starts at exactly the set
            point the primary is asking for rather than at that plus whatever offset was left
            from the last time cascade was used.

        Both reset the PID history for the reason given in :meth:`PID.reset`.
        """
        if mode not in MODES:
            raise ValueError(f"unknown mode {mode!r}")
        if mode == "AUTO" and self.mode != "AUTO":
            self.sp = clamp(self.pv, self.sp_lo, self.sp_hi)
            self._pid.reset()
        if mode == "CAS" and self.mode != "CAS":
            self.bias = 0.0
            self._pid.reset()
        self.mode = mode

    def set_sp(self, v: float) -> None:
        """Move the set point, clamped to [sp_lo, sp_hi]. Meaningful in AUTO."""
        self.sp = clamp(v, self.sp_lo, self.sp_hi)

    def set_op(self, v: float) -> None:
        """Drive the output by hand, clamped to [op_lo, op_hi]. Meaningful in MAN."""
        self.mv = clamp(v, self.op_lo, self.op_hi)

    def set_bias(self, v: float) -> None:
        """Offset the cascade set point, clamped to +/-CAS_BIAS_LIM. Meaningful in CAS.

        The clamp is V1 finding P1-1: an unbounded bias lets a saturated primary push the
        secondary's set point out of range permanently.
        """
        self.bias = clamp(v, -CAS_BIAS_LIM, CAS_BIAS_LIM)

    def set_tuning(self, *, Kc: float | None = None, Ti: float | None = None,
                   Td: float | None = None, Tf: float | None = None,
                   Dz: float | None = None) -> None:
        """Change tuning without disturbing the output. Legal in any mode.

        The velocity form is what makes this bumpless: the gain multiplies an INCREMENT, so
        a new Kc changes the next move and not the current position. A positional controller
        would step its output the instant the gain changed.
        """
        if Kc is not None:
            self._pid.Kc = Kc
        if Ti is not None:
            self._pid.Ti = Ti
        if Td is not None:
            self._pid.Td = Td
        if Tf is not None:
            self._pid.Tf = Tf
        if Dz is not None:
            self._pid.Dz = Dz

    # -- simulation tick ----------------------------------------------------------------

    def step(self, pv: float | None, dt: float, cas_sp: float | None = None) -> float:
        """Advance one simulation tick and return the current MV [%].

        Process utility
        ---------------
        The bad-PV guard at the top is the instrument-failure behaviour, and it is training
        content in its own right. A transmitter that fails — reading None, NaN, or outside
        [-5, 105] % of span — puts the loop into MAN and FREEZES the output at its last good
        value. It does not drive the valve shut, and it does not keep regulating on a lie.
        The operator finds a loop in MAN that they did not put there, which is exactly the
        cue they must learn to recognise.
        """
        # A NaN PV is what a diverging plant produces, so it is tested explicitly rather than
        # left to the comparisons below, which are all False for a NaN.
        bad = (pv is None
               or (isinstance(pv, float) and math.isnan(pv))
               or pv < BAD_PV_LO or pv > BAD_PV_HI)
        if bad:
            self._pv_bad = True
            if self.mode != "MAN":
                self.mode = "MAN"
                self._pid.reset()
            return self.mv          # freeze the last good MV

        self._pv_bad = False
        self.pv = pv
        self.cas_sp = cas_sp
        slew_max = self.rate * dt

        if self.mode == "MAN":
            pass                    # output held; the operator moves it with set_op()

        elif self.mode == "AUTO":
            raw = self._sigma() * self._pid.step(self.sp, pv, dt)
            delta = clamp(raw, -slew_max, slew_max)
            new_mv = clamp(self.mv + delta, self.op_lo, self.op_hi)
            self._mv_hi_clamp = (new_mv >= self.op_hi)
            self._mv_lo_clamp = (new_mv <= self.op_lo)
            self.mv = new_mv

        elif self.mode == "CAS":
            # The primary's output becomes this loop's set point, offset by the bias and
            # clamped to this loop's own SP range — a secondary never accepts a set point
            # outside the span it is configured for, however hard the primary pushes.
            if cas_sp is not None:
                self.sp = clamp(cas_sp + self.bias, self.sp_lo, self.sp_hi)
            raw = self._sigma() * self._pid.step(self.sp, pv, dt)
            delta = clamp(raw, -slew_max, slew_max)
            new_mv = clamp(self.mv + delta, self.op_lo, self.op_hi)
            self._mv_hi_clamp = (new_mv >= self.op_hi)
            self._mv_lo_clamp = (new_mv <= self.op_lo)
            self.mv = new_mv

        elif self.mode == "OOS":
            # Out of service: ramp to the fail position at the same slew rate a live output
            # would use, so the valve travel looks the same as any other move.
            target = self._fail_target()
            delta = clamp(target - self.mv, -slew_max, slew_max)
            self.mv = clamp(self.mv + delta, self.op_lo, self.op_hi)

        return self.mv

    def as_packet(self) -> dict:
        """The faceplate's published state, in V1's exact key order.

        Process utility
        ---------------
        This is everything a faceplate renders and nothing else: it is a snapshot, not a
        handle. A console reads it and draws it; it never writes back through it, and it
        never recomputes a field from the others. Two stations looking at the same tag are
        looking at the same dictionary.

        The three status flags are the annunciation an operator reads before anything else:
        a bad PV, and whether the output is sitting on a limit. A controller pinned at 100 %
        is not controlling, and the faceplate has to say so.
        """
        return {
            "mode": self.mode,
            "pv": self.pv,
            "sp": self.sp,
            "mv": self.mv,
            "cas_sp": self.cas_sp,
            "bias": self.bias,
            "action": self.action,
            "tuning": {
                "Kc": self._pid.Kc,
                "Ti": self._pid.Ti,
                "Td": self._pid.Td,
                "Tf": self._pid.Tf,
                "Dz": self._pid.Dz,
            },
            "limits": {
                "op_lo": self.op_lo, "op_hi": self.op_hi,
                "sp_lo": self.sp_lo, "sp_hi": self.sp_hi,
                "rate": self.rate,
            },
            "fail_action": self.fail_action,
            "status": {
                "pv_bad": self._pv_bad,
                "mv_hi_clamp": self._mv_hi_clamp,
                "mv_lo_clamp": self._mv_lo_clamp,
            },
        }


__all__ = [
    "BAD_PV_LO",
    "BAD_PV_HI",
    "CAS_BIAS_LIM",
    "MODES",
    "FAIL_ACTIONS",
    "PID",
    "Controller",
]
