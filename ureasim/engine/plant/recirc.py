"""Unit 323's seven steps: the liquor train 323C003 -> 323F004 -> 323F010 -> 323D002, the two LP
condensers, 323E003 / 323D001 and 323E011 / 323D011, and 323P001B's standby faceplate, wired as V1
steps them.

What this is
------------
The schedule's entries for V1's ``step_sim`` sections 7 to 13 (the liquor train, each stage's inlet
line its own), 23 (323E003 / 323D001), 24 (323E011 / 323D011) and 33 (SIC-323902, the standby's
faceplate, stepped on its own output for liveness). Each liquor stage takes its upstream stage's
drain of THIS tick and reads its downstream neighbour's pressure as that neighbour left it on the
tick before — 323C003 reads 323F004 and 323D001, 323F004 reads 323E011 and 323F010, 323F010 reads
324E002's shell (stage 1's vacuum) — the tears V1's order makes. The LP header is the steam
network's after its step this tick (section 4).

Three routings are the process engineer's, and not V1's:

* **The stripper's blow-through reaches 323C003** (handoff A-16, 2026-10-03). The gas an uncovered LV-322501
  passes loads the column's pressure, SV32351 / SV32352 relieve it at their set pressure, and what
  is left leaves overhead to 323E003 with the column's own gas. V1 sends it straight to 323E003.
* **A full 328D001 overflows into 323E011** up its vent line (handoff A-15), the same tick: the
  drum steps in section 20, the condenser in 24. **A full 323F004 does too**, up its vapour line
  (handoff A-22, decided 2026-10-17): the drum steps in section 9.
* **PFD 734 enters 323E003** (handoff B-37, decided 2026-10-10): FIC-323401's ammonia water from
  328D003, which steps before the condenser, the same tick, as its departure from the PFD's row
  (B-94, decided 2026-10-14). V1 books it into no unit.

The two LP condensers take their inlets' producers' live temperatures (handoff B-31, decided
2026-10-16): 323E003 323C003's, 328D001's and 322C001's of this tick and 323E011's of the tick
before; 323E011 323F004's, 323E003's, 328D001's and 328D003's compartment II's, all of this tick.

Source: V1 ``backend/main.py`` ``step_sim`` 8183-8664, 9513-9664, 10081; the units' own modules
(`ureasim.units.recirc`) and their equivalence tests, which carry V1's call sites line for line.
"""

from __future__ import annotations

from ureasim.engine.schedule import DeclaredTear, Operator, Result, State, Step, Tear
from ureasim.units.recirc import flash_condenser as fc
from ureasim.units.recirc import flash_tank as ft
from ureasim.units.recirc import lp_carbamate_condenser as lpcc
from ureasim.units.recirc import pre_evaporator as pe
from ureasim.units.recirc import rectifying_column as rc
from ureasim.units.recirc import solution_tank as st
from ureasim.units.synthesis.stripper_sump import TOP_GAS_MW_FALLBACK

__all__ = ["units", "steps", "tears"]


def units() -> tuple[dict, dict]:
    """The six units and their controllers, and the standby's faceplate, seeded on the design."""
    return ({"323C003": rc.RectifyingColumn(), "323F004": ft.FlashTank(),
             "323F010": pe.PreEvaporator(), "323D002": st.SolutionTank(),
             "323E003": lpcc.LpCarbamateCondenser(), "323E011": fc.FlashCondenser()},
            {"323C003": (rc.tic_323007(), rc.pic_329202(), rc.lic_323501()),
             "323F004": (ft.lic_323505(),),
             "323F010": (pe.tic_323012(), pe.pic_329208()),
             "323D002": (st.lic_323507(), st.fic_324401()),
             "323E003": (lpcc.pic_323202(), lpcc.lic_323502(), lpcc.sic_323901(),
                         lpcc.tic_323013()),
             "323E011": (fc.pic_323203(), fc.lic_323503(), fc.fic_323418()),
             "SIC-323902": (lpcc.sic_323902(),)})


def _323c003(plant, a, dt):
    return plant.units["323C003"].step(
        *plant.loops["323C003"], a["drain_kgh"], a["tt_323001_c"], a["bottoms_mass_pct"],
        a["tt_322004_c"], a["p_lp_bara"], a["p_f004_bara"], a["p_d001_bara"], dt,
        blow_in_kgh=a["blow_in_kgh"], blow_mw=a["blow_mw"] or TOP_GAS_MW_FALLBACK)


