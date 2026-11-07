"""The vendor control valves — `ureasim.data.control_valves` (handoff B-44, decided 2026-09-30).

Pins that the catalogue is the vendors' sheets as read, that the modified equal-percentage trim
the port runs reproduces every sizing case Flowserve printed for it, and the design strokes and
full-stroke capacities derived from them. Every number here was measured before it was written.
"""

from __future__ import annotations

import math

import pytest

from ureasim.control.valve import MOD_EQUAL_PCT_RANGE, cv_fraction, stroke_for_cv_fraction
from ureasim.data import control_valves as cvd
from ureasim.data import control_valves_fisher as fv
from ureasim.data import (unit_320, unit_323, unit_323e003, unit_323e011, unit_324, unit_328c002,
                          unit_328c003, unit_328d003)
from ureasim.data.design_point import R323_M314_DES, R323_M319_DES, R323_M324_DES

MODIFIED = [v for v in cvd.VENDOR_VALVES.values() if v.characteristic == "mod_equal_pct"]
#: The Valtek V726 linear trims; PV-329207C's Mark One MegaStream, linear too, is with the sheets
#: found in session 69 below.
LINEAR = [v for v in cvd.VENDOR_VALVES.values()
          if v.characteristic == "linear" and v.tag != "PV-329207C"]


def test_the_catalogue():
    """Twenty-four Valtek modified equal-percentage valves (LV-329505 added in session 52), three
    linear, one CCI equal percentage, nine Metso Neldiscs on their printed points (two in session
    51, six in session 52, FV-329409 in session 53); 67 sizing cases on the modified trim (unit 324's two false-air bleeds
    and two motive valves added in session 33, unit 329's four in session 37). Every normal case
    prints its stroke but LV-329503's, LV-329504's and LV-329505's, whose capacities are printed on
    the maximum case only."""
    assert len(cvd.VENDOR_VALVES) == 46      # 42 + Flowserve's Pos. 65, 76, 148, 149 (session 69)
    assert (len(MODIFIED), len(LINEAR)) == (24, 3)
    assert sum(len(v.cases) for v in MODIFIED) == 67
    assert {t for t, v in cvd.VENDOR_VALVES.items() if v.characteristic == "equal_pct"} == {
        "PV-322203", "HV-329601", "LV-324501A", "LV-324501B"}
    assert set(fv.FISHER_VALVES) == {"LV-328503", "LV-328504", "HV-329602", "PV-323202"}
    unprinted = {v.tag for v in MODIFIED + LINEAR if v.normal_case.stroke_pct is None}
    assert unprinted == {"LV-329503", "LV-329504", "LV-329505"}


@pytest.mark.parametrize("valve", MODIFIED, ids=lambda v: v.tag)
def test_the_modified_trim_reproduces_every_printed_stroke(valve):
    """R = 20 with the tangent line below 33.4 %: every stroke the sheets print, to within the
    whole per cent they print it to."""
    for c in valve.cases:
        if c.stroke_pct is None:
            continue
        h = 100.0 * stroke_for_cv_fraction(c.capacity / valve.rated, "mod_equal_pct")
        assert abs(h - c.stroke_pct) <= 0.50 + 1e-9, (valve.tag, c)


@pytest.mark.parametrize("valve", LINEAR, ids=lambda v: v.tag)
def test_the_linear_trims_run_just_below_their_stroke(valve):
    """The two linear Valtek trims pass 0.3 to 2.2 points of stroke less than a pure line; the
    port's linear law is that line."""
    for c in valve.cases:
        if c.stroke_pct is None:
            continue
        short = c.stroke_pct - 100.0 * c.capacity / valve.rated
        assert 0.0 < short <= 2.25, (valve.tag, c)


