# Deck v10 brief (Jasper, 10/27): simple, professional, in the format of a reference deck

## Format (copy the format, not the content)
Reference: a friend's onsite deck. White slides; bold black title top-left; content in light-grey rounded cards with a
bold card heading and short bullets; two or three cards side by side; photos and figures at the right or inside cards;
a thin black footer bar with a letter-spaced deck name at left and the page number at right; plain title slide with
name | Mechanical Engineering | Texas A&M; plain "Thank you" end slide. Arial/Calibri. No evidence pills, no colour
accents beyond black/grey/one dark blue, no icons, no decorative shapes.

## Rules
- Bullets only. Jasper talks; the slide reminds him. Short.
- NOTHING invented. Every number and claim must come from the record (DECK_V9_NOTES.md slide table, the answers file,
  REQUIREMENTS.md, DECISIONS.md, calculations/, docs/COST_BREAKDOWN_20261026.md, DESIGN_INTENT_20261027.md).
- No statement the author cannot fully back up. If the record says "assumed" or "calculated", the slide says so.
- Nothing "crazy": no dense tables, no walls of text, no jargon without a plain word next to it.

## Flow (one slide each unless noted)
1. Title.
2. About me.
3. Project scope: the problem, the proposed solution, how we do it.
4. Generation 1: the first design (central unit driving four corner motors, overhead ceiling camera).
5. Problems with Generation 1.
6. What a winch on a wall needs to work: the button (what it does), the encoder (what it does) -> and now all this wiring.
7. The solution: a modular box that only needs power. 16 AWG: a short loss calculation (and cost) for why 16 gauge.
8. Modular, for the everyday user: unmount, remount, plug in, take out; slip out of the mount to open the electronics
   and work on it, close it, slide it back; no unscrewing from the wall.
9. Trade-offs, one slide: the graphs and what each component needs (weight, heat/cooling, pull, the factors), BEFORE
   the claw.
10-11. The mount assembly design: a picture of the assembly, geometry, why dovetails; bullet reminders only.
12. The claw, and why it is modular.
13-14. Electrical, testing, making it work (station bench, claw bench, on the wall).
15. How the claw calibrates itself, explained simply (text in CALIBRATION_SIMPLE.md).
16. Next steps / next iteration: what was not working and what changes (Jasper shows new CAD).
17. Thank you.
