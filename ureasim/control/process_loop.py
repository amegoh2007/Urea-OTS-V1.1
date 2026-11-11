"""The engineering-unit regulatory loop — the controller almost every tag on this plant uses.

Why there are two controllers in this package
---------------------------------------------
V1 carries two I-PD implementations and uses both. They are NOT duplicates, and they are not
merged here, because they behave differently in four ways that an operator can see:

============================  ==========================  ==============================
                              :class:`ProcessLoop`         :class:`~.controller.Controller`
                              (V1 ``main.py _ctrl_ipd``)   (V1 ``backend/controllers.py``)
============================  ==========================  ==============================
PV units                      engineering (C, bar a,      per cent of span
                              % level, t/h)
Bad-PV test                   non-finite only             non-finite **or** outside
                                                          [-5, 105] % of span
On a bad PV                   freeze the output, stay     freeze the output **and drop
                              in the current mode         the loop to MAN**
Output slew limit             none                        rate . dt per tick
Modes                         MAN / AUTO / CAS            MAN / AUTO / CAS / OOS
Td < 0                        sentinel: derivative off    used as given
PV history while in MAN       kept current                frozen
============================  ==========================  ==============================

Every loop on the plant except SIC-321950 and SIC-321951 (the NH3 pump speed controllers,
whose PV genuinely is a percentage) is a :class:`ProcessLoop`. Unifying the two would change
the behaviour of one set or the other, which §5 of the agent directives forbids.

The two most consequential rows are the last two but one. A temperature loop reading 135 C is
outside [-5, 105] and must not be declared bad — that is why the engineering-unit form exists
at all. And a loop that keeps its PV history current while in MAN resumes on the operator's
actual last two samples when it is put back in AUTO, instead of on a reset.

Source
------
Ported verbatim from V1 ``backend/main.py`` ``_pv_ok``, ``_ctrl_ipd`` and ``_fic_flow``.

Equations implemented
---------------------
Velocity I-PD, in engineering units::

    du = act . Kc . [ -(PV_k - PV_{k-1}) + I(SP, PV) + D(PV) ]
    I  = 0 if |SP - PV| < Dz else (dt/Ti).(SP - PV)
    D  = -Td.(PV_k - 2.PV_{k-1} + PV_{k-2})/dt                   Tf <= 0, unfiltered
       = G_k - G_{k-1},  G_k = Tf/(Tf+dt).G_{k-1}
                               - Td/(Tf+dt).(PV_k - PV_{k-1})    Tf > 0, filtered
    OP = clamp(OP + du, op_lo, op_hi)

and, for a flow loop closed around its valve at a fixed differential::

    flow_pre = design . f(OP_{k-1}) / f(OP_des)
    PV       = first_order_lag(flow_pre, tau)
    flow     = design . f(OP_k) / f(OP_des)

where f is the valve trim's `control.valve.cv_fraction`. A linear trim — V1's, everywhere — is
written as V1 writes it, design . (OP / OP_des).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import ClassVar

from ureasim.control.valve import cv_fraction
from ureasim.core.numeric import clamp
from ureasim.core.signal import first_order_lag

#: The modes an engineering-unit loop supports. There is no OOS here: these loops have no
#: faceplate fail position in V1, and inventing one would invent operator behaviour.
MODES = ("MAN", "AUTO", "CAS")


def pv_ok(*values: object) -> bool:
    """True when every value is a finite real number.

    Process utility
    ---------------
    The bad-measurement test for an engineering-unit loop. It asks only whether the number
    is a number — NOT whether it lies inside a percentage span, because a reactor at 183 C
    and a synthesis loop at 144 bar a are both perfectly good readings far outside [0, 100].

    The set point is passed in alongside the PV wherever a loop's set point is itself
    computed, so a cascade master that has diverged freezes the secondary instead of driving
    it with a NaN.
    """
    return all(isinstance(v, (int, float)) and math.isfinite(v) for v in values)


@dataclass
class ProcessLoop:
    """One regulatory loop working in the PV's own engineering units.

    Process utility
    ---------------
    This is the object behind almost every faceplate on the plant: LIC-323501 on a level in
    per cent, TIC-329007 on a temperature in C, PIC-324203 on a pressure in bar a,
    FIC-324401 on a flow in t/h. Its output is a valve demand in per cent, which
    :mod:`ureasim.control.valve` turns into a flow.

    Seeding
    -------
    Every loop is seeded ``pv == sp == pv1 == pv2`` at its design point, so the first tick
    computes ``du == 0`` and the boot fixed point is preserved bit-exact. That is not a
    convenience — it is how the whole flowsheet stays pinned to the PFD at t = 0.
    """

    tag: str
    #: Proportional gain, always positive; ``act`` carries the direction.
    Kc: float
    #: Integral time [s]. There is deliberately no divide-by-zero guard: V1 has none, and a
    #: loop configured with Ti = 0 is a configuration error that should be loud.
    Ti: float
    #: Derivative time [s]. **-1 is the DCS sentinel for "derivative disabled"** and is
    #: honoured as such; see :meth:`step`.
    Td: float = -1.0
    #: Direction of action: +1 REVERSE (output rises as PV falls below SP), -1 DIRECT.
    act: float = 1.0
    op: float = 0.0
    sp: float = 0.0
    pv: float = 0.0
    pv1: float = 0.0
    pv2: float = 0.0
    op_lo: float = 0.0
    op_hi: float = 100.0
    sp_lo: float = 0.0
    sp_hi: float = 100.0
    mode: str = "AUTO"
    #: Derivative first-order filter time [s]. <= 0 leaves the unfiltered second-difference
    #: form, which is the default everywhere on this plant.
    Tf: float = 0.0
    #: Error deadzone half-width in the PV's engineering units. 0 disables it.
    Dz: float = 0.0
    #: Filtered-derivative state G_{k-1}, carried per unit of Kc so a tuning change does not
    #: disturb it.
    dfilt: float = 0.0
    #: Through a bad PV the history is unknown and the first good sample reseeds it (decided
    #: 2026-11-11, decision 186, handoff B-130); False is V1's step on recovery. A class switch,
    #: so a saved exercise keeps its shape.
    reseed_after_bad: ClassVar[bool] = True

    def __post_init__(self) -> None:
        if self.mode not in MODES:
            raise ValueError(f"unknown mode {self.mode!r} for {self.tag}")

    def step(self, pv: float, dt: float, cas_sp: float | None = None) -> float:
        """Advance one simulation tick and return the output [%].

        Process utility
        ---------------
        Three behaviours in this method are training content rather than arithmetic:

          * **a bad measurement freezes the output** at its last good value and leaves the
            loop in the mode the operator put it in. It does not slam the valve and it does
            not silently take itself off; the operator sees a frozen indication, which is the
            symptom they must learn to read.
          * **a cascade set point is clamped to this loop's own span.** A secondary never
            accepts a set point outside the range it is configured for, however hard a
            saturated primary pushes.
          * **in MAN the PV history is still advanced.** The loop is watching even while it
            is not acting, so putting it back into AUTO resumes on the two samples that
            actually just happened.
          * **the first good sample after a bad one reseeds the history** (B-130). The two
            samples before it are unknown, so the loop acts on its integral alone that tick
            instead of stepping its output by Kc times the PV's move through the outage, which
            is V1's behaviour and ``reseed_after_bad = False``.
        """
        if not pv_ok(pv, self.sp):
            if self.reseed_after_bad:
                self.pv1 = self.pv2 = math.nan                # the history through it is unknown
            return clamp(self.op, self.op_lo, self.op_hi)    # freeze last good on a bad PV
        if self.reseed_after_bad and not (math.isfinite(self.pv1) and math.isfinite(self.pv2)):
            self.pv1 = self.pv2 = pv                         # reseed on the first good sample

        if self.mode == "CAS" and cas_sp is not None:
            self.sp = clamp(cas_sp, self.sp_lo, self.sp_hi)  # remote set point from the master

        pv1, pv2 = self.pv1, self.pv2
        if self.mode in ("AUTO", "CAS"):
            # Proportional on PV: a set-point move does not appear here.
            p = -(pv - pv1)

            # Integral on error, with the optional deadzone. Dz = 0 makes the test never
            # true, so the default is inert rather than a special case.
            err = self.sp - pv
            i = 0.0 if abs(err) < self.Dz else (dt / self.Ti) * err

            # Td sentinel decode. The DCS writes Td = -1 to mean "derivative disabled". A
            # negative derivative time is non-physical and, unguarded, flips the sign of the
            # D term, injecting a wrong-way kick on every transient. Clamping < 0 to 0
            # honours the sentinel exactly.
            td = self.Td
            if td < 0.0:
                td = 0.0

            tf = self.Tf
            if dt <= 0.0:
                d = 0.0
            elif tf <= 0.0:
                d2 = (pv - 2.0 * pv1 + pv2) / dt
                d = -td * d2
            else:
                g_prev = self.dfilt
                g_k = (tf / (tf + dt)) * g_prev - (td / (tf + dt)) * (pv - pv1)
                d = g_k - g_prev
                self.dfilt = g_k

            du = self.act * self.Kc * (p + i + d)
            self.op = clamp(self.op + du, self.op_lo, self.op_hi)

        self.pv2 = pv1
        self.pv1 = pv
        self.pv = pv
        return self.op

    def observe(self, pv: float) -> None:
        """Advance the PV history by one sample WITHOUT acting on it.

        Process utility
        ---------------
        For a loop that must keep watching while something else decides its output: a ratio
        master whose slave has been taken off cascade, or a loop held by a safety permissive.
        Its measurement is still live and its history must stay current, so that when it is
        allowed to act again it resumes on the two samples that actually just happened
        instead of on a stale pair from before the hold.

        This is the extraction of V1's inline ``pv2 = pv1; pv1 = x; pv = x`` idiom, which
        appears verbatim in ``step_uf85_cascade``. It is a rename, not a new behaviour.
        """
        self.pv2 = self.pv1
        self.pv1 = pv
        self.pv = pv

    def set_mode(self, mode: str) -> None:
        """Select MAN, AUTO or CAS.

        Deliberately NOT bumpless in the way :class:`~.controller.Controller` is. V1's
        engineering-unit loops keep their PV history current in every mode and do not adopt
        the PV as a set point on transfer, so a transfer here leaves the set point where the
        operator left it. That is the installed behaviour, and changing it would change what
        a trainee sees when they close a loop.
        """
        if mode not in MODES:
            raise ValueError(f"unknown mode {mode!r} for {self.tag}")
        self.mode = mode

    def set_sp(self, value: float) -> None:
        """Move the set point, clamped to this loop's own span."""
        self.sp = clamp(value, self.sp_lo, self.sp_hi)

    def set_op(self, value: float) -> None:
        """Drive the output by hand, clamped to its limits. Meaningful in MAN."""
        self.op = clamp(value, self.op_lo, self.op_hi)

    def as_packet(self) -> dict:
        """The four fields a faceplate renders.

        Rounding for display belongs to the publication layer, not here: a value rounded at
        source is a value the next tick integrates.
        """
        return {"mode": self.mode, "pv": self.pv, "sp": self.sp, "op": self.op}