def test_the_trim_is_continuous_at_its_tangent_point():
    h0 = 1.0 / math.log(MOD_EQUAL_PCT_RANGE)
    below, above = cv_fraction(h0 * (1 - 1e-12), "mod_equal_pct"), cv_fraction(h0, "mod_equal_pct")
    assert above == pytest.approx(below, rel=1e-11)
    assert h0 == pytest.approx(0.3338, abs=1e-4)


@pytest.mark.parametrize("h", [0.0, 0.05, 0.2, 0.3338, 0.5, 0.7, 0.95, 1.0])
def test_the_stroke_inverse_round_trips(h):
    for char in ("mod_equal_pct", "equal_pct", "linear", "quick_open"):
        if h == 0.0:
            with pytest.raises(ValueError):
                stroke_for_cv_fraction(cv_fraction(h, char), char)
        else:
            assert stroke_for_cv_fraction(cv_fraction(h, char), char) == pytest.approx(h, abs=1e-12)


@pytest.mark.parametrize("name, stroke", [
    ("unit_328d003.FIC_323401_OP_DES_PCT", 49.255), ("unit_328d003.FIC_323402_OP_DES_PCT", 38.233),
    ("unit_328d003.FIC_328402_OP_DES_PCT", 58.403), ("unit_323e011.LV503_OP_DES_PCT", 52.865),
    ("unit_323e011.FIC418_OP_DES_PCT", 78.454), ("unit_323.LV501_OP_DES_PCT", 56.649),
    ("unit_323.LV505_OP_DES_PCT", 67.735), ("unit_323.FV401_OP_DES_PCT", 72.359),
    ("unit_320.PV_322203_OP_DES_PCT", 79.330),
    ("unit_328c003.PV328203_OP_DES_PCT", 70.562),
    ("unit_328c002.LV503_OP_DES_PCT", 56.946), ("unit_328c003.LV504_OP_DES_PCT", 57.802),
    ("unit_323e003.E003_PV_OP_DES_PCT", 36.446), ("unit_324.LV_324501A_OP_DES_PCT", 75.347),
])
def test_the_design_strokes(name, stroke):
    """Each ported vendor valve's design stroke, where its rated capacity passes its design
    flow on its normal case (V1: 50 % each, and 100 % for PV-322203). FV-328402's on 735 since
    B-39 (decided 2026-10-09; 58.791 on 744). The four found in session 69 (decision 150): V1's
    50, 50, 25 and 75 %; LV-324501A's on its sheet's Kv taken to the melt's 1221 kg/m3."""
    module, const = name.split(".")
    assert getattr({"unit_328d003": unit_328d003, "unit_323e011": unit_323e011,
                    "unit_323": unit_323, "unit_320": unit_320,
                    "unit_328c003": unit_328c003, "unit_328c002": unit_328c002,
                    "unit_323e003": unit_323e003, "unit_324": unit_324}[module], const) == \
        pytest.approx(stroke, abs=1e-3)


def test_each_design_stroke_passes_its_design_flow_on_the_normal_case():
    for valve, m in ((cvd.LV_323501, R323_M314_DES), (cvd.LV_323505, R323_M319_DES),
                     (cvd.FV_324401, R323_M324_DES)):
        c = valve.normal_case
        h = cvd.design_stroke_pct(valve, m) / 100.0
        assert valve.rated * cv_fraction(h, valve.characteristic) == pytest.approx(
            c.capacity * m / (c.flow * c.rho), rel=1e-12)


def test_the_full_stroke_capacities():
    """The two valves shut at design: FV-328405 passes 3.23 m3/h wide open, FV-328406 77.8 m3/h,
    where V1 took one branch's 1534 kg/h and the whole of 739's 33 724 kg/h."""
    assert cvd.full_stroke_m3h(cvd.FV_328405) == pytest.approx(3.2307, abs=1e-4)
    assert cvd.full_stroke_m3h(cvd.FV_328406) == pytest.approx(77.7589, abs=1e-4)
    assert unit_328d003.S793_CAP_KGH == pytest.approx(3206.15, abs=0.01)
    assert unit_328d003.S741_CAP_KGH == pytest.approx(77169.47, abs=0.01)


