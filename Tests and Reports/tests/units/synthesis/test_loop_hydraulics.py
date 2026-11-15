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


#: The reactor's feed at the design seed [kmol/h], rounded: the line's mass factor.
_R001_FEED = {"NH3": 7399.37, "CO2": 2403.50, "H2O": 957.17, "Urea": 0.43, "N2": 45.42,
              "CH4": 4.00, "H2": 2.12, "O2": 7.39}


def test_the_reactors_pt_holds_v1s_reading_until_the_melt_flashes_decided_divergence():
    """B-109, decided 2026-10-22. At the design (the melt exactly at 322E002's 144.2) and below the
    cap both read V1's — 136.12 bar a on the design seed's feed, 134.92 with the melt at 143.0. A
    CO2-rich melt at 216 bar a on a loop at 151 (S5-6c): V1's PT reads 231.70; capped at 322E002's
    154.5 the port's reads 170.20, V1's feed-line law still adding (151 - 144.2) x 2.31. N/C 2.6's
    ratio-law 264.33 at the design loop: V1 256.25, the port the design's 136.12. Both on V1's
    feed line, B-112's own test below."""
    for p_bub, p_syn, v1_bara, port_bara in ((144.2, 140.7, 136.1208, 136.1208),
                                             (143.0, 140.7, 134.9208, 134.9208),
                                             (216.0, 151.0, 231.6968, 170.1968),
                                             (264.33, 140.7, 256.2508, 136.1208)):
        theirs = lh.reactor_bara(p_bub, p_syn, _R001_FEED, 170.0, flash_cap=False,
                                 design_drop=False)
        ours = lh.reactor_bara(p_bub, p_syn, _R001_FEED, 170.0, design_drop=False)
        assert (theirs, ours) == (pytest.approx(v1_bara, abs=1e-4),
                                  pytest.approx(port_bara, abs=1e-4))
    assert lh.reactor_bara(143.0, 140.7, _R001_FEED, 170.0, design_drop=False) == lh.reactor_bara(
        143.0, 140.7, _R001_FEED, 170.0, flash_cap=False, design_drop=False)


def test_the_reactors_pt_takes_its_feed_lines_design_drop_decided_divergence():
    """B-112, decided 2026-10-22. V1's feed line drops ``p_syn - 144.2`` times 2.31 at design (the
    nominal 990 kg/m3 over the correlation's 752.2, the seed's 250 639 kg/h over the condenser's
    189 258): 136.12 bar a where PFD 203/207 put the reactor's top at 141.3, and 3.31 bar per bar
    of PT-329201 under B-109's cap. The port's line is the PFD's 144.2 - 141.3 on the seed's feed:
    141.30 at design, 140.10 with the melt at 143.0, 151.60 on a 151 loop and 152.60 on a 152 one
    — one bar per bar — where V1's reads 170.20 and 173.51. A feed 20 % lighter drops 2.9 x 0.64:
    142.344; a 160 C feed, denser, 141.318."""
    light = {k: 0.8 * v for k, v in _R001_FEED.items()}
    for p_bub, p_syn, feed, t_c, v1_bara, port_bara in (
            (144.2, 140.7, _R001_FEED, 170.0, 136.1208, 141.3000),
            (143.0, 140.7, _R001_FEED, 170.0, 134.9208, 140.1000),
            (216.0, 151.0, _R001_FEED, 170.0, 170.1968, 151.6000),
            (216.0, 152.0, _R001_FEED, 170.0, 173.5051, 152.6000),
            (144.2, 140.7, light, 170.0, 139.0293, 142.3440),
            (144.2, 140.7, _R001_FEED, 160.0, 136.1705, 141.3179)):
        theirs = lh.reactor_bara(p_bub, p_syn, feed, t_c, design_drop=False)
        ours = lh.reactor_bara(p_bub, p_syn, feed, t_c)
        assert (theirs, ours) == (pytest.approx(v1_bara, abs=1e-4),
                                  pytest.approx(port_bara, abs=1e-4))
    rise = (lh.reactor_bara(216.0, 152.0, _R001_FEED, 170.0)
            - lh.reactor_bara(216.0, 151.0, _R001_FEED, 170.0))
    assert rise == pytest.approx(1.0, abs=1e-12)
