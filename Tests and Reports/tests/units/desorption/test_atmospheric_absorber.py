"""Behaviour of 323C005 — `ureasim.units.desorption.atmospheric_absorber`.

Equivalence with V1 is proven tick by tick in
`tests/equivalence/test_atmospheric_absorber_equivalence.py`. This file pins what the absorber
DOES: the design held to the bit, the vent answering the inerts and the solvent temperature, the
absorption heat warming the liquor, the boiling point that stops the absorption when the solvent
is lost, and the sump that holds only its drain head. Every number here was measured on the
module before it was written down.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_323c005 as c
from ureasim.units.desorption import atmospheric_absorber as aa

M702, M756, M708 = c.C005_M702_DES_KGH, c.C005_M756_DES_KGH, c.C005_M708_DES_KGH


def _run(seconds: float, dt: float = 0.1, **after):
    """Run 323C005 on its design boundaries, with `after` applied from 10 s. Returns the last
    result, the first time the boiling point limits the absorption, and the worst mass
    residual of any tick [kg/h]."""
    u = aa.AtmosphericAbsorber()
    first, worst, r = {}, 0.0, None
    for k in range(1, int(round(seconds / dt)) + 1):
        t = round(k * dt, 6)
        x = {"m702": M702, "m756": M756, "m708": M708, "f706": 1.0, "t_solvent": 43.0}
        if t > 10.0:
            x.update(after)
        m_before = u.m_kg
        r = u.step(x["m702"], x["m756"], x["m708"],
                   {q: v * x["f706"] for q, v in c.E002_INERT_DES_KMOLH.items()},
                   x["t_solvent"], dt)
        into = x["m702"] + x["m708"] + x["m756"]
        worst = max(worst, abs(into - r.m_341_kgh - r.m_343_kgh
                               - (u.m_kg - m_before) * 3600.0 / dt))
        if r.boil_limited:
            first.setdefault("boil", t)
    return r, first, worst


def test_the_design_point_holds_to_the_bit():
    """An hour at design: 80 kg/h to the stack, 822 absorbed, 34 180 kg/h of bottoms, the
    liquor at 55 C and the sump at 8.07 kg, 49 mm over N4."""
    r, first, worst = _run(3600.0)
    assert (r.m_341_kgh, r.abs_kgh, r.m_343_kgh, r.t_c, r.m_kg) == (
        c.C005_VENT_DES_KGH, c.C005_ABS_DES_KGH, c.C005_BOT_DES_KGH, c.C005_T_C,
        aa.SUMP_M_DES_KG)
    assert r.m_kg == pytest.approx(8.070, abs=1e-3)
    assert r.sump_head_m == pytest.approx(0.0485, abs=1e-4)
    assert first == {} and worst == 0.0


@pytest.mark.parametrize("change, vent, t_c", [
    ({"m702": 3.0 * M702}, 146.05, 65.29),   # an NH3 surge: more inerts and more heat
    ({"m702": 0.0}, 46.97, 49.65),           # PV-323203 shut: 708's inerts alone
    ({"f706": 2.0}, 126.97, 54.38),          # 708 carries twice 324E002's inerts
    ({"t_solvent": 55.0}, 89.25, 66.56),     # a warm solvent holds more vapour at the top, and
])                                           # brings its 55 C to the liquor (B-31)
def test_the_vent_answers_the_inerts_and_the_solvent_temperature(change, vent, t_c):
    """The vent is the inert gas that arrives, saturated at the solvent's temperature: it
    follows the inerts and the top temperature, and the absorption heat moves the liquor.
    The mass balance closes on every tick."""
    r, first, worst = _run(600.0, **change)
    assert r.m_341_kgh == pytest.approx(vent, abs=0.01)
    assert r.t_c == pytest.approx(t_c, abs=0.01)
    assert first == {} and worst < 1e-9


def test_half_the_solvent_warms_the_liquor_and_leaves_the_vent():
    """756 halved: the vent is saturated at the SAME 43 C solvent at the top, so it stays at 80
    kg/h, and the same absorption heat in half the liquor carries it to 66.4 C."""
    r, _, worst = _run(600.0, m756=0.5 * M756)
    assert r.m_341_kgh == pytest.approx(c.C005_VENT_DES_KGH, rel=1e-12)
    assert r.t_c == pytest.approx(66.38, abs=0.01)
    assert r.m_343_kgh == pytest.approx(0.5 * M756 + c.C005_ABS_DES_KGH, rel=1e-9)
    assert worst < 1e-9


def test_the_solvent_lost_boils_the_liquor_and_vents_the_gas():
    """756 cut: within 1.4 s the absorption heat would carry the few kilograms left past water's
    boiling point at 1.0 bar a; the absorption is cut to what holds the liquor there, 31 kg/h,
    and the other 871 kg/h of 702 and 708 go to the stack."""
    r, first, worst = _run(600.0, m756=0.0)
    assert first["boil"] == pytest.approx(11.4, abs=1e-9)
    assert r.boil_limited and r.t_c == pytest.approx(aa.T_BOIL_C, abs=1e-6)
    assert r.abs_kgh == pytest.approx(31.07, abs=0.01)
    assert r.m_341_kgh == pytest.approx(M702 + M708 - r.abs_kgh, rel=1e-12)
    assert worst < 1e-9


def test_with_nothing_arriving_the_sump_drains_empty():
    """Every inlet stopped: the sump drains through N4 to nothing within a minute, and the liquor
    temperature stays where it was — nothing flows to move it."""
    r, _, worst = _run(70.0, m702=0.0, m756=0.0, m708=0.0, f706=0.0)
    assert r.m_kg < 1e-6 and r.m_343_kgh < 1e-3
    assert r.t_c == c.C005_T_C and worst < 1e-9


@pytest.mark.parametrize("h", [0.0, 0.02, 0.0485, 0.2, 0.5])
def test_the_n4_drain_is_a_weir_then_an_orifice(h):
    """At low head the liquor spills over the pipe rim as over a weir; the orifice law on the
    bore takes over only at a deep head. The design 49 mm is on the weir."""
    weir = c.C005_C_WEIR * 3.141592653589793 * c.C005_N4_ID_M * h ** 1.5
    assert aa.sump_drain_m3s(h) <= weir
    if h <= 0.0485:
        assert aa.sump_drain_m3s(h) == pytest.approx(weir, rel=1e-12)


def test_323e011s_overflow_falls_to_the_sump_with_its_sensible_heat():
    """A-20 (decided 2026-10-03): 8.2 t/h of 323E011's overflow at 46 C from 10 s. It is neither
    gas nor vent: the stack still takes 80 kg/h and the solvent 822; the bottoms carry it on, 42 380
    kg/h after ten minutes, the sump 2.6 kg deeper, and the liquor, cooled by 46 C liquor, settles
    at 53.27 C — 702 arriving at the same condensate's 46 C (B-31). The mass balance closes on every
    tick, overflow included."""
    u = aa.AtmosphericAbsorber()
    worst, r = 0.0, None
    for k in range(1, 6001):
        over = 8200.0 if k * 0.1 > 10.0 else 0.0
        m_before = u.m_kg
        r = u.step(M702, M756, M708, dict(c.E002_INERT_DES_KMOLH), 43.0, 0.1,
                   m_e011_over_kgh=over, t_e011_over_c=46.0)
        worst = max(worst, abs(M702 + M708 + M756 + over - r.m_341_kgh - r.m_343_kgh
                               - (u.m_kg - m_before) * 36000.0))
    assert (r.m_341_kgh, r.abs_kgh, r.e011_over_kgh) == (c.C005_VENT_DES_KGH,
                                                          c.C005_ABS_DES_KGH, 8200.0)
    assert r.m_343_kgh == pytest.approx(M756 + c.C005_ABS_DES_KGH + 8200.0, rel=1e-12)
    assert r.m_kg == pytest.approx(10.653, abs=1e-3) and r.t_c == pytest.approx(53.272, abs=1e-3)
    assert worst < 1e-8


def test_no_overflow_is_the_column_without_one():
    """At zero overflow the keyword changes nothing, to the bit, whatever temperature it names —
    on V1's inlets: the same temperature is 702's since B-31, which has its own test."""
    a, b = aa.AtmosphericAbsorber(live_inlets=False), aa.AtmosphericAbsorber(live_inlets=False)
    for k in range(600):
        m756 = 0.0 if 100 <= k < 300 else M756
        ra = a.step(M702, m756, M708, dict(c.E002_INERT_DES_KMOLH), 43.0, 0.1)
        rb = b.step(M702, m756, M708, dict(c.E002_INERT_DES_KMOLH), 43.0, 0.1,
                    m_e011_over_kgh=0.0, t_e011_over_c=95.0)
        assert ra == rb


def test_708_at_324f002s_discharge_b97():
    """B-97 (decided 2026-10-16): 708 at the temperature the vacuum train publishes. The design's
    462 kg/h at 63 C instead of 121 C cools the liquor to 54.22 C in ten minutes, the vent and the
    absorption unmoved; at 121 C, or on V1's inlets whatever it names, the column is V1's to the
    bit."""
    def run(live, t708):
        u = aa.AtmosphericAbsorber(live_inlets=live)
        for _ in range(6000):
            r = u.step(M702, M756, M708, dict(c.E002_INERT_DES_KMOLH), 43.0, 0.1, t_708_c=t708)
        return r
    assert run(True, 121.0) == run(False, 63.04) == run(False, 121.0)
    r = run(True, 63.04)
    assert (r.m_341_kgh, r.abs_kgh, r.m_343_kgh) == (c.C005_VENT_DES_KGH, c.C005_ABS_DES_KGH,
                                                     c.C005_BOT_DES_KGH)
    assert r.t_c == pytest.approx(54.2184, abs=1e-4)
