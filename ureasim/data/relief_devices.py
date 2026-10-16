"""The urea plant's relief devices — Uhde's safety-valve and rupture-disc specifications, as set.

What this is
------------
Every safety relief valve and rupture disc Uhde specified for units 320 to 335 — the urea plant
the simulator models, with its CO2 compressor (320), ammonia pumping station (321), steam and
condensate system (329) and UF85 dosing (335): 61 valves and 3 discs. Each carries what its
technical specification prints on page 1: the equipment it protects (the "basis of <3 % pressure
drop"), the line it sits on, the failures it was sized for and the flow of each, the design,
operating and relieving pressures, and the set (or burst) pressure under "Additional
requirements". The relief model (`core.relief`, decided 2026-09-30, handoff B-47) reads it.

Sempell's orifice selections add what each valve can pass: the selected orifice, its certified
discharge coefficient and the actual capacity at the relieving pressure, the fluid it was sized
on, and its blowdown — 10 % of the set pressure on every gas and steam valve, 20 % on every liquid one.
`RELIEF_SIZING` carries the seventeen valves whose selections have been read from the vendor
archive (unit 329's six in session 37, SV32064 in session 47).

The set pressures are gauge, on the sheet's own atmosphere (1.010 or 1.013 bar a); the other
pressures are absolute. Every relieving pressure is the set pressure plus 10 % accumulation,
bar SV32261's (set at 1 bar g, relieving at 2.65 bar a).

Source
------
Uhde, "Safety Relief Valve — Technical Specification", one per device, UD-RL-3xx-EC-00nn (listed
per entry), scanned, read from the rendered pages; routed from the HFC table of contents
UD-AM-G00-AB-0022, file 02.02. Cross-checked against Sempell's set-pressure certificates
(UD-RL-G00-DZ-0001-008, SV32852 on page 96 of 161: 23.0 bar g; UD-RL-G00-DZ-0002-004: SV32251,
SV32252, SV32253, SV32351, SV32352, SV32355, SV32356, SV32850, SV32851 — every one as specified).

Sempell, "safety relief valve series S (DIN), specification sheet, orifice selection / capacity
calculation, VdTÜV type test", AD 2000-A2, 08.06.2005 and 10.08.2005, scanned, read from the
rendered pages: Uhde "Safety Relief Valves — Calculation of Orifice" UD-RL-G00-DZ-0001-001 (group
A04, 163 pages; SV32064 page 72, SV32261 page 89, SV32353 page 90, SV32357 page 91, SV32852
page 92) and
UD-RL-G00-DZ-0002-001 (6 pages; SV32251/52, SV32253, SV32351/52, SV32355/56, SV32850/51, pages
1 to 5 of 5).
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ReliefCase", "ReliefDevice", "RELIEF_DEVICES", "relief_devices_on", "ReliefSizing",
           "RELIEF_SIZING", "GAS_KD_ASSUMED", "GAS_BLOWDOWN", "gas_reseat_bara"]


@dataclass(frozen=True)
class ReliefCase:
    """One sizing case on a sheet: the fluid, its state, and the flow to discharge [kg/h]."""

    fluid: str
    state: str
    flow_kgh: float


@dataclass(frozen=True)
class ReliefDevice:
    """One safety valve or rupture disc, as its technical specification prints it."""

    tag: str
    kind: str                           # "safety valve" or "rupture disc"
    unit: str
    pid: str                            # the P&I sheet
    protects: str                       # the sheet's "basis of <3 % pressure drop, to"
    line: str
    failures: tuple[str, ...]
    cases: tuple[ReliefCase, ...]
    design_bara: float
    operating_bara: float
    relieving_bara: float
    atm_bara: float
    back_bara: float                    # superimposed back pressure
    set_barg: float                     # set pressure, or a disc's burst pressure
    source: str

    @property
    def set_bara(self) -> float:
        """The set pressure on the sheet's own atmosphere [bar a]."""
        return self.set_barg + self.atm_bara


