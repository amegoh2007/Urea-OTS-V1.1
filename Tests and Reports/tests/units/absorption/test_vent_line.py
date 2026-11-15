"""Behaviour of 322C001's vent line — `ureasim.units.absorption.vent_line`.

V1 has no vent line: it puts XV-322915's 500 kW into 322C001's liquor and trips on the liquor's
temperature. The line is the rewrite's, decided by the process engineer on 2026-10-01 (handoff
B-55); V1's side is asserted in `tests/equivalence/test_lp_absorber_decided_equivalence.py`. This
file pins where the gas leaves the beds, what the flood's steam does to TI-322015, the line's own
condensation, and I 22.1 as AC4's PC22.5.1 executes it (handoff B-56, decided 2026-10-01): with
the thermometer downstream of the injection the flood holds itself in, and HS-322915's keyswitch
is what ends it.

The trace steam (decided 2026-10-07): FO-329458 and FO-322457 put 60 kg/h into the line all the
time, FO-329459 30 kg/h into SV32253's discharge. TI-322015 reads 53.7 C at design where it read
the column's 46 C, and trip 22.1's 57 C is reached with the beds' top at 49.5 C where it took 57.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_322c001 as c
from ureasim.thermo import iapws
from ureasim.units.absorption import lp_absorber as la
from ureasim.units.absorption import packed_beds as pb
from ureasim.units.absorption import vent_line as vl


def _design_tick():
    pin = la.design_pin()
    unit, loops = la.LpAbsorber(), la.LpAbsorberLoops()
    return pin, unit.step(loops, pin.gas_kmolh, pin.gas_kgh, pin.t_gas_c, c.C001_M755_DES_KGH,
                          c.C001_T_755_C, c.C001_CPL_DES_KGH, False, 0.1)


def test_the_gas_leaves_the_beds_at_954s_temperature():
    """At design the polish carries four times the gas's heat capacity, so the gas leaves at 954's
    46 C — PFD 797's temperature. XV-322915 shut, TI-322015 reads it with the trace steam on it,
    53.7 C."""
    _, r = _design_tick()
    assert r.t_top_c == c.C001_T_CPL_C == 46.0
    assert r.t_ti_322015_c == pytest.approx(53.708, abs=1e-3)
    assert r.m_flood_kgh == 0.0 and r.m_trace_kgh == 90.0


@pytest.mark.parametrize("p_9, trace", [(9.0, 60.0), (8.5, 56.820), (7.0, 47.218),
                                        (5.0, 34.243), (2.0, 13.730)])
def test_the_trace_steam_follows_the_9_bar_header(p_9, trace):
    """FO-329458 and FO-322457, 30 kg/h each at 9.0 bar a (Uhde's loop summaries), choked like
    the flood and on the same header; FO-329459's 30 kg/h into SV32253's discharge likewise."""
    assert c.C001_TRACE_STEAM_KGH == 60.0 and c.C001_SV_PURGE_STEAM_KGH == 30.0
    assert vl.trace_steam_kgh(p_9) == pytest.approx(trace, abs=1e-3)
    assert vl.sv_purge_steam_kgh(p_9) == pytest.approx(trace / 2.0, abs=1e-3)
    assert vl.trace_steam_kgh(vl.FLOOD_STEAM_P_BARA) == 60.0


@pytest.mark.parametrize("top, ti", [(46.0, 53.708), (48.0, 55.588), (49.5, 56.998),
                                     (50.0, 57.469)])
def test_the_trace_steam_brings_trip_22_1_within_3_5_k_of_the_design_top(top, ti):
    """Without the trace steam TI-322015 read the beds' top, so 22.1 fired at a 57 C top; with it,
    on a 49.5 C top, 3.5 K over the design's 46."""
    _, r = _design_tick()
    line = vl.vent_line(r.m_vent_kgh, r.y_vent, top, False)
    assert line.t_ti_322015_c == pytest.approx(ti, abs=1e-3)
    assert line.m_trace_kgh == 60.0 and line.m_condensed_kgh == 0.0


def test_a_lost_polish_or_a_heavy_gas_carries_the_lower_bed_up():
    """954 lost: the gas leaves at the liquor's temperature. A gas outweighing the polish leaves
    between the two, closer to the liquor the heavier it is; none at all, at 954's."""
    pin, r = _design_tick()
    beds = r.beds
    assert vl.column_top_c(beds, pin.gas_kmolh, 0.0, 46.0, 70.0) == 70.0
    heavy = pb.BedsResult(absorbed_kmolh=beds.absorbed_kmolh,
                          vent_kmolh={k: 8.0 * v for k, v in beds.vent_kmolh.items()},
                          ntu=beds.ntu, y_star_lo=beds.y_star_lo, dt_up_k=beds.dt_up_k,
                          abs_up=beds.abs_up)
    assert vl.column_top_c(heavy, pin.gas_kmolh, c.C001_CPL_DES_KGH, 46.0, 70.0) == (
        pytest.approx(56.571, abs=1e-3))
    empty = pb.BedsResult(absorbed_kmolh={}, vent_kmolh={}, ntu={}, y_star_lo={}, dt_up_k=0.0,
                          abs_up={"NH3": 0.0, "CO2": 0.0, "dT": 0.0})
    assert vl.column_top_c(empty, {}, c.C001_CPL_DES_KGH, 46.0, 70.0) == 46.0


def test_the_flood_is_xv_322915s_rated_steam_b60():
    """Handoff B-60, decided 2026-10-01: the valve's rated normal flow, 1000 kg/h of steam at
    9.0 bar a and 175 C (loop summary X 322915) — 564 kW of latent heat, where V1 floods 500."""
    assert (vl.FLOOD_STEAM_KGH, vl.FLOOD_STEAM_T_C) == (1000.0, 175.0) == (
        c.C001_FLOOD_STEAM_KGH, c.C001_FLOOD_STEAM_T_C)
    assert c.C001_FLOOD_STEAM_P_BARA == 9.0
    assert iapws.tsat_c(c.C001_FLOOD_STEAM_P_BARA) == pytest.approx(175.36, abs=0.01)
    assert vl.FLOOD_STEAM_KGH * iapws.hvap_kjkg(vl.FLOOD_STEAM_T_C) / 3600.0 == (
        pytest.approx(564.0, abs=0.5))


@pytest.mark.parametrize("p_9, steam", [(9.0, 1000.0), (8.5, 946.997), (7.0, 786.960),
                                        (5.0, 570.723), (2.0, 228.838)])
def test_the_flood_follows_the_9_bar_header_b73(p_9, steam):
    """Handoff B-73, decided 2026-10-02 (the Typo Rule). XV-322915 draws 329D009's header down a
    line choked against the atmospheric vent: the rated 1000 kg/h at the header's 9.0 bar a, in
    proportion to the header below it (the saturated steam's temperature moves it a little) —
    where V1's 500 kW and B-60's rated flow came whatever the header held. Shut, nothing. (At
    2 bar a the line is no longer choked against the atmosphere, now the standard 1.01325 bar
    (B-6): 228.838 kg/h, 228.849 on V1's 1.013.)"""
    assert vl.FLOOD_STEAM_P_BARA == c.C001_FLOOD_STEAM_P_BARA == 9.0
    assert vl.flood_steam_kgh(p_9) == pytest.approx(steam, abs=1e-3)
    assert vl.flood_steam_kgh(vl.FLOOD_STEAM_P_BARA) == vl.FLOOD_STEAM_KGH
    _, r = _design_tick()
    line = vl.vent_line(r.m_vent_kgh, r.y_vent, 46.0, True, p_9)
    assert line.m_steam_kgh == vl.flood_steam_kgh(p_9)
    assert vl.vent_line(r.m_vent_kgh, r.y_vent, 46.0, False, p_9).m_steam_kgh == 0.0


@pytest.mark.parametrize("vent, ti", [(None, 114.226), (0.0, 175.0), (3000.0, 93.900),
                                      (10000.0, 65.417)])
def test_the_steam_heats_ti_322015(vent, ti):
    """XV-322915 open on the design vent: TI-322015 reads 114.2 C, the trace steam with it. With no
    vent it reads the steam itself; a heavier vent dilutes it — 93.9 C on 3 t/h, 65.4 C on
    10 t/h."""
    _, r = _design_tick()
    line = vl.vent_line(r.m_vent_kgh if vent is None else vent, r.y_vent, 46.0, True)
    assert line.t_ti_322015_c == pytest.approx(ti, abs=1e-3)
    assert line.m_condensed_kgh == 0.0 and line.m_steam_kgh == vl.FLOOD_STEAM_KGH


def test_a_cold_heavy_vent_condenses_the_steam():
    """20 t/h of a 3 % wet gas at 5 C takes the flood and the trace steam below their dew point:
    260 kg/h of the water condenses and the line settles at 46.2 C, its vapour saturated (on the
    standard atmosphere, B-6; 45.482 C and 258.89 kg/h before the trace steam)."""
    y = {"N2": 0.97, "H2O": 0.03}
    line = vl.vent_line(20000.0, y, 5.0, True)
    assert line.t_ti_322015_c == pytest.approx(46.235, abs=1e-3)
    assert line.m_condensed_kgh == pytest.approx(260.34, abs=0.01)
    n_w = (20000.0 * 0.03 + line.m_steam_kgh + line.m_trace_kgh - line.m_condensed_kgh) / 18.0152
    p_w = n_w / (n_w + 20000.0 * 0.97 / 28.0134) * vl.VENT_LINE_P_BARA
    assert p_w == pytest.approx(iapws.psat_bara(line.t_ti_322015_c), rel=1e-9)


def test_i_22_1_is_pc22_5_1s_or_on_a_fail_open_valve():
    """AC4's PC22.5.1: XVY-322915 = NOT(TT-322015 > H2) OR HS-322915, and XV-322915 fails open.
    The valve opens on the limit alone, and the keyswitch shuts it whatever the limit says."""
    assert [vl.xv_322915_open(h2, hs) for h2, hs in
            ((False, False), (True, False), (False, True), (True, True))] == [
        False, True, False, False]


def _i_22_1(r, script):
    """I 22.1 over a script of (beds' top [C], HS-322915): each tick TI-322015 on the valve the
    tick before left, the limit, then the valve. Returns (TI, limit, valve) per tick."""
    trip, xv, out = vl.trip_22_1(), False, []
    for top, hs in script:
        ti = vl.vent_line(r.m_vent_kgh, r.y_vent, top, xv).t_ti_322015_c
        h2 = trip.update_from_pv(ti)
        xv = vl.xv_322915_open(h2, hs)
        out.append((ti, h2, xv))
    return trip, out


def test_the_flood_holds_itself_in_until_hs_322915_ends_it_b56():
    """Handoff B-56, decided 2026-10-01, on the plant DCS's H2 of 110 C (read back 2026-10-13; V1's
    57 / 55 C before). The top at 115 C fires 22.1 and the steam reads 146.7 C on TI-322015; the
    top back at 46 C, still 114.2 — over the limit, so the flood holds itself in. The keyswitch
    shuts the valve on the tick, TI-322015 falls to the trace steam's 53.7 C and the limit clears;
    released, the valve stays shut. Nothing latches: released onto a live limit, the flood comes
    straight back."""
    _, r = _design_tick()
    trip, out = _i_22_1(r, [(115.0, False), (115.0, False), (46.0, False), (46.0, True),
                            (46.0, True), (46.0, False), (115.0, True), (115.0, False)])
    assert (trip.trip_above, trip.clear_below, trip.operator_resettable) == (110.0, 108.0, False)
    assert [x[2] for x in out] == [True, True, True, False, False, False, False, True]
    assert [x[1] for x in out] == [True, True, True, True, False, False, True, True]
    assert out[1][0] == pytest.approx(146.733, abs=1e-3)
    assert out[2][0] == out[3][0] == pytest.approx(114.226, abs=1e-3)
    assert out[4][0] == out[5][0] == pytest.approx(53.708, abs=1e-3)
    assert out[6][0] == out[7][0] == pytest.approx(118.585, abs=1e-3)
