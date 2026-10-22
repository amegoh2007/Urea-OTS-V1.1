"""323D002's design basis — `ureasim.data.unit_323d002` (split from `unit_323`, 2026-10-23).

Pins the stage-4 design values the move must not change, each measured before it was written, and
the re-export through `unit_323`.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_323
from ureasim.data import unit_323d002 as d002


def test_the_tank():
    """Compartment I 80 m3, 92 080 kg full on PFD 317's 1151 kg/m3, 9208 kg at its 10 % set
    point; Compartment II 300 m3."""
    assert (d002.D002_VOL_I_M3, d002.D002_VOL_II_M3, d002.D002_LVL_SP_PCT) == (80.0, 300.0, 10.0)
    assert d002.D002_M_I_FULL_KG == pytest.approx(92080.0, abs=1e-9)
    assert d002.D002_M_I_DES_KG == pytest.approx(9208.0, abs=1e-9)


def test_the_valve_and_controllers():
    """FV-324401's modified equal-percentage trim from 72.36 %; FT-324401's 110 m3/h span 126.61
    t/h, so FIC-324401's table gain 0.40 is 0.3159 %/(t/h)."""
    assert d002.FV401_CHAR == "mod_equal_pct"
    assert d002.FV401_OP_DES_PCT == pytest.approx(72.3587, abs=1e-4)
    assert d002.FT_324401_SPAN_TH == pytest.approx(126.61, abs=1e-9)
    assert d002.FIC_324401_KC == pytest.approx(0.315931, abs=1e-6)
    assert (d002.LIC_323507_KC, d002.LIC_323507_TI_S, d002.FT_324401_TAU_S) == (1.0, 4030.0, 5.0)


def test_unit_323_re_exports_every_name():
    for name in d002.__all__:
        assert getattr(unit_323, name) is getattr(d002, name), name
        assert name in unit_323.__all__, name
