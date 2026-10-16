"""322C001's two packed beds — how much ammonia and carbon dioxide the LP absorber takes up.

What this models
----------------
The gas HV-322604 lets down climbs two packed beds counter-current to their washes:

    lower bed   1500 mm in the 922 mm part, washed by PFD 755 (322P002 / 322E006) and by the
                954 leaving the bed above with what it took up
    upper bed   1000 mm in the 576 mm part, washed by clean steam condensate, PFD 954

Each bed, each volatile species, is the counter-current gas-film balance on a straight
equilibrium line (Colburn):

    (y_out - y*_in) / (y_in - y*_in) = (1 - lam) / (exp(NTU (1 - lam)) - lam),   lam = m G / L

    NTU      = c_i . k_G a_w P Z / G_m                          Onda, Takeuchi & Okumoto (1968)
    a_w / a  = 1 - exp(-1.45 (sig_c/sig)^0.75 Re_L^0.1 Fr_L^-0.05 We_L^0.2)
    k_G      = 5.23 (a D_G / R T) Re_G^0.7 Sc_G^(1/3) (a d_p)^-2

**Lower bed.** y*_in is the NH3 or CO2 partial pressure over the liquid that washes it — 755 and
the upper bed's effluent mixed — at the live liquor temperature, and the slope m is dp/dx over
the LIVE sump liquor (`thermo.ammonia_backpressure`): a liquor that has loaded up or warmed up
takes less. A liquid gives up (desorbs) no more of a species than it brings into the bed.
**Upper bed.** 954 enters clean (y*_in = 0); NH3 loads it along its equilibrium line and the bed
warms by its own heat of absorption; CO2 is taken up only while there is NH3 in the wash to bind
it. **The vent** leaves the 954 wash saturated with water, y_w = a_w psat(T_top) / P.

The beds couple through the liquid: the lower bed sees the upper bed's effluent. A unit step
passes once and lags that uptake over the upper bed's liquid residence — the time the 954 takes to
trickle down — and ``passes`` > 1 relaxes the two to a steady state, as the calibration does.

The calibration
---------------
c_i is the one per-species number the sources do not supply (Onda quotes k_G to about +/-30 %).
It is solved at the design point so the design uptake is the PFD 204 -> 797 split exactly:
0.80 for NH3, 0.84 for CO2; and a_w, the vent's water activity, 0.88, against PFD 797's
2.28 mol % of water.

Source: V1 ``backend/packed_absorber.py`` (``area_m2``, ``wetted_fraction``, ``onda_ntu``,
``liquid_residence_s``, ``colburn``, ``solve``, ``calibrate``). Ported verbatim; the packing and
the beds are in `ureasim.data.unit_322c001`, the properties in `thermo.transport_properties` and
`thermo.ammonia_backpressure`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

from ureasim.core.stream import MW_COMP
from ureasim.core.units_of_measure import G_ACC, R_GAS_J
from ureasim.data.unit_322c001 import (
    BED_CP_GAS,
    BED_CP_LIQ,
    BED_LO_HEIGHT_M,
    BED_LO_ID_M,
    BED_RHO_LIQ_KGM3,
    BED_UP_HEIGHT_M,
    BED_UP_ID_M,
    PACKING_AREA_M2M3,
    PACKING_SIGMA_C_NM,
    PACKING_SIZE_M,
)
from ureasim.thermo import iapws
from ureasim.thermo.ammonia_backpressure import back_pressure, heat_of_absorption_j_mol
from ureasim.thermo.transport_properties import (
    diffusivity_m2s,
    gas_mu_pas,
    water_mu_pas,
    water_sigma_nm,
)

#: The species the beds transfer.
VOLATILE = ("NH3", "CO2")

#: The molar mass taken for a species outside the table [kg/kmol], V1's.
MW_UNKNOWN = 28.0

#: The longest liquid residence a bed is given [s], and the superficial liquid velocity below
#: which it is taken [m/s].
RESIDENCE_MAX_S = 3600.0
U_LIQ_FLOOR_MS = 1e-12

#: Numerical guards, V1's: no gas [kmol/h]; the absorption factor's unit pole; the exponent's
#: ceiling; the liquid in an absorption factor [kmol/h]; the gas in a mole fraction [kmol/h];
#: the upper bed's heat capacity [kW/K]; the 954 that counts as a wash [kg/h].
GAS_FLOOR_KMOLH = 1e-12
LAMBDA_POLE = 1.0e-9
EXP_CEILING = 700.0
LIQ_FLOOR_KMOLH = 1e-9
CAP_FLOOR_KWK = 1e-9
WASH_FLOOR_KGH = 1e-9

#: The upper bed's temperature rise: iterations and tolerance [K]; the relaxation's tolerance
#: [kmol/h] and passes.
DT_UP_ITERATIONS = 8
DT_UP_TOL_K = 1e-6
RELAX_TOL_KMOLH = 1e-12
CALIBRATION_PASSES = 200

#: The vent's water fraction ceiling [-].
Y_WATER_MAX = 0.9

#: The calibration's seed, its bracket on c_i, its bisection budget and its convergence, and
#: the sweeps over the two species, which couple weakly through the bed heat.
CAL_SEED = {"NH3": 1.0, "CO2": 1.0, "a_w": 0.88}
CAL_BRACKET = (1e-4, 1e3)
CAL_BISECTIONS = 200
CAL_REL_TOL = 1e-15
CAL_SWEEPS = 3


@dataclass(frozen=True)
class PackedBed:
    """A packed bed: its packed height and the column's inside diameter there [m]."""

    height_m: float
    id_m: float

    @property
    def area_m2(self) -> float:
        """The column's cross-section at the bed [m2]."""
        return math.pi * 0.25 * self.id_m ** 2


