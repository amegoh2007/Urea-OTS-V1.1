"""323E011 / 323D011's three controllers — PIC-323203, LIC-323503 and FIC-323418 — seeded as V1 seeds them.

What it models
--------------
The loops on the flash condenser's gas node and its level tank: PIC-323203 on the node pressure
through PV-323203, LIC-323503 on 323D011's level through LV-323503's total 718 draw, and FIC-323418
on the 718B leg to 323E003. Each is seeded ``pv == sp == pv1 == pv2`` at its design point, so the
first tick moves nothing. LIC-323503 reads LT-323503 between its taps (decision 233, handoff
B-156) and is seeded on that reading, 26.77 % at the design holdup; ``taps=False`` is V1's 50 %.

Source
------
V1 ``backend/main.py`` ``State.__init__`` (6831-6835, 6893-6898, 6916-6937, 6981-6990); the design
data in `ureasim.data.unit_323e011`. Split from `flash_condenser` on 2026-11-16 (session 123),
which re-exports the three factories.
"""

from __future__ import annotations

from ureasim.control.process_loop import FlowLoop, ProcessLoop
from ureasim.data.unit_323e011 import (
    D011_LVL_SP_PCT,
    E011_P_BARA,
    FIC418_OP_DES_PCT,
    FIC_323418_KC,
    FIC_323418_SP_HI_M3H,
    FIC_323418_TD_S,
    FIC_323418_TI_S,
    FT_323418_TAU_S,
    FV418_CHAR,
    LIC_323503_KC,
    LIC_323503_TI_S,
    LT_323503_DES_PCT,
    LV503_OP_DES_PCT,
    M718B_DES_KGH,
    PIC_323203_KC,
    PIC_323203_SP_HI_BARA,
    PIC_323203_SP_LO_BARA,
    PIC_323203_TD_S,
    PIC_323203_TI_S,
    RHO_718_KGM3,
)
from ureasim.units.recirc.flash_gas_node import PV_323203_TRIM

__all__ = ["pic_323203", "lic_323503", "fic_323418"]


# ======================================================================================
# The three controllers, seeded on their design points; LIC-323503 on its tap reading (decision 233)
# ======================================================================================

def pic_323203(op_des_pct: float = PV_323203_TRIM[0]) -> ProcessLoop:
    """PIC-323203, the node pressure. DIRECT acting: a node above set point opens PV-323203.

    Seeded as V1 seeds it, but at PV-323203's vendor design stroke (V1's 25 % is
    ``E011_PV_OP_DES_PCT``) and with the table's gain rescaled to PT-323203's span — 60 %/bar,
    not V1's 0.60 (decided 2026-09-27, handoff B-32)."""
    return ProcessLoop(
        tag="PIC-323203", Kc=PIC_323203_KC, Ti=PIC_323203_TI_S, Td=PIC_323203_TD_S, act=-1.0,
        op=op_des_pct, sp=E011_P_BARA, pv=E011_P_BARA, pv1=E011_P_BARA, pv2=E011_P_BARA,
        op_lo=0.0, op_hi=100.0, sp_lo=PIC_323203_SP_LO_BARA, sp_hi=PIC_323203_SP_HI_BARA)


def lic_323503(taps: bool = True) -> ProcessLoop:
    """LIC-323503, the 323D011 level. DIRECT acting: a level above set point raises the total
    718 draw demand. Seeded on LT-323503 between its taps, the design holdup's 26.77 % (decision
    233); ``taps=False`` is V1's 50 %."""
    r = LT_323503_DES_PCT if taps else D011_LVL_SP_PCT
    return ProcessLoop(
        tag="LIC-323503", Kc=LIC_323503_KC, Ti=LIC_323503_TI_S, Td=0.0, act=-1.0,
        op=LV503_OP_DES_PCT, sp=r, pv=r, pv1=r, pv2=r, op_lo=0.0, op_hi=100.0, sp_lo=0.0,
        sp_hi=100.0)


def fic_323418() -> FlowLoop:
    """FIC-323418, the 718B lean-carbamate leg to 323E003 — a VOLUMETRIC loop in m3/h."""
    v = M718B_DES_KGH / RHO_718_KGM3
    loop = ProcessLoop(
        tag="FIC-323418", Kc=FIC_323418_KC, Ti=FIC_323418_TI_S, Td=FIC_323418_TD_S, act=+1.0,
        op=FIC418_OP_DES_PCT, sp=v, pv=v, pv1=v, pv2=v,
        op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=FIC_323418_SP_HI_M3H)
    return FlowLoop(loop=loop, design_flow=M718B_DES_KGH, op_des=FIC418_OP_DES_PCT,
                    tau_s=FT_323418_TAU_S, rho_kgm3=RHO_718_KGM3, characteristic=FV418_CHAR)