def _323f004(plant, a, dt):
    return plant.units["323F004"].step(
        *plant.loops["323F004"], a["drain_kgh"], a["drain_t_c"], a["drain_w"], a["p_e011_bara"],
        a["p_f010_bara"], dt)


def _323f010(plant, a, dt):
    return plant.units["323F010"].step(
        *plant.loops["323F010"], a["drain_kgh"], a["drain_t_c"], a["drain_w"], a["blow_kgh"],
        a["blow_kmolh"], a["blow_y"], a["hic_323605_pct"], a["p_lp_bara"], a["p_324e002_bara"],
        dt)


def _323d002(plant, a, dt):
    return plant.units["323D002"].step(
        *plant.loops["323D002"], a["drain_kgh"], a["drain_t_c"], a["drain_w"], a["recycle_kgh"],
        a["recycle_t_c"], dict(a["recycle_w"]), a["tie_open"], dt)


def _323e003(plant, a, dt):
    # What leaves 323C003 overhead: its head space's gas, less what SV32351 / SV32352 relieved
    # (handoff A-16); the fraction is exactly 1.0 with the valves shut.
    f = a["overhead_frac"]
    return plant.units["323E003"].step(
        *plant.loops["323E003"], a["m_305_kgh"] * f, a["m_flash_gas_kgh"] * f,
        a["m_heater_gas_kgh"] * f, a["blow_322501_kgh"] * f, a["blow_323501_kgh"],
        a["m_718b_kgh"], a["m_776_kgh"], a["p_e011_bara"], dt, m_734_kgh=a["m_734_kgh"],
        tw_pump_running=bool(a["tw_running"]), t_c003_c=a["t_c003_c"], t_e011_c=a["t_e011_c"], t_d001_c=a["t_d001_c"],
        t_c001_c=a["t_c001_c"])


def _323e011(plant, a, dt):
    return plant.units["323E011"].step(
        *plant.loops["323E011"], a["m_701_kgh"], a["blow_505_kgh"], a["blow_501_kgh"],
        a["m_786_kgh"], a["m_321_kgh"], a["m_402_kgh"], dt,
        m_d001_over_kgh=a["m_d001_over_kgh"], t_d001_over_c=a["t_d001_c"],
        m_f004_over_kgh=a["m_f004_over_kgh"], t_f004_c=a["t_f004_c"], t_e003_c=a["t_e003_c"], t_d003_ii_c=a["t_d003_ii_c"])


def _sic_323902(plant, a, dt):
    loop = plant.loops["SIC-323902"][0]
    return loop.step(loop.op, dt)


