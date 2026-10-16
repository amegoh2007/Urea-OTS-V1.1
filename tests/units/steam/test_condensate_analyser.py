"""AI-329701, the LP condensate's conductivity in 329D001 —
`ureasim.units.steam.condensate_analyser`.

Pinned: clean condensate reads pure water; the ammonia and CO2 a tube leak puts into the steam
read as ammonium bicarbonate on the ions' limiting conductivities, the lesser of the two pairing;
the transmitter reads the top of its 0-10 uS/cm range past it; on the plant, a 322E002 tube leak of
0.1 kg/h already reads 2.2 uS/cm and 10 t/h pegs the analyser (handoff B-90, decided 2026-10-09);
its high and high-high alarms on the plant DCS's 15 and 18 uS/cm (read back 2026-10-13).
"""

from __future__ import annotations

import pytest

from ureasim.data.unit_329 import (
    AI_329701_H1_US_CM,
    AI_329701_H2_US_CM,
    AI_329701_SPAN_US_CM,
    KAPPA_WATER_US_CM,
)
from ureasim.engine.command import apply_command
from ureasim.engine.plant import build_plant
from ureasim.engine.scheduler import Scheduler
from ureasim.units.steam.condensate_analyser import (
    ai_329701_alarms,
    ai_329701_reading,
    condensate_conductivity_us_cm,
)


def test_clean_condensate_reads_pure_water():
    assert condensate_conductivity_us_cm(0.0, 0.0, 52000.0) == KAPPA_WATER_US_CM == 0.055
    assert condensate_conductivity_us_cm(1.0, 1.0, 0.0) == KAPPA_WATER_US_CM


def test_the_lesser_of_ammonia_and_co2_pairs_as_ammonium_bicarbonate():
    """1e-5 mol/L of ammonium bicarbonate: (73.5 + 44.5) S cm2/mol, 1.18 uS/cm over pure water.
    The excess of either species adds nothing."""
    q = 1000.0                               # kg/h of condensate, a litre a kilogram
    n = 1e-5 * q / 1000.0                    # kmol/h for 1e-5 mol/L
    assert condensate_conductivity_us_cm(n, n, q) == pytest.approx(0.055 + 1.18, rel=1e-12)
    assert condensate_conductivity_us_cm(4 * n, n, q) == condensate_conductivity_us_cm(n, n, q)
    assert condensate_conductivity_us_cm(n, 4 * n, q) == condensate_conductivity_us_cm(n, n, q)


def test_the_transmitter_reads_the_top_of_its_range_past_it():
    assert AI_329701_SPAN_US_CM == 10.0
    assert ai_329701_reading(2.5) == (2.5, False)
    assert ai_329701_reading(250.0) == (10.0, True)


def test_the_alarms_stand_on_the_plant_dcs_set_points():
    """H1 15 and H2 18 uS/cm (the plant DCS, read back 2026-10-13), on the condensate's
    conductivity: both above the 0-10 uS/cm range the archive gives the transmitter."""
    assert (AI_329701_H1_US_CM, AI_329701_H2_US_CM) == (15.0, 18.0)
    assert ai_329701_alarms(14.9) == (False, False)
    assert ai_329701_alarms(15.1) == (True, False)
    assert ai_329701_alarms(18.1) == (True, True)


def test_a_tube_leak_reads_on_ai_329701():
    """At design the analyser reads pure water; a bare trigger leaks the decided 10 t/h and pegs
    it (216 624 uS/cm measured, past the dilute law's range); 0.1 kg/h reads 2.22 uS/cm (2.2232
    before the loop's vapour inventory, B-77 (b))."""
    sched = Scheduler(*build_plant())
    sched.tick()
    u = sched.results["329-USERS"]
    assert (u.ai_329701_us_cm, u.ai_329701_over) == (0.055, False)
    assert apply_command(sched.plant, {"type": "trigger_fault", "id": "322E002"}).ok
    sched.tick()
    u = sched.results["329-USERS"]
    assert u.kappa_329d001_us_cm == pytest.approx(216624.0, rel=1e-4)
    assert (u.ai_329701_us_cm, u.ai_329701_over) == (10.0, True)
    assert (u.ai_329701_h1, u.ai_329701_h2) == (True, True)
    assert apply_command(sched.plant, {"type": "trigger_fault", "id": "322E002",
                                       "rate": 0.0001}).ok
    sched.tick()
    u = sched.results["329-USERS"]
    assert u.ai_329701_us_cm == pytest.approx(2.2222, abs=1e-3) and not u.ai_329701_over