def _sv(tag, unit, pid, protects, line, failures, cases, design, operating, relieving, set_barg,
        doc, atm=1.013, back=None, kind="safety valve"):
    return ReliefDevice(
        tag=tag, kind=kind, unit=unit, pid=pid, protects=protects, line=line,
        failures=tuple(failures), cases=tuple(ReliefCase(*c) for c in cases),
        design_bara=design, operating_bara=operating, relieving_bara=relieving, atm_bara=atm,
        back_bara=atm if back is None else back, set_barg=set_barg,
        source=f"Uhde {doc}, Technical Specification, page 1")


def _cooling_water(tag, unit, pid, protects, line, doc):
    """A cooling-water side's thermal-expansion valve: the sheet's standard case — 100 kg/h of
    water, 9.00 bar a design, 2.60 operating, 9.80 relieving, set 8.0 bar g."""
    return _sv(tag, unit, pid, protects, line, ["Thermal expansion"],
               [("Water", "Liquid", 100.0)], 9.00, 2.60, 9.80, 8.0, doc)


def _ammonia_thermal(tag, pid, protects, line, doc):
    """A liquid-ammonia section's thermal-expansion valve on 321's 31 bar a system: 100 kg/h,
    26.00 bar a operating, 34.00 relieving, set 30.0 bar g."""
    return _sv(tag, "321", pid, protects, line, ["Thermal expansion"],
               [("Ammonia liquid", "Liquid", 100.0)], 31.00, 26.00, 34.00, 30.0, doc)


