"""V1 <-> V1.1 equivalence for the flowsheet primitives in `ureasim.core`.

What is being proved
--------------------
The core layer carries no correlations of its own — it is the plumbing every unit operation
will be built on — so the risk is not a wrong coefficient. It is a *convention* drifting:
an argument order swapped, a cap changed, a limiter's NaN behaviour "tidied", a rounding
digit lost from a published record. Each of those would pass unit tests and change the
plant.

So this file pins the conventions against V1 directly:

  * both `clamp` forms, including what each does with a NaN;
  * the packet's closure check, its mixing rule and its sensible-enthalpy term;
  * the dead-time equation, both transit-time forms with their different caps and argument
    orders, and the full-line vs empty-line seeding of the two transport functions;
  * the vapour-space pressure equation, term by term;
  * the published stream record, field for field, including its rounding.

`backend/main.py` cannot be imported — it builds a FastAPI app and a full plant state at
import — so the three `make_stream` constructors are compared by executing V1's own
function source in a controlled namespace. That is V1's code running, not a re-derivation
of it.
"""

from __future__ import annotations

import ast
import math

import pytest

from ureasim.core import node, numeric, packet, signal, stream, transport
from ureasim.data import design_point as dp
from ureasim.data import process_routes as routes
from tests.equivalence import routes_switch
from tests.equivalence.v1_loader import V1_BACKEND, load, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)


@pytest.fixture(scope="module")
def v1_consequence():
    return load("consequence")


@pytest.fixture(scope="module")
def v1_hydraulics():
    return load("hydraulics")


# --------------------------------------------------------------------------------------
# Limiters
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("x", [-5.0, 0.0, 0.5, 1.0, 50.0, 100.0, 101.0])
def test_both_clamp_forms_agree_on_ordinary_numbers(x, v1_consequence):
    assert numeric.clamp(x, 0.0, 100.0) == max(0.0, min(100.0, x))
    assert numeric.clamp_preserving_nan(x, 0.0, 100.0) == v1_consequence.clamp(x, 0.0, 100.0)
    assert numeric.clamp(x, 0.0, 100.0) == numeric.clamp_preserving_nan(x, 0.0, 100.0)


def test_the_two_clamp_forms_differ_on_a_nan_and_that_is_the_reason_both_exist():
    """V1's `main.py` limiter pins a NaN to the upper bound; `consequence.py`'s passes it.

    Neither is "the" behaviour. Merging them would silently change one family of call
    sites, so the difference is pinned here instead.
    """
    nan = float("nan")
    assert numeric.clamp(nan, 0.0, 100.0) == 100.0
    assert math.isnan(numeric.clamp_preserving_nan(nan, 0.0, 100.0))


# --------------------------------------------------------------------------------------
# Stream packets
# --------------------------------------------------------------------------------------

#: A 323C003 bottoms cut and a 328 condensate, as mass fractions.
LIQUORS = [
    ({"Urea": 0.6874, "H2O": 0.2450, "NH3": 0.0500, "CO2": 0.0150, "Biuret": 0.0026}, 135.0, 2.5),
    ({"H2O": 0.9800, "NH3": 0.0150, "CO2": 0.0050}, 61.0, 4.1),
]


@pytest.mark.parametrize("w,t_c,cp", LIQUORS)
@pytest.mark.parametrize("m_kgh", [1.0, 1234.5, 130482.0])
def test_packet_construction_matches_v1(w, t_c, cp, m_kgh, v1_consequence):
    mine = packet.packet_from_mass_fraction(m_kgh, t_c, w, cp)
    tot_w = sum(v for v in w.values() if v > 0.0)
    comp = {k: m_kgh * v / tot_w for k, v in w.items() if v > 0.0}
    theirs = v1_consequence.make_stream_packet(sum(comp.values()), comp, t_c, cp)

    assert mine.mass_kgh == theirs.mass_kgh
    assert mine.temperature_c == theirs.temperature_c
    assert mine.cp_kj_kgk == theirs.cp_kj_kgk
    assert mine.component_kgh == theirs.component_kgh
    assert mine.mass_fraction == theirs.mass_fraction
    assert mine.sensible_kw == theirs.sensible_kw


