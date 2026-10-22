"""Unit 324's vacuum train — `ureasim.data.unit_324_train` (the condensers' ratings, the vapour rows
and the ejectors' vendor ratings moved in from `unit_324`, 2026-10-23).

Pins the design values the move must not change, each measured before it was written, and the
re-export through `unit_324`.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_324
from ureasim.data import unit_324_train as train

MOVED = ["CW_CP_KJKG_K", "lmtd_countercurrent", "CondenserRating", "VACUUM_CONDENSERS",
         "PFD_324_MOL_PCT", "VAC_PFD_KMOLH", "VAC_AIR_MW", "VAC_AIR_FRAC", "EjectorDuty",
         "F004_DUTY_GAS_KGH", "EJECTOR_DUTIES", "EjectorLoad", "F002_MOTIVE_DES_KGH",
         "F004_MOTIVE_DES_KGH", "F005_MOTIVE_DES_KGH"]


def test_the_condensers():
    """Four condensers; the cooling water's cp back-solved so 324E002's 1591 t/h over 10 K is its
    18.46 MW; its LMTD 37.59 K on 116 / 45 C against 30 / 40 C."""
    assert sorted(train.VACUUM_CONDENSERS) == ["324E002", "324E005", "324E006", "324E007"]
    e002 = train.VACUUM_CONDENSERS["324E002"]
    assert train.CW_CP_KJKG_K == pytest.approx(4.1769956, abs=1e-7)
    assert e002.q_kw == pytest.approx(18460.0, abs=1e-9)
    assert e002.lmtd_k == pytest.approx(37.592059, abs=1e-6)


def test_the_ejectors_and_their_motive():
    """324F004's suction gas 21.614 kg/kmol on Körting's mass flows; the PFD's motive 390, 1220
    and 180 kg/h; the hand valves' design strokes 69.06 % and 80.16 %."""
    assert train.EJECTOR_DUTIES["324F004"].mw_suction == pytest.approx(21.613896, abs=1e-6)
    assert (train.F002_MOTIVE_DES_KGH, train.F004_MOTIVE_DES_KGH,
            train.F005_MOTIVE_DES_KGH) == (390.0, 1220.0, 180.0)
    assert train.HV_329605_OP_DES_PCT == pytest.approx(69.0569, abs=1e-4)
    assert train.HV_329606_OP_DES_PCT == pytest.approx(80.1645, abs=1e-4)


def test_unit_324_re_exports_every_moved_name():
    """The same objects through `unit_324`; its design loads stay there, on the moved ratings."""
    for name in MOVED:
        assert getattr(unit_324, name) is getattr(train, name), name
        assert name in unit_324.__all__ and name in train.__all__, name
    loads = unit_324.EJECTOR_DESIGN_LOADS
    assert loads["324F004"].suction_kgh == train.VACUUM_CONDENSERS["324E005"].vent_kgh
    assert isinstance(loads["324F002"], train.EjectorLoad)