_DEVICES = [
    # ----- 320: the CO2 compressor and its turbine ------------------------------------------
    _cooling_water("SV32061", "320", "126/1", "320E005", "WR1-388650-BB07DA",
                   "UD-RL-320-EC-0001 rev 01"),
    _sv("SV32062", "320", "126/2", "320MT02", "STMH1-320505-KE13E", ["Operating failure"],
        [("MP steam", "Steam", 60000.0)], 28.50, 25.00, 30.70, 27.0, "UD-RL-320-EC-0002"),
    _sv("SV32064", "320", "101", "320R001", "CO02-320202-BG17L", ["Operating failure"],
        [("CO2", "Gas", 67000.0)], 168.00, 148.00, 177.00, 160.0, "UD-RL-320-EC-0003"),
    _cooling_water("SV32071", "320", "121/1", "320E002", "WR20-388664-BB07DA",
                   "UD-RL-320-EC-0004 rev 01"),
    _sv("SV32085", "320", "125/1", "320MT02", "STMH1-320502-KE13E", ["Operating failure"],
        [("MP steam", "Steam", 92000.0)], 28.50, 25.00, 31.26, 27.5, "UD-RL-320-EC-0005"),
    _cooling_water("SV32091", "320", "126/1", "320U002-E01", "WR20-388651-BB07DA",
                   "UD-RL-320-EC-0006 rev 01"),
    _cooling_water("SV32073", "320", "121/1", "320E004", "WR1-388666-BB07DA",
                   "UD-RL-320-EC-0007 rev 01"),
    _cooling_water("SV32075", "320", "121/1", "320E003", "WR20-388665-BB07DA",
                   "UD-RL-320-EC-0008 rev 01"),
    _cooling_water("SV32080", "320", "121/2", "320U001-E01", "WR20-388658-BB07DA",
                   "UD-RL-320-EC-0009 rev 01"),
    _cooling_water("SV32081", "320", "121/2", "320U001-E02", "WR20-388658-BB07DA",
                   "UD-RL-320-EC-0010 rev 01"),
    # ----- 321: the ammonia pumping station --------------------------------------------------
    _sv("SV32151", "321", "101", "321P002B", "AL3-321107-BE11DA",
        ["Operating failure HP NH3 pump"], [("Ammonia liquid", "Boiling liquid", 55000.0)],
        31.00, 26.00, 34.00, 30.0, "UD-RL-321-EC-0001"),
    _sv("SV32155", "321", "101", "321D003", "AG1-321005-EC13E", ["Max. energy of 321P002"],
        [("Ammonia liquid", "Boiling liquid", 70000.0)], 31.00, 26.00, 34.00, 30.0,
        "UD-RL-321-EC-0002"),
    _ammonia_thermal("SV32158", "101", "321F005A", "AL22-309021-BE11DA",
                     "UD-RL-321-EC-0003 rev 01"),
    _ammonia_thermal("SV32160", "101", "321F005A/B", "AL22-309021-BE11DA",
                     "UD-RL-321-EC-0004 rev 01"),
    _sv("SV32150", "321", "101", "321P002A", "AL3-321103-BE11DA",
        ["Operating failure HP NH3 pump"], [("Ammonia liquid", "Boiling liquid", 55000.0)],
        31.00, 26.00, 34.00, 30.0, "UD-RL-321-EC-0005"),
    _ammonia_thermal("SV32153", "101", "321D003", "AL3-321101-BE11DA",
                     "UD-RL-321-EC-0006 rev 01"),
    _ammonia_thermal("SV32154", "101", "321D003", "AL3-321101-BE11DA",
                     "UD-RL-321-EC-0007 rev 01"),
    _sv("SV32157", "321", "101", "321P002A", "AL1-321104-BE17L", ["Thermal expansion"],
        [("Ammonia liquid", "Liquid", 100.0)], 206.00, 161.70, 226.50, 205.0,
        "UD-RL-321-EC-0008"),
    _ammonia_thermal("SV32159", "101", "321F005B", "AL22-309021-BE11DA",
                     "UD-RL-321-EC-0009 rev 01"),
    # ----- 322: synthesis --------------------------------------------------------------------
    _sv("SV32251", "322", "102", "322R001 (N2)", "GCB2-322251-EK19L", ["Operating failure"],
        [("Carbamate gas", "Gas", 105000.0)], 168.00, 142.00, 175.90, 159.0,
        "UD-RL-322-EC-0001"),
    _sv("SV32252", "322", "102", "322R001 (N2)", "GCB2-322251-EK19L", ["Operating failure"],
        [("Carbamate gas", "Gas", 105000.0)], 168.00, 142.00, 175.90, 159.0,
        "UD-RL-322-EC-0002"),
    _sv("SV32253", "322", "102", "322C001 N11", "GCB7-322C001-EG13EA",
        ["Blocked outlet", "Blocked outlet"],
        [("Carbamate gas", "Gas", 5000.0), ("Ammonia water", "Boiling liquid", 60000.0)],
        17.00, 3.90, 6.50, 5.0, "UD-RL-322-EC-0003"),
    _sv("SV32261", "322", "170", "322", "AII20-329524-EC07D",
        ["Failure of PCV322211", "Operating error"],
        [("Instrument air", "Gas", 70.0), ("Carbamate gas", "Liquid", 100.0)],
        6.00, 1.30, 2.65, 1.0, "UD-RL-322-EC-0004 rev 01"),
    # ----- 323: LP recirculation -------------------------------------------------------------
    _sv("SV32351", "323", "103/1", "323C003", "GCB4-323201-EG07D", ["Failure of LV 322501"],
        [("Carbamate gas", "Gas", 60000.0)], 6.00, 4.10, 6.50, 5.0, "UD-RL-323-EC-0001",
        atm=1.010, back=2.000),
    _sv("SV32352", "323", "103/1", "323C003", "GCB4-323201-EG07D", ["Failure of LV 322501"],
        [("Carbamate gas", "Gas", 60000.0)], 6.00, 4.10, 6.50, 5.0, "UD-RL-323-EC-0002",
        atm=1.010, back=2.000),
    _sv("SV32353", "323", "103/2", "328D001 N2", "ACA4-323207-EG07D", ["Failure of LV 323503"],
        [("Ammonia water", "Liquid", 77000.0)], 11.00, 3.60, 6.50, 5.0, "UD-RL-323-EC-0003",
        atm=1.010),
    _sv("SV32355", "323", "103/1", "323P001A", "ACA4-323023-EG08D", ["Operating failure"],
        [("Carbamate liquid", "Liquid", 50000.0)], 11.00, 3.20, 10.90, 9.0,
        "UD-RL-323-EC-0004", atm=1.010, back=1.490),
    _sv("SV32356", "323", "103/1", "323P001B", "ACA4-323003-EG08D", ["Operating failure"],
        [("Carbamate liquid", "Liquid", 50000.0)], 11.00, 3.20, 10.90, 9.0,
        "UD-RL-323-EC-0005", atm=1.010, back=1.490),
    _sv("SV32357", "323", "103/2", "323D011 N6", "AW3-323208-EG07D", ["Blocked outlet"],
        [("Ammonia water", "Liquid", 12000.0)], 17.00, 1.30, 6.50, 5.0, "UD-RL-323-EC-0006",
        atm=1.010),
    # ----- 328: desorption and hydrolysis ----------------------------------------------------
    _sv("SV32850", "328", "104", "328C002", "AW4-328066-EC08D",
        ["Blocked outlet", "Blocked lines"],
        [("Ammonia water", "Liquid", 32000.0), ("LP steam", "Steam", 21000.0)],
        9.00, 3.90, 6.50, 5.0, "UD-RL-328-EC-0001", atm=1.010),
    _sv("SV32851", "328", "104", "328C002", "AW4-328066-EC08D",
        ["Blocked outlet", "Blocked lines"],
        [("Ammonia water", "Liquid", 32000.0), ("LP steam", "Steam", 21000.0)],
        9.00, 3.90, 6.50, 5.0, "UD-RL-328-EC-0002", atm=1.010),
    _sv("SV32852", "328", "104", "328C003", "STMH2-329302-EG13E",
        ["Blocked outlet", "Blocked outlet"],
        [("MP steam", "Steam", 16000.0), ("Ammonia water", "Liquid", 83000.0)],
        28.50, 16.80, 26.30, 23.0, "UD-RL-328-EC-0003", atm=1.010),
    _sv("SV32854", "328", "104", "328E021B", "AW2-328059-EG13E", ["Thermal expansion"],
        [("Ammonia water", "Liquid", 2400.0)], 26.00, 16.80, 28.50, 25.0,
        "UD-RL-328-EC-0004 rev 01", atm=1.010),
    _sv("SV32855", "328", "104", "328E021A", "AW2-328059-EG13E", ["Thermal expansion"],
        [("Ammonia water", "Liquid", 2400.0)], 26.00, 16.80, 28.50, 25.0,
        "UD-RL-328-EC-0005 rev 01", atm=1.010),
    _sv("SV32856", "328", "104", "328E021B", "AW7-328056-EG13E", ["Thermal expansion"],
        [("Ammonia water", "Liquid", 2400.0)], 30.00, 24.40, 31.81, 28.0,
        "UD-RL-328-EC-0006 rev 01", atm=1.010),
    _sv("SV32857", "328", "104", "328E021A", "AW7-328056-EG13E", ["Thermal expansion"],
        [("Ammonia water", "Liquid", 2400.0)], 30.00, 24.40, 31.81, 28.0,
        "UD-RL-328-EC-0007 rev 01", atm=1.010),
    # ----- 329: steam and condensate ---------------------------------------------------------
    _sv("RD329182", "329", "102", "322E001", "STMS2-329402-BA13E", ["Tube rupture"],
        [("MP steam", "Steam", 110000.0)], 32.00, 20.50, 35.10, 31.0, "UD-RL-329-EC-0001",
        kind="rupture disc"),
    _sv("RD329184", "329", "102", "322E003", "WC1-329055-BB11DA", ["Tube rupture"],
        [("Carbamate gas", "Gas", 70000.0)], 14.50, 9.00, 14.75, 12.5, "UD-RL-329-EC-0002",
        kind="rupture disc"),
    _sv("RD329187", "329", "102", "322E002", "STLS6-329355-BB07D", ["Tube rupture"],
        [("LP steam", "Steam", 100000.0)], 9.00, 4.40, 9.80, 8.0, "UD-RL-329-EC-0003",
        kind="rupture disc"),
    _sv("SV32901", "329", "107/2", "390E001A/B", "CPL5-329046-BB08D", ["Control loop failure"],
        [("LP condensate", "Liquid", 85000.0)], 16.00, 9.20, 12.00, 10.0, "UD-RL-329-EC-0004"),
    _cooling_water("SV32904", "329", "107/2", "329E005", "WR1-329155-BB07DA",
                   "UD-RL-329-EC-0005 rev 01"),
    _cooling_water("SV32905", "329", "107/2", "321E001", "WR1-329795-BB07DA",
                   "UD-RL-329-EC-0006 rev 01"),
    _cooling_water("SV32921", "329", "109", "329E004", "WR1-329152-BB07DA",
                   "UD-RL-329-EC-0007 rev 01"),
    _cooling_water("SV32927", "329", "103/2", "323E011", "WR1-329187-BB07DA",
                   "UD-RL-329-EC-0008 rev 01"),
    _cooling_water("SV32929", "329", "102", "322E006", "WR1-329180-BB07DA",
                   "UD-RL-329-EC-0009 rev 01"),
    _sv("SV32951", "329", "107/1", "329D005 (N5)", "STMH2-329D005-BA13E",
        ["Control loop failure"], [("MP steam", "Steam", 100000.0)], 28.50, 19.90, 27.40, 24.0,
        "UD-RL-329-EC-0010"),
    _sv("SV32952", "329", "107/1", "329D009 (N8)", "STLS3-329D009-BB08D",
        ["Control loop failure", "Control loop failure"],
        [("LP steam", "Steam", 40000.0), ("MP condensate", "Boiling water", 205000.0)],
        12.00, 9.00, 13.10, 11.0, "UD-RL-329-EC-0011"),
    _cooling_water("SV32965", "329", "109", "329E002", "WR1-329153-BB07DA",
                   "UD-RL-329-EC-0012"),
    _cooling_water("SV32966", "329", "104", "328E001", "WR1-329110-BB07DA",
                   "UD-RL-329-EC-0013"),
    _cooling_water("SV32968", "329", "103/2", "328E004", "WR1-329157-BB07DA",
                   "UD-RL-329-EC-0014"),
    _cooling_water("SV32969", "329", "105/1", "324E002", "WR1-329190-BB07DA",
                   "UD-RL-329-EC-0015"),
    _cooling_water("SV32970", "329", "109", "321P002A", "WR1-329170-BB07DA",
                   "UD-RL-329-EC-0016"),
    _cooling_water("SV32971", "329", "109", "321P002B", "WR1-329171-BB07DA",
                   "UD-RL-329-EC-0017"),
    _cooling_water("SV32972", "329", "109", "323P001A", "WR1-329172-BB07DA",
                   "UD-RL-329-EC-0018"),
    _cooling_water("SV32973", "329", "109", "323P001B", "WR1-329173-BB07DA",
                   "UD-RL-329-EC-0019"),
    _cooling_water("SV32976", "329", "107/2", "329E001", "WR1-329156-BB07DA",
                   "UD-RL-329-EC-0020"),
    *(_sv(tag, "329", "107/1", protects, line, ["Control loop failure", "Control loop failure"],
          [("LP steam", "Steam", 55000.0), ("LP condensate", "Liquid", 53000.0)],
          7.00, 4.40, 7.60, 6.0, doc)
      for tag, protects, line, doc in (
          ("SV32978", "322D001A", "STLS1-322D001A-BB07D (N14A)", "UD-RL-329-EC-0021"),
          ("SV32979", "322D001A", "STLS1-322D001A-BB07D (N14B)", "UD-RL-329-EC-0022"),
          ("SV32980", "322D001B", "STLS1-322D001B-BB07D (N14B)", "UD-RL-329-EC-0023"),
          ("SV32981", "322D001B", "STLS1-322D001B-BB07D (N14A)", "UD-RL-329-EC-0024"))),
    _cooling_water("SV32982", "329", "105/2", "324E005", "WR1-329114-BB07DA",
                   "UD-RL-329-EC-0025 rev 01"),
    _cooling_water("SV32983", "329", "105/2", "324E006", "WR1-329115-BB07DA",
                   "UD-RL-329-EC-0026 rev 01"),
    _cooling_water("SV32984", "329", "105/2", "324E007", "WR1-329116-BB07DA",
                   "UD-RL-329-EC-0027 rev 01"),
    # ----- 335: UF85 dosing ------------------------------------------------------------------
    _sv("SV33554", "335", "106", "335P002A/B", "UF1-335183-EC08DB", ["Thermal expansion"],
        [("Ureaformaldehyde", "Liquid", 100.0)], 11.00, 6.00, 12.00, 10.0,
        "UD-RL-335-EC-0001 rev 01", atm=1.010),
]

