"""Transport properties for a packed absorber's transfer units — water and the inert carrier gas.

What this gives the plant model
-------------------------------
A packed bed's mass-transfer rate is set by how well its liquid wets the packing and how fast the
absorbed species crosses the gas film. Both are correlated on transport properties: the liquid's
viscosity and surface tension (Onda's wetted fraction), the gas's viscosity, and each solute's
diffusivity through the carrier gas (Onda's gas-film coefficient). The washes 322C001 runs are
dilute ammonia water and steam condensate, and its gas is three-quarters nitrogen, so water's
properties stand for the liquid's and nitrogen's for the gas's.

The equations
-------------
    mu_L    = 2.414e-5 . 10^(247.8 / (T - 140))                      [Vogel, Pa s]
    sigma   = 0.2358 . tau^1.256 . (1 - 0.625 tau),  tau = 1 - T/Tc  [IAPWS R1-76, N/m]
    mu_G    = 1.781e-5 . (300.55 + 111)/(T + 111) . (T/300.55)^1.5   [Sutherland, N2, Pa s]
    D_G     = 1e-7 T^1.75 sqrt(1/M_A + 1/M_B) / (P [atm] (v_A^(1/3) + v_B^(1/3))^2)
                                                    [Fuller, Schettler & Giddings 1966, m2/s]

Source: V1 ``backend/packed_absorber.py`` (``water_mu_pas``, ``water_sigma_nm``, ``gas_mu_pas``,
``diffusivity_m2s`` and the Fuller diffusion volumes). Ported verbatim.
"""

from __future__ import annotations

import math

from ureasim.thermo.domains import MW

__all__ = ["FULLER_VOLUMES", "water_mu_pas", "water_sigma_nm", "gas_mu_pas", "diffusivity_m2s"]

#: Fuller-Schettler-Giddings atomic diffusion volumes of the species that cross the gas film,
#: and of the carrier [cm3/mol].
FULLER_VOLUMES = {"NH3": 20.7, "CO2": 26.9, "N2": 18.5}

#: Water's critical temperature [K], IAPWS R1-76's reference.
_T_CRIT_K = 647.096

#: Floor on the reduced temperature distance from critical, so the surface tension stays real.
_TAU_FLOOR = 1e-9

#: One standard atmosphere [Pa], Fuller's pressure unit.
_ATM_PA = 101325.0


def water_mu_pas(t_k: float) -> float:
    """Viscosity of liquid water [Pa s], by the Vogel equation.

    Process utility
    ---------------
    The wash's viscosity enters the liquid Reynolds number of Onda's wetted fraction and the
    film holdup of the liquid residence: a colder wash wets less of the packing and trickles
    down more slowly.
    """
    return 2.414e-5 * 10.0 ** (247.8 / (t_k - 140.0))


def water_sigma_nm(t_k: float) -> float:
    """Surface tension of water [N/m], IAPWS R1-76.

    Process utility
    ---------------
    Against the packing's critical surface tension it decides how much of the packing the wash
    spreads over (Onda's wetted fraction).
    """
    tau = max(1.0 - t_k / _T_CRIT_K, _TAU_FLOOR)
    return 0.2358 * tau ** 1.256 * (1.0 - 0.625 * tau)


def gas_mu_pas(t_k: float) -> float:
    """Viscosity of the carrier gas [Pa s]: Sutherland's law for nitrogen, 75 mol % of PFD 797.

    Process utility
    ---------------
    The gas Reynolds and Schmidt numbers of Onda's gas-film coefficient.
    """
    return 1.781e-5 * (300.55 + 111.0) / (t_k + 111.0) * (t_k / 300.55) ** 1.5


def diffusivity_m2s(species: str, t_k: float, p_pa: float) -> float:
    """Binary diffusivity of ``species`` through nitrogen [m2/s], Fuller-Schettler-Giddings.

    Process utility
    ---------------
    How fast ammonia or carbon dioxide crosses the gas film to the wetted packing: a higher
    column pressure slows it in proportion, a hotter gas speeds it.
    """
    va, vb = FULLER_VOLUMES[species], FULLER_VOLUMES["N2"]
    root = math.sqrt(1.0 / MW[species] + 1.0 / MW["N2"])
    return 1.0e-7 * t_k ** 1.75 * root / ((p_pa / _ATM_PA) * (va ** (1 / 3) + vb ** (1 / 3)) ** 2)
