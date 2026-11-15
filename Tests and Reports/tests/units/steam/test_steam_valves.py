"""Behaviour of unit 329's valves — `ureasim.units.steam.steam_valves`.

V1's butterfly law is proven ``==`` V1's ``_valve_flow`` in
`tests/equivalence/test_steam_network_equivalence.py`; this file pins the vendor globes at their
design strokes, the letdowns' choke, and the butterflies on their loop summaries' cases.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_329_network as n
from ureasim.units.steam import steam_valves as sv


def test_the_globes_pass_their_design_flows_at_their_design_strokes():
    """LV-329502 904's 57 989 kg/h at 86.87 %, LV-329503 913's 53 056 at 58.88 %, LV-329504 the
    closure's 19 501 at 48.26 %, PV-329205A 903's 1754 at 19.55 %; PV-329205B 10 486 wide open
    on its sizing case."""
    assert sv.lv_329502_kgs(n.LV502_OP_DES_PCT, 19.7, 9.0) * 3600.0 == pytest.approx(57989.0,
                                                                                    rel=1e-12)
    assert sv.lv_329503_kgs(n.LV503_OP_DES_PCT, 9.0, 5.01325) * 3600.0 == pytest.approx(
        53056.0, rel=1e-12)
    assert sv.lv_329504_kgs(n.LV504_OP_DES_PCT, 5.01325) * 3600.0 == pytest.approx(19501.0,
                                                                                  rel=1e-12)
    assert sv.pv_329205a_kgs(n.PV205A_OP_DES_PCT, 25.0, 9.0) * 3600.0 == pytest.approx(
        1754.0, rel=1e-12)
    assert sv.pv_329205b_kgs(100.0, 8.9, 4.4) * 3600.0 == pytest.approx(10486.18, abs=0.01)
    assert sv.pv_329205a_kgs(0.0, 25.0, 9.0) == 0.0


def test_lv_329502_chokes_on_its_saturated_condensate():
    """Decision 31: handed 329D005's pressure as its vapour pressure, LV-329502 passes the same
    57 989 kg/h whether 329D009 is at 9 or 5 bar a — it is choked, as Flowserve sized it; it
    unchokes only when 329D009 rises to within 1.2 bar of 329D005 (44 027 kg/h at 18.5)."""
    assert sv.lv_329502_kgs(n.LV502_OP_DES_PCT, 19.7, 5.0) * 3600.0 == pytest.approx(57989.0,
                                                                                    rel=1e-12)
    assert sv.lv_329502_kgs(n.LV502_OP_DES_PCT, 19.7, 18.5) * 3600.0 == pytest.approx(
        44026.9, abs=0.1)


def test_the_butterflies_on_their_loop_summaries():
    """§4: wide open, HV-329601 passes its sheet's 8000 kg/h from 17.0 to 1.5 bar a and 9200
    from 329D005's 19.7 bar a to atmosphere (V1's coefficient: 288 t/h); PV-329207C 32 000 from
    20 to 7 and 39 600 from the 25 bar a supply into the LP header, choked; PV-329207A 65 000 from
    4.0 to 2.0 and 83 400 from the LP header to atmosphere."""
    assert sv.steam_valve_kgs(n.K_HV601, 100.0, 17.0, 1.5) * 3600.0 == pytest.approx(8000.0,
                                                                                    rel=1e-12)
    assert sv.steam_valve_kgs(n.K_HV601, 100.0, 19.7, 1.01325, n.HV601_P1_DES_BARA,
                              n.HV601_P2_DES_BARA) * 3600.0 == pytest.approx(9200.46, abs=0.01)
    assert sv.steam_valve_kgs(n.K_963, 100.0, 20.0, 7.0) * 3600.0 == pytest.approx(32000.0,
                                                                                  rel=1e-12)
    assert sv.steam_valve_kgs(n.K_963, 100.0, 25.0, 5.01325, n.P963_P1_DES_BARA,
                              n.P963_P2_DES_BARA) * 3600.0 == pytest.approx(39599.21, abs=0.01)
    assert sv.steam_valve_kgs(n.K_207A, 100.0, 4.0, 2.0) * 3600.0 == pytest.approx(65000.0,
                                                                                  rel=1e-12)
    assert sv.steam_valve_kgs(n.K_207A, 100.0, 5.01325, 1.01325, n.P207A_P1_DES_BARA,
                              n.P207A_P2_DES_BARA) * 3600.0 == pytest.approx(83432.75, abs=0.01)


def test_the_three_vendor_globes_on_their_sheets():
    """Decision 150, both sides. Wide open each passes its full-stroke capacity on its normal case:
    HV-329601 16 151 kg/h from 19.9 to 1.5 bar a, PV-329207C 34 882 and HV-329602 39 233 from 22.0
    to 4.4. At its sheet's maximum case HV-329601 at 82 % passes 6917 kg/h from 17.1 bar a where the
    sheet sizes 8000 (its travels sit off the 50:1 curve); V1's law, on the loop summary's maximum
    case at full stroke, 8000 wide open from 17.0. Into the design LP header from the 25 bar a
    supply PV-329207C wide open passes 39 371 kg/h, V1's law 39 599."""
    assert sv.hv_329601_kgs(100.0, 19.9) * 3600.0 == pytest.approx(16150.74, abs=0.01)
    assert n.PV207C_FULL_KGS * 3600.0 == pytest.approx(34882.07, abs=0.01)
    assert n.HV602_FULL_KGS * 3600.0 == pytest.approx(39233.23, abs=0.01)
    assert sv.hv_329601_kgs(82.0, 17.1) * 3600.0 == pytest.approx(6916.99, abs=0.01)
    assert sv.hv_329601_kgs(0.0, 19.7) == sv.pv_329207c_kgs(0.0, 5.0) == 0.0
    assert sv.pv_329207c_kgs(100.0, 5.01325) * 3600.0 == pytest.approx(39370.66, abs=0.01)
    assert sv.steam_valve_kgs(n.K_963, 100.0, 25.0, 5.01325, n.P963_P1_DES_BARA,
                              n.P963_P2_DES_BARA) * 3600.0 == pytest.approx(39599.21, abs=0.01)


def test_pv_329204_passes_pfd_902_at_its_seed():
    """Decision 47: 57 989 kg/h at 50 %, 25 -> 19.7 bar a."""
    assert sv.steam_valve_kgs(n.K_902, 50.0, 25.0, 19.7, 25.0, 19.7) * 3600.0 == pytest.approx(
        57989.0, rel=1e-12)
