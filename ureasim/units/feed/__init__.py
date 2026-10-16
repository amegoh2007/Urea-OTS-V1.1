"""Unit 321 — the NH3 pumping station.

Ammonia arrives at the battery limit, is buffered in 321D003, and is pushed into the
synthesis loop by the two 321P002 triplex pumps through the 322F001 ejector. The N/C feed
ratio block lives here too, because it is the ammonia side of the ratio that it commands.

Package map

    pump        321P002 A/B, triplex positive-displacement, and the VOITH scoop
    feed_drum   321D003 inventory, temperature, and the suction instruments
    station     the section step: ratio cascade, pumps, drum, motive stream out

Where this section ends
-----------------------
At the motive ammonia stream, after its battery-limit transit. The 322F001 ejector is
synthesis equipment and belongs to `ureasim.units.synthesis`; this package hands over the
stream and the two anchoring fractions (`phi_motive`, `phi_forward`) and stops there, which
is where the plant's own unit boundary is.

What comes in from elsewhere
----------------------------
The live CO2 feed to the loop, in t/h, computed by the 320K002 discharge node. The ratio
block divides by it, so the section cannot be stepped without it — and the validity gate on
that division is the reason `ratio_pv_bad` exists.
"""
