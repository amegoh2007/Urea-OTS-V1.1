"""The product-line routes — the physical runs of pipe between the 323/324 vessels.

What this is
------------
Five named connections, each with the design flow it carries and the transit time that
follows from its geometry. `core.transport` moves packets down them; this module says what
they are.

Why these five and not others
-----------------------------
They are the main product train, where the fluid is a concentrating urea liquor and the
dead time is long enough to matter:

    322E001 -> 323C003 -> 323F004 -> 323F010 -> 323D002 -> 324E001

Every other tie in the plant is either a vapour line (transit time far below the
integration step, so modelling it would add state without adding behaviour) or a nozzle-to-
nozzle connection between adjacent vessels.

Dead time is DERIVED, never fitted
----------------------------------
    td = rho . V_line / m_dot,      V_line = sum_i  pi/4 . D_i^2 . L_i

so it rises as the plant slows and falls as it speeds up — the behaviour a trainee must see
after cutting a feed. A fixed lag cannot do this: at 50 % load the real transit time
doubles.

Provenance of each input, stated separately because they are not equally strong
-------------------------------------------------------------------------------
* **Geometry — the as-built isometrics** (decided by the process engineer 2026-10-07, handoff
  A-11: "A physics-based simulation cannot rely on layout estimates when the actual plant
  geometry is available"). Uhde's isometric index for units 323 / 324, UD-RL-323-AB-0001 /
  -0002, maps each line to its drawing, UD-RL-100-MB-xxxx (the vendor archive, scanned, read
  from the page images). Each drawing's bill of material lists the straight pipe of each size on
  the sheet, as built, to 0.1 m, and its elbows; each route below is that pipe on the flowing
  path plus the elbows' centreline arcs, each size at its own bore. Not counted: the valve
  bodies (LV-322501, LV-323501, LV-323505, FV-324401), the reducers, tees, flanges, strainers and
  the pump casing, whose volumes no drawing gives — so each volume is a lower bound by a few per
  cent — and the dead legs (instrument and drain branches, the standby pump's legs). V1 took one
  bore, DN 200 at 187.1 mm, and lengths of 25, 15, 15, 30 and 40 m, plant-layout estimates.
* **Design carrier flow** — PFD, through the design chain in `ureasim.data.design_point`.
* **Density** — PFD stream rows at each stage's own temperature and composition (V1's).

Downstream of a letdown the line runs two-phase (handoff B-81, decided 2026-10-09)
----------------------------------------------------------------------------------
LV-322501, LV-323501 and LV-323505 let the liquor down across its bubble point; it flashes at the
valve's outlet and the rest of the line carries the flash gas with the liquid. The line's
inventory is its liquid-full run upstream of the valve at the liquor's density plus its run
downstream at the homogeneous two-phase density of the flash at the outlet:

    td    = (rho_l . V_up + rho_m . V_down) / m_dot
    rho_m = 1 / ( x / rho_g + (1 - x) / rho_l )             [homogeneous, no slip]

x and rho_g are the design flash at each valve's outlet: PFD 301 for LV-322501 (17.2 t/h at
3.39 kg/m3), PFD 701 for LV-323501 (4.4 t/h at 0.68), and for LV-323505, whose flash the PFD does
not separate from 323E010's boil-up, PFD 319's sensible heat above its bubble point at 323F010's
pressure, at PFD 790's density. Where each valve sits on its line is read from the isometrics.
V1's lines are liquid plugs end to end.

Source: V1 `backend/main.py`, "INTER-VESSEL PROCESS TRANSPORT" (the law and the densities); the
isometrics named at each route (the geometry). As-Built §LXII.3.
"""

from __future__ import annotations

import math

from ureasim.core.transport import (
    ConsequenceRoute,
    packet_transport_time_s,
    pipe_volume_from_mm,
)
from ureasim.data.design_point import (
    R323_D002_RHO,
    R323_FEED_DES_KGH,
    R323_M314_DES,
    R323_M317_DES,
    R323_M319_DES,
    R323_PHI_V701,
    R324_FEED_DES,
)
from ureasim.data.unit_323 import EVAP_LAMBDA_KJKG, F010_P_BARA, W_S319
from ureasim.thermo.empirical import urea_soln_cp
from ureasim.thermo.urea_liquor import design_bubble_t

