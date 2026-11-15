"""Behaviour of 323C003 / 323E002 — `ureasim.units.recirc.rectifying_column`.

Equivalence with V1 is proven tick by tick in
`tests/equivalence/test_rectifying_column_equivalence.py`. This file pins what stage 1 DOES: the
design point, the two independent gas sources behind PT-323201, the live stripper temperature
(As-Built §XXVIII.6), and the design seed a fixed point with PFD 314's urea closed on the drain
(handoff B-20, decided 2026-10-10). Every number here was measured on the module before it was
written down, on the decided chest anchor and cascade gains (2026-09-30, As-Built §XL.1-2) and
the closed PFD 314; and the stripper's blow-through with SV32351 / SV32352 (handoff A-16, decided
2026-10-03).
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_323 as d
from ureasim.data.design_point import R323_FEED_DES_KGH, R323_M314_DES
from ureasim.data.unit_323c003 import SV32351_RESEAT_BARA
from ureasim.data.unit_329 import P_LP_BARA
from ureasim.units.recirc import rectifying_column as rc

#: PFD 208 in mass percent, as the stripper publishes it.
BOTTOMS_PCT = dict(Urea=55.85, Biuret=0.24, NH3=7.92, CO2=10.28, H2O=25.68)


def _run(seconds: float, dt: float = 0.1, tt_322004: float = 172.0, drain: float = None,
         setup=None, sample=None):
    """Run stage 1 alone on fixed design boundaries; return the last result (or samples)."""
    col = rc.RectifyingColumn()
    tic, pic, lic = rc.tic_323007(), rc.pic_329202(), rc.lic_323501()
    if setup:
        setup(tic, pic, lic)
    drain = R323_FEED_DES_KGH if drain is None else drain
    out = []
    n = int(round(seconds / dt))
    for k in range(1, n + 1):
        r = col.step(tic, pic, lic, drain, 119.0, BOTTOMS_PCT, tt_322004, P_LP_BARA,
                     d.F004_P_BARA, d.E003_P_DES_BARA, dt)
        if sample and sample(k * dt):
            out.append(r)
    return out if sample else r


# ======================================================================================
# 1. The design point
# ======================================================================================

def test_the_first_design_tick_is_the_pfd():
    r = _run(0.1)
    assert (r.t_c, r.p_bara, r.p_target_bara) == (d.C003_T_SP_C, d.C003_P_BARA, d.C003_P_BARA)
    assert (r.flash_gas_ratio, r.heater_gas_ratio) == (1.0, 1.0)
    assert r.m_305_kgh == d.M305_DES_KGH
    assert r.m_314_kgh == R323_M314_DES
    assert (r.q_e002_kw, r.chest_p_bara) == (d.E002_Q_DES_KW, d.E002_PCHEST_DES_BARA)
    assert r.tt_323002_c == d.C003_T313_C
    assert r.vapour_domain == "electrolyte_gamma_phi"


# ======================================================================================
# 2. PT-323201 and its two gas sources
# ======================================================================================

def test_each_source_charges_the_column_on_its_own():
    """Stream 301 (the stripper bottoms' letdown flash) and stream 302 (the 323E002 gas) are
    independent terms: either alone holds the column above its 3.2 bar a discharge node."""
    f = rc.column_pressure_target_bara
    assert f(1.0, 1.0, 3.2) == 4.1
    assert f(1.0, 0.0, 3.2) == pytest.approx(3.5935, abs=1e-4)      # stripper flash only
    assert f(0.0, 1.0, 3.2) == pytest.approx(3.3319, abs=1e-4)      # heater gas only
    assert f(0.0, 0.0, 3.2) == 3.2


def test_the_sources_are_weighted_by_the_pfds_own_volumes():
    """301 is 64 % of the design gas load and 302 is 36 %, so 20 % more of each is not
    worth the same pressure."""
    f = rc.column_pressure_target_bara
    assert f(1.2, 1.0, 3.2) == pytest.approx(4.3120, abs=1e-4)
    assert f(1.0, 1.2, 3.2) == pytest.approx(4.2186, abs=1e-4)


@pytest.mark.parametrize("tt_322004, p_bara", [(160.0, 3.96453), (172.0, 4.10000),
                                               (180.0, 4.18171)])
def test_a_hotter_stripper_raises_the_column_pressure(tt_322004, p_bara):
    """Decided 2026-09-26 (As-Built §XXVIII.6): the flash source reads the LIVE TT-322004. V1's store-key typo
    read 172.0 for ever, and its column could not see the stripper at all."""
    r = _run(60.0, tt_322004=tt_322004)
    assert r.flash_gas_ratio == pytest.approx((tt_322004 - 119.0) / (172.0 - 119.0), rel=1e-12)
    assert r.p_bara == pytest.approx(p_bara, abs=1e-5)


def test_with_the_steam_shut_the_stripper_still_charges_the_column():
    """PV-329202 shut: the heater stops condensing and its source collapses, while the letdown
    flash keeps the column near its flash-only pressure. What the heater path still carries is
    the pool flashing off whatever it holds above its bubble point."""
    def shut(tic, pic, lic):
        pic.set_mode("MAN")
        pic.op = 0.0
    r = _run(300.0, setup=shut)
    # On V1's 40-sweep flash budget: exactly 0.0 kW, 0.0563, 3.6181 bar a, 116.07 C. The 60-sweep
    # budget reaches the rigorous vapour here (handoff A-9, decided 2026-09-30), and the chest's
    # solve on that branch closes to 1e-10 kW. LV-323501 on its vendor stroke and FL (B-44),
    # choking on the liquor's bubble pressure (B-46; unchoked: 0.0285 and 3.6058 bar a). On the
    # closed PFD 314 (B-20): 0.0282 and 115.55 C, where the table's row gave 0.0281 and 115.56.
    assert r.q_e002_kw == pytest.approx(0.0, abs=1e-9)
    assert r.flash_gas_ratio == 1.0
    assert r.heater_gas_ratio == pytest.approx(0.0282, abs=1e-4)
    assert r.p_bara == pytest.approx(3.6056, abs=1e-4)
    assert r.t_c == pytest.approx(115.55, abs=0.01)


def test_with_no_bottoms_the_column_falls_to_its_discharge_node():
    r = _run(120.0, drain=0.0)
    assert r.flash_gas_ratio == 0.0 and r.m_305_kgh == 0.0
    assert r.p_bara == pytest.approx(3.2031, abs=1e-4)


def test_a_hotter_set_point_opens_the_steam_valve():
    """TIC-323007 -> PIC-329202 in cascade: a 140 C set point raises the chest-pressure
    demand, PV-329202 opens, the duty and the heater gas rise, and so does the column."""
    r = _run(60.0, setup=lambda tic, pic, lic: tic.set_sp(140.0))
    assert r.tic_op_bara > d.E002_PCHEST_DES_BARA
    assert r.pic_op_pct > d.PV_329202_OP_DES_PCT
    assert r.q_e002_kw > d.E002_Q_DES_KW and r.heater_gas_ratio > 1.0
    assert r.t_c > d.C003_T_SP_C and r.p_bara > d.C003_P_BARA


# ======================================================================================
# 3. PFD 314's urea on the drain — handoff B-20, decided 2026-10-10
# ======================================================================================

def test_the_design_seed_is_a_fixed_point_with_its_urea_on_the_drain():
    """TIC-323007 in MAN for two hours: the column stays on its design point. PFD 314 is closed on
    its urea against the drain (`data.unit_323.W_S314`), so the back-solve sends no urea overhead
    and nothing accumulates: 135.00000002 C, the urea 2e-7 points over the row, the overhead and the
    drain within 4e-5 kg/h of design. On the table's row the column settled 0.0039 C off at
    +0.0033 points of urea, 6.8 kg/h to the drain instead of the overhead (V1's side, the
    equivalence test). Run at dt = 1 s."""
    def man(tic, pic, lic):
        tic.set_mode("MAN")
    r = _run(7200.0, dt=1.0, setup=man)
    assert r.t_c == pytest.approx(d.C003_T_SP_C, abs=1e-7)
    assert abs(r.w["Urea"] - d.W_S314["Urea"]) * 100.0 < 1e-6
    assert abs(r.m_305_kgh - d.M305_DES_KGH) < 1e-3
    assert abs(r.m_314_kgh - R323_M314_DES) < 1e-3
    assert r.p_bara == pytest.approx(d.C003_P_BARA, abs=1e-8)


def test_on_the_span_gains_the_closed_loop_settles_below_the_cap():
    """TIC-323007 in AUTO. On V1's gains — 2.0 bar/K on the master — the loop reaches for exactly
    135.000 C faster than the composition cap in `min(phi . m_feed, flash + heater)` lets the
    overhead follow, winds against the cap and cycles, +/-0.01 C with a 267-268 s period (the
    equivalence test runs V1's side). On the table's gains per cent of span, 0.075 bar/K, it
    settles: the column holds 135.000000 C to 1e-8 from the second hour on, PV-329202 stands at
    77.794 %, and the overhead never touches the cap (on the table's PFD 314, before B-20: 135.00000
    to 135.00002 C, 77.738 %). Run at dt = 1 s, which reproduces the 0.1 s trace to 1e-7."""
    tail = _run(10800.0, dt=1.0, sample=lambda t: t > 5400.0)
    t = [r.t_c for r in tail]
    assert max(abs(x - 135.0) for x in t) < 1e-8
    pv = [r.pic_op_pct for r in tail]
    assert max(pv) - min(pv) < 1e-3 and pv[-1] == pytest.approx(33.140, abs=1e-3)
    assert max(r.m_305_kgh for r in tail) < d.M305_DES_KGH


# ======================================================================================
# Handoff A-16, decided 2026-10-03: the stripper's blow-through and SV32351 / SV32352
# ======================================================================================

def _blown(seconds: float, p0: float = None, p_d001: float = d.E003_P_DES_BARA,
           blow: float = 30000.0, mw: float = 30.0) -> list:
    """Stage 1 on design boundaries with ``blow`` kg/h of stripper gas blowing through
    LV-322501; the results of every tick."""
    col = rc.RectifyingColumn()
    if p0 is not None:
        col.p_bara = p0
    loops = rc.tic_323007(), rc.pic_329202(), rc.lic_323501()
    return [col.step(*loops, R323_FEED_DES_KGH, 119.0, BOTTOMS_PCT, 172.0, P_LP_BARA,
                     d.F004_P_BARA, p_d001, 0.1, blow_in_kgh=blow, blow_mw=mw)
            for _ in range(int(round(seconds / 0.1)))]


def test_with_no_blowthrough_the_valves_stay_shut_and_everything_leaves_overhead():
    """At design for ten minutes: nothing blows through, the valves never lift, and every
    overhead flow is carried on a fraction of exactly 1.0."""
    for r in _blown(600.0, blow=0.0):
        assert (r.blow_in_kgh, r.relief_kgh, r.relief_lifted, r.overhead_frac) == (
            0.0, 0.0, False, 1.0)


def test_the_blowthrough_loads_the_column_by_its_own_volume():
    """30 t/h of stripper gas (molar mass 30) adds its ideal-gas volume at the head space's
    state to the line's load. Against the design 3.2 bar a downstream the column settles at
    5.471 bar a, below its valves' 6.01: they need the downstream node to rise with it."""
    first = _blown(0.1)[0]
    blow_m3h = 30000.0 / rc.gas_density_ideal(d.C003_P_BARA, first.t_c, 30.0)
    assert first.p_target_bara == rc.column_pressure_target_bara(
        first.flash_gas_ratio, first.heater_gas_ratio, d.E003_P_DES_BARA, blow_m3h)
    last = _blown(30.0)[-1]
    assert last.p_bara == pytest.approx(5.4486, abs=1e-4) and not last.relief_lifted


def test_sv32351_pops_at_set_and_reseats_on_its_blowdown():
    """The column at 6.05 bar a with 30 t/h blowing through and 323D001 at 4.3 bar a: the valves
    lift, relieve every kilogram the head space receives, and the law reads the downstream node
    alone; four ticks later the column passes 5.51 bar a and they reseat. Shut, the column climbs
    back over 2.2 s and they lift again on the 27th tick (PV-329202 on its vendor trim, decided
    2026-10-15; the 26th on V1's valve) — the saw-tooth of an oversized valve on half its sizing
    case."""
    rs = _blown(2.9, p0=6.05, p_d001=4.3)
    lifted = [k for k, r in enumerate(rs, 1) if r.relief_lifted]
    assert lifted == [1, 2, 3, 4, 27, 28, 29]
    for k in (1, 27):
        r = rs[k - 1]
        assert r.relief_kgh == r.m_305_kgh + r.blow_in_kgh and r.overhead_frac == 0.0
        assert r.p_target_bara == 4.3
    assert rs[3].p_bara < SV32351_RESEAT_BARA < rs[2].p_bara
    assert all(r.relief_kgh == 0.0 and r.overhead_frac == 1.0 for r in rs[4:26])


def test_the_valves_pass_their_certified_capacity_and_no_more():
    """Each orifice is back-solved from Sempell's 72 273.6 kg/h at 6.51 bar a; lifted on more gas
    than two valves pass, they pass exactly their critical flow at the live pressure."""
    sv = rc.sv_32351()
    cap = rc.psv_api520_choked_kgh(sv.area_m2, 6.51, 398.15, 25.07, k=1.010, kd=sv.kd)
    assert cap == pytest.approx(72273.6, rel=1e-12) and sv.count == 2
    w = rc.head_space_relief_kgh(sv, 6.05, 135.0, 0.0, 1.0e6, 25.07)
    assert w == 2 * rc.psv_api520_choked_kgh(sv.area_m2, 6.05, 408.15, 25.07, k=1.010,
                                             kd=sv.kd)
    assert rc.head_space_relief_kgh(rc.sv_32351(), 6.00, 135.0, 0.0, 1.0e6, 25.07) == 0.0


def test_pv_329202_on_its_vendor_trim_holds_the_chest_on_a_falling_header():
    """Decision 108's class, applied 2026-10-15: PV-329202 on Metso's DN 200 Neldisc from its
    32.92 % design stroke, where V1 runs it linear from 77.79 % (the harness proves V1's ==).
    The LP header 10 % down from 0.5 s: after five minutes V1's valve stands wide at 95.6 %, the
    chest at 3.8084 bar a and the column at 134.200 C; the Neldisc, at 39.3 (38.3 before decision 178) %, holds the chest at
    3.8909 (3.8940 before decision 178) and the column at 134.900 (134.936 before decision 178) C."""
    def run(chest):
        col = rc.RectifyingColumn(chest=chest)
        tic, pic, lic = rc.tic_323007(), rc.pic_329202(chest), rc.lic_323501()
        for k in range(1, 3001):
            col.step(tic, pic, lic, R323_FEED_DES_KGH, 119.0, BOTTOMS_PCT, 172.0,
                     P_LP_BARA * (0.9 if k > 5 else 1.0), d.F004_P_BARA, d.E003_P_DES_BARA, 0.1)
        return col.chest_p_bara, col.t_c, pic.op
    assert run(rc.V1_CHEST) == (pytest.approx(3.8084, abs=1e-4), pytest.approx(134.200, abs=1e-3),
                                pytest.approx(95.61, abs=0.01))
    assert run(rc.PV_329202_CHEST) == (pytest.approx(3.8909, abs=1e-4),
                                       pytest.approx(134.900, abs=1e-3),
                                       pytest.approx(39.31, abs=0.01))
