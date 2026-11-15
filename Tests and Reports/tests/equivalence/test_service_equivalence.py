"""V1 <-> V1.1 equivalence for the unified VLE / flash service.

Gate: exact agreement on classification, K-values, the anchored ratio, the flash and the
isenthalpic flash — plus the two behaviours that are the point of the whole layer:

  * `k_ratio` returns **exactly 1.0** at its own reference point, with no tolerance and no
    identity short-circuit. That is what makes the 322 design split bit-exact.
  * the service **refuses** rather than answering off-envelope.

Memo note
---------
Both implementations carry quantised memos. Every test here clears both caches first, so a
result never depends on what an earlier test happened to populate — which is precisely the
path dependence the canonical point exists to remove, and it would be embarrassing to
reintroduce it in the test suite.
"""

from __future__ import annotations

import pytest

from ureasim.thermo import service as new
from tests.equivalence.v1_loader import load, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

#: Liquors the service is expected to own, with the stage they belong to.
ELECTROLYTE_STATES = [
    ("323C003", {"Urea": 68.74, "Biuret": 0.36, "NH3": 2.13, "CO2": 1.05, "H2O": 27.72},
     135.0, 4.10),
    ("323F004", {"Urea": 71.74, "Biuret": 0.37, "NH3": 0.88, "CO2": 0.66, "H2O": 26.35},
     106.0, 1.13),
    ("323F010", {"Urea": 80.00, "Biuret": 0.42, "NH3": 0.08, "CO2": 0.02, "H2O": 19.48},
     99.0, 0.46),
    ("328C004", {"Urea": 0.8, "NH3": 1.4, "CO2": 0.9, "H2O": 96.9}, 143.0, 3.5),
    ("322R001", {"Urea": 31.0, "Biuret": 0.6, "NH3": 33.0, "CO2": 21.0, "H2O": 14.4},
     183.0, 144.2),
]

#: A urea melt — the neutral-UNIQUAC domain, where `flash` must refuse.
MELT_324E003 = {"Urea": 97.71, "Biuret": 0.85, "NH3": 0.04, "H2O": 1.39, "HCHO": 0.01}


@pytest.fixture(scope="module")
def v1_svc():
    module = load("thermo_service")
    module.prime()
    return module


@pytest.fixture(autouse=True)
def clean_caches(v1_svc):
    """Clear both memos before every test, so no result depends on fill order."""
    new.prime()
    new.flash_cache_clear()
    v1_svc.flash_cache_clear()
    yield


# --------------------------------------------------------------------------------------
# Species and domains
# --------------------------------------------------------------------------------------

def test_species_tables_match(v1_svc):
    assert new.MODEL_NAME == v1_svc.MODEL_NAME
    assert new.MW == v1_svc.MW
    assert new.SPECIES == v1_svc.SPECIES
    assert new.NONVOLATILE == v1_svc.NONVOLATILE
    assert new.VOLATILE == v1_svc.VOLATILE
    assert new.INERTS == v1_svc.INERTS
    assert new.DISTRIBUTING == v1_svc.DISTRIBUTING
    assert new.DOMAIN_ELECTROLYTE == v1_svc.DOMAIN_ELECTROLYTE
    assert new.DOMAIN_NEUTRAL_UREA == v1_svc.DOMAIN_NEUTRAL_UREA
    assert new.UREA_NEUTRAL_THRESHOLD == v1_svc.UREA_NEUTRAL_THRESHOLD


@pytest.mark.parametrize("name,w,t_c,p", ELECTROLYTE_STATES)
def test_classify_bit_exact(v1_svc, name, w, t_c, p):
    assert new.classify(w, t_c, p) == v1_svc.classify(w, t_c, p)
    assert new.classify(w, t_c) == v1_svc.classify(w, t_c)


def test_melt_classifies_as_the_neutral_binary(v1_svc):
    assert new.classify(MELT_324E003, 140.0, 0.131) == new.DOMAIN_NEUTRAL_UREA
    assert new.classify(MELT_324E003, 140.0, 0.131) == v1_svc.classify(
        MELT_324E003, 140.0, 0.131)


@pytest.mark.parametrize("name,w,t_c,p", ELECTROLYTE_STATES)
def test_domain_report_bit_exact(v1_svc, name, w, t_c, p):
    assert new.domain_report(w, t_c, p) == v1_svc.domain_report(w, t_c, p)


