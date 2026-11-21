"""Behaviour of the steam-jet ejectors' maps — `ureasim.units.evaporation.ejector_map`.

The 1-D gas dynamics are V1's, proven in `tests/equivalence/test_ejector_gas_dynamics_equivalence.py`;
V1's straight lines against the maps run in `test_ejector_map_decided_equivalence.py`. This file
pins what the maps DO: each vendor duty point on the vendor's map, each PFD design load off the
decided table (handoff B-61, decided 2026-10-01), the table's agreement with the 1-D points it is
made of, the pull rising with the suction pressure down to the ejector's shut-off, the break above
the critical back pressure, the stall a motive sag brings, and the vendor's margin over the
design. Decision 251 (2026-11-18): the decided map's critical back pressure and break width are
anchored on the plant's 5 Nov 2026 break-off bracket (As-Built CV.5); the vendor map keeps the
vendor's scale and V1's break, and both sides are pinned here.
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
    pressures on the vendor's map. The decided map is critical to its own discharge on the duty
    (decision 251: 0.773, 0.412 and 1.648 bar a, where V1 broke at the vendor's)."""
    m = em.vendor_map(tag)
    d = m.duty
    assert em.critical_capacity_kgh(m, d.p_suction_bara, d.p_motive_bara) == pytest.approx(
        suction, rel=1e-12)
    assert em.critical_back_pressure_bara(m, d.p_suction_bara, d.p_motive_bara) == (
        pytest.approx(p_crit, rel=1e-12))
    decided = {"324F002": 0.772815, "324F004": 0.412396, "324F005": 1.647577}[tag]
    assert em.interpolated(tag, d.p_suction_bara, d.p_motive_bara)[1] == pytest.approx(
        decided, abs=1e-6)
    assert m.break_width is None
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
        assert (m.throat_m2, m.mixing_m2) == (v.throat_m2, v.mixing_m2)
    # Decision 251: the vendor's scale on the vendor map (V1's), the plant's on the decided map.
    assert (m4.pc_scale, m5.pc_scale, m2.pc_scale) == (
        pytest.approx(0.26507, abs=1e-5), pytest.approx(0.50146, abs=1e-5),
        pytest.approx(0.56430, abs=1e-5))
    assert (d4.pc_scale, d5.pc_scale, d2.pc_scale) == (
        pytest.approx(0.31233, abs=1e-5), pytest.approx(0.71224, abs=1e-5),
        pytest.approx(0.43610, abs=1e-5))
    assert (d4.break_width, d5.break_width, d2.break_width) == (
        pytest.approx(1.05737, abs=1e-5), pytest.approx(1.04014, abs=1e-5),
        pytest.approx(1.09820, abs=1e-5))


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
    """324F004 at full motive against 0.3 bar a: 526 kg/h at 0.12 bar a, 952 at 0.2, 5333 at
    1.0 — and nothing below 14.6 mbar, where its jet fills the mixing throat. At 0.05 bar a the
    decided break (decision 251) cannot discharge into 0.3; V1's pulled 138."""
    pulls = [em.suction_capacity_kgh("324F004", p, 4.1, 0.3) for p in (0.05, 0.12, 0.2, 1.0)]
    assert pulls == [0.0, pytest.approx(525.961, abs=1e-3),
                     pytest.approx(952.008, abs=1e-3), pytest.approx(5333.259, abs=1e-3)]
    m = em.ejector_map("324F004")
    assert em.critical_capacity_kgh(m, 0.01458, 4.1) > 0.0 == em.critical_capacity_kgh(
        m, 0.01457, 4.1)


def test_above_its_critical_back_pressure_the_ejector_breaks():
    """324F004 at 0.131 bar a and full motive, decision 251: critical to 0.434 bar a, 536 kg/h
    at 0.444, 351 at 0.454, nothing from 0.4593, P_c times the anchored width 1.0574. V1's break,
    still the vendor map's, ran on to P_c / r* (`unchoked_fraction` with no width)."""
    pulls = [em.suction_capacity_kgh("324F004", 0.131, 4.1, pd)
             for pd in (0.4339, 0.4443, 0.4543, 0.4593)]
    assert pulls == [pytest.approx(584.0, rel=1e-14), pytest.approx(536.374, abs=1e-3),
                     pytest.approx(351.255, abs=1e-3), 0.0]
    assert em.unchoked_fraction(0.3, 0.4) == 1.0 == em.unchoked_fraction(0.4, 0.4)
    assert em.unchoked_fraction(0.4 / em.R_STAR, 0.4) == 0.0
    assert em.unchoked_fraction(0.5, 0.0) == 0.0


