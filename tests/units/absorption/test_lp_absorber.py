"""Behaviour of 322C001, the LP absorber — `ureasim.units.absorption.lp_absorber`.

Equivalence with V1 is proven in `tests/equivalence/test_lp_absorber_equivalence.py` and
`test_lp_absorber_decided_equivalence.py`. This file pins what the absorber DOES: the PFD's design
point; that the liquor's only heat sink is the washes' sensible heat against 755 from 322E006 —
so whatever cuts the wash, warms it or loads the gas heats the liquor; the carbamate liquor a
cooling-loss purge brings from its letdown line; SV32253's relief of a shut vent; XV-322915's
flood, in the vent line; and the heel and the full column, the liquor's books closed.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_322c001 as c
from ureasim.data import unit_322e006 as e6
from ureasim.data.unit_322e003 import CCW_KGH_DES, CCW_T_IN_DES_C, HIC604_DES_PCT, OFFGAS_P_BARA
from ureasim.data.unit_322r001 import OFFGAS_DES_KMOLH as REACTOR_OFFGAS_DES_KMOLH
from ureasim.units.absorption import feed_cooler as fc
from ureasim.units.absorption import lp_absorber as la
from ureasim.units.absorption import packed_beds as pb
from ureasim.units.absorption import vent_line as vl
from ureasim.units.synthesis.purge_valve import purge_valve_322604
from ureasim.units.synthesis.scrubber import scrubber_322e003

DT = 0.5


def _gas(scale=1.0, nh3=1.0, co2=1.0, t_gas=None):
    pin = la.design_pin()
    comp = {k: v * scale * (nh3 if k == "NH3" else co2 if k == "CO2" else 1.0)
            for k, v in pin.gas_kmolh.items()}
    return comp, sum(v * pb.MW_COMP[k] for k, v in comp.items()), (
        pin.t_gas_c if t_gas is None else t_gas)


def _condensing_purge(cool_frac):
    """HV-322604's purge on a cooling loss in 322E003: its gas, and the liquor it condensed."""
    sc = scrubber_322e003(REACTOR_OFFGAS_DES_KMOLH, 1.0, CCW_T_IN_DES_C, CCW_KGH_DES,
                          cool_frac=cool_frac)
    r = purge_valve_322604(sc.offgas_kmolh, sc.t_offgas_c, HIC604_DES_PCT, OFFGAS_P_BARA)
    gas = {k: v for k, v in r.vapour_kmolh.items() if v > 0.0}
    return gas, sum(v * pb.MW_COMP[k] for k, v in gas.items()), r.t_out_c, r.liquor_kmolh


def _run(seconds, dt=DT, gas=None, m755=c.C001_M755_DES_KGH, cpl=c.C001_CPL_DES_KGH, xv=False,
         man=None, t0=10.0, t755=c.C001_T_755_C):
    """Drive the absorber from its design seed; from `t0` the boundaries given replace the
    design's. Returns the last result, every lift of SV32253, its band, and the liquor the books
    did not see."""
    unit, loops = la.LpAbsorber(), la.LpAbsorberLoops()
    for name, op in (man or {}).items():
        getattr(loops, name).set_mode("MAN")
        getattr(loops, name).op = op
    r, lifts, p_hi, p_lo, made = None, [], 0.0, 99.0, 0.0
    for k in range(1, int(round(seconds / dt)) + 1):
        t = round(k * dt, 6)
        late = t > t0
        g = gas if (gas is not None and late) else _gas()
        x755 = m755 if late else c.C001_M755_DES_KGH
        x954 = cpl if late else c.C001_CPL_DES_KGH
        pre, was = unit.m_kg, unit.sv_32253.valve.lifted
        r = unit.step(loops, g[0], g[1], g[2], x755, t755 if late else c.C001_T_755_C, x954,
                      xv and late, dt, liquor_kmolh=g[3] if len(g) > 3 else None)
        made += unit.m_kg - pre - (x755 + x954 + r.m_abs_kgh + r.m_liquor_kgh - r.m_756_kgh
                                   - r.m_overflow_kgh) * dt / 3600.0
        if r.relief_lifted and not was:
            lifts.append(t)
        if lifts:
            p_hi, p_lo = max(p_hi, r.p_bara), min(p_lo, r.p_bara)
    return r, lifts, p_hi, p_lo, made