#: The lower bed, in the 922 mm part, and the upper, in the 576 mm part.
BED_LO = PackedBed(BED_LO_HEIGHT_M, BED_LO_ID_M)
BED_UP = PackedBed(BED_UP_HEIGHT_M, BED_UP_ID_M)


@dataclass(frozen=True)
class BedCalibration:
    """The per-species transfer factors, the vent's water activity, and the steady upper-bed
    uptake that seeds the unit's lag {NH3, CO2 [kmol/h], dT [K]}."""

    nh3: float
    co2: float
    a_w: float
    abs_up: dict = field(default_factory=dict)

    def factor(self, species: str) -> float:
        """c_i for ``species``."""
        return self.nh3 if species == "NH3" else self.co2


@dataclass(frozen=True)
class BedsResult:
    """What the two beds do to the gas on one pass."""

    #: Taken up and vented per species [kmol/h]; absorbed water < 0, the gas leaving wetter.
    absorbed_kmolh: dict
    vent_kmolh: dict
    #: The transfer units, ``lo_NH3`` ... ``up_CO2``; the lower bed's equilibrium gas fractions.
    ntu: dict
    y_star_lo: dict
    #: The upper bed's temperature rise [K], and its uptake as the lower bed will see it.
    dt_up_k: float
    abs_up: dict


def wetted_fraction(l_kgm2s: float, t_k: float) -> float:
    """Onda's wetted fraction of the packing surface [-].

    Process utility
    ---------------
    Only the wetted packing transfers: a starved wash wets little of the bed, so a 954 cut
    loses the upper bed's polish faster than its flow.
    """
    if l_kgm2s <= 0.0:
        return 0.0
    mu, sig = water_mu_pas(t_k), water_sigma_nm(t_k)
    re = l_kgm2s / (PACKING_AREA_M2M3 * mu)
    fr = l_kgm2s ** 2 * PACKING_AREA_M2M3 / (BED_RHO_LIQ_KGM3 ** 2 * G_ACC)
    we = l_kgm2s ** 2 / (BED_RHO_LIQ_KGM3 * sig * PACKING_AREA_M2M3)
    return 1.0 - math.exp(-1.45 * (PACKING_SIGMA_C_NM / sig) ** 0.75 * re ** 0.1 * fr ** -0.05
                          * we ** 0.2)


def onda_ntu(species: str, bed: PackedBed, m_liq_kgh: float, m_gas_kgh: float,
             n_gas_kmolh: float, t_k: float, p_pa: float) -> float:
    """A bed's gas-film transfer units for ``species``, k_G a_w P Z / G_m, before its c_i.

    Process utility
    ---------------
    How many times over the bed can bring the gas to equilibrium with its wash: more gas
    through the same packing, fewer units; a higher column pressure, more.
    """
    if m_gas_kgh <= 0.0 or n_gas_kmolh <= 0.0 or m_liq_kgh <= 0.0:
        return 0.0
    area = bed.area_m2
    l_flux = m_liq_kgh / 3600.0 / area
    v_flux = m_gas_kgh / 3600.0 / area
    gm = n_gas_kmolh * 1000.0 / 3600.0 / area                     # mol/(m2 s)
    rho_g = p_pa * (m_gas_kgh / n_gas_kmolh / 1000.0) / (R_GAS_J * t_k)
    mu_g = gas_mu_pas(t_k)
    d_g = diffusivity_m2s(species, t_k, p_pa)
    k_g = (5.23 * (PACKING_AREA_M2M3 * d_g / (R_GAS_J * t_k))
           * (v_flux / (PACKING_AREA_M2M3 * mu_g)) ** 0.7
           * (mu_g / (rho_g * d_g)) ** (1.0 / 3.0)
           * (PACKING_AREA_M2M3 * PACKING_SIZE_M) ** -2.0)            # mol/(m2 s Pa)
    return k_g * PACKING_AREA_M2M3 * wetted_fraction(l_flux, t_k) * p_pa * bed.height_m / gm


