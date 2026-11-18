"""V1 <-> V1.1 for unit 324's ejector pull — handoffs B-57 and B-61, decided 2026-10-01, both ways.

V1 writes each ejector's pull inline in its stage's pressure loop, so the two lines are
transcribed here and declared as such (``main.py`` 9827 for 324F002, 9955 for 324F004 / 324F005),
on V1's own constants lifted from ``main.py``:

    pull_F002 = R324_F001_EJPULL_DES x (motive / R324_F002_MOTIVE_DES) x (P / R324_F001_P_BARA)
    pull_F004 = R324_F003_EJPULL_DES x (HIC-329606 / R324_HIC9606_DES_PCT) x (P / R324_F003_P_BARA)

The port's pull is the synthesized map (`units.evaporation.ejector_map`) on the vendors' throats,
its capacity anchored on the PFD's design loads (B-61), at a motive pressure and against a
discharge pressure V1's lines have no use for. V1's motive is a flow, the map's a pressure: a
choked nozzle passes a flow proportional to its pressure (`nozzle_pressure_bara`), so half V1's
motive is half the map's motive pressure.
"""

from __future__ import annotations

import pytest

from ureasim.units.evaporation import ejector_map as em
from tests.equivalence.v1_loader import lift, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)


@pytest.fixture(scope="module")
def v1():
    return lift(["R324_F001_EJPULL_DES", "R324_F002_MOTIVE_DES", "R324_F001_P_BARA",
                 "R324_F003_EJPULL_DES", "R324_HIC9606_DES_PCT", "R324_F003_P_BARA",
                 "R324_F004_MOTIVE_DES", "R324_F005_MOTIVE_DES"])


def _v1_f002(v1, motive_kgh, p):
    return v1["R324_F001_EJPULL_DES"] * (motive_kgh / v1["R324_F002_MOTIVE_DES"]) * (
        p / v1["R324_F001_P_BARA"])


def _v1_f004(v1, hic_pct, p):
    return v1["R324_F003_EJPULL_DES"] * (hic_pct / v1["R324_HIC9606_DES_PCT"]) * (
        p / v1["R324_F003_P_BARA"])


@pytest.mark.parametrize("case, v1_f004, port_f004, v1_f002, port_f002", [
    ("design", 584.0, 584.0, 72.0, 72.0),
    ("motive halved", 292.0, 643.183, 36.0, 0.000),
    ("discharge raised", 584.0, 0.0, 72.0, 0.0),
    ("from atmosphere", 4517.084, 5406.218, 221.073, 296.872),
])
def test_the_ejector_pull_decided_divergence(v1, case, v1_f004, port_f004, v1_f002, port_f002):
    """B-57 and B-61. At the PFD's vacuums and design motive both pull the PFD's 584 and 72 kg/h:
    V1's lines by construction, the maps on their design anchor. Halve the motive and V1 halves
    its pull; 324F004's map, still critical, pulls a little more (643), and 324F002's, its nozzle
    at 2.05 bar a below the plant's lost stroke, breaks and pulls nothing (decision 251; 639 and 89
    before it). Raise the discharge to 1.5 bar a (324F004) and 2.5 (324F002) and V1 does not
    notice; the ejectors break and pull nothing. From atmosphere, V1's line climbs with the
    pressure to 4517 and 221 kg/h; the maps to 5406 (5401 before decision 251) and 297."""
    p4, p2, hic, motive, d4, d2 = {
        "design": (0.131, 0.33, 50.0, 390.0, 0.30, 1.0),
        "motive halved": (0.131, 0.33, 25.0, 195.0, 0.30, 1.0),
        "discharge raised": (0.131, 0.33, 50.0, 390.0, 1.5, 2.5),
        "from atmosphere": (1.01325, 1.01325, 50.0, 390.0, 1.01325, 1.01325),
    }[case]
    m_p = em.nozzle_pressure_bara("324F002", motive)
    assert em.nozzle_pressure_bara("324F004", 1220.0 * hic / 50.0) == m_p
    assert _v1_f004(v1, hic, p4) == pytest.approx(v1_f004, abs=1e-3)
    assert _v1_f002(v1, motive, p2) == pytest.approx(v1_f002, abs=1e-3)
    assert em.suction_capacity_kgh("324F004", p4, m_p, d4) == pytest.approx(port_f004, abs=1e-3)
    assert em.suction_capacity_kgh("324F002", p2, m_p, d2) == pytest.approx(port_f002, abs=1e-3)


def test_the_design_motive_is_v1s_b64(v1):
    """Handoff B-64, decided 2026-10-02, option a: the design motive the maps' nozzle pressure is
    anchored on is V1's own, PFD 924, 927 and 929 — where B-57 had built the maps' anchor on
    Uhde's 1061 and 366 kg/h."""
    from ureasim.data import unit_324 as d
    assert (d.F002_MOTIVE_DES_KGH, d.F004_MOTIVE_DES_KGH, d.F005_MOTIVE_DES_KGH) == (
        v1["R324_F002_MOTIVE_DES"], v1["R324_F004_MOTIVE_DES"], v1["R324_F005_MOTIVE_DES"])
    assert [d.EJECTOR_DESIGN_LOADS[t].motive_kgh for t in ("324F002", "324F004", "324F005")] == [
        390.0, 1220.0, 180.0]
