"""328E007 — the desorber heat exchanger, a feed/effluent plate interchanger.

What this models
----------------
328E007 recovers the heat the purified condensate carries out of 328C004 into the desorbers'
feed. Its cold side takes PFD 735 from 328D003's compartment II (56 C) and sends it to 328C002 as
738 (114 C); its hot side takes 739, 328C004's bottoms through LV-328505 (143 C), and sends it
on as 740 (89 C). No stream is split or mixed here: 738 is 735 and 740 is 739, heated and cooled.

The exchange law (V1's two-part idiom)
--------------------------------------
The cold outlet is fixed by a temperature effectiveness back-solved from the design
temperatures, and the hot outlet by the energy balance, not a second effectiveness, so the
exchanger cannot create or destroy energy while the hot side can give what the cold side takes:

    T_738     = T_735 + eps_T . (T_739 - T_735),          eps_T = 58/87
    T_740,raw = T_739 - (m_735 (T_738 - T_735) + L) / max(m_739, 1e-6),   L = 16 484 kg.K/h
    T_740     = T_740,raw clamped between the two inlet temperatures

cp cancels between the sides (one aqueous cp on both); L is the shell loss the design state
leaves between the hot duty and the cold duty, 18.32 kW. At design both outlets are the PFD's to
the bit: 114.0 and 89.0 C.

Where this unit departs from V1 — decided 2026-09-27 (handoff B-40, decision 14)
------------------------------------------------------------------------------
V1's cold outlet does not look at the hot flow. When 739 cannot give the cold side's duty down
to the pinch — at design 735, a hot flow under 20 932 kg/h, 62 % of design; at design 739, a
draw over 50 302 kg/h, which 328D003 sends above 80.8 % level — V1 clamps the hot outlet at the
feed's temperature and still heats the feed by eps_T, so the heat 739 did not give is made:
2023 kW with 328C004's bottoms stopped, 769 kW with the tank full.

Here, where the clamp binds, the feed takes only what 739 gave: the hot outlet stands at the
clamp and the cold outlet closes the balance on what 739 gave less the shell loss,

    T_738 = T_735 + (m_739 (T_739 - T_740) - L) / m_735        (m_735 > 0)

bounded between no change and V1's eps_T share, so a loss 739 cannot pay is not charged to the
feed. With the tank full the feed reaches 328C002 at 102.88 C, with 328C004's bottoms halved at
102.62 C, and with them stopped it passes through at compartment II's 56 C. With no feed the
outlets are V1's. The cap is inert while the clamp does not bind, where every tick is V1's. Each
binding is flagged (``hot_outlet_clamped``) — the exchanger pinched.

The boundaries this unit reads, and when
----------------------------------------
  * 735 and compartment II's temperature from 328D003 — THIS tick's
    (`AmmoniaWaterTankResult.m_735_kgh`, `.t_ii_c`): V1 steps the exchanger right after the tank;
  * 739 and 328C004's temperature — last tick's (V1 ``R328_739`` and ``s.a328_c004_T``), tears:
    328C004 is stepped after 328C002, which takes this unit's 738.

It publishes 738 and its temperature for 328C002 on the same tick, and 740 and its temperature
for the purified-condensate side (TT-328006) and unit 328's energy diagnostic.

No thermal loop closes here within a tick. The feed's heat returns to this exchanger only
through 328C002, 328C003 and 328C004 — a tick later, through 328C004's temperature. And the
condensate return 740 -> 328E001 -> 741 -> 328D003 is open: 741 enters the tank at a design 40 C
(handoff B-31), so 740's temperature reaches nothing downstream.

Source
------
V1 ``backend/main.py`` step_sim, "328E007 feed/effluent interchanger (AUDIT C10)" (8952-8963) and
``m_738 = m_735`` (8967). The design data are in `ureasim.data.unit_328e007`.
"""

from __future__ import annotations

from dataclasses import dataclass

from ureasim.data.unit_328e007 import E007_EPS_T, E007_HOT_FLOW_FLOOR_KGH, E007_LOSS_DT_KGKH


