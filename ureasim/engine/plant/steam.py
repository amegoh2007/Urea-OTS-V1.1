"""Unit 329's steps: the steam network, and the meter that hands it its users' draws.

What this is
------------
The schedule's entry for V1's ``step_sim`` section 4, the steam network, and the users' meter the
port adds after the last user steps. V1 steps the network ahead of every user it supplies, so the
network takes each user's draw as the user left it on the tick before; the users then read the
headers the network left this tick. The stripper's draw on 329D005 and the HPCC's raising out of
322D001A/B's water are the synthesis loop's of this tick (section 3, `synthesis`), on their PFD
rows; trip 21.2 forces PIC-329204 and HV-329601 as the trips left it on the tick before. A 322E002
tube leak (handoff B-82) discharges into 322D001A/B on the same tick.

The meter turns each simulated user's live draw into the header's view of it (handoff B-68; the
users the simulator does not model at their PFD rows): each unit's live ratio on its PFD row where
its own model's design differs (decision 47's class) — the chests on their duties, 323E002's 918 on
its 5858 kW, 323E010's 926, 324E001's 919, 324E003's 920 on theirs; the motive steam, 328C004's 931
and XV-322915's flood as they pass (their models' designs are the PFD's rows); 322C001's three
trace-steam orifices as they pass, taken out of PFD 910, the 9-bar header's steam tracing, which
carries them (decided 2026-10-07); 328C003's 911 for FT-329403.

Source: V1 ``backend/main.py`` ``step_sim`` 7823-7856; `ureasim.units.steam.steam_network`; As-Built
Part LIV.
"""

from __future__ import annotations

from dataclasses import dataclass

from ureasim.data.unit_323 import E002_Q_DES_KW, E010_Q_DES_KW
from ureasim.data.unit_324 import E001_Q_DES_KW, E003_Q_DES_KW
from ureasim.data.unit_329 import (
    LP_USERS_PFD,
    MP9_TRACE_DES_KGH,
    MP9_USERS_PFD,
    STEAM_PFD_KGH,
    design_users,
)
from ureasim.engine.plant.evaporation import MOTIVE
from ureasim.engine.schedule import DeclaredTear, Result, State, Step, Tear
from ureasim.units.steam.condensate_analyser import (
    ai_329701_alarms,
    ai_329701_reading,
    condensate_conductivity_us_cm,
)
from ureasim.units.steam.steam_network import SteamDraws, SteamNetwork, pfd_basis_kgh

__all__ = ["USERS", "SteamUsersResult", "units", "steps", "tears"]

#: The users' meter's step name.
USERS = "329-USERS"


@dataclass(frozen=True)
class SteamUsersResult:
    """What every steam user drew on this tick, on the headers' PFD basis [kg/h, by stream]."""

    users_lp_kgh: dict
    users_9_kgh: dict
    m_911_kgh: float
    #: AI-329701, the LP condensate's conductivity in 329D001 [uS/cm]: the measured value, the
    #: transmitter's reading on its 0-10 range, and whether it is over the range (B-90); its high
    #: and high-high alarms on the plant DCS's set points.
    kappa_329d001_us_cm: float
    ai_329701_us_cm: float
    ai_329701_over: bool
    ai_329701_h1: bool = False
    ai_329701_h2: bool = False


def units() -> tuple[dict, dict]:
    """The network, seeded on its design closure."""
    return {"329": SteamNetwork()}, {}


def _network(plant, a, dt):
    leak = a["leak"]
    draws = SteamDraws(strip_kgh=a["strip_kgh"], raise_kgh=a["raise_kgh"],
                       users_9_kgh=a["users_9_kgh"], users_lp_kgh=a["users_lp_kgh"],
                       c003_kgh=a["c003_kgh"], leak_vapour_kgh=leak.vapour_kgh,
                       leak_liquid_kgh=leak.liquid_kgh, leak_solids_kgh=leak.solids_kgh,
                       leak_boil_kgh=leak.boil_kgh)
    return plant.units["329"].step(draws, dt, trip_21_2=a["trip_21_2"])