#: Every device by tag.
RELIEF_DEVICES: dict[str, ReliefDevice] = {d.tag: d for d in _DEVICES}


def relief_devices_on(equipment: str) -> list[ReliefDevice]:
    """The devices whose sheet names `equipment` as what they protect.

    Process utility
    ---------------
    Where a unit's pressure can run away — a blocked overhead, a failed letdown — the relief
    model reads the device that protects it here: its set pressure is where the unit stops
    rising, and its sized case is what it can pass.
    """
    return [d for d in _DEVICES if d.protects.split()[0] == equipment]


# ======================================================================================
# What each valve can pass: Sempell's orifice selections
# ======================================================================================

@dataclass(frozen=True)
class ReliefSizing:
    """A valve's certified capacity, as its vendor's orifice selection prints it."""

    orifice: str                        # the orifice letter
    area_mm2: float                     # the selected orifice's flow area
    service: str                        # "gas", "steam" or "liquid", the fluid it was sized on
    t_c: float                          # the sizing temperature [deg C]
    mw: float | None                    # molar mass [kg/kmol], gas only
    k: float | None                     # isentropic exponent, gas only
    z: float | None                     # compressibility, gas only
    rho_kgm3: float | None              # density, liquid only
    kd: float                           # the certified discharge coefficient the capacity is on
    capacity_kgh: float                 # the actual capacity at the relieving pressure
    overpressure: float                 # the relieving pressure's rise over set [- of set]
    blowdown: float                     # how far below set it reseats [- of set]
    source: str

    def relieving_bara(self, device: ReliefDevice) -> float:
        """The pressure the capacity is certified at [bar a]: set plus the overpressure."""
        return device.set_bara + self.overpressure * device.set_barg

    def reseat_bara(self, device: ReliefDevice) -> float:
        """The pressure the valve reseats at [bar a]: set less the blowdown."""
        return device.set_bara - self.blowdown * device.set_barg


