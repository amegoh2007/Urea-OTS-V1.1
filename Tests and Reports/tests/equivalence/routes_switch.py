"""V1's product-line routes on the isometrics' geometry — handoff A-11, decided 2026-10-07.

What this is
------------
V1 builds each product-line route with ``_proc_route(source, destination, carrier, length, rho)``
on one bore, 187.1 mm, and a plant-layout length (25, 15, 15, 30, 40 m). The process engineer
decided the routes run on the as-built isometrics (`ureasim.data.process_routes`). An equivalence
harness hands V1's block the decided route through `decided`: V1's own ``ConsequenceRoute`` on the
port's design dead time, so V1's transport code runs unchanged on the measured geometry and the
rest of the block is proved against the port. `v1_verbatim` is V1's own route, for the tests that
assert both sides (`test_core_equivalence.py`).
"""

from __future__ import annotations

from ureasim.data.process_routes import PROCESS_ROUTES

#: V1's lengths [m], `main.py` 6239-6247, by route.
V1_LENGTHS_M = {"322E001_TO_323C003": 25.0, "323C003_TO_323F004": 15.0,
                "323F004_TO_323F010": 15.0, "323F010_TO_323D002": 30.0,
                "323D002_TO_324E001": 40.0}


def decided(ns: dict, name: str):
    """V1's ``ConsequenceRoute`` for ``name`` on the port's measured dead time."""
    r = PROCESS_ROUTES[name]
    consequence = ns["_proc_route"].__globals__["consequence"]
    return consequence.ConsequenceRoute(r.source, r.destination, r.design_carrier_kgh,
                                        r.design_dead_time_s)


def v1_verbatim(ns: dict, name: str, rho: float):
    """V1's own route for ``name``: its layout length on its 187.1 mm bore."""
    r = PROCESS_ROUTES[name]
    return ns["_proc_route"](r.source, r.destination, r.design_carrier_kgh, V1_LENGTHS_M[name],
                             rho)
