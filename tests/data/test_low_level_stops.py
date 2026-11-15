"""The four low-level stops' stand-in limits (decision 217, data gap 8)."""

from __future__ import annotations

from ureasim.data import low_level_stops as stops
from ureasim.data.unit_323e011 import LT_323503_L2_HYST_PCT, LT_323503_L2_PCT


def test_every_stop_takes_lt_323503s_read_back_limit_and_hysteresis():
    """The process engineer's stand-in of 2026-11-15: each pair's L2 is LT-323503's DCS L2, and its
    hysteresis 323P008's 2-unit stand-in (decision 111's class)."""
    assert set(stops.L2_PCT) == {"LT-328501", "LT-328503", "LT-328505", "LY-324501"}
    assert all(v == LT_323503_L2_PCT == 5.0 for v in stops.L2_PCT.values())
    assert stops.L2_HYST_PCT == LT_323503_L2_HYST_PCT == 2.0
