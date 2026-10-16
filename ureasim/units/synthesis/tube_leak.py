"""322E002's tube leak — the HP carbamate condenser's process side into its boiling shell.

What this models
----------------
A tube failure in 322E002, the instructor's malfunction. The tube side is the high-pressure side:
the condensing carbamate at the loop's pressure, 140.7 bar a at design, against the shell's boiling
water at 322D001A/B's saturation, 5.0 bar a. A rupture therefore leaks process into the shell: the
loop loses inventory, the leaked ammonia, CO2 and inerts flash in the boiling shell into the LP
steam, and the leaked water and urea join the drums' water. Decided 2026-10-09 (handoff B-82): V1's
malfunction (``tests/run_hpcc_rupture.py``) injects the shell's water into the process, against the
differential.

Equations
---------
The leak on the live differential, an orifice the instructor sizes by its rate at the design
differential:

    W = W_sev . sqrt( max(P_tube - P_shell, 0) / dP_des ),    W <= m_product

P_tube PT-329201 and P_shell 322D001A/B's steam space, both as the tick before left them; dP_des the
two design pressures' difference, 135.69 bar. The leak takes the two-phase product pro rata,

    f = W / m_product,    n_leak,k = f (n_gas,k + n_liq,k),

and 322R001 receives (1 - f) of each component of the product and of the combined feed. In the
shell the volatiles and inerts (`LEAK_VOLATILE`) leave as vapour with the LP steam and the water,
urea and biuret join the drums' water; the leak's heat above that end state,

    Q = H0(leak gas, T_prod, vapour) + H0(leak liquid, T_prod, liquid)
        - H0(volatiles, T_shell, vapour) - H0(water and solids, T_shell, liquid),

boils Q / h_fg(T_shell) of the drums' water (or condenses that much of their steam, Q < 0) — H0 the
elements-datum enthalpy (`thermo.enthalpy`), which prices NH3 and CO2 dissolved in the leak's liquid
and so pays their desorption out of the shell.

Source
------
Handoff B-82 (decided 2026-10-09); 322E002's product (`carbamate_condenser`); `data.unit_322e002`
``LEAK_DP_DES_BAR``, ``LEAK_VOLATILE``. No plant document sizes a tube failure: the rate is the
instructor's.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

from ureasim.core.stream import MW_COMP
from ureasim.data.unit_322e002 import LEAK_DP_DES_BAR, LEAK_VOLATILE
from ureasim.thermo.enthalpy import h0_stream
from ureasim.thermo.iapws import hvap_kjkg
from ureasim.units.synthesis.carbamate_condenser import CondenserResult

__all__ = ["TubeLeakResult", "NO_LEAK", "tube_leak"]


@dataclass(frozen=True)
class TubeLeakResult:
    """One tick of 322E002's tube leak [kg/h, kW]."""

    #: What leaves the tube side.
    m_kgh: float = 0.0
    #: Its share of the product, f.
    frac: float = 0.0
    #: The leaked components [kmol/h].
    leaked_kmolh: dict = field(default_factory=dict)
    #: Into the shell: the volatiles and inerts with the LP steam; the water and solids into the
    #: drums' water, of which the solids (urea, biuret); the drums' water the leak's heat boils
    #: (negative: their steam it condenses).
    vapour_kgh: float = 0.0
    liquid_kgh: float = 0.0
    solids_kgh: float = 0.0
    boil_kgh: float = 0.0
    #: The leak's heat above its end state in the shell [kW].
    q_kw: float = 0.0


#: No leak: every flow a literal zero, so the loop and the steam network are their own to the bit.
NO_LEAK = TubeLeakResult()


def _scaled(d: dict, keep: float) -> dict:
    return {k: v * keep for k, v in d.items()}


def tube_leak(severity_kgh: float, p_tube_bara: float, p_shell_bara: float,
              hpcc: CondenserResult, t_shell_c: float) -> tuple[TubeLeakResult, CondenserResult]:
    """(the leak, 322E002's product as 322R001 receives it).

    Process utility
    ---------------
    The instructor's tube failure: the loop loses the leak (PT-329201 falls, the reactor is fed
    less), the LP steam carries its ammonia and CO2, and 322D001A/B's level rises with its water.
    The rate follows the live differential, so a loop whose pressure collapses leaks less. A
    severity of zero returns the product untouched.

    Arguments
    ---------
    severity_kgh
        The leak's rate at the design differential [kg/h], the instructor's.
    p_tube_bara, p_shell_bara
        PT-329201 and 322D001A/B's steam space [bar a], the tick before.
    hpcc
        322E002's evaluation this tick (`carbamate_condenser_322e002`).
    t_shell_c
        The shell's saturation [deg C], what the leak's end state is priced at.

    Equations in the module docstring.
    """
    m_product = hpcc.gas_kgh + hpcc.liq_kgh
    if severity_kgh <= 0.0 or m_product <= 0.0:
        return NO_LEAK, hpcc
    dp = max(p_tube_bara - p_shell_bara, 0.0)
    w = min(severity_kgh * math.sqrt(dp / LEAK_DP_DES_BAR), m_product)
    f = w / m_product
    gas = _scaled(hpcc.gas_kmolh, f)
    liq = _scaled(hpcc.liq_kmolh, f)
    leaked = {k: gas.get(k, 0.0) + liq.get(k, 0.0) for k in MW_COMP}
    vol = {k: (leaked[k] if k in LEAK_VOLATILE else 0.0) for k in MW_COMP}
    wet = {k: (0.0 if k in LEAK_VOLATILE else leaked[k]) for k in MW_COMP}

    # The leak's heat above its end state in the shell, on the elements datum.
    q_kw = (h0_stream(gas, hpcc.t_prod, "vapour")["enthalpy_flow_kW"]
            + h0_stream(liq, hpcc.t_prod, "liquid")["enthalpy_flow_kW"]
            - h0_stream(vol, t_shell_c, "vapour")["enthalpy_flow_kW"]
            - h0_stream(wet, t_shell_c, "liquid")["enthalpy_flow_kW"])
    leak = TubeLeakResult(
        m_kgh=w, frac=f, leaked_kmolh=leaked,
        vapour_kgh=sum(vol[k] * MW_COMP[k] for k in MW_COMP),
        liquid_kgh=sum(wet[k] * MW_COMP[k] for k in MW_COMP),
        solids_kgh=sum(wet[k] * MW_COMP[k] for k in ("Urea", "Biuret")),
        boil_kgh=q_kw * 3600.0 / hvap_kjkg(t_shell_c), q_kw=q_kw)

    # What 322R001 receives: (1 - f) of the product and of the combined feed it is read on.
    keep = 1.0 - f
    after = replace(
        hpcc, feed_kmolh=_scaled(hpcc.feed_kmolh, keep), gas_kmolh=_scaled(hpcc.gas_kmolh, keep),
        liq_kmolh=_scaled(hpcc.liq_kmolh, keep), gas_kgh=hpcc.gas_kgh * keep,
        liq_kgh=hpcc.liq_kgh * keep, gas_th=hpcc.gas_th * keep, liq_th=hpcc.liq_th * keep,
        gas_mol=hpcc.gas_mol * keep, liq_mol=hpcc.liq_mol * keep,
        m_dot_kgh=hpcc.m_dot_kgh * keep)
    return leak, after
