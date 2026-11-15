"""Elemental closure of the synthesis loop's units, tick by tick (handoff A-34, session 99).

What this audits
----------------
The dynamic audit (`tests/engine/test_dynamic_audit.py`) closes the mass of four holdups; this file
closes the atoms. A minute of a load disturbance — 320K002's CO2 demand cut a fifth and HV-322605
throttled to 45 %, from five seconds after the seed — and on every tick each synthesis unit's call
must return the nitrogen, carbon, hydrogen and oxygen it was given:

* 322E001's tubes: the tube feed (the reactor's overflow of the tick before plus the CO2 sweep) to
  the top gas and the bottoms;
* 322F001: the motive ammonia and the suction drawn from 322E003's sump to the discharge;
* 322E002: its feed (322E001's top gas and 322F001's discharge) to its gas and its liquid;
* 322R001's reaction: its corrected feed to the overflow and the off-gas, the boil included;
* 322E003's tubes: the reactor's off-gas, the carbamate wash and any carry-over to the vent and the
  overflow.

Each closes to 1e-9 kmol/h; measured, 7.3e-12 at most (As-Built Part CX).

The two named exceptions
------------------------
Two places in the loop do not conserve atoms, by V1's construction, and each is asserted here as what
it is, so that a change to either is seen:

1. **The reactor's recycle tear (handoff B-127).** `reactor_322r001` removes the pinned vector
   `REACT_TEAR_DES_KMOLH` from its feed, scaled by the CO2 load ratio: N 121.45, C 1.25, H 359.07 and
   O 1.84 kmol/h at the design.
2. **The reactor's holdup has no composition (handoff B-126).** `ReactorInventory` sends on the tick's
   reaction product scaled to the hydraulic outflow, so the overflow carries the present composition,
   and the 136 t it holds carries none. Through the disturbance the overflow differs from the reaction's
   by up to 1 595 kmol/h of nitrogen.

The smaller holdups the loop runs mass-only, 322E001's sump, 322E002's holdup and 322E003's sump, are of
the same class as the second: each passes on the composition of the tick it was filled on. They lie
outside the units' calls this file closes.

Source: As-Built Part CVIII.6 (the tear), CVIII.5 (the holdup), Part CX (this file's measurements).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from ureasim.core.stream import MW_COMP
from ureasim.data.synthesis_pin import REACT_TEAR_DES_KMOLH
from ureasim.engine.command import apply_command
from ureasim.engine.plant import build_plant
from ureasim.engine.scheduler import Scheduler
from ureasim.units.synthesis.ejector import MOTIVE_W

#: Atoms of N, C, H and O in each published species, from its formula.
ATOMS = {"CO2": (0, 1, 0, 2), "CH4": (0, 1, 4, 0), "H2": (0, 0, 2, 0), "H2O": (0, 0, 2, 1),
         "N2": (2, 0, 0, 0), "NH3": (1, 0, 3, 0), "O2": (0, 0, 0, 2),
         "Urea": (2, 1, 4, 1), "Biuret": (3, 2, 5, 2)}

#: The closure each unit's call must meet [kmol/h of each element]; rounding is about 1e-11.
CLOSURE_KMOLH = 1.0e-9

UNITS = ("322E001", "322F001", "322E002", "322E002 feed", "322E001 feed", "322R001 reaction",
         "322E003")


def elements(kmolh: dict) -> tuple:
    """N, C, H and O carried by a molar stream [kmol/h]."""
    out = [0.0, 0.0, 0.0, 0.0]
    for k, v in kmolh.items():
        for i, a in enumerate(ATOMS[k]):
            out[i] += a * v
    return tuple(out)


def _kmolh(kgh: dict) -> dict:
    return {k: v / MW_COMP[k] for k, v in kgh.items()}


def _diff(a: dict, *b: dict) -> float:
    """The largest elemental residual between ``a`` and the sum of ``b`` [kmol/h]."""
    ea = elements(a)
    eb = [sum(t) for t in zip(*(elements(x) for x in b))]
    return max(abs(x - y) for x, y in zip(ea, eb))


@pytest.fixture(scope="module")
def loop():
    """A minute of the disturbance, each unit's worst residual and the two exceptions recorded."""
    sched = Scheduler(*build_plant())
    for _ in range(50):
        sched.tick()
    plant = sched.plant
    for cmd in ({"type": "co2_set", "value": 0.8 * plant.operator["320K002-CO2"]},
                {"type": "hic605_set", "op": 45.0}):
        assert apply_command(plant, cmd, sched.results).ok, cmd
    out = SimpleNamespace(worst=dict.fromkeys(UNITS, 0.0), tear=[], scaled=0.0, holdup_n=0.0)
    prev_overflow = dict(plant.units["322R001"].overflow_kmolh)
    for _ in range(600):
        y_sump = dict(plant.units["322E003"].y_overflow)
        r = sched.tick().results
        strip, cond = r["322E001"].stripper, r["322E002"].holdup.condenser
        ej, react, step = r["322F001"], r["322R001"].reaction, r["322R001"]
        scrub = r["322E003"].scrubber
        motive = _kmolh({k: r["321"].motive_nh3_kgh * MOTIVE_W[k] for k in MW_COMP})
        suction = _kmolh({k: ej.suction_kgh * y_sump.get(k, 0.0) for k in MW_COMP})
        res = {"322E001": _diff(strip.feed_kmolh, strip.top_kmolh, strip.bot_kmolh),
               "322E001 feed": _diff(strip.feed_kmolh, prev_overflow, strip.co2_feed_kmolh),
               "322F001": _diff(_kmolh(ej.comp_kgh), motive, suction),
               "322E002": _diff(cond.feed_kmolh, cond.gas_kmolh, cond.liq_kmolh),
               "322E002 feed": _diff(cond.feed_kmolh, strip.top_kmolh, _kmolh(ej.comp_kgh)),
               "322R001 reaction": _diff(react.feed_corrected_kmolh, react.overflow_kmolh,
                                         react.offgas_kmolh),
               "322E003": _diff(scrub.feed_kmolh, scrub.offgas_kmolh, scrub.overflow_kmolh)}
        for unit, v in res.items():
            out.worst[unit] = max(out.worst[unit], v)
        out.tear.append((react.co2_scale,
                         {k: react.feed_kmolh.get(k, 0.0) - react.feed_corrected_kmolh.get(k, 0.0)
                          for k in MW_COMP}))
        m_react = sum(react.overflow_kmolh[k] * MW_COMP[k] for k in react.overflow_kmolh)
        f_out = step.m_out_kgh / m_react
        out.scaled = max(out.scaled, max(abs(step.overflow_kmolh[k] - react.overflow_kmolh[k] * f_out)
                                         for k in react.overflow_kmolh))
        dn = elements(step.overflow_kmolh)[0] - elements(react.overflow_kmolh)[0]
        out.holdup_n = dn if abs(dn) > abs(out.holdup_n) else out.holdup_n
        prev_overflow = dict(step.overflow_kmolh)
    return out


