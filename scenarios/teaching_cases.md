# Teaching cases for the instructor

This folder ships the simulator's verified steady states, one `<name>.json` each, which the start-up intro's LOAD
button lists. This note lists procedure cases an instructor can set up from them. It is read by people only: the
engine lists `*.json` here and nothing else.

## Load reduction without the evaporator-feed reduction (323D002 drains)

*Decision 279 (2026-11-20); As-Built §CXLIX.3 and §CL.1.*

- **Start from:** `load100_steam` (or the 100 % design seed).
- **Instructor action:** reduce the battery-limit CO2 demand (`co2_set`) toward 70-75 % at about 0.5 % per minute.
- **The step the trainee should take:** Operating Manual UD-VT-G00-DC-0003 p. 6-23, "slowly reduce the urea solution
  flow to first stage evaporator": FIC-324401 taken off cascade and its set point lowered with the load, the cascade
  under LIC-323507 restored once the plant is steady (p. 1-69).
- **What happens if it is skipped:** the urea solution leaving 323C003 falls with the load while LIC-323507's cascade
  answers slowly, so 323D002 drains and 323P003 loses suction about 20-30 minutes after the load reduction ends (on the
  engine, 4 980-5 000 s from the start of a ramp to 69-74 %).
- **What the trainee should see:** 323D002's level falling at LIC-323507's minimum, then 323P003's suction lost and the
  evaporator's feed stepping when the tank recovers.
- **Caveat:** the drain's rate rests on LIC-323507's tuning (Kc 1.0 t/h per %, Ti 4 030 s), which is V1's estimate; the
  loop has no row in the DCS tuning table, and its tuning page is on the DCS readback checklist (row 29).
