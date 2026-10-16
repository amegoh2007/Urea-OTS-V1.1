"""Behaviour of the urea melt's anchored equilibrium — `ureasim.thermo.urea_melt`.

Equivalence with V1 is proven in `tests/equivalence/test_urea_melt_equivalence.py`, which also
runs handoff B-58's departure both ways. This file pins what the stages' melt DOES on the
decided model — the UNIQUAC parameter refitted to the PFD (-85.3 K) and the non-volatile
ceiling: its design strength, how it answers temperature and vacuum against the Fahmy-Nassar
plant correlation, where the model's window holds it, the PFD's own water activity it was fitted
to, and the ceiling.
"""

from __future__ import annotations

import math

import pytest

from ureasim.data import unit_324 as d
from ureasim.thermo import extended_uniquac as eu
from ureasim.thermo import iapws
from ureasim.thermo import urea_melt as um

A = d.MELT_A_UREA_WATER_K
E001 = (d.E001_W_UREA_DES, d.E001_T_DES_C, d.F001_P_DES_BARA)
E003 = (d.E003_W_UREA_DES, d.E003_T_DES_C, d.F003_P_DES_BARA)


def _w(t, p, stage, **kw):
    return um.equilibrium_urea_fraction(t, p, *stage, a_urea_water_k=A, **kw)


def fahmy_nassar(t_c: float, p_bara: float) -> float:
    """The Fahmy-Nassar plant correlation's urea mass fraction (``References/Urea-Water VLE Data
    Research.md`` sec. 4.1): ln Pw[mmHg] = 16.2886 - 3186.44 / (T + 227.02),
    x_w = 1.06425 (0.95 Pv / Pw)^0.92498, Cw by the molar masses 18.016 and 60.056."""
    p_w = math.exp(16.2886 - 3186.44 / (t_c + 227.02))
    x_w = 1.06425 * (0.95 * p_bara * 750.0616827 / p_w) ** 0.92498
    return 1.0 - 18.016 * x_w / (60.056 * (1.0 - x_w) + 18.016 * x_w)


def _slopes(f, t, p):
    """d(wt%)/dK and d(wt%) per 0.01 bar, central differences of 1 K and 1 %."""
    return ((f(t + 1.0, p) - f(t - 1.0, p)) / 2.0 * 100.0,
            (f(t, p * 1.01) - f(t, p * 0.99)) / (0.02 * p) * 100.0 * 0.01)


def test_each_stage_holds_its_pfd_melt_at_design():
    """PFD 401 and 402: 94.31 and 97.71 wt% urea, to the bit; the soft sensor reads them."""
    assert _w(130.0, 0.33, E001) == 0.9431
    assert _w(140.0, 0.131, E003) == 0.9771
    assert um.melt_concentration_pct(*E003, 140.0, 0.131, a_urea_water_k=A) == pytest.approx(
        97.71, abs=1e-12)


@pytest.mark.parametrize("stage, slopes, fn_slopes", [
    (E001, (0.1745, -0.1732), (0.1670, -0.2024)),
    (E003, (0.0451, -0.1190), (0.0446, -0.1440)),
])
def test_the_melts_slopes_are_grounded_on_fahmy_nassar_b58(stage, slopes, fn_slopes):
    """Handoff B-58, decided 2026-10-01: the equilibrium grounded on the Fahmy-Nassar plant
    correlation. The refitted strength moves +0.175 and +0.045 wt% per kelvin, the correlation's
    +0.167 and +0.045 — within 5 % (V1's +0.249 and +0.069 are 49 and 55 % steep). The vacuum
    slopes, -0.173 and -0.119 per 0.01 bar against -0.202 and -0.144, are 14 and 17 % shallow:
    the binary takes the whole vacuum as the water's pressure (B-58)."""
    w_des, t, p = stage
    mine = _slopes(lambda tc, pp: _w(tc, pp, stage), t, p)
    plant = _slopes(fahmy_nassar, t, p)
    assert mine == pytest.approx(slopes, abs=1e-4)
    assert plant == pytest.approx(fn_slopes, abs=1e-4)
    assert abs(mine[0] / plant[0] - 1.0) < 0.05
    assert abs(mine[1] / plant[1] - 1.0) < 0.18


