"""323C003 / 323E002's design basis — `ureasim.data.unit_323c003` (the stage moved in from
`unit_323`, 2026-10-23).

Pins the stage-1 design values the move must not change, each measured before it was written, and
the re-export through `unit_323`. The column's relief is pinned in
`tests/units/recirc/test_rectifying_column.py`.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_323
from ureasim.data import unit_323c003 as c003


def test_the_rows():
    """PFD 208 and 314 as mass fractions; 314 closed on the drain, its urea 68.7477 wt % against
    the table's 68.74 (decision 101)."""
    assert sum(c003.W_S208.values()) == pytest.approx(1.0, abs=1e-12)
    assert sum(c003.W_S314.values()) == pytest.approx(1.0, abs=1e-12)
    assert c003.W_S314_TAB["Urea"] == pytest.approx(0.6874, abs=1e-12)
    assert c003.W_S314["Urea"] == pytest.approx(0.687477, abs=1e-6)


def test_the_design_point():
    """The overhead 24 563 kg/h split 11 066 flash gas and 13 498 heater vapour by duty; the
    effective latent heat 1562.4 kJ/kg; the heater's conductance 760.57 kW/K on the 3.9 bar a
    chest; the holdup 3530.6 kg at the 60 % set point."""
    assert c003.M305_DES_KGH == pytest.approx(24563.175, abs=1e-3)
    assert c003.M_FLASH_GAS_DES_KGH + c003.M_POOL_VAP_DES_KGH == pytest.approx(
        c003.M305_DES_KGH, rel=1e-15)
    assert c003.M_FLASH_GAS_DES_KGH == pytest.approx(11065.536, abs=1e-3)
    assert c003.LAMBDA_305_KJKG == pytest.approx(1562.4065, abs=1e-4)
    assert c003.E002_UA_KW == pytest.approx(760.5745, abs=1e-4)
    assert c003.C003_M_DES_KG == pytest.approx(3530.6275, abs=1e-4)
    assert c003.GAS_LOAD_COEFF_M3H_PER_BAR == pytest.approx(3097.8451, abs=1e-4)


def test_the_valves_and_controllers():
    """LV-323501 linear from 56.65 %, FL 0.9319; PV-329202's Neldisc from 33.14 (32.92 before decision 178) %, xT 0.53; the
    cascade on span, TIC-323007 0.075 bar/K and PIC-329202 10.83 %/bar."""
    assert (c003.LV501_CHAR, c003.LV501_FL) == ("linear", 0.9319)
    assert c003.LV501_OP_DES_PCT == pytest.approx(56.6495, abs=1e-4)
    assert (c003.PV_329202_OP_DES_PCT, c003.PV_329202_XT) == (pytest.approx(33.1398, abs=1e-4),
                                                              0.53)
    assert c003.TIC_323007_KC == pytest.approx(0.075, rel=1e-15)
    assert c003.PIC_329202_KC == pytest.approx(10.8333, abs=1e-4)


def test_lt_323501_reads_between_its_taps():
    """Decision 241: LI-323501 reads 323C003's liquid over the 2000 mm between its taps, the lower
    250 mm below the R.L. at EL +15.703, and V1's design holdup reads the plant's 40 % exactly. The
    neck, the 15-degree cone and the shell join without a step (12.5, 21.75 and 62.75 %); the reading
    rises with the holdup, 0.031311 %/kg at the design where V1's M / M_full x 100 moves 0.016994; it
    clamps at the taps, 2737.4 and 6052.6 kg; and LV-323501's seal is lost at N5's lower edge,
    29.21 %, 3214.5 kg."""
    f = c003.lt_323501_pct
    assert f(c003.C003_M_DES_KG) == c003.LT_323501_DES_PCT == 40.0
    assert c003.LT_323501_DES_H_M == pytest.approx(0.55, abs=1e-12)
    assert c003.C003_V_DES_M3 == pytest.approx(0.650052, abs=1e-6)
    v0 = c003.C003_M_DES_KG - c003.C003_V_DES_M3 * c003.LT_323501_RHO_KGM3
    assert f(v0) == pytest.approx(12.5, abs=1e-12)
    for m, pct in ((2811.6704, 12.5), (3027.9088, 21.75), (4395.8918, 62.75)):
        assert f(m) == pytest.approx(pct, abs=1e-5)
        assert f(m + 1e-6) - f(m - 1e-6) == pytest.approx(0.0, abs=1e-6)
    ms = [2700.0 + 10.0 * k for k in range(340)]
    assert all(f(a) <= f(b) for a, b in zip(ms, ms[1:]))
    assert f(c003.C003_M_DES_KG + 0.5) - f(c003.C003_M_DES_KG - 0.5) == pytest.approx(0.031311,
                                                                                     abs=1e-6)
    assert 100.0 / c003.C003_M_FULL_KG == pytest.approx(0.016994, abs=1e-6)
    assert (f(2737.0), f(2738.0)) == (0.0, pytest.approx(0.1008, abs=1e-4))
    assert (f(6052.0), f(6053.0)) == (pytest.approx(99.9869, abs=1e-4), 100.0)
    assert c003.LT_323501_SEAL_PCT == pytest.approx(29.2067, abs=1e-4)
    assert f(3214.5255) == pytest.approx(c003.LT_323501_SEAL_PCT, abs=1e-6)


def test_unit_323_re_exports_the_stage():
    """Every stage-1 name is `unit_323`'s too, the same object; the relief's names and LT-323501's
    geometry (decision 241) stay here."""
    relief = {n for n in c003.__all__ if n.startswith("SV32351_")} | {"MW_305"}
    assert len(relief) == 10
    taps = {n for n in c003.__all__ if n.startswith(("LT_323501_", "C003_NECK", "C003_CONE",
                                                      "C003_SHELL"))}
    taps |= {"E002_TUBES_AREA_M2", "C003_V_DES_M3", "lt_323501_pct"}
    assert len(taps) == 19
    relief |= taps
    for name in set(c003.__all__) - relief:
        assert getattr(unit_323, name) is getattr(c003, name), name
        assert name in unit_323.__all__, name
    assert not relief & set(unit_323.__all__)
