"""Handoff B-67's, B-71's and B-87's switch on the V1 side of the vacuum-condenser equivalences.

What this is
------------
Decided 2026-10-02 (handoff B-67, option a, closed; As-Built §LIV.1): a condenser's NH3 and CO2
vent pressures are the PFD's partial pressures plus the departure of the condensate's Extended
UNIQUAC back-pressure from its design value, floored at zero,

    p_k = Y_des s_k P_des + (p*_k(w_cond, T_v) - p*_k,des)                k = NH3, CO2

where V1 multiplies the PFD's partial pressure by the back-pressure's ratio to its design value.
Decided 2026-10-02 (handoff B-71, closed; As-Built §LV.1): the addition applies only where the
design back-pressure is at most the PFD's partial pressure; above it — 324E007's CO2, 324E005's
NH3 and CO2, 324E006's CO2 — V1's ratio stands. The port runs both (`vacuum_condenser.vent_moles`).
Decided 2026-10-09 (handoff B-87, option b; As-Built §LXIV.2): every species the vent carries, and
the inerts that size it, is floored at zero, so no vent is negative; the transcription carries it.

To keep proving the rest of every condenser, condenser node, stage and train against V1's own
bytes, `switched_module` loads a second, private copy of V1's ``backend/vacuum_condenser.py`` and
replaces its ``vent_moles`` with V1's function TRANSCRIBED line for line with that one switch
(declared as such, handoff A-12): V1's ``solve``, ``_q_balance`` and ``vent_kgh_at`` find it
through their module globals, so every other line they run is V1's. `switched_specs` lifts V1's
four design specs out of ``main.py`` on that copy. V1's own module stays loaded and untouched for
the tests that run the departure both ways.
"""

from __future__ import annotations

import importlib.util
import math
import sys

from tests.equivalence.v1_loader import V1_BACKEND, lift, load

#: The private copy's module name; never V1's bare name, so nothing else resolves to it.
ALIAS = "v1_vacuum_condenser_b67"

_CACHE: dict = {}


def _transcribed_vent_moles(m):
    """V1 ``vacuum_condenser.vent_moles`` (161-189) on module ``m``, with B-67's, B-71's and B-87's
    switch."""

    def vent_moles(spec: dict, p_bara: float, t_v_c: float, n_in: dict, bp: tuple = None) -> dict:
        # B-87: V1 writes ``n_in.get(k, 0.0)`` here, and below, unfloored.
        n_i = sum(max(n_in.get(k, 0.0), 0.0) for k in m.INERT)
        y = spec["y_des"] * (spec["p_des"] / max(p_bara, 1.0e-9)) \
            * (m.iapws_if97.psat_bara(t_v_c) / spec["psat_v_des"])
        split = spec["split"]
        w_cond = m.condensate_fractions(n_in) if "bp_des" in spec else {}
        if w_cond:
            if bp is None:
                bp = m.packed_absorber.back_pressure(w_cond, t_v_c)
            # B-67 / B-71: V1 writes ``... * (spec["p_des"] / max(p_bara, 1.0e-9)) * (bp[k] /
            # spec["bp_des"][k])`` for NH3 and CO2; where the design back-pressure is at most the
            # PFD's partial pressure the decided departure is added instead.
            p = max(p_bara, 1.0e-9)
            rel = {"H2O": y * split["H2O"]}
            for i, k in enumerate(("NH3", "CO2")):
                if spec["bp_des"][i] > spec["y_des"] * split[k] * spec["p_des"] * 1.0e5:
                    rel[k] = spec["y_des"] * split[k] * (spec["p_des"] / p)                         * (bp[i] / spec["bp_des"][i])
                else:
                    rel[k] = max(spec["y_des"] * split[k] * (spec["p_des"] / p)
                                 + (bp[i] - spec["bp_des"][i]) / (1.0e5 * p), 0.0)
            y = sum(rel.values())
            split = {k: rel[k] / y for k in m.CONDENSABLE} if y > 0.0 else split
        y = min(max(y, 0.0), m._Y_MAX)
        n_c = n_i * y / (1.0 - y)
        vent = {k: max(min(n_c * split[k], n_in.get(k, 0.0)), 0.0) for k in m.CONDENSABLE}
        for k in m.INERT:
            vent[k] = max(n_in.get(k, 0.0), 0.0)
        vent["Urea"] = 0.0
        return vent

    return vent_moles


def switched_module():
    """A private copy of V1's ``vacuum_condenser`` with B-67's ``vent_moles``."""
    if "module" not in _CACHE:
        load("vacuum_condenser")            # V1's own copy, and the modules it imports, first
        spec = importlib.util.spec_from_file_location(ALIAS, V1_BACKEND / "vacuum_condenser.py")
        m = importlib.util.module_from_spec(spec)
        sys.modules[ALIAS] = m
        spec.loader.exec_module(m)
        m.vent_moles = _transcribed_vent_moles(m)
        _CACHE["module"] = m
    return _CACHE["module"]


def switched_specs() -> dict:
    """V1's ``VACUUM_CONDENSER_SPECS``, lifted from ``main.py`` on the switched copy."""
    if "specs" not in _CACHE:
        _CACHE["specs"] = lift(["VACUUM_CONDENSER_SPECS"],
                               seed={"math": math, "vacuum_condenser": switched_module()}
                               )["VACUUM_CONDENSER_SPECS"]
    return _CACHE["specs"]
