# Station 12 V power wiring: cut list (2026-10-21)

Source of the routes: docs/ROOM_LAYOUT_20261014.md. The supply sits on a 3 ft stand near one corner. Each pair
runs down to the floor, along the perimeter and up to a station at 9 ft. Each station gets its own independent
red/black pair of 16 AWG copper, 100 ft roll. Slack is 3 ft per run.

| Run | Route | Cut |
|---|---|---|
| Station above the supply (A if the supply is in A's corner) | 6 ft straight up | 9 ft |
| Along the 11 ft wall (B) | 3 + 11 + 9 = 23 ft | 26 ft |
| Along the 9 ft wall (D) | 3 + 9 + 9 = 21 ft | 24 ft |
| Diagonal (C) | 3 + 11 + 9 + 9 = 32 ft | 35 ft |
| Total | | 94 ft (6 ft spare) |

- Measure each real route before cutting.
- Cut the longest first.
- Label both ends of each pair.

**Supply end:**
1. Supply → existing 7.5 A main fuse.
2. → a WAGO bus for +12 V (red) and a WAGO bus for GND (black).
3. → one inline fuse per red branch, at the supply end. The lead recommends 3 A blade fuses; the value is not
   measured-qualified.

**Station end:** J1 on the Rev D perfboard: red to X01 (+12 V), black to X03 (GND).
- Fit a 5.08 mm screw terminal, or splice a short 18–20 AWG lead, because 16 AWG does not fit the holes.
- Meter the polarity first. The DROK buck has no reverse-input protection.

**Voltage drop:** the 35 ft run is a 70 ft loop, about 0.28 Ω, so about 0.3 V at 1 A.
