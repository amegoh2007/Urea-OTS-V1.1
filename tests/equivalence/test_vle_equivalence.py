"""V1 <-> V1.1 equivalence for the NH3-CO2-H2O liquor VLE.

Gate: exact agreement on the interpolated activities, the partial-pressure vector, the
bubble pressure and the bubble temperature — cold and warm start.

Both sides build (or load) a 1215-node activity table by continuation. The build is about
10 s and is cached, so this module is slower than the rest of the suite on a first run and
fast afterwards.

The states swept are the plant's own, and the three validated 323 stages are asserted
against the PFD as well as against V1 — so a port that agreed with V1 but had lost the
validation would still fail here.
"""

from __future__ import annotations

import pytest

from ureasim.thermo import vle as new
from tests.equivalence.v1_loader import load, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

#: The three stages whose bubble pressures are validated against the PFD.
#: (name, mass-% liquor, T [C], P_PFD [bar a], documented error [%])
VALIDATED_STAGES = [
    ("323C003", {"Urea": 68.74, "Biuret": 0.36, "NH3": 2.13, "CO2": 1.05, "H2O": 27.72},
     135.0, 4.10, 6.1),
    ("323F004", {"Urea": 71.74, "Biuret": 0.37, "NH3": 0.88, "CO2": 0.66, "H2O": 26.35},
     106.0, 1.13, 15.0),
    ("323F010", {"Urea": 80.00, "Biuret": 0.42, "NH3": 0.08, "CO2": 0.02, "H2O": 19.48},
     99.0, 0.46, 1.8),
]

#: Liquors spanning the whole tabulated band, including the two HP-loop states that the
#: molality grid could not represent at all.
LIQUORS = [
    ("323C003", VALIDATED_STAGES[0][1], 135.0),
    ("323F004", VALIDATED_STAGES[1][1], 106.0),
    ("323F010", VALIDATED_STAGES[2][1], 99.0),
    # 328 desorption: dilute, hot.
    ("328C004", {"Urea": 0.8, "NH3": 1.4, "CO2": 0.9, "H2O": 96.9}, 143.0),
    ("328C003", {"Urea": 2.0, "NH3": 0.6, "CO2": 0.4, "H2O": 97.0}, 200.0),
    # 322R001 overflow: s = 0.688 — off the old molality grid by 6x.
    ("322R001", {"Urea": 31.0, "Biuret": 0.6, "NH3": 33.0, "CO2": 21.0, "H2O": 14.4},
     183.0),
    # A liquor carrying the four permanent gases at a realistic DISSOLVED level.
    # Their Henry constants are of order 1e5 bar, so a plausible-looking 1 wt% would put
    # the bubble pressure in the thousands of bar; real dissolved inerts are tens of ppm.
    ("322-inerts", {"Urea": 31.0, "Biuret": 0.6, "NH3": 33.0, "CO2": 21.0, "H2O": 14.4,
                    "N2": 0.001, "O2": 0.0003, "CH4": 0.00025, "H2": 0.00008}, 183.0),
]


@pytest.fixture(scope="module")
def v1_vle():
    module = load("vle_nh3co2h2o")
    module.prime()
    return module


@pytest.fixture(scope="module", autouse=True)
def primed():
    new.prime()


# --------------------------------------------------------------------------------------
# Table and envelope
# --------------------------------------------------------------------------------------

def test_model_name_and_envelope_match(v1_vle):
    assert new.MODEL_NAME == v1_vle.MODEL_NAME
    assert new.VALID_PRESSURE_BARA == v1_vle.VALID_PRESSURE_BARA
    assert new.MW == v1_vle.MW
    assert new.NONVOLATILE == v1_vle.NONVOLATILE
    assert new.INERTS == v1_vle.INERTS
    assert new.envelope() == v1_vle.envelope()


def test_every_node_converged():
    """A cleared node flag means the interpolator must refuse cells touching it.

    V1 measured 1215/1215; anything less is a regression in the continuation march, not an
    acceptable loss.
    """
    stats = new.build_stats()
    assert stats["nodes"] == 1215
    assert stats["failed"] == 0


# --------------------------------------------------------------------------------------
# Coordinates
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("name,w,t_c", LIQUORS)
def test_coords_and_loadings_bit_exact(v1_vle, name, w, t_c):
    assert new.coords(w) == v1_vle.coords(w)
    assert new.loadings(w) == v1_vle.loadings(w)


def test_loadings_still_names_the_old_failure(v1_vle):
    """`loadings` is kept as the diagnostic that explains WHY the molality grid failed.

    For the 322E003 feed it returns numbers far off the top of the old table, which is a
    far more legible way to say "no water left" than "s = 0.953".
    """
    feed = {"Urea": 5.0, "NH3": 55.0, "CO2": 38.0, "H2O": 2.0}
    n_load, c_load = new.loadings(feed)
    assert n_load > 100.0 and c_load > 20.0
    assert (n_load, c_load) == v1_vle.loadings(feed)


def test_waterless_liquor_does_not_divide_by_zero():
    """`coords` works from mole counts, so a dry liquor reports s = 1.0 rather than inf."""
    s, f = new.coords({"NH3": 60.0, "CO2": 40.0, "H2O": 0.0})
    assert s == 1.0
    assert new.in_grid({"NH3": 60.0, "CO2": 40.0, "H2O": 0.0}, 183.0) is False