def test_the_pressure_recovery_factors_the_liquid_sites_take():
    assert (unit_323.LV501_FL, unit_323.LV505_FL) == (0.9319, 0.8926)


def test_the_pressure_drop_ratio_the_gas_site_takes():
    """PV-328203, the hydrolyser's overhead, on its normal case's xT where V1 runs the IEC
    0.75."""
    assert unit_328c003.PV328203_XT == cvd.PV_328203.normal_case.xt == 0.8047


def test_unit_324s_vacuum_valves_b61():
    """Session 33, read from Flowserve's sheets (Pos. 55, 56, 66, 67). The false-air bleeds are
    sized for 46 and 23 kg/h of air: PFD 784's and 783's 21 kg/h sit at 61.1 and 92.0 % of
    stroke, and wide open they pass 67.4 and 26.7 kg/h. The motive valves' normal cases are the
    PFD's 390 kg/h for 324F002 and Uhde's 1061 + 366 for 324F004 / F005 (80.8 %); the design
    motive through HV-329606 is the PFD's 1220 + 180 (handoff B-64, decided 2026-10-02), at
    80.16 %. HV-329605 sits at 69.1 %."""
    strokes = [cvd.design_stroke_pct(v, m) for v, m in (
        (cvd.PV_324202, 21.0), (cvd.PV_324203, 21.0), (cvd.HV_329605, 390.0),
        (cvd.HV_329606, 1061.0 + 366.0), (cvd.HV_329606, 1220.0 + 180.0))]
    assert strokes == [pytest.approx(61.074, abs=1e-3), pytest.approx(92.026, abs=1e-3),
                       pytest.approx(69.057, abs=1e-3), pytest.approx(80.802, abs=1e-3),
                       pytest.approx(80.165, abs=1e-3)]
    assert (cvd.full_stroke_m3h(cvd.PV_324202), cvd.full_stroke_m3h(cvd.PV_324203)) == (
        pytest.approx(67.399, abs=1e-3), pytest.approx(26.667, abs=1e-3))


def _iec_liquid_kv(c, pv_bara, pc_bara, fl):
    """IEC 60534-2-1's liquid Kv for a printed case: Q (rho / 1000 / dP_eff)^0.5."""
    ff = 0.96 - 0.28 * math.sqrt(pv_bara / pc_bara)
    dp = min(c.p1_bara - c.p2_bara, fl * fl * (c.p1_bara - ff * pv_bara))
    return c.flow * math.sqrt(c.rho / 1000.0 / dp)


def test_unit_329s_level_valves_session_37():
    """Flowserve's Pos. 68, 69, 70, read from the scans. The IEC calculation, on each case's printed
    vapour pressure, critical pressure and FL, reproduces every capacity Flowserve prints —
    LV-329502's 15.25 / 42.55 / 37.36 (sized flashing), LV-329503's 61.11 and LV-329504's 20.67
    on their maximum cases — to 0.04 %; the minimum and normal capacities those two sheets leave
    out are that calculation's. The design strokes pass PFD 904, 913 and the closure's 916:
    86.87, 58.88 and 48.26 %."""
    pv = {"LV-329502": (24.61, 19.55, 17.0), "LV-329503": (9.9, 8.93, 7.92),
          "LV-329504": (1.0, 1.0, 1.0)}
    pc = {"LV-329502": 221.2, "LV-329503": 222.0, "LV-329504": 220.0}
    for valve in (cvd.LV_329502, cvd.LV_329503, cvd.LV_329504):
        for c, p_v in zip(valve.cases, pv[valve.tag]):
            kv = _iec_liquid_kv(c, p_v, pc[valve.tag], c.fl)
            assert kv == pytest.approx(c.capacity, rel=4e-4), (valve.tag, c)
    assert [cvd.design_stroke_pct(v, m) for v, m in (
        (cvd.LV_329502, 57989.0), (cvd.LV_329503, 53056.0), (cvd.LV_329504, 19501.0))] == [
        pytest.approx(86.871, abs=1e-3), pytest.approx(58.882, abs=1e-3),
        pytest.approx(48.264, abs=1e-3)]


