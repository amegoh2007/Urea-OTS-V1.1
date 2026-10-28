"""322E001 — the HP stripper's tube bundle: the replacement the plant runs, and V1's.

What this covers
----------------
The geometry the stripper's hydraulics and holdups run on: the tube count, size and length, the
exchange surface, the per-tube flooding limit, the bottom channel LT-322501's sump fills, and the
shell's thermal capacity. Two bundles are carried, because the plant changed under the model:

* ``BUNDLE_V1`` — the 2,600-tube stripper Uhde built and V1 models (Uhde DDS
  UD-AU-322-DZ-0003-003 rev 00, page 3). The equivalence harnesses run the port on it, so V1's
  bytes are compared against V1.1's on V1's own stripper.
* ``BUNDLE_2950`` — the 2,950-tube replacement Officine Luigi Resta built to Stamicarbon's design
  (project Z524-H1269, Resta job 6355, built 2025) and installed at the last turnaround.
  ``BUNDLE``, the one the plant runs, is this one (decided 2026-10-28, session 72, `project.md`
  decision 154).

The 1750 MTPD PFD stays the flowsheet's anchor (decision 47): the feed, split, duty and product
temperatures the stripper is pinned on are the PFD's, and only the equipment's own model — its
flooding limit, its liquid holdup, its standing-full mass, its sump and its shell's capacity — runs
on the bundle installed.

Sources for the replacement (the vendor archive's ``New Stripper`` folder)
---------------------------------------------------------------------------
* Resta 6355 rev 6, general arrangement: 2,950 tubes LG. 6863, e31 x 2.5 M.W.; total effective
  surface 1,724 m2; capacity 14.67 m3 shell side, 28.83 m3 tube side.
* Resta 6355-A1 rev 4, tube bundle: 2,950 tubes e31 (+-0.2) x 2.5 M.W. (-0/+20 %), 6,000 mm
  tubesheet to tubesheet, 40 mm triangular pitch.
* Resta 6355-A9 rev 3, bottom tubesheet: I.D. channel 2,425 mm.
* Resta 6355-A7 rev 6, nozzle N17: a radar's stilling pipe, blinded, the bottom channel's only
  level connection — the vessel has no level taps, so LT-322501's span stays its instrument's.
* Stamicarbon process data sheet A4-101124 rev -: 41,738 kW; MP steam 79,375 kg/h at 19.7 bar,
  212 / 212 C; liquor 263,357 kg/h in at 182 C, out at 173 C; gas out at 187 C; tube side
  144.2 bar. It prints no heat-transfer coefficient and no corrected mean temperature difference.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

__all__ = ["TubeBundle", "UA_V1_KW_K", "UA_2950_KW_K", "BUNDLE_V1", "BUNDLE_2950", "BUNDLE"]


@dataclass(frozen=True)
class TubeBundle:
    """One 322E001 tube bundle, as the stripper's equipment model runs it."""

    #: What the record is, for a test's or a log's message.
    name: str
    #: Number of tubes [-].
    n_tubes: int
    #: Tube outside diameter [m].
    tube_od_m: float
    #: Tube wall thickness [m].
    tube_wall_m: float
    #: Effective tube length, tubesheet to tubesheet [m].
    tube_l_eff_m: float
    #: Exchange surface, the datasheet's own figure [m2]: the check on the geometry above.
    surface_m2: float
    #: Solution per tube at the flooding limit [kg/h].
    flood_kgh_per_tube: float
    #: The bottom channel's cross-section, which LT-322501's sump fills [m2].
    sump_area_m2: float
    #: The liquid band LT-322501 spans, 0 to 100 % [m]. The transmitter's, not the vessel's.
    level_span_m: float
    #: The shell's U.A over V1's bundle's [-]: what this bundle transfers at a given LMTD.
    shell_capacity: float
    #: The tube side's whole volume, channels and heads with the tubes [m3]: what the stripper
    #: opens to the synthesis loop's gas (`data.unit_322_loop.V_E001_M3`).
    tube_side_m3: float

    @property
    def tube_id_m(self) -> float:
        """Tube inside diameter [m]: the outside diameter less two walls."""
        return self.tube_od_m - 2.0 * self.tube_wall_m

    @property
    def v_tubes_m3(self) -> float:
        """The bundle's liquid volume [m3], what its tubes hold standing full.

        Process utility
        ---------------
        The holdup the stripper's rate laws integrate over, and what a full sump backs up into
        (B-104). Written as V1 writes STRIP_V_TUBES_M3, so V1's bundle returns V1's bytes.
        """
        return self.n_tubes * math.pi * 0.25 * self.tube_id_m ** 2 * self.tube_l_eff_m

    @property
    def v_sump_m3(self) -> float:
        """The sump's volume between LT-322501's two limits [m3], as V1 writes STRIP_V_SUMP_M3."""
        return self.sump_area_m2 * self.level_span_m


