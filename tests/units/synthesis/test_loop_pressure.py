"""PT-329201: the loop's vapour inventory, its design hold, its backlog and SV32251 / SV32252."""

from __future__ import annotations

import pytest

from ureasim.core.relief import psv_api520_choked_kgh
from ureasim.core.stream import MW_COMP
from ureasim.data.unit_322_loop import (
    SV32251_K,
    SV32251_MW_REL,
    SV32251_P_REL_BARA,
    SV32251_RESEAT_BARA,
    SV32251_SET_BARA,
    SV32251_T_REL_K,
    SV32251_Z_REL,
    SYN_LOOP_IN_DES_KGH,
    SYN_LOOP_OUT_DES_KGH,
    SYN_LOOP_RESID_DES_KGH,
    SYN_LOOP_V_M3,
    SYN_LOOP_V_V1_M3,
)
from ureasim.data.unit_322e001 import LEVEL_SP_DES_PCT
from ureasim.data.unit_322e002 import LEVEL_NLL_PCT
from ureasim.data.unit_322e003 import HOLDUP_NLL_KG
from ureasim.data.unit_322r001 import OFFGAS_DES_KMOLH
from ureasim.units.synthesis.loop_pressure import (
    B_207_PER_BAR,
    SV32251_AREA_M2,
    Z_GAS_DES,
    LoopPressure,
    gas_mw,
    loop_liquid,
    loop_mass_fraction,
    vapour_capacity_kg_per_bar,
)
from ureasim.units.synthesis.reactor_inventory import M_LIQ_DES_KG

DT = 0.1

#: The liquid the design holds in the loop: (mass [kg], volume [m3]).
LIQ_DES = loop_liquid(M_LIQ_DES_KG, HOLDUP_NLL_KG, LEVEL_NLL_PCT, LEVEL_SP_DES_PCT)


#: The node's capacity on the design's liquids [kg/bar].
C_DES = (vapour_capacity_kg_per_bar(LIQ_DES[1], gas_mw(OFFGAS_DES_KMOLH), 183.0)
         + B_207_PER_BAR * M_LIQ_DES_KG)


def _design_step(node: LoopPressure, uncond=0.0, cool=1.0, frac=1.0, extra_in=0.0,
                 m_reactor=M_LIQ_DES_KG, dm_reactor=0.0):
    """One tick on the design boundary: in and out at V1's design flows."""
    return node.step(SYN_LOOP_IN_DES_KGH + extra_in, 0.0, 0.0, SYN_LOOP_OUT_DES_KGH, 0.0, 0.0,
                     uncond, cool, frac, dict(OFFGAS_DES_KMOLH), 183.0, DT,
                     m_reactor_kg=m_reactor, dm_liquid=(dm_reactor, 0.0, 0.0, 0.0))


def test_the_node_is_the_loops_vapour_and_the_reactor_liquors_buffering():
    """B-77 (b), decided 2026-10-09: 245.61 m3 of vessels — 241.7 in V1's plant, 322E001's
    replacement holding 28.83 m3 to its 24.7 (decision 154) and 0.222 m3 of plugged bores out of
    322E002 and 322E003 (decision 155) — 93.2 m3 of vapour over the design liquids, the gas's 0.763
    compressibility on the PFD's 113.3 kg/m3 — 74.7 kg/bar — and PFD 207's buffering, 0.01536
    kg/(kg.bar), 2088 kg/bar on the design holdup. An empty loop holds 196.9 kg/bar of vapour and
    nothing buffers it."""
    assert SYN_LOOP_V_M3 == pytest.approx(245.6078, abs=1e-4)
    assert SYN_LOOP_V_V1_M3 == pytest.approx(241.7, abs=1e-9)
    assert Z_GAS_DES == pytest.approx(0.76273, abs=1e-5)
    assert B_207_PER_BAR == pytest.approx(0.0153639, abs=1e-7)
    assert SYN_LOOP_V_M3 - LIQ_DES[1] == pytest.approx(93.172, abs=1e-3)
    mw = gas_mw(OFFGAS_DES_KMOLH)
    assert vapour_capacity_kg_per_bar(LIQ_DES[1], mw, 183.0) == pytest.approx(74.709, abs=1e-3)
    assert B_207_PER_BAR * M_LIQ_DES_KG == pytest.approx(2088.01, abs=0.01)
    assert vapour_capacity_kg_per_bar(0.0, mw, 183.0) == pytest.approx(196.938, abs=1e-3)
    assert loop_liquid(0.0, 0.0, 0.0, 0.0) == (0.0, 0.0)


def test_mass_the_liquid_takes_is_not_pressure():
    """10 t/h more in, all of it gained by the reactor's holdup: V1's node rises 6.7 bar an hour;
    here only the vapour the liquid displaces is compressed: 10 m3 of the 93 m3, 0.51 bar in the
    hour."""
    node = LoopPressure()
    m_r = M_LIQ_DES_KG
    for _ in range(36000):
        m_r += 10000.0 * DT / 3600.0
        r = _design_step(node, extra_in=10000.0, m_reactor=m_r, dm_reactor=10000.0)
    assert r.dm_liq_kgh == pytest.approx(10000.0 * (1.0 - r.m_liq_kg * 0.0) - 10000.0 / 990.0
                                         * 140.7 * gas_mw(OFFGAS_DES_KMOLH)
                                         / (Z_GAS_DES * 0.0831446261815324 * 456.15), rel=1e-3)
    assert node.p_syn_bara - 140.7 == pytest.approx(0.5108, abs=1e-4)


