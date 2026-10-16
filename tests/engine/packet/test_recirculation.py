"""Unit 323 in the console packet — `ureasim.engine.packet.recirculation`.

Pinned: 323C005's inflows are the recycle tears the tick read and its balance the absorber's
own; a volumetric loop's faceplate carries its stream's volume and mass; TV-323013A and B split
the tempered water; the standby SIC-323902 shows its own output; the liquor train reads the
port's units.
"""

from __future__ import annotations

from ureasim.data.unit_328d003 import RHO_735_KGM3
from tests.engine.packet.conftest import run


def test_323c005s_inflows_are_the_tears_the_tick_read(design):
    c5 = design.packet["LPCC_3232"]["C005"]
    read = design.scheduler.tears_read
    assert (c5["in756_kgh"], c5["in702_kgh"], c5["in708_kgh"]) == (
        round(read.m_756_kgh, 1), round(read.m_702_kgh, 1), round(read.m_708_kgh, 1))
    res = design.results["323C005"]
    assert c5["closure_kgh"] == round(res.in_kgh - res.m_343_kgh - res.m_341_kgh, 6)
    assert abs(c5["closure_kgh"]) < 0.06      # 0.0502 kg/h measured in session 51


def test_the_condensers_at_design(design):
    e3 = design.packet["LPCC_3232"]["E003"]
    m_735 = design.results["328D003"].m_735_kgh           # FIC-328402 meters 735 (B-39)
    assert e3["FIC_328402"]["vol_m3h"] == round(m_735 / RHO_735_KGM3, 2) == 31.4
    assert e3["FIC_328402"]["kgh"] == round(m_735, 1)
    assert e3["TV_323013A"] + e3["TV_323013B"] == 100.0
    assert e3["SIC_323902"] == {"pv": 0.0, "sp": 0.0, "op": 0.0, "mode": "MAN"}
    assert e3["SIC_323901"]["mode"] == "CAS"


def test_the_liquor_train_at_design(design):
    r = design.packet["RECIRC_323"]
    assert r["C003"]["TT_323002"] == 121.0 and r["C003"]["P_bara"] == 4.1
    assert r["F004"]["TT_323005"] == 106.0 and r["F010"]["TT_323010"] == 99.0
    assert r["D002"]["urea_pct"] == round(design.results["323D002"].w["Urea"] * 100.0, 2)
    assert r["C003"]["TIC_323007"]["mode"] == "AUTO" and r["F010"]["PIC_329208"]["mode"] == "CAS"


def test_the_standby_faceplate_shows_what_the_operator_sets():
    """SIC-323902 at 30 % by hand: its PV reads 30, as V1's liveness step makes it."""
    def set_op(plant):
        plant.loops["SIC-323902"][0].op = 30.0
    assert run(2, set_op).packet["LPCC_3232"]["E003"]["SIC_323902"]["pv"] == 30.0