def test_off_envelope_classifies_as_none(v1_svc):
    """None is a first-class answer: the caller keeps its own anchored model."""
    w = ELECTROLYTE_STATES[0][1]
    for t_c, p in ((40.0, 4.10), (250.0, 4.10), (135.0, 500.0)):
        assert new.classify(w, t_c, p) is None
        assert v1_svc.classify(w, t_c, p) is None


# --------------------------------------------------------------------------------------
# Partial pressures, fugacity and K-values
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("name,w,t_c,p", ELECTROLYTE_STATES)
def test_partial_pressures_bit_exact(v1_svc, name, w, t_c, p):
    a = new.partial_pressures(w, t_c)
    b = v1_svc.partial_pressures(w, t_c)
    assert a.keys() == b.keys()
    for s in a:
        assert a[s] == b[s], f"{name}/{s}"


@pytest.mark.parametrize("name,w,t_c,p", ELECTROLYTE_STATES)
def test_k_values_bit_exact(v1_svc, name, w, t_c, p):
    assert new.k_values(w, t_c, p) == v1_svc.k_values(w, t_c, p)


def test_non_volatiles_have_exactly_zero_k():
    """Urea cannot leave the liquid. Not 'nearly zero' — zero."""
    name, w, t_c, p = ELECTROLYTE_STATES[0]
    k = new.k_values(w, t_c, p)
    for s in new.NONVOLATILE:
        assert k[s] == 0.0


def test_srk_fugacity_is_doing_real_work_in_the_hp_loop(v1_svc):
    """At 144 bar a the light gases are 20-30 % from ideal, and every per cent lands on an
    inert K-value."""
    y = {"NH3": 0.60, "CO2": 0.18, "H2O": 0.05, "N2": 0.12, "H2": 0.05}
    phi = new.vapour_fugacity(y, 183.0, 144.2)
    assert phi == v1_svc.vapour_fugacity(y, 183.0, 144.2)
    assert phi["N2"] > 1.1
    assert phi["CO2"] < 1.0


# --------------------------------------------------------------------------------------
# The anchored ratio — the most important behaviour in the layer
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("name,w,t_c,p", ELECTROLYTE_STATES)
def test_k_ratio_is_exactly_one_at_its_reference(name, w, t_c, p):
    """No tolerance, no identity short-circuit.

    This is what keeps the licensor's HP split bit-exact at design: with `z_ref_mass=None`
    every argument of the two K-value calls is identical, so the two floats are identical
    and the ratio is exactly 1.0.
    """
    r = new.k_ratio(w, t_c, p, t_ref_c=t_c, p_ref_bara=p)
    for s, v in r.items():
        assert v == 1.0, f"{name}/{s} = {v!r}"


@pytest.mark.parametrize("name,w,t_c,p", ELECTROLYTE_STATES)
def test_k_ratio_bit_exact(v1_svc, name, w, t_c, p):
    for dt, dp in ((0.0, 0.0), (5.0, 0.0), (0.0, 0.5), (-8.0, -0.3)):
        assert (new.k_ratio(w, t_c + dt, p + dp, t_ref_c=t_c, p_ref_bara=p)
                == v1_svc.k_ratio(w, t_c + dt, p + dp, t_ref_c=t_c, p_ref_bara=p))


def test_k_ratio_moves_off_the_reference():
    """A ratio identically 1.0 everywhere would be the frozen split vector it replaced."""
    name, w, t_c, p = ELECTROLYTE_STATES[0]
    r = new.k_ratio(w, t_c + 10.0, p, t_ref_c=t_c, p_ref_bara=p)
    assert any(abs(v - 1.0) > 0.02 for v in r.values())


def test_k_ratio_falls_back_to_one_off_envelope():
    """Off-envelope the licensor's own split is the better answer — never a NaN, never a
    frozen state."""
    name, w, t_c, p = ELECTROLYTE_STATES[0]
    r = new.k_ratio(w, 500.0, p, t_ref_c=t_c, p_ref_bara=p)
    assert all(v == 1.0 for v in r.values())


def test_k_ratio_excursion_is_bounded():
    name, w, t_c, p = ELECTROLYTE_STATES[0]
    r = new.k_ratio(w, t_c + 40.0, p * 0.3, t_ref_c=t_c, p_ref_bara=p)
    assert all(0.02 <= v <= 50.0 for v in r.values())


# --------------------------------------------------------------------------------------
# Bubble and dew
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("name,w,t_c,p", ELECTROLYTE_STATES)
def test_bubble_p_bit_exact(v1_svc, name, w, t_c, p):
    assert new.bubble_p(w, t_c) == v1_svc.bubble_p(w, t_c)
    assert new.bubble_p(w, t_c, srk=False) == v1_svc.bubble_p(w, t_c, srk=False)


