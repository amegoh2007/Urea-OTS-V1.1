"""Behaviour of unit 324's vacuum condensers — `ureasim.units.evaporation.vacuum_condenser`.

Equivalence with V1 is proven in `tests/equivalence/test_vacuum_condenser_equivalence.py`. This
file pins what a condenser DOES: the PFD's vents at design, by construction; and the cold end and
the vent answering the cooling water and the shell pressure, which is what loads the ejector
behind it.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_324 as d
from ureasim.units.evaporation import vacuum_condenser as vc

PFD_VENT = {"324E002": 72.0, "324E005": 584.0, "324E006": 41.0, "324E007": 31.0}


def _solve(tag, p=1.0, cw=1.0, cw_in=None):
    s = vc.design_specs()[tag]
    return s, vc.solve(s, s.p_des * p, s.n_in_des, s.t_in_des, s.cw_flow_kgh * cw,
                       s.cw_in_c if cw_in is None else cw_in)


@pytest.mark.parametrize("tag", list(PFD_VENT))
def test_the_design_vents_are_the_pfds(tag):
    """Each condenser at its design: the anchored vent is the PFD's to the bit, the cold end its
    PFD temperature to 4e-8 K (the falsi's stop; 324E007's 3.6e-8 since B-71)."""
    s, r = _solve(tag)
    assert vc.vent_kgh(s, r) == PFD_VENT[tag] == s.vent_kgh
    assert r.t_vent_c == pytest.approx(d.VACUUM_CONDENSERS[tag].hot_out_c, abs=4e-8)


def test_324e002s_balance_against_its_cooling_water():
    """324E002 at design: the H0 balance gives 18 019 kW against the 18 460 its cooling water
    carries (the H0 tier's missing mixing and carbamate heat), on a back-solved UA of 478.4 kW/K;
    the water leaves at 39.76 C."""
    s, r = _solve("324E002")
    assert (s.q_des_kw, s.ua_kw_k) == (pytest.approx(18018.66, abs=0.01),
                                       pytest.approx(478.374, abs=1e-3))
    assert d.VACUUM_CONDENSERS["324E002"].q_kw == pytest.approx(18460.0, rel=1e-12)
    assert r.cw_out_c == pytest.approx(39.761, abs=1e-3)


def test_less_or_warmer_water_lifts_the_cold_end_and_the_vent():
    """324E002's water halved: the cold end rises to 48.35 C and the vent to 85.3 kg/h; supplied at
    35 C instead of 30, 51.23 C and 106.1 kg/h (B-67's departures; V1's ratio gives 87.0 and
    111.6); lost, nothing condenses: every vapour and the inert gas leave for the ejector, and only
    the entrained urea drains."""
    s, half = _solve("324E002", cw=0.5)
    assert (half.t_vent_c, vc.vent_kgh(s, half)) == (pytest.approx(48.354, abs=1e-3),
                                                     pytest.approx(85.326, abs=1e-3))
    s, warm = _solve("324E002", cw_in=35.0)
    assert (warm.t_vent_c, vc.vent_kgh(s, warm)) == (pytest.approx(51.226, abs=1e-3),
                                                     pytest.approx(106.113, abs=1e-3))
    s, lost = _solve("324E002", cw=0.0)
    assert lost.q_kw == 0.0 and lost.t_vent_c == s.t_in_des
    assert all(lost.vent_kmolh[k] == s.n_in_des[k] for k in ("H2O", "NH3", "CO2", "N2", "O2"))
    assert lost.condensate_model_kgh == pytest.approx(s.n_in_des["Urea"] * 60.056, rel=1e-3)


def test_a_falling_shell_pressure_swells_the_vent():
    """The shell 20 % below its design vacuum holds more vapour per mole of inert: 92.5 kg/h
    leave 324E002; 25 % above, 61.9 (B-67's departures move the third decimal)."""
    s, low = _solve("324E002", p=0.8)
    s, high = _solve("324E002", p=1.25)
    assert vc.vent_kgh(s, low) == pytest.approx(92.546, abs=1e-3)
    assert vc.vent_kgh(s, high) == pytest.approx(61.895, abs=1e-3)
