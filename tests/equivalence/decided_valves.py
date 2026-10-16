"""The vendor valve trims (handoff B-44, decided 2026-09-30), for the transcriptions.

Why this exists
---------------
The port runs every vendor valve on its own trim, where V1 runs it linear. Each unit's
equivalence harness carries a switch, ``valves_decided``, that puts the vendor trim into V1's
transcribed step so the port can be compared with V1's own code on the decided valves, and
runs V1 verbatim without it. What the switch needs lives here, once:

* `trim` — the vendor's modified equal-percentage characteristic, written from its formula
  (As-Built §XL.3), not imported from the port, so the port's `control.valve.cv_fraction` is
  checked against an independent statement of it;
* `design_stroke_pct` — a vendor valve's design stroke from its catalogue entry, re-derived;
* `fic_flow` — V1's ``_fic_flow`` (``main.py`` 5977-6006), TRANSCRIBED with the trim in place of
  ``op / op_des``, calling V1's own ``_lag1`` and ``_ctrl_ipd``;
* `hydraulics` — V1's ``hydraulics`` module loaded a second time, private to the decided side,
  its ``cv_fraction`` answering the vendor trim's name and deferring to V1's for every other,
  so V1's IEC laws execute on the vendor trim.
"""

from __future__ import annotations

import importlib.util
import math

from tests.equivalence.v1_loader import V1_BACKEND, load

#: The vendor trim's rangeability, as decided (As-Built §XL.3).
MOD_EQUAL_PCT_RANGE = 20.0

#: The vendor trim's name, as the port's `cv_fraction` takes it.
MOD_EQUAL_PCT = "mod_equal_pct"


def trim(h: float) -> float:
    """Kv/Kvs of Valtek's modified equal-percentage plug at fractional stroke ``h``."""
    h = min(max(h, 0.0), 1.0)
    if h <= 0.0:
        return 0.0
    a = math.log(MOD_EQUAL_PCT_RANGE)
    if h >= 1.0 / a:
        return MOD_EQUAL_PCT_RANGE ** (h - 1.0)
    return h * math.e * a / MOD_EQUAL_PCT_RANGE


def _inverse(phi: float, characteristic: str) -> float:
    if characteristic == "linear":
        return phi
    if characteristic == "equal_pct":
        return 1.0 + math.log(phi) / math.log(50.0)
    a = math.log(MOD_EQUAL_PCT_RANGE)
    if phi >= math.e ** (1.0 - a):
        return 1.0 + math.log(phi) / a
    return phi * MOD_EQUAL_PCT_RANGE / (math.e * a)


def design_stroke_pct(valve, m_des_kgh: float) -> float:
    """The stroke [%] at which a catalogued vendor valve passes ``m_des_kgh`` on its normal case."""
    c = valve.cases[valve.normal]
    return 100.0 * _inverse(c.capacity * (m_des_kgh / (c.flow * c.rho)) / valve.rated,
                            valve.characteristic)


def fic_flow(g: dict, c: dict, design: float, op_des: float, store: dict, key: str, dt: float,
             tau_s: float = 5.0, cas_sp=None, rho=None, cap=None) -> float:
    """V1 ``_fic_flow`` TRANSCRIBED, the vendor trim in place of ``op / op_des``, and the
    transmitter capped at ``cap`` as `FlowLoop.step(flow_cap=...)` caps it."""
    pre = design * (trim(c["op"] / 100.0) / trim(op_des / 100.0))
    if cap is not None:
        pre = min(pre, cap)
    pv = g["_lag1"](store, key, pre, tau_s, dt)
    if rho is not None:
        pv = pv / rho
        if cas_sp is not None:
            cas_sp = cas_sp / rho
    op = g["_ctrl_ipd"](c, pv, dt, cas_sp)
    return design * (trim(op / 100.0) / trim(op_des / 100.0))


_HYDRAULICS: list = []


def hydraulics():
    """V1's ``hydraulics``, loaded afresh and private to the decided side, its ``cv_fraction``
    answering the vendor trim."""
    if not _HYDRAULICS:
        load("hydraulics")                     # V1's own imports resolve first
        spec = importlib.util.spec_from_file_location("v1_hydraulics_decided",
                                                      V1_BACKEND / "hydraulics.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        v1_cv_fraction = module.cv_fraction

        def cv_fraction(h, characteristic="equal_pct"):
            if characteristic == MOD_EQUAL_PCT:
                return trim(h)
            return v1_cv_fraction(h, characteristic)

        module.cv_fraction = cv_fraction
        _HYDRAULICS.append(module)
    return _HYDRAULICS[0]


__all__ = ["MOD_EQUAL_PCT_RANGE", "MOD_EQUAL_PCT", "trim", "design_stroke_pct", "fic_flow",
           "hydraulics"]
