# Motor station electrical - Rev D (2026-10-21)

Supersedes [Rev C](../station_revC_20261016/README.md) for building. Rev C is
kept unchanged (power circuit, control circuit and audit are carried over).

Read: [RoomCleaner_Station_RevD.pdf](RoomCleaner_Station_RevD.pdf), 5 sheets.
Regenerate with `python3 draw_schematic.py` (reportlab + DejaVu fonts).

| Sheet | Content |
|---|---|
| 1 | Power: J1 12 V inlet, DROK buck to 5.00 V, D1 1N5819, JP1 USB/external link, C1 100 uF/50 V at VMOT, branch fuses at the supply end |
| 2 | Control: XIAO ESP32-C3 D1/GPIO3 STEP, D2/GPIO4 DIR, D3/GPIO5 ENABLE (R1 10k to 3V3), R2/R3 10k STEP/DIR to GND, VDD/RESET/SLEEP to 3V3, NC homing/end-of-travel switch on D10/GPIO10 (R4 10k to 3V3), motor coils |
| 3 | **New:** AS5600 encoder on D4/GPIO6 SDA + D5/GPIO7 SCL at 3.3 V (DIR to GND, OUT unconnected); A4988 Vref for **1.35 A** (D29): R100 -> 1.08 V, R050 -> 0.54 V; microstep jumpers must match config `microsteps` (full step = all LOW = 1) |
| 4 | Connection ledger (every net and every point on it) and meter checks |
| 5 | Audit notes and controlled power-up sequence |

Pin map matches `firmware/winch_station/winch_station.ino` (STEP 3, DIR 4,
EN 5, HOME 10, SDA 6, SCL 7). The "button" on the station is the KW12-3 NC
switch (homing / bead end-of-travel, D26).
