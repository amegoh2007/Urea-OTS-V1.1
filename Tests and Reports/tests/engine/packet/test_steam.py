"""Unit 329 in the console packet — `ureasim.engine.packet.steam`.

Pinned: each of V1's steam keys reads the port's network on the stream the module docstring maps
it to — FT-329403 the 901 the network sums, PIC-329205's output the split range's net stroke,
PIC-329207's output the vent and the turbine, its gauge readings on 1.01325 — the LP header's
start-of-tick pressure is what 322E002 boiled against, and the mass residuals are kg/s.
"""

from __future__ import annotations

import pytest

from tests.engine.packet.conftest import run


def test_the_network_at_design(design):
    s, r = design.packet["STEAM_SYSTEM"], design.results["329"]
    f = r.flows_kgh
    assert s["FT_329403_th"] == round(f["901"] / 1000.0, 2) == 60.85
    assert s["FT_329407_th"] == round(f["932"] / 1000.0, 2) and s["FT_329407_design_th"] == 16.71
    assert s["MP"]["P_bara"] == 19.7 and s["DRUM_9BAR"]["P_bara"] == 9.0
    assert s["SUPPLY_25BAR"] == {"P_bara": 25.0, "TI_sat": 224.0}
    assert s["PIC_329207"]["pv_barg"] == 4.0 and s["MASTER_SP_329207"]["on"] is True
    assert s["PIC_329207"]["op"] == round((f["PV-329207A"] + f["932"]) / 1000.0, 2)
    assert s["PIC_329205"]["op"] == round(r.strokes_pct["PV-329205A"]
                                          - r.strokes_pct["PV-329205B"], 1)
    assert s["LP"]["P_bara"] == round(r.p_lp_start_bara, 2)
    assert s["LP"]["TI_sat"] == round(design.results["322E002"].t_shell_c, 1)
    assert s["mass_residual_kg_s"]["d005_vapor"] == pytest.approx(
        r.vapour_residual_kgh["329D005"] / 3600.0)
    assert {k: s[k]["mode"] for k in ("LIC_329502", "LIC_329503", "LIC_329504")} == {
        "LIC_329502": "AUTO", "LIC_329503": "AUTO", "LIC_329504": "AUTO"}
    # AI-329701 and the drums' solids, the port's ANALYSERS block (B-90): clean at design, its
    # alarms on the plant DCS's set points (2026-10-13) clear.
    assert design.packet["ANALYSERS"] == {"AI_329701": 0.055, "AI_329701_over": False,
                                          "AI_329701_H1": False, "AI_329701_H2": False,
                                          "D001_solids_ppm": 0.0}


def test_the_hp_vent_opened_by_hand_shows_its_flow():
    """HV-329601 at 20 %: the vent's stroke and flow both read."""
    def vent(plant):
        plant.units["329"].hv_329601.hic_pct = 20.0
    s = run(5, vent).packet["STEAM_SYSTEM"]
    assert s["HP_VENT"]["pct"] == 20.0 and s["HP_VENT"]["m_th"] > 0.0
