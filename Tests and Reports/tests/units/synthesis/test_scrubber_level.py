"""322E003's sump level and LT-329501 — `ureasim.units.synthesis.scrubber_level` (split from
`scrubber`, 2026-10-23).

Pins the level and the indication at and off design, each value measured before it was written,
and the re-export through `scrubber`. The swell's behaviour on a cooling loss is pinned in
`test_scrubber.py`.
"""

from __future__ import annotations

import pytest

from ureasim.data.unit_322e003 import HOLDUP_NLL_KG, LEVEL_NLL_PCT, SWELL_NOISE_PCT, SWELL_PCT_MAX
from ureasim.units.synthesis import scrubber
from ureasim.units.synthesis import scrubber_level as level


def test_the_design_inventory_reads_normal_level():
    """The design holdup reads the 50 % normal level exactly; the level is clamped to its span."""
    assert level.sump_level_pct(HOLDUP_NLL_KG) == LEVEL_NLL_PCT == 50.0
    assert (level.sump_level_pct(-5.0), level.sump_level_pct(1.0e9)) == (0.0, 100.0)


def test_the_indication_is_the_level_while_the_shell_condenses_in_full():
    """Swell and hunt scale with the deficit: zero at a full condensation, whatever the clock."""
    assert level.lt_329501_swell(1.0) == 0.0
    assert level.lt_329501_noise(1.0, 123.0) == 0.0
    assert level.lt_329501_indication(50.0, 1.0, 77.0) == 50.0


def test_a_lost_shell_reads_high_and_hunts():
    """With nothing condensed the cell reads the full 18 % swell high, and hunts up to 2 % about
    it on the two periods off the plant clock."""
    assert level.lt_329501_swell(0.0) == SWELL_PCT_MAX == 18.0
    assert SWELL_NOISE_PCT == 2.0
    assert level.lt_329501_noise(0.0, 0.0) == 0.0
    assert abs(level.lt_329501_noise(0.0, 37.0)) <= SWELL_NOISE_PCT
    assert level.lt_329501_indication(50.0, 0.0, 0.0) == pytest.approx(68.0, abs=1e-12)


def test_scrubber_re_exports_every_name():
    for name in level.__all__:
        assert getattr(scrubber, name) is getattr(level, name), name
        assert name in scrubber.__all__, name
