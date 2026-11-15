"""Behaviour of the condensing-steam chest — `ureasim.units.steam_chest`, on 323E002.

Equivalence with V1 is in `tests/equivalence/test_steam_chest_equivalence.py`, and the chest is
driven tick by tick inside the 323C003 equivalence test as well. Every number here was measured
before it was written.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_323 as d
from ureasim.data.unit_329 import P_LP_BARA
from ureasim.thermo import iapws
from ureasim.units.steam_chest import chest_residual_kw, steam_chest_pressure


def _chest(stroke_pct: float, header_bara: float = P_LP_BARA, t_process_c: float = 135.0):
    return steam_chest_pressure(stroke_pct, header_bara, d.E002_OP_DES_PCT,
                                d.E002_PCHEST_DES_BARA, d.E002_UA_KW, t_process_c,
                                d.E002_Q_DES_KW, P_LP_BARA)


def test_the_design_stroke_gives_the_datasheet_chest_pressure():
    assert _chest(d.E002_OP_DES_PCT) == d.E002_PCHEST_DES_BARA


def test_a_shut_valve_lands_the_chest_on_the_process_saturation_pressure():
    """No steam admitted, no heat: the chest settles where condensation stops, which is the
    process temperature's own saturation pressure."""
    assert _chest(0.0) == pytest.approx(iapws.psat_bara(135.0), abs=1e-12)


def test_a_process_hotter_than_the_header_drives_the_chest_to_the_header():
    assert iapws.tsat_c(P_LP_BARA) < 160.0
    assert _chest(d.E002_OP_DES_PCT, t_process_c=160.0) == pytest.approx(P_LP_BARA, abs=1e-9)


def test_the_chest_rises_with_the_stroke_but_far_less_than_the_stroke():
    """The wall condenses more as the chest rises, so 20 to 100 % stroke moves the chest only
    3.35 to 4.07 bar a on the 3.9 bar a datasheet anchor."""
    strokes = (20.0, 40.0, 60.0, 90.0, 100.0)
    p = [_chest(s) for s in strokes]
    assert p == sorted(p)
    assert p[0] == pytest.approx(3.3469, abs=1e-4)
    assert p[-1] == pytest.approx(4.0715, abs=1e-4)


def test_a_sagging_header_starves_the_chest():
    assert _chest(d.E002_OP_DES_PCT, header_bara=4.6) == pytest.approx(3.7746, abs=1e-4)


def test_the_residual_is_zero_at_design_and_falls_with_pressure():
    args = (d.E002_OP_DES_PCT, P_LP_BARA, d.E002_OP_DES_PCT, d.E002_PCHEST_DES_BARA,
            P_LP_BARA, d.E002_UA_KW, 135.0, d.E002_Q_DES_KW)
    assert chest_residual_kw(d.E002_PCHEST_DES_BARA, *args) == pytest.approx(0.0, abs=1e-9)
    assert chest_residual_kw(3.5, *args) > 0.0 > chest_residual_kw(4.5, *args)


def test_the_chest_gain_pic_329202_works_against():
    """0.0083 bar per per cent of stroke at design: PIC-329202's 10.83 %/bar on span (the table's
    0.65 on PT-329202's 6 bar) makes a loop gain of 0.090, a slave settling in about six
    minutes against a temperature master whose integral time is 500 s."""
    slope = (_chest(d.E002_OP_DES_PCT + 0.5) - _chest(d.E002_OP_DES_PCT - 0.5)) / 1.0
    assert slope == pytest.approx(0.008295, abs=1e-6)
    assert d.PIC_329202_KC * slope == pytest.approx(0.0899, abs=1e-4)
