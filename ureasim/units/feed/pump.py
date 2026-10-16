"""321P002 A/B — HP ammonia feed pumps, triplex reciprocating.

What this models
----------------
The two positive-displacement plunger pumps that put fresh liquid ammonia into the synthesis
loop, and the VOITH torque-converter scoop that sets their speed. One is running and one is
the stopped standby; which is which is an operator decision.

Source
------
Ported from V1 ``backend/main.py``: the module docstring's pump physics, `pump_flow_m3h`,
`pump_shaft_power_kW`, `pump_current_A`, `mode_tag`, and the per-pump loop inside `step_sim`.

Why a positive-displacement machine has no map
-----------------------------------------------
A centrifugal machine trades head against flow, so it needs a characteristic. A triplex
plunger pump does not: it sweeps a fixed volume
per revolution and delivers it against whatever pressure the discharge happens to be at, up
to its own relief valve. So the flow is a function of SPEED alone, and the discharge pressure
is set by what is downstream — never by the pump.

That has a direct training consequence. On a centrifugal feed pump an operator can throttle
the discharge to trim the flow. Here they cannot: closing the discharge valve on a running
plunger pump raises the pressure until something gives. Flow is changed by changing speed,
and only by changing speed.

Equations implemented
---------------------
    V_swept = (pi/4) D^2 L n_plungers                    [m3/rev]
    Q       = N . V_swept . eta_v . 60                   [m3/h]
    P_shaft = Q . dP / eta_m                             [kW]
    I       = (N / N_rated) . I_rated                    [A], floored at the live zero
    N       = (opening / 100) . N_rated                  the scoop
"""

from __future__ import annotations

from dataclasses import dataclass

from ureasim.control.controller import Controller
from ureasim.core.numeric import clamp
from ureasim.data.unit_321 import (
    PUMP_ETA_M,
    PUMP_ETA_V,
    PUMP_IDLE_I,
    PUMP_RATED_I,
    PUMP_RATED_RPM,
    PUMP_SCOOP_TAU_S,
    PUMP_V_PER_REV,
)

#: Faceplate mode letters, as V1's HMI renders them. E is cascade ("external").
MODE_LETTER = {"MAN": "M", "AUTO": "A", "CAS": "E", "OOS": "O"}


def flow_m3h(speed_rpm: float) -> float:
    """Volumetric delivery at a given speed [m3/h].

    Process utility
    ---------------
    The whole pump. Everything else in this module is instrumentation around this line: a
    plunger pump's delivery is its swept volume times its speed times how much of each stroke
    it actually keeps.

    Negative speeds return zero rather than a negative flow — a reversing plunger pump is not
    a model, it is a broken machine, and it needs its own failure case rather than a sign.
    """
    return max(0.0, speed_rpm) * PUMP_V_PER_REV * PUMP_ETA_V * 60.0


def shaft_power_kw(speed_rpm: float, dp_bar: float) -> float:
    """Shaft power absorbed [kW].

    Process utility
    ---------------
    A display and a motor-loading check. It is the hydraulic power divided by the mechanical
    efficiency, so it rises linearly with both speed and differential — which is why a
    blocked discharge on a positive-displacement pump trips the motor rather than simply
    stopping the flow.

    Equation
    --------
        P = Q[m3/s] . dP[Pa] / eta_m / 1000
    """
    q_m3s = flow_m3h(speed_rpm) / 3600.0
    return (q_m3s * dp_bar * 1e5) / PUMP_ETA_M / 1000.0


def current_a(speed_rpm: float, running: bool) -> float:
    """Motor current [A].

    Process utility
    ---------------
    A display proxy, anchored on the DCS reading of 43.9 A at 131 rpm. A STOPPED machine
    reads the instrument's live zero, not nothing: an ammeter reading exactly 0.000 is a dead
    instrument, and the operator should be able to tell the two apart on the faceplate.
    """
    if not running:
        return PUMP_IDLE_I
    return max(PUMP_IDLE_I, (max(0.0, speed_rpm) / PUMP_RATED_RPM) * PUMP_RATED_I)