def liquid_residence_s(bed: PackedBed, m_liq_kgh: float, t_k: float) -> float:
    """The time the liquid takes to cross a bed [s]: operating holdup over volumetric flow.

    Process utility
    ---------------
    How late the lower bed sees what the upper bed's wash took up — the lag the unit puts on the
    beds' coupling, about 24 s for the design 954.

    Equation
    --------
        h_L = (12 mu_L a^2 u_L / (rho_L g))^(1/3)      [laminar film, the whole surface wetted]
        t   = Z h_L / u_L
    """
    area = bed.area_m2
    u_l = m_liq_kgh / BED_RHO_LIQ_KGM3 / 3600.0 / area           # m/s superficial
    if u_l <= U_LIQ_FLOOR_MS:
        return RESIDENCE_MAX_S
    h_l = (12.0 * water_mu_pas(t_k) * PACKING_AREA_M2M3 ** 2 * u_l
           / (BED_RHO_LIQ_KGM3 * G_ACC)) ** (1.0 / 3.0)
    return min(bed.height_m * h_l / u_l, RESIDENCE_MAX_S)


def colburn(y_in: float, y_star: float, ntu: float, lam: float) -> float:
    """The counter-current gas outlet on a straight equilibrium line through ``y_star``.

    Process utility
    ---------------
    One bed's answer to "how close to its wash's equilibrium does the gas leave?" — the whole
    of an absorber bed in closed form.
    """
    if ntu <= 0.0:
        return y_in
    if abs(1.0 - lam) < LAMBDA_POLE:
        f = 1.0 / (1.0 + ntu)
    else:
        f = (1.0 - lam) / (math.exp(min(ntu * (1.0 - lam), EXP_CEILING)) - lam)
    return y_star + (y_in - y_star) * f