def test_the_decided_break_narrows_v1s_flux_shape_decision_251():
    """Decision 251: with a width w the flux shape that ran from x = 1 to 1/r* runs from 1 to w.
    No width is V1's law; at w = 1/r* the two laws agree; F is 1 up to the critical back
    pressure, 0 from w times it, continuous and falling between."""
    rng = random.Random(7)
    for _ in range(500):
        p_c, x = rng.uniform(0.1, 2.0), rng.uniform(0.5, 2.0)
        assert em.unchoked_fraction(x * p_c, p_c, 1.0 / em.R_STAR) == pytest.approx(
            em.unchoked_fraction(x * p_c, p_c), abs=1e-12)
    w = 1.05
    fs = [em.unchoked_fraction(1.0 + k * (w - 1.0) / 400, 1.0, w) for k in range(401)]
    assert fs[0] == 1.0 and fs[-1] < 1e-6
    assert all(b <= a for a, b in zip(fs, fs[1:]))
    assert max(a - b for a, b in zip(fs, fs[1:])) < 0.1   # square-root fall at the shut-off
    assert em.unchoked_fraction(0.9, 1.0, w) == 1.0
    assert em.unchoked_fraction(1.06, 1.0, w) == 0.0
    assert em.vendor_map("324F004").break_width is None


@pytest.mark.parametrize("tag", TAGS)
def test_each_ejector_holds_and_loses_on_the_plants_bracket_decision_251(tag):
    """Decision 251, As-Built CV.5: on the logged header (PT-329207 4.22 bar g) the ejector is
    critical against its design discharge at its design suction with its motive valve at the
    stroke the plant still held (HIC-329605 64 %, HIC-329606 40 %), and at the stroke the plant
    lost (55 %, 38 %) it pulls its design load less the design bleed."""
    b, load = u324.EJECTOR_BREAKS[tag], u324.EJECTOR_DESIGN_LOADS[tag]
    p_hold, p_lost = em.break_nozzle_bara(tag, b.hold_pct), em.break_nozzle_bara(tag, b.lost_pct)
    assert em.interpolated(tag, load.p_suction_bara, p_hold)[1] == pytest.approx(
        b.p_discharge_bara, rel=1e-4)
    assert em.suction_capacity_kgh(tag, load.p_suction_bara, p_lost, b.p_discharge_bara) == (
        pytest.approx(load.suction_kgh - b.bleed_des_kgh, rel=2e-2))
    m = em.ejector_map(tag)
    x = b.p_discharge_bara / em.critical_back_pressure_bara(m, load.p_suction_bara, p_lost)
    assert 1.0 < x < m.break_width < 1.0 / em.R_STAR


def test_a_motive_sag_stalls_the_ejector():
    """324F004 at 0.131 bar a against 0.3: the critical back pressure falls with the motive, and
    below about 1.7 bar a, the plant's 38 % stroke, the ejector can no longer discharge into
    324E006 (decision 251; V1's break still pulled 625 kg/h at 1.5 and 194 at 0.8); no motive,
    no pull."""
    pulls = [em.suction_capacity_kgh("324F004", 0.131, pm, 0.3) for pm in (2.5, 1.5, 1.0, 0.8)]
    assert pulls == [pytest.approx(629.146, abs=1e-3), 0.0, 0.0, 0.0]
    assert em.suction_capacity_kgh("324F004", 0.131, 0.0, 0.3) == 0.0
    assert em.motive_kgh(em.ejector_map("324F004"), 0.0) == 0.0


def test_the_vendor_ratings_stand_as_margin_b61():
    """Handoff B-61, both anchors. On their vendor duties 324F004 would pull 845 kg/h at 0.131
    bar a against PFD 712's 584, and 324F002 214 at 0.33 against 706's 72 — the PFD's vacuums
    part-load points the bleeds could not reach. On the design loads the vendor's points are
    margin: 324F004 526 kg/h at 0.12 bar a against Körting's 761, 324F005 48.0 at 0.33 against
    84. 324F002 at 0.2 bar a no longer discharges into 1.0 bar a on the decided break (decision
    251; V1 pulled 31.6 against the vendor's 94)."""
    v4, v2 = em.vendor_map("324F004"), em.vendor_map("324F002")
    assert em.critical_capacity_kgh(v4, 0.131, 4.1) == pytest.approx(844.970, abs=1e-3)
    assert em.critical_capacity_kgh(v2, 0.33, 4.1) == pytest.approx(214.063, abs=1e-3)
    assert [em.suction_capacity_kgh(t, p, 4.1, pd) for t, p, pd in (
        ("324F004", 0.12, 0.35), ("324F002", 0.2, 1.0), ("324F005", 0.33, 1.16))] == [
        pytest.approx(525.961, abs=1e-3), 0.0, pytest.approx(48.020, abs=1e-3)]