def _sempell(orifice, area, service, t_c, kd, capacity, blowdown, doc, mw=None, k=None, z=None,
             rho=None):
    return ReliefSizing(orifice=orifice, area_mm2=area, service=service, t_c=t_c, mw=mw, k=k,
                        z=z, rho_kgm3=rho, kd=kd, capacity_kgh=capacity, overpressure=0.10,
                        blowdown=blowdown, source=f"Sempell orifice selection, Uhde {doc}")


_SIZING = {
    # 322R001's two: a lift-limited K orifice (9.04 mm), 105 t/h of carbamate gas required.
    ("SV32251", "SV32252"): _sempell("K", 1452.20, "gas", 183.0, 0.732, 116667.0, 0.10,
                                     "UD-RL-G00-DZ-0002-001 page 1", mw=24.0, k=1.010, z=0.78),
    # 322C001's: sized on liquid and gas blowing simultaneously.
    ("SV32253",): _sempell("M", 2827.43, "liquid", 114.0, 0.644, 212834.0, 0.20,
                           "UD-RL-G00-DZ-0002-001 page 2", rho=947.0),
    # 323C003's two: 60 t/h of carbamate gas required on LV-322501 failing open.
    ("SV32351", "SV32352"): _sempell("T", 20106.20, "gas", 125.0, 0.917, 72273.6, 0.10,
                                     "UD-RL-G00-DZ-0002-001 page 3", mw=25.07, k=1.010, z=1.00),
    ("SV32355", "SV32356"): _sempell("H", 615.75, "liquid", 75.0, 0.644, 70297.6, 0.20,
                                     "UD-RL-G00-DZ-0002-001 page 4", rho=1218.0),
    # 328C002's two: lift-limited (16.23 mm) to the 22.5 t/h required.
    ("SV32850", "SV32851"): _sempell("T", 20106.20, "gas", 159.0, 0.353, 25000.0, 0.10,
                                     "UD-RL-G00-DZ-0002-001 page 5", mw=18.0, k=1.310, z=0.99),
    # 320R001's on the CO2 discharge line CO02-320202: lift-limited (5.26 mm) on orifice H,
    # 67 t/h of CO2 required (read in session 47).
    ("SV32064",): _sempell("H", 615.75, "gas", 140.0, 0.654, 74444.40, 0.10,
                           "UD-RL-G00-DZ-0001-001 page 72", mw=43.370, k=1.510, z=0.74),
    ("SV32261",): _sempell("D1", 153.94, "gas", 60.0, 0.581, 150.71, 0.10,
                           "UD-RL-G00-DZ-0001-001 page 89", mw=29.0, k=1.010, z=0.78),
    # 328D001's and 323D011's: liquid-rated, "not for flashing liquids".
    ("SV32353",): _sempell("K", 1462.20, "liquid", 63.8, 0.644, 110870.0, 0.20,
                           "UD-RL-G00-DZ-0001-001 page 90", rho=976.0),
    ("SV32357",): _sempell("F", 240.53, "liquid", 63.8, 0.644, 18340.5, 0.20,
                           "UD-RL-G00-DZ-0001-001 page 91", rho=976.0),
    # 328C003's: superheated steam at 330 C, 16 t/h required on a blocked outlet; the sheet
    # prints no molar mass, exponent or compressibility for steam.
    ("SV32852",): _sempell("L", 2206.18, "steam", 330.0, 0.922, 24897.4, 0.10,
                           "UD-RL-G00-DZ-0001-001 page 92"),
    # Unit 329's drums (read in session 37): "superheated steam" at the set pressure's saturation
    # temperature. 329D005's is lift-limited (29.60 mm) on orifice R, 125 t/h required.
    ("SV32951",): _sempell("R", 12271.80, "steam", 224.0, 0.813, 138889.0, 0.10,
                           "UD-RL-G00-DZ-0001-001 page 103"),
    ("SV32952",): _sempell("Q", 8494.87, "steam", 188.0, 0.922, 53030.3, 0.10,
                           "UD-RL-G00-DZ-0001-001 page 104"),
    # 322D001A/B's four, 55 t/h required each (pages 114 to 117).
    ("SV32978", "SV32979", "SV32980", "SV32981"): _sempell(
        "T", 20106.20, "steam", 165.0, 0.922, 73383.5, 0.10,
        "UD-RL-G00-DZ-0001-001 pages 114-117"),
}