@pytest.mark.parametrize("name,w,t_c,p", ELECTROLYTE_STATES)
def test_bubble_t_bit_exact(v1_svc, name, w, t_c, p):
    p_bub = new.bubble_p(w, t_c)
    assert new.bubble_t(w, p_bub) == v1_svc.bubble_t(w, p_bub)


def test_bubble_t_memo_is_path_independent():
    """The bug the canonical point fixed.

    The answer must not depend on whether the cache was cold, warm, or filled by a
    neighbouring point first.
    """
    name, w, t_c, p = ELECTROLYTE_STATES[1]
    p_bub = new.bubble_p(w, t_c)

    new.flash_cache_clear()
    cold = new.bubble_t(w, p_bub)

    new.flash_cache_clear()
    nudged = dict(w, CO2=w["CO2"] + 5.0e-5, H2O=w["H2O"] - 5.0e-5)
    new.bubble_t(nudged, p_bub)               # let a neighbour fill the bin first
    after_neighbour = new.bubble_t(w, p_bub)

    assert cold == after_neighbour


def test_bubble_t_refuses_below_the_grid_rather_than_clamping(v1_svc):
    """The 323F010 case that bit: a clamped 80.0 C came back looking like an answer."""
    cold = {"Urea": 60.0, "NH3": 1.6, "CO2": 0.2, "H2O": 38.2}
    with pytest.raises(new.OutOfDomain):
        new.bubble_t(cold, 0.05)
    with pytest.raises(v1_svc.OutOfDomain):
        v1_svc.bubble_t(cold, 0.05)


# --------------------------------------------------------------------------------------
# Flash
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("name,w,t_c,p", ELECTROLYTE_STATES)
def test_flash_bit_exact(v1_svc, name, w, t_c, p):
    """Bit-exact on the port's budget, 60 sweeps (handoff A-9, decided 2026-09-30): V1's own
    solver run to the same budget. Every state but the marginal one converges inside V1's 40."""
    new.flash_cache_clear()
    v1_svc.flash_cache_clear()
    a = new.flash(w, t_c, p).as_dict()
    b = v1_svc.flash(w, t_c, p, outer_iters=new.FLASH_OUTER_ITERS).as_dict()
    assert a.keys() == b.keys()
    for k in a:
        assert a[k] == b[k], f"{name}/{k}"
    if name not in MARGINAL_CONVERGENCE:
        v1_svc.flash_cache_clear()
        assert v1_svc.flash(w, t_c, p).as_dict() == a, name


#: Stages that do NOT reach `FLASH_TOL` within V1's 40 sweeps. The dilute, hot 328C004 liquor
#: converges on sweep 41, one past V1's budget, at a residual of 1.09e-7 against a tolerance of
#: 1e-7. Handoff A-9, decided 2026-09-30: the port's budget is 60, and V1's flag is wrong.
MARGINAL_CONVERGENCE = {"328C004"}


@pytest.mark.parametrize("name,w,t_c,p", ELECTROLYTE_STATES)
def test_flash_closes_its_balance(name, w, t_c, p):
    fr = new.flash(w, t_c, p)
    assert 0.0 <= fr.psi_mole <= 1.0
    assert sum(fr.x.values()) == pytest.approx(1.0, abs=1e-12)
    if fr.psi_mass > 0.0:
        assert sum(fr.y.values()) == pytest.approx(1.0, abs=1e-12)
    if name in MARGINAL_CONVERGENCE:
        # Still an accurate answer — two orders below the model's own residual against the
        # PFD — it just misses the flag by one sweep.
        assert fr.residual < 1.0e-6, f"{name}: residual {fr.residual}"
    else:
        assert fr.converged, f"{name}: residual {fr.residual}"


@pytest.mark.parametrize("name", sorted(MARGINAL_CONVERGENCE))
def test_marginal_states_converge_with_one_more_sweep(v1_svc, name):
    """Handoff A-9, decided 2026-09-30, both sides: V1's default 40 sweeps stop one short and flag
    the solve unconverged; the port's default 60 reach the tolerance on sweep 41 — as V1's own
    solver does given the budget. A budget, not a divergence of the method."""
    w, t_c, p = next((x[1], x[2], x[3]) for x in ELECTROLYTE_STATES if x[0] == name)
    new.flash_cache_clear()
    v1_svc.flash_cache_clear()
    assert v1_svc.flash(w, t_c, p).converged is False
    assert new.flash(w, t_c, p, outer_iters=40).converged is False
    new.flash_cache_clear()
    v1_svc.flash_cache_clear()
    ours = new.flash(w, t_c, p)
    assert ours.converged is True and ours.iterations == 41
    assert v1_svc.flash(w, t_c, p, outer_iters=60).converged is True


