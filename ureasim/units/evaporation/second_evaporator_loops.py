"""324E003 and 324F003's four controllers: TIC-324002, PIC-329212, PIC-324203 and LIC-324501.

What this holds
---------------
The factories that seed stage 2's controllers, moved verbatim from `second_evaporator` (session
133, decision 252, to keep that module within 600 lines); `second_evaporator` re-exports them and
holds `SecondEvaporatorLoops`, the class a saved exercise names.

Process utility
---------------
Each factory builds one loop seeded at its design steady state, so the plant starts on its design
point with every controller's output at the stroke that passes the design flow.

Sources
-------
V1 ``backend/main.py``, the stage's controllers (``State.__init__``); the gains and seeds in
`ureasim.data.unit_324`, each with its source.
"""

from __future__ import annotations

from ureasim.control.process_loop import ProcessLoop
from ureasim.data.control_valves import PV_329212
from ureasim.data.unit_324 import (
    E003_OP_DES_PCT,
    E003_PCHEST_DES_BARA,
    E003_T_DES_C,
    F003_LEVEL_SP_PCT,
    F003_P_DES_BARA,
    LIC_324501_KC,
    LIC_324501_OP_DES_PCT,
    LIC_324501_TI_S,
    LV_324501A_OP_DES_PCT,
    PIC_324203_KC,
    PIC_324203_TI_S,
    PIC_329212_KC,
    PIC_329212_TI_S,
    PV_324203_OP_DES_PCT,
    PV_329212_OP_DES_PCT,
    PV_329212_XT,
    TIC_324002_KC,
    TIC_324002_TI_S,
)
from ureasim.data.unit_329 import P_MP_BARA
from ureasim.data.unit_335 import LIC_324501_X_DES_PCT
from ureasim.units.steam_chest import ChestValve

# ======================================================================================
# The four controllers, seeded as V1 seeds them, on the table's gains per cent of span
# ======================================================================================

def tic_324002() -> ProcessLoop:
    """TIC-324002, the melt-temperature master: its output is the chest-pressure DEMAND [bar a]
    handed to PIC-329212 as a remote set point."""
    return ProcessLoop(
        tag="TIC-324002", Kc=TIC_324002_KC, Ti=TIC_324002_TI_S, Td=0.0, act=+1.0,
        op=E003_PCHEST_DES_BARA, sp=E003_T_DES_C,
        pv=E003_T_DES_C, pv1=E003_T_DES_C, pv2=E003_T_DES_C,
        op_lo=0.0, op_hi=P_MP_BARA, sp_lo=0.0, sp_hi=200.0)


#: PV-329212 as the port runs it, on its vendor's trim (DN 80 balanced Neldisc, Cv 150, from 54.68 %; decided 2026-10-14; the S-Disc shape since decision 170),
#: and as V1 runs it, linear from V1's stroke — which the equivalence harness keeps.
PV_329212_CHEST = ChestValve(PV_329212_OP_DES_PCT, PV_329212.characteristic, PV_329212_XT)
V1_CHEST = ChestValve(E003_OP_DES_PCT)


def pic_329212(valve: ChestValve = PV_329212_CHEST) -> ProcessLoop:
    """PIC-329212, the 324E003 chest-pressure slave, in CASCADE under TIC-324002: its output is
    the PV-329212 stroke [%], seeded on ``valve``'s design stroke."""
    return ProcessLoop(
        tag="PIC-329212", Kc=PIC_329212_KC, Ti=PIC_329212_TI_S, Td=-1.0, act=+1.0, mode="CAS",
        op=valve.op_des_pct, sp=E003_PCHEST_DES_BARA,
        pv=E003_PCHEST_DES_BARA, pv1=E003_PCHEST_DES_BARA, pv2=E003_PCHEST_DES_BARA,
        op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=P_MP_BARA)


def pic_324203() -> ProcessLoop:
    """PIC-324203, the 324F003 vacuum: reverse acting, a pressure under its set point admits
    more false air. Its output is the PV-324203 stroke [%]."""
    return ProcessLoop(
        tag="PIC-324203", Kc=PIC_324203_KC, Ti=PIC_324203_TI_S, Td=-1.0, act=+1.0,
        op=PV_324203_OP_DES_PCT, sp=F003_P_DES_BARA,
        pv=F003_P_DES_BARA, pv1=F003_P_DES_BARA, pv2=F003_P_DES_BARA,
        op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=1.0)


def lic_324501(vendor: bool = True, ac4: bool = True) -> ProcessLoop:
    """LIC-324501, the melt level: direct acting. On AC4 PC35.2 its output X sets PIC-335201's set
    point and LV-324501B's stroke, seeded where the set point is the design header, 35 % (decision
    224); with ``ac4`` False it is the stroke the route selector hands to one valve, seeded at
    LV-324501A's design stroke on its vendor trim (decision 150), or V1's 75 % with ``vendor``
    False."""
    seed = (LIC_324501_OP_DES_PCT if not vendor
            else LIC_324501_X_DES_PCT if ac4 else LV_324501A_OP_DES_PCT)
    return ProcessLoop(
        tag="LIC-324501", Kc=LIC_324501_KC, Ti=LIC_324501_TI_S, Td=-1.0, act=-1.0,
        op=seed, sp=F003_LEVEL_SP_PCT,
        pv=F003_LEVEL_SP_PCT, pv1=F003_LEVEL_SP_PCT, pv2=F003_LEVEL_SP_PCT,
        op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=100.0)


__all__ = ["tic_324002", "PV_329212_CHEST", "V1_CHEST", "pic_329212", "pic_324203", "lic_324501"]
