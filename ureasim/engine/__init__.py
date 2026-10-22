"""Simulation runtime: plant state, execution scheduler with recycle tearing, the fixed-step
integrator, the trend historian, and the state-to-UI snapshot.

Headless by rule. The engine runs behind the console server (`ureasim.net.server`): physics
and presentation share no object, and the test suites and the Phase 7 runners drive it with no
display, so **nothing in this package may import Qt**.
The console's end of the link lives in `ureasim.hmi.bridge`.

Package map

    state       the plant clock, the recycle tears (one step late by construction, A-10), the
                units, their controllers, the operator's positions and the boundary values
    schedule    V1's section order as checked data: the five sources, the declared tears
    scheduler   the tick: every unit once, in order, the tears committed at its end
    plant       the plant's schedule, one module per plant section, and its design seed
    simulator   the fixed 0.1 s step paid out of the wall clock at a pacing (A-14)
"""
