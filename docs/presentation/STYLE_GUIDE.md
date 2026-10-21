# Deck Style Guide — "Flight Test Report"

The interview deck should look like an engineer's test report, not a
marketing pitch: quiet, precise, lots of white space, one loud colour used
only where the eye must go. Every slide should be able to survive the
question "how do you know that?" — so every claim carries an evidence tag.

This guide is the contract for every slide. The sampler deck
(`docs/presentation/deck_assets/style_sampler.pptx`) shows each rule in use.

---

## 1. Canvas

| Item | Value |
|---|---|
| Size | 16:9 widescreen, 13.33 × 7.5 in (PowerPoint "Widescreen") |
| Outer margin | 0.6 in on all sides; nothing but full-bleed photos crosses it |
| Grid | 12 columns, 0.25 in gutters inside the margins |
| Footer band | bottom 0.45 in: section name left, slide number right, 9 pt steel |

## 2. Colour

One dominant neutral, one support neutral, one accent. That's it.

| Token | Hex | Use |
|---|---|---|
| **Ink** | `0E1116` | Titles, body text, dark title/section slides (≈ 60 % of the deck's visual weight) |
| **Paper** | `FFFFFF` | Content slide background |
| **Fog** | `E9ECEF` | Cards, table header rows, image mats |
| **Steel** | `6B7480` | Secondary text, axis labels, captions, non-focus chart series |
| **Signal** | `FF6A13` | The ONE thing to look at: chosen option, focus series, callout dot, key number |
| Signal tint | `FFE6D6` | Background of the chosen option card only |

Rules
- Signal orange appears **at most once or twice per slide**. If everything is
  orange, nothing is.
- No other hues. Red/green status colours are replaced by text ("PASS" /
  "FAIL") and the evidence tags.
- Photos keep their real colour; renders use the render palette (§8).

## 3. Type

| Role | Font | Size | Weight / case |
|---|---|---|---|
| Slide title (a claim, ≤ 12 words, aim for one line) | Arial | 30 pt | Bold, sentence case |
| Eyebrow label | Arial | 11 pt | Bold, UPPERCASE, 1.5 pt character spacing, Steel |
| Body | Calibri | 16 pt (14 pt minimum) | Regular |
| Big number | Arial | 72 pt | Bold, Ink (Signal if it's the punchline) |
| Big-number label | Calibri | 14 pt | Steel |
| Caption / source | Calibri | 11 pt | Italic, Steel |
| Equation | Cambria Math / Cambria | 20 pt | Regular |

Arial and Calibri are chosen because they ship with every copy of
PowerPoint and Google Slides, so the deck will look identical on the
panel's laptop.

Writing rules
- **Titles are claims, not topics.** "A 1/8 in fin keeps the motor under
  80 °C" beats "Thermal design".
- Max ~30 words of body text per slide. The talk carries the rest; put
  details in speaker notes.
- Numbers always carry units and, where it matters, a ± or a test count
  ("5/5 runs", "σ ≈ 11 mm").
- Left-aligned everywhere. Never centre body text.

## 4. Evidence tags

Every quantitative claim gets one pill, top-right of the slide or next to
the number. They tell the panel how much to trust the number at a glance.

| Tag | Look | Means |
|---|---|---|
| **MEASURED** | Solid Ink pill, white text | Done on hardware with an instrument |
| **CALCULATED** | Ink outline, Ink text | Hand calc / closed form |
| **SIMULATED** | Dashed Steel outline, Steel text | Ran in the simulator / FEA |
| **PLANNED** | Fog fill, Steel text | Not done yet — honest about it |

Pills: 9 pt Arial Bold uppercase, 0.28 in tall, fully rounded.

## 5. The motif — dimension callouts and the decision rail

Two recurring elements, nothing else decorative:

1. **Dimension callout** — a thin 1 pt Ink leader line ending in a small
   Signal dot on the feature, with a short label at the other end
   ("Ø22.5 bore", "40 N limit"). Used on photos and renders to point at the
   thing being discussed. Max three per image.
2. **Decision rail** — five numbered steps along the bottom of a decision
   slide: `WANTED → REALIZED → DECIDED → RESULT → BUT` (the story flow; BUT = the cost
   accepted or what is still unproven, never skipped). Completed steps
   are Ink, the step being discussed is Signal, future steps are Fog. It is
   the visual signature of the talk: "here's how I think".

## 6. Slide archetypes

| ID | Name | When | Layout |
|---|---|---|---|
| A | Title | Opening | Dark Ink, full-bleed hero photo on the right 55 %, title + name + date left |
| B | Section divider | Start of each act | Dark Ink, giant section number in Signal, one-line section claim |
| C | Decision story | The core slide (one per decision) | Eyebrow "DECISION 04 · HEAT", claim title, hero image left 55 %, three short lines right, decision rail along the bottom |
| D | Options compared | Showing alternatives I rejected | 2–4 Fog cards side by side; chosen card gets Signal tint + "CHOSEN" pill; one line per card on why it lost/won |
| E | Big number | A single result worth pausing on | One 72 pt number, label under it, the equation or test that produced it, evidence tag |
| F | Chart + commentary | Data | Native chart left 60 %, 2–3 takeaways right; focus series Signal, others Steel |
| G | Photo spread | Build/process, "I made this" | 2–3 photos in a row with 0.15 in gaps, numbered captions, optional callouts |
| H | Timeline | Project arc / generations | Horizontal line with dated nodes; current node Signal |
| I | Closing | Lessons + what's next | Dark Ink, three lessons, contact line |

Content slides are white. Title, dividers and closing are dark — the
"sandwich" rhythm tells the panel where the acts break.

## 7. Charts and tables

- Native PowerPoint charts only (editable, crisp when projected).
- One focus series in Signal; all others Steel. No legend if there's one
  series — label the line directly.
- Light horizontal gridlines (`E9ECEF`), no vertical gridlines, no chart
  border, axis text 11 pt Steel.
- Always label the limit or target line ("40 N motor limit").
- Tables: Fog header row, Ink bold header text, no vertical rules, thin
  `E9ECEF` horizontal rules, numbers right-aligned.

## 8. Images

Photos
- Crop tight to the subject. Most shop photos are portrait (1200 × 1600):
  use them as half-height-right or tall-left panels, never stretched.
- No drop shadows, no rounded corners, no frames. Hard edges, like a lab
  notebook.
- If a photo is busy, put a single dimension callout on it rather than
  adding text around it.

Renders (`tools/render_deck_assets.py`)
- Orthographic iso, transparent background, soft studio light.
- PETG / context parts: light grey `CCCFD4`.
- Aluminium: brushed grey with a little specular.
- The part the slide is about: Signal orange. Everything else stays grey.

## 9. Never

- Accent bars, title underlines, coloured header strips
- Gradients, glows, bevels, 3D chart effects, clip-art
- Centred paragraphs, bullet lists longer than four items
- SpaceX logos, imagery or branding (it's their room — don't decorate it)
- Any mention of AI tools in the deck
- Stock photos — every image is mine or my CAD

## 10. Speaker notes

Every slide gets notes with: the one sentence I must say, the numbers I'll
quote, and the likely follow-up question with my answer.