__all__ = ["ID_DN400_MM", "ID_DN200_MM", "ID_DN150_MM", "ID_HP160_MM", "ID_HP120_MM",
           "LR_ELBOW_RADIUS_MM", "elbow_arc_m", "ROUTE_SEGMENTS", "route_volume_m3",
           "TWO_PHASE_SEGMENTS", "two_phase_volume_m3", "homogeneous_density",
           "M301_DES_KGH", "RHO_301_KGM3", "RHO_701_KGM3", "RHO_790_KGM3", "LETDOWN_FLASH",
           "PROCESS_ROUTES", "route"]

# ======================================================================================
# The pipe, as the bills of material give it: outside diameter less twice the wall [mm]
# ======================================================================================

#: DIN 2463 stainless pipe, 406.4 x 5.6 (DN 400), 219.1 x 4.5 (DN 200) and 168.3 x 4.0 (DN 150).
ID_DN400_MM = 406.4 - 2.0 * 5.6
ID_DN200_MM = 219.1 - 2.0 * 4.5
ID_DN150_MM = 168.3 - 2.0 * 4.0

#: DIN 2462 high-pressure pipe, 219.1 x 16.0 ("160") and 168.3 x 12.5 ("120") — the 322E001
#: bottoms line, the 187.1 mm V1 took for the whole train.
ID_HP160_MM = 219.1 - 2.0 * 16.0
ID_HP120_MM = 168.3 - 2.0 * 12.5

#: Long-radius elbows, ASME B16.9 (the bills of material: "ELBOW, LR, ANSI B 16.9"): centreline
#: radius 1.5 times the nominal pipe size [mm], by DN.
LR_ELBOW_RADIUS_MM = {400: 1.5 * 16 * 25.4, 200: 1.5 * 8 * 25.4, 150: 1.5 * 6 * 25.4}


def elbow_arc_m(dn: int, degrees: float, count: int = 1) -> float:
    """Centreline length of ``count`` long-radius elbows of ``degrees`` on DN ``dn`` [m].

    Process utility
    ---------------
    An elbow holds liquor as a pipe does; its centreline arc is the length it adds to the run.

        L = count . pi . R . theta / 180,     R = 1.5 . NPS
    """
    return count * math.pi * LR_ELBOW_RADIUS_MM[dn] * degrees / 180.0 / 1000.0


