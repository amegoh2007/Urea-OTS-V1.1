"""Urea Plant Operator Training Simulator, version 1.1.

A dynamic model of a 1750 MTPD Stamicarbon-type CO2-stripping urea plant, with a PyQt6
DCS-replica HMI.

Layering (imports flow downward only):

    hmi      PyQt6 presentation .................. no physics
    engine   integrator, state, scheduler, historian
    units    unit operations
    control  PID / ratio / valves / jet pump / interlocks
    core     stream, node, flowsheet primitives
    thermo   property and VLE packages ........... no plant knowledge
    data     design basis, tag registry, screen layout
"""

__version__ = "1.1.0"