def test_a_packet_with_an_inconsistent_total_is_refused(v1_consequence):
    """The closure check is the whole reason the type exists. Both refuse identically."""
    comp = {"H2O": 100.0, "NH3": 10.0}
    with pytest.raises(ValueError):
        packet.make_stream_packet(200.0, comp, 60.0, 4.0)
    with pytest.raises(ValueError):
        v1_consequence.make_stream_packet(200.0, comp, 60.0, 4.0)


def test_a_dry_line_gives_the_empty_packet_rather_than_raising():
    """Reachable from any upset that takes a transported line to exactly zero flow."""
    assert packet.packet_from_mass_fraction(0.0, 135.0, {"H2O": 1.0}, 4.0) is packet.ZERO_PACKET
    assert packet.packet_from_mass_fraction(100.0, 135.0, {}, 4.0) is packet.ZERO_PACKET


def test_a_non_finite_temperature_drops_the_packet_instead_of_killing_the_tick():
    """Deep in a collapse a stage temperature can go non-finite.

    `make_stream_packet` raises on it — correctly, it is a real defect — but the transport
    layer is a diagnostic consumer and must not be the thing that takes the plant down.
    """
    assert packet.packet_from_mass_fraction(
        100.0, float("nan"), {"H2O": 1.0}, 4.0) is packet.ZERO_PACKET


def test_a_non_positive_heat_capacity_is_floored_not_dropped():
    p = packet.packet_from_mass_fraction(100.0, 60.0, {"H2O": 1.0}, 0.0)
    assert p.cp_kj_kgk == 0.1


def test_mixing_matches_v1_and_conserves_sensible_enthalpy(v1_consequence):
    a = packet.packet_from_mass_fraction(1000.0, 140.0, {"Urea": 0.8, "H2O": 0.2}, 2.4)
    b = packet.packet_from_mass_fraction(500.0, 45.0, {"H2O": 0.95, "NH3": 0.05}, 4.1)
    mine = packet.mix_stream_packets(a, b)

    a1 = v1_consequence.make_stream_packet(a.mass_kgh, a.component_kgh, a.temperature_c,
                                           a.cp_kj_kgk)
    b1 = v1_consequence.make_stream_packet(b.mass_kgh, b.component_kgh, b.temperature_c,
                                           b.cp_kj_kgk)
    theirs = v1_consequence.mix_stream_packets(a1, b1)

    assert mine.mass_kgh == theirs.mass_kgh
    assert mine.temperature_c == theirs.temperature_c
    assert mine.cp_kj_kgk == theirs.cp_kj_kgk
    assert mine.component_kgh == theirs.component_kgh
    # The mixed temperature is an ENERGY balance, not a flow-weighted average: the two
    # differ whenever the streams have different heat capacities, and here they do.
    assert mine.sensible_kw == pytest.approx(a.sensible_kw + b.sensible_kw, rel=1e-12)
    flow_weighted = (a.mass_kgh * a.temperature_c
                     + b.mass_kgh * b.temperature_c) / (a.mass_kgh + b.mass_kgh)
    assert abs(mine.temperature_c - flow_weighted) > 1.0


def test_the_solution_species_molar_masses_are_one_table():
    """V1 keeps MW_SOL beside MW_COMP; here the six solution species read one table.

    That is only admissible because the values are identical, which this asserts against
    V1's own source text rather than against a copy of it.
    """
    from ureasim.thermo.domains import MW
    text = (V1_BACKEND / "main.py").read_text(encoding="utf-8", errors="replace")
    start = text.index("MW_SOL = {")
    mw_sol = ast.literal_eval(text[start + len("MW_SOL = "):text.index("}", start) + 1])
    assert tuple(mw_sol) == packet.SOLUTION_SPECIES
    for sp, value in mw_sol.items():
        assert MW[sp] == value


# --------------------------------------------------------------------------------------
# Transport
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("volume_m3,flow_kgh,rho", [
    (0.4124, 130482.0, 1150.0),
    (0.2747, 105918.0, 1140.0),
    (1.0, 1.0, 1000.0),        # a nearly stalled line: must hit the cap, not infinity
    (0.5, 0.0, 1000.0),
])
def test_packet_transit_time_matches_v1(volume_m3, flow_kgh, rho, v1_consequence):
    assert (transport.packet_transport_time_s(volume_m3, flow_kgh, rho)
            == v1_consequence.transport_time_s(volume_m3, flow_kgh, rho))