def test_the_design_point_is_the_pfds():
    """Twenty minutes on the design boundaries: 43 C, 3.9 bar a, LI-322502 on 50 % with 506 kg;
    the beds take up the PFD's 130 kg/h (to 2e-9), PV-322201 vents 1578.3 kg/h of a 26.6 kg/kmol
    gas carrying 1.79 kg/h of NH3, and LV-322502 draws 33 358."""
    r, _, _, _, made = _run(1200.0)
    assert (r.t_c, r.p_bara, r.level_pct) == (pytest.approx(43.0, abs=1e-12),
                                              pytest.approx(3.9, abs=1e-12),
                                              pytest.approx(50.0, abs=1e-9))
    assert r.m_abs_kgh == pytest.approx(130.0, abs=3e-9)
    assert (r.m_vent_kgh, r.mw_vent, r.m_756_kgh) == (pytest.approx(1578.32, abs=0.01),
                                                      pytest.approx(26.608, abs=1e-3),
                                                      pytest.approx(33358.0, abs=1e-6))
    assert r.y_vent["NH3"] * r.m_vent_kgh == pytest.approx(1.794, abs=1e-3)
    assert not (r.drained or r.overloaded or r.relief_lifted) and abs(made) < 1e-9


def test_the_liquor_has_no_sink_but_its_washes():
    """There is no cooling water: the design's absorption heat leaves as the washes' sensible heat,
    sens = -(gas + residual). 755 lost (322P002 tripped), 954 alone carries it: the liquor runs to
    68.9 C and the beds, on a hot sump, take up 65 kg/h. The polish still holds the gas, which
    leaves at 954's 46 C: TI-322015, 53.47 C on the trace steam, does not see the hot sump, and
    trip 22.1 stays clear."""
    r, _, _, _, _ = _run(1200.0)
    assert r.q_sens_kw == pytest.approx(-(r.q_gas_kw + la.design_pin().q_res_kw), abs=1e-9)
    hot, _, _, _, made = _run(1200.0, m755=0.0)
    assert hot.t_c == pytest.approx(68.896, abs=1e-3) and hot.t_top_c == 46.0
    assert hot.t_ti_322015_c == pytest.approx(53.474, abs=1e-3)
    assert hot.m_abs_kgh == pytest.approx(65.08, abs=0.01) and abs(made) < 1e-9


def test_322e006_losing_its_cooling_water_heats_the_liquor():
    """B-54. 322E006's cooling water lost: 755 arrives at 744's 44 C, the liquor settles at
    46.72 C, 3.7 K hotter, and the vent slips 2.12 kg/h of NH3 against the design's 1.79."""
    t755 = fc.feed_cooler_322e006(e6.E006_M744_DES_KGH, e6.E006_T744_DES_C, 0.0).t_755_c
    r, _, _, _, made = _run(1200.0, t755=t755)
    assert (r.t_755_c, r.t_c) == (44.0, pytest.approx(46.718, abs=1e-3))
    assert r.y_vent["NH3"] * r.m_vent_kgh == pytest.approx(2.118, abs=1e-3)
    assert abs(made) < 1e-9


def test_an_ammonia_rich_purge_heats_the_liquor():
    """A cooling loss upstream: the purge 1.2 times, its NH3 six times and CO2 three, let down at
    26 C. The beds take up 844 kg/h, 433 kW goes into the liquor, and it settles at 52.1 C with
    the vent still clean, 0.33 % NH3 by mass."""
    r, _, _, _, _ = _run(1200.0, gas=_gas(1.2, 6.0, 3.0, 26.0))
    assert (r.m_abs_kgh, r.q_gas_kw, r.t_c) == (pytest.approx(844.28, abs=0.01),
                                                pytest.approx(433.48, abs=0.01),
                                                pytest.approx(52.096, abs=1e-3))
    assert r.y_vent["NH3"] == pytest.approx(0.00332, abs=1e-5)


