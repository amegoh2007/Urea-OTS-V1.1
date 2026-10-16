"""Unit 335's UF85 dosing — FFIC-335406 over FIC-335405 and 335P002A / B — the design data.

What this is for
----------------
The anti-caking additive UF85, a urea-formaldehyde precondensate, is dosed into the urea melt on
its way to the granulator (PFD 697 into 402G, making 609), its flow held in ratio to the melt by
FFIC-335406 trimming FIC-335405, the metering pumps' flow loop (decided 2026-10-16, `project.md`
decision 123: the dosing runs live on LV-324501A's route, where V1 keeps it interlocked).

The PFD's 697 and 402G rows are the granulation section's own design case: 85 405 kg/h of melt is
2 050 t/d, the granulator's 2 000 MTPD (`References/324-1b Equipment Descriprion and Datasheet
3.md`, its introduction), not the urea plant's 1 750. At the plant's design drain, 75 938 kg/h
(V1's reconciled 402), the PFD's ratio doses 617.1 kg/h — the operating manual's 625 kg/h
(`References/Urea_Operating_Manual_Helwan.md` §2.6) — so FIC-335405 is seeded there and the
design holds; the pumps' stroke law stays anchored on the PFD's 694 kg/h at V1's 50 %.

Source: `References/Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md` (streams 402G, 609,
697); V1 ``backend/main.py`` 3404-3411 (the rows, the ratio, the 50 % stroke) and ``State.__init__``
6803-6814 (the two loops' tunings and limits). Neither loop has a row in the plant DCS's tuning
table (`References/Master_PID_Tuning_Constants.md`), so both keep V1's (handoff Open data gaps);
Uhde's functional diagrams for unit 335 (UD-MR-335-FF-0002, read from the scans) draw no other
structure for them.
"""

from __future__ import annotations

from ureasim.core.packet import normalise_solution_mass_fraction as _w_norm
from ureasim.data.unit_324 import P2_DES_KGH

#: PFD 402G, the raw melt into unit 335 at the granulation case [kg/h].
PFD_402G_KGH = 85405.0

#: PFD 697, UF85 into the melt [kg/h], its temperature [deg C] and density [kg/m3] (1305 at 40 C,
#: the stream's; 1320 is the tank transmitter's SG calibration, V1's note), and its mass fractions,
#: the PFD's 60 % formaldehyde, 25 % urea, 15 % water.
PFD_697_KGH = 694.0
PFD_697_T_C = 40.0
PFD_697_RHO_KGM3 = 1305.0
W_697 = _w_norm(dict(Urea=25.0, H2O=15.0, HCHO=60.0))

#: The dosing ratio, UF85 per kilogram of melt [-]: the PFD's 697 over 402G (V1 ``R324_UF_RATIO``;
#: the DCS ratios on FQI-335401, the melt's flow).
UF_RATIO_DES = PFD_697_KGH / PFD_402G_KGH

#: The UF85 the ratio doses at the plant's design drain [kg/h], 617.1: FIC-335405's seed.
UF85_DES_KGH = UF_RATIO_DES * P2_DES_KGH

#: FIC-335405's stroke at the PFD's 694 kg/h [%] (V1 ``R324_FIC405_OP_DES``): the metering pumps'
#: delivery is linear in it, V1's ``_fic_flow``, the flow transmitter lagged 5 s.
FIC_335405_OP_DES_PCT = 50.0
FT_335405_TAU_S = 5.0

#: FFIC-335406, the ratio master: V1's tuning on the ratio itself, its output the ratio the slave is
#: asked for, 0 to 0.05 (V1 ``State.FFIC_335406``).
FFIC_335406_KC = 0.5
FFIC_335406_TI_S = 60.0
FFIC_335406_RATIO_HI = 0.05

#: FIC-335405, the slave: V1's tuning on its PV in t/h, set point 0 to 1 t/h, output 0 to 100 %
#: (V1 ``State.FIC_335405``).
FIC_335405_KC = 100.0
FIC_335405_TI_S = 15.0
FIC_335405_SP_HI_TH = 1.0

__all__ = [
    "PFD_402G_KGH", "PFD_697_KGH", "PFD_697_T_C", "PFD_697_RHO_KGM3", "W_697", "UF_RATIO_DES",
    "UF85_DES_KGH", "FIC_335405_OP_DES_PCT", "FT_335405_TAU_S", "FFIC_335406_KC",
    "FFIC_335406_TI_S", "FFIC_335406_RATIO_HI", "FIC_335405_KC", "FIC_335405_TI_S",
    "FIC_335405_SP_HI_TH",
]
