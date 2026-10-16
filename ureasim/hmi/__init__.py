"""PyQt6 operator console — presentation only.

This package may read a published engine snapshot and emit operator commands. It contains
no process physics: no bubble point, no mass balance, no controller arithmetic. Everything
it needs crosses `ureasim.engine.bridge.EngineBridge`.

    theme          colour tokens and fonts, transcribed from the V1 stylesheet
    state_access   dot-path resolution, formatting, shared-tag resolution
    widgets/       the eleven overlay element widgets
    screen_view    one process screen: drawing plus overlays, scaled to fit
    main_window    tab bar, the ten screens, status bar
"""
