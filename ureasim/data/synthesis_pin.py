"""The synthesis loop's boot pin — the design constants V1 back-solves from its settled loop.

What this is
------------
Six of the HP synthesis loop's anchors cannot be written down from a document: they are what the
assembled loop does at its own design seed. V1 computes them at start-up (``_pin_hpcc_ua``, ``main.py``
12095-12350): it settles the plant for 18 000 ticks in cascade, captures the reactor's feed from one
step of the manual seed, back-solves the recycle tear and the kinetics against the PFD's extents, then
settles 3000 ticks more for the steam sizing. Because that takes twenty seconds, V1 caches the result
in ``backend/.boot_pin_cache.json`` keyed by a SHA-256 of its model sources, and boots from the cache
whenever the key matches. The values below ARE that cache — the constants V1 runs on — and
``tests/data/test_synthesis_pin.py`` proves both halves: that the cache's key is the hash of V1's
present source, and that every value here is the cache's to the last bit.

Each is the reference of a term that vanishes at the design seed, so each holds the design point the
PFD publishes; none is a free parameter tuned to a response.

Not carried (the reachable-only rule): ``REACT_MASS_DES``, ``EJ_MOTIVE_DES_LIVE`` and
``REACT_W_FEED_DES``, which nothing in V1 reads after the pin; ``M_USERS_LP``, the steam network's V1
sizing, which the port's network replaces with the PFD's closure (decision 47, handoff B-68); the
322C001 pins, which `units.absorption.lp_absorber.design_pin` re-solves. ``M_HPCC_DES_LIVE`` is carried
as the reference of the HPCC's raising ratio, which the network sees on its PFD row.

Source: V1 ``backend/main.py`` ``_pin_hpcc_ua``, ``_collect_pin``, ``_apply_pin``; ``backend/
.boot_pin_cache.json`` (key 81269104...d56c, written 2026-09-18 00:45, after ``main.py``'s last edit).
"""

from __future__ import annotations

from types import MappingProxyType

__all__ = [
    "PIN_CACHE_KEY",
    "HPCC_UA_KJHK",
    "HPCC_LIQ_DES_LIVE_KGH",
    "HPCC_NC_DES_LIVE",
    "HPCC_RAISE_DES_LIVE_KGS",
    "REACT_TEAR_DES_KMOLH",
    "REACT_L_FEED_DES",
    "REACT_X_DES",
    "REACT_A2_PRE_PER_H",
    "REACT_KEQ_OV_REF",
    "REACT_T_REF_K",
    "REACT_BIURET_A",
    "REACT_ANCHOR_T_NODES_C",
    "REACT_ANCHOR_LEVEL_FRAC",
    "REACT_ANCHOR_VDOT_M3H",
    "REACT_ANCHOR_M_FEED_KGH",
    "REACT_NODE_SS_DES_C",
    "REACT_CP_MELT_KJKGK",
]

#: The cache's key: the SHA-256 of V1's model sources the pin was settled on.
PIN_CACHE_KEY = "81269104a1fecd86c72c13501e914fd9feeab90c6cc9cb6536415255e9afd56c"

# ======================================================================================
# 322E002, the carbamate condenser
# ======================================================================================

#: The shell's conductance [kJ/(h.K)], back-solved so the gate-1 design quench lands TT-322010 on
#: 170.0 C on the synthetic design feed at the reconciled W0 / L0. Source: V1 ``HPCC_UA``.
HPCC_UA_KJHK = 1610148.4998608052

#: The condenser's liquid make at the manual design seed [kg/h] — LT-322E002's fill reference and the
#: reactor line's design flow. The synthetic HPCC_LIQ_DES_KGH understates it by about 2 %, which left
#: the level winding past its NLL. Source: V1 ``HPCC_LIQ_DES_LIVE``.
HPCC_LIQ_DES_LIVE_KGH = 189257.54705597984

#: The design melt's N/C [-], the anchor of 322E002's bubble-point N/C lift, so that the melt the
#: seed makes bubbles at 144.2 bar a. Source: V1 ``HPCC_NC_DES_LIVE``.
HPCC_NC_DES_LIVE = 3.0785808282834624

#: The LP steam 322E002 raises at the manual design seed [kg/s], its q_steam over 2120 kJ/kg: the
#: reference of the raising ratio the LP header sees on its PFD row (decision 47's class).
#: Source: V1 ``M_HPCC_DES_LIVE``.
HPCC_RAISE_DES_LIVE_KGS = 29.519694361307973

# ======================================================================================
# 322R001, the reactor
# ======================================================================================

#: The recycle tear [kmol/h]: the reactor's seed feed less the feed the PFD's two product vectors
#: imply run back through both reactions — what the reduced flowsheet counts twice. Subtracted from
#: the feed times the CO2 load ratio (`reactor.reactor_322r001`). Source: V1 ``REACT_TEAR_DES``.
REACT_TEAR_DES_KMOLH = MappingProxyType({
    "CO2": 5.840982601357155,
    "CH4": 0.140197531736431,
    "H2": 0.10240529819914546,
    "H2O": -5.066654296402703,
    "N2": 0.894566126575107,
    "NH3": 129.1160457970018,
    "O2": -0.025599999999999845,
    "Urea": -4.727722289752363,
    "Biuret": 0.0,
})

#: The seed's reactor-feed N/C [-], AT-322701's partition anchor. Source: V1 ``REACT_L_FEED_DES``.
REACT_L_FEED_DES = 3.072961

#: The design per-pass conversion [-]: the PFD's urea extent over the seed feed's CO2 — the
#: conversion-deficit slip's reference. Source: V1 ``REACT_X_DES``.
REACT_X_DES = 0.5418221209090279

#: The rate laws' calibration, re-solved on the seed's live feed so its extents are the PFD's
#: 1302.27 and 2.414 kmol/h: the dehydration pre-exponential [1/h], the overall equilibrium constant
#: [m3/kmol] at its reference temperature [K], the biuret pre-exponential [m3/(kmol.h)]
#: (`reactor_column.ColumnKinetics`). Source: V1 ``REACT_KIN_CAL``.
REACT_A2_PRE_PER_H = 4419528381826.887
REACT_KEQ_OV_REF = 0.8442273226700852
REACT_T_REF_K = 450.11039545151175
REACT_BIURET_A = 3607598.160057515

#: The column state the calibration was solved at — the seed step's own [deg C, -, m3/h, kg/h].
#: Source: V1 ``REACT_KIN_ANCHOR``.
REACT_ANCHOR_T_NODES_C = (170.72092895078652, 174.89256347417546, 179.22812478297084,
                          183.00000000000003)
REACT_ANCHOR_LEVEL_FRAC = 0.8
REACT_ANCHOR_VDOT_M3H = 227.4996553830439
REACT_ANCHOR_M_FEED_KGH = 250638.93497140185

#: The design node profile [deg C] and the melt's back-solved heat capacity [kJ/(kg.K)], both as the
#: pin restores them — equal to the import-time thermal-kinetic fixed point
#: (`reactor.NODE_PROFILE_DES`, `reactor.CP_MELT_KJKGK`). Source: V1 ``REACT_NODE_SS_DES``,
#: ``REACT_CP_MELT``.
REACT_NODE_SS_DES_C = (170.72092895078652, 174.89256347417546, 179.22812478297084,
                       183.00000000000003)
REACT_CP_MELT_KJKGK = 4.740797681190962
