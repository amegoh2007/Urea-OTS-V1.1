"""Behaviour of the unit-323 liquor lines — `ureasim.units.recirc.liquor_line`.

The four inlets are proven against V1 inside each stage's equivalence test, since V1 writes
them inline in `step_sim`. This file pins what a line DOES: the liquor's temperature,
composition and cp arrive a line residence late, and its flow at once — so the line conserves
mass on every flow change, where V1's FIFO delayed the flow too and created and destroyed liquor
(handoff B-21, decided 2026-09-30). Every number here was measured before it was written down.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_323 as d
from ureasim.data.design_point import R323_CP_SOLN, R323_M314_DES
from ureasim.data.process_routes import PROCESS_ROUTES
from ureasim.units.recirc.liquor_line import receive_liquor, stream_cp

ROUTE = "323C003_TO_323F004"


def _deliver(profile, seconds: float, dt: float = 0.1):
    """Send `profile(t)` kg/h of design column bottoms down the line; return the arrivals and
    the totals sent and arrived [kg]."""
    state = {}
    w = dict(d.W_S314)
    sent = arrived = 0.0
    out = []
    for k in range(1, int(round(seconds / dt)) + 1):
        m = profile(k * dt)
        a = receive_liquor(state, ROUTE, m, d.C003_T_SP_C, w, d.CP_C003_DES, dt)
        sent += m * dt / 3600.0
        arrived += a.m_kgh * dt / 3600.0
        out.append((k * dt, a))
    return out, sent, arrived


@pytest.mark.parametrize("w_urea, t_c, cp_des", [
    (d.W_S208["Urea"], d.FEED_DES_T_C, d.CP_S208_DES),
    (d.W_S314["Urea"], d.C003_T_SP_C, d.CP_C003_DES),
    (d.W_S319["Urea"], d.F004_T_SP_C, d.CP_F004_DES),
])
def test_every_stream_carries_the_lumped_cp_at_its_design_state(w_urea, t_c, cp_des):
    assert stream_cp(w_urea, t_c, cp_des) == R323_CP_SOLN


def test_a_settled_line_hands_back_the_original_scalars():
    w = dict(d.W_S314)
    a = receive_liquor({}, ROUTE, R323_M314_DES, d.C003_T_SP_C, w, d.CP_C003_DES, 0.1)
    assert a.m_kgh == R323_M314_DES and a.t_c == d.C003_T_SP_C and a.w is w
    assert a.cp_kj_kgk == R323_CP_SOLN


def test_a_temperature_step_arrives_one_line_residence_later():
    """405 kg in the line at 105.9 t/h is 13.75 s of dead time, on the isometrics' geometry, the
    run after LV-323501 holding the valve's flash at its homogeneous two-phase density (handoff
    B-81, decided 2026-10-09; 960 kg, 32.6 s as a liquid plug; handoff A-11, decided 2026-10-07:
    V1's layout estimate held 470 kg, 16.0 s)."""
    route = PROCESS_ROUTES[ROUTE]
    assert route.line_inventory_kg == pytest.approx(404.56, abs=0.01)
    assert route.dead_time_s(R323_M314_DES) == pytest.approx(13.75, abs=0.01)
    state = {}
    w = dict(d.W_S314)
    arrived = []
    for k in range(1, 501):
        t_dep = 140.0 if k * 0.1 > 5.0 else d.C003_T_SP_C
        arrived.append(receive_liquor(state, ROUTE, R323_M314_DES, t_dep, w, d.CP_C003_DES,
                                      0.1).t_c)
    first = next(i for i, t in enumerate(arrived, start=1) if t == 140.0)
    assert first * 0.1 == pytest.approx(5.1 + 13.75, abs=0.1)


# ======================================================================================
# Handoff B-21, decided 2026-09-30: the flow at once, the properties a residence later
# ======================================================================================

def test_a_stopped_line_delivers_nothing():
    """The drain stops at 5 s and nothing more arrives from that tick. V1's FIFO delayed the
    flow with the liquor: a stopped carrier sent the dead time to its 1800 s cap and 323F004
    received the full design drain for the whole cap — 53 t from a line that holds 470 kg."""
    out, sent, arrived = _deliver(lambda t: 0.0 if t > 5.0 else R323_M314_DES, 1900.0)
    still = [t for t, a in out if a.m_kgh > 0.0]
    assert max(still) == pytest.approx(5.0, abs=0.1)
    assert sent == pytest.approx(147.1, abs=0.1) and arrived == sent


@pytest.mark.parametrize("factor, v1_created_kg", [(0.75, 157.4), (1.2, -78.9)])
def test_a_flow_step_neither_creates_nor_destroys_liquor(factor, v1_created_kg):
    """A liquid-full line passes a flow change at once and delays only what the liquor IS, so
    what arrives is what was sent, to the kilogram. V1's FIFO, which delayed the flow on a dead
    time that jumps with the new flow, created 157.4 kg on a 25 % cut and destroyed 78.9 kg on a
    20 % rise."""
    out, sent, arrived = _deliver(lambda t: factor * R323_M314_DES if t > 5.0 else R323_M314_DES,
                                  200.0)
    assert arrived - sent == pytest.approx(0.0, abs=1e-9)
    assert all(a.m_kgh == (factor * R323_M314_DES if t > 5.0 else R323_M314_DES)
               for t, a in out)


def test_a_temperature_step_behind_a_flow_cut_arrives_on_the_slower_line():
    """Cut the drain 25 % at 5 s and send hotter liquor from 10 s: the flow drops at once, and
    the hotter liquor takes the slower line's residence — 405 kg at 79.4 t/h, 18.33 s (B-81; 960 kg
    and 43.50 s as a liquid plug)."""
    state, w = {}, dict(d.W_S314)
    arrived = []
    for k in range(1, 801):
        t = k * 0.1
        m = 0.75 * R323_M314_DES if t > 5.0 else R323_M314_DES
        t_dep = 140.0 if t > 10.0 else d.C003_T_SP_C
        a = receive_liquor(state, ROUTE, m, t_dep, w, d.CP_C003_DES, 0.1)
        assert a.m_kgh == m
        arrived.append(a.t_c)
    first = next(i for i, t_c in enumerate(arrived, start=1) if t_c == 140.0)
    assert PROCESS_ROUTES[ROUTE].dead_time_s(0.75 * R323_M314_DES) == pytest.approx(18.33, abs=0.01)
    # Sent at 10.1 s, due at 28.43 s: the first tick past it is 28.5 s.
    assert first * 0.1 == pytest.approx(28.5, abs=1e-9)
