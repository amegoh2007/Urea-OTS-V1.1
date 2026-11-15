"""Henry's constants — `ureasim.thermo.henry`.

Pinned: the module's two stated validations. At 25 C the IAPWS G7-04 rows reproduce the textbook
mole-fraction constants of N2, O2, CH4 and H2 to the errors its docstring states (1.0, 0.8, 4.4 and
0.3 %); and G7-04's CO2 row, carried for that purpose only, agrees with the independent Rumpf and
Maurer correlation the flash uses to 0.2 % at 25 C, 2.3 % at 140 C and 5.0 % at 183 C. Beyond
them: NH3 is three orders of magnitude more soluble than CO2 and grows less soluble with
temperature; a permanent gas's constant passes through its maximum inside the water envelope.
"""

from __future__ import annotations

import pytest

from ureasim.thermo.henry import (G704_VALID_T_K, HENRY_G704, henry_co2_MPa, henry_inert_MPa,
                                  henry_nh3_MPa)

T25 = 298.15
#: Textbook mole-fraction Henry constants at 25 C [bar], as the module docstring cites them,
#: with the error it states for each.
TEXTBOOK_25C = {"N2": (86_500.0, 0.010), "O2": (44_000.0, 0.008), "CH4": (41_300.0, 0.044),
                "H2": (71_200.0, 0.003)}


@pytest.mark.parametrize("sp", sorted(TEXTBOOK_25C))
def test_the_g704_rows_reproduce_the_textbook_constants_at_25_c(sp):
    textbook_bar, stated = TEXTBOOK_25C[sp]
    error = abs(henry_inert_MPa(sp, T25) * 10.0 / textbook_bar - 1.0)
    assert error == pytest.approx(stated, abs=0.0006)


@pytest.mark.parametrize("t_c, stated", [(25.0, 0.002), (140.0, 0.023), (183.0, 0.050)])
def test_g704s_co2_row_agrees_with_rumpf_and_maurer(t_c, stated):
    t = t_c + 273.15
    error = abs(henry_inert_MPa("CO2", t) / henry_co2_MPa(t) - 1.0)
    assert error <= stated + 0.001


def test_ammonia_is_far_more_soluble_than_co2_and_loses_solubility_with_heat():
    assert henry_co2_MPa(T25) / henry_nh3_MPa(T25) > 1000.0
    temps = [280.0 + 10.0 * k for k in range(18)]
    nh3 = [henry_nh3_MPa(t) for t in temps]
    assert all(b > a for a, b in zip(nh3, nh3[1:]))


@pytest.mark.parametrize("sp", ["N2", "O2", "CH4", "H2"])
def test_a_permanent_gas_passes_through_its_maximum(sp):
    lo, hi = G704_VALID_T_K
    temps = [lo + 5.0 * k for k in range(int((hi - 20.0 - lo) / 5.0))]
    values = [henry_inert_MPa(sp, t) for t in temps]
    peak = values.index(max(values))
    assert 0 < peak < len(values) - 1
    assert set(HENRY_G704) >= {"N2", "O2", "CH4", "H2", "CO2"}
