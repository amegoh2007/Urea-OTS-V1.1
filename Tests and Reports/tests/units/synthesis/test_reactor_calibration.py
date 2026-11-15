"""322R001's kinetic calibration — `ureasim.units.synthesis.reactor_calibration`.

Pinned on the reactor's own design inputs: the seed calibration's pre-exponential makes the column
march reproduce the PFD's dehydration extent, its biuret pre-exponential reproduces the PFD's biuret
extent exactly (the rate is linear in it), and its equilibrium constant is the mass-action
quotient at the ceiling composition; the joint thermal-kinetic fixed point the plant runs on lands
the profile on the PFD's overflow temperature and still reproduces the extent.
"""

from __future__ import annotations

import dataclasses

import pytest

from ureasim.thermo.kinetics import biuret_k_m3_kmol_h
from ureasim.units.synthesis import reactor as r
from ureasim.units.synthesis.reactor_calibration import calibrate_kinetics
from ureasim.units.synthesis.reactor_column import node_liquid_volumes, urea_extent_pfr

FEED = r._HPCC_DES.feed_kmolh
LEVEL = r.LEVEL_NLL_PCT / 100.0


def _extent(kinetics, profile) -> float:
    xi, _ = urea_extent_pfr(FEED, profile, r.ZETA_NODES, r.AREA_M2, r.LIQ_H_M, LEVEL,
                            r.VDOT_DES_M3H, dataclasses.replace(kinetics, biuret_a=0.0))
    return xi


@pytest.fixture(scope="module")
def seed():
    return calibrate_kinetics(FEED, r._SEED_PROFILE_C, r.ZETA_NODES, r.AREA_M2, r.LIQ_H_M, LEVEL,
                              r.VDOT_DES_M3H, r.XI_UREA_DES, r.XI_BIURET_DES, r.X_INF,
                              r.OVERFLOW_DES_KMOLH["Urea"])


def test_the_seed_calibration_reproduces_its_anchors(seed):
    assert seed == r._SEED_KINETICS
    assert _extent(seed, r._SEED_PROFILE_C) == pytest.approx(r.XI_UREA_DES, rel=1e-12)
    c_urea = r.OVERFLOW_DES_KMOLH["Urea"] / r.VDOT_DES_M3H
    vols = node_liquid_volumes(r.ZETA_NODES, r.AREA_M2, r.LIQ_H_M, LEVEL)
    biuret = sum(seed.biuret_a * biuret_k_m3_kmol_h(t, 1.0) * c_urea * c_urea * v
                 for v, t in zip(vols, r._SEED_PROFILE_C) if v > 0.0)
    assert biuret == pytest.approx(r.XI_BIURET_DES, rel=1e-12)


def test_the_equilibrium_constant_is_the_ceiling_quotient(seed):
    v = r.VDOT_DES_M3H
    xi = r.X_INF * FEED["CO2"]
    quotient = (((FEED.get("Urea", 0.0) + xi) / v) * ((FEED["H2O"] + xi) / v)
                / (((FEED["NH3"] - 2.0 * xi) / v) ** 2 * ((FEED["CO2"] - xi) / v)))
    assert seed.keq_ov_ref == pytest.approx(quotient, rel=1e-14)
    assert seed.t_ref_k == pytest.approx(sum(r._SEED_PROFILE_C) / len(r._SEED_PROFILE_C) + 273.15)


def test_the_fixed_point_lands_on_the_pfd():
    assert r.NODE_PROFILE_DES[0] > r.FEED_T_DES_C
    assert r.NODE_PROFILE_DES[-1] == pytest.approx(r.OVERFLOW_T_DES_C, abs=1e-9)
    assert _extent(r.KINETICS, r.NODE_PROFILE_DES) == pytest.approx(r.XI_UREA_DES, rel=1e-12)
    assert r.KINETICS.keq_ov_ref == r._SEED_KINETICS.keq_ov_ref
