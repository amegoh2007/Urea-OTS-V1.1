"""Constants V1's console packet publishes or evaluates its indications with.

What these are
--------------
A handful of V1's published indications are not a unit's output but a display relation in the
packet itself: TT-321002's stratification below TT-321001, PI-321003's affinity-law header
pressure, the discharge header's idle reading. Each constant below is one of those, quoted from
V1's packet with V1's own comment. None of them feeds the plant.

Source
------
V1 ``backend/main.py``, ``step_sim``'s return statement (10445-11320) and the lines it names; no
reference document carries them (``CLAUDE.md`` §4 rule 3).
"""

from __future__ import annotations

from ureasim.data.unit_321 import P_SYN_DOWN_BAR
from ureasim.data.unit_323c005 import (
    PFD_341_MOL_PCT,
    PFD_702_MOL_PCT,
    PFD_703_MOL_PCT,
    PFD_708_MOL_PCT,
)

__all__ = [
    "TT_321002_STRAT_K", "LSL_321501_FRAC", "PI_321003_DES_BARG", "PI_DISCH_IDLE_BARG",
    "PI_DISCH_DES_BARG", "RHO_755_KGM3", "REACT_OVERFLOW_RHO", "REACT_OFFGAS_RHO",
    "STREAM_PCT", "STREAM_STATES", "CW_SUPPLY_P_BARA", "CW_RETURN_P_BARA", "CW_MAIN",
]

# ----- unit 321 -----------------------------------------------------------------------------

#: TT-321002, 321D003's top-right thermowell, reads below TT-321001 by this much times the
#: tank's empty fraction [K]: a level-dependent stratification of the vapour space ("F6:
#: TT-321002 de-aliased"). Source: V1 `main.py` 10471, ``s.tank_T_C - 0.8 * (1 - level)``.
TT_321002_STRAT_K = 0.8

#: LSL-321501, 321D003's low-level switch, active below this fraction of the tank [-].
#: Source: V1 `main.py` 10472.
LSL_321501_FRAC = 0.15

#: PI-321003, the feed header's pressure at design [bar g], drooping with the pumps' affinity-law
#: head (``phi_fwd``, 1 at design). Source: V1 `main.py` 10475, "F6: PI-321003 feed-header P
#: de-pinned".
PI_321003_DES_BARG = 7.3

#: The 321P002 discharge header with both machines stopped [bar g]. Source: V1 `main.py` 10178,
#: 10502.
PI_DISCH_IDLE_BARG = 7.5

#: The discharge header at design [bar g]: the 165 bar a downstream synthesis pressure, made gauge
#: by V1 with a bare 1.0 bar ("164.0 at design"). Source: V1 `main.py` 10178.
PI_DISCH_DES_BARG = P_SYN_DOWN_BAR - 1.0

# ----- unit 328 -----------------------------------------------------------------------------

#: PFD 755's effective density at 40 C [kg/m3]: FT-322402 reads the 755 draw in m3/h on it,
#: 31 478 / 1005 = 31.3, the PFD's own figure. Source: V1 `main.py` A328_M755_RHO, "Combined_1750
#: tbl, col 755"; `References/Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md`, stream 755.
RHO_755_KGM3 = 1005.0

# ----- the stream registry (the stream inspector's ``STREAMS``) ----------------------------

#: 322R001's overflow, the urea solution [kg/m3], and its off-gas [kg/m3], the densities V1's
#: registry publishes the two streams' volume on. Source: V1 `main.py` REACT_OVERFLOW_RHO (4667),
#: REACT_OFFGAS_RHO (4676).
REACT_OVERFLOW_RHO = 990.0
REACT_OFFGAS_RHO = 113.30