@pytest.mark.parametrize("unit", UNITS)
def test_each_unit_returns_the_atoms_it_is_given(loop, unit):
    """Each synthesis unit's call, and the two feeds the loop hands from one unit to the next, close
    on N, C, H and O on every tick of the disturbance (7.3e-12 kmol/h at most, measured)."""
    assert loop.worst[unit] < CLOSURE_KMOLH, (unit, loop.worst[unit])


def test_the_reactor_tear_is_the_pinned_vector_on_the_co2_load(loop):
    """B-127: what the reactor removes from its feed is `REACT_TEAR_DES_KMOLH` times the CO2 load
    ratio on every tick, species by species, and at the design it is N 121.45, C 1.25, H 359.07 and
    O 1.84 kmol/h (As-Built CVIII.6). Its move onto the stream it corrects closes this exception."""
    for s, tear in loop.tear:
        for k in MW_COMP:
            assert tear[k] == pytest.approx(REACT_TEAR_DES_KMOLH.get(k, 0.0) * s, abs=1e-9), k
    n, c, h, o = elements(dict(REACT_TEAR_DES_KMOLH))
    assert (n, c, h, o) == pytest.approx((121.45, 1.25, 359.07, 1.84), abs=0.01)


def test_the_reactor_holdup_sends_the_reactions_composition(loop):
    """B-126: the overflow 322R001 sends on is this tick's reaction product scaled to the outflow,
    species by species, to the bit (0.0 kmol/h measured), so the holdup carries no composition; through
    the disturbance the overflow's nitrogen differs from the reaction's by up to -1 595.22 kmol/h.
    Carrying the holdup's species closes this exception."""
    assert loop.scaled < 1e-9
    assert loop.holdup_n == pytest.approx(-1595.22, abs=0.01)
