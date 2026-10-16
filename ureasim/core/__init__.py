"""Flowsheet primitives: the stream, the node, the pipe between them, and the graph.

This package knows about *flowsheets*, never about a specific piece of equipment. Nothing
here may import from `ureasim.control`, `ureasim.units`, `ureasim.engine`, `ureasim.net` or
`ureasim.hmi`; it may import `ureasim.thermo` and `ureasim.data`.

Package map

    numeric            limiters and the shared time factor
    units_of_measure   the unit conventions and the constants that convert between them
    packet             a closed stream sample: mass, temperature, cp and composition as one
    transport          plug-flow dead time of a line, and the routes packets travel down
    signal             what an INDICATOR does to a value: lag, dead time, FOPTD
    node               inventory: vapour-space pressure, liquid holdup, level indication
    stream             the published process-stream record behind the stream inspector
    flowsheet          the directed graph, its declared recycle tears, and the solve order

The division that matters here is `transport` against `signal`. Transport moves MATERIAL,
so it carries mass and composition and it changes what a downstream vessel receives. A
signal block moves a NUMBER to a screen and changes nothing about the plant. Applying a
signal lag to a state is an invented time constant, which the agent directives forbid.
"""
