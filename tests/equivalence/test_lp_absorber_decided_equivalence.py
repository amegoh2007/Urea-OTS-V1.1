"""V1 <-> V1.1 equivalence for 322C001's decided divergences, each asserted from both sides.

What is being proved
--------------------
`test_lp_absorber_equivalence.py` compares the port with the transcription carrying every
departure on every tick of every scenario. Here each departure runs both ways: V1's lines for it
against the port, bit-exact until it first acts, then V1's behaviour asserted on V1's side and
the port's on the port's. Seven were decided by the process engineer for this unit on 2026-10-01
(SV32253, handoffs B-47 and A-16; 755 from 322E006, B-54; XV-322915's flood in the vent line,
B-55; I 22.1 on the DCS's logic, B-56; XV-322915 with no operator open, B-59; the flood on the
valve's rated steam, B-60; HV-322604's condensate, B-19); five are classes decided on other units
and applied under §5 rule 7 (decisions 33, 11, 23 and 10).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from ureasim.core.stream import MW_COMP
from ureasim.data import unit_322c001 as c
from ureasim.data import unit_322e006 as e6
from ureasim.units.absorption import feed_cooler as fc
from ureasim.units.absorption import lp_absorber as la
from ureasim.units.absorption import vent_line as vl
from ureasim.data import unit_322e003 as sc
from ureasim.thermo import real_gas
from tests.equivalence import test_lp_absorber_equivalence as c001_eq
from tests.equivalence.v1_loader import v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

#: V1's namespace, built as 322C001's own equivalence test builds it.
v1 = c001_eq.v1

ALL = c001_eq.ALL
_design, _step, _manual, _gas = c001_eq._design, c001_eq._step, c001_eq._manual, c001_eq._gas


def _both(v1, script, ticks, dt, before, v1_decided, at=()):
    """V1 with `v1_decided` against the port: the tick they part, the tick each of the port's
    flags first rises, each side's liquor books, the port's relief lifts and band, both sides at
    the `at` times, and both sides at the end."""
    s, unit, loops = c001_eq._v1_state(v1, v1_decided), la.LpAbsorber(), la.LpAbsorberLoops()
    if before:
        before(s, unit, loops)
    out = SimpleNamespace(parted=None, first={}, made_v1=0.0, made=0.0, lifts=[], p_hi=0.0,
                          p_lo=99.0, at={}, s=s, unit=unit, loops=loops, a=None, b=None)
    for k in range(ticks):
        x = script(k)
        s.cpl_flow_kgh, s.XV_322915 = x["cpl"], x["xv"]
        v1_pre, pre = s.a328_c001_M, unit.m_kg
        a = c001_eq._v1_c001(v1, s, x["gas"], x["m755"], dt, v1_decided, x["t755"])
        g = x["gas"]
        b = unit.step(loops, g["comp_kmolh"], g["mass_kgh"], g["T_out"], x["m755"], x["t755"],
                      x["cpl"], x["xv"], dt, liquor_kmolh=g.get("liquor"))
        out.made_v1 += s.a328_c001_M - v1_pre - (x["m755"] + x["cpl"] + a["abs"][3] + a["liq"]
                                                 - a["756"] - a["over"]) * dt / 3600.0
        out.made += unit.m_kg - pre - (x["m755"] + x["cpl"] + b.m_abs_kgh + b.m_liquor_kgh
                                       - b.m_756_kgh - b.m_overflow_kgh) * dt / 3600.0
        if out.parted is None:
            try:
                c001_eq._assert_tick(a, b, s, unit, loops, f"tick {k}")
            except AssertionError:
                out.parted = k
        for key, flag in (("drained", b.drained), ("over", b.m_overflow_kgh > 0.0),
                          ("v1 relief", a["sv253"] > 0.0), ("v1 full", a["over"] > 0.0)):
            if flag:
                out.first.setdefault(key, k)
        if b.relief_lifted and not (out.b and out.b.relief_lifted):
            out.lifts.append(k)
        if out.lifts:
            out.p_hi, out.p_lo = max(out.p_hi, b.p_bara), min(out.p_lo, b.p_bara)
        t = round((k + 1) * dt, 6)
        if t in at:
            out.at[t] = (s.a328_c001_P, unit.p_bara, s.a328_c001_T, unit.t_c)
        out.a, out.b = a, b
    return out


# --------------------------------------------------------------------------------------
# Decided for this unit, 2026-10-01
# --------------------------------------------------------------------------------------

def test_sv32253_relieves_a_shut_vent_decided_divergence(v1):
    """B-47, A-16. PV-322201 shut on the design purge: the 1578 kg/h the beds do not take up has
    no way out of a 3.1 m3 gas space, 0.13 bar/s. Bit-exact until SV32253 lifts at its certified
    6.013 bar a, 15.5 s on. V1's valve, set at the vessel's 30 bar g design pressure, lifts only at
    198 s, and V1's column stands at 31.09 bar a passing 1554 kg/h through its linear ramp. The
    port's vents the column to 5.513 bar a, on the gas blowdown, and lifts again every 5 s — 237
    times in twenty minutes, peaking at 6.068 bar a on the half-second tick. The liquor's books
    close on both sides: the relief takes gas only."""
    r = _both(v1, lambda k: _design(), 2400, 0.5, _manual("PIC_322201", "pic_322201", 0.0),
              ALL - {"relief"}, at=(60.0,))
    assert r.parted == 31 and r.lifts[:3] == [31, 41, 51] and len(r.lifts) == 237
    assert r.first["v1 relief"] == 395 and (r.first["v1 relief"] + 1) * 0.5 == 198.0
    assert r.at[60.0][0] == pytest.approx(12.199, abs=1e-3)
    assert r.s.a328_c001_P == pytest.approx(31.0933, abs=1e-4)
    assert r.a["sv253"] == pytest.approx(1554.12, abs=0.01)
    assert (r.p_hi, r.p_lo) == (pytest.approx(6.0681, abs=1e-4), c.SV32253_RESEAT_BARA)
    assert abs(r.made) < 1e-9 and abs(r.made_v1) < 1e-9


def test_755_from_322e006_decided_divergence(v1):
    """B-54. 322E006 loses its cooling water 5 s on: 755 arrives at 744's own 44 C. Bit-exact
    until then. V1 holds 755 at 40 C and its liquor stays at 43.0 C; the port's settles 3.7 K
    hotter, 46.72 C, its back-pressure up, and the vent slips 2.12 kg/h of NH3 against 1.79."""
    t755 = fc.feed_cooler_322e006(e6.E006_M744_DES_KGH, e6.E006_T744_DES_C, 0.0).t_755_c
    assert t755 == e6.E006_T744_DES_C == 44.0
    r = _both(v1, _step(10, t755=t755), 2400, 0.5, None, ALL - {"B-54"})
    assert r.parted == 10
    assert (r.s.a328_c001_T, r.unit.t_c) == (pytest.approx(43.0, abs=1e-9),
                                             pytest.approx(46.7179, abs=1e-4))
    assert r.a["y_vent"]["NH3"] * r.a["vent"] == pytest.approx(1.7944, abs=1e-4)
    assert r.b.y_vent["NH3"] * r.b.m_vent_kgh == pytest.approx(2.1181, abs=1e-4)
    assert abs(r.made) < 1e-9 and abs(r.made_v1) < 1e-9


def test_the_flood_in_the_vent_line_decided_divergence(v1):
    """B-55. XV-322915 opened 5 s on. Bit-exact until then. V1 puts its 500 kW into the liquor,
    with no steam: the liquor settles at 56.24 C, above trip 22.1's 55 C reset. The port's liquor
    stays at 43.0 C; the valve's rated 1000 kg/h of steam at 175 C (B-60) enters the vent line,
    and TI-322015 reads 114.2 C there (112.4 before the trace steam, decided 2026-10-07), from
    the 46.0 C the gas leaves the beds at."""
    r = _both(v1, _step(10, xv=True), 2400, 0.5, None, ALL - {"B-55"})
    assert r.parted == 10
    assert (r.s.a328_c001_T, r.unit.t_c) == (pytest.approx(56.2444, abs=1e-4),
                                             pytest.approx(43.0, abs=1e-9))
    assert r.b.m_flood_kgh == vl.FLOOD_STEAM_KGH == 1000.0
    assert (r.b.t_top_c, r.b.t_ti_322015_c) == (pytest.approx(46.0, abs=1e-9),
                                                 pytest.approx(114.226, abs=1e-3))
    assert abs(r.made) < 1e-9 and abs(r.made_v1) < 1e-9


def _v1_i_22_1(s, pv, close):
    """V1's I 22.1, transcribed (handoff A-12): the operator's ``322915`` command
    (``main.py`` 11494-11500) between steps, then the trip block (10142-10148) in step_sim."""
    if close:
        if s["xv"]:
            s["xv"] = False
        elif not s["latched"]:
            s["xv"] = True
    s["live"] = pv > 57.0
    if s["live"]:
        s["latched"] = True
    elif pv < 55.0:
        s["latched"] = False
    if s["latched"]:
        s["xv"] = True
    return s["xv"]


def test_i_22_1_on_the_dcs_logic_decided_divergence():
    """B-56. V1 latches XV-322915 open on its liquor, flooded at 56.24 C (the B-55 test's end), and
    re-opens it in the same step every time the operator closes it: the latch never clears while the
    flood heats the liquor over 55 C. The port's valve is AC4's PC22.5.1: HS-322915 held, it stays
    shut, TI-322015 falls from 114.2 to 53.7 C — the column's 46.0 C with the trace steam on it
    (decided 2026-10-07) — and the limit clears; released, the valve stays shut."""
    s = {"xv": False, "live": False, "latched": False}
    seen = [_v1_i_22_1(s, 60.0, False)] + [_v1_i_22_1(s, 56.2444, k % 2 == 0) for k in range(6)]
    assert seen == [True] * 7 and s["latched"] and not s["live"]
    trip, xv = vl.trip_22_1(), True
    trip.latched = True
    pin = la.design_pin()
    r = la.LpAbsorber().step(la.LpAbsorberLoops(), pin.gas_kmolh, pin.gas_kgh, pin.t_gas_c,
                             c.C001_M755_DES_KGH, c.C001_T_755_C, c.C001_CPL_DES_KGH, False, 0.1)
    ti = []
    for hs in (False, True, True, False):
        ti.append(vl.vent_line(r.m_vent_kgh, r.y_vent, 46.0, xv).t_ti_322015_c)
        xv = vl.xv_322915_open(trip.update_from_pv(ti[-1]), hs)
    assert ti == [pytest.approx(114.226, abs=1e-3), pytest.approx(114.226, abs=1e-3),
                  pytest.approx(53.708, abs=1e-3), pytest.approx(53.708, abs=1e-3)]
    assert not xv and not trip.latched


def test_xv_322915_has_no_operator_open_decided_divergence():
    """B-59. V1's operator command ``322915`` opens XV-322915 whenever trip 22.1 is clear, and the
    overlay's valve and its EXT-OVR button both send it. AC4's PC22.5.1 has no input that opens
    the valve: with TT-322015 under its limit it stays shut whatever the operator does, and the
    screen's only control for it is HS-322915, a maintained keyswitch."""
    from ureasim.data.screen_layout import OVERLAYS
    s = {"xv": False, "live": False, "latched": False}
    assert _v1_i_22_1(s, 46.0, True) and not s["latched"]
    assert not any(vl.xv_322915_open(False, hs) for hs in (False, True))
    els = {e["k"]: e for e in OVERLAYS["screen-328-2"]}
    assert "cmd" not in els["xv322915"]
    assert (els["ovrxv322915"]["tag"], els["ovrxv322915"]["cmd"]) == ("HS-322915", "HS-322915")


def test_the_flood_on_the_valves_rated_steam_decided_divergence(v1, monkeypatch):
    """B-60. V1's flood is 500 kW of latent heat; carried as LP steam at its 5.013 bar a header
    (151.9 C) it is 854 kg/h, and TI-322015 reads 98.1 C over the design vent. The port's is
    XV-322915's rated 1000 kg/h at 9.0 bar a and 175 C: 564 kW, TI-322015 114.2 C. Both sides
    carry the trace steam (decided 2026-10-07; 96.3 and 112.4 C before it)."""
    from ureasim.data.unit_329 import P_LP_BARA
    from ureasim.thermo import iapws
    pin = la.design_pin()
    r = la.LpAbsorber().step(la.LpAbsorberLoops(), pin.gas_kmolh, pin.gas_kgh, pin.t_gas_c,
                             c.C001_M755_DES_KGH, c.C001_T_755_C, c.C001_CPL_DES_KGH, False, 0.1)
    port = vl.vent_line(r.m_vent_kgh, r.y_vent, 46.0, True).t_ti_322015_c
    t_v1 = iapws.tsat_c(P_LP_BARA)
    m_v1 = v1["A328_QFLOOD_KW"] / iapws.hvap_kjkg(t_v1) * 3600.0
    monkeypatch.setattr(vl, "FLOOD_STEAM_KGH", m_v1)
    monkeypatch.setattr(vl, "FLOOD_STEAM_T_C", t_v1)
    v1_side = vl.vent_line(r.m_vent_kgh, r.y_vent, 46.0, True).t_ti_322015_c
    assert (v1["A328_QFLOOD_KW"], m_v1, t_v1) == (500.0, pytest.approx(854.05, abs=0.01),
                                                  pytest.approx(151.936, abs=1e-3))
    assert (v1_side, port) == (pytest.approx(98.108, abs=1e-3), pytest.approx(114.226, abs=1e-3))
    assert c.C001_FLOOD_STEAM_KGH * iapws.hvap_kjkg(c.C001_FLOOD_STEAM_T_C) / 3600.0 == (
        pytest.approx(564.0, abs=0.5))


@pytest.mark.parametrize("cf, t_v1, t_port, liq, t_liq_v1, t_liq_port, slip_v1, slip_port", [
    (0.9, 26.0, 71.7, 120.35, 68.485, 68.464, 18.90, 17.41),
    (0.7, -36.0, 76.5, 696.24, 88.274, 88.981, 454.51, 392.40),
])
def test_the_purge_condensate_decided_divergence(v1, cf, t_v1, t_port, liq, t_liq_v1,
                                                 t_liq_port, slip_v1, slip_port):
    """B-19. 322E003 at 90 % and at 70 % of its cooling, the column fed from 5 s on. V1 lets the
    purge down dry — to 26.0 C, 46 K under its dew point, and at 70 % to its solver's -36 C floor
    — and the absorber takes it all as gas. The port's purge reaches the column at 71.7 and
    76.5 C with 120 and 696 kg/h of carbamate liquor, which joins the sump while the gas climbs
    the beds. The purge's enthalpy is the same either way, so the liquor ends within 0.02 K of
    V1's at 90 %; at the floor, where V1's purge is not a root of its own balance, 0.7 K above.
    Less ammonia reaches the beds, and less slips to atmosphere."""
    gas = c001_eq._purge(cf)
    total = {k: gas["comp_kmolh"].get(k, 0.0) + gas["liquor"].get(k, 0.0)
             for k in set(gas["comp_kmolh"]) | set(gas["liquor"])}
    t_in = c001_eq._scrubber_vent(cf)[1]
    v1_gas = {"comp_kmolh": {k: v for k, v in total.items() if v > 0.0},
              "mass_kgh": sum(v * MW_COMP[k] for k, v in total.items()),
              "T_out": round(real_gas.isenthalpic_letdown(total, t_in, sc.OFFGAS_P_BARA,
                                                          sc.HV604_P_OUT_BARA)["t_out_c"], 1)}
    assert (v1_gas["T_out"], gas["T_out"]) == (t_v1, t_port)
    s, unit, loops = (c001_eq._v1_state(v1, ALL - {"B-19"}), la.LpAbsorber(),
                      la.LpAbsorberLoops())
    made = 0.0
    for k in range(2400):
        x_v1 = c001_eq._design(gas=v1_gas) if k >= 10 else c001_eq._design()
        x = c001_eq._design(gas=gas) if k >= 10 else c001_eq._design()
        a = c001_eq._v1_c001(v1, s, x_v1["gas"], x_v1["m755"], 0.5, ALL - {"B-19"}, 40.0)
        g, pre = x["gas"], unit.m_kg
        b = unit.step(loops, g["comp_kmolh"], g["mass_kgh"], g["T_out"], x["m755"], x["t755"],
                      x["cpl"], x["xv"], 0.5, liquor_kmolh=g.get("liquor"))
        if k < 10:
            c001_eq._assert_tick(a, b, s, unit, loops, f"tick {k}")
        made += unit.m_kg - pre - (x["m755"] + x["cpl"] + b.m_abs_kgh + b.m_liquor_kgh
                                   - b.m_756_kgh - b.m_overflow_kgh) * 0.5 / 3600.0
    assert b.m_liquor_kgh == pytest.approx(liq, abs=0.01) and a["liq"] == 0.0
    assert (s.a328_c001_T, unit.t_c) == (pytest.approx(t_liq_v1, abs=1e-3),
                                         pytest.approx(t_liq_port, abs=1e-3))
    assert (a["y_vent"]["NH3"] * a["vent"], b.y_vent["NH3"] * b.m_vent_kgh) == (
        pytest.approx(slip_v1, abs=0.01), pytest.approx(slip_port, abs=0.01))
    assert abs(made) < 1e-9


# --------------------------------------------------------------------------------------
# Classes decided on other units, applied under §5 rule 7
# --------------------------------------------------------------------------------------

def test_the_vessel_and_its_taps_decided_divergence(v1):
    """Decision 33. Both seeded at rest on 50 %: V1 holds 1392.3 kg on half its lower cylinder,
    the port 506.0 on LT-322502's taps. LV-322502 shut: V1's cylinders, 3.27 m3, are full at 204 s;
    the port's 3.60 m3 at 335.5 s. 755 cut a fifth: the port's sump, a third of V1's, is back on
    its set point ten minutes on (49.998 %) where V1's still reads 50.65 %."""
    r = _both(v1, lambda k: _design(), 1, 0.5, None, ALL - {"B-53"})
    assert r.parted == 0
    assert (r.s.a328_c001_M, r.unit.m_kg) == (pytest.approx(1392.31, abs=0.01),
                                              pytest.approx(506.03, abs=0.01))
    assert (r.a["LI"], r.b.level_pct) == (pytest.approx(50.0, abs=1e-12),
                                          pytest.approx(50.0, abs=1e-12))
    q = _both(v1, lambda k: _design(), 1000, 0.5, _manual("LIC_322502", "lic_322502", 0.0),
              ALL - {"B-53"})
    assert (q.first["v1 full"] + 1) * 0.5 == 204.0 and (q.first["over"] + 1) * 0.5 == 336.0
    assert q.unit.m_kg == c.C001_FULL_KG == 3618.0
    k = _both(v1, _step(10, m755=0.8 * c.C001_M755_DES_KGH), 1200, 0.5, None, ALL - {"B-53"})
    assert (k.a["LI"], k.b.level_pct) == (pytest.approx(50.655, abs=1e-3),
                                          pytest.approx(49.998, abs=1e-3))


def test_lv_322502_at_the_heel_decided_divergence(v1):
    """Decision 11. LV-322502 held wide open: it asks 3.9 times the design 756, 130 t/h. Bit-exact
    until the sump reaches its heel, 18.5 s on. From then on V1 floors the sump at 1 kg and goes on
    drawing, making up 31.8 t of liquor in twenty minutes; the port draws only what arrives,
    flags it, and makes up nothing."""
    r = _both(v1, lambda k: _design(), 2400, 0.5, _manual("LIC_322502", "lic_322502", 100.0),
              ALL - {"heel"})
    assert r.parted == 37 == r.first["drained"]
    assert r.made_v1 == pytest.approx(31783.98, abs=0.01) and abs(r.made) < 1e-9
    assert r.s.a328_c001_M == r.unit.m_kg == 1.0
    assert r.b.drained and r.b.m_756_kgh == pytest.approx(33358.0, abs=1e-6)
    assert r.a["756"] == pytest.approx(130224.92, abs=0.01)


def test_a_full_column_overflows_decided_divergence(v1):
    """Decision 11. LV-322502 shut: bit-exact until the column is full, 336 s on. V1 has no full
    column: half an hour on its sump holds 17 185 kg in a 3.6 m3 vessel; the port's excess, the
    33 358 kg/h that arrives, leaves as a published stream, its books closed."""
    r = _both(v1, lambda k: _design(), 3600, 0.5, _manual("LIC_322502", "lic_322502", 0.0),
              ALL - {"overflow"})
    assert r.parted == 671 == r.first["over"]
    assert r.s.a328_c001_M == pytest.approx(17184.87, abs=0.01)
    assert r.unit.m_kg == c.C001_FULL_KG and r.b.m_overflow_kgh == pytest.approx(33358.0, abs=1e-3)
    assert abs(r.made) < 1e-9


@pytest.mark.parametrize("v1_name, name, op, field, design, v1_ratio, port_ratio", [
    ("LIC_322502", "lic_322502", 80.0, "756", c.C001_M756_DES_KGH, 1.6, 2.1443),
    ("PIC_322201", "pic_322201", 80.0, "vent", c.C001_VENT_DES_KGH, 1.17994, 1.5889),
])
def test_the_valves_on_their_vendor_trims_decided_divergence(v1, v1_name, name, op, field,
                                                             design, v1_ratio, port_ratio):
    """Decision 23. Each valve held at 80 %: V1's linear trims from 50 and 67.8 % pass 1.60 and 1.18
    times the design flow; the vendor's modified equal percentage from 54.5 and 64.5 % pass 2.14
    and 1.59 times."""
    r = _both(v1, lambda k: _design(), 1, 0.5, _manual(v1_name, name, op), ALL - {"valve"})
    assert r.parted == 0
    port = r.b.m_756_kgh if field == "756" else r.b.m_vent_kgh
    assert r.a[field] / design == pytest.approx(v1_ratio, abs=1e-4)
    assert port / design == pytest.approx(port_ratio, abs=1e-4)


def test_pic_322201_on_span_decided_divergence(v1):
    """Decision 10. PIC-322201's set point to 4.5 bar a: V1's 6.0 %/bar reaches 4.07 bar a in 30 s
    and overshoots to 4.63 at two minutes; the port's 21.43 %/bar reaches 4.23 in 30 s and 4.504
    at two minutes, on its set point at five (V1 4.493)."""
    r = _both(v1, lambda k: _design(), 600, 0.5, c001_eq._sp45, ALL - {"gains"},
              at=(30.0, 120.0, 300.0))
    assert r.parted == 0
    v30, p30, _, _ = r.at[30.0]
    v120, p120, _, _ = r.at[120.0]
    v300, p300, _, _ = r.at[300.0]
    assert (v30, p30) == (pytest.approx(4.0672, abs=1e-4), pytest.approx(4.2261, abs=1e-4))
    assert (v120, p120) == (pytest.approx(4.6307, abs=1e-4), pytest.approx(4.5044, abs=1e-4))
    assert (v300, p300) == (pytest.approx(4.4926, abs=1e-4), pytest.approx(4.5, abs=1e-5))
