"""322R001 stepped: the boot-pinned seed, the throughput basis, the holdup's response, the carryover.

Closes handoffs B-14 and B-15 by measurement on the design seed the engine starts from.
"""

from __future__ import annotations

import pytest

from ureasim.core.stream import MW_COMP
from ureasim.data import synthesis_pin as pin
from ureasim.data.unit_322r001 import XI_BIURET_DES, XI_UREA_DES
from ureasim.engine.plant import build_plant
from ureasim.engine.scheduler import Scheduler
from ureasim.units.synthesis.reactor_hydraulics import melt_density
from ureasim.units.synthesis.reactor_inventory import (
    M_LIQ_DES_KG,
    M_OVERFLOW_DES_KGH,
    ReactorInventory,
)

DT = 0.1


@pytest.fixture(scope="module")
def seed():
    """The plant's first tick: what 322R001 is handed at its design seed."""
    sch, plant = build_plant()
    r = Scheduler(sch, plant).tick().results
    return {"hpcc": r["322E002"].holdup.condenser, "co2": r["320K002"].feed_to_loop_th,
            "ratio": r["321"].ratio_pv, "suction": r["322F001"].suction_kgh,
            "result": r["322R001"]}


def _step(unit, seed, hic605=60.0, hic602=74.0, suction=None):
    return unit.step(seed["hpcc"], seed["co2"], seed["ratio"], hic605, hic602,
                     seed["suction"] if suction is None else suction, 140.7, DT)


def test_the_seed_makes_the_pfds_urea_and_biuret_b14(seed):
    """B-14: on the boot pin's calibration (V1's own, re-solved at the live seed) the reactor makes
    the PFD's 1302.27 kmol/h of urea and 2.414 of biuret at the profile it runs."""
    r = _step(ReactorInventory(), seed)
    assert r.reaction.xi_urea == pytest.approx(XI_UREA_DES, abs=1e-9)
    assert r.reaction.xi_biuret == pytest.approx(XI_BIURET_DES, abs=1e-12)


def test_the_seeded_throughput_is_the_calibrations_b15():
    """B-15: the residence time the seed runs on — the design overflow at the pinned profile's bulk
    density — is the throughput the kinetics were solved at, 227.4997 m3/h."""
    unit = ReactorInventory()
    vdot = sum(unit.overflow_kmolh[k] * w for k, w in MW_COMP.items()) / melt_density(
        sum(unit.t_nodes_c) / 4.0)
    assert vdot == pytest.approx(pin.REACT_ANCHOR_VDOT_M3H, rel=1e-15)
    assert vdot == pytest.approx(227.4997, abs=1e-4)


def test_the_seed_holdup_is_the_profiles():
    """The seeded holdup reads the NLL on the pinned profile's bulk density, 135 903.7 kg."""
    assert M_LIQ_DES_KG == pytest.approx(135903.708, abs=1e-3)
    assert M_OVERFLOW_DES_KGH == pytest.approx(226176.845, abs=1e-3)


def test_throttling_hv_322605_floods_the_reactor_and_starves_the_stripper(seed):
    """45 % for a minute on the seed's feed: the level rises, the stripper gets less."""
    unit = ReactorInventory()
    for _ in range(600):
        r = _step(unit, seed, hic605=45.0)
    assert r.level_pct > 80.3
    assert r.m_out_kgh < 0.85 * M_OVERFLOW_DES_KGH
    assert sum(r.overflow_kmolh.values()) < 0.85 * sum(seed["result"].overflow_kmolh.values())


def test_a_spindle_move_pulses_carbamate_forward_and_washes_out(seed):
    """HV-322602 74 to 60 %: a forward pulse that the 8 min washout takes back to zero."""
    unit = ReactorInventory()
    first = _step(unit, seed, hic602=60.0)
    assert first.m_fwd_kgh > 0.0
    for _ in range(36000):
        r = _step(unit, seed, hic602=60.0)
    assert abs(r.m_fwd_kgh) < 1e-3 * first.m_fwd_kgh


def test_a_full_vessel_spills_into_the_off_gas_line(seed):
    """HV-322605 shut: the holdup fills the vessel and the excess carries over to 322E003 at the
    overflow's composition."""
    unit = ReactorInventory(m_liq_kg=M_LIQ_DES_KG * 1.24, level_pct=99.0)
    r = _step(unit, seed, hic605=0.0)
    for _ in range(600):
        if r.carry_kgh > 0.0:
            break
        r = _step(unit, seed, hic605=0.0)
    assert r.carry_kgh > 0.0 and r.level_pct == pytest.approx(100.0, abs=1e-9)
    assert sum(r.carry_kmolh.values()) > 0.0


def test_a_stripper_standing_full_holds_the_liquor_back_in_the_reactor(seed):
    """B-104, decided 2026-10-22: HV-322605 discharges no more than 322E001's full tubes can take,
    and what they hand back past their ceiling returns to the holdup — the reactor keeps both, its
    level rising. Without a cap and with nothing handed back the step is the uncapped one's."""
    free = _step(ReactorInventory(), seed)
    unit = ReactorInventory()
    capped = unit.step(seed["hpcc"], seed["co2"], seed["ratio"], 60.0, 74.0, seed["suction"],
                       140.7, DT, m_out_cap_kgh=100_000.0, backup_kgh=20_000.0)
    assert capped.m_out_kgh == 100_000.0 < free.m_out_kgh
    assert capped.overflow_kgh == 100_000.0
    gained = (free.m_out_kgh - 100_000.0 + 20_000.0) * DT / 3600.0
    assert capped.m_liq_kg - free.m_liq_kg == pytest.approx(gained, rel=1e-9)
    same = ReactorInventory().step(seed["hpcc"], seed["co2"], seed["ratio"], 60.0, 74.0,
                                   seed["suction"], 140.7, DT, m_out_cap_kgh=1e9, backup_kgh=0.0)
    assert (same.m_out_kgh, same.m_liq_kg) == (free.m_out_kgh, free.m_liq_kg)
