"""Deviation-consequence physics shared by every vessel, valve and pump.

Why this sub-package exists
---------------------------
In V1 each written-up deviation scenario was wired into `main.py` at the one tag it had been
written up against, with its own hand-picked constant. Losing the liquid seal on 323C003 and
losing it on 328C004 are the same event — a drain nozzle uncovers and the vessel's gas
inventory escapes through a valve sized for liquid — yet one produced 5000 kg/h of gas and
the other produced nothing at all, because nobody had written that scenario down yet. A
trainee who learns the plant on a model like that learns the model's authoring history.

Everything here is therefore written once, generically, and called by every unit that has the
equipment it describes. V1 collected the same functions in `backend/consequence.py`, and this
sub-package is that file split along its own section headings, one physical concept per
module, per the agent directives §1.

Package map

    seal             the liquid seal over a drain nozzle, and the IEC 60534 gas
                     blow-through the same valve trim passes once the nozzle uncovers
    crystallisation  the mushy-zone flow restriction as a urea-bearing line cools

The design-anchor contract
--------------------------
The engine is pinned bit-exactly at the 1750 MTPD / 100 % load design point. Every function
in this sub-package is therefore written so that at the design arguments it returns EXACTLY
zero extra effect — `seal_fraction` is 1.0 at any normal level, `blowthrough_kgh` carries a
`(1 - seal)` factor and so is 0.0, `mushy_flow_factor` is 1.0 above the crystallisation
boundary. They are also monotone and bounded, so none of them can drive an integrator to a
rail, and every one of them is continuous in its arguments, so a consequence can be undone by
correct operator action instead of being latched by a state override.

Source: V1 `backend/consequence.py`.
"""
