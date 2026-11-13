"""The plant's boundary values and the operator's seeds — what the schedule does not compute.

What this is
------------
The battery limits and the boundaries V1 writes as constants — the numbers the scheduled units
read but no scheduled unit produces: 323C005's atmospheric pressure, which 324F002 discharges
against, the 335 melt header's PIC-335201 (the granulator is outside the simulated plant; only its
UF85 dosing is scheduled), and 322E006's cooling water. Since session 39
the synthesis loop is scheduled (`synthesis`, `synthesis_loop`) and none of its outputs is a
boundary.

The operator's seeds are the hand valves, hand switches and set points at their design positions,
as V1's ``State`` seeds them: HIC-323605, HIC-329605, HIC-329606, HV-323D002-TIE shut, HS-322915
released, FIC-322404's 954, 322P002 running; the CO2 asked of 320K002 (V1's ``co2_set``, PFD 101's
54.618 t/h; the instructor sets it and 322-1's CO2 FEED panel steps it, decision 220), HIC-322602 at the ejector's design 74 %, HIC-322605 at 60 %, HIC-322604 at 50 %,
XV-322903 open; the auxiliary pumps' roster, each pair's A machine running and B its spare, both
in AUTO (``322P002`` is either of its pair running, which the command layer keeps), and 321P002's
EXT. OVERRIDE released (`data.operator_commands`).

The boundary sinks are the flows that leave the plant by decision: the overflows of a full 328C003,
328C004 and 322C001 (decided 2026-10-03, handoff A-15), and SV32064's relief of the CO2 line (decided
2026-10-09, handoff B-83). Each is published to the consoles
(`ureasim.engine.packet`, ``BOUNDARY_SINKS``) and the historian, and no unit takes it: it leaves the
plant's thermodynamics where it leaves its vessel.

Source: the data modules named beside each value, each carrying its own source.
"""

from __future__ import annotations

from ureasim.data.operator_commands import (
    AUX_PUMP_SEEDS,
    EXT_OVERRIDE_TAG,
    TRIP_21_HAND_SWITCHES,
)
from ureasim.data.unit_321 import CO2_DES_KGH
from ureasim.data.unit_322c001 import C001_CPL_DES_KGH
from ureasim.data.unit_322e003 import HIC604_DES_PCT
from ureasim.data.unit_322f001 import OPEN_DES_PCT as HIC_322602_DES_PCT
from ureasim.data.unit_322r001 import HIC605_DES_PCT
from ureasim.data.unit_323 import HIC_323605_DES_PCT
from ureasim.data.unit_323c005 import C005_P_BARA
from ureasim.data.unit_324 import PIC_335201_DES_BARG
from ureasim.data.unit_324_train import HV_329605_OP_DES_PCT, HV_329606_OP_DES_PCT
from ureasim.units.absorption.feed_cooler import E006_M_CW_DES_KGH

__all__ = ["BOUNDARY_SINKS", "boundary_values", "operator_seeds"]

#: The flows that leave the plant by decision (handoff A-15, 2026-10-03): each vessel's overflow
#: [kg/h] and the temperature it leaves at [deg C], as the unit's result fields name them.
#:
#: * 328C003, the hydrolyser: above its 62.27 m3 shell (on the plant it would discharge through
#:   PV-328203 to 328C002, or lift SV32852 on liquid).
#: * 328C004, desorber II: above its 15.99 m3 shell (on the plant it would carry up 750 into
#:   328C002).
#: * 322C001, the LP absorber: above its 3.60 m3 (on the plant it would carry into PV-322201's
#:   vent line, or lift SV32253).
#: * 320K002's discharge line: what SV32064 relieves of it to atmosphere (handoff B-83, decided
#:   2026-10-09), at the line's temperature.
BOUNDARY_SINKS = {
    "328C003": ("m_overflow_kgh", "t_c"),
    "328C004": ("m_overflow_kgh", "t_c"),
    "322C001": ("m_overflow_kgh", "t_c"),
    "320K002": ("relief_kgh", "relief_t_c"),
}


def boundary_values() -> dict:
    """The boundary values by name, at their design.

    Process utility
    ---------------
    What the plant's edges hold: the atmosphere a vent discharges to, the units not yet ported,
    the cooling water V1 writes as a constant.
    """
    return {
        # 323C005 at atmospheric pressure, 324F002's discharge (V1's literal 1.0 bar a).
        "323C005.p_bara": C005_P_BARA,
        # UF85's PIC-335201 at its design, LV-324501 on its forward route (unit 335).
        "PIC-335201.barg": PIC_335201_DES_BARG,
        # 322E006's cooling water at the flow its datasheet UA takes 744 to 755's 40 C on
        # (decision 36).
        "322E006.cw_kgh": E006_M_CW_DES_KGH,
    }


def operator_seeds() -> dict:
    """The hand valves, hand switches and set points at their design positions."""
    return {
        "HIC-323605": HIC_323605_DES_PCT,
        "HIC-329605": HV_329605_OP_DES_PCT,
        "HIC-329606": HV_329606_OP_DES_PCT,
        "HV-323D002-TIE": False,
        "HS-322915": False,
        **{f"HS-{t}": False for t in TRIP_21_HAND_SWITCHES},
        "FIC-322404": C001_CPL_DES_KGH,
        "322P002": True,
        "320K002-CO2": CO2_DES_KGH / 1000.0,
        "HIC-322602": HIC_322602_DES_PCT,
        "HIC-322605": HIC605_DES_PCT,
        "HIC-322604": HIC604_DES_PCT,
        "XV-322903": True,
        **{pump: {"on": on, "mode": mode} for pump, (on, mode) in AUX_PUMP_SEEDS.items()},
        EXT_OVERRIDE_TAG: False,
    }