def interchanger_outlets(t_cold_in_c: float, t_hot_in_c: float, m_cold_kgh: float,
                         m_hot_kgh: float, eps_t: float, loss_dt_kgkh: float,
                         hot_flow_floor_kgh: float) -> tuple[float, float, bool]:
    """Both outlet temperatures of a feed/effluent interchanger anchored at its design point.

    Process utility
    ---------------
    The desorption section's plate exchangers recover the heat of a hot effluent into a cold
    feed: 328E007 the purified condensate into the desorbers' feed. The cold outlet sets the
    column's feed enthalpy, and so the steam the column needs; the hot outlet is what the
    effluent leaves at.

    Equation
    --------
        T_c,out     = T_c,in + eps_T . (T_h,in - T_c,in)
        T_h,out,raw = T_h,in - (m_c (T_c,out - T_c,in) + L) / max(m_h, floor)
        T_h,out     = clamp(T_h,out,raw, min(T_c,in, T_h,in), max(T_c,in, T_h,in))

    and, where the clamp binds and a feed flows (decided 2026-09-27, handoff B-40):

        Q_share = m_c . eps_T . (T_h,in - T_c,in)                  V1's duty on the feed
        Q_given = m_h (T_h,in - T_h,out) - L                       what the hot side gave, less loss
        T_c,out = T_c,in + clamp(Q_given, min(Q_share, 0), max(Q_share, 0)) / m_c

    The clamp keeps a counter-current exchanger from driving the hot outlet past the cold inlet.
    V1 left the cold side's duty as it was, making the heat the hot side could not give; here
    the cold side takes what the hot side gave, less the shell loss, and the balance closes on
    the loss actually paid, between 0 and L — a loss the hot side cannot pay is not charged to
    the feed. The third value is True when the clamp binds — the exchanger pinched.

    Source: V1 `main.py` 8959-8963 (the 328E007 block), and the decided cap.
    """
    t_cold_out = t_cold_in_c + eps_t * (t_hot_in_c - t_cold_in_c)
    # The hot side gives what the cold side took, plus the shell loss.
    t_hot_raw = t_hot_in_c - (m_cold_kgh * (t_cold_out - t_cold_in_c)
                              + loss_dt_kgkh) / max(m_hot_kgh, hot_flow_floor_kgh)
    lo, hi = min(t_cold_in_c, t_hot_in_c), max(t_cold_in_c, t_hot_in_c)
    t_hot_out = min(max(t_hot_raw, lo), hi)
    pinched = not lo <= t_hot_raw <= hi
    if pinched and m_cold_kgh > 0.0:
        # The feed takes only what the hot side gave down to the clamp, less the shell loss —
        # never more than its eps_T share, and never the other way: a loss the hot side cannot
        # pay is not charged to the feed (decided divergence).
        share = m_cold_kgh * (t_cold_out - t_cold_in_c)
        given = m_hot_kgh * (t_hot_in_c - t_hot_out) - loss_dt_kgkh
        taken = min(max(given, min(share, 0.0)), max(share, 0.0))
        t_cold_out = t_cold_in_c + taken / m_cold_kgh
    return t_cold_out, t_hot_out, pinched


@dataclass(frozen=True)
class DesorberHeatExchangerResult:
    """Everything 328E007 publishes on one tick."""

    #: PFD 738, the preheated feed to 328C002 [kg/h] and its temperature (TT-328010) [deg C].
    m_738_kgh: float
    t_738_c: float
    #: PFD 740, the purified condensate after the exchanger [kg/h] and its temperature
    #: (TT-328006) [deg C].
    m_740_kgh: float
    t_740_c: float
    #: The exchanger pinched: 739 could not give the feed its design share of the approach, the
    #: hot outlet stands at an inlet temperature, and the feed took only what 739 gave (B-40).
    hot_outlet_clamped: bool


def desorber_heat_exchanger(m_735_kgh: float, t_735_c: float, m_739_kgh: float,
                            t_739_c: float) -> DesorberHeatExchangerResult:
    """Step 328E007: preheat the desorbers' feed on 328C004's bottoms.

    Arguments
    ---------
    m_735_kgh, t_735_c
        328P003's draw to the desorbers and compartment II's temperature, THIS tick's.
    m_739_kgh, t_739_c
        328C004's bottoms and its temperature, last tick's, tears.
    """
    t_738, t_740, clamped = interchanger_outlets(
        t_735_c, t_739_c, m_735_kgh, m_739_kgh, E007_EPS_T, E007_LOSS_DT_KGKH,
        E007_HOT_FLOW_FLOOR_KGH)
    return DesorberHeatExchangerResult(m_738_kgh=m_735_kgh, t_738_c=t_738, m_740_kgh=m_739_kgh,
                                       t_740_c=t_740, hot_outlet_clamped=clamped)


__all__ = ["interchanger_outlets", "DesorberHeatExchangerResult", "desorber_heat_exchanger"]