def test_unit_329s_steam_letdowns_session_37():
    """Flowserve's Pos. 74 and 75: PV-329205A passes PFD 903's 1754 kg/h at 19.55 % (Flowserve's
    normal case, 1763 kg/h, at 20 %); PV-329205B, shut at design, passes 10 486 kg/h wide open on
    its normal case."""
    assert cvd.design_stroke_pct(cvd.PV_329205A, 1754.0) == pytest.approx(19.548, abs=1e-3)
    assert cvd.full_stroke_m3h(cvd.PV_329205B) == pytest.approx(10486.18, abs=0.01)
    assert (cvd.PV_329205A.normal_case.xt, cvd.PV_329205B.normal_case.xt) == (0.662, 0.673)


@pytest.mark.parametrize("valve", [cvd.PV_329203, cvd.PV_329212], ids=lambda v: v.tag)
def test_a_neldisc_runs_on_its_printed_points(valve):
    """Decided 2026-10-14 (decision 108): Metso's sheets name no curve, so the trim is its printed
    capacities at their travels, shut to the rated Cv wide open; the inverse returns every printed
    travel exactly, and the design stroke passes the PFD's flow on the normal case (39.31 % for
    PFD 919, 54.68 % for PFD 920)."""
    for c in valve.cases:
        assert 100.0 * stroke_for_cv_fraction(c.capacity / valve.rated,
                                              valve.characteristic) == pytest.approx(
            c.stroke_pct, abs=1e-9)
    from ureasim.data.unit_329 import STEAM_PFD_KGH
    pfd = STEAM_PFD_KGH["919" if valve.tag == "PV-329203" else "920"]
    # PV-329212 is a balanced S-Disc: since decision 170 (2026-11-06) the table's shape runs between
    # its printed points, so its design stroke is 54.6843 % (54.6805 % on the chord; both sides are
    # pinned in test_control_valves_metso.py). PV-329203 is conventional and keeps the chord.
    assert cvd.design_stroke_pct(valve, pfd) == pytest.approx(
        39.3096 if valve.tag == "PV-329203" else 54.6843, abs=1e-4)


@pytest.mark.parametrize("valve, flow, stroke", [
    (cvd.FV_329401, 6495.0, 26.0), (cvd.PV_329202, 9027.0, 32.9244),
    (cvd.PV_329204, 57989.0, 44.1), (cvd.PV_329207B, 16707.0, 55.9717),
    (cvd.PV_329208, 11230.0, 27.2640), (cvd.FV_329409, 306000.0, 46.8464)], ids=lambda x: getattr(x, "tag", x))
def test_metsos_sheets_25_to_32_run_on_their_printed_points(valve, flow, stroke):
    """Decision 108's class (session 52; wired 2026-10-15, session 53): every printed travel is
    returned exactly, and the design stroke is where the normal case passes the PFD's flow — PFD
    931, 918, 902, 932, 926 and 322E003's 306 t/h. FV-329401's and PV-329204's PFD rows are their
    normal cases' own flows, so their strokes are the printed 26.0 and 44.1 %. PV-329207B and
    PV-329208 are balanced S-Discs: decision 170 (2026-11-06) puts Valmet's table between their
    printed points, which moves their design strokes from the chord's 54.9630 and 27.2232 % to 55.9717
    and 27.2640 % (both sides pinned in test_control_valves_metso.py)."""
    for c in valve.cases:
        assert 100.0 * stroke_for_cv_fraction(c.capacity / valve.rated,
                                              valve.characteristic) == pytest.approx(
            c.stroke_pct, abs=1e-9)
    assert cvd.design_stroke_pct(valve, flow) == pytest.approx(stroke, abs=1e-4)


