"""V1 <-> V1.1 equivalence for the NH3-CO2-H2O Extended UNIQUAC property basis.

Gate: exact agreement. The port split one 778-line module into six, but changed no
expression, no coefficient and no evaluation order, so anything other than bit-for-bit
equality is a transcription error.

States swept are the ones the plant occupies:

    dilute, 25 C              the textbook validation region
    323 recirculation         moderate loading, 99-135 C
    328 desorption            high loading, 139-200 C
    322 synthesis loop        N = 100 mol/kg water at the reactor overflow
                              (reachable only through the seeded Newton — see
                              `speciate`'s "Why m_guess exists")
"""

from __future__ import annotations

import pytest

from ureasim.thermo import properties as new
from tests.equivalence.v1_loader import load, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

#: (N_tot, C_tot) [mol per kg water] and T [K] the plant actually sits at.
LOADINGS = [
    (0.1, 0.05, 298.15),          # dilute reference
    (2.0, 0.8, 298.15),           # weak carbamate wash
    (5.0, 2.0, 372.15),           # 99 C, 323F010 pre-evaporator region
    (8.0, 3.5, 408.15),           # 135 C, 323C003 rectifying column
    (12.0, 5.0, 412.15),          # 139 C, 328C002 desorber bottoms
    (6.0, 2.5, 473.15),           # 200 C, 328C003 hydrolyser
]

TEMPERATURES_K = [273.15, 298.15, 333.15, 372.15, 408.15, 456.15, 473.15]

SPECIES = ["H2O", "H+", "OH-", "NH3(aq)", "NH4+", "CO2(aq)",
           "HCO3-", "CO3--", "NH2COO-"]


@pytest.fixture(scope="module")
def v1():
    return load("props_nh3co2h2o")


# --------------------------------------------------------------------------------------
# Verbatim parameter tables — a transcription check, not a numerical one
# --------------------------------------------------------------------------------------

def test_standard_state_table_identical(v1):
    assert new.STANDARD_STATE == v1.STANDARD_STATE


def test_reactions_identical(v1):
    assert new.REACTIONS == v1.REACTIONS


def test_uniquac_rq_identical(v1):
    assert new.UNIQUAC_RQ == v1.UNIQUAC_RQ


def test_interaction_tables_identical(v1):
    assert new.U0 == v1.U0
    assert new.UT == v1.UT


def test_charge_and_srk_tables_identical(v1):
    assert new.CHARGE == v1.CHARGE
    assert new.SRK_CRIT == v1.SRK_CRIT
    assert new.HENRY_G704 == v1.HENRY_G704
    assert new.B_DH == v1.B_DH
    assert new.R == v1.R
    assert new.T0 == v1.T0
    assert new.M_W == v1.M_W


# --------------------------------------------------------------------------------------
# Standard-state thermodynamics
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("T", TEMPERATURES_K)
@pytest.mark.parametrize("sp", SPECIES)
def test_cp0_and_h0_bit_exact(v1, sp, T):
    assert new.cp0(sp, T) == v1.cp0(sp, T)
    assert new.h0(sp, T) == v1.h0(sp, T)
    assert new.mu0_over_RT(sp, T) == v1.mu0_over_RT(sp, T)


@pytest.mark.parametrize("T", TEMPERATURES_K)
@pytest.mark.parametrize("rx", list(new.REACTIONS))
def test_lnK_and_dH_reaction_bit_exact(v1, rx, T):
    assert new.lnK(rx, T) == v1.lnK(rx, T)
    assert new.pK(rx, T) == v1.pK(rx, T)
    assert new.dH_reaction(rx, T) == v1.dH_reaction(rx, T)


def test_textbook_pk_oracle():
    """The transcription's own oracle: aqueous pKw at 0 C and 60 C.

    Literature values are 14.94 and 13.02. Reproducing them from formation energies and
    Helgeson coefficients alone is what licenses the whole standard-state chain.
    """
    assert new.pK("R1_water", 273.15) == pytest.approx(14.94, abs=0.05)
    assert new.pK("R1_water", 333.15) == pytest.approx(13.02, abs=0.05)