#: The PFD rows V1's registry builds its numbered streams on, per cent: the vapour rows on a mole
#: basis, the liquid rows on a mass basis (V1's ``PFD_324_MASS_PCT``, "its VAPOUR rows are the
#: PFD's mole per cent"). Rows another data module already carries are taken from it. Source:
#: V1 `main.py` 3856-3884; `References/Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md`.
STREAM_PCT = {
    "341": PFD_341_MOL_PCT,
    "343": {"CO2": 3.71, "H2O": 90.24, "NH3": 5.23, "Urea": 0.82},
    "702": PFD_702_MOL_PCT,
    "703": PFD_703_MOL_PCT,
    "705": {"CO2": 0.82, "H2O": 96.77, "N2": 0.07, "NH3": 2.07, "O2": 0.02, "Urea": 0.25},
    "708": PFD_708_MOL_PCT,
    "709": {"CO2": 3.54, "H2O": 87.58, "N2": 0.33, "NH3": 7.48, "O2": 0.09, "Urea": 0.98},
    "714": {"CO2": 3.88, "H2O": 87.98, "N2": 0.61, "NH3": 7.37, "O2": 0.16},
    "717": {"CO2": 2.22, "H2O": 89.93, "N2": 5.05, "NH3": 1.49, "O2": 1.34},
    "719": {"CO2": 3.50, "H2O": 91.75, "NH3": 4.08, "Urea": 0.66},
    "720": {"CO2": 3.92, "H2O": 88.73, "NH3": 3.68, "Urea": 3.68},
    "721": {"CO2": 8.54, "H2O": 84.87, "NH3": 6.59},
    "744": {"CO2": 0.11, "H2O": 98.50, "NH3": 0.63, "Urea": 0.76},
    "755": {"CO2": 3.81, "H2O": 91.13, "NH3": 4.17, "Urea": 0.89},
    "756": {"CO2": 3.79, "H2O": 91.18, "NH3": 4.20, "Urea": 0.84},
    "759": {"CO2": 2.27, "H2O": 96.31, "NH3": 1.42},
    "783": {"N2": 79.06, "O2": 20.94},
    "784": {"N2": 79.06, "O2": 20.94},
    "797": {"CH4": 6.47, "CO2": 0.05, "H2": 3.43, "H2O": 2.28, "N2": 75.15, "NH3": 0.18,
            "O2": 12.44},
}

#: Each numbered stream's registry state: temperature [deg C], pressure [bar a] and density
#: [kg/m3] or None, V1's literals (the PFD's operating conditions, rounded as V1 wrote them).
#: Source: V1 `main.py` 10247-10316.
STREAM_STATES = {
    "341": (43.0, 1.0, None), "343": (56.0, 1.0, 992.2), "702": (45.0, 1.0, None),
    "703": (116.0, 0.3, None), "705": (130.0, 0.3, None), "706": (None, 0.3, None),
    "708": (121.0, 1.0, None), "709": (140.0, 0.1, None), "712": (None, 0.1, None),
    "714": (104.0, 0.3, None), "715": (None, 0.3, None), "717": (120.0, 1.0, None),
    "719": (45.0, 0.3, 999.1), "720": (40.0, 0.1, 1014.0), "721": (41.0, 0.3, 1036.0),
    "722": (None, 1.0, None), "744": (44.0, 1.0, 1002.0), "755": (40.0, 3.9, 1005.0),
    "756": (43.0, 3.9, 1003.0), "759": (55.0, 1.0, 989.1), "783": (32.0, 1.0, None),
    "784": (32.0, 1.0, None), "797": (46.0, 3.9, None), "924": (146.0, 4.1, None),
    "927": (146.0, 4.1, None), "929": (146.0, 4.1, None), "954": (46.0, 12.0, 990.32),
}

#: The vacuum condensers' cooling-water supply and return pressures [bar a], V1's registry
#: literals. Source: V1 `main.py` 10322-10327.
CW_SUPPLY_P_BARA = 3.6
CW_RETURN_P_BARA = 2.2

#: The cooling-water mains, PFD 1001 and 1051: flow [kg/h], temperature [deg C], pressure [bar a].
#: Source: V1 `main.py` 10328-10331, the PFD's cooling-water block.
CW_MAIN = {"1001": (4_847_000.0, 30.0, 4.7), "1051": (4_865_000.0, 39.0, 2.2)}