#: Each route's flowing path as (bore [mm], length [m]) segments.
ROUTE_SEGMENTS: dict[str, tuple[tuple[float, float], ...]] = {
    # 200-US1-322302-EK19L (UD-RL-100-MB-0014, two sheets, as built): 322E001/N2 through
    # LV-322501 to 323C003/N1. High-pressure pipe, its bends formed in the pipe: 120 3.4 m from
    # the stripper to LV-322501 (sheet 1, the valve item 25), 160 30.3 m from the valve on.
    "322E001_TO_323C003": ((ID_HP120_MM, 3.4), (ID_HP160_MM, 30.3)),
    # 400-US14-323266-EG07D (MB-0148): 323C003/N5 down to LV-323501, DN 400 1.4 m, one 90 and
    # one 45 degree elbow; then 200-US4-323252-EC07DB (MB-0138) to 323F004/N1: DN 200 8.8 m and
    # four 90 degree elbows, DN 400 1.0 m — downstream of the valve.
    "323C003_TO_323F004": ((ID_DN400_MM, 1.4 + elbow_arc_m(400, 90) + elbow_arc_m(400, 45)),
                           (ID_DN400_MM, 1.0),
                           (ID_DN200_MM, 8.8 + elbow_arc_m(200, 90, 4))),
    # 150-US4-323253-EC07DB (MB-0139, two sheets, as built): 323F004/N3 through LV-323505 to
    # 323E010/N1, the pre-evaporator's inlet. DN 400 1.2 m and two 45 degree elbows; DN 150
    # 12.2 + 1.2 m, four 90 and one 45 degree elbow. LV-323505 is on sheet 2, 0.29 m into its
    # 1.2 m (50 + 133 + 105 mm to the valve's flange); the 0.91 m after it, the sheet's 90 and 45
    # degree elbows, rise to 323E010/N1.
    "323F004_TO_323F010": ((ID_DN400_MM, 1.2 + elbow_arc_m(400, 45, 2)),
                           (ID_DN150_MM, 12.2 + 0.29 + elbow_arc_m(150, 90, 3)),
                           (ID_DN150_MM, 0.91 + elbow_arc_m(150, 90) + elbow_arc_m(150, 45))),
    # 200-US6-323256-EC07DB (MB-0142): 323F010/N2 to 323D002/N1. DN 400 0.9 m and one 45 degree
    # elbow; DN 200 13.4 m and three 90 degree elbows.
    "323F010_TO_323D002": ((ID_DN400_MM, 0.9 + elbow_arc_m(400, 45)),
                           (ID_DN200_MM, 13.4 + elbow_arc_m(200, 90, 3))),
    # 323D002/N13 and N19 to 323P003A's suction on 200-US9-323254-EC08DB (MB-0140, three
    # sheets, as built): the header from both nozzles, sheet 1, 2.4 m, one 45 and one 90 degree
    # elbow; the header on sheet 2 to the tee, 0.9 m and a 45 — sheet 2's 2.0 m less sheet 3's
    # 1.1, taking the standby 323P003B's leg on sheet 2 as long as 323P003A's on sheet 3 —
    # and 323P003A's leg, sheet 3, 1.1 m and a 45. 323P003A's discharge to 324E001/N1 on
    # 150-US9-323255-EC08DB (MB-0141, three sheets, as built): sheet 1, 1.3 m, a 90 and a 45;
    # sheet 3, 13.9 m, six 90s and a 45. The standby's discharge leg, sheet 2, is not on the path.
    "323D002_TO_324E001": ((ID_DN200_MM, 2.4 + 0.9 + 1.1 + elbow_arc_m(200, 90)
                            + elbow_arc_m(200, 45, 3)),
                           (ID_DN150_MM, 1.3 + 13.9 + elbow_arc_m(150, 90, 7)
                            + elbow_arc_m(150, 45, 2))),
}


def route_volume_m3(name: str) -> float:
    """A route's line volume [m3]: its segments, each at its own bore.

    Process utility: the liquor a change at the upstream vessel must displace before it
    reaches the downstream one.

        V = sum_i pi/4 . D_i^2 . L_i
    """
    return sum(pipe_volume_from_mm(d_mm, l_m) for d_mm, l_m in ROUTE_SEGMENTS[name])


# ======================================================================================
# The letdowns' two-phase runs (handoff B-81, decided 2026-10-09)
# ======================================================================================

#: Each letdown route's segments downstream of its valve, by index into ``ROUTE_SEGMENTS``.
TWO_PHASE_SEGMENTS: dict[str, tuple[int, ...]] = {
    "322E001_TO_323C003": (1,),
    "323C003_TO_323F004": (1, 2),
    "323F004_TO_323F010": (2,),
}


def two_phase_volume_m3(name: str) -> float:
    """The volume of a route downstream of its letdown valve [m3]; zero on a liquid-full route."""
    return sum(pipe_volume_from_mm(*ROUTE_SEGMENTS[name][i])
               for i in TWO_PHASE_SEGMENTS.get(name, ()))


def homogeneous_density(x: float, rho_g: float, rho_l: float) -> float:
    """Density of a flashing liquor's two-phase mixture, the phases moving together [kg/m3].

    Process utility
    ---------------
    What a line downstream of a letdown holds per cubic metre: the flash gas fills most of its
    volume, so the line holds a fraction of the liquor a full line would, and a change in the
    liquor reaches the next stage that much sooner. The homogeneous form takes no slip between
    the phases, the step up from a liquid plug that needs no slip correlation (decided
    2026-10-09, handoff B-81).

    Equation
    --------
        rho_m = 1 / ( x / rho_g + (1 - x) / rho_l )
    """
    return 1.0 / (x / rho_g + (1.0 - x) / rho_l)


