"""The synthesis loop's boot pin is V1's: its cache is keyed on V1's present source, and every value
is the cache's to the last bit."""

from __future__ import annotations

import hashlib
import json

import pytest

from ureasim.data import synthesis_pin as pin
from ureasim.units.synthesis import reactor as r
from tests.equivalence.v1_loader import V1_BACKEND, lift, v1_available

pytestmark = pytest.mark.skipif(not v1_available(), reason="V1 source tree not present")


@pytest.fixture(scope="module")
def cache():
    return json.loads((V1_BACKEND / ".boot_pin_cache.json").read_text(encoding="utf-8"))


def test_the_cache_is_keyed_on_v1s_present_source(cache):
    """V1's own key function over V1's own file list: the cache V1 boots from today."""
    files = lift(["_PIN_SRC_FILES"])["_PIN_SRC_FILES"]
    h = hashlib.sha256()
    for name in files:
        path = V1_BACKEND / name
        h.update(path.read_bytes() if path.is_file() else b"\x00")
    assert h.hexdigest() == cache["key"] == pin.PIN_CACHE_KEY


def test_every_value_is_the_caches(cache):
    c = cache["pin"]
    assert pin.HPCC_UA_KJHK == c["HPCC_UA"]
    assert pin.HPCC_LIQ_DES_LIVE_KGH == c["HPCC_LIQ_DES_LIVE"]
    assert pin.HPCC_NC_DES_LIVE == c["HPCC_NC_DES_LIVE"]
    assert pin.HPCC_RAISE_DES_LIVE_KGS == c["M_HPCC_DES_LIVE"]
    assert dict(pin.REACT_TEAR_DES_KMOLH) == c["REACT_TEAR_DES"]
    assert pin.REACT_L_FEED_DES == c["REACT_L_FEED_DES"]
    assert pin.REACT_X_DES == c["REACT_X_DES"]
    k = c["REACT_KIN_CAL"]
    assert (pin.REACT_A2_PRE_PER_H, pin.REACT_KEQ_OV_REF, pin.REACT_T_REF_K,
            pin.REACT_BIURET_A) == (k["A2"], k["Keq_ov_ref"], k["T_ref_K"], k["biu_A"])
    a = c["REACT_KIN_ANCHOR"]
    assert (list(pin.REACT_ANCHOR_T_NODES_C), pin.REACT_ANCHOR_LEVEL_FRAC,
            pin.REACT_ANCHOR_VDOT_M3H, pin.REACT_ANCHOR_M_FEED_KGH) == (
        a["T_node"], a["lvl"], a["vdot"], a["m_feed"])
    assert list(pin.REACT_NODE_SS_DES_C) == c["REACT_NODE_SS_DES"]
    assert pin.REACT_CP_MELT_KJKGK == c["REACT_CP_MELT"]


def test_the_condenser_conductance_is_the_import_time_back_solve():
    """V1's pin back-solves 322E002's UA on the synthetic design feed, which the port does at
    import. The port solves it on the standard atmosphere and gravity (handoffs B-6, B-7,
    decided 2026-10-07), so its motive ammonia is a hair different and its UA 9.6e-10 below the
    cache's, solved on V1's 1.013 bar and 9.81 (the same line on the same constants is ``==``,
    `tests/equivalence/test_carbamate_condenser_equivalence.py`)."""
    from ureasim.units.synthesis.carbamate_condenser import UA_KJHK
    assert UA_KJHK / pin.HPCC_UA_KJHK - 1.0 == pytest.approx(-9.62e-10, abs=0.05e-10)


def test_the_pinned_profile_is_the_import_time_fixed_point():
    """The pin restores the node profile and the melt's heat capacity the reactor already solves at
    import; only the kinetics move, re-solved on the seed's live feed (A2 +1.5 %, the biuret
    pre-exponential +14.6 %, the reference temperature 2.7 K lower)."""
    assert list(pin.REACT_NODE_SS_DES_C) == list(r.NODE_PROFILE_DES)
    assert pin.REACT_CP_MELT_KJKGK == r.CP_MELT_KJKGK
    assert pin.REACT_A2_PRE_PER_H / r.KINETICS.a2_pre_per_h == pytest.approx(1.01455, abs=1e-5)
    assert pin.REACT_BIURET_A / r.KINETICS.biuret_a == pytest.approx(1.14583, abs=1e-5)
    assert pin.REACT_T_REF_K - r.KINETICS.t_ref_k == pytest.approx(-2.7483, abs=1e-4)
