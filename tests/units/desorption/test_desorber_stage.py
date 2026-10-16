"""Behaviour of a desorption-train stage's species layer — `ureasim.units.desorption.desorber_stage`.

Equivalence with V1 is proven through 328C002, every tick, in
`tests/equivalence/test_first_desorber_equivalence.py`. This file pins what the layer DOES: the
design alphas back to the bit at the design state; a column that loses half its stripping vapour
strips its volatiles a hundred times less well; the implicit step holds the design point, cannot
go negative on a stiff trace, and keeps an empty stage's liquid.
"""

from __future__ import annotations

import pytest

from ureasim.data import desorption_train as t
from ureasim.data import unit_328c002 as c
from ureasim.thermo.ammonia_water import desorber_stage
from ureasim.units.desorption.desorber_stage import advance_species, alpha_live

V_DES = t.C002_M748_DES_KGH + t.C002_M750_DES_KGH


def test_the_design_state_returns_the_design_alphas():
    st = c.C002_STAGE
    alpha, domain = alpha_live(st, st.t_eq_c, V_DES, t.C002_M743_DES_KGH, t.W_S743, st.p_bara)
    assert alpha == t.DES_C002.alpha and domain == "electrolyte_gamma_phi"


def test_half_the_stripping_vapour_strips_a_hundred_times_less():
    """At half its design V/L 328C002's stripping factor drops below 1, Kremser's residual jumps,
    and the lumped NH3 and CO2 volatilities fall to 1.03 % of design."""
    st = c.C002_STAGE
    alpha, _ = alpha_live(st, st.t_eq_c, 0.5 * V_DES, t.C002_M743_DES_KGH, t.W_S743, st.p_bara)
    for k in ("NH3", "CO2"):
        assert alpha[k] / t.DES_C002.alpha[k] == pytest.approx(0.0103150, abs=1e-7), k
    assert alpha["H2O"] == 1.0 and alpha["Urea"] == 0.0


def _c004_step(w, feeds, dt=0.1):
    return advance_species(w, 1436.0, feeds, t.C004_M750_DES_KGH, t.DES_C004.alpha,
                           t.C004_M739_DES_KGH, 0.0, dt)


def test_the_design_point_holds():
    """328C004's rows close to 0.034 kg/h of urea (their rounding); in 100 s the liquid moves by
    under 5e-7 and the overhead by under 3e-11."""
    feeds = [(t.W_S747, t.C004_M749_DES_KGH), (t.W_STEAM, t.C004_M931_DES_KGH)]
    w = dict(t.W_S739)
    for _ in range(1000):
        w, y = _c004_step(w, feeds)
    assert max(abs(w[k] - t.W_S739[k]) for k in w) < 5e-7
    assert max(abs(y[k] - t.DES_C004.y[k]) for k in y) < 3e-11
    assert sum(w.values()) == pytest.approx(1.0, abs=1e-15)


def test_a_stiff_trace_cannot_go_negative():
    """Ten times the ammonia into a sump holding 1.4 g of it, at 0.1 s: the implicit step walks
    the bottoms to 15.8 ppm with nothing negative, where explicit Euler overshoots."""
    f = dict(t.W_S747)
    f["NH3"] *= 10.0
    f = {k: v / sum(f.values()) for k, v in f.items()}
    w = dict(t.W_S739)
    for _ in range(100):
        w, _ = _c004_step(w, [(f, t.C004_M749_DES_KGH), (t.W_STEAM, t.C004_M931_DES_KGH)])
    assert w["NH3"] * 1e6 == pytest.approx(15.767, abs=1e-3)
    assert min(w.values()) >= 0.0


def test_an_empty_stage_keeps_its_liquid():
    w0 = {k: 0.0 for k in t.W_S739}
    w, y = advance_species(w0, 1.0, [], 0.0, t.DES_C004.alpha, 0.0, 0.0, 0.1)
    assert w == w0 and y["H2O"] == 1.0 and sum(y.values()) == 1.0


def test_a_stage_built_on_other_terms_moves_its_reference():
    """The builder's terms are what the live factor is taken against: a stage built on half the
    design vapour returns ITS design alphas at half the vapour."""
    st = desorber_stage(t.DES_C002, t.C002_NTHEO, 0.5 * V_DES, t.C002_M743_DES_KGH,
                        c.C002_STAGE.p_bara, t.KINF)
    alpha, _ = alpha_live(st, st.t_eq_c, 0.5 * V_DES, t.C002_M743_DES_KGH, t.W_S743, st.p_bara)
    assert alpha == t.DES_C002.alpha
