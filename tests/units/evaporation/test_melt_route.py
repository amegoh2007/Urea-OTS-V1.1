"""`units/evaporation/melt_route.py` — LV-324501's selector: forward with UF85, or back to
323D002 without it."""

from __future__ import annotations

import pytest

from ureasim.data.unit_324 import W_S402
from ureasim.data.unit_335 import PFD_697_T_C, W_697
from ureasim.units.evaporation.melt_route import melt_route


def test_route_a_takes_the_uf85_at_the_sensible_heat_weighted_temperature():
    """Route A: 609 = 402G + 697, the UF85 at ``uf_ratio`` per kilogram of melt, the mix between
    the melt's 140 C and the UF85's own temperature."""
    r = melt_route(75938.1, W_S402, 140.0, False, uf_ratio=0.005)
    assert (r.route, r.recycle_kgh) == ("A", 0.0)
    assert r.uf85_kgh == pytest.approx(379.6905, abs=1e-9)
    assert r.forward_kgh == pytest.approx(75938.1 + 379.6905, abs=1e-9)
    assert PFD_697_T_C < r.forward_t_c < 140.0
    assert r.forward_w["Urea"] == pytest.approx(
        (75938.1 * W_S402["Urea"] + 379.6905 * W_697["Urea"]) / (75938.1 + 379.6905), rel=1e-12)


def test_route_b_returns_the_raw_melt_with_no_uf85():
    """Route B: the recycle to 323D002 at the melt's temperature, the UF85 interlocked off."""
    r = melt_route(75938.1, W_S402, 140.0, True, uf_ratio=0.005)
    assert (r.route, r.forward_kgh, r.uf85_kgh) == ("B", 0.0, 0.0)
    assert (r.recycle_kgh, r.recycle_t_c) == (75938.1, 140.0)
    assert sum(r.recycle_w.values()) == pytest.approx(1.0, abs=1e-12)


def test_an_empty_composition_is_refused():
    with pytest.raises(ValueError):
        melt_route(1.0, {}, 140.0, False)