@pytest.mark.parametrize("v_line,rho,mdot", [
    (5234.0, 1.0, 54618.0),    # the CO2 feed line, expressed as a back-solved inventory
    (0.4124, 1150.0, 130482.0),
    (0.4124, 1150.0, 0.0),
])
def test_line_residence_time_matches_v1(v_line, rho, mdot, v1_hydraulics):
    assert (transport.line_residence_time_s(v_line, rho, mdot)
            == v1_hydraulics.transport_time_s(v_line, rho, mdot))


def test_the_two_transit_time_forms_have_different_caps_and_that_is_intentional():
    """1800 s against 3600 s. Merging them would re-cap one family of call sites."""
    assert transport.packet_transport_time_s(1.0, 0.0, 1000.0) == 1800.0
    assert transport.line_residence_time_s(1.0, 1000.0, 0.0) == 3600.0


@pytest.mark.parametrize("dn_mm,length_m", [(187.1, 15.0), (187.1, 40.0), (0.0, 10.0)])
def test_pipe_volume_matches_v1(dn_mm, length_m, v1_consequence, v1_hydraulics):
    assert (transport.pipe_volume_from_mm(dn_mm, length_m)
            == v1_consequence.pipe_volume_m3(dn_mm, length_m))
    assert (transport.pipe_volume_from_m(dn_mm / 1000.0, length_m)
            == v1_hydraulics.line_volume_m3(dn_mm / 1000.0, length_m))


def test_route_dead_time_matches_v1_at_and_away_from_design(v1_consequence):
    for name, r in routes.PROCESS_ROUTES.items():
        theirs = v1_consequence.ConsequenceRoute(
            r.source, r.destination, r.design_carrier_kgh, r.design_dead_time_s)
        assert r.line_inventory_kg == theirs.line_inventory_kg, name
        for flow in (r.design_carrier_kgh, r.design_carrier_kgh * 0.5, 1.0, 0.0):
            assert r.dead_time_s(flow) == theirs.dead_time_s(flow), (name, flow)


#: V1's route densities [kg/m3], `main.py` 6239-6247 (the last two are R323_D002_RHO).
V1_ROUTE_RHO = {"322E001_TO_323C003": 1150.0, "323C003_TO_323F004": 1140.0,
                "323F004_TO_323F010": 1145.0}


@pytest.mark.parametrize("name, v_port, td_port, td_v1", [
    ("322E001_TO_323C003", 0.8879, 28.17, 21.81),
    ("323C003_TO_323F004", 0.8421, 32.63, 15.98),
    ("323F004_TO_323F010", 0.5677, 23.06, 16.75),
    ("323F010_TO_323D002", 0.6835, 30.54, 36.85),
    ("323D002_TO_324E001", 0.5588, 24.96, 49.13),
])
def test_the_routes_on_the_isometrics_decided_divergence(name, v_port, td_port, td_v1,
                                                          v1_consequence):
    """A-11, decided 2026-10-07. V1 runs each product line on one 187.1 mm bore and a layout
    length (25, 15, 15, 30, 40 m); the port on the as-built isometrics' pipe, each size at its own
    bore. The volumes (m3) and the design dead times (s): the bottoms line, 33.7 m mostly at
    187.1 mm, 28.2 s where V1 has 21.8; the line to 323F004, DN 400 at both vessels, twice V1's;
    the tank to 324E001, 23.7 m of DN 200 and DN 150, half V1's 40 m estimate. The dead times are
    the liquid plug's on the isometrics, V1's law; downstream of a letdown the port's line runs
    two-phase (B-81, `test_the_letdowns_two_phase_lines_decided_divergence`)."""
    from ureasim.data.design_point import R323_D002_RHO
    r = routes.PROCESS_ROUTES[name]
    rho = V1_ROUTE_RHO.get(name, R323_D002_RHO)
    v_v1 = v1_consequence.pipe_volume_m3(187.1, routes_switch.V1_LENGTHS_M[name])
    theirs = v1_consequence.transport_time_s(v_v1, r.design_carrier_kgh, rho)
    plug = v1_consequence.transport_time_s(v_port, r.design_carrier_kgh, rho)
    assert routes.route_volume_m3(name) == pytest.approx(v_port, abs=1e-4)
    assert (plug, theirs) == (pytest.approx(td_port, abs=0.01), pytest.approx(td_v1, abs=0.01))
    if name not in routes.LETDOWN_FLASH:
        assert r.design_dead_time_s == pytest.approx(plug, rel=2e-4)


