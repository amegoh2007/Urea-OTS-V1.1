"""Behaviour of the steam-jet ejectors' maps — `ureasim.units.evaporation.ejector_map`.

The 1-D gas dynamics are V1's, proven in `tests/equivalence/test_ejector_gas_dynamics_equivalence.py`;
V1's straight lines against the maps run in `test_ejector_map_decided_equivalence.py`. This file
pins what the maps DO: each vendor duty point on the vendor's map, each PFD design load off the
decided table (handoff B-61, decided 2026-10-01), the table's agreement with the 1-D points it is
made of, the pull rising with the suction pressure down to the ejector's shut-off, the break above
the critical back pressure, the stall a motive sag brings, and the vendor's margin over the
design.
"""

from __future__ import annotations

import math
import random

import pytest

from ureasim.data import unit_324 as u324
from ureasim.units.evaporation import ejector_map as em

TAGS = ("324F002", "324F004", "324F005")


@pytest.mark.parametrize("tag, suction, p_crit, motive", [
    ("324F002", 94.0, 1.0, 650.0), ("324F004", 761.0, 0.35, 1061.0),
    ("324F005", 84.0, 1.16, 366.0),
])
def test_each_vendor_duty_point_is_on_the_vendor_map(tag, suction, p_crit, motive):
    """Uhde's vacuum-unit table and Körting's operating data: the suction capacity, the
    discharge pressure the ejector is critical at, and the motive steam, at the duty's
    pressures on the vendor's map; the decided map breaks at the same discharge."""
    m = em.vendor_map(tag)
    d = m.duty
    assert em.critical_capacity_kgh(m, d.p_suction_bara, d.p_motive_bara) == pytest.approx(
        suction, rel=1e-12)
    assert em.critical_back_pressure_bara(m, d.p_suction_bara, d.p_motive_bara) == (
        pytest.approx(p_crit, rel=1e-12))
    assert em.interpolated(tag, d.p_suction_bara, d.p_motive_bara)[1] == pytest.approx(
        p_crit, rel=1e-12)
    assert em.motive_kgh(m, d.p_motive_bara) == pytest.approx(motive, rel=1e-12)


@pytest.mark.parametrize("tag, suction, p_suction, p_discharge, motive", [
    ("324F002", 72.0, 0.33, 1.0, 390.0), ("324F004", 584.0, 0.131, 0.3, 1220.0),
    ("324F005", 41.0, 0.3, 1.0, 180.0),
])
def test_each_design_load_comes_off_the_table_b61(tag, suction, p_suction, p_discharge, motive):
    """Handoff B-61, decided 2026-10-01: PFD 706, 712 and 715 at the design vacuums and the
    duty's 4.1 bar a of motive, read off the decided table to rounding, critical against the
    design discharge; the design motive flow — the PFD's 924, 927 and 929 (B-64) — is the duty's
    motive pressure."""
    p_m = em.nozzle_pressure_bara(tag, motive)
    assert p_m == 4.1
    assert em.suction_capacity_kgh(tag, p_suction, p_m, p_discharge) == pytest.approx(
        suction, rel=1e-14)


def test_the_nozzle_pressure_is_anchored_on_the_pfds_motive_b64():
    """Handoff B-64, decided 2026-10-02, option a: PFD 927's 1220 and 929's 180 kg/h put the
    nozzles at the duty's 4.1 bar a, as 924's 390 does 324F002's. Uhde's 1061 and 366, the
    flows the nozzles are rated for, would have read 3.566 and 8.337 bar a; the nozzles still
    pass them at 4.1 (`motive_kgh`)."""
    assert u324.EJECTOR_DESIGN_LOADS["324F004"].motive_kgh == 1220.0
    assert u324.EJECTOR_DESIGN_LOADS["324F005"].motive_kgh == 180.0
    assert em.nozzle_pressure_bara("324F004", 1061.0) == pytest.approx(3.5657, abs=1e-4)
    assert em.nozzle_pressure_bara("324F005", 366.0) == pytest.approx(8.3367, abs=1e-4)
    assert em.motive_kgh(em.ejector_map("324F004"), 4.1) == pytest.approx(1061.0, rel=1e-12)
    assert em.motive_kgh(em.ejector_map("324F005"), 4.1) == pytest.approx(366.0, rel=1e-12)


def test_the_nozzles_and_throats_are_the_vendors():
    """The motive flows Uhde's table gives choke through 98.1 and 98.2 % of Körting's 24.7 and
    14.5 mm orifices; the mixing throats are the drawings' 106.5 and 30.8 mm, which the loss-free
    model under- and over-states by 33 and 13 % on the vendor duty. 324F002 has no throat in the
    archive: on its duty the loss-free model puts it at 44.4 mm, 5.40 times its 19.1 mm nozzle.
    On the design loads (B-61) K is 0.919, 0.497 and 0.336 — the decided map keeps every throat
    and the break."""
    m4, m5, m2 = (em.vendor_map(t) for t in ("324F004", "324F005", "324F002"))
    area = lambda d_mm: math.pi / 4.0 * (d_mm / 1000.0) ** 2   # noqa: E731
    assert m4.throat_m2 / area(24.7) == pytest.approx(0.98096, abs=1e-5)
    assert m5.throat_m2 / area(14.5) == pytest.approx(0.98191, abs=1e-5)
    assert (m4.mixing_m2, m5.mixing_m2) == (area(106.5), area(30.8))
    assert (m4.k_capacity, m5.k_capacity, m2.k_capacity) == (
        pytest.approx(1.32998, abs=1e-5), pytest.approx(0.87008, abs=1e-5), 1.0)
    assert math.sqrt(m2.mixing_m2 / (math.pi / 4.0)) * 1000.0 == pytest.approx(44.448, abs=1e-3)
    assert m2.mixing_m2 / m2.throat_m2 == pytest.approx(5.398, abs=1e-3)
    d4, d5, d2 = (em.ejector_map(t) for t in ("324F004", "324F005", "324F002"))
    assert (d4.k_capacity, d5.k_capacity, d2.k_capacity) == (
        pytest.approx(0.91921, abs=1e-5), pytest.approx(0.49739, abs=1e-5),
        pytest.approx(0.33635, abs=1e-5))
    for v, m in ((m4, d4), (m5, d5), (m2, d2)):
        assert (m.throat_m2, m.mixing_m2, m.pc_scale) == (v.throat_m2, v.mixing_m2, v.pc_scale)