@dataclass
class FlowLoop:
    """A flow controller closed around a pure-gain flow element.

    Process utility
    ---------------
    A flow control valve and its transmitter form the fastest loop on any plant, and the
    model of it here is deliberately the simplest thing that is still a proper loop: the
    element is a pure gain from stroke to flow, and the measurement is that flow lagged by
    the transmitter's time constant. Lagging the MEASUREMENT rather than the flow is what
    makes the loop a first-order system with |z| < 1 — stable for any tuning the trainee can
    dial in — while leaving the delivered flow itself instantaneous, which is what the
    downstream mass balance must receive.

    What this means for the flowsheet
    ---------------------------------
    A FIC in AUTO holds its leg at set point by integral action, so it REJECTS any upstream
    element placed in series with it. Do not model a series level valve by derating
    ``design_flow``: an upstream level loop has no steady-state authority that way and will
    wind up. Cascade it into this loop through ``cas_sp`` instead, which is how LIC-323503
    and FIC-328405 are wired.

    Bit-exact at design
    -------------------
    ``op == op_des`` gives ``pre == design`` gives ``pv == design == sp`` gives ``du == 0``,
    so the output stays at ``op_des`` and the delivered flow is the design flow to the last
    bit.
    """

    loop: ProcessLoop
    #: Design flow of this leg. The UNIT is the caller's — several V1 loops run in t/h — and
    #: whatever unit is passed is the unit returned.
    design_flow: float
    #: Valve stroke at that design flow [%].
    op_des: float
    #: Flow-transmitter time constant [s].
    tau_s: float = 5.0
    #: Liquid density [kg/m3] for a VOLUMETRIC loop, or None for a mass loop. See
    #: :meth:`step`.
    rho_kgm3: float | None = None
    #: The valve's trim, a `control.valve.cv_fraction` name. V1 runs every flow valve linear;
    #: the vendor's valves run their own (handoff B-44, decided 2026-09-30).
    characteristic: str = "linear"
    #: Lag state of the flow transmitter. Owned by this loop rather than shared, so two
    #: loops can never collide on a key.
    _lag_state: dict = field(default_factory=dict)

    #: Key the transmitter lag is stored under inside ``_lag_state``.
    _LAG_KEY = "pv"

    def step(self, dt: float, cas_sp: float | None = None,
             flow_cap: float | None = None, pressure_ratio: float = 1.0) -> float:
        """Advance one tick and return the delivered flow, in ``design_flow``'s own unit.

        A valve between live pressures
        ------------------------------
        ``pressure_ratio`` is what the valve's line passes at a stroke against what it passes
        there on its design pressures — the anchored gas or liquid law's pressure term, its
        trim factored out. A steam valve on a header that falls passes less at the same stroke,
        and the loop opens to hold its set point until the valve is wide open (handoff B-73).
        The default, 1.0, is the pure-gain element exactly.

        A pump that lost suction
        ------------------------
        ``flow_cap`` is the flow the leg actually delivered on the previous tick when the
        process limited it below the stroke's flow — a pump drawing a vessel down to its heel.
        The transmitter then reads that flow, not the stroke's, so the controller sees the
        shortfall and opens. ``None``, the default, leaves the loop exactly as it was.

        Volumetric loops
        ----------------
        FIC-323401, FIC-328405 and FIC-323418 run their loops in VOLUMETRIC units: the field
        element meters volume, not mass, so the controller must compare a volumetric PV
        against a volumetric set point. When ``rho_kgm3`` is given, the lagged mass PV and any
        cascade set point are divided by it before the controller sees them, and the loop's
        own seeds, ``sp_hi`` and gain are expected to be in volumetric units already.

        The retune that goes with it keeps the closed loop invariant: the open-loop gain
        scales as ``g_vol = g_mass / rho``, so ``Kc_vol = Kc_mass . rho`` leaves ``Kc.g``
        unchanged, and the integral term ``Kc.(dt/Ti).err`` is likewise unchanged because the
        error scales the other way. Ti therefore stays as it is.

        The RETURN is always the mass (or caller-unit) flow, so every downstream balance is
        untouched by the choice of loop units.
        """
        pre = self.stroke_flow(self.loop.op) * pressure_ratio
        if flow_cap is not None:
            pre = min(pre, flow_cap)
        pv = first_order_lag(self._lag_state, self._LAG_KEY, pre, self.tau_s, dt)
        if self.rho_kgm3 is not None:
            pv = pv / self.rho_kgm3
            if cas_sp is not None:
                cas_sp = cas_sp / self.rho_kgm3
        op = self.loop.step(pv, dt, cas_sp)
        return self.stroke_flow(op) * pressure_ratio

    def stroke_flow(self, op: float) -> float:
        """The flow the valve passes at stroke ``op`` [%], in ``design_flow``'s unit.

        Process utility
        ---------------
        The flow element's gain: through the trim's curve, anchored so the design stroke passes
        the design flow exactly. A linear trim is V1's expression, operand for operand.
        """
        if self.characteristic == "linear":
            return self.design_flow * (op / self.op_des)
        return self.design_flow * (cv_fraction(op / 100.0, self.characteristic)
                                   / cv_fraction(self.op_des / 100.0, self.characteristic))

    def force_measurement(self, target: float, dt: float) -> float:
        """Drive the transmitter lag toward ``target`` without running the controller.

        Process utility
        ---------------
        For a hard permissive — a trip that zeroes the pump regardless of controller mode.
        The physical flow has stopped, so the measurement must decay toward zero on the
        transmitter's own time constant; leaving it at its last value would have the
        faceplate claim a flow that is not there. The controller is deliberately NOT stepped,
        which is what stops it winding up against a safety permissive.
        """
        return first_order_lag(self._lag_state, self._LAG_KEY, target, self.tau_s, dt)

    @property
    def measurement(self) -> float:
        """The current transmitter reading, in the loop's own units."""
        return self._lag_state.get(self._LAG_KEY, 0.0)


__all__ = [
    "MODES",
    "pv_ok",
    "ProcessLoop",
    "FlowLoop",
]
