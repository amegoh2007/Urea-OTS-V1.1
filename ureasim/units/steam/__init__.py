"""Unit 329 — the steam network: the 25 bar a supply, 329D005, 329D009 and 322D001A/B.

The battery-limit steam is let down into the three drums; their vapours are the headers the
plant's steam users draw on (handoff B-68: every simulated user live on its header, the rest at
their PFD rows), and their condensate cascades down to 322D001, where 322E002 raises the LP steam.

Package map

    drums           each drum's water over its whole vessel, heads included, and the level its
                    transmitter reads between its taps (decision 33's class)
    steam_valves    the butterflies on V1's anchored ISA-75.01 law; PV-329205A / B and
                    LV-329502 / 503 / 504 on Flowserve's trims (decision 23), the letdowns
                    choking on their saturated condensate (decision 31)
    header_control  PIC-329204 with trip 21.2's set point and HV-329601's forcing, PIC-329205's
                    split range, the PIC-329207 trio on its master set point, the level loops
    steam_network   the network stepped: the vapour nodes as lumped saturated capacitances,
                    semi-implicit, the drums' water balances, the superheated inlets boiling
                    their drums' water and the letdowns flashing (handoff B-70), the safety
                    valves (decision 32)
"""
