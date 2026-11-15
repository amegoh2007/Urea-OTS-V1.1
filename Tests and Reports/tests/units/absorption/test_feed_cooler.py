"""Behaviour of 322E006, the LP absorber feed cooler — `ureasim.units.absorption.feed_cooler`.

V1 has no 322E006: it fixes 755 at 40 C. The exchanger is the rewrite's, decided by the process
engineer on 2026-10-01 (handoff B-54); what V1 does instead is asserted beside it in
`tests/equivalence/test_lp_absorber_decided_equivalence.py`. This file pins the exchanger: the
datasheet's UA reproduces its own rating case, the design point is the PFD's to the bit on PFD 28's
cooling water with the UA re-anchored (decision 151), and 755
answers the cooling water, the load and 744's temperature the way a counter-current plate
exchanger must.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_322e006 as d
from ureasim.units.absorption import feed_cooler as fc


def test_the_datasheet_ua_reproduces_its_own_rating_case():
    """UA = 222 kW over the rated LMTD, 7.2135 K: 30.776 kW/K, U = 4779 W/(m2 K) on 6.44 m2. On it,
    the rating case — 38 200 kg/h from 45 C against 19 150 kg/h of water from 30 C — comes out at
    40.015 C and 222.1 kW, the datasheet's 40.00 C and 222 kW to the heat capacities' rounding."""
    assert d.E006_UA_KW_K == pytest.approx(30.7757, abs=1e-4)
    assert d.E006_UA_KW_K / d.E006_AREA_M2 * 1000.0 == pytest.approx(4778.8, abs=0.1)
    r = fc.feed_cooler_322e006(d.E006_M_HOT_DS_KGH, d.E006_T_HOT_IN_DS_C, d.E006_M_CW_DS_KGH,
                               ua_kw_k=d.E006_UA_KW_K)
    assert (r.t_755_c, r.q_kw, r.t_cw_out_c) == (pytest.approx(40.015, abs=1e-3),
                                                 pytest.approx(222.12, abs=0.01),
                                                 pytest.approx(40.003, abs=1e-3))


def test_the_design_point_is_the_pfds_to_the_bit():
    """Decision 151. PFD 744 at 44 C to PFD 755 at exactly 40.0 C: 146.9 kW against PFD 28's 14 t/h
    of cooling water (streams 1010 / 1011), returning at 39.05 C against PFD 28's rounded 40, on
    the UA back-solved for it, 20.448 kW/K, two-thirds of the datasheet's 30.776. On the datasheet
    UA that water would bring 755 to 39.23 C; the datasheet's 19 150 kg/h, on the anchored UA, to
    39.54 C. Before PFD 28 was read the port back-solved the water instead, 10 374 kg/h."""
    assert fc.DESIGN.t_755_c == d.E006_T755_DES_C == 40.0
    assert fc.E006_M_CW_DES_KGH == d.E006_M_CW_PFD_KGH == 14000.0
    assert fc.E006_UA_DES_KW_K == pytest.approx(20.448, abs=1e-3)
    assert (fc.DESIGN.q_kw, fc.DESIGN.t_cw_out_c) == (pytest.approx(146.875, abs=1e-3),
                                                      pytest.approx(39.048, abs=1e-3))
    on_ds = fc.feed_cooler_322e006(d.E006_M744_DES_KGH, d.E006_T744_DES_C, 14000.0,
                                   ua_kw_k=d.E006_UA_KW_K)
    assert on_ds.t_755_c == pytest.approx(39.227, abs=1e-3)
    full = fc.feed_cooler_322e006(d.E006_M744_DES_KGH, d.E006_T744_DES_C, d.E006_M_CW_DS_KGH)
    assert full.t_755_c == pytest.approx(39.545, abs=1e-3)


@pytest.mark.parametrize("frac, t_755", [(0.0, 44.0), (0.25, 42.468), (0.5, 41.255),
                                         (0.75, 40.490), (1.5, 39.427)])
def test_755_follows_the_cooling_water(frac, t_755):
    """The cooling water throttled or lost: 755 warms toward 744's 44 C, which it reaches with no
    water at all — the absorber's wash then as warm as compartment I."""
    r = fc.feed_cooler_322e006(d.E006_M744_DES_KGH, d.E006_T744_DES_C,
                               fc.E006_M_CW_DES_KGH * frac)
    assert r.t_755_c == pytest.approx(t_755, abs=1e-3)


def test_a_warmer_tank_a_lighter_load_and_warmer_water():
    """Compartment I at 50 C: 755 at 44.3 C. 744 cut to 60 %: 37.8 C, the plates over-cool a
    lighter load. The cooling water supplied at 35 C: 41.4 C."""
    m, cw = d.E006_M744_DES_KGH, fc.E006_M_CW_DES_KGH
    assert fc.feed_cooler_322e006(m, 50.0, cw).t_755_c == pytest.approx(44.286, abs=1e-3)
    assert fc.feed_cooler_322e006(0.6 * m, 44.0, cw).t_755_c == pytest.approx(37.821, abs=1e-3)
    assert fc.feed_cooler_322e006(m, 44.0, cw, 35.0).t_755_c == pytest.approx(41.429, abs=1e-3)


def test_no_flow_on_either_side_crosses_nothing():
    """322P002 stopped or the cooling water shut: no duty, 755 at 744's temperature."""
    for m744, mcw in ((0.0, fc.E006_M_CW_DES_KGH), (d.E006_M744_DES_KGH, 0.0)):
        r = fc.feed_cooler_322e006(m744, 44.0, mcw)
        assert (r.q_kw, r.t_755_c, r.eps) == (0.0, 44.0, 0.0)


def test_the_effectiveness_limits():
    """Balanced capacities, NTU / (1 + NTU); a condensing-like side, 1 - exp(-NTU); no area, 0."""
    assert fc.effectiveness(2.0, 1.0) == pytest.approx(2.0 / 3.0, rel=1e-15)
    assert fc.effectiveness(2.0, 0.0) == pytest.approx(0.864665, abs=1e-6)
    assert fc.effectiveness(0.0, 0.5) == 0.0
