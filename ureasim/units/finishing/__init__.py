"""Unit 335 (screen 324-1B's finishing side) — what the plant does to its melt before granulation.

The granulator itself is outside the simulated plant: the forward melt leaves at the battery limit,
its header's pressure (PIC-335201) a boundary input. What is simulated is the additive dosed into
the melt on its way there.

Package map

    uf85_dosing         FFIC-335406 over FIC-335405 and 335P002A / B: UF85 in ratio to the melt
                        LV-324501A sends forward, joined at LV-324501's selector (PFD 697 into
                        402G, making 609); LV-324501B its hard permissive
"""