@dataclass
class ReciprocatingPump:
    """One 321P002 machine and its torque-converter scoop.

    Process utility
    ---------------
    The state an operator can see and change: whether the machine is running, where its
    converter opening actually is, what speed that gives, and what the ammeter reads. The
    opening is the CONTROLLED variable — SIC-321950/951 command an opening in per cent, and
    the speed is derived from it — because that is what the VOITH scoop presents to the DCS.

    ``fault`` is the instructor's equipment-fault handle. V1 abstracted the lube-oil fluid
    dynamics away deliberately: trips 21.8 and 21.10 fire on this boolean rather than on a
    continuous lube-oil pressure, because what the trainee has to learn is the response to the
    trip, not the hydraulics of a bearing.
    """

    tag: str
    #: True when the machine is running. An operator start/stop, or a latched trip.
    running: bool = False
    #: Actual torque-converter opening [%] — the SIC's PV.
    opening_pct: float = 0.0
    #: Derived shaft speed [rpm].
    speed_rpm: float = 0.0
    #: Motor current [A].
    current: float = PUMP_IDLE_I
    #: Instructor-set equipment fault. Arms trip 21.8 / 21.10 while the machine runs.
    fault: bool = False
    #: Faceplate mode letter, mirrored from the controller each tick.
    mode_letter: str = "M"

    def step(self, controller: Controller, dt: float, *,
             suction_open: bool, discharge_open: bool,
             cas_sp: float | None = None) -> float:
        """Advance the machine one tick and return its delivered flow [m3/h].

        Process utility
        ---------------
        Three behaviours here are plant behaviour rather than bookkeeping:

          * **a stopped machine forces its controller to MAN.** A SIC in AUTO or CAS sitting
            on a dead pump winds its output against a PV that cannot move, and the ratio
            cascade would be commanding a speed to a machine that is not turning. The
            operator picks AUTO or CAS again once it is running — the faceplate greys those
            buttons while it is stopped, so the choice is never silently reverted.
          * **an isolated machine goes to zero opening, not zero flow.** Shutting XV-321901 or
            XV-322901 drives the scoop closed; the converter then takes its own two seconds to
            get there. Zeroing the flow while leaving the opening up would show an operator a
            machine at 80 % passing nothing.
          * **the scoop lags.** ``alpha = min(1, dt/tau)`` is a first-order approach with the
            step capped at one, so even a very long tick cannot overshoot the target.

        At the design seed pump A is the stopped standby ALREADY in MAN with its output at
        zero, so the forced-manual branch never fires and the design fixed point is untouched.
        """
        if (not self.running) and controller.mode != "MAN":
            controller.set_mode("MAN")      # forced-manual on a stopped machine
            controller.set_op(0.0)          # and its output drops with it

        # The controller's PV is the ACTUAL opening, not the commanded one, so the scoop lag
        # below is inside the loop and the SIC has to drive through it.
        controller.step(self.opening_pct, dt, cas_sp=cas_sp)
        target = 0.0 if (not self.running or not suction_open or not discharge_open) \
            else controller.mv

        alpha = min(1.0, dt / PUMP_SCOOP_TAU_S)
        self.opening_pct = clamp(self.opening_pct + (target - self.opening_pct) * alpha,
                                 0.0, 100.0)
        self.speed_rpm = self.opening_pct / 100.0 * PUMP_RATED_RPM
        self.current = current_a(self.speed_rpm, self.running)
        self.mode_letter = MODE_LETTER.get(controller.mode, "M")
        return flow_m3h(self.speed_rpm) if self.running else 0.0

    def as_packet(self) -> dict:
        """The pump tile's published state, in V1's key order."""
        return {"on": self.running, "open_act": self.opening_pct,
                "speed_act": self.speed_rpm, "current": self.current,
                "mode": self.mode_letter, "fault": self.fault}


__all__ = [
    "MODE_LETTER",
    "flow_m3h",
    "shaft_power_kw",
    "current_a",
    "ReciprocatingPump",
]
