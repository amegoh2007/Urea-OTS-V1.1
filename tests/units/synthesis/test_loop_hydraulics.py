"""The synthesis loop's line pressures: each unit on its design offset from PT-329201."""

from __future__ import annotations

import pytest

from ureasim.data.unit_322r001 import OFFGAS_DES_KMOLH, OVERFLOW_DES_KMOLH
from ureasim.units.synthesis import loop_hydraulics as lh


def test_at_design_every_line_is_its_design_differential():
    """140.0 / 144.2 at the ejector, 144.0 on the stripper's tubes, 141.3 on the off-gas line,
    TT-322014's 183 C as the stripper's feed — to the bit."""
    assert lh.ejector_pressures_bara(140.7) == (140.0, 144.2)
    assert lh.stripper_feed_t_c(183.0) == 183.0
    assert lh.stripper_tube_bara(140.7, dict(OVERFLOW_DES_KMOLH), 183.0) == 144.0
    assert lh.reactor_offgas_bara(140.7, dict(OFFGAS_DES_KMOLH), 183.0) == 141.3


def test_a_heavier_207_run_drops_more():
    """10 % more overflow: the tube side 3.3 x 1.21 = 3.99 bar above the loop."""
    more = {k: 1.1 * v for k, v in OVERFLOW_DES_KMOLH.items()}
    assert lh.stripper_tube_bara(140.7, more, 183.0) == pytest.approx(144.693, abs=1e-3)


def test_the_ejector_rides_the_live_loop():
    """The lift stays 4.2 bar when the loop moves; both ends move with it."""
    s, d = lh.ejector_pressures_bara(138.0)
    assert (s, d) == pytest.approx((137.3, 141.5), abs=1e-9)


def test_a_hotter_off_gas_drops_more():
    """The off-gas's density falls with its temperature: the same flow drops more."""
    hot = lh.reactor_offgas_bara(140.7, dict(OFFGAS_DES_KMOLH), 200.0)
    assert hot - 140.7 == pytest.approx(0.6 * (200.0 + 273.15) / (183.0 + 273.15), rel=1e-12)