def test_a_condensing_purge_brings_its_liquor_to_the_sump():
    """B-19. 322E003 at 90 % of its cooling: the purge reaches the column at 71.7 C with 120 kg/h
    of carbamate liquor, which joins the sump; its gas climbs the beds, which take up 1897 kg/h.
    The liquor settles at 68.46 C, the vent slipping 17.4 kg/h of NH3."""
    r, _, _, _, made = _run(1200.0, gas=_condensing_purge(0.9))
    assert (r.t_gas_c, r.m_liquor_kgh) == (71.7, pytest.approx(120.35, abs=0.01))
    assert (r.t_c, r.m_abs_kgh) == (pytest.approx(68.464, abs=1e-3),
                                    pytest.approx(1897.40, abs=0.01))
    assert r.y_vent["NH3"] * r.m_vent_kgh == pytest.approx(17.41, abs=0.01)
    assert abs(made) < 1e-9


def test_sv32253_holds_a_shut_vent():
    """PV-322201 shut, on the 0.1 s step: SV32253 lifts at 6.013 bar a 15.3 s on, vents to 5.513
    on the gas blowdown and lifts again every 4.3 s — 136 times in ten minutes, never above
    6.026 bar a. The liquor's books close; the relief takes gas only."""
    r, lifts, p_hi, p_lo, made = _run(600.0, dt=0.1, man={"pic_322201": 0.0})
    assert lifts[:3] == [15.3, 19.6, 23.9] and len(lifts) == 136
    assert p_hi == pytest.approx(6.0264, abs=1e-4) and p_lo == c.SV32253_RESEAT_BARA == 5.513
    assert abs(made) < 1e-9


def test_xv_322915s_flood_goes_into_the_vent_line():
    """B-55, B-60. XV-322915 open: its rated 1000 kg/h of steam enter the vent line, where
    TI-322015 reads 114.2 C with the trace steam (112.4 without it); the liquor's balance does not
    see it, and the liquor stays at 43.0 C."""
    r, *_ = _run(2400.0, xv=True)
    assert r.m_flood_kgh == vl.FLOOD_STEAM_KGH
    assert r.t_c == pytest.approx(43.0, abs=1e-9)
    assert r.t_ti_322015_c == pytest.approx(114.226, abs=1e-3)


def test_hv_322604_shut_leaves_the_column_where_its_vent_left_it():
    """No purge: the beds take up nothing, PIC-322201 shuts PV-322201, and the column stands at
    2.25 bar a with the liquor cooling to 40.35 C."""
    r, *_ = _run(1200.0, gas=_gas(0.0))
    assert (r.m_abs_kgh, r.m_vent_kgh, r.pic_op_pct) == (0.0, 0.0, 0.0)
    assert (r.p_bara, r.t_c) == (pytest.approx(2.2474, abs=1e-4), pytest.approx(40.352, abs=1e-3))


def test_lv_322502_at_the_heel_and_a_full_column():
    """LV-322502 wide open: the draw falls to what arrives, flagged; shut, the column fills its
    3.60 m3 in 336 s and the excess leaves as a stream. The books close both ways."""
    r, _, _, _, made = _run(600.0, man={"lic_322502": 100.0})
    assert r.drained and r.m_kg == c.C001_M_FLOOR_KG and abs(made) < 1e-9
    r, _, _, _, made = _run(600.0, man={"lic_322502": 0.0})
    assert r.m_kg == c.C001_FULL_KG and r.m_overflow_kgh == pytest.approx(33358.0, abs=1e-3)
    assert abs(made) < 1e-9