@pytest.mark.parametrize("name, v_down, x, rho_m, td_plug, td_port", [
    ("322E001_TO_323C003", 0.8331, 0.13145, 25.30, 28.17, 2.32),
    ("323C003_TO_323F004", 0.4941, 0.04179, 16.05, 32.63, 13.75),
    ("323F004_TO_323F010", 0.0292, 0.02780, 10.34, 23.06, 21.88),
])
def test_the_letdowns_two_phase_lines_decided_divergence(name, v_down, x, rho_m, td_plug,
                                                         td_port, v1_consequence):
    """B-81, decided 2026-10-09: downstream of LV-322501, LV-323501 and LV-323505 the line holds
    the valve's flash at the homogeneous two-phase density. V1's law, a liquid plug end to end, on
    the isometrics' volume (s), against the port's: the stripper's bottoms reach 323C003 in 2.3 s
    where the plug takes 28.2 (30.3 m of its 33.7 m after the valve, at 25.3 kg/m3 for 1150); the
    column's bottoms reach 323F004 in 13.8 s for 32.6; the flash tank's liquid 323E010 in 21.9 s
    for 23.1 (LV-323505 sits 1.7 m from the pre-evaporator's inlet)."""
    r = routes.PROCESS_ROUTES[name]
    v = routes.route_volume_m3(name)
    rho_l = V1_ROUTE_RHO[name]
    flash, rho_g = routes.LETDOWN_FLASH[name]
    assert routes.two_phase_volume_m3(name) == pytest.approx(v_down, abs=1e-4)
    assert flash == pytest.approx(x, abs=1e-5)
    assert routes.homogeneous_density(flash, rho_g, rho_l) == pytest.approx(rho_m, abs=0.01)
    assert v1_consequence.transport_time_s(v, r.design_carrier_kgh, rho_l) == pytest.approx(
        td_plug, abs=0.01)
    assert r.design_dead_time_s == pytest.approx(td_port, abs=0.01)
    td = transport.packet_transport_time_s
    assert r.design_dead_time_s == pytest.approx(
        td(v - routes.two_phase_volume_m3(name), r.design_carrier_kgh, rho_l)
        + td(routes.two_phase_volume_m3(name), r.design_carrier_kgh,
             routes.homogeneous_density(flash, rho_g, rho_l)), rel=1e-12)


def test_halving_the_flow_doubles_the_dead_time():
    """The behaviour a fixed FIFO lag cannot produce, and the one a trainee must see."""
    r = routes.route("323F010_TO_323D002")
    full = r.dead_time_s(r.design_carrier_kgh)
    half = r.dead_time_s(r.design_carrier_kgh * 0.5)
    assert half == pytest.approx(2.0 * full, rel=1e-12)


def test_a_process_line_starts_FULL_so_the_design_pin_survives_the_boot(v1_consequence):
    """A line that started empty would starve the 323 train for one dead time on every boot."""
    r = routes.route("323C003_TO_323F004")
    p = packet.packet_from_mass_fraction(r.design_carrier_kgh, 135.0,
                                         {"Urea": 0.69, "H2O": 0.31}, 2.5)
    mine_store: dict = {}
    arrived = transport.transport_process_packet(
        mine_store, "k", p, r, r.design_carrier_kgh, 0.1)
    assert arrived == p

    theirs_route = v1_consequence.ConsequenceRoute(
        r.source, r.destination, r.design_carrier_kgh, r.design_dead_time_s)
    theirs_packet = v1_consequence.make_stream_packet(
        p.mass_kgh, p.component_kgh, p.temperature_c, p.cp_kj_kgk)
    theirs_store: dict = {}
    theirs_arrived = v1_consequence.transport_process_packet(
        theirs_store, "k", theirs_packet, theirs_route, r.design_carrier_kgh, 0.1)
    assert theirs_arrived.mass_kgh == arrived.mass_kgh
    assert theirs_arrived.temperature_c == arrived.temperature_c


def test_a_consequence_line_starts_EMPTY_so_nothing_arrives_before_it_happened():
    r = routes.route("323C003_TO_323F004")
    p = packet.packet_from_mass_fraction(50.0, 135.0, {"Urea": 0.69, "H2O": 0.31}, 2.5)
    store: dict = {}
    assert transport.transport_stream_packet(store, "k", p, r, 50.0, 0.1) is packet.ZERO_PACKET