def solve(gas_kmolh: dict, t_liq_c: float, t_cpl_c: float, p_bara: float, m_755_kgh: float,
          w_755: dict, m_cpl_kgh: float, w_liquor: dict, cal: BedCalibration,
          abs_up: dict | None = None, passes: int = 1) -> BedsResult:
    """The gas up both beds: what they take up and what they vent.

    Process utility
    ---------------
    The absorber's uptake, its ammonia slip to atmosphere and the water its vent carries — the
    numbers the sump's mass, species and heat balances and the column's pressure are built on.
    ``abs_up`` is the upper bed's uptake {NH3, CO2, dT} as the lower bed sees it; the result
    carries the new one.
    """
    p_pa = p_bara * 1.0e5
    n_in = {k: max(v, 0.0) for k, v in gas_kmolh.items()}
    g_in = sum(n_in.values())
    if g_in <= GAS_FLOOR_KMOLH:
        # No gas: the 954 leaves the upper bed as clean as it came, so the uptake the unit lags
        # toward is zero (a shut HV-322604 must not leave the lower bed washed by old ammonia).
        return BedsResult(absorbed_kmolh={k: 0.0 for k in n_in}, vent_kmolh=dict(n_in), ntu={},
                          y_star_lo={"NH3": 0.0, "CO2": 0.0}, dt_up_k=0.0,
                          abs_up={"NH3": 0.0, "CO2": 0.0, "dT": 0.0})
    m_gas = sum(n_in[k] * MW_COMP.get(k, MW_UNKNOWN) for k in n_in)
    ntus, y_star_lo = {}, {"NH3": 0.0, "CO2": 0.0}

    # The lower bed is washed by 755 AND by the 954 leaving the upper bed with what it took up,
    # so its back-pressure depends on the upper bed's uptake.
    t_lo_k, t_cpl_k = t_liq_c + 273.15, t_cpl_c + 273.15
    m_lo = m_755_kgh + m_cpl_kgh
    l_lo, l_up = m_lo / MW_COMP["H2O"], m_cpl_kgh / MW_COMP["H2O"]
    _, _, dpdx_liq_n, dpdx_liq_c = back_pressure(w_liquor, t_liq_c)
    dt_up = abs_up.get("dT", 0.0) if abs_up else 0.0
    abs_up = {"NH3": abs_up["NH3"], "CO2": abs_up["CO2"]} if abs_up else {"NH3": 0.0, "CO2": 0.0}
    new_up = dict(abs_up)
    n_top = {}
    for _outer in range(max(int(passes), 1)):
        m_up_nh3, m_up_co2 = abs_up["NH3"] * MW_COMP["NH3"], abs_up["CO2"] * MW_COMP["CO2"]
        m_mix = m_755_kgh + m_cpl_kgh + m_up_nh3 + m_up_co2
        if m_mix > WASH_FLOOR_KGH:
            w_lo_in = {k: m_755_kgh * w_755.get(k, 0.0) / m_mix
                       for k in ("NH3", "CO2", "H2O", "Urea")}
            w_lo_in["NH3"] += m_up_nh3 / m_mix
            w_lo_in["CO2"] += m_up_co2 / m_mix
            w_lo_in["H2O"] += m_cpl_kgh / m_mix
        else:
            w_lo_in = dict(w_755)
        p_nlo, p_clo, _, _ = back_pressure(w_lo_in, t_liq_c)

        # ----- the lower bed ------------------------------------------------------------------
        n_mid = dict(n_in)
        for sp in VOLATILE:
            ntu = cal.factor(sp) * onda_ntu(sp, BED_LO, m_lo, m_gas, g_in, t_lo_k, p_pa)
            y_star = min((p_nlo if sp == "NH3" else p_clo) / p_pa, 1.0)
            slope = dpdx_liq_n if sp == "NH3" else dpdx_liq_c
            lam = (slope / p_pa) * g_in / max(l_lo, LIQ_FLOOR_KMOLH)
            y_in = n_in.get(sp, 0.0) / g_in
            # A liquid can give up no more of a species than it brings into the bed.
            liq_in = (m_755_kgh * w_755.get(sp, 0.0)
                      + (m_up_nh3 if sp == "NH3" else m_up_co2)) / MW_COMP[sp]
            n_out = n_in.get(sp, 0.0) - (y_in - colburn(y_in, y_star, ntu, lam)) * g_in
            n_mid[sp] = min(max(n_out, 0.0), n_in.get(sp, 0.0) + liq_in)
            ntus["lo_" + sp] = ntu
            y_star_lo[sp] = y_star
        g_mid = sum(n_mid.values())
        m_mid = sum(n_mid[k] * MW_COMP.get(k, MW_UNKNOWN) for k in n_mid)

        # ----- the upper bed: 954 enters clean and warms by what it takes up ---------------
        # The equilibrium line's slope is taken over the bed's effluent, so CO2 is taken up only
        # while there is NH3 in the wash to bind it.
        if m_cpl_kgh > WASH_FLOOR_KGH:
            w_up_out = {"H2O": m_cpl_kgh, "NH3": abs_up["NH3"] * MW_COMP["NH3"],
                        "CO2": abs_up["CO2"] * MW_COMP["CO2"]}
            m_up_out = sum(w_up_out.values())
            w_up_out = {k: v / m_up_out for k, v in w_up_out.items()}
        else:
            w_up_out = {"H2O": 1.0}
        n_top = dict(n_mid)
        for _inner in range(DT_UP_ITERATIONS):
            t_up_k = t_cpl_k + 0.5 * dt_up
            _, _, s_n, s_c = back_pressure(w_up_out, t_up_k - 273.15)
            n_top = dict(n_mid)
            for sp in VOLATILE:
                ntu = cal.factor(sp) * onda_ntu(sp, BED_UP, m_cpl_kgh, m_mid, g_mid, t_up_k, p_pa)
                lam = ((s_n if sp == "NH3" else s_c) / p_pa) * g_mid / max(l_up, LIQ_FLOOR_KMOLH)
                y_in = n_mid.get(sp, 0.0) / max(g_mid, GAS_FLOOR_KMOLH)
                n_top[sp] = max(n_mid.get(sp, 0.0) - (y_in - colburn(y_in, 0.0, ntu, lam)) * g_mid,
                                0.0)
                ntus["up_" + sp] = ntu
            dh_n, dh_c = heat_of_absorption_j_mol(w_up_out, t_up_k - 273.15)
            q_kw = ((n_mid["NH3"] - n_top["NH3"]) * dh_n
                    + (n_mid["CO2"] - n_top["CO2"]) * dh_c) * 1000.0 / 3.6e6
            cap = (m_cpl_kgh * BED_CP_LIQ + m_mid * BED_CP_GAS) / 3600.0
            dt_new = q_kw / cap if cap > CAP_FLOOR_KWK else 0.0
            done = abs(dt_new - dt_up) < DT_UP_TOL_K
            dt_up = dt_new
            if done:
                break
        new_up = {sp: n_mid[sp] - n_top[sp] for sp in VOLATILE}
        if passes <= 1 or max(abs(new_up[sp] - abs_up[sp]) for sp in VOLATILE) < RELAX_TOL_KMOLH:
            break
        abs_up = {sp: 0.5 * (abs_up[sp] + new_up[sp]) for sp in VOLATILE}   # relaxed steady state

    # ----- the vent's water: saturated at the top of the 954 wash ----------------------------
    y_w = min(cal.a_w * iapws.psat_bara(t_cpl_c) / p_bara, Y_WATER_MAX)
    dry = sum(v for k, v in n_top.items() if k != "H2O")
    n_top["H2O"] = dry * y_w / (1.0 - y_w)
    keys = list(n_in) + [k for k in n_top if k not in n_in]
    absorbed = {k: n_in.get(k, 0.0) - n_top.get(k, 0.0) for k in keys}
    return BedsResult(absorbed_kmolh=absorbed, vent_kmolh=n_top, ntu=ntus, y_star_lo=y_star_lo,
                      dt_up_k=dt_up,
                      abs_up={"NH3": new_up["NH3"], "CO2": new_up["CO2"], "dT": dt_up})


