"""Behaviour of the LP flash gas node's relations — `ureasim.units.recirc.flash_gas_node`.

Split from `flash_condenser` on 2026-10-16. Equivalence of the generation with V1's
``e011_vent_generation_kgh`` is proven in `tests/equivalence/test_flash_condenser_equivalence.py`
and the unit's behaviour in `tests/units/recirc/test_flash_condenser.py`, both through the unit's
re-exports; this file pins that the re-exports are these relations, and their design anchors.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_323e011 as e
from ureasim.units.recirc import flash_condenser as fc
from ureasim.units.recirc import flash_gas_node as gn


def test_the_unit_re_exports_the_node_relations():
    assert (fc.vent_generation_kgh, fc.dew_point_c, fc.condensation_capacity_kgh,
            fc.vent_valve_kgh) == (gn.vent_generation_kgh, gn.dew_point_c,
                                   gn.condensation_capacity_kgh, gn.vent_valve_kgh)


def test_the_design_node_is_the_pfd():
    """At 1.13 bar a: the dew point 45 C, 5589 kg/h condensed, PV-323203 passing PFD 702's 440 kg/h
    at its vendor design stroke, 21.64 %, and on V1's linear law at 25 %; V1's generation, the load
    above 5589."""
    assert gn.dew_point_c(e.E011_P_BARA) == e.E011_T_C
    assert gn.condensation_capacity_kgh(e.E011_P_BARA) == e.E011_CONDENSATION_CAPACITY_DES_KGH
    assert gn.PV_323203_TRIM[0] == pytest.approx(21.637, abs=1e-3)
    assert gn.vent_valve_kgh(gn.PV_323203_TRIM[0], e.E011_P_BARA) == pytest.approx(
        e.E011_MV_DES_KGH, rel=1e-15)
    assert gn.vent_valve_kgh(e.E011_PV_OP_DES_PCT, e.E011_P_BARA, trim=None) == pytest.approx(
        e.E011_MV_DES_KGH, rel=1e-15)
    assert gn.vent_generation_kgh(e.E011_CONDENSATION_CAPACITY_DES_KGH + 440.0) == 440.0


def test_the_vent_passes_nothing_at_or_below_the_absorber():
    """B-30 (decided 2026-10-15): no differential, no flow; V1's 0.001 bar floor still passes."""
    assert gn.vent_valve_kgh(25.0, 1.0) == gn.vent_valve_kgh(25.0, 0.9) == 0.0
    assert gn.vent_valve_kgh(25.0, 0.9, e.VENT_DP_FLOOR_BAR) > 0.0


def test_pv_323203_on_its_vendor_trim():
    """Decision 23's class, decided 2026-10-17: at the design node Metso's Neldisc passes PFD 702 at
    21.64 % and 2.70 times it at the sheet's 44.6 % — the sheet's 1600 over 540 Nm3/h, its normal
    case 400 kg/h against PFD 702's 440 — where V1's linear law passes 1.78 times; wide open it
    passes 10.31 times PFD 702 against V1's 4.0. The valve is large for its duty, so it works low
    on its curve and its gain per per cent of stroke at design is 1.85 times V1's."""
    p = e.E011_P_BARA
    assert gn.vent_valve_kgh(44.6, p) / e.E011_MV_DES_KGH == pytest.approx(2.698, abs=1e-3)
    assert gn.vent_valve_kgh(44.6, p, trim=None) / e.E011_MV_DES_KGH == pytest.approx(1.784,
                                                                                      abs=1e-9)
    assert gn.vent_valve_kgh(0.0, p) == 0.0
    assert gn.vent_valve_kgh(100.0, p) / e.E011_MV_DES_KGH == pytest.approx(10.310, abs=1e-3)
    assert gn.vent_valve_kgh(100.0, p, trim=None) / e.E011_MV_DES_KGH == pytest.approx(4.0,
                                                                                       rel=1e-12)
    des = gn.PV_323203_TRIM[0]
    gain = (gn.vent_valve_kgh(des + 0.5, p) - gn.vent_valve_kgh(des - 0.5, p)) / e.E011_MV_DES_KGH
    assert gain / (1.0 / 25.0) == pytest.approx(1.85, abs=0.01)