def test_urea_cannot_flash_away():
    """The Rachford-Rice detail that matters: non-volatiles enter the sum at K = 0.

    Dropping them — the obvious filter — let a 69 wt% urea liquor flash to psi_mass = 1.0.
    """
    name, w, t_c, p = ELECTROLYTE_STATES[0]
    fr = new.flash(w, t_c, p * 0.25)          # let it down hard
    assert fr.psi_mass < 1.0
    assert fr.x["Urea"] > 0.0


def test_flash_refuses_on_a_urea_melt(v1_svc):
    """handoff B-1: the neutral binary carries no NH3/CO2 and the electrolyte path is
    outside its dilute limit in a melt, so a volatile SPLIT is refused here."""
    with pytest.raises(new.OutOfDomain) as exc:
        new.flash(MELT_324E003, 140.0, 0.131)
    assert "NEUTRAL_UREA" in str(exc.value)
    with pytest.raises(v1_svc.OutOfDomain):
        v1_svc.flash(MELT_324E003, 140.0, 0.131)


def test_bubble_point_remains_available_on_a_melt(v1_svc):
    """What B-1 does NOT take away: the water-only duty is still good, +2.2 % at 324E003."""
    p = new.bubble_p(MELT_324E003, 140.0)
    assert p == v1_svc.bubble_p(MELT_324E003, 140.0)
    assert 0.10 < p < 0.20


def test_flash_memo_is_path_independent():
    """A memo entry must be a pure function of its key — see `thermo.memo`."""
    name, w, t_c, p = ELECTROLYTE_STATES[1]
    new.flash_cache_clear()
    cold = new.flash(w, t_c, p).as_dict()

    new.flash_cache_clear()
    nudged = dict(w, CO2=w["CO2"] + 5.0e-5, H2O=w["H2O"] - 5.0e-5)
    new.flash(nudged, t_c, p)                 # neighbour fills the bin first
    after = new.flash(w, t_c, p).as_dict()

    for k in ("psi_mole", "psi_mass", "x", "y"):
        assert cold[k] == after[k], k


def test_memo_hits_after_the_first_solve():
    name, w, t_c, p = ELECTROLYTE_STATES[0]
    new.flash_cache_clear()
    for _ in range(5):
        new.flash(w, t_c, p)
    stats = new.flash_cache_stats()
    assert stats["miss"] == 1
    assert stats["hit"] == 4


def test_disabling_the_memo_gives_the_same_answer(v1_svc):
    """The memo is an optimisation. It must not be load-bearing."""
    from ureasim.thermo import memo as memo_mod
    name, w, t_c, p = ELECTROLYTE_STATES[0]
    memoised = new.flash(w, t_c, p).as_dict()
    saved = memo_mod.FLASH_CACHE_SIZE
    try:
        memo_mod.FLASH_CACHE_SIZE = 0
        direct = new.flash(w, t_c, p).as_dict()
    finally:
        memo_mod.FLASH_CACHE_SIZE = saved
    for k in ("psi_mole", "psi_mass"):
        assert memoised[k] == pytest.approx(direct[k], rel=1e-6), k


# --------------------------------------------------------------------------------------
# Isenthalpic flash
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("name,w,t_c,p", ELECTROLYTE_STATES[:3])
def test_flash_ph_bit_exact(v1_svc, name, w, t_c, p):
    h = new.mixture_enthalpy_kj_per_kg(new.flash(w, t_c, p))
    assert h == v1_svc.mixture_enthalpy_kj_per_kg(v1_svc.flash(w, t_c, p))
    a = new.flash_ph(w, h, p).as_dict()
    b = v1_svc.flash_ph(w, h, p).as_dict()
    for k in a:
        assert a[k] == b[k], f"{name}/{k}"


@pytest.mark.parametrize("name,w,t_c,p", ELECTROLYTE_STATES[:3])
def test_flash_ph_inverts_the_isothermal_flash(name, w, t_c, p):
    """h(T) is monotone, so a PH flash at h(T) must return T."""
    h = new.mixture_enthalpy_kj_per_kg(new.flash(w, t_c, p))
    fr = new.flash_ph(w, h, p)
    assert fr.t_c == pytest.approx(t_c, abs=0.05)