#: PFD 301, the flash gas of the stripper bottoms across LV-322501 at 4.1 bar a and 119 C: its
#: molar flow times its molar weight [kg/h], 650.46 kmol/h at 26.39 (the table's mass cell reads
#: 1716, a digit short), and its density [kg/m3].
M301_DES_KGH = 650.46 * 26.39
RHO_301_KGM3 = 3.39

#: PFD 701, LV-323501's flash into 323F004 at 1.1 bar a and 106 C, its density [kg/m3].
RHO_701_KGM3 = 0.68

#: PFD 790, 323F010's vapour at 0.5 bar a and 99 C, its density [kg/m3] — the gas LV-323505's
#: flash joins.
RHO_790_KGM3 = 0.29

#: LV-323505's flash at design [-]: PFD 319, 106 C, cooling to its own bubble point at 323F010's
#: pressure on the rigorous surface, the sensible heat boiling water at the pre-evaporator's
#: latent heat — the PFD carries no stream for it, the separator's 790 being mostly 323E010's
#: boil-up.
X_LV323505_DES = (urea_soln_cp(W_S319["Urea"], 106.0)
                  * (106.0 - design_bubble_t(W_S319, F010_P_BARA)) / EVAP_LAMBDA_KJKG)

#: The design flash at each letdown's outlet: (vapour mass fraction of the carrier, its density).
LETDOWN_FLASH: dict[str, tuple[float, float]] = {
    "322E001_TO_323C003": (M301_DES_KGH / 130582.0, RHO_301_KGM3),
    "323C003_TO_323F004": (R323_PHI_V701, RHO_701_KGM3),
    "323F004_TO_323F010": (X_LV323505_DES, RHO_790_KGM3),
}


def _proc_route(name: str, source: str, destination: str, carrier_kgh: float,
                rho_kgm3: float) -> ConsequenceRoute:
    """Build one product-line route whose design dead time is its inventory over its flow, not a
    fitted number: rho_l . V on a liquid-full line; downstream of a letdown, the two-phase run at
    the homogeneous density of the valve's design flash (B-81).

        td = (rho_l . V_up + rho_m . V_down) / m_dot
    """
    v_down = two_phase_volume_m3(name)
    td_s = packet_transport_time_s(route_volume_m3(name) - v_down, carrier_kgh, rho_kgm3)
    if name in LETDOWN_FLASH:
        x, rho_g = LETDOWN_FLASH[name]
        td_s += packet_transport_time_s(v_down, carrier_kgh,
                                        homogeneous_density(x, rho_g, rho_kgm3))
    return ConsequenceRoute(source, destination, carrier_kgh, td_s)


#: The five product-line routes on their isometrics; the liquid densities are V1's.
PROCESS_ROUTES: dict[str, ConsequenceRoute] = {
    "322E001_TO_323C003": _proc_route("322E001_TO_323C003", "322E001", "323C003",
                                      R323_FEED_DES_KGH, 1150.0),
    "323C003_TO_323F004": _proc_route("323C003_TO_323F004", "323C003", "323F004",
                                      R323_M314_DES, 1140.0),
    "323F004_TO_323F010": _proc_route("323F004_TO_323F010", "323F004", "323F010",
                                      R323_M319_DES, 1145.0),
    "323F010_TO_323D002": _proc_route("323F010_TO_323D002", "323F010", "323D002",
                                      R323_M317_DES, R323_D002_RHO),
    "323D002_TO_324E001": _proc_route("323D002_TO_324E001", "323D002", "324E001",
                                      R324_FEED_DES, R323_D002_RHO),
}


def route(name: str) -> ConsequenceRoute:
    """Look one route up by name, failing loudly on a typo.

    A missing route would otherwise present as a missing dead time — the teleporting-parcel
    defect, which is silent — so the lookup raises with the available names listed.
    """
    try:
        return PROCESS_ROUTES[name]
    except KeyError:
        raise KeyError(
            f"unknown process route {name!r}; known routes: "
            + ", ".join(sorted(PROCESS_ROUTES))
        ) from None
