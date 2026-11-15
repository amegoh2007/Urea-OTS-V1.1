"""322E002's tube leak — `ureasim.units.synthesis.tube_leak` (handoff B-82, decided 2026-10-09).

Pinned: no leak returns the product untouched; the rate follows the live differential and is
capped at the product; the leak's mass splits into the steam's volatiles and the drums' water,
and 322R001 receives the rest of each component; the leak's heat in the shell, on the elements
datum, condenses steam at design (the dissolved ammonia and CO2 pay their desorption); and on the
whole plant the loop loses what leaks, 322D001A/B takes it, and the instructor's command sets it.
"""

from __future__ import annotations

import math

import pytest

from ureasim.core.stream import MW_COMP
from ureasim.data.unit_322e002 import LEAK_DP_DES_BAR, LEAK_VOLATILE
from ureasim.data.unit_329 import P_LP_BARA
from ureasim.engine.command import apply_command
from ureasim.engine.plant import build_plant
from ureasim.engine.scheduler import Scheduler
from ureasim.units.synthesis.tube_leak import NO_LEAK, tube_leak

P_TUBE = 140.7
T_SHELL = 151.8


@pytest.fixture(scope="module")
def hpcc():
    sched = Scheduler(*build_plant())
    sched.tick()
    return sched.results["322E002"].holdup.condenser


def test_no_leak_returns_the_product_untouched(hpcc):
    leak, after = tube_leak(0.0, P_TUBE, P_LP_BARA, hpcc, T_SHELL)
    assert leak is NO_LEAK and after is hpcc
    assert (NO_LEAK.m_kgh, NO_LEAK.vapour_kgh, NO_LEAK.liquid_kgh, NO_LEAK.boil_kgh) == (0.0,) * 4


def test_the_rate_follows_the_differential_and_is_capped(hpcc):
    """10 t/h at the design differential, 135.69 bar; at half of it 10 / sqrt(2); never more than
    the 250.6 t/h product, which then all leaks and nothing reaches 322R001."""
    assert LEAK_DP_DES_BAR == pytest.approx(140.7 - P_LP_BARA, abs=1e-12)
    leak, _ = tube_leak(10000.0, P_LP_BARA + LEAK_DP_DES_BAR, P_LP_BARA, hpcc, T_SHELL)
    assert leak.m_kgh == pytest.approx(10000.0, rel=1e-12)
    half, _ = tube_leak(10000.0, P_LP_BARA + 0.5 * LEAK_DP_DES_BAR, P_LP_BARA, hpcc, T_SHELL)
    assert half.m_kgh == pytest.approx(10000.0 / math.sqrt(2.0), rel=1e-12)
    none, _ = tube_leak(10000.0, P_LP_BARA, P_LP_BARA, hpcc, T_SHELL)
    assert none.m_kgh == 0.0
    whole, after = tube_leak(1.0e9, P_TUBE, P_LP_BARA, hpcc, T_SHELL)
    assert whole.m_kgh == pytest.approx(hpcc.gas_kgh + hpcc.liq_kgh, rel=1e-12)
    assert whole.frac == 1.0 and after.m_dot_kgh == 0.0 and sum(after.feed_kmolh.values()) == 0.0


def test_the_leak_closes_its_books(hpcc):
    """10 t/h at design, 3.99 % of the product: 9.31 t/h of volatiles and inerts to the steam,
    0.69 t/h of water and solids (1.03 kg/h of urea) to the drums; 322R001 receives the rest of
    every component of the product and of the combined feed."""
    leak, after = tube_leak(10000.0, P_TUBE, P_LP_BARA, hpcc, T_SHELL)
    f = leak.frac
    assert f == pytest.approx(10000.0 / (hpcc.gas_kgh + hpcc.liq_kgh), rel=1e-12)
    assert leak.vapour_kgh + leak.liquid_kgh == pytest.approx(leak.m_kgh, rel=1e-12)
    assert (leak.vapour_kgh, leak.liquid_kgh, leak.solids_kgh) == (
        pytest.approx(9310.98, abs=0.01), pytest.approx(689.02, abs=0.01),
        pytest.approx(1.031, abs=0.001))
    vol = sum(leak.leaked_kmolh[k] * MW_COMP[k] for k in LEAK_VOLATILE)
    assert vol == pytest.approx(leak.vapour_kgh, rel=1e-12)
    for k in MW_COMP:
        assert leak.leaked_kmolh[k] == pytest.approx(
            f * (hpcc.gas_kmolh.get(k, 0.0) + hpcc.liq_kmolh.get(k, 0.0)), rel=1e-12, abs=1e-15)
        assert after.feed_kmolh.get(k, 0.0) == pytest.approx(
            (1.0 - f) * hpcc.feed_kmolh.get(k, 0.0), rel=1e-12, abs=1e-15)
    assert after.liq_kgh + after.gas_kgh + leak.m_kgh == pytest.approx(
        hpcc.liq_kgh + hpcc.gas_kgh, rel=1e-12)


def test_the_leaks_heat_condenses_steam_at_design(hpcc):
    """The leak arrives at 170 C, its ammonia and CO2 mostly dissolved; desorbing them in the
    shell at 151.8 C takes 1 382 kW more than its sensible heat gives, so it condenses 2.36 t/h of
    the drums' steam."""
    leak, _ = tube_leak(10000.0, P_TUBE, P_LP_BARA, hpcc, T_SHELL)
    assert leak.q_kw == pytest.approx(-1381.95, abs=0.01)
    assert leak.boil_kgh == pytest.approx(-2360.03, abs=0.01)


def test_the_instructors_leak_on_the_plant():
    """10 t/h from design for a minute: PT-329201 holds, 140.709 bar a — the leak drains 322E002's
    liquor, which the loop's vapour inventory does not count (B-77 (b), decided 2026-10-09; it fell
    0.080 bar on V1's lumped node; 140.710 before session 53's decisions, 2026-10-15, the leak's steam
    reaching an LP header now on Metso's trims; 140.709 before the reactor's bubble-point ceiling, B-92); the LP
    steam carries the leak's volatiles, 322D001A/B's water takes its solids. The command takes its
    rate as ``rate`` or ``value``, and a bare trigger leaks 10 t/h (B-90, decided 2026-10-09; it was
    refused before); clear_fault stops it."""
    sched = Scheduler(*build_plant())
    plant = sched.plant
    assert apply_command(plant, {"type": "trigger_fault", "id": "322E002", "rate": 2.5}).ok
    assert plant.units["322E002"].leak_severity_kgh == 2500.0
    assert apply_command(plant, {"type": "trigger_fault", "id": "322E002", "value": 4.0}).ok
    assert plant.units["322E002"].leak_severity_kgh == 4000.0
    assert apply_command(plant, {"type": "trigger_fault", "id": "322E002"}).ok
    assert plant.units["322E002"].leak_severity_kgh == 10000.0
    for _ in range(600):
        sched.tick()
    res = sched.results
    leak = res["322E002"].holdup.leak
    assert res["PT-329201"].m_out_kgh > leak.m_kgh > 9990.0
    assert plant.units["PT-329201"].p_syn_bara == pytest.approx(140.709, abs=0.001)
    assert res["329"].flows_kgh["leak_vapour"] == pytest.approx(leak.vapour_kgh, rel=1e-12)
    assert res["329"].d001_solids_ppm > 0.0
    assert apply_command(plant, {"type": "clear_fault", "id": "322E002"}).ok
    sched.tick()
    assert sched.results["322E002"].holdup.leak.m_kgh == 0.0
