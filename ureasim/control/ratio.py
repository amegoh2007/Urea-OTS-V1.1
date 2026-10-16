"""Ratio control — a master that commands a ratio and a slave that delivers the flow.

What this models
----------------
The plant's ratio pairs, of which FFIC-335406 -> FIC-335405 (the UF85 additive dosing on the
finishing section) is the one V1 implements in full. The master's PV is not a flow at all: it
is the ACHIEVED RATIO of a dosed stream to a base stream. Its output becomes the slave flow
controller's set point.

`RatioStation` is the other form Uhde's functional diagrams draw, the RATIOSTN block: no
controller, the slave's set point is the ratio set point times the base flow (FFIC-329401 on
the desorbers, decided 2026-09-30, handoff B-49).

Source
------
Ported from V1 ``backend/main.py`` ``step_uf85_cascade``. The tag-specific parts of that
function — the t/h scalings, the LV-324501B recycle permissive, the 335 design constants —
stay with the unit that owns them; what is here is the ratio block itself.

Equations implemented
---------------------
    ratio_PV  = measured_flow / base_flow          (0 when there is no base flow)
    demand    = max(ratio_command . base_flow, 0)

Why a ratio block is not just a multiplication
----------------------------------------------
Two behaviours make it a control block rather than an expression, and both exist to stop the
master winding up against something it cannot influence:

  * **external-reset feedback.** While the slave is NOT in cascade the master has no
    authority: nothing it computes reaches a valve. An integrating controller left running
    in that state ramps to its limit and then dumps that accumulated output onto the plant
    the moment cascade is restored. Instead the master in AUTO TRACKS the achieved ratio, so
    its output is always the ratio the plant is actually making and a transfer to cascade is
    bumpless. A master deliberately left in MAN keeps the operator's number; only its PV
    history is kept current.
  * **freeze on a permissive.** When a hard interlock has zeroed the dosing pump, the ratio
    is zero because the equipment is stopped, not because the controller is failing to hold
    it. The master is frozen rather than stepped, and the measurement is decayed toward zero
    so that no faceplate claims an additive flow that is not being delivered.
"""

from __future__ import annotations

from dataclasses import dataclass

from ureasim.core.numeric import clamp
from ureasim.control.process_loop import ProcessLoop

#: Base flows below this are treated as no flow at all. A ratio against a base flow of a few
#: grams per hour is arithmetic, not a measurement, and it would slam the master's PV.
BASE_FLOW_FLOOR = 1.0e-12

#: The modes a ratio station takes: the operator's output, or the ratio times the base flow.
STATION_MODES = ("MAN", "AUTO")


@dataclass(frozen=True)
class RatioResult:
    """What one tick of a ratio master produced.

    Every field is published to the faceplate, and the three numbers are deliberately kept
    apart: ``measured`` is what the plant is doing, ``command`` is what the master is asking
    for, and ``demand`` is that command turned into a flow for the slave. An operator
    diagnosing a ratio that will not hold reads the gap between the first two.
    """

    #: The achieved ratio, dosed flow over base flow.
    measured: float
    #: The master's output — the ratio it is commanding.
    command: float
    #: The slave's flow set point, ``command . base_flow``, floored at zero.
    demand: float
    #: True when a hard permissive has taken the dosing equipment away from the controller.
    interlocked: bool


@dataclass
class RatioMaster:
    """A ratio controller with external-reset feedback and a permissive freeze.

    Process utility
    ---------------
    The master decides HOW MUCH additive per tonne of product; the slave decides how to get
    that flow through its valve. Splitting them is what lets an operator hold the ratio while
    the plant rate changes, which is the entire point of the arrangement — and it is why the
    master must not be allowed to integrate while the slave is not listening.
    """

    #: The ratio controller. Its PV is a RATIO, and its output limits are ratio limits.
    loop: ProcessLoop

    def step(self, measured_flow: float, base_flow: float, dt: float, *,
             slave_in_cascade: bool, permissive_ok: bool = True) -> RatioResult:
        """Advance one tick.

        Parameters
        ----------
        measured_flow
            The dosed stream's measured flow, in the same unit as ``base_flow``.
        base_flow
            The stream the ratio is taken against, in the same unit as ``measured_flow``.
            Both units cancel, so the ratio is dimensionless whichever is used — but they
            must be the SAME unit, and the caller owns that conversion.
        slave_in_cascade
            Whether the slave flow controller is accepting a remote set point. When it is
            not, the master tracks instead of acting.
        permissive_ok
            False when a hard interlock has taken the dosing equipment out of service. The
            master is then frozen and everything it publishes is zero.
        """
        base = max(float(base_flow), 0.0)
        dosed = max(float(measured_flow), 0.0)
        no_base = base <= BASE_FLOW_FLOOR

        if not permissive_ok or no_base:
            # Interlock override, including while the master is in MAN. Zero the measurement
            # state so no faceplate claims additive flow, and freeze the controller so it
            # does not integrate against a safety permissive it cannot influence.
            self.loop.observe(0.0)
            return RatioResult(measured=0.0, command=self.loop.op, demand=0.0,
                               interlocked=True)

        measured = dosed / base

        if not slave_in_cascade:
            # External-reset feedback. The master has no authority, so an AUTO master follows
            # the ratio the plant is actually making. A master the operator deliberately left
            # in MAN keeps their number; its history is still advanced either way.
            if self.loop.mode == "AUTO":
                self.loop.op = clamp(measured, self.loop.op_lo, self.loop.op_hi)
            self.loop.observe(measured)
            command = self.loop.op
        else:
            command = self.loop.step(measured, dt)

        return RatioResult(measured=measured, command=command,
                           demand=max(command * base, 0.0), interlocked=False)


