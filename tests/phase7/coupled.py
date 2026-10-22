"""The coupled synthesis-loop transients of `References/scenarios/Scenarios5.md`, put to the plant.

What this is
------------
``Scenarios5.md`` is a generic note on a Stamicarbon CO2-stripping loop (HP stripper, HPCC, reactor,
HP scrubber, HP ejector): an LPCC ammonia-water addition traced in eight steps, and eleven more
cases each with an initial perturbation, a counter-intuitive intermediate shift and a delayed
feedback. Like the four notes before it (`tests.phase7.deviations`) it is not plant data
(CLAUDE.md §4): each step is an EXPECTATION, measured on the port's plant on the console's own
lever, against an unperturbed run of the same length.

Each claim is read in one of two waves, as the note's own timing does:

* ``W1`` — the first five minutes: the departure from the control of largest magnitude in
  (0, 300] s, signed;
* ``W2`` — the delayed feedback, 15 to 45 minutes: the mean departure over [900, 2700] s;
* ``REV`` — a reversal: the W2 mean less the W1 departure, so "the level drops back" is a negative
  REV whatever the level did first (its first move is its own W1 claim).

Helwan's loop is the note's in its vessels and differs in its levers: the HPCC raises LP steam
into 322D001A/B on the LP header, so the note's "HPCC LP steam drum pressure" is MASTER-329207's
set point; the motive ammonia is 321P002's, on FFIC-321404's ratio (2.0 to 5.0) or SIC-321951's
speed; the reactor's outlet is HV-322605 on its hand controller, there is no reactor level
controller; the scrubber's tempered water is TIC-329005's; the stripper's MP steam is
PIC-329204's on 329D005. Where a lever does not exist (no motive-ammonia preheater on Helwan's
loop) the case is listed in `NOT_PUT` with the reason. A claim no published indicator carries is
listed in the case's ``unmodelled``.

Indicators carried by no packet field are read off the tick's results (``x.`` paths,
`run_coupled.EXTRA`).

Source: ``D:/Work/Urea Simulation/References/scenarios/Scenarios5.md``.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The note's two waves [s after the step]: the first five minutes, and 15 to 45 minutes.
W1_S = (0.0, 300.0)
W2_S = (900.0, 2700.0)
DURATION_S = 2700.0


@dataclass(frozen=True)
class Claim:
    """One step of a case: the indicator, the claimed direction (+1 rises, -1 falls), the wave."""

    step: str
    path: str
    sign: int
    wave: str
    claim: str


@dataclass(frozen=True)
class Coupled:
    """One case of the note, put on Helwan's plant."""

    key: str
    source: str
    title: str
    helwan: str
    commands: tuple
    claims: tuple
    duration_s: float = DURATION_S
    unmodelled: tuple = ()


C = Claim

# ---- the indicators, by what the note calls them --------------------------------------------
P_SYN = "x.p_syn_bara"                       # PT-329201, unrounded (the packet shows 0.1 bar)
SCR_LEVEL = "SCRUB_322E003.LT_329501"         # the HP scrubber's level
SCR_T_OVF = "SCRUB_322E003.TT_322002"         # its liquid overflow (bottom carbamate)
SCR_T_GAS = "SCRUB_322E003.TT_322011"         # its gas outlet (vent top)
SCR_OVF = "SCRUB_322E003.ov_th"               # what it condenses into its overflow
SCR_OFF = "SCRUB_322E003.off_th"              # its off-gas to 322C001 through HV-322604
EJ_T = "EJ_322F001.TT_322012"                 # the HP ejector's discharge
EJ_SUCT = "EJ_322F001.suction_kgh"            # what it entrains from the scrubber
R_LEVEL = "REACT_322R001.LT_322504"
R_NC = "REACT_322R001.L_feed"                 # the reactor feed's N/C
R_HC = "REACT_322R001.W_feed"                 # and its H/C
R_X = "REACT_322R001.X_conv"
R_T_TOP = "REACT_322R001.TT_322005"           # the top node
R_T_BOT = "REACT_322R001.TT_322008"           # the bottom node
R_OFFGAS = "x.reactor_offgas_th"              # the reactor's off-gas to the scrubber
HPCC_COND = "HPCC_322E002.liq_th"             # what 322E002 condenses
HPCC_GAS = "HPCC_322E002.gas_th"              # the gas it passes to the reactor
HPCC_STEAM = "HPCC_322E002.steam.kgh"         # the LP steam it raises
ST_T_BOT = "STRIP_322E001.TT_322004"
ST_NH3 = "STRIP_322E001.bot_mass_pct.NH3"     # the carbamate the stripper leaves in its bottoms
ST_TOP = "STRIP_322E001.top_th"               # its top gas to 322E002
LP_GAS = "RECIRC_323.C003.v305_th"            # the LP decomposer's gas to the LPCC
LPCC_P = "LPCC_3232.E003.P_bara"
LPCC_T = "LPCC_3232.E003.TT_323006"
LPCC_LEVEL = "LPCC_3232.E003.LI_323502"
PUMP_308 = "LPCC_3232.E003.carbamate308_th"   # the HP carbamate pump 323P001's delivery