def test_the_table_holds_the_1d_points_it_is_made_of():
    """Bilinear on 0.005 bar x 0.05 bar cells: within 0.1 % of the 1-D map wherever the ejector
    pulls more than a tenth of its duty, 0.05-1.10 bar a suction, 2.5-5.0 bar a motive."""
    rng = random.Random(1)
    for tag in TAGS:
        m = em.ejector_map(tag)
        for _ in range(1500):
            p_s, p_m = rng.uniform(0.05, 1.1), rng.uniform(2.5, 5.0)
            exact = em.critical_capacity_kgh(m, p_s, p_m)
            if exact > 0.1 * m.duty.suction_kgh:
                assert em.interpolated(tag, p_s, p_m)[0] == pytest.approx(exact, rel=1e-3)


def test_the_pull_rises_with_the_suction_down_to_the_shut_off():
    """324F004 at full motive against 0.3 bar a: 138 kg/h at 0.05 bar a, 526 at 0.12, 952 at
    0.2, 5333 at 1.0 — and nothing below 14.6 mbar, where its jet fills the mixing throat."""
    pulls = [em.suction_capacity_kgh("324F004", p, 4.1, 0.3) for p in (0.05, 0.12, 0.2, 1.0)]
    assert pulls == [pytest.approx(138.000, abs=1e-3), pytest.approx(525.961, abs=1e-3),
                     pytest.approx(952.008, abs=1e-3), pytest.approx(5333.259, abs=1e-3)]
    m = em.ejector_map("324F004")
    assert em.critical_capacity_kgh(m, 0.01458, 4.1) > 0.0 == em.critical_capacity_kgh(
        m, 0.01457, 4.1)


def test_above_its_critical_back_pressure_the_ejector_breaks():
    """324F004 at 0.131 bar a and full motive: critical to 0.369 bar a, 396 kg/h at 0.60, 69 at
    0.68, nothing from 0.69 — P_c / r*."""
    pulls = [em.suction_capacity_kgh("324F004", 0.131, 4.1, pd)
             for pd in (0.3686, 0.6, 0.68, 0.69)]
    assert pulls == [pytest.approx(584.0, rel=1e-14), pytest.approx(396.239, abs=1e-3),
                     pytest.approx(68.863, abs=1e-3), 0.0]
    assert em.unchoked_fraction(0.3, 0.4) == 1.0 == em.unchoked_fraction(0.4, 0.4)
    assert em.unchoked_fraction(0.4 / em.R_STAR, 0.4) == 0.0
    assert em.unchoked_fraction(0.5, 0.0) == 0.0


def test_a_motive_sag_stalls_the_ejector():
    """324F004 at 0.131 bar a against 0.3: the critical back pressure falls with the motive, and
    below about 1.5 bar a the ejector can no longer discharge into 324E006 — 489 kg/h at 1.0,
    194 at 0.8; no motive, no pull."""
    pulls = [em.suction_capacity_kgh("324F004", 0.131, pm, 0.3) for pm in (2.5, 1.5, 1.0, 0.8)]
    assert pulls == [pytest.approx(629.127, abs=1e-3), pytest.approx(624.684, abs=1e-3),
                     pytest.approx(489.172, abs=1e-3), pytest.approx(194.077, abs=1e-3)]
    assert em.suction_capacity_kgh("324F004", 0.131, 0.0, 0.3) == 0.0
    assert em.motive_kgh(em.ejector_map("324F004"), 0.0) == 0.0


def test_the_vendor_ratings_stand_as_margin_b61():
    """Handoff B-61, both anchors. On their vendor duties 324F004 would pull 845 kg/h at 0.131
    bar a against PFD 712's 584, and 324F002 214 at 0.33 against 706's 72 — the PFD's vacuums
    part-load points the bleeds could not reach. On the design loads the vendor's points are
    margin: 324F004 526 kg/h at 0.12 bar a against Körting's 761, 324F002 31.6 at 0.2 against 94,
    324F005 48.0 at 0.33 against 84."""
    v4, v2 = em.vendor_map("324F004"), em.vendor_map("324F002")
    assert em.critical_capacity_kgh(v4, 0.131, 4.1) == pytest.approx(844.970, abs=1e-3)
    assert em.critical_capacity_kgh(v2, 0.33, 4.1) == pytest.approx(214.063, abs=1e-3)
    assert [em.suction_capacity_kgh(t, p, 4.1, pd) for t, p, pd in (
        ("324F004", 0.12, 0.35), ("324F002", 0.2, 1.0), ("324F005", 0.33, 1.16))] == [
        pytest.approx(525.961, abs=1e-3), pytest.approx(31.617, abs=1e-3),
        pytest.approx(48.020, abs=1e-3)]