def test_a_step_arrives_one_dead_time_later_and_matches_v1_tick_for_tick(v1_consequence):
    """The whole point of the layer: the parcel must not teleport.

    Both implementations are driven with the same step at the same sub-steps and compared
    on every tick, so a difference of one sample would fail rather than average out.
    """
    r = routes.route("323C003_TO_323F004")
    theirs_route = v1_consequence.ConsequenceRoute(
        r.source, r.destination, r.design_carrier_kgh, r.design_dead_time_s)

    def mk(t_c):
        return packet.packet_from_mass_fraction(
            r.design_carrier_kgh, t_c, {"Urea": 0.69, "H2O": 0.31}, 2.5)

    dt = 0.1
    mine_store: dict = {}
    theirs_store: dict = {}
    seen_before, seen_after = False, False
    for i in range(600):
        t_c = 135.0 if i < 50 else 145.0
        p = mk(t_c)
        tp = v1_consequence.make_stream_packet(p.mass_kgh, p.component_kgh,
                                               p.temperature_c, p.cp_kj_kgk)
        a = transport.transport_process_packet(
            mine_store, "k", p, r, r.design_carrier_kgh, dt)
        b = v1_consequence.transport_process_packet(
            theirs_store, "k", tp, theirs_route, r.design_carrier_kgh, dt)
        assert a.temperature_c == b.temperature_c, i
        elapsed = (i + 1) * dt
        # The step enters the buffer on the tick it is first seen, which is t = 5.1 s, so
        # it can only be emitted from t = 5.1 + td onward. Asserting against td alone
        # would be off by one tick.
        step_entered_s = 5.1
        if 5.0 < elapsed < step_entered_s + r.design_dead_time_s:
            assert a.temperature_c == 135.0      # the step has not arrived yet
            seen_before = True
        if elapsed > step_entered_s + r.design_dead_time_s + 1.0:
            assert a.temperature_c == 145.0      # and it has now
            seen_after = True
    assert seen_before and seen_after


# --------------------------------------------------------------------------------------
# Nodes
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("p_bara,t_k,v_v,mw,n_gen,n_out", [
    (140.7, 456.15, 12.0, 30.0, 1800.0, 1800.0),     # synthesis loop, balanced
    (4.1, 408.15, 8.0, 20.0, 120.0, 100.0),          # 323C003 rectifier
    (0.33, 403.15, 25.0, 18.02, 900.0, 950.0),       # 324E001, deep vacuum
    (0.0, 400.0, 0.0, 18.0, 10.0, 5.0),              # degenerate: must not raise
])
def test_vessel_dpdt_matches_v1(p_bara, t_k, v_v, mw, n_gen, n_out, v1_hydraulics):
    for dtdt, dvvdt in ((0.0, 0.0), (0.05, 0.0), (0.0, 0.002), (-0.03, -0.001)):
        assert (node.vessel_dpdt(p_bara, t_k, v_v, mw, n_gen, n_out, dtdt, dvvdt)
                == v1_hydraulics.vessel_dpdt(p_bara, t_k, v_v, mw, n_gen, n_out,
                                             dtdt, dvvdt))


def test_a_balanced_node_holds_its_pressure_exactly():
    """The design pin: equal generation and withdrawal must give a literal 0.0."""
    assert node.vessel_dpdt(140.7, 456.15, 12.0, 30.0, 1800.0, 1800.0) == 0.0


def test_a_fuller_vessel_gives_a_stiffer_pressure_response():
    """The coupling the lumped capacitance threw away."""
    empty = node.vapour_volume_m3(50.0, 5_000.0, 1150.0)
    full = node.vapour_volume_m3(50.0, 40_000.0, 1150.0)
    assert full < empty
    assert (abs(node.vessel_dpdt(4.1, 408.15, full, 20.0, 120.0, 100.0))
            > abs(node.vessel_dpdt(4.1, 408.15, empty, 20.0, 120.0, 100.0)))


@pytest.mark.parametrize("v_vessel,m_liq,rho", [
    (50.0, 5000.0, 1150.0), (50.0, 60000.0, 1150.0), (0.0, 100.0, 1000.0),
    (10.0, 100.0, 0.0),
])
def test_vapour_volume_matches_v1(v_vessel, m_liq, rho, v1_hydraulics):
    assert (node.vapour_volume_m3(v_vessel, m_liq, rho)
            == v1_hydraulics.vapour_volume_m3(v_vessel, m_liq, rho))