#: Every valve with an orifice selection in the archive, by tag.
RELIEF_SIZING: dict[str, ReliefSizing] = {tag: sizing for tags, sizing in _SIZING.items()
                                          for tag in tags}


# ======================================================================================
# A liquid-rated valve on a vapour node (decided 2026-10-01, handoff A-16)
# ======================================================================================

#: The gas discharge coefficient taken for a valve Sempell rated on liquid alone, where the model
#: relieves vapour through it (SV32253 on 322C001, SV32353 on 328D001, SV32357 on 323D011): the
#: series' own full-lift gas coefficient, alpha_w 0.917, as certified on SV32351/52's orifice T
#: (UD-RL-G00-DZ-0002-001 page 3). An ASSUMPTION, decided by the process engineer on 2026-10-01
#: (option b): Sempell's VdTUV type test for orifices F, K and M in gas service is not in the
#: archive (handoff, Open data gaps); to be validated in Phase 7.
GAS_KD_ASSUMED = RELIEF_SIZING["SV32351"].kd

#: How far below set a valve relieving gas reseats [- of set]: 10 %, the Series S manual's figure
#: for gases (UD-RL-G00-DZ-0001-003, section 3.9), and Sempell's on every gas valve it sized here.
GAS_BLOWDOWN = 0.10


def gas_reseat_bara(device: ReliefDevice) -> float:
    """Where a liquid-rated valve relieving gas reseats [bar a]: set less the gas blowdown.

    Process utility
    ---------------
    Sempell sets the blowdown by the fluid relieved — gases close 10 % of set below it, liquids
    20 %. A valve sized on liquid that the model lifts on vapour is relieving gas, so it cycles
    on the gas band.
    """
    return device.set_bara - GAS_BLOWDOWN * device.set_barg
