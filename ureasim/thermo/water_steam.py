"""Water and steam in a drum — the saturated relations the steam network balances on.

What this models
----------------
No equipment: the five water-steam relations every drum of unit 329 (329D005, 329D009,
322D001A/B) and every let-down into one is balanced on, on the IAPWS-IF97 line of
`ureasim.thermo.iapws`:

  * the saturated condensate's density at a drum's pressure, held at the triple point below it;
  * the saturated vapour's density, and a vapour space's capacitance, the mass it gains per bar:

        C = V_vap . d(rho_g,sat)/dP                          [kg/bar, central difference]

  * the fraction of a saturated condensate that flashes when it is let down to a lower drum:

        x = (h_f(P_up) - h_f(P_down)) / (h_g(P_down) - h_f(P_down))

  * the water a superheated steam evaporates when it reaches saturation in a drum:

        m_w / m_s = (h_in - h_g(P)) / (h_g(P) - h_f(P))

    the steam's superheat paid as the drum water's latent heat (handoff B-70, decided
    2026-10-02: the water is the drum's, and its level balance loses it).

Source
------
V1 ``backend/steam_system.py``: ``_rho_drum_liquid``, ``_rho_vapour_sat``,
``_header_capacitance`` and ``P_TRIPLE_BARA``, ported verbatim. The flash and the desuperheat
are the PFD's own closures on IAPWS-IF97 (PFD-21's steam block: 904 -> 905 + 906, 913 -> 914 +
915, 903's 275 kg/h of "saturation water"), new with the steam network's port (session 37).
"""

from __future__ import annotations

from ureasim.thermo.iapws import (
    h_liquid_sat_kjkg,
    h_vapour_sat_kjkg,
    rho_liquid_sat_kgm3,
    tsat_c,
    v_vapour_sat_m3kg,
)

#: Water's triple point [bar a]: IF97's saturation line starts here. Source: V1
#: `steam_system.py` P_TRIPLE_BARA.
P_TRIPLE_BARA = 0.00611657

#: The half-width of the central difference a capacitance is taken over [bar]. Source: V1
#: `steam_system.py` ``_header_capacitance``'s default.
CAPACITANCE_DP_BAR = 0.5


def rho_drum_liquid_kgm3(p_bara: float) -> float:
    """Saturated condensate density at a drum pressure [kg/m3], held at the triple point below it.

    Process utility
    ---------------
    The density a level valve passes a drum's condensate at. A tripped plant can pull a header
    under 6.1 mbar a, where there is no saturated liquid for IF97 to describe; the drum's water
    is then subcooled at about 1000 kg/m3, which the triple-point value (999.8) is.
    """
    return rho_liquid_sat_kgm3(tsat_c(max(p_bara, P_TRIPLE_BARA)))


def rho_vapour_sat_kgm3(p_bara: float) -> float:
    """Saturated-steam density at a header pressure [kg/m3], IAPWS-IF97."""
    return 1.0 / v_vapour_sat_m3kg(tsat_c(p_bara))


def vapour_capacitance_kg_bar(v_vapour_m3: float, p_bara: float,
                              dp: float = CAPACITANCE_DP_BAR) -> float:
    """What a saturated vapour space gains per bar it rises [kg/bar].

    Process utility
    ---------------
    How stiff a header is: the drum's steam space, not a fitted lumping factor, decides how far
    a mismatch of steam in and out moves its pressure in a tick.

    Equation in the module docstring.
    """
    return v_vapour_m3 * (rho_vapour_sat_kgm3(p_bara + dp)
                          - rho_vapour_sat_kgm3(p_bara - dp)) / (2.0 * dp)


def _floor(p_bara: float) -> float:
    """A pressure held at the triple point, below which IF97 has no saturation line."""
    return max(p_bara, P_TRIPLE_BARA)


def h_vapour_sat_at_kjkg(p_bara: float) -> float:
    """Saturated steam's enthalpy at a drum's pressure [kJ/kg], held at the triple point.

    Process utility
    ---------------
    What 329D009's vapour carries into the LP header through PV-329205B, whose superheat there
    boils 322D001's water.
    """
    return h_vapour_sat_kjkg(tsat_c(_floor(p_bara)))


def flash_fraction(p_up_bara: float, p_down_bara: float) -> float:
    """The fraction of a saturated condensate that flashes, let down from one drum to another [-].

    Process utility
    ---------------
    The steam LV-329503 makes out of 329D009's condensate in 322D001 (PFD 915): the lower drum's
    pressure sets how much of the hotter water boils on arrival, and the rest joins its water.
    Zero if the downstream drum is no lower. Equation in the module docstring.
    """
    p_up, p_down = _floor(p_up_bara), _floor(p_down_bara)
    if p_down >= p_up:
        return 0.0
    t_dn = tsat_c(p_down)
    h_f_dn = h_liquid_sat_kjkg(t_dn)
    return max((h_liquid_sat_kjkg(tsat_c(p_up)) - h_f_dn)
               / (h_vapour_sat_kjkg(t_dn) - h_f_dn), 0.0)


def superheat_water_ratio(h_in_kjkg: float, p_bara: float) -> float:
    """The drum water a superheated steam evaporates per kilogram, reaching saturation [-].

    Process utility
    ---------------
    902 enters 329D005 at 328 C, 963 and 960 enter 322D001 superheated: each steam's superheat
    boils the drum's own water, which the drum's level then loses and its vapour gains (handoff
    B-70). Zero for a steam at or below saturation. Equation in the module docstring.
    """
    t = tsat_c(_floor(p_bara))
    h_g = h_vapour_sat_kjkg(t)
    return max((h_in_kjkg - h_g) / (h_g - h_liquid_sat_kjkg(t)), 0.0)


__all__ = [
    "P_TRIPLE_BARA", "CAPACITANCE_DP_BAR", "rho_drum_liquid_kgm3", "rho_vapour_sat_kgm3",
    "vapour_capacitance_kg_bar", "h_vapour_sat_at_kjkg", "flash_fraction",
    "superheat_water_ratio",
]