def test_fv_329409s_sheet_prints_no_density():
    """Page 26 (item 25) prints 95 C water and no density; the cases carry IAPWS-IF97's saturated
    liquid there, 961.89 kg/m3 (decided 2026-10-15), and the vapour pressure it prints, 0.85 bar a,
    is IAPWS's at 95 C to the second figure."""
    from ureasim.thermo.iapws import psat_bara
    assert [c.rho for c in cvd.FV_329409.cases] == [pytest.approx(961.887, abs=1e-3)] * 3
    assert psat_bara(95.0) == pytest.approx(0.85, abs=0.005)
    assert [c.fl for c in cvd.FV_329409.cases] == [0.86, 0.80, 0.75]


def test_lv_329505s_unprinted_capacities_are_iec_60534s():
    """Flowserve's Pos. 71 prints LV-329505's capacity on its maximum case only (Kv 46.57 at 74 %,
    flashing). IEC 60534-2-1 on each case's printed pressures, flow, density, vapour pressure,
    critical pressure and FL gives 11.969 and 32.366 on the minimum and normal cases and 46.548 on
    the maximum, 0.05 % under the printed 46.57; the normal case puts the design stroke, on PFD
    919's 18 489 kg/h, at 62.19 % (decided 2026-10-15)."""
    import math
    v = cvd.LV_329505

    def kv(c):
        ff = 0.96 - 0.28 * math.sqrt({0: 3.93, 1: 3.61, 2: 3.61}[v.cases.index(c)] / 221.0)
        pv = {0: 3.93, 1: 3.61, 2: 3.61}[v.cases.index(c)]
        dp = min(c.p1_bara - c.p2_bara, c.fl ** 2 * (c.p1_bara - ff * pv))
        return c.flow * math.sqrt(c.rho / 1000.0 / dp)
    assert [round(kv(c), 3) for c in v.cases] == [11.969, 32.366, 46.548]
    assert v.cases[2].capacity == 46.57
    from ureasim.data.unit_324 import LV_329505_VENDOR_OP_DES_PCT
    assert LV_329505_VENDOR_OP_DES_PCT == pytest.approx(62.194, abs=1e-3)


#: The sheets found in session 69 and how far their printed travels sit from the port's named
#: curves [points of stroke, printed less the curve's], case by case (decision 150).
SESSION_69 = {
    "HV-329601": (-9.33, -8.25, -4.97), "PV-329207C": (-6.73, -7.34, -5.47),
    "LV-324501A": (-1.63, -1.34, 0.0), "LV-324501B": (1.30, -1.38, -1.92),
    "LV-328503": (-4.96, -4.79, -4.33), "LV-328504": (-4.57, -4.66, -4.82),
    "HV-329602": (3.98, -2.98, -2.88), "PV-323202": (-2.27, -19.84, -6.61),
}


@pytest.mark.parametrize("tag", list(SESSION_69))
def test_the_session_69_sheets_print_their_travels_off_the_named_curves(tag):
    """Decision 150: each sheet names its curve, equal percentage or linear, and the port runs its
    own law of that name (50:1 for the equal percentage); the travels the vendors print sit off it —
    Flowserve's 0310 within two points, Fisher's letdowns five below, the Mark Ones five to nine,
    TV-323013's Whisper I cage (the port's PV-323202) twenty below at its normal case. LV-324501A's
    maximum case needs more than its Kvs and is printed wide open."""
    v = {**cvd.VENDOR_VALVES, **fv.FISHER_VALVES}[tag]
    for c, dev in zip(v.cases, SESSION_69[tag]):
        h = 100.0 * stroke_for_cv_fraction(min(c.capacity / v.rated, 1.0), v.characteristic)
        assert c.stroke_pct - h == pytest.approx(dev, abs=0.005), (tag, c)