# --------------------------------------------------------------------------------------
# Henry's law
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("T", TEMPERATURES_K)
def test_henry_volatiles_bit_exact(v1, T):
    assert new.henry_nh3_MPa(T) == v1.henry_nh3_MPa(T)
    assert new.henry_co2_MPa(T) == v1.henry_co2_MPa(T)


@pytest.mark.parametrize("T", TEMPERATURES_K)
@pytest.mark.parametrize("sp", ["N2", "O2", "CH4", "H2", "CO2"])
def test_henry_inerts_bit_exact(v1, sp, T):
    assert new.henry_inert_MPa(sp, T) == v1.henry_inert_MPa(sp, T)


def test_henry_inert_refuses_unknown_species():
    """A species with no published row must raise, not borrow a neighbour's constants."""
    with pytest.raises(KeyError):
        new.henry_inert_MPa("Ar", 298.15)


# --------------------------------------------------------------------------------------
# Activity coefficients
# --------------------------------------------------------------------------------------

def _mole_fractions(n_tot: float, c_tot: float) -> dict:
    """A crude but well-conditioned composition for exercising the activity model.

    It does not have to be an equilibrium state — the activity model is a function of
    composition alone, so any positive composition exercises the same code path.
    """
    w = new.N_W_PER_KG
    raw = {
        "H2O": w,
        "NH3(aq)": 0.30 * n_tot,
        "NH4+": 0.45 * n_tot,
        "NH2COO-": 0.20 * n_tot,
        "CO2(aq)": 0.25 * c_tot,
        "HCO3-": 0.55 * c_tot,
        "CO3--": 0.05 * c_tot,
        "H+": 1e-7,
        "OH-": 1e-7,
    }
    tot = sum(raw.values())
    return {k: v / tot for k, v in raw.items()}


@pytest.mark.parametrize("n_tot,c_tot,T", LOADINGS)
def test_activity_ln_gamma_bit_exact(v1, n_tot, c_tot, T):
    x = _mole_fractions(n_tot, c_tot)
    a = new.activity_ln_gamma(x, T)
    b = v1.activity_ln_gamma(x, T)
    assert a.keys() == b.keys()
    for sp in a:
        assert a[sp] == b[sp], sp


@pytest.mark.parametrize("n_tot,c_tot,T", LOADINGS)
def test_activity_parts_bit_exact(v1, n_tot, c_tot, T):
    x = _mole_fractions(n_tot, c_tot)
    assert new.uniquac_combinatorial_ln_gamma(x) == v1.uniquac_combinatorial_ln_gamma(x)
    assert new.uniquac_residual_ln_gamma(x, T) == v1.uniquac_residual_ln_gamma(x, T)
    assert new.debye_huckel_ln_gamma(x, T) == v1.debye_huckel_ln_gamma(x, T)
    assert new.ionic_strength(x) == v1.ionic_strength(x)
    assert new.debye_huckel_A(T) == v1.debye_huckel_A(T)
    assert new.short_range_ln_gamma(x, T) == v1.short_range_ln_gamma(x, T)


@pytest.mark.parametrize("n_tot,c_tot,T", LOADINGS)
def test_excess_enthalpy_bit_exact(v1, n_tot, c_tot, T):
    x = _mole_fractions(n_tot, c_tot)
    assert new.excess_enthalpy(x, T) == v1.excess_enthalpy(x, T)


@pytest.mark.parametrize("sp", ["NH3(aq)", "CO2(aq)", "NH4+", "HCO3-", "CO3--", "NH2COO-"])
@pytest.mark.parametrize("T", [298.15, 408.15, 473.15])
def test_infinite_dilution_limits_bit_exact(v1, sp, T):
    assert (new.uniquac_combinatorial_ln_gamma_inf(sp)
            == v1.uniquac_combinatorial_ln_gamma_inf(sp))
    assert (new.uniquac_residual_ln_gamma_inf(sp, T)
            == v1.uniquac_residual_ln_gamma_inf(sp, T))


# --------------------------------------------------------------------------------------
# SRK vapour fugacity
# --------------------------------------------------------------------------------------

