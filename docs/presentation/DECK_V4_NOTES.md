# Deck v4: industry-standard restyle (2026-10-21)

Jasper asked whether deck v3's theme was the most appropriate and professional choice, and to research and apply an
industry standard instead of a custom look.

## Standard used

**Assertion-evidence slide design**: Michael Alley's group, Penn State College of Engineering; taught to engineers and
scientists, with studies showing better comprehension and recall than topic-and-bullet slides.
- Every content slide's headline is one full sentence that states the takeaway; it is not a topic label.
- The visual is the evidence: chart, photo, CAD render or diagram.

Sources: https://writing.engr.psu.edu/research.html, https://www.huck.psu.edu/event/rethinking-slide-design-in-scientific-presentation-the-assertion-evidence-approach-1

Styling follows plain engineering-company conventions:
- Arial throughout, black text on white, one dark-blue accent.
- Headline at top left with a thin grey rule under it. No small-caps section labels above the title.
- Square, light-grey equation boxes labelled "Key equations".
- Plain (non-italic) captions; every chart caption is a source line: "Source: calculation sheet (Google Sheets), '<tab>' tab. Calculated, not measured."
- Footer: name, date and page number.

## What changed and what did not

- **Changed:** every content slide's title is now an assertion headline, one line each.
- **Content:** the same as v3.2: bullets, equations, Sheet charts, photos and speaker notes.
  - Two bullets were shortened to fit Arial: the fin-length slide's "Looks" bullet and the winch slide's design-force bullet.
  - Bullets stay, because Jasper asked for bullets on every subject. In assertion-evidence they are supporting text.
- **Files:**
  - `deck_v4/build_deck_v4.js` builds `RoomCleaner_Buntinx_Oct27_v4.pptx` / `.pdf` (46 slides, validated).
  - Figures and Sheet charts are read from `deck_v3/fig`.
  - v1, v2 and v3 stay unchanged.
