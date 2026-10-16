"""320K002 — the CO2 feed compressor, as an automated boundary feed.

What this models
----------------
The four-stage machine that takes CO2 from the ammonia plant's battery limit and puts it into
the synthesis loop. It is the plant's rate-setting machine: the N/C ratio block divides by its
delivery, so every ammonia flow on the site follows from what this machine does.

320K002 is outside the simulator's scope (decided by the process engineer on 2026-10-08,
As-Built §LXII.1): it is "a fully automated boundary feed", its speed governor and its surge
protection hardwired "to perfectly match the synthesis loop's demand without any operator
intervention or faceplate exposure". What the boundary keeps is what the loop sees of the
machine — the CO2 rate the plant's load calls for, pushed into the discharge line at whatever
pressure the line presents. What it drops is the machine itself: no curve, no speed, no
surge and no stonewall, so no fitted or digitised map stands between the demand and the loop.

The demand is the battery-limit CO2 rate, PFD 101's ``CO2_DES_KGH`` at design. It is the
instructor's boundary condition (``co2_set``), never a trainee's control.

Why a perfect governor, and not an open boundary
------------------------------------------------
The plant's machine is FLOW controlled: the turbine's governor trims speed to hold the demanded
rate, and its antisurge recycle keeps it on its curve at every rate. An open-loop machine on this
flowsheet is divergent — V1 measured 140.7 to 134.7 bar a over 16,000 s: a falling loop pressure
pulls the line down, the machine rides up its curve and delivers more CO2, the extra CO2
condenses into carbamate and leaves the vapour space, and the pressure falls further. A governor
that holds the demand exactly breaks that loop by construction.

Equation
--------
    delivery = max(demand, 0)          [kg/h, into the discharge line's node]

Source: the process engineer's decision of 2026-10-08. V1 ``backend/main.py`` ran the machine on
a parabola fitted to two representative numbers under an integral governor (tau 8 s);
``tests/equivalence/test_co2_line_equivalence.py`` asserts both.
"""

from __future__ import annotations


def delivery_kgh(demand_kgh: float) -> float:
    """CO2 the boundary pushes into the discharge line [kg/h]: the demand, never negative.

    Process utility
    ---------------
    What the hardwired governor holds. The discharge line's node, its check valve and its vent
    then decide where the CO2 goes: into the loop at the tie-in, or out of PV-322203 when the
    tie-in is shut. A governor cannot drive a machine backwards, so a negative demand is zero.
    """
    return max(demand_kgh, 0.0)


__all__ = ["delivery_kgh"]
