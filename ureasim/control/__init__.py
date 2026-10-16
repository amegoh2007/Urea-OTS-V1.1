"""DCS control layer: the regulatory loops, the valves they drive, and the trips above them.

May import `ureasim.core`, `ureasim.thermo`, `ureasim.data`. Nothing here knows which piece
of equipment it is attached to — a level controller does not know it is on 323F004 — so a
unit supplies the tags, the tuning and the design point, and this package supplies the law.

Package map

    valve         IEC 60534-2-1 control valve, check valve and gravity discharge
    process_loop  the engineering-unit I-PD loop, and the flow loop built around it
    controller    the per-cent-of-span faceplate controller, with slew limiting and OOS
    ratio         a ratio master with external-reset feedback, and the open-loop demand
    interlocks    latching trips: plain, armed, reset-banded and self-clearing
    jet_pump      liquid-liquid constant-area jet pump: the momentum closure, its
                  single-root proof and the geometry back-solve

Two controllers, deliberately
-----------------------------
`process_loop.ProcessLoop` and `controller.Controller` are both velocity-form I-PD, and they
are NOT duplicates. V1 uses both: the per-cent-span form on SIC-321950 and SIC-321951, the
engineering-unit form on every other tag. They differ on the bad-PV band, on whether a bad
PV drops the loop to MAN, on output slew limiting, on the OOS mode and on the Td = -1
sentinel. Merging them would declare a 183 C reactor measurement failed. The full comparison
is in `process_loop`'s module docstring.

Logic and action are separate
-----------------------------
`interlocks` decides whether a trip is LATCHED. It does not stop a pump, shut a valve or
force a controller to manual: a trip's action list is plant knowledge and belongs to the unit
that owns the equipment. A unit reads `interlock.latched` and does what its own trip schedule
says.
"""