def test_holdup_integration_reproduces_the_v1_stage_form():
    """`max(M + (in - out)/3600 . dt, 1.0)` — V1 writes this inline at every 323 stage."""
    m, m_in, m_out, dt = 3000.0, 130482.0, 105918.825, 0.1
    assert node.advance_holdup_kg(m, m_in, m_out, dt) == max(
        m + (m_in - m_out) / 3600.0 * dt, 1.0)
    # The floor holds against a total drain.
    assert node.advance_holdup_kg(5.0, 0.0, 1e6, 1.0) == 1.0


def test_level_indication_is_exact_at_the_anchor():
    assert node.level_pct_from_holdup(4200.0, 4200.0, 50.0) == 50.0
    assert node.level_pct_from_holdup(0.0, 4200.0, 50.0) == 0.0
    assert node.level_pct_from_holdup(1e9, 4200.0, 50.0) == 100.0


# --------------------------------------------------------------------------------------
# Published stream records
# --------------------------------------------------------------------------------------

def _v1_stream_module():
    """Execute V1's three `make_stream*` functions in a controlled namespace.

    `backend/main.py` builds a FastAPI app and a full plant state at import, so it cannot
    be imported to check three pure functions. Their source is lifted out of the file by
    AST and executed against V1's own `MW_COMP` (parsed from the same file) and V1's own
    H0 enthalpy module. This is V1's code running, not a paraphrase of it.
    """
    text = (V1_BACKEND / "main.py").read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(text)
    wanted = {"make_stream", "make_stream_mass_pct", "make_stream_mole_pct",
              "_vent_mole_pct"}
    ns = {"h0_enthalpy": load("gap_g6_h0_enthalpy")}
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign) and getattr(stmt.targets[0], "id", "") == "MW_COMP":
            ns["MW_COMP"] = ast.literal_eval(stmt.value)
        if isinstance(stmt, ast.FunctionDef) and stmt.name in wanted:
            exec(compile(ast.Module([stmt], []), "<v1 main.py>", "exec"), ns)
    missing = wanted - set(ns)
    assert not missing, f"could not lift {sorted(missing)} out of V1 main.py"
    assert "MW_COMP" in ns
    return ns


@pytest.fixture(scope="module")
def v1_streams():
    return _v1_stream_module()


def test_the_published_molar_mass_table_matches_v1(v1_streams):
    assert stream.MW_COMP == v1_streams["MW_COMP"]


#: Real stream compositions from the registry: an HP off-gas, a urea product and a
#: condensate, plus an empty line.
STREAM_CASES = [
    ({"NH3": 1580.0, "CO2": 690.0, "H2O": 120.0, "N2": 22.0, "CH4": 3.84, "H2": 2.03},
     43.0, 4.0, "vapor", None),
    ({"Urea": 1544.0, "H2O": 1710.0, "NH3": 280.0, "CO2": 95.0, "Biuret": 3.1},
     99.0, 1.0, "liquid", 1151.0),
    ({"H2O": 5140.0}, 143.0, 3.9, "liquid", 923.28),
    ({}, 40.0, 1.0, "liquid", None),
]


@pytest.mark.parametrize("comp,t_c,p_bara,phase,rho", STREAM_CASES)
def test_make_stream_matches_v1_field_for_field(comp, t_c, p_bara, phase, rho, v1_streams):
    mine = stream.make_stream(comp, t_c, p_bara, "n", "A", "B", phase, rho=rho).as_packet()
    theirs = v1_streams["make_stream"](comp, t_c, p_bara, "n", "A", "B", phase, rho=rho)
    assert mine == theirs


@pytest.mark.parametrize("m_kgh", [0.0, 1234.5, 130482.0])
def test_make_stream_mass_pct_matches_v1(m_kgh, v1_streams):
    row = {"Urea": 68.74, "H2O": 24.50, "NH3": 5.00, "CO2": 1.50, "Biuret": 0.26}
    mine = stream.make_stream_mass_pct(
        m_kgh, row, 106.0, 1.13, "n", "A", "B", "liquid", rho=1210.0).as_packet()
    theirs = v1_streams["make_stream_mass_pct"](
        m_kgh, row, 106.0, 1.13, "n", "A", "B", "liquid", rho=1210.0)
    assert mine == theirs