def steps() -> dict:
    """The six steps by unit; `ureasim.engine.plant` puts them in V1's order."""
    c003, f004, f010 = "323C003", "323F004", "323F010"
    return {
        c003: Step(c003, "rectifying column and 323E002", "323", 7, {
            "drain_kgh": Result("322E001", "sump.drain_kgh"),
            "tt_323001_c": Result("322E001", "sump.tt_323001_c"),
            "bottoms_mass_pct": Result("322E001", "stripper.bot_mass_pct"),
            "tt_322004_c": Result("322E001", "sump.tt_322004_c"),
            "blow_in_kgh": Result("322E001", "sump.blowthrough_kgh"),
            "blow_mw": Result("322E001", "stripper.top_mw"),
            "p_lp_bara": State("329", "p_lp_bara"),
            "p_f004_bara": State(f004, "p_bara"),
            "p_d001_bara": State("323E003", "p_bara")}, _323c003),
        f004: Step(f004, "flash tank", "323", 9, {
            "drain_kgh": Result(c003, "m_314_kgh"), "drain_t_c": Result(c003, "drain_t_c"),
            "drain_w": Result(c003, "drain_w"),
            "p_e011_bara": State("323E011", "p_bara"),
            "p_f010_bara": State(f010, "p_bara")}, _323f004),
        f010: Step(f010, "pre-evaporator and 323E010", "323", 11, {
            "drain_kgh": Result(f004, "m_319_kgh"), "drain_t_c": Result(f004, "drain_t_c"),
            "drain_w": Result(f004, "drain_w"), "blow_kgh": Result(f004, "blowthrough_kgh"),
            "blow_kmolh": Result(f004, "blowthrough_kmolh"),
            "blow_y": Result(f004, "blowthrough_y"),
            "hic_323605_pct": Operator("HIC-323605"),
            "p_lp_bara": State("329", "p_lp_bara"),
            "p_324e002_bara": State("324E001", "p_bara")}, _323f010),
        "323D002": Step("323D002", "urea solution tank", "323", 13, {
            "drain_kgh": Result(f010, "m_317_kgh"), "drain_t_c": Result(f010, "drain_t_c"),
            "drain_w": Result(f010, "drain_w"),
            "recycle_kgh": Tear("m_recycle_324_kgh"), "recycle_t_c": Tear("t_recycle_324_c"),
            "recycle_w": Tear("w_recycle_324"),
            "tie_open": Operator("HV-323D002-TIE")}, _323d002),
        "323E003": Step("323E003", "LP carbamate condenser and 323D001", "323", 23, {
            "m_305_kgh": Result(c003, "m_305_kgh"),
            "m_flash_gas_kgh": Result(c003, "m_flash_gas_kgh"),
            "m_heater_gas_kgh": Result(c003, "m_heater_gas_kgh"),
            "blow_322501_kgh": Result(c003, "blow_in_kgh"),
            "overhead_frac": Result(c003, "overhead_frac"),
            "blow_323501_kgh": Result(c003, "blowthrough_kgh"),
            "m_718b_kgh": Tear("m_718b_kgh"),
            "m_776_kgh": Result("328D001", "m_776_kgh"),
            "m_734_kgh": Result("328D003", "m_734_kgh"),
            "p_e011_bara": State("323E011", "p_bara"), "tw_running": Operator("329P003"),
            "t_c003_c": Result(c003, "t_c"), "t_e011_c": State("323E011", "t_c"),
            "t_d001_c": Result("328D001", "t_c"),
            "t_c001_c": Result("322C001", "t_c")}, _323e003),
        "323E011": Step("323E011", "LP condenser and 323D011", "323", 24, {
            "m_701_kgh": Result(f004, "m_701_kgh"),
            "blow_505_kgh": Result(f004, "blowthrough_kgh"),
            "blow_501_kgh": Result(c003, "blowthrough_kgh"),
            "m_786_kgh": Result("328D001", "m_786_kgh"),
            "m_321_kgh": Result("323E003", "m_321_kgh"),
            "m_402_kgh": Result("328D003", "m_791_kgh"),
            "m_d001_over_kgh": Result("328D001", "m_overflow_kgh"),
            "t_d001_c": Result("328D001", "t_c"),
            "m_f004_over_kgh": Result(f004, "m_overflow_kgh"),
            "t_f004_c": Result(f004, "t_c"), "t_e003_c": Result("323E003", "t_c"),
            "t_d003_ii_c": Result("328D003", "t_ii_c")}, _323e011),
        "SIC-323902": Step("SIC-323902", "323P001B's standby faceplate", "323", 33, {},
                           _sic_323902),
    }


def tears() -> tuple[DeclaredTear, ...]:
    """The one-tick reads unit 323's steps make, each with the reason V1's order gives it."""
    return (
        DeclaredTear(State("323F004", "p_bara"), "323C003",
                     "LV-323501 lets down into 323F004, which steps after 323C003 (V1 section 9)"),
        DeclaredTear(State("323E003", "p_bara"), "323C003",
                     "323C003's pressure rides 323D001's, which steps in section 23"),
        DeclaredTear(State("323E011", "p_bara"), "323F004",
                     "323F004 vents to 323E011, which steps in section 24"),
        DeclaredTear(State("323F010", "p_bara"), "323F004",
                     "LV-323505 lets down into 323F010, which steps after 323F004"),
        DeclaredTear(State("324E001", "p_bara"), "323F010",
                     "HV-323605 discharges into 324E002's shell, stage 1's vacuum, which steps "
                     "in section 26 (the pre-evaporator's explicit tear)"),
        DeclaredTear(Tear("m_recycle_324_kgh"), "323D002",
                     "LV-324501B's recycle from stage 2, which steps in section 29 (R324_recyc)"),
        DeclaredTear(Tear("t_recycle_324_c"), "323D002", "the recycle's temperature, likewise"),
        DeclaredTear(Tear("w_recycle_324"), "323D002", "the recycle's composition, likewise"),
        DeclaredTear(Tear("m_718b_kgh"), "323E003",
                     "323D011's condensate through FV-323418, 323E011 stepping after 323E003 "
                     "(R3232_718B)"),
        DeclaredTear(State("323E011", "p_bara"), "323E003",
                     "PV-323202 vents 323D001 to 323E011, which steps after 323E003"),
        DeclaredTear(State("323E011", "t_c"), "323E003",
                     "718B's temperature, 323D011's condensate, likewise (B-31)"),
    )