def calibrate(gas_kmolh: dict, t_liq_c: float, t_cpl_c: float, p_bara: float, m_755_kgh: float,
              w_755: dict, m_cpl_kgh: float, w_liquor: dict,
              target_abs_kmolh: dict) -> BedCalibration:
    """c_NH3, c_CO2 and the vent's water activity that make the design uptake
    ``target_abs_kmolh`` {NH3, CO2, H2O}.

    Process utility
    ---------------
    Pins the one per-species number the sources leave open, so the design point is the PFD's
    204 -> 797 split by construction and the beds' rate law, not a fixed fraction, carries every
    departure from it (V1's boot pin).
    """
    cal = BedCalibration(CAL_SEED["NH3"], CAL_SEED["CO2"], CAL_SEED["a_w"])
    fields = {"NH3": "nh3", "CO2": "co2"}

    def absorbed(c: BedCalibration) -> dict:
        return solve(gas_kmolh, t_liq_c, t_cpl_c, p_bara, m_755_kgh, w_755, m_cpl_kgh, w_liquor,
                     c, passes=CALIBRATION_PASSES).absorbed_kmolh

    for _ in range(CAL_SWEEPS):
        for sp in VOLATILE:
            lo, hi = CAL_BRACKET
            for _ in range(CAL_BISECTIONS):
                mid = math.sqrt(lo * hi)
                if absorbed(replace(cal, **{fields[sp]: mid}))[sp] < target_abs_kmolh[sp]:
                    lo = mid
                else:
                    hi = mid
                if hi / lo - 1.0 < CAL_REL_TOL:
                    break
            cal = replace(cal, **{fields[sp]: math.sqrt(lo * hi)})
    base = solve(gas_kmolh, t_liq_c, t_cpl_c, p_bara, m_755_kgh, w_755, m_cpl_kgh, w_liquor, cal,
                 passes=CALIBRATION_PASSES)
    dry = sum(v for k, v in base.vent_kmolh.items() if k != "H2O")
    vent_w = gas_kmolh.get("H2O", 0.0) - target_abs_kmolh["H2O"]
    a_w = (vent_w / (dry + vent_w)) * p_bara / iapws.psat_bara(t_cpl_c)
    # The steady bed coupling, to seed the unit's lag.
    return replace(cal, a_w=a_w, abs_up=dict(base.abs_up))


__all__ = [
    "VOLATILE", "MW_UNKNOWN", "PackedBed", "BED_LO", "BED_UP", "BedCalibration", "BedsResult",
    "wetted_fraction", "onda_ntu", "liquid_residence_s", "colburn", "solve", "calibrate",
]