def test_outside_the_window_the_state_is_held_at_its_edge():
    """Below 99 C (or a NaN) the melt is the window's edge, 93.15 % on stage 2; the diagnostics
    say so."""
    edge = _w(99.0, 0.131, E003)
    assert _w(60.0, 0.131, E003) == edge
    assert _w(math.nan, 0.131, E003) == edge
    assert edge == pytest.approx(0.931505, abs=1e-6)
    assert um.melt_diagnostics(90.0, 0.131, edge, a_urea_water_k=A) == (
        "OUTSIDE_MODEL_DOMAIN", None)
    status, residual = um.melt_diagnostics(140.0, 0.131, 0.9771, a_urea_water_k=A)
    assert status == "DESIGN_ANCHORED_EXTRAPOLATION"
    assert residual == pytest.approx(0.063046, abs=1e-6)


@pytest.mark.parametrize("t, p, row_w, row_water, y_water, gamma_pfd, gamma_v1, gamma_refit", [
    (130.0, 0.33, 94.31, 4.97, 96.77, 0.7908, 0.5167, 0.7594),
    (140.0, 0.131, 97.71, 1.39, 87.58, 0.7010, 0.4845, 0.7327),
])
def test_the_refit_holds_the_melts_water_as_the_pfd_does_b58(t, p, row_w, row_water, y_water,
                                                              gamma_pfd, gamma_v1, gamma_refit):
    """Handoff B-58. The PFD's melt (401, 402, mass per cent) under its own vapour (705, 709, the
    water's mole per cent) implies a water activity coefficient of 0.79 and 0.70. The published
    parameter gives 0.52 and 0.48 (raw, it boils the PFD melts 14 and 13 K hotter); the refit,
    0.76 and 0.73 — within 4.5 %."""
    n_w, n_u = row_water / 18.01528, row_w / 60.05526
    x_w = n_w / (n_w + n_u)
    p_w = y_water / 100.0 * p
    assert p_w / (x_w * iapws.psat_bara(t)) == pytest.approx(gamma_pfd, abs=1e-4)
    t_k = t + 273.15
    assert math.exp(eu.ln_gamma(x_w, 1.0 - x_w, t_k)[0]) == pytest.approx(gamma_v1, abs=1e-4)
    g = math.exp(eu.ln_gamma(x_w, 1.0 - x_w, t_k, a_urea_water_k=A)[0])
    assert g == pytest.approx(gamma_refit, abs=1e-4)
    assert abs(g / gamma_pfd - 1.0) < 0.046


def test_the_melt_never_passes_what_its_non_volatiles_leave_b58():
    """Handoff B-58. PFD 402 carries 0.86 wt% of biuret and formaldehyde, so its urea tops out at
    99.13 %. On the refit the anchored strength reaches it only at 0.02 bar a above 170 C; the
    ceiling holds it there, so the stage can never boil its biuret as water."""
    ceiling = um.strength_ceiling(97.71, 0.85 + 0.0099)
    assert ceiling == pytest.approx(0.991276, abs=1e-6)
    assert _w(160.0, 0.02, E003) < ceiling < um.equilibrium_urea_fraction(
        170.0, 0.02, *E003, a_urea_water_k=A)
    assert _w(170.0, 0.02, E003, w_max=ceiling) == ceiling
    assert _w(140.0, 0.131, E003, w_max=ceiling) == 0.9771
    assert um.strength_ceiling(0.0, 0.0) == 1.0