VAPOURS = [
    # PFD stream 204 — the HV-322604 inert purge: mostly nitrogen, which is exactly why a
    # constant Joule-Thomson coefficient was wrong for it.
    ({"N2": 0.688, "O2": 0.114, "CH4": 0.059, "H2": 0.031,
      "NH3": 0.083, "CO2": 0.022, "H2O": 0.003}, 387.15, 140.7e5),
    ({"NH3": 0.70, "CO2": 0.22, "H2O": 0.08}, 456.15, 144.2e5),   # 322 loop vapour
    ({"NH3": 0.30, "CO2": 0.15, "H2O": 0.55}, 408.15, 4.1e5),     # 323C003 overhead
    ({"H2O": 0.90, "NH3": 0.08, "CO2": 0.02}, 318.15, 0.33e5),    # 324 vacuum vent
]


@pytest.mark.parametrize("y,T,P", VAPOURS)
def test_srk_phi_bit_exact(v1, y, T, P):
    phi_new, z_new = new.srk_phi(y, T, P)
    phi_v1, z_v1 = v1.srk_phi(y, T, P)
    assert z_new == z_v1
    assert phi_new.keys() == phi_v1.keys()
    for sp in phi_new:
        assert phi_new[sp] == phi_v1[sp], sp


def test_srk_approaches_ideal_at_low_pressure():
    """Sanity oracle: phi -> 1 as P -> 0. Independent of V1."""
    phi, z = new.srk_phi({"NH3": 0.5, "CO2": 0.5}, 298.15, 1.0)
    assert z == pytest.approx(1.0, abs=1e-6)
    for sp in phi:
        assert phi[sp] == pytest.approx(1.0, abs=1e-5)


# --------------------------------------------------------------------------------------
# Speciation — the R1-R5 Newton solve
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("n_tot,c_tot,T", LOADINGS)
def test_speciate_bit_exact(v1, n_tot, c_tot, T):
    a = new.speciate(n_tot, c_tot, T)
    b = v1.speciate(n_tot, c_tot, T)
    assert a.keys() == b.keys()
    for k in a:
        assert a[k] == b[k], k


@pytest.mark.parametrize("n_tot,c_tot,T", LOADINGS)
def test_speciate_closes_its_balances(v1, n_tot, c_tot, T):
    """The solve's own validation: every balance and reaction quotient to ~1e-10."""
    m = new.speciate(n_tot, c_tot, T)
    assert m["resid"] < 1e-9
    assert m["NH3(aq)"] + m["NH4+"] + m["NH2COO-"] == pytest.approx(n_tot, rel=1e-9)
    assert (m["CO2(aq)"] + m["HCO3-"] + m["CO3--"] + m["NH2COO-"]
            == pytest.approx(c_tot, rel=1e-9))


def test_seeded_newton_reaches_the_synthesis_loop(v1):
    """`m_guess` is what puts the HP loop inside the model's reach.

    Marching from a converged neighbour, the same solver reaches loadings an unseeded call
    cannot. This walks the N/C = 4.46 ray from N = 20 to N = 100 — the 322R001 overflow —
    and asserts both implementations march identically.
    """
    nc = 4.46
    t = 456.15                       # 183 C, the reactor overflow temperature
    guess_new = None
    guess_v1 = None
    for n in (20.0, 40.0, 60.0, 80.0, 100.0):
        c = n / nc
        a = new.speciate(n, c, t, m_guess=guess_new)
        b = v1.speciate(n, c, t, m_guess=guess_v1)
        for k in a:
            assert a[k] == b[k], f"N={n}, {k}"
        guess_new = {s: a[s] for s in new.SOLUTES}
        guess_v1 = {s: b[s] for s in new.SOLUTES}
    # The seeded march must actually converge at the loop loading, not merely agree.
    assert a["resid"] < 1e-9


def test_speciate_refuses_off_reference_without_cp(v1, monkeypatch):
    """Refusal must survive the port (Rule 2).

    The NH3(aq) Cp row is temporarily removed to reproduce the pre-2023 state, where the
    coefficients were paywalled. `speciate` must raise off 298.15 K rather than fabricate.
    """
    original = new.STANDARD_STATE["NH3(aq)"]
    new.STANDARD_STATE["NH3(aq)"] = (original[0], original[1], None)
    try:
        with pytest.raises(ValueError):
            new.speciate(2.0, 1.0, 373.15)
    finally:
        new.STANDARD_STATE["NH3(aq)"] = original
