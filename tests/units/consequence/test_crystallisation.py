"""What the mushy-zone restriction DOES — behaviour, with no V1 tree required.

Three properties are pinned:

  * it is EXACTLY 1.0 at every design state in this flowsheet, so it contributes nothing to
    the anchored balance;
  * it is a continuous ramp, so the plugging it models is progressive and recoverable rather
    than a line that works and then does not;
  * the warning band is 5 deg C wide and sits ABOVE the solidus, so the operator sees the
    drain fall while there is still something they can do about it.
"""

from __future__ import annotations

import pytest

from ureasim.data.unit_322e001 import (
    MUSHY_BAND_C,
    T_BOTTOM_DES_C,
    T_CRYSTALLISATION_C,
)
from ureasim.units.consequence.crystallisation import (
    MUSHY_BAND_DEFAULT_C,
    mushy_flow_factor,
)

#: The two boundaries the plant is actually judged against: the 132.7 deg C urea melting
#: point at the 322E001 bottoms, and the 60 deg C carbamate boundary at the 322E003 overflow.
UREA_MELT_C = T_CRYSTALLISATION_C
CARBAMATE_C = 60.0


def test_the_stripper_bottoms_design_state_is_identically_unrestricted():
    """172 deg C against a 132.7 deg C solidus — 39.3 deg C of margin, factor exactly 1.0."""
    assert mushy_flow_factor(T_BOTTOM_DES_C, UREA_MELT_C) == 1.0


@pytest.mark.parametrize("t_cryst", [UREA_MELT_C, CARBAMATE_C])
def test_the_band_is_five_degrees_and_sits_above_the_solidus(t_cryst):
    """Restriction begins at T_cryst + 5 and reaches zero at T_cryst, not below it."""
    assert mushy_flow_factor(t_cryst + MUSHY_BAND_DEFAULT_C, t_cryst) == 1.0
    assert mushy_flow_factor(t_cryst + MUSHY_BAND_DEFAULT_C + 1e-9, t_cryst) == 1.0
    assert mushy_flow_factor(t_cryst, t_cryst) == 0.0
    assert mushy_flow_factor(t_cryst - 40.0, t_cryst) == 0.0


def test_the_data_module_carries_the_same_band_as_the_relation():
    """`unit_322e001.MUSHY_BAND_C` and the generic default are one number, not two.

    They are declared in different layers — the plant datum beside the 322E001 constants,
    the algorithm default beside the equation — so a drift between them would be silent.
    """
    assert MUSHY_BAND_C == MUSHY_BAND_DEFAULT_C


@pytest.mark.parametrize("t_cryst", [UREA_MELT_C, CARBAMATE_C])
def test_the_ramp_is_continuous_and_monotone(t_cryst):
    """Progressive, so a trainee can watch it happen and reverse it."""
    offsets = [-2.0, 0.0, 0.5, 1.0, 2.5, 4.0, 5.0, 7.0]
    factors = [mushy_flow_factor(t_cryst + d, t_cryst) for d in offsets]
    assert all(b >= a for a, b in zip(factors, factors[1:]))
    assert all(0.0 <= f <= 1.0 for f in factors)
    # Linear inside the band: the midpoint is exactly half.
    assert mushy_flow_factor(t_cryst + MUSHY_BAND_DEFAULT_C / 2.0, t_cryst) \
        == pytest.approx(0.5)


def test_a_wider_band_gives_an_earlier_warning_and_a_gentler_slope():
    """The band is an argument because the two services do not plug at the same rate."""
    at_two_degrees_narrow = mushy_flow_factor(UREA_MELT_C + 2.0, UREA_MELT_C, 5.0)
    at_two_degrees_wide = mushy_flow_factor(UREA_MELT_C + 2.0, UREA_MELT_C, 12.0)
    assert at_two_degrees_wide < at_two_degrees_narrow
    assert mushy_flow_factor(UREA_MELT_C + 8.0, UREA_MELT_C, 5.0) == 1.0
    assert mushy_flow_factor(UREA_MELT_C + 8.0, UREA_MELT_C, 12.0) < 1.0


def test_a_non_finite_temperature_reports_an_unrestricted_line():
    """Documented, not desirable: this takes the engine limiter, so a NaN comes back as 1.0.

    Stated here because it is the behaviour a NaN bottoms temperature produces in the sump,
    and because it is the one place where V1's two copies of this relation disagree — see
    `tests/equivalence/test_consequence_equivalence.py` and `handoff.md`.
    """
    assert mushy_flow_factor(float("nan"), UREA_MELT_C) == 1.0
