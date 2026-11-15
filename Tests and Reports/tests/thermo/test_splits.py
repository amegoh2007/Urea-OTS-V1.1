"""The anchored component splits — `ureasim.thermo.splits`.

Pinned: a K-value ratio of 1.0 returns the licensor's split to the bit, both at a fixed phase ratio
and with the phase ratio re-solved; a ratio above 1.0 sends more of that species to the vapour, the
larger vapour carrying the others on their own unchanged K-values, every fraction in [0, 1];
species the calibration puts wholly in one phase, and a feed with nothing to flash, come back
untouched; the inert-vent closure lets every
inert out, carries the condensables' saturation on the inert basis, scales the saturation back to
its ceiling and never vents more of a condensable than arrived.
"""

from __future__ import annotations

import pytest

from ureasim.thermo.splits import anchored_split, ratio_shift_frac, saturated_inert_vent

#: A reactor-top-like design split: fraction of each species' feed leaving in the vapour.
FRAC_DES = {"NH3": 0.30, "CO2": 0.20, "H2O": 0.05, "UREA": 0.0, "N2": 1.0}
FEED = {"NH3": 900.0, "CO2": 400.0, "H2O": 500.0, "UREA": 300.0, "N2": 20.0}


def test_ratio_shift_at_unit_ratio_is_the_identity_and_stays_a_fraction():
    for theta in (1e-6, 0.13, 0.5, 0.999):
        assert ratio_shift_frac(theta, 1.0) == theta
        up, down = ratio_shift_frac(theta, 3.0), ratio_shift_frac(theta, 0.2)
        assert down < theta < up < 1.0 and down > 0.0
    # The relation inverts: shifting by r then by 1/r returns the fraction.
    assert ratio_shift_frac(ratio_shift_frac(0.3, 2.5), 0.4) == pytest.approx(0.3, abs=1e-15)
    # Structural cases are returned unchanged: nothing to move, or a nonsensical ratio.
    assert ratio_shift_frac(0.0, 5.0) == 0.0 and ratio_shift_frac(1.0, 0.1) == 1.0
    assert ratio_shift_frac(0.4, 0.0) == 0.4


def test_anchored_split_at_unit_ratio_returns_the_design_vector_to_the_bit():
    out = anchored_split(FRAC_DES, FEED, {k: 1.0 for k in FRAC_DES})
    assert out == pytest.approx(FRAC_DES, abs=1e-15)
    assert out["UREA"] == 0.0 and out["N2"] == 1.0


def test_a_raised_k_ratio_grows_the_vapour_on_the_others_own_k_values():
    out = anchored_split(FRAC_DES, FEED, {"NH3": 1.5})
    assert out["NH3"] > FRAC_DES["NH3"]
    assert out["CO2"] > FRAC_DES["CO2"] and out["H2O"] > FRAC_DES["H2O"]

    def k(theta: dict, sp: str) -> float:
        flashing = ("NH3", "CO2", "H2O")
        z = {s: FEED[s] / sum(FEED[t] for t in flashing) for s in flashing}
        psi = sum(z[s] * theta[s] for s in z)
        return theta[sp] * (1.0 - psi) / (psi * (1.0 - theta[sp]))

    assert k(out, "NH3") / k(FRAC_DES, "NH3") == pytest.approx(1.5, rel=1e-12)
    assert k(out, "CO2") / k(FRAC_DES, "CO2") == pytest.approx(1.0, rel=1e-12)
    assert k(out, "H2O") / k(FRAC_DES, "H2O") == pytest.approx(1.0, rel=1e-12)
    assert all(0.0 <= v <= 1.0 for v in out.values())
    assert out["UREA"] == 0.0 and out["N2"] == 1.0          # one-phase species stay out of it


def test_extreme_ratios_rail_the_flash_instead_of_failing():
    gas = anchored_split(FRAC_DES, FEED, {"NH3": 1e6, "CO2": 1e6, "H2O": 1e6})
    liquid = anchored_split(FRAC_DES, FEED, {"NH3": 1e-6, "CO2": 1e-6, "H2O": 1e-6})
    assert all(gas[k] > 0.999 for k in ("NH3", "CO2", "H2O"))
    assert all(liquid[k] < 1e-3 for k in ("NH3", "CO2", "H2O"))


def test_no_flashing_feed_returns_the_design_vector():
    assert anchored_split(FRAC_DES, {"UREA": 10.0, "N2": 1.0}, {"NH3": 2.0}) == FRAC_DES


def test_the_inert_vent_closure():
    feed = {"N2": 10.0, "O2": 2.0, "NH3": 500.0, "H2O": 300.0}
    y_des = {"NH3": 0.40, "H2O": 0.10}
    vent = saturated_inert_vent(feed, ("N2", "O2"), ("NH3", "H2O"), y_des, 0.95)
    assert vent["N2"] == 10.0 and vent["O2"] == 2.0
    # n_inert y_c / (1 - sum y_c): 12 x 0.40 / 0.50 and 12 x 0.10 / 0.50.
    assert vent["NH3"] == pytest.approx(9.6) and vent["H2O"] == pytest.approx(2.4)
    # A K ratio moves the saturation of its own species only.
    warmer = saturated_inert_vent(feed, ("N2", "O2"), ("NH3", "H2O"), y_des, 0.95, {"NH3": 1.5})
    assert warmer["NH3"] == pytest.approx(12.0 * 0.60 / 0.30) and warmer["N2"] == 10.0


def test_the_saturation_ceiling_and_the_feed_cap():
    feed = {"N2": 10.0, "NH3": 1e6, "H2O": 1e6}
    vent = saturated_inert_vent(feed, ("N2",), ("NH3", "H2O"), {"NH3": 0.8, "H2O": 0.4}, 0.9)
    # Scaled back to 0.9 keeping the 2 : 1 ratio, so the inert-basis factor is 1 / 0.1.
    assert vent["NH3"] == pytest.approx(10.0 * 0.6 / 0.1)
    assert vent["H2O"] == pytest.approx(10.0 * 0.3 / 0.1)
    starved = saturated_inert_vent({"N2": 10.0, "NH3": 1.0}, ("N2",), ("NH3",), {"NH3": 0.5},
                                   0.95)
    assert starved["NH3"] == 1.0