_NO_DP = "the stripper's tube-side pressure drop (no dP transmitter or flooding hydraulics)"

COUPLED = (
    Coupled(
        "S5-W", "Scenarios5.md, the LPCC ammonia-water case", "Ammonia water to the LPCC increased",
        "PFD 734, FIC-323401's ammonia water from 328D003 to 323E003: FIC-323401 in MAN, FV-323401 "
        "49.3 -> 100 %, 1 534 -> about 7 000 kg/h (its set point stops at 2 000 kg/h); LIC-323502 on "
        "SIC-323901 carries the extra liquid to 322E003 as PFD 308, its water with it (B-105)",
        ({"type": "r323_ctrl_set", "id": "FIC-323401", "mode": "MAN", "op": 100.0},),
        (C("2", PUMP_308, +1, "W1", "the LPCC level controller raises the HP carbamate pump"),
         C("2", SCR_OVF, +1, "W1", "absorption in the scrubber improves"),
         C("2", SCR_T_OVF, -1, "W1", "the scrubber's liquid overflow cools"),
         C("2", SCR_T_GAS, -1, "W1", "the scrubber's gas outlet cools"),
         C("3", P_SYN, -1, "W1", "the synthesis pressure decreases"),
         C("3", SCR_LEVEL, +1, "W1", "the scrubber level rises"),
         C("4", EJ_T, +1, "W1", "the ejector temperature increases"),
         C("5", R_LEVEL, +1, "W1", "the reactor level rises"),
         C("5", R_NC, -1, "W1", "the N/C ratio decreases"),
         C("6", R_OFFGAS, -1, "W2", "less gas leaves the reactor for the scrubber"),
         C("7", SCR_LEVEL, -1, "REV", "the scrubber level drops back"),
         C("7", SCR_T_OVF, -1, "REV", "the scrubber temperatures recede"),
         C("8", R_HC, +1, "W2", "the extra water raises the reactor's H/C"),
         C("8", R_X, -1, "W2", "conversion drops after 30-45 min"),
         C("8", R_T_TOP, -1, "W2", "the reactor top temperature drops"),
         C("8", ST_NH3, +1, "W2", "more unconverted carbamate loads the stripper"),
         C("8", P_SYN, +1, "REV", "the synthesis pressure ultimately rebounds")),
        unmodelled=("the density analyser's cross-sensitivity to H/C",)),
    Coupled(
        "S5-1", "Scenarios5.md §1", "Raising the HPCC's LP steam pressure",
        "322E002 raises steam into 322D001A/B on the LP header: MASTER-329207 5.01 -> 5.5 bar a",
        ({"type": "master207_set", "sp": 5.5},),
        (C("1", HPCC_COND, -1, "W1", "less stripper gas condenses in the HPCC"),
         C("1", HPCC_GAS, +1, "W1", "more gas enters the reactor"),
         C("1", R_T_TOP, +1, "W1", "reactor temperatures rise slightly"),
         C("1", P_SYN, +1, "W1", "the synthesis pressure climbs"),
         C("1", R_OFFGAS, +1, "W1", "more gas leaves the reactor for the scrubber"),
         C("1", SCR_T_GAS, +1, "W1", "the scrubber's gas outlet heats"),
         C("1", SCR_T_OVF, +1, "W1", "the scrubber's overflow heats"),
         C("1", SCR_LEVEL, +1, "W1", "the scrubber level rises"),
         C("1", EJ_T, +1, "W1", "the ejector discharge temperature rises"),
         C("1", HPCC_COND, +1, "REV", "the HPCC's condensation recovers partway"),
         C("1", R_OFFGAS, -1, "REV", "the reactor's gas breakthrough subsides"),
         C("1", SCR_LEVEL, +1, "W2", "the scrubber settles slightly higher"))),
    Coupled(
        "S5-2", "Scenarios5.md §2", "High N/C excursion above the azeotrope",
        "more motive NH3 to 322F001: FFIC-321404's ratio 2.023 -> 2.124 (+5 %), the reactor feed's "
        "N/C from 3.07 to about 3.2",
        ({"type": "ratio_set", "sp": 2.124},),
        (C("0", R_NC, +1, "W1", "the reactor N/C rises above 3.1"),
         C("2", SCR_LEVEL, -1, "W1", "the scrubber level drops at once"),
         C("2", EJ_T, -1, "W1", "the ejector discharge cools"),
         C("2", R_T_TOP, -1, "W2", "the reactor temperature drops"),
         C("2", P_SYN, +1, "W2", "the synthesis pressure rises sharply"),
         C("2", R_OFFGAS, +1, "W2", "a large NH3 stream leaves the reactor for the scrubber"),
         C("2", SCR_OFF, +1, "W2", "uncondensed NH3 breaks through the scrubber overhead"),
         C("2", PUMP_308, +1, "W2", "the LPCC's recycle raises the HP carbamate pump"),
         C("2", SCR_LEVEL, +1, "REV", "the scrubber level is pushed back up"))),
    Coupled(
        "S5-3", "Scenarios5.md §3", "Over-stripping: HP stripper steam raised",
        "329D005's MP header: PIC-329204 19.7 -> 20.5 bar a",
        ({"type": "pic329204_set", "mode": "AUTO", "sp": 20.5},),
        (C("3", ST_T_BOT, +1, "W1", "the stripper bottoms temperature rises"),
         C("3", ST_NH3, -1, "W1", "stripping efficiency rises"),
         C("3", ST_TOP, +1, "W1", "more gas leaves the stripper top for the HPCC"),
         C("3", P_SYN, +1, "W1", "the synthesis pressure rises"),
         C("3", R_OFFGAS, +1, "W1", "more uncondensed gas passes the reactor to the scrubber"),
         C("3", PUMP_308, -1, "W1", "the LPCC level controller throttles the HP carbamate pump"),
         C("3", SCR_T_OVF, +1, "W1", "the scrubber's overflow heats"),
         C("3", SCR_T_GAS, +1, "W1", "the scrubber's gas outlet heats"),
         C("3", SCR_LEVEL, -1, "W1", "the scrubber level dips"),
         C("3", SCR_LEVEL, +1, "REV", "then rebounds as the reactor gas condenses"),
         C("3", P_SYN, +1, "W2", "the loop settles at a higher pressure"))),
    Coupled(
        "S5-4", "Scenarios5.md §4", "Inert blanketing: the HP scrubber vent throttled",
        "HV-322604, 322E003's off-gas to 322C001: HIC-322604 72 -> 40 %",
        ({"type": "hic604_set", "op": 40.0},),
        (C("4", HPCC_STEAM, -1, "W2", "the HPCC's LP steam generation drops"),
         C("4", P_SYN, +1, "W1", "the synthesis pressure rises"),
         C("4", P_SYN, +1, "REV", "and keeps climbing, not self-correcting"),
         C("4", R_OFFGAS, +1, "W1", "more gas leaves the reactor for the scrubber"),
         C("4", SCR_T_GAS, +1, "W1", "the scrubber's gas outlet heats")),
        unmodelled=("the inert film's mass-transfer resistance in 322E002 and 322E003 (no "
                    "blanketing model: the condensers' capacities do not see the inerts)",
                    "a passivation-air surge (no lever: the CO2's air is the boundary's)")),
    Coupled(
        "S5-5a", "Scenarios5.md §5", "HP stripper flooding: the sump flooded",
        "LIC-322501 in MAN, LV-322501 46 -> 10 %: LT-322501 fills, holds its excess back in the "
        "tubes (B-103) up to their 8 689 kg standing full, and 322R001 keeps the rest (B-104)",
        ({"type": "lic_set", "mode": "MAN", "op": 10.0},),
        (C("5", ST_T_BOT, -1, "W1", "the stripper bottoms temperature plunges"),
         C("5", ST_NH3, +1, "W1", "unstripped carbamate leaves the bottoms"),
         C("5", LP_GAS, +1, "W1", "a gas surge leaves the LP decomposer"),
         C("5", LPCC_P, +1, "W2", "the LPCC's pressure rises"),
         C("5", LPCC_T, +1, "W2", "and its temperature"),
         C("5", LPCC_LEVEL, +1, "W2", "and its level"),
         C("5", PUMP_308, +1, "W2", "the HP carbamate pump ramps up"),
         C("5", SCR_LEVEL, +1, "W2", "the scrubber level surges"),
         C("5", EJ_T, +1, "W2", "the ejector temperature surges"),
         C("5", R_LEVEL, +1, "W2", "the reactor level spikes")),
        unmodelled=(_NO_DP,)),
    Coupled(
        "S5-5b", "Scenarios5.md §5", "HP stripper flooding: excessive liquid load",
        "the reactor's liquor dumped on the stripper: HIC-322605 60 -> 100 %",
        ({"type": "hic605_set", "op": 100.0},),
        (C("5", ST_T_BOT, -1, "W1", "the stripper bottoms temperature plunges"),
         C("5", ST_NH3, +1, "W1", "unstripped carbamate leaves the bottoms"),
         C("5", LP_GAS, +1, "W1", "a gas surge leaves the LP decomposer"),
         C("5", LPCC_P, +1, "W2", "the LPCC's pressure rises"),
         C("5", LPCC_T, +1, "W2", "and its temperature"),
         C("5", LPCC_LEVEL, +1, "W2", "and its level"),
         C("5", PUMP_308, +1, "W2", "the HP carbamate pump ramps up"),
         C("5", SCR_LEVEL, +1, "W2", "the scrubber level surges"),
         C("5", EJ_T, +1, "W2", "the ejector temperature surges"),
         C("5", R_LEVEL, +1, "W2", "the reactor level spikes")),
        unmodelled=(_NO_DP,)),
    Coupled(
        "S5-6a", "Scenarios5.md §6", "Low N/C excursion below the azeotrope: the NH3 pump slowed",
        "the HP ammonia pump slowed: SIC-321951 in MAN, 321P002B 83.6 -> 75.2 % (-10 %), below "
        "322F001's stall at 0.907 of its design motive; FFIC-321404's ratio set point stops at 2.0",
        ({"type": "controller_set", "id": "SIC-321951", "mode": "MAN", "op": 75.2},),
        (C("0", R_NC, -1, "W1", "the reactor N/C falls below 2.8"),
         C("6", SCR_LEVEL, +1, "W1", "the scrubber level rises at once"),
         C("6", EJ_T, +1, "W1", "the ejector discharge heats"),
         C("6", HPCC_COND, -1, "W1", "the HPCC's condensation drops"),
         C("6", P_SYN, +1, "W1", "the synthesis pressure climbs sharply"),
         C("6", R_T_TOP, -1, "W1", "reactor temperatures drop"),
         C("6", R_X, -1, "W1", "conversion drops"),
         C("6", R_OFFGAS, +1, "W1", "CO2-rich gas breaks through the reactor to the scrubber"),
         C("6", SCR_T_OVF, +1, "W1", "the scrubber heats"),
         C("6", ST_T_BOT, +1, "W1", "the stripper bottoms temperature ticks up"),
         C("6", ST_T_BOT, -1, "REV", "then drops as the low-conversion effluent arrives"),
         C("6", ST_NH3, +1, "W2", "carbamate slips through the stripper"),
         C("6", LPCC_LEVEL, +1, "W2", "the LP section floods"))),
    Coupled(
        "S5-6b", "Scenarios5.md §6", "Low N/C excursion below the azeotrope: more CO2",
        "the N/C lowered with the motive held: SIC-321951 in MAN at its 83.56 %, the CO2 boundary "
        "54.62 -> 60.08 t/h (+10 %, the instructor's co2_set), the reactor feed's N/C to about 2.8",
        ({"type": "controller_set", "id": "SIC-321951", "mode": "MAN", "op": 83.561},
         {"type": "co2_set", "value": 60.08}),
        (C("0", R_NC, -1, "W1", "the reactor N/C falls below 2.8"),
         C("6", SCR_LEVEL, +1, "W1", "the scrubber level rises at once"),
         C("6", EJ_T, +1, "W1", "the ejector discharge heats"),
         C("6", HPCC_COND, -1, "W1", "the HPCC's condensation drops"),
         C("6", P_SYN, +1, "W1", "the synthesis pressure climbs sharply"),
         C("6", R_T_TOP, -1, "W1", "reactor temperatures drop"),
         C("6", R_X, -1, "W1", "conversion drops"),
         C("6", R_OFFGAS, +1, "W1", "CO2-rich gas breaks through the reactor to the scrubber"),
         C("6", SCR_T_OVF, +1, "W1", "the scrubber heats"),
         C("6", ST_T_BOT, +1, "W1", "the stripper bottoms temperature ticks up"),
         C("6", ST_T_BOT, -1, "REV", "then drops as the low-conversion effluent arrives"),
         C("6", ST_NH3, +1, "W2", "carbamate slips through the stripper"),
         C("6", LPCC_LEVEL, +1, "W2", "the LP section floods"))),
    Coupled(
        "S5-6c", "Scenarios5.md §6", "Low N/C excursion below the azeotrope: more CO2, +20 %",
        "the N/C lowered with the motive held: SIC-321951 in MAN at its 83.56 %, the CO2 boundary "
        "54.62 -> 65.54 t/h (+20 %, the instructor's co2_set), the reactor feed's N/C toward 2.6 "
        "(B-106's measurement)",
        ({"type": "controller_set", "id": "SIC-321951", "mode": "MAN", "op": 83.561},
         {"type": "co2_set", "value": 65.544}),
        (C("0", R_NC, -1, "W1", "the reactor N/C falls below 2.8"),
         C("6", SCR_LEVEL, +1, "W1", "the scrubber level rises at once"),
         C("6", EJ_T, +1, "W1", "the ejector discharge heats"),
         C("6", HPCC_COND, -1, "W1", "the HPCC's condensation drops"),
         C("6", P_SYN, +1, "W1", "the synthesis pressure climbs sharply"),
         C("6", R_T_TOP, -1, "W1", "reactor temperatures drop"),
         C("6", R_X, -1, "W1", "conversion drops"),
         C("6", R_OFFGAS, +1, "W1", "CO2-rich gas breaks through the reactor to the scrubber"),
         C("6", SCR_T_OVF, +1, "W1", "the scrubber heats"),
         C("6", ST_T_BOT, +1, "W1", "the stripper bottoms temperature ticks up"),
         C("6", ST_T_BOT, -1, "REV", "then drops as the low-conversion effluent arrives"),
         C("6", ST_NH3, +1, "W2", "carbamate slips through the stripper"),
         C("6", LPCC_LEVEL, +1, "W2", "the LP section floods"))),
    Coupled(
        "S5-7", "Scenarios5.md §7", "Lowering the HPCC's LP steam pressure",
        "MASTER-329207 5.01 -> 4.5 bar a",
        ({"type": "master207_set", "sp": 4.5},),
        (C("7", HPCC_COND, +1, "W1", "the HPCC condenses nearly all the stripper gas"),
         C("7", P_SYN, -1, "W1", "the synthesis pressure drops rapidly"),
         C("7", R_T_BOT, -1, "W1", "the reactor bottom temperature drops"),
         C("7", R_T_TOP, -1, "W1", "and its top"),
         C("7", R_OFFGAS, -1, "W1", "almost no gas leaves the reactor for the scrubber"),
         C("7", SCR_T_OVF, -1, "W1", "the scrubber cools"),
         C("7", SCR_LEVEL, -1, "W1", "the scrubber level drops"),
         C("7", EJ_T, -1, "W1", "the ejector temperature decreases"),
         C("7", R_X, -1, "W2", "the colder reactor's conversion drops"),
         C("7", ST_T_BOT, -1, "W2", "the stripper bottoms temperature drops"),
         C("7", ST_NH3, +1, "W2", "carbamate slips to the LPCC"),
         C("7", PUMP_308, +1, "W2", "the HP carbamate pump ramps up"),
         C("7", SCR_LEVEL, +1, "REV", "the scrubber level is driven back up"))),
    Coupled(
        "S5-8", "Scenarios5.md §8", "HP scrubber tempered water degraded",
        "TIC-329005 80 -> 86 C",
        ({"type": "tic_set", "mode": "AUTO", "sp": 86.0},),
        (C("8", SCR_T_OVF, +1, "W1", "the scrubber's overflow climbs"),
         C("8", SCR_T_GAS, +1, "W1", "its gas outlet climbs"),
         C("8", EJ_T, +1, "W1", "the ejector discharge heats"),
         C("8", P_SYN, +1, "W1", "the synthesis pressure rises"),
         C("8", SCR_OFF, +1, "W1", "uncondensed gas breaks through the scrubber overhead"),
         C("8", LPCC_LEVEL, +1, "W2", "the LPCC's level rises"),
         C("8", LPCC_T, +1, "W2", "and its temperature"),
         C("8", PUMP_308, +1, "W2", "the HP carbamate pump raises its flow"),
         C("8", SCR_LEVEL, +1, "W2", "the scrubber level rises"),
         C("8", SCR_T_OVF, -1, "REV", "the scrubber temperatures are pulled partway back"))),
    Coupled(
        "S5-9", "Scenarios5.md §9", "Opening the reactor's outlet valve",
        "Helwan has no reactor level controller: HV-322605 opened, HIC-322605 60 -> 75 %",
        ({"type": "hic605_set", "op": 75.0},),
        (C("9", R_LEVEL, -1, "W1", "the reactor level drops"),
         C("9", ST_T_BOT, -1, "W1", "the stripper bottoms temperature drops"),
         C("9", ST_NH3, +1, "W1", "stripping efficiency declines"),
         C("9", R_X, -1, "W1", "conversion drops (less residence)"),
         C("9", LPCC_LEVEL, +1, "W2", "the LPCC level surges"),
         C("9", PUMP_308, +1, "W2", "the HP carbamate pump ramps up"),
         C("9", SCR_LEVEL, +1, "W2", "the scrubber level rises"),
         C("9", EJ_T, +1, "W2", "the ejector temperature rises"),
         C("9", R_LEVEL, +1, "REV", "the reactor level climbs back up"),
         C("9", R_NC, -1, "W2", "the reactor N/C is diluted"),
         C("9", R_HC, +1, "W2", "and its H/C raised"))),
    Coupled(
        "S5-11", "Scenarios5.md §11", "Under-stripping: HP stripper steam dropped",
        "PIC-329204 19.7 -> 18.9 bar a",
        ({"type": "pic329204_set", "mode": "AUTO", "sp": 18.9},),
        (C("11", ST_T_BOT, -1, "W1", "the stripper bottoms temperature drops"),
         C("11", ST_NH3, +1, "W1", "stripping efficiency falls"),
         C("11", ST_TOP, -1, "W1", "much less gas leaves the stripper top"),
         C("11", P_SYN, -1, "W1", "the synthesis pressure drops"),
         C("11", HPCC_STEAM, -1, "W1", "the HPCC's LP steam generation falls"),
         C("11", R_OFFGAS, -1, "W1", "less gas passes the reactor to the scrubber"),
         C("11", SCR_T_OVF, -1, "W1", "the scrubber's temperatures dip"),
         C("11", SCR_LEVEL, -1, "W1", "and its level"),
         C("11", LPCC_P, +1, "W2", "the LPCC's pressure rises"),
         C("11", LPCC_T, +1, "W2", "its temperature"),
         C("11", LPCC_LEVEL, +1, "W2", "and its level"),
         C("11", PUMP_308, +1, "W2", "the HP carbamate pump ramps up strongly"),
         C("11", SCR_LEVEL, +1, "REV", "the scrubber level rises sharply"),
         C("11", EJ_T, +1, "W2", "the ejector temperature increases"),
         C("11", R_LEVEL, +1, "W2", "the reactor level rises"),
         C("11", R_NC, -1, "W2", "the reactor N/C drops"),
         C("11", R_HC, +1, "W2", "and its H/C rises"),
         C("11", R_X, -1, "W2", "conversion falls"))),
)

#: The note's cases Helwan's plant has no lever for, and why.
NOT_PUT = {
    "S5-10": ("Scenarios5.md §10, cold motive NH3 (HP NH3 preheater fouled)",
              "Helwan's loop has no motive-ammonia preheater: 321P002 delivers the NH3 off "
              "321D003 at its pump's discharge temperature, and no console lever moves it"),
}

__all__ = ["W1_S", "W2_S", "DURATION_S", "Claim", "Coupled", "COUPLED", "NOT_PUT"]
