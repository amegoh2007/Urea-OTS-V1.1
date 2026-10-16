"""Unit 329's steam network stepped — three vapour nodes over three drums of water.

What this models
----------------
329D005 (the HP saturator, 19.7 bar a), 329D009 (the 9-bar drum) and 322D001A/B (the LP drums,
4.0 bar g — handoff B-69) as lumped saturated vapour capacitances over the water each drum holds,
the battery limit's 25 bar a steam held. Each tick, in V1's order:

  1. LIC-329502 drains 329D005 to 329D009 through LV-329502; PIC-329204 admits the supply through
     PV-329204; HV-329601 vents 329D005 (trip 21.2's forcing); 902's superheat boils 329D005's
     water, ds_5 = m_902 (h_902 - h_g) / h_fg; a drum gives at most what it holds (decision 11);
     4658 / 57 989 of LV-329502's condensate flashes into 329D009's vapour (V1's anchor).
  2. PIC-329205's split range admits PV-329205A or lets PV-329205B down to the LP header; 329D009
     pays 903's superheat from its own water, V1's 275 kg/h of 903's 1754 (handoff B-70).
  3. The PIC-329207 trio vents through PV-329207A, exports through PV-329207B and admits through
     PV-329207C (and HV-329602 in parallel, by hand); 963's superheat boils 322D001's water.
  4. LIC-329503 drains 329D009 through LV-329503 and LIC-329504 makes 322D001 up through
     LV-329504, at the tick's starting pressures; 913 flashes into the LP header as it arrives,
     x = (h_f,9 - h_f,LP) / h_fg,LP (handoff B-70; V1 evaluates the two valves after the pressure
     step and flashes nothing).
  5. Each vapour node's balance, every simulated user's live draw on it and the rest at their PFD
     rows (handoff B-68), stepped semi-implicitly on its capacitance and the conductance of
     everything that resists it (V1's scheme):
         P' = P + r dt / (C + g dt),   g = -dr/dP (one 1e-3 bar perturbation, at least 0)
     with nothing holding the LP header up (V1 floors it at 3.5 bar a, handoff B-70); a lifted
     safety valve vents what the tick would otherwise carry past its reseat (decision 32).
  6. Each drum's water: 329D005 the stripper's condensate in, ds_5 and LV-329502 out; 329D009
     what LV-329502 leaves after its flash in, ds_9 and LV-329503 out; 322D001 what LV-329503
     leaves after its flash and LV-329504 in, 322E002's raising, the superheats and 959's
     blowdown out (handoff B-70). A full drum's excess is published as an overflow.

A 322E002 tube leak (handoff B-82, decided 2026-10-09; `units.synthesis.tube_leak`) discharges
process into the shell, so into 322D001A/B: its volatiles and inerts into the steam space with the
raising, its water and solids into the drums' water, its heat boiling (or condensing) that water.
The solids (urea, biuret) stay in the water and leave with the blowdown and any overflow at the
water's strength (``m_d001_solids_kg``); the volatiles leave with the LP steam
(``flows_kgh["leak_vapour"]``). With no leak every term is a literal zero.

The draws are on the PFD's basis (decision 47's class, `pfd_basis_kgh`): the stripper's duty ratio
on the 66 902 kg/h it condenses at design, the HPCC's raising ratio on the 66 359 it raises, each
chest's ratio on its PFD row.

The LP header sits downstream of 322D001A/B
-------------------------------------------
322D001A/B's water is boiled in 322E002's shell: it runs down to the shell, the HPCC's condensing
carbamate boils it at the drums' saturation, and the steam returns to the drums, which separate it
(the ``raise`` this module takes out of 322D001's water and into its steam space, the shell at
``t_lp_c``). The drums' tops (N3) discharge it as PFD 917 into the DN 700 LP header (line
700-STLS1-329353), where PT-329207 reads the pressure PIC-329207's trio
controls and every LP user, PV-329207A and PV-329207B draw. 963 (PV-329207C, HV-329602), 915 (913's
flash) and 916 (LV-329504's make-up) enter the drums; 960 (PV-329205B) joins the header downstream
of them, so its superheat leaves with the header's steam and boils no drum water (PFD 26,
UD-VT-329-FB-0001; P&ID 107/1, UD-VT-329-FB-0006; the process engineer's topology note,
2026-10-02). The header has no hold-up of its own: the PFD puts 917 and PT-329207's normal at the
same 4.4 bar a and no document gives the line's volume, so the drums' steam space is the header's
capacitance and one pressure serves both; 917 is the drums' discharge, what the header's users and
valves take less 960.

Source
------
V1 ``backend/steam_system.py`` ``step_steam`` and its call in ``main.py`` (7823-7856); handoffs
B-68, B-69, B-70 (decided 2026-10-02); As-Built Parts LIII, LIV and LVI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from ureasim.core.relief import GasReliefValve, SafetyValve, psv_area_from_rated_m2
from ureasim.data.unit_329 import (
    BLOWDOWN_KGH,
    FLASH9_FRACTION,
    H_902_KJKG,
    H_963_KJKG,
    MP9_USERS_LIVE,
    MP9_USERS_PFD,
    LP_USERS_LIVE,
    LP_USERS_PFD,
    P_ATM_VENT_BARA,
    P_HP_BARA,
    P_LP_BARA,
    P_MP_BARA,
    P_SUP_BARA,
    P_TURBINE_OUT_BARA,
    RAISE_DES_KGH,
    STEAM_MW,
    STEAM_PFD_KGH,
    STRIP_DES_KGH,
    design_users,
)
from ureasim.data.unit_329_network import (
    C_9_KG_BAR,
    C_LP_KG_BAR,
    C_MP_KG_BAR,
    DRUM_M_FLOOR_KG,
    DS9_DES_KGS,
    K_207A,
    K_207B,
    K_902,
    K_963,
    HV601_P1_DES_BARA,
    HV601_P2_DES_BARA,
    K_HV601,
    K_HV602,
    LEVEL_SP_DES_PCT,
    LV502_OP_DES_PCT,
    LV503_OP_DES_PCT,
    LV504_OP_DES_PCT,
    M_903_DES_KGS,
    N_SV_322D001,
    P207A_P1_DES_BARA,
    P207A_P2_DES_BARA,
    P963_P1_DES_BARA,
    P963_P2_DES_BARA,
    SV_322D001,
    SV_329D005,
    SV_329D009,
    V_D001_VAP_M3,
    V_D005_VAP_M3,
    V_D009_VAP_M3,
)
from ureasim.thermo.iapws import tsat_c
from ureasim.thermo.water_steam import (
    flash_fraction,
    superheat_water_ratio,
)
from ureasim.units.steam.drums import D001, D005, D009
from ureasim.units.steam.header_control import (
    Hv329601,
    LevelLoop,
    Pic329204,
    Pic329205,
    Pic329207,
    v1_pic_329204,
    v1_pic_329207,
)
from ureasim.units.steam.steam_valves import (
    lv_329502_kgs,
    lv_329503_kgs,
    lv_329504_kgs,
    pv_329204_kgs,
    pv_329205a_kgs,
    pv_329205b_kgs,
    pv_329207a_kgs,
    pv_329207b_kgs,
    steam_valve_kgs,
)

#: The perturbation the resisting conductance is read over [bar]. Source: V1 ``_DP_PROBE``.
DP_PROBE_BAR = 1.0e-3


def pfd_basis_kgh(row_kgh: float, live: float, design: float) -> float:
    """A unit's live draw on its PFD row [kg/h] (decision 47's class).

    Process utility
    ---------------
    Where an equipment's own model draws a different design flow from the PFD's row — the
    stripper's vendor rating, the HPCC's balance, 324E003's chest — the header sees the row
    scaled by the unit's live-to-design ratio, so the network's design is the PFD's and the
    unit's response is its own.
    """
    return row_kgh * live / design if design > 0.0 else 0.0


def _users_lp() -> dict:
    return design_users({**LP_USERS_LIVE, **LP_USERS_PFD})


def _users_9() -> dict:
    return design_users({**MP9_USERS_LIVE, **MP9_USERS_PFD})


@dataclass(frozen=True)
class SteamDraws:
    """What the plant takes from and gives the network on a tick [kg/h], on the PFD's basis.

    ``strip_kgh`` the steam 322E001's shell condenses from 329D005; ``raise_kgh`` the steam
    322E002 raises out of 322D001's water; ``users_9_kgh`` and ``users_lp_kgh`` each header's
    users by PFD stream (932, PV-329207B's export, excepted); ``c003_kgh`` 328C003's steam from the
    battery limit (911), which loads no header — FT-329403 reads it.
    """

    strip_kgh: float = STRIP_DES_KGH
    raise_kgh: float = RAISE_DES_KGH
    users_9_kgh: Mapping = field(default_factory=_users_9)
    users_lp_kgh: Mapping = field(default_factory=_users_lp)
    c003_kgh: float = STEAM_PFD_KGH["911"]
    #: A 322E002 tube leak into the shell (B-82): its volatiles to the steam space, its water and
    #: solids to the drums' water, of which the solids, and the drums' water its heat boils.
    leak_vapour_kgh: float = 0.0
    leak_liquid_kgh: float = 0.0
    leak_solids_kgh: float = 0.0
    leak_boil_kgh: float = 0.0


@dataclass(frozen=True)
class SteamNetworkResult:
    """One tick: the headers [bar a, deg C], the flows [kg/h], the strokes [%] and levels [%].

    ``p_lp_bara`` and ``t_lp_c`` are 322D001A/B's steam space, which is the LP header's: PT-329207
    reads it on the header, 322E002's shell boils at its saturation."""

    p_hp_bara: float
    p_9_bara: float
    p_lp_bara: float
    #: The LP header as the tick began [bar a]: what 322E002's shell boiled against this tick.
    p_lp_start_bara: float
    t_hp_c: float
    t_9_c: float
    t_lp_c: float
    flows_kgh: dict
    strokes_pct: dict
    levels_pct: dict
    #: The vapour nodes' and the drums' accumulation [kg/h], in less out.
    vapour_residual_kgh: dict
    water_residual_kgh: dict
    relief_kgh: dict
    overflow_kgh: dict
    hv_329601_blocked: bool
    #: 322D001A/B's water's solids (urea, biuret) from a tube leak [mg/kg] (B-82).
    d001_solids_ppm: float = 0.0


def _relief_valve(tag: str, sv: dict, count: int = 1) -> GasReliefValve:
    return GasReliefValve(valve=SafetyValve(tag, sv["set"], sv["reseat"]),
                          area_m2=psv_area_from_rated_m2(sv["cap"], sv["p_rel"], sv["t_rel_k"],
                                                         STEAM_MW, z=sv["z"]),
                          count=count)


def _cap(m_kg: float, inflow: float, outflow: float, dt: float) -> float:
    """The factor a drum's outflows are scaled by so it keeps its heel [-] (decision 11)."""
    available = (m_kg - DRUM_M_FLOOR_KG) / dt + inflow
    if outflow <= available or outflow <= 0.0:
        return 1.0
    return max(available, 0.0) / outflow


def _implicit(p: float, res: float, res_fn, capacitance: float, dt: float) -> tuple:
    """The resisting conductance [kg/s per bar] and V1's semi-implicit step's denominator."""
    g = (res - res_fn(p + DP_PROBE_BAR)) / DP_PROBE_BAR
    return capacitance + max(g, 0.0) * dt


@dataclass
class SteamNetwork:
    """The network's state, seeded on the design (`ureasim.data.unit_329`'s closure)."""

    p_hp_bara: float = P_HP_BARA
    p_9_bara: float = P_MP_BARA
    p_lp_bara: float = P_LP_BARA
    m_d005_kg: float = field(default_factory=lambda: D005.mass_at_level_kg(LEVEL_SP_DES_PCT))
    m_d009_kg: float = field(default_factory=lambda: D009.mass_at_level_kg(LEVEL_SP_DES_PCT))
    m_d001_kg: float = field(default_factory=lambda: D001.mass_at_level_kg(LEVEL_SP_DES_PCT))
    #: The solids a 322E002 tube leak has left in 322D001A/B's water [kg] (B-82).
    m_d001_solids_kg: float = 0.0
    pic_329204: Pic329204 = field(default_factory=Pic329204)
    hv_329601: Hv329601 = field(default_factory=Hv329601)
    pic_329205: Pic329205 = field(default_factory=Pic329205)
    pic_329207: Pic329207 = field(default_factory=Pic329207)
    lic_329502: LevelLoop = field(
        default_factory=lambda: LevelLoop("LIC-329502", True, LV502_OP_DES_PCT))
    lic_329503: LevelLoop = field(
        default_factory=lambda: LevelLoop("LIC-329503", True, LV503_OP_DES_PCT))
    lic_329504: LevelLoop = field(
        default_factory=lambda: LevelLoop("LIC-329504", False, LV504_OP_DES_PCT))
    #: HV-329602, PV-329207C's parallel hand valve [%].
    hv_329602_pct: float = 0.0
    sv_329d005: GasReliefValve = field(default_factory=lambda: _relief_valve("SV32951", SV_329D005))
    sv_329d009: GasReliefValve = field(default_factory=lambda: _relief_valve("SV32952", SV_329D009))
    sv_322d001: GasReliefValve = field(
        default_factory=lambda: _relief_valve("SV32978", SV_322D001, N_SV_322D001))
    #: PV-329204, PV-329207A and PV-329207B on Metso's trims (decision 108's class, decided
    #: 2026-10-15); False is V1's anchored law, which ``v1_butterflies()`` gives the harness.
    vendor_butterflies: bool = True

    def _m_902(self, op_pct: float, p_hp_bara: float) -> float:
        """PV-329204's supply [kg/s] at a 329D005 pressure."""
        if self.vendor_butterflies:
            return pv_329204_kgs(op_pct, P_SUP_BARA, p_hp_bara)
        return steam_valve_kgs(K_902, op_pct, P_SUP_BARA, p_hp_bara, P_SUP_BARA, P_HP_BARA)

    def _m_207a(self, op_pct: float, p_lp_bara: float) -> float:
        """PV-329207A's vent [kg/s] at an LP header pressure."""
        if self.vendor_butterflies:
            return pv_329207a_kgs(op_pct, p_lp_bara)
        return steam_valve_kgs(K_207A, op_pct, p_lp_bara, P_ATM_VENT_BARA, P207A_P1_DES_BARA,
                               P207A_P2_DES_BARA)

    def _m_932(self, op_pct: float, p_lp_bara: float) -> float:
        """PV-329207B's export to 320MT02 [kg/s] at an LP header pressure."""
        if self.vendor_butterflies:
            return pv_329207b_kgs(op_pct, p_lp_bara)
        return steam_valve_kgs(K_207B, op_pct, p_lp_bara, P_TURBINE_OUT_BARA, P_LP_BARA,
                               P_TURBINE_OUT_BARA)

    @property
    def t_hp_c(self) -> float:
        """329D005's saturation [deg C]: the temperature 322E001's shell condenses at."""
        return tsat_c(self.p_hp_bara)

    @property
    def t_lp_c(self) -> float:
        """322D001A/B's saturation [deg C]: the temperature their water boils at in 322E002's
        shell."""
        return tsat_c(self.p_lp_bara)

    def step(self, draws: SteamDraws, dt: float, trip_21_2: bool = False) -> SteamNetworkResult:
        """Advance the network one tick (module docstring, steps 1 to 6)."""
        p_hp, p_9, p_lp = self.p_hp_bara, self.p_9_bara, self.p_lp_bara
        strip = draws.strip_kgh / 3600.0
        raise_ = draws.raise_kgh / 3600.0
        users_9 = sum(draws.users_9_kgh.values()) / 3600.0
        users_lp = sum(draws.users_lp_kgh.values()) / 3600.0
        blow = BLOWDOWN_KGH / 3600.0
        leak_v, leak_l = draws.leak_vapour_kgh / 3600.0, draws.leak_liquid_kgh / 3600.0
        leak_b = draws.leak_boil_kgh / 3600.0

        # 1. 329D005: its drain, its supply, its vent, its water boiled by 902's superheat.
        op_502 = self.lic_329502.step(D005.level_pct(self.m_d005_kg), dt)
        m_502 = lv_329502_kgs(op_502, p_hp, p_9)
        op_204 = self.pic_329204.step(p_hp, trip_21_2, dt)
        m_902 = self._m_902(op_204, p_hp)
        op_601 = self.hv_329601.step(p_hp, trip_21_2, dt)
        m_601 = steam_valve_kgs(K_HV601, op_601, p_hp, P_ATM_VENT_BARA, HV601_P1_DES_BARA,
                                HV601_P2_DES_BARA)
        ds_5 = m_902 * superheat_water_ratio(H_902_KJKG, p_hp)
        f_5 = _cap(self.m_d005_kg, strip, ds_5 + m_502, dt)
        ds_5, m_502 = ds_5 * f_5, m_502 * f_5
        m_906 = FLASH9_FRACTION * m_502

        # 2. 329D009: the split range, its water boiled by 903's superheat (V1's anchor).
        op_205a, op_205b = self.pic_329205.step(p_9)
        m_903 = pv_329205a_kgs(op_205a, P_SUP_BARA, p_9)
        m_960 = pv_329205b_kgs(op_205b, p_9, p_lp)
        ds_9 = DS9_DES_KGS * (m_903 / M_903_DES_KGS)

        # 3. The LP header's trio; 963's superheat boils 322D001's water. 960 joins the header
        #    downstream of the drums, so its superheat boils none.
        op_207a, op_207b, op_207c = self.pic_329207.step(p_lp, dt)
        m_207a = self._m_207a(op_207a, p_lp)
        m_932 = self._m_932(op_207b, p_lp)
        m_963 = (steam_valve_kgs(K_963, op_207c, P_SUP_BARA, p_lp, P963_P1_DES_BARA,
                                 P963_P2_DES_BARA)
                 + steam_valve_kgs(K_HV602, self.hv_329602_pct, P_SUP_BARA, p_lp,
                                   P963_P1_DES_BARA, P963_P2_DES_BARA))

        def ds_lp_at(p, m_963_p):
            return m_963_p * superheat_water_ratio(H_963_KJKG, p)

        ds_lp = ds_lp_at(p_lp, m_963)

        # 4. The cascade's drain and the make-up at the starting pressures; 913's flash.
        op_503 = self.lic_329503.step(D009.level_pct(self.m_d009_kg), dt)
        m_503 = lv_329503_kgs(op_503, p_9, p_lp)
        op_504 = self.lic_329504.step(D001.level_pct(self.m_d001_kg), dt)
        m_916 = lv_329504_kgs(op_504, p_lp)
        f_9 = _cap(self.m_d009_kg, m_502 - m_906, ds_9 + m_503, dt)
        ds_9, m_503 = ds_9 * f_9, m_503 * f_9
        m_915 = m_503 * flash_fraction(p_9, p_lp)
        f_1 = _cap(self.m_d001_kg, m_503 - m_915 + m_916 + leak_l - min(leak_b, 0.0),
                   raise_ + ds_lp + blow + max(leak_b, 0.0), dt)
        raise_, ds_lp, blow = raise_ * f_1, ds_lp * f_1, blow * f_1
        leak_b = leak_b * f_1 if leak_b > 0.0 else leak_b

        # 5. The vapour nodes. 322D001A/B's steam space carries the LP header: the drums take the
        #    raising, 963, its boil-off and 915, and discharge 917, what the header's users and
        #    valves take less what 960 lets into the header.
        res_hp = m_902 + ds_5 - strip - m_601
        res_9 = m_903 + m_906 + ds_9 - users_9 - m_960
        m_917 = users_lp + m_207a + m_932 - m_960
        res_lp = raise_ + m_963 + ds_lp + m_915 - m_917 + leak_v + leak_b

        def res_hp_at(p):
            m = self._m_902(op_204, p)
            return (m + m * superheat_water_ratio(H_902_KJKG, p) * f_5 - strip
                    - steam_valve_kgs(K_HV601, op_601, p, P_ATM_VENT_BARA, HV601_P1_DES_BARA,
                                      HV601_P2_DES_BARA))

        def res_9_at(p):
            m = pv_329205a_kgs(op_205a, P_SUP_BARA, p)
            return (m + m_906 + DS9_DES_KGS * (m / M_903_DES_KGS) * f_9 - users_9
                    - pv_329205b_kgs(op_205b, p, p_lp))

        def res_lp_at(p):
            p9 = self.p_9_bara              # V1 steps the three in turn: 329D009's new pressure
            m_960_p = pv_329205b_kgs(op_205b, p9, p)
            m_963_p = (steam_valve_kgs(K_963, op_207c, P_SUP_BARA, p, P963_P1_DES_BARA,
                                       P963_P2_DES_BARA)
                       + steam_valve_kgs(K_HV602, self.hv_329602_pct, P_SUP_BARA, p,
                                         P963_P1_DES_BARA, P963_P2_DES_BARA))
            m_917_p = (users_lp
                       + self._m_207a(op_207a, p)
                       + self._m_932(op_207b, p)
                       - m_960_p)
            return (raise_ + m_963_p + ds_lp_at(p, m_963_p) * f_1
                    + m_503 * flash_fraction(p9, p) - m_917_p + leak_v + leak_b)

        relief = {}
        for tag, attr, res, fn, cap, sv, v_vap in (
                ("SV32951", "p_hp_bara", res_hp, res_hp_at, C_MP_KG_BAR, self.sv_329d005,
                 V_D005_VAP_M3),
                ("SV32952", "p_9_bara", res_9, res_9_at, C_9_KG_BAR, self.sv_329d009,
                 V_D009_VAP_M3),
                ("SV32978", "p_lp_bara", res_lp, res_lp_at, C_LP_KG_BAR, self.sv_322d001,
                 V_D001_VAP_M3)):
            p = getattr(self, attr)
            den = _implicit(p, res, fn, cap, dt)
            p_free = p + res * dt / den
            w = sv.vent_kgh(p, p_free, tsat_c(p) + 273.15, STEAM_MW, v_vap, dt)
            relief[tag] = w
            setattr(self, attr, max(0.0, p + (res - w / 3600.0) * dt / den))

        # 6. The drums' water.
        water = {"329D005": strip - ds_5 - m_502,
                 "329D009": m_502 - m_906 - ds_9 - m_503,
                 "322D001": m_503 - m_915 + m_916 - raise_ - ds_lp - blow + leak_l - leak_b}
        overflow = {}
        for tag, drum, attr in (("329D005", D005, "m_d005_kg"), ("329D009", D009, "m_d009_kg"),
                                ("322D001", D001, "m_d001_kg")):
            m = getattr(self, attr) + water[tag] * dt
            overflow[tag] = max(m - drum.full_kg, 0.0) / dt * 3600.0
            setattr(self, attr, min(m, drum.full_kg))
        # The leak's solids in 322D001A/B's water: in with the leak, out with the blowdown and the
        # overflow at the water's strength (B-82).
        if self.m_d001_solids_kg > 0.0 or draws.leak_solids_kgh > 0.0:
            strength = self.m_d001_solids_kg / max(self.m_d001_kg, DRUM_M_FLOOR_KG)
            out = (blow + overflow["322D001"] / 3600.0) * strength
            self.m_d001_solids_kg = max(
                self.m_d001_solids_kg + (draws.leak_solids_kgh / 3600.0 - out) * dt, 0.0)

        flows = {"902": m_902, "903": m_903, "904": m_502, "906": m_906, "913": m_503,
                 "915": m_915, "916": m_916, "917": m_917, "932": m_932, "959": blow,
                 "960": m_960,
                 "963": m_963, "HV-329601": m_601, "PV-329207A": m_207a, "strip": strip,
                 "raise": raise_, "ds_329D005": ds_5, "ds_329D009": ds_9, "ds_322D001": ds_lp,
                 "users_9": users_9, "users_lp": users_lp, "leak_vapour": leak_v,
                 "leak_liquid": leak_l, "leak_boil": leak_b}
        flows = {k: v * 3600.0 for k, v in flows.items()}
        flows["901"] = draws.c003_kgh + flows["902"] + flows["903"] + flows["963"]
        return SteamNetworkResult(
            p_hp_bara=self.p_hp_bara, p_9_bara=self.p_9_bara, p_lp_bara=self.p_lp_bara,
            p_lp_start_bara=p_lp, t_hp_c=tsat_c(self.p_hp_bara), t_9_c=tsat_c(self.p_9_bara),
            t_lp_c=tsat_c(self.p_lp_bara), flows_kgh=flows,
            strokes_pct={"PV-329204": op_204, "HV-329601": op_601, "PV-329205A": op_205a,
                         "PV-329205B": op_205b, "PV-329207A": op_207a, "PV-329207B": op_207b,
                         "PV-329207C": op_207c, "HV-329602": self.hv_329602_pct,
                         "LV-329502": op_502, "LV-329503": op_503, "LV-329504": op_504},
            levels_pct={"LIC-329502": D005.level_pct(self.m_d005_kg),
                        "LIC-329503": D009.level_pct(self.m_d009_kg),
                        "LIC-329504": D001.level_pct(self.m_d001_kg)},
            vapour_residual_kgh={"329D005": res_hp * 3600.0, "329D009": res_9 * 3600.0,
                                 "322D001": res_lp * 3600.0},
            water_residual_kgh={k: v * 3600.0 for k, v in water.items()},
            relief_kgh=relief, overflow_kgh=overflow,
            hv_329601_blocked=self.hv_329601.blocked,
            d001_solids_ppm=self.m_d001_solids_kg / max(self.m_d001_kg, DRUM_M_FLOOR_KG) * 1e6)


def v1_butterflies() -> dict:
    """The network's fields as V1 runs PV-329204, PV-329207A and PV-329207B — its anchored law and
    its seeds — for the equivalence harness: ``SteamNetwork(**v1_butterflies())``."""
    return {"vendor_butterflies": False, "pic_329204": v1_pic_329204(),
            "pic_329207": v1_pic_329207()}


__all__ = ["DP_PROBE_BAR", "pfd_basis_kgh", "SteamDraws", "SteamNetworkResult", "SteamNetwork",
           "v1_butterflies"]