def test_the_residual_is_v1s_and_holds_the_design():
    """+2024.9 kg/h the design pins leave in the boundary (handoff B-75); credited back on a full
    loop, the node holds 140.7 bar a."""
    assert SYN_LOOP_RESID_DES_KGH == pytest.approx(2024.909, abs=1e-3)
    node = LoopPressure()
    r = _design_step(node)
    assert r.m_net_kgh == pytest.approx(0.0, abs=1e-9)
    assert r.p_syn_bara == pytest.approx(140.7, abs=1e-12)


def test_without_the_credit_the_residual_climbs_the_loop():
    """An empty loop integrates its raw balance: the residual is 0.94 bar an hour on the design's
    2160 kg/bar (1.35 on V1's 1500)."""
    node = LoopPressure()
    for _ in range(36000):
        _design_step(node, frac=0.0)
    assert node.p_syn_bara - 140.7 == pytest.approx(SYN_LOOP_RESID_DES_KGH / C_DES, rel=1e-9)


def test_a_liquor_above_its_bubble_point_buffers_its_saturation_fraction():
    """B-91 (a), decided 2026-10-10: the reactor liquor's buffering taken at the liquor's
    saturation fraction — at 0.5, half the 2088 kg/bar; at 0, the vapour's 74.7 kg/bar alone, so a
    loop below its melt's bubble pressure pressurises on its vapour."""
    node = LoopPressure()
    c = {f: node.step(SYN_LOOP_IN_DES_KGH, 0.0, 0.0, SYN_LOOP_OUT_DES_KGH, 0.0, 0.0, 0.0, 1.0, 1.0,
                      dict(OFFGAS_DES_KMOLH), 183.0, DT, sat_frac=f) for f in (1.0, 0.5, 0.0)}
    assert c[1.0].c_buf_kg_per_bar == B_207_PER_BAR * M_LIQ_DES_KG
    assert c[0.5].c_buf_kg_per_bar == pytest.approx(0.5 * B_207_PER_BAR * M_LIQ_DES_KG, rel=1e-15)
    assert c[0.0].c_buf_kg_per_bar == 0.0
    assert c[0.0].c_vap_kg_per_bar == pytest.approx(74.709, abs=1e-3)


def test_the_loop_mass_fraction():
    assert loop_mass_fraction(80.0, 50.0, 50.0) == 1.0
    assert loop_mass_fraction(90.0, 60.0, 60.0) == 1.0
    assert loop_mass_fraction(40.0, 25.0, 25.0) == 0.5


def test_the_backlog_recondenses_on_its_next_pass():
    """1000 kg/h uncondensed for a minute, then full cooling: the backlog grows to 16.7 kg and
    decays on the 4 min pass. It adds no pseudo-mass to the node (B-77 (b)): the vapour it holds is
    what 322E003's sump did not receive, which the liquid inventory carries; V1 adds 0.902 of it."""
    node = LoopPressure()
    for _ in range(600):
        r = _design_step(node, uncond=1000.0, cool=0.0)
    assert node.vap_excess_kg == pytest.approx(1000.0 / 60.0, rel=1e-9)
    assert r.m_net_kgh == pytest.approx(0.0, abs=1e-9)
    m0 = node.vap_excess_kg
    for _ in range(2400):
        r = _design_step(node)
    assert node.vap_excess_kg == pytest.approx(m0 * (1.0 - DT / 240.0) ** 2400, rel=1e-9)
    assert r.m_recond_kgh > 0.0


def test_sv32251_and_sv32252_relieve_on_their_certified_capacity():
    """Each orifice back-solved on Sempell's 116 667 kg/h at 175.91 bar a; two lift at 160.01 bar a
    and vent the reactor top's vapour until 144.11, 642 s on the design's 2160 kg/bar; never past
    the reseat in a tick."""
    assert psv_api520_choked_kgh(SV32251_AREA_M2, SV32251_P_REL_BARA, SV32251_T_REL_K,
                                 SV32251_MW_REL, k=SV32251_K, z=SV32251_Z_REL) \
        == pytest.approx(116667.0, rel=1e-12)
    assert (SV32251_SET_BARA, SV32251_RESEAT_BARA) == pytest.approx((160.013, 144.113), abs=1e-9)
    node = LoopPressure(p_syn_bara=160.5)
    r = _design_step(node)
    assert r.relief_lifted and r.m_relief_kgh > 100000.0
    m_og = sum(v * MW_COMP[k] for k, v in OFFGAS_DES_KMOLH.items())
    assert r.m_relief_nh3_kgh == pytest.approx(
        r.m_relief_kgh * OFFGAS_DES_KMOLH["NH3"] * MW_COMP["NH3"] / m_og, rel=1e-12)
    lifted = 0
    while node.sv_32251.lifted:
        _design_step(node)
        lifted += 1
    assert node.p_syn_bara <= SV32251_RESEAT_BARA + 1e-9
    assert node.p_syn_bara > SV32251_RESEAT_BARA - 0.01
    assert 6400 < lifted < 6450