@pytest.mark.parametrize("m_kgh", [0.0, 990.0, 12040.0])
def test_make_stream_mole_pct_matches_v1(m_kgh, v1_streams):
    row = {"H2O": 55.2, "NH3": 4.1, "CO2": 2.1, "N2": 38.6}
    mine = stream.make_stream_mole_pct(
        m_kgh, row, 45.0, 0.3, "n", "A", "B", "vapor").as_packet()
    theirs = v1_streams["make_stream_mole_pct"](
        m_kgh, row, 45.0, 0.3, "n", "A", "B", "vapor")
    assert mine == theirs


def test_a_mole_percent_row_read_as_mass_percent_is_a_real_error_not_a_rounding_one():
    """Stream 706: 38.6 mol % nitrogen is not 38.6 mass % nitrogen.

    The wrong reading publishes an average molar weight of about 22.4 against the PFD's
    own 24.1 — which is why the two constructors are separate functions.
    """
    row = {"H2O": 55.2, "NH3": 4.1, "CO2": 2.1, "N2": 38.6}
    as_mole = stream.make_stream_mole_pct(990.0, row, 45.0, 0.3, "n", "A", "B", "vapor")
    as_mass = stream.make_stream_mass_pct(990.0, row, 45.0, 0.3, "n", "A", "B", "vapor")
    assert as_mole.MW != as_mass.MW
    assert abs(as_mole.MW - as_mass.MW) > 1.0


def test_vent_composition_is_live_not_tabulated(v1_streams):
    vent = {"H2O": 0.8, "NH3": 0.05, "CO2": 0.02, "N2": 1.4}
    assert stream.vent_mole_pct(vent) == v1_streams["_vent_mole_pct"]({"vent_kmolh": vent})
    assert sum(stream.vent_mole_pct(vent).values()) == pytest.approx(100.0)
    assert stream.vent_mole_pct({"N2": 0.0}) == {"N2": 0.0}


def test_both_composition_bases_come_from_one_vector():
    """A stream cannot be 38.6 % by mole on one line of the display and by mass on the next."""
    rec = stream.make_stream({"NH3": 100.0, "CO2": 50.0, "H2O": 30.0},
                             135.0, 4.1, "n", "A", "B", "liquid")
    # Each published per cent is independently rounded to 3 decimals, so the column sums
    # to 100 to within nine half-units in the last place and not exactly. That is a
    # display convention and V1's; the CLOSED quantity is the component vector below.
    assert sum(rec.mol_pct.values()) == pytest.approx(100.0, abs=0.01)
    assert sum(rec.mass_pct.values()) == pytest.approx(100.0, abs=0.01)
    for sp in stream.MW_COMP:
        assert rec.component_kgh[sp] == rec.component_kmolh[sp] * stream.MW_COMP[sp]


def test_an_unknown_density_stays_none_rather_than_being_invented():
    rec = stream.make_stream({"NH3": 10.0}, 40.0, 1.0, "n", "A", "B", "liquid")
    assert rec.rho is None and rec.vol_m3h is None


def test_an_explicit_enthalpy_is_published_as_plant_reconciled():
    rec = stream.make_stream({"H2O": 100.0}, 143.0, 3.9, "n", "A", "B", "liquid",
                             h_kjkg=602.0)
    assert rec.enthalpy_kJkg == 602.0
    assert rec.enthalpy_basis == "H2_plant_reconciled"


# --------------------------------------------------------------------------------------
# The design flow chain the routes are built on
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("name,value", [
    ("STRIP_BOT_DES_KGH", dp.STRIP_BOT_DES_KGH),
    ("R323_D002_RHO", dp.R323_D002_RHO),
])
def test_design_flow_anchors_match_v1_source(name, value):
    import re
    text = (V1_BACKEND / "main.py").read_text(encoding="utf-8", errors="replace")
    m = re.search(rf"^{re.escape(name)}\s*=\s*([-\d.eE+]+)", text, re.MULTILINE)
    assert m, f"{name} not found in V1 main.py"
    assert value == float(m.group(1))


