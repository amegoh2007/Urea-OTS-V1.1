"""Behaviour of a unit 324 condenser as a flowsheet node — `ureasim.units.evaporation.condenser_node`.

Equivalence with V1 is proven in `tests/equivalence/test_condenser_node_equivalence.py`. This file
pins what the node DOES: the design books by construction, the vent answering the false air the
vacuum controller admits, a condenser that has lost its water venting everything, and the
blow-through gas replacing part of the PFD row.
"""

from __future__ import annotations

import pytest

from ureasim.units.evaporation import condenser_node as cn
from ureasim.units.evaporation import vacuum_condenser as vc

E002 = vc.design_specs()["324E002"]


def test_the_design_inlet_is_the_pfd_row_and_the_books_close():
    """At design the live inlet is the PFD row exactly; 324E002 vents 72 kg/h and condenses
    26 768, 324E005 584 and 2758, with nothing left over."""
    n = cn.inlet_kmolh("324E002", E002.inlet_kgh, 21.0, 21.0)
    assert n == E002.n_in_des
    node = cn.condenser_node("324E002", E002.inlet_kgh, n, E002.p_des)
    assert (node.vent_kgh, node.condensate_kgh, node.mass_residual_kgh) == (72.0, 26768.0, 0.0)
    assert node.t_vent_c == pytest.approx(45.0, abs=1e-9)
    assert abs(node.energy_residual_kw) < 1e-6
    e005 = vc.design_specs()["324E005"]
    d5 = cn.condenser_node("324E005", e005.inlet_kgh,
                           cn.inlet_kmolh("324E005", e005.inlet_kgh, 21.0, 21.0), e005.p_des)
    assert (d5.vent_kgh, d5.condensate_kgh) == (584.0, 2758.0)


@pytest.mark.parametrize("air, n2, vent", [(42.0, 1.73922, 107.979), (63.0, 2.31470, 143.908)])
def test_false_air_swells_the_vent(air, n2, vent):
    """PIC-324202 admitting twice and three times its design 21 kg/h of false air: the inert gas
    the vent carries, and the vapour it holds saturated with it, take 324E002's vent from 72 to
    108 and 144 kg/h."""
    m_in = E002.inlet_kgh - 21.0 + air
    n = cn.inlet_kmolh("324E002", m_in, air, 21.0)
    node = cn.condenser_node("324E002", m_in, n, E002.p_des)
    assert n["N2"] == pytest.approx(n2, abs=1e-5)
    assert node.vent_kgh == pytest.approx(vent, abs=1e-3)
    assert abs(node.mass_residual_kgh) < 1e-9       # the subtraction's own rounding


def test_a_condenser_without_water_vents_everything():
    """324E002's cooling water lost: nothing condenses and the whole inlet, 26 840 kg/h, goes to
    324F002."""
    node = cn.condenser_node("324E002", E002.inlet_kgh, E002.n_in_des, E002.p_des, 0.0)
    assert (node.vent_kgh, node.condensate_kgh, node.q_kw) == (E002.inlet_kgh, 0.0, 0.0)


def test_blow_through_gas_replaces_part_of_the_row():
    """850 kg/h of LV-323505's blow-through gas (55 % NH3, 30 % CO2, 15 % water by mass) in
    324E002's inlet: 25.40 kmol/h more NH3 and 5.12 more CO2, 36.20 less water, the inerts
    untouched."""
    n = cn.inlet_kmolh("324E002", E002.inlet_kgh, 21.0, 21.0,
                       (850.0, {"NH3": 0.55, "CO2": 0.30, "H2O": 0.15}))
    d = {k: n[k] - E002.n_in_des[k] for k in n}
    assert (d["NH3"], d["CO2"], d["H2O"]) == (pytest.approx(25.3974, abs=1e-4),
                                              pytest.approx(5.1158, abs=1e-4),
                                              pytest.approx(-36.1989, abs=1e-4))
    assert d["N2"] == d["O2"] == 0.0
