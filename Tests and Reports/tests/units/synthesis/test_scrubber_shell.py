"""322E003's shell — `ureasim.units.synthesis.scrubber_shell` (split from `scrubber`, 2026-10-23).

Pins the shell's three relations at and off design, each value measured before it was written, and
the re-export through `scrubber`. The capacity gate's three failures are pinned in
`test_scrubber.py`.
"""

from __future__ import annotations

import math

import pytest

from ureasim.data.unit_322e003 import (
    CCW_CP_KJKGK,
    CCW_KGH_DES,
    CCW_T_IN_DES_C,
    OVERFLOW_P_DES_BARA,
    OVERFLOW_T_DES_C,
    UA_KWK,
)
from ureasim.units.synthesis import scrubber
from ureasim.units.synthesis import scrubber_shell as shell


def test_the_condensing_temperature_is_its_anchor_at_design():
    """At the overflow line's 140.7 bar a the logarithm is a literal zero: 165 C exactly."""
    assert shell.condensing_temperature_c(OVERFLOW_P_DES_BARA) == OVERFLOW_T_DES_C == 165.0


def test_the_conductance_is_the_effectiveness_ntu_bridge():
    """eps . C on the datasheet's UA: 62.70 kW/K at the design circulation, whose C is 355.3 kW/K;
    with no water it falls to the floor, not to zero."""
    c = CCW_KGH_DES * CCW_CP_KJKGK / 3600.0
    assert shell.shell_conductance_kwk(CCW_KGH_DES) == (1.0 - math.exp(-UA_KWK / c)) * c
    assert shell.shell_conductance_kwk(CCW_KGH_DES) == pytest.approx(62.70, abs=1e-9)
    assert shell.shell_conductance_kwk(0.0) == shell.UA_EFF_FLOOR_KWK


def test_the_capacity_is_one_at_design_and_effectiveness_limited_off_it():
    """Exactly 1.0 at design; at half the water the UA-limited shell keeps 91.18 % of its
    capacity, where V1's flow ratio keeps 50 % (handoff B-99 (b1))."""
    assert shell.condensation_capacity(CCW_KGH_DES, 1.0, CCW_T_IN_DES_C, OVERFLOW_P_DES_BARA,
                                       1.0) == 1.0
    assert shell.condensation_capacity(CCW_KGH_DES / 2, 1.0, CCW_T_IN_DES_C, OVERFLOW_P_DES_BARA,
                                       1.0) == pytest.approx(0.911765, abs=1e-6)
    assert shell.condensation_capacity(CCW_KGH_DES / 2, 1.0, CCW_T_IN_DES_C, OVERFLOW_P_DES_BARA,
                                       1.0, effectiveness=False) == 0.5


def test_scrubber_re_exports_every_name():
    for name in shell.__all__:
        assert getattr(scrubber, name) is getattr(shell, name), name
        assert name in scrubber.__all__, name
