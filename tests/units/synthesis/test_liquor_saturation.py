"""The loop liquor at its bubble point — `ureasim.units.synthesis.liquor_saturation`.

Pinned: the reactor liquor's buffering read once off the design (decision 95); the saturation
fraction, exactly 1 at the design and at or above the melt's bubble pressure, falling by b_207 per
bar the loop stands below it and floored at zero (decided 2026-10-10, handoff B-91 (a)); and
322E002 holding only that fraction of its condensing volatiles, its exotherm and its outlet
temperature with them.
"""

from __future__ import annotations

import pytest

from ureasim.data.unit_320 import SYN_P_DES_BARA
from ureasim.data.unit_322_loop import LIQUOR_DP_DES_BAR
from ureasim.data.unit_322e002 import P_DES_BARA
from ureasim.units.synthesis import loop_pressure
from ureasim.units.synthesis.liquor_saturation import B_207_PER_BAR, saturation_fraction
from tests.units.synthesis.test_carbamate_condenser import run


def test_the_buffering_is_read_once_at_the_design():
    """0.01536 kg of loop gas per kg of PFD 207's liquor per bar; PT-329201's node reads the same
    object (decision 95)."""
    assert B_207_PER_BAR == pytest.approx(0.015364, abs=1e-6)
    assert loop_pressure.B_207_PER_BAR is B_207_PER_BAR


def test_the_design_is_saturated_exactly():
    """PI-322E002's 144.2 bar a at the condenser outlet over PT-329201's 140.7 is the design head,
    a subtraction of the two design pressures (A-13): the fraction is a literal 1."""
    assert LIQUOR_DP_DES_BAR == P_DES_BARA - SYN_P_DES_BARA == 3.5
    assert saturation_fraction(P_DES_BARA, SYN_P_DES_BARA) == 1.0
    assert saturation_fraction(P_DES_BARA, SYN_P_DES_BARA + 5.0) == 1.0
    assert saturation_fraction(P_DES_BARA - 20.0, SYN_P_DES_BARA) == 1.0


@pytest.mark.parametrize("deficit_bar, frac", [(1.0, 0.984636), (10.0, 0.846361),
                                               (40.0, 0.385444), (65.0, 0.001348), (80.0, 0.0)])
def test_below_the_bubble_pressure_the_liquor_holds_less(deficit_bar, frac):
    """1 - b_207 per bar of deficit, nothing past 65.09 bar (1 / b_207)."""
    assert saturation_fraction(P_DES_BARA, SYN_P_DES_BARA - deficit_bar) == pytest.approx(
        frac, abs=1e-6)
    assert 1.0 / B_207_PER_BAR == pytest.approx(65.088, abs=1e-3)


def test_the_condenser_holds_its_fraction_of_the_volatiles():
    """322E002 at its design feed: at a fraction of 1 the call is the default's to the bit; at 0.5
    the melt holds half of each distributing species — 94.6 t/h of 189.3 — and all its urea; the
    absorbed CO2's exotherm falls from 62.6 to 20.9 MW, the outlet to 157.70 C and PI-322E002 to
    120.78 bar a; at 0 only the urea stays liquid."""
    full, half, none = run(), run(sat_frac=0.5), run(sat_frac=0.0)
    assert run(sat_frac=1.0) == full
    for k in ("CO2", "NH3", "H2O", "N2"):
        assert half.liq_kmolh[k] == pytest.approx(0.5 * full.liq_kmolh[k], rel=1e-12)
    assert half.liq_kmolh["Urea"] == full.liq_kmolh["Urea"]
    assert (full.liq_kgh, half.liq_kgh) == (pytest.approx(189257.5, abs=0.1),
                                            pytest.approx(94641.7, abs=0.1))
    assert (full.duty_kw, half.duty_kw) == (pytest.approx(62581.8, abs=0.1),
                                            pytest.approx(20938.7, abs=0.1))
    assert (full.t_prod, half.t_prod) == (170.0, pytest.approx(157.697, abs=1e-3))
    assert half.p_bub_bara == pytest.approx(120.779, abs=1e-3)
    assert {k for k, v in none.liq_kmolh.items() if v} == {"Urea"}


def test_322e003_reads_its_own_liquor_on_a_zero_design_head():
    """B-91, decided 2026-10-14: 322E003's sump liquor stands at the loop's own pressure at design
    (PFD 206 at 140.7 bar a), so its head is zero — exactly 1 there, 1 - b_207 per bar above."""
    from ureasim.units.synthesis.scrubber import LIQUOR_DP_DES_BAR
    assert LIQUOR_DP_DES_BAR == 0.0
    assert saturation_fraction(140.7, 140.7, LIQUOR_DP_DES_BAR) == 1.0
    assert saturation_fraction(150.7, 140.7, LIQUOR_DP_DES_BAR) == pytest.approx(
        1.0 - 10.0 * B_207_PER_BAR, rel=1e-12)