def test_the_design_chain_closes_stage_by_stage():
    """Each split is the PFD stream over its parent, so the chain closes by construction."""
    assert dp.R323_FEED_DES_KGH == dp.STRIP_BOT_DES_KGH
    assert dp.R323_M314_DES == (1.0 - dp.R323_PHI_V305) * dp.R323_FEED_DES_KGH
    assert dp.R323_M319_DES == (1.0 - dp.R323_PHI_V701) * dp.R323_M314_DES
    assert dp.R323_M317_DES == (1.0 - dp.R323_PHI_VEVAP) * dp.R323_M319_DES
    assert dp.R324_FEED_DES == dp.R323_M317_DES
    # And it lands where the PFD says it should: about 92.7 t/h of 80 % urea solution.
    assert dp.R323_M317_DES == pytest.approx(92749.0, abs=1.0)


# --------------------------------------------------------------------------------------
# Signal conditioning
# --------------------------------------------------------------------------------------

def _v1_signal_module():
    """Lift V1's `_lag1`, `_delay` and `_foptd` out of `main.py` by AST, as above."""
    text = (V1_BACKEND / "main.py").read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(text)
    wanted = {"_lag1", "_delay", "_foptd"}
    ns: dict = {"deque": __import__("collections").deque}
    for stmt in tree.body:
        if isinstance(stmt, ast.FunctionDef) and stmt.name in wanted:
            exec(compile(ast.Module([stmt], []), "<v1 main.py>", "exec"), ns)
    missing = wanted - set(ns)
    assert not missing, f"could not lift {sorted(missing)} out of V1 main.py"
    return ns


@pytest.fixture(scope="module")
def v1_signals():
    return _v1_signal_module()


#: A step, a ramp and a settled hold, on the sub-step sizes the integrator actually uses —
#: including the numerical crumb that would break a sample-counted buffer.
def _drive():
    for i in range(400):
        dt = 0.1 if i % 40 else 1.0e-8
        yield (135.0 if i < 100 else 145.0), dt


@pytest.mark.parametrize("tau_s", [0.0, 2.0, 30.0])
def test_first_order_lag_matches_v1_tick_for_tick(tau_s, v1_signals):
    mine: dict = {}
    theirs: dict = {}
    for target, dt in _drive():
        a = signal.first_order_lag(mine, "k", target, tau_s, dt)
        b = v1_signals["_lag1"](theirs, "k", target, tau_s, dt)
        assert a == b


@pytest.mark.parametrize("td_s", [0.0, 3.0, 345.0])
def test_dead_time_matches_v1_tick_for_tick(td_s, v1_signals):
    mine: dict = {}
    theirs: dict = {}
    for target, dt in _drive():
        a = signal.dead_time(mine, "k", target, td_s, dt)
        b = v1_signals["_delay"](theirs, "k", target, td_s, dt)
        assert a == b


def test_foptd_matches_v1_tick_for_tick(v1_signals):
    mine: dict = {}
    theirs: dict = {}
    for target, dt in _drive():
        a = signal.first_order_plus_dead_time(mine, "k", target, 8.0, 12.0, dt)
        b = v1_signals["_foptd"](theirs, "k", target, 8.0, 12.0, dt)
        assert a == b


def test_a_settled_indication_equals_its_input_exactly():
    """The design pin: a lag and a dead time must both be transparent at steady state."""
    store: dict = {}
    for _ in range(500):
        y = signal.first_order_plus_dead_time(store, "k", 135.0, 8.0, 12.0, 0.1)
    assert y == 135.0


def test_the_dead_time_buffer_is_sized_by_SAMPLES_not_by_td_over_dt():
    """The reason the FIFO is timestamped rather than counted.

    A buffer sized as ``n = td / dt`` would need about 3.45e10 entries for a 345 s feed
    delay on a 1e-8 s remainder sub-step, which is a MemoryError and not a lag. Timestamped,
    200 sub-steps cost 200 entries whatever their size.
    """
    store: dict = {}
    for _ in range(200):
        signal.dead_time(store, "k", 135.0, 345.0, 1.0e-8)
    assert len(store["k"]["buf"]) == 200


def test_the_dead_time_buffer_prunes_once_history_exceeds_the_delay():
    """Superseded samples are dropped, so a long run does not grow without bound."""
    store: dict = {}
    for _ in range(2000):
        signal.dead_time(store, "k", 135.0, 3.0, 0.1)
    # 3 s of history at 0.1 s, plus the one sample the zero-order hold is still emitting.
    assert len(store["k"]["buf"]) <= 32