def _terminal_ua_kw_k(q_kw: float, t_steam_c: float, t_top_c: float, t_bot_c: float) -> float:
    """A process datasheet's U.A on its own terminal temperatures [kW/K].

    Process utility
    ---------------
    Neither stripper's datasheet prints its coefficient or its corrected mean temperature
    difference, so each is read as its duty over the LMTD of condensing steam against its tube
    side's top and bottom temperatures — the same profile `stripper_shell` bounds the shell on.
    Only the two bundles' RATIO is used, so the shared simplification cancels.
    """
    dt_top = t_steam_c - t_top_c
    dt_bot = t_steam_c - t_bot_c
    return q_kw * math.log(dt_bot / dt_top) / (dt_bot - dt_top)


#: V1's bundle's rating, 1 160.5 kW/K: 39 400 kW on saturated MP steam at 214 C, the tube side
#: 187 -> 172 C. Source: 322E001's licensor process datasheet, UD-AU-322-EC-0003 page 4.
UA_V1_KW_K = _terminal_ua_kw_k(39_400.0, 214.0, 187.0, 172.0)

#: The replacement's rating, 1 325.7 kW/K: 41 738 kW on steam at 212 C, the gas leaving the top
#: at 187 C and the liquor the bottom at 173 C. Source: Stamicarbon process data sheet A4-101124.
#: Per square metre the two agree to 0.7 %, 0.764 and 0.769 kW/(m2 K): the same tube, the same
#: service, 13.5 % more surface.
UA_2950_KW_K = _terminal_ua_kw_k(41_738.0, 212.0, 187.0, 173.0)

#: V1's 2,600-tube bundle. Source: Uhde DDS UD-AU-322-DZ-0003-003 rev 00, page 3 — line 34 the
#: count, line 36 the 31 x 3.0 mm tube, line 35 "6000 mm eff.", line 25 the 1,519.00 m2 surface,
#: which N.pi.d_o.L reproduces to +0.018 %; the bottom head's 2,430 mm I.D. and LT-322501's 1.5 m
#: span from their datasheets; 145 kg/h per tube at the flooding limit from Brouwer, "How to Solve
#: Stripper Efficiency Issues", UreaKnowHow 2025, citing IFS Proceeding 166 — at 183 C and 140 bar
#: in a one-inch tube, the 25.0 mm (0.984 inch) bore taking it without scaling. V1 `main.py`
#: STRIP_N_TUBES to STRIP_LEVEL_SPAN_M. The tube side's 24.7 m3 from the arrangement drawing,
#: UD-AU-322-DZ-0003-003 (session 40).
BUNDLE_V1 = TubeBundle(
    name="322E001 2,600 tubes (Uhde, V1)", n_tubes=2600, tube_od_m=0.031, tube_wall_m=0.003,
    tube_l_eff_m=6.000, surface_m2=1519.00, flood_kgh_per_tube=145.0, sump_area_m2=4.638,
    level_span_m=1.5, shell_capacity=1.0, tube_side_m3=24.7)

#: The replacement's 2,950-tube bundle (the module note's sources). The tube is the same 31 mm
#: outside on a 2.5 mm minimum wall, so its bore is 26.0 mm, 4 % wider than V1's; N.pi.d_o.L =
#: 2950 x pi x 0.031 x 6.000 = 1 723.85 m2 against the general arrangement's 1 724.
#:
#: The flooding limit per tube scales on Wallis's counter-current flooding law: at a fixed
#: gas-to-liquid ratio the dimensionless superficial velocities j* = j . sqrt(rho / (g D drho))
#: run as m / D^2.5, so a tube floods at a liquor flow proportional to D^2.5 — 145 x (26/25)^2.5 =
#: 159.9 kg/h, scaled from the bore V1 applied the cited figure to. The length is the same 6.000 m.
#: The bottom channel is 2,425 mm I.D.; LT-322501 keeps its 1.5 m span. The shell's capacity is the
#: two datasheets' U.A ratio, 1.142. The tube side holds 28.83 m3 (the general arrangement's
#: capacity, tube side; the shell side's is 14.67 m3).
BUNDLE_2950 = TubeBundle(
    name="322E001 2,950 tubes (Stamicarbon / Resta 6355)", n_tubes=2950, tube_od_m=0.031,
    tube_wall_m=0.0025, tube_l_eff_m=6.000, surface_m2=1724.0,
    flood_kgh_per_tube=145.0 * (0.026 / 0.025) ** 2.5,
    sump_area_m2=math.pi * 0.25 * 2.425 ** 2, level_span_m=1.5,
    shell_capacity=UA_2950_KW_K / UA_V1_KW_K, tube_side_m3=28.83)

#: The bundle the plant runs (decided 2026-10-28, decision 154).
BUNDLE = BUNDLE_2950