def _users(plant, a, dt):
    pfd = STEAM_PFD_KGH
    lp = design_users(LP_USERS_PFD)
    lp.update({
        "918": pfd_basis_kgh(pfd["918"], a["q_323e002_kw"], E002_Q_DES_KW),
        "919": pfd_basis_kgh(pfd["919"], a["q_324e001_kw"], E001_Q_DES_KW),
        "926": pfd_basis_kgh(pfd["926"], a["q_323e010_kw"], E010_Q_DES_KW),
        "924": a["m_924_kgh"], "927": a["m_927_kgh"], "929": a["m_929_kgh"],
        "931": a["m_931_kgh"]})
    mp9 = design_users(MP9_USERS_PFD)
    mp9.update({"920": pfd_basis_kgh(pfd["920"], a["q_324e003_kw"], E003_Q_DES_KW),
                "flood": a["m_flood_kgh"],
                "910": pfd["910"] - MP9_TRACE_DES_KGH,
                "trace": a["m_trace_kgh"]})
    leaked = a["leak"].leaked_kmolh
    kappa = condensate_conductivity_us_cm(leaked.get("NH3", 0.0), leaked.get("CO2", 0.0),
                                          sum(lp.values()))
    pv, over = ai_329701_reading(kappa)
    h1, h2 = ai_329701_alarms(kappa)
    return SteamUsersResult(users_lp_kgh=lp, users_9_kgh=mp9, m_911_kgh=a["m_911_kgh"],
                            kappa_329d001_us_cm=kappa, ai_329701_us_cm=pv, ai_329701_over=over,
                            ai_329701_h1=h1, ai_329701_h2=h2)


def steps() -> dict:
    """The two steps by unit; `ureasim.engine.plant` puts them in V1's order."""
    return {
        "329": Step("329", "steam network", "329", 4, {
            "strip_kgh": Result("322E001", "strip_kgh"),
            "raise_kgh": Result("322E002", "raise_kgh"),
            "leak": Result("322E002", "holdup.leak"),
            "users_lp_kgh": Tear("steam_users_lp_kgh"),
            "users_9_kgh": Tear("steam_users_9_kgh"),
            "c003_kgh": Tear("m_911_kgh"),
            "trip_21_2": State("SYN-TRIPS", "trip_21_2")}, _network),
        USERS: Step(USERS, "steam users' draws", "329", 31, {
            "q_323e002_kw": Result("323C003", "q_e002_kw"),
            "q_323e010_kw": Result("323F010", "q_e010_kw"),
            "q_324e001_kw": Result("324E001", "q_kw"),
            "q_324e003_kw": Result("324E003", "q_kw"),
            "m_924_kgh": Result(MOTIVE, "m_924_kgh"), "m_927_kgh": Result(MOTIVE, "m_927_kgh"),
            "m_929_kgh": Result(MOTIVE, "m_929_kgh"),
            "m_931_kgh": Result("328C004", "m_931_kgh"),
            "m_flood_kgh": Result("322C001", "m_flood_kgh"),
            "m_trace_kgh": Result("322C001", "m_trace_kgh"),
            "m_911_kgh": Result("328C003", "m_911_kgh"),
            "leak": Result("322E002", "holdup.leak")}, _users),
    }


def tears() -> tuple[DeclaredTear, ...]:
    """The network's one-tick reads: every user steps after it."""
    reason = "V1 steps the network in section 4, ahead of every user it supplies (B-68)"
    return (DeclaredTear(Tear("steam_users_lp_kgh"), "329", reason),
            DeclaredTear(Tear("steam_users_9_kgh"), "329", reason),
            DeclaredTear(Tear("m_911_kgh"), "329", "FT-329403 reads 328C003's steam, section 18"),
            DeclaredTear(State("SYN-TRIPS", "trip_21_2"), "329",
                         "trip 21.2 is evaluated at the foot of V1's tick, section 34"))