@dataclass
class RatioStation:
    """A ratio station: the slave's set point is the ratio set point times the base flow.

    Process utility
    ---------------
    The DCS block Uhde draws as RATIOSTN — FFIC-329401 on the desorbers, which holds the LP
    steam to the desorbers' feed. Unlike `RatioMaster` it has no controller: it does not
    integrate on the achieved ratio, it multiplies. The slave flow controller gets its target
    the moment the base flow moves, and the slave alone decides how fast the valve follows.
    The achieved ratio is published beside it, so the operator sees the ratio the plant is
    actually making.

    The station is sequenced on its slave's external set-point status: while the slave is not
    in cascade the station's ratio set point tracks the achieved ratio, so the return to
    cascade hands the slave the flow it already has. Nothing integrates, so nothing winds up.
    In MAN the operator sets the output — the slave's set point — directly.

    Equation
    --------
        OUTP = ratio_sp . base_flow . factor          (clamped to the output limits)

    Source: Uhde's functional diagram UD-MR-329-FF-0002 page 2 (FFIC-329401 RATIOSTN: EXTRATIO
    the measured ratio, MV the base flow, SEQAUTO / SEQE1 the slave's external status).
    """

    tag: str
    #: The ratio set point, and its limits, in the ratio's own units.
    sp: float
    #: The output — the slave's set point — and its limits, in the slave's units.
    op: float
    #: The achieved ratio last seen.
    pv: float
    sp_lo: float = 0.0
    sp_hi: float = 1.0
    op_lo: float = 0.0
    op_hi: float = 100.0
    #: Converts ratio x base flow into the slave's unit (t/m3 x m3/h -> kg/h: 1000).
    factor: float = 1.0
    mode: str = "AUTO"

    def __post_init__(self) -> None:
        if self.mode not in STATION_MODES:
            raise ValueError(f"unknown mode {self.mode!r} for {self.tag}")

    def step(self, measured: float, base_flow: float, *, slave_in_cascade: bool) -> float:
        """Advance one tick and return the output, the slave's set point.

        ``measured`` is the achieved ratio; ``base_flow`` the base stream, in the unit the
        ratio is written against.
        """
        if self.mode == "AUTO":
            if not slave_in_cascade:
                # The slave is not listening: the ratio set point tracks what the plant makes.
                self.sp = clamp(measured, self.sp_lo, self.sp_hi)
            self.op = clamp(self.sp * base_flow * self.factor, self.op_lo, self.op_hi)
        self.pv = measured
        return self.op

    def set_mode(self, mode: str) -> None:
        """Select MAN or AUTO."""
        if mode not in STATION_MODES:
            raise ValueError(f"unknown mode {mode!r} for {self.tag}")
        self.mode = mode

    def set_sp(self, value: float) -> None:
        """Move the ratio set point, clamped to its limits."""
        self.sp = clamp(value, self.sp_lo, self.sp_hi)

    def set_op(self, value: float) -> None:
        """Drive the output by hand, clamped to its limits. Meaningful in MAN."""
        self.op = clamp(value, self.op_lo, self.op_hi)

    def as_packet(self) -> dict:
        """The four fields a faceplate renders."""
        return {"mode": self.mode, "pv": self.pv, "sp": self.sp, "op": self.op}


def ratio_demand(ratio_sp: float, base_flow: float, factor: float = 1.0) -> float:
    """Flow demand from a ratio set point [same unit as ``base_flow``].

    Process utility
    ---------------
    The open-loop half of ratio control, used where the ratio is a set point rather than a
    controlled variable — the N/C ratio on the synthesis feed, where the operator dials a
    molar ratio and the ammonia pumps are asked for the mass flow that delivers it.

    ``factor`` converts the ratio's own basis into the flow's. For N/C it is
    ``M_NH3 / M_CO2``, because a molar ratio commanding a mass flow has to cross that bridge:

        m_NH3 = (N/C) . (M_NH3 / M_CO2) . m_CO2

    Equation
    --------
        demand = ratio_sp . factor . base_flow
    """
    return ratio_sp * factor * base_flow


__all__ = [
    "BASE_FLOW_FLOOR",
    "STATION_MODES",
    "RatioResult",
    "RatioMaster",
    "RatioStation",
    "ratio_demand",
]