#: Uhde's Figure 15, "Three phase equilibria of system Urea - Water", in the Helwan operating
#: manual's Fundamentals (UD-VT-G00-DC-0003 rev 00 page 1-44; `References/Sources/Urea Production
#: Diagrams.pdf` PDF page 19, a 300 dpi scan): each iso-strength line [wt% urea, urea-water basis]
#: digitised on the scan's own ticks (log P at 798 px a decade, the temperature axis in 1/T) and
#: fitted straight, log10 P_H2O [mmHg] = a + b / T [K], over the range the chart draws it [C]. The
#: fits' residuals are under 0.006 in log10 P. The 90 % line (a 0.034 residual) and the 99.7 % line
#: (the chart's illustrative point D) are left out.
LICENSOR_LINES = {
    0.925: (8.0042, -2198.37, 111.0), 0.95: (7.8663, -2214.98, 130.0),
    0.97: (7.6819, -2231.03, 124.0), 0.98: (7.4444, -2212.24, 136.0),
    0.99: (7.0530, -2187.99, 133.0),
}


def _licensor_p_bara(w: float, t_c: float) -> float:
    a, b, _ = LICENSOR_LINES[w]
    return 10.0 ** (a + b / (t_c + 273.15)) / 750.0616827


def _licensor_w(t_c: float, p_bara: float) -> float:
    """The chart's strength at (T, P): ln P interpolated in ln x_w between its lines."""
    pts = []
    for w in sorted(LICENSOR_LINES):
        x_w = eu.mole_fractions_from_urea_mass_fraction(w)[0]
        pts.append((math.log(x_w), math.log(_licensor_p_bara(w, t_c))))
    lp = math.log(p_bara)
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if min(y1, y2) <= lp <= max(y1, y2):
            x_w = math.exp(x1 + (lp - y1) * (x2 - x1) / (y2 - y1))
            return 1.0 - 18.01528 * x_w / (60.05526 * (1.0 - x_w) + 18.01528 * x_w)
    raise ValueError("outside the chart's lines")


def test_the_refit_lies_on_the_licensors_own_chart_b58():
    """Uhde's Figure 15 for Helwan. Over every line from 92.5 to 99 wt% and the temperatures it is
    drawn at, the refit's water vapour pressure is within 13 % of the chart (at most 7 % low); the
    published parameter (V1's) is 27 to 35 % low everywhere. PFD 401 on the chart's basis is
    95.0 % — the chart puts its water at 0.314 bar a at 130 C, the PFD's vapour at 0.319."""
    for w, (a, b, t_lo) in LICENSOR_LINES.items():
        for t in range(int(t_lo), 151):
            chart = _licensor_p_bara(w, float(t))
            refit = eu.water_activity(w, t + 273.15, a_urea_water_k=A) * iapws.psat_bara(t)
            v1 = eu.water_activity(w, t + 273.15) * iapws.psat_bara(t)
            assert -0.073 < math.log(refit / chart) < 0.123, (w, t)
            assert -0.43 < math.log(v1 / chart) < -0.25, (w, t)
    assert _licensor_p_bara(0.95, 130.0) == pytest.approx(0.3140, abs=1e-4)


@pytest.mark.parametrize("stage, chart_slope", [(E001, 0.1587), (E003, 0.0441)])
def test_the_melts_temperature_slope_is_the_licensors_b58(stage, chart_slope):
    """TIC-324001's and TIC-324002's process gain on the licensor's chart: +0.159 and +0.044 wt%
    per kelvin at the stages' vacuums. The refit's +0.175 and +0.045 are within 10 and 3 %; V1's
    +0.249 and +0.069, 57 % steep."""
    _, t, p = stage
    chart = (_licensor_w(t + 1.0, p) - _licensor_w(t - 1.0, p)) / 2.0 * 100.0
    assert chart == pytest.approx(chart_slope, abs=1e-4)
    mine = _slopes(lambda tc, pp: _w(tc, pp, stage), t, p)[0]
    assert abs(mine / chart - 1.0) < 0.105