# --------------------------------------------------------------------------------------
# Partial pressures and bubble point
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("name,w,t_c", LIQUORS)
def test_partial_pressures_bit_exact(v1_vle, name, w, t_c):
    a = new.partial_pressures_bara(w, t_c)
    b = v1_vle.partial_pressures_bara(w, t_c)
    assert a.keys() == b.keys()
    for k in a:
        assert a[k] == b[k], f"{name}/{k}"


@pytest.mark.parametrize("name,w,t_c", LIQUORS)
def test_bubble_pressure_bit_exact(v1_vle, name, w, t_c):
    assert new.bubble_p_bara(w, t_c) == v1_vle.bubble_p_bara(w, t_c)


@pytest.mark.parametrize("name,w,t_c", LIQUORS)
def test_in_grid_agrees(v1_vle, name, w, t_c):
    assert new.in_grid(w, t_c) == v1_vle.in_grid(w, t_c)


def test_bubble_pressure_is_the_sum_of_its_parts():
    """The bubble point and the flash K-values cannot be allowed to disagree."""
    for _name, w, t_c in LIQUORS:
        p = new.partial_pressures_bara(w, t_c)
        total = p["NH3"] + p["CO2"] + p["H2O"] + sum(p[k] for k in new.INERTS)
        assert new.bubble_p_bara(w, t_c) == pytest.approx(total, rel=1e-15)


@pytest.mark.parametrize("name,w,t_c,p_pfd,err_pct", VALIDATED_STAGES)
def test_validated_stages_reproduce_the_documented_error(name, w, t_c, p_pfd, err_pct):
    """The As-Built reference quotes +6.1 / +15.0 / +1.8 %.

    Asserting the documented error, not just agreement with V1, means a port that agreed
    with V1 but had silently lost the validation would still fail.
    """
    p = new.bubble_p_bara(w, t_c)
    assert 100.0 * (p / p_pfd - 1.0) == pytest.approx(err_pct, abs=0.15)
    assert new.in_grid(w, t_c) is True


# --------------------------------------------------------------------------------------
# Bubble temperature — cold and warm start
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("name,w,t_c", LIQUORS)
def test_bubble_temperature_cold_start_bit_exact(v1_vle, name, w, t_c):
    p = new.bubble_p_bara(w, t_c)
    assert new.bubble_t_c(w, p) == v1_vle.bubble_t_c(w, p)


@pytest.mark.parametrize("name,w,t_c", LIQUORS)
def test_bubble_temperature_warm_start_bit_exact(v1_vle, name, w, t_c):
    p = new.bubble_p_bara(w, t_c)
    for guess in (t_c, t_c - 8.0, t_c + 8.0):
        assert new.bubble_t_c(w, p, t_guess=guess) == v1_vle.bubble_t_c(
            w, p, t_guess=guess)


def test_warm_start_at_the_anchor_returns_the_anchor_unchanged():
    """What makes the design point bit-exact.

    A guess already within the ln-P tolerance is returned untouched, so the departure form
    `T_des + [T_bub(live) - T_bub(design)]` is identically zero on a design-state tick.
    """
    _name, w, t_c = LIQUORS[0]
    p = new.bubble_p_bara(w, t_c)
    assert new.bubble_t_c(w, p, t_guess=t_c) == t_c


def test_bubble_pressure_rises_monotonically_with_temperature():
    """Uniqueness of the root, on which both solvers depend."""
    for _name, w, t_c in LIQUORS:
        pressures = [new.bubble_p_bara(w, t) for t in (t_c - 20, t_c - 10, t_c, t_c + 10)]
        assert pressures == sorted(pressures)


def test_bubble_point_responds_to_composition():
    """The defect that condemned the pure-water anchor.

    A water-only model gave a derivative of EXACTLY ZERO with respect to NH3 and CO2
    loading — so no stripping, absorption or recycle upset could move a column's bubble
    point. Here, moving one point of water to ammonia at 323C003 lifts the bubble pressure
    from 4.3516 to 4.4262 bar a, about +1.7 %.
    """
    base = {"Urea": 68.74, "Biuret": 0.36, "NH3": 2.13, "CO2": 1.05, "H2O": 27.72}
    richer = dict(base, NH3=3.13, H2O=26.72)
    p_base = new.bubble_p_bara(base, 135.0)
    p_rich = new.bubble_p_bara(richer, 135.0)
    assert p_rich > p_base
    assert 100.0 * (p_rich / p_base - 1.0) == pytest.approx(1.7, abs=0.3)


def test_permanent_gas_solubility_has_a_turning_point():
    """IAPWS G7-04's whole reason for existing, and the reason a van 't Hoff fit was refused.

    Permanent-gas solubility in water passes through a MINIMUM near 80-100 C — so the
    Henry constant passes through a MAXIMUM there and falls again above it. A two-parameter
    van 't Hoff extrapolated from 25 C data has it rising monotonically and is badly wrong
    by 183 C, the loop's own temperature.
    """
    from ureasim.thermo import properties as props
    h = [props.henry_inert_MPa("N2", t + 273.15) for t in (40, 80, 100, 150, 183, 210)]
    assert h[1] == max(h), "the Henry constant must peak near 80 C"
    assert h[-1] < h[1] * 0.5, "and fall well below that peak by 210 C"
