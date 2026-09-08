---
name: GTAB
description: Guitar tablature read back from video, on a plain-text tab sheet.
colors:
  paper: "#fbfbf8"
  paper-2: "#f4f3ee"
  paper-3: "#edece4"
  ink: "#20211c"
  ink-2: "#575852"
  ink-3: "#706f68"
  ink-ghost: "#9a9a90"
  rule: "#dad8ce"
  rule-2: "#c4c2b6"
  route: "#cc4033"
  route-bright: "#d8564a"
  route-press: "#b5372c"
  route-ink: "#ffffff"
  route-wash: "rgba(204, 64, 51, 0.1)"
  route-line: "rgba(204, 64, 51, 0.42)"
  route-faint: "rgba(204, 64, 51, 0.32)"
typography:
  lead:
    fontFamily: "Overpass, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(12px, 2.4vw, 16px)"
    fontWeight: 600
    lineHeight: 1.9
    letterSpacing: "0.14em"
  body:
    fontFamily: "Overpass, ui-sans-serif, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  message:
    fontFamily: "Overpass, ui-sans-serif, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Overpass, ui-sans-serif, system-ui, sans-serif"
    fontSize: "10px"
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: "0.16em"
  stamp:
    fontFamily: "Overpass Mono, ui-monospace, monospace"
    fontSize: "13px"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "0.12em"
  mono-staff:
    fontFamily: "Overpass Mono, ui-monospace, monospace"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.9
    letterSpacing: "0"
  mono-readout:
    fontFamily: "Overpass Mono, ui-monospace, monospace"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "tabular-nums"
  mono-value:
    fontFamily: "Overpass Mono, ui-monospace, monospace"
    fontSize: "19px"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "0.1em"
    fontFeature: "tabular-nums"
rounded:
  sharp: "0"
  focus: "1px"
spacing:
  step: "8px"
  panel-pad: "20px"
  stage-inset: "40px"
  dock-h: "172px"
components:
  button-primary:
    backgroundColor: "{colors.route}"
    textColor: "{colors.route-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.sharp}"
    height: "44px"
    width: "100%"
  button-primary-hover:
    backgroundColor: "{colors.route-bright}"
    textColor: "{colors.route-ink}"
  button-primary-active:
    backgroundColor: "{colors.route-press}"
    textColor: "{colors.route-ink}"
  button-primary-disabled:
    backgroundColor: "{colors.paper-3}"
    textColor: "{colors.ink-ghost}"
  button-ghost:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink-2}"
    typography: "{typography.label}"
    rounded: "{rounded.sharp}"
    height: "38px"
    width: "100%"
  button-ghost-hover:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
  transport-button:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sharp}"
    height: "34px"
    width: "34px"
  readout-row:
    backgroundColor: "{colors.paper-2}"
    textColor: "{colors.ink-2}"
    typography: "{typography.mono-readout}"
    rounded: "{rounded.sharp}"
    padding: "8px 0"
---

# Design System: GTAB

## Overview

**Creative North Star: "The Grease-Pencil Tab Sheet"**

GTAB is a plain-text tablature sheet, not an upload form and not a DAW. The whole
surface is a warm paper-white sheet ruled with single hairlines: a full-bleed
stage that carries the six-line ASCII staff anchored top-left and growing
downward, a right control column where a transport would sit, and a bottom dock
holding a to-scale chord-shape diagram. There is no centered drop-card and no
friendly stepper — the empty stage is itself the drop target, and the readable
payoff is a monospace tab block you can copy verbatim.

The system is flat, quiet, and near-monochrome. Depth is three warm tonal steps
of paper plus two weights of 1px hairline — no cards, no shadows, no gradients,
no glow. One color has hue: a grease-pencil red (`#cc4033`) that behaves like a
mark made on the sheet by hand. It carries the present moment (the playhead, the
fret digits sounding now inverted white-on-red, the fretted dots on the chord
diagram, the scrub fill), the single primary action, and the machine's own
status marks (focus ring, text selection, the processing scan line, the
drop-target frame, the failure tag). Everything else is graphite ink on paper.

Two typefaces divide all the labor: Overpass for tracked-uppercase labels and
running prose, Overpass Mono for the tab staff and every number. Graphite ink is
never pure black. Corners are square everywhere; the only curve in the build is a
1px focus outline. `color-scheme` is locked to `light`.

**Key Characteristics:**
- Full-bleed sheet: stage + right control column + bottom chord dock, no page margins.
- Warm paper ground (`#fbfbf8`) with 1px hairlines instead of shadows or cards.
- One hue only — grease-pencil red — for "now", the one action, and machine status.
- Square corners (0 radius); the only curve is the 1px focus outline.
- Two-font split: tracked-caps / prose Overpass, everything numeric in Overpass Mono.
- Graphite ink (`#20211c`), never `#000`.

## Colors

A warm paper greyscale with a single hand-drawn red; nothing else carries hue.

### Primary
- **Grease-Pencil Red** (`route`, `#cc4033`): The only hue. Fills the primary
  action button; draws the 2px playhead line and its arrowhead; backs the fret
  digit(s) sounding "now" as white-on-red inversion in the staff; fills the
  fretted dots (with white fret numbers) on the chord diagram; fills the video
  scrub progress; draws the processing scan line and its scattered tick marks;
  outlines the armed drop-target and the failure tag; is the focus-ring and
  text-selection color. Hover brightens to **Red Bright** (`route-bright`,
  `#d8564a`); press/active darkens to **Red Press** (`route-press`, `#b5372c`),
  which is also the selection text color. **Red Ink** (`route-ink`, `#ffffff`) is
  the text/number color on any red fill. `route-wash` (10% alpha) is the
  selection background, drop-zone fill, and scan-trail tint; `route-line` (42%
  alpha) is the dashed drop frame and failure-tag border; `route-faint` (32%
  alpha) is the dot before each system's start-time callout.

### Neutral
- **Paper** (`paper`, `#fbfbf8`): Stage and app background; the opaque backing
  behind the idle prompt so it clears the ghost staff.
- **Paper 2** (`paper-2`, `#f4f3ee`): The right control column and the bottom
  dock fill.
- **Paper 3** (`paper-3`, `#edece4`): Recessed fills — the scrub track, disabled
  and busy primary button, the inline `<code>` chip, one band of the dev video hatch.
- **Ink** (`ink`, `#20211c`): Primary text, the stamp border, promoted fret
  digits in the staff, transport glyphs, the chord-diagram nut and value readout.
- **Ink 2** (`ink-2`, `#575852`): Secondary prose, readout values, string-label
  spans in the staff, ghost-button text, open-string rings.
- **Ink 3** (`ink-3`, `#706f68`): Tertiary labels (the AA floor on paper for
  small text), the recessed staff structure (dashes and bars), timestamps,
  section labels, string lines on the chord diagram.
- **Ink Ghost** (`ink-ghost`, `#9a9a90`): Barely-there marks — disabled-button
  text, scrollbar thumb hover, the idle ghost staff at its faintest.
- **Hairline** (`rule`, `#dad8ce`): The default 1px division — header rule, stage
  head border, readout row dividers, system separators, the idle ghost staff.
- **Hairline Strong** (`rule-2`, `#c4c2b6`): The heavier 1px stroke — control
  column and dock edges, ghost/transport button borders, the video frame, the
  chord-diagram frets, scrollbar thumb.

### Named Rules
**The Red Is A Mark Rule.** Red is a grease-pencil mark on the sheet, not a
brand color. It only ever means one of three things: *this is happening now*
(playhead, now-notes, fretted dots, scrub fill), *this is the one action*
(primary button), or *this is the machine talking* (focus ring, selection,
processing scan, drop frame, failure tag). An element that wants red for
emphasis, hierarchy, or decoration gets an ink grey instead.

**The Graphite Rule.** Text ink is `#20211c` and never pure black. Every darker-
looking mark is either red or one of the four ink greys.

**The Recessed-Staff / Promoted-Digit Rule.** In the tab block the structure —
dashes, bars, string letters — sits at Ink 3; only the fret numbers lift to Ink,
and only the now-notes go to white-on-red. Legibility of the payload is tonal,
not chromatic.

## Typography

**Label / Prose Font:** Overpass (variable; fallback ui-sans-serif, system-ui) — self-hosted via `next/font/google`, exposed as `--font-sans` / `--font-ui`.
**Staff / Numeric Font:** Overpass Mono (variable; fallback ui-monospace, monospace) — self-hosted via `next/font/google`, exposed as `--font-mono` / `--font-tab`.

**Character:** Overpass is a humanist grotesque used two ways only: tracked and
uppercase for labels and tags, or plain sentence case for prose. Overpass Mono is
the instrument face — it draws the fixed-width ASCII staff and every readout,
clock, count, and voicing, always with `tabular-nums` so columns stay true.

### Hierarchy
- **Lead** (Overpass, 600, `clamp(12–16px)`, 0.14em, uppercase, line-height 1.9,
  Ink 2): the idle-state invitation ("DROP A GUITAR VIDEO TO READ ITS TAB"),
  max 26ch, balanced wrap. The largest type in the system.
- **Chord Value** (Overpass Mono, 600, 19px, 0.1em, `tabular-nums`, Ink): the
  `x 0 2 x x x` voicing string in the bottom dock.
- **Message** (Overpass, 400, 15px, line-height 1.6, Ink): the failure message
  line; 13px Ink 2 for its recovery hint; the empty-result note.
- **Body** (Overpass, 400, 14px base / 11–13px small, line-height 1.5–1.6, Ink 2–3):
  panel hints, the "reading the diagram" blurb, the empty-tab note.
- **Label** (Overpass, 600, 9.5–10.5px, 0.16–0.2em, uppercase, Ink 3): readout
  keys (`dt`), legend/section heads, the stamp sub-line, the header file prefix
  ("TAB"), the process label; the failure tag is this in red at 0.2em inside a
  red-line border.
- **Stamp** (Overpass Mono, 600, 13px, 0.12em, Ink) inside a 1.5px Ink border:
  the "GTAB" mark at the top of the control column — a rubber-stamp, not a logo.
- **Staff** (Overpass Mono, 400, 16px, line-height 1.9, letter-spacing 0,
  `white-space: pre`, Ink 3 structure / Ink digits / white-on-red now-notes):
  the six-line tablature block, `PLAYABLE = 72` characters wide per system.
- **Readout / Clock** (Overpass Mono, 400, 11–12px, `tabular-nums`, Ink 2–3):
  file name (ellipsis at 20ch), length, note count, tuning, transport time,
  elapsed seconds, per-system start times, the header stats line.

### Named Rules
**The Two Voices Rule.** Overpass carries every label (tracked, uppercase) and
every sentence (sentence case) — nothing else. Overpass Mono carries the staff
and anything numeric. A number never appears in the sans face; a running
sentence never appears in the mono face. No third family, no italics (the staff's
digit promotion is a color/weight change, not `<i>`).

**The Tracked-Caps-Or-Sentence Rule.** Overpass appears only at 0.14–0.2em
tracking in uppercase, or at normal tracking in sentence case. There is no
in-between (no title-case headings, no tracked lowercase).

## Layout

**Shell:** A CSS grid — `"stage side" 1fr / "dock dock" var(--dock-h)`. The stage
is `minmax(0, 1fr)`; the right control column is `clamp(300px, 24vw, 348px)`; the
bottom dock is a fixed 172px. Full viewport height (`100dvh`), `overflow: hidden`
— the page never scrolls; only the tab area and the control column scroll
internally.

**Stage:** A flex column. A stage head (`padding: 15px 30px 13px 40px`, 1px
`rule` bottom border) carries the "TAB · filename" prefix, a flexible hairline,
and — when done — the "N notes · M:SS · E A D G B e" stats. Below it the state
body fills. The ASCII staff is anchored to the top-left with a ~40px left inset
and grows downward; systems stack and are separated by a 1px `rule` top border,
each with its start time pinned top-right as a dimension-style callout.

**Right column:** Vertical flex, `padding: 18px 20px`, `gap: 16px`. Stamp at top
over a hairline; on the done screen the 16:10 video and transport slot in below
it; then the readout `<dl>` (hairline-divided rows, `padding: 8px 0`); then the
legend; then the actions block pinned to the bottom (`margin-top: auto`) above a
hairline. `background: paper-2`, 1px `rule-2` left border.

**Dock:** `grid-template-columns: auto 1fr` — the chord diagram + voicing meta in
a left cell with a 1px `rule` right border, a prose "reading the diagram" note
filling the rest. `background: paper-2`, 1px `rule-2` top border.

**Spacing:** Nominal `--step` is 8px, but padding is set per context (13, 14, 16,
18, 20, 22, 28, 30, 40px observed) rather than snapped hard to the scale. Density
is tight in the control column, generous in the stage.

**Responsive:** Three breakpoints.
- **880px:** the grid restacks to single-column `stage / side / dock`; height
  goes `auto` with `min-height: 100dvh`; the column's left border becomes a top
  border; the stage takes `min-height: 60vh`; staff type drops to 14px; stage
  padding-left tightens to 24px.
- **640px:** the header's flexible rule and stats line are hidden.
- **520px:** the dock collapses to one column, the prose note is hidden, and the
  chord diagram centers.

## Elevation & Depth

**No shadows. No blur. No glow. No `box-shadow` anywhere in the build.** Depth is
warm tonal layering plus 1px hairlines only. The paper stack, lightest to
deepest: `paper #fbfbf8` (stage) → `paper-2 #f4f3ee` (control column, dock) →
`paper-3 #edece4` (scrub track, disabled/busy button, code chip). Every boundary
is a single 1px line — `rule #dad8ce` for content divisions (rows, systems,
header), `rule-2 #c4c2b6` for structural and interactive edges (column/dock
edges, button and video borders).

### Named Rules
**The Hairline Rule.** Every division in the UI is one 1px line — `rule` inside
content, `rule-2` at the structural edges. Never a card, never a shadow, never a
fill change alone to imply an edge.

**The Motion-Is-A-Mark Rule.** The processing scan is a 2px red line with a
`route-wash`→transparent gradient trail; that gradient is an alpha mask shaping a
*moving* mark (a scanning head), not a fill. It must not widen, brighten, slow to
rest, or leave red in the static chrome. Same for the `route-wash` behind text
selection: a wash, not a highlight block.

## Shapes

**Radius is 0 everywhere** — buttons, the video frame, the scrub track and fill,
the stamp box, the drop frame, the failure tag, legend swatches. The only curve
in the system is `:focus-visible`: a `2px solid var(--route)` outline at
`outline-offset: 2px` with a `1px` border-radius. The now-note spans and scrub
fill carry a nominal `1px` radius that reads as square at their size.

**Strokes over fills for form.** Ghost buttons, transport buttons, the stamp, the
failure tag, the armed drop zone, the chord-diagram open-string rings and "chord"
legend swatch are all defined by 1px borders on paper, not filled shapes. Filled
shapes are reserved for the red primary button and the red now/playhead/fretted
marks.

**Chord diagram (signature geometry).** A flat SVG box (viewBox 108×132): a
heavier Ink nut when the shape sits at position 1, otherwise a light `rule-2` top
line with an `Nfr` mono label; `rule-2` fret lines; six string lines in Ink 3
weighted progressively toward the low E (`0.6 + i*0.18`px); red dots (r 6.5) with
white mono fret numbers for fretted notes, Ink 2 rings for open strings, Ink 3
`×` for muted. It renders as a full grid only when ≥2 notes were struck together,
a single dot otherwise; no chord-name inference.

## Components

### Buttons
- **Shape:** Square (0 radius). Full-width in the actions stack; `width: auto` with
  `0 20–22px` horizontal padding when inline ("Choose a file", "Start over").
- **Primary** (`.primary`): Red fill (`#cc4033`), white text, 44px tall, Overpass
  700 / 11px / 0.2em uppercase. Hover → Red Bright. Active → Red Press +
  `translateY(1px)`. Disabled → Paper 3 fill, Ink Ghost text, `not-allowed`.
  Busy (`.primaryBusy`) → Paper 3 fill, Ink 2 text, `cursor: progress`, with a
  trailing 7px red square that blinks on a 1s `steps(2, jump-none)` loop. The
  file input is a visually-hidden `<input type="file">` inside a `<label>` styled
  as this button.
- **Ghost** (`.ghost`): No fill, 1px `rule-2` border, Ink 2 text, 38px tall,
  Overpass 600 / 10.5px / 0.16em uppercase. Hover → border to Ink 3, text to Ink.
  Used for "New file", "Start over", "Choose a file".
- **Transport** (`.transportBtn`): 34px square, 1px `rule-2` border, Ink inline-
  SVG play/pause glyph. Hover → border to Ink 2 (never red — hover affordances
  move within the greys, per The Red Is A Mark Rule).

### Readouts (signature)
A `<dl>` of key/value rows, each `padding: 8px 0` with 1px `rule` top and bottom
borders. `dt` = Overpass 600 / 9.5px / 0.16em uppercase / Ink 3. `dd` = Overpass
Mono 12px / `tabular-nums` / Ink 2, right-aligned, truncating with ellipsis at
20ch. Empty values render as an em dash (`—`), never blank. Keys carry a
lab-bench register on purpose ("Specimen", "Length", "Notes", "Tuning").

### Scrubber
A 3px-tall `paper-3` track, 0 radius, with an absolutely-positioned red
`scrubFill` measured by percentage. `role="slider"`, keyboard-seekable ±2s with
arrows. A click on any staff column also seeks; both feed one `seek()`.

### Inputs / Fields
No text inputs on this surface — the only input is the hidden file picker. There
is no focus "glow"; focus is the themed 2px red outline from `globals.css`,
applied uniformly.

### Interactive Tab Block (signature)
Stacked "systems" of fixed 72-character width, `white-space: pre`, Overpass Mono
16px / 1.9, Ink 3. Each system is a `role="button"` seekable region separated
from the next by a 1px `rule` top border, with its start time pinned top-right in
11px mono preceded by a `route-faint` dot. Each string line is rebuilt from raw
text so structure stays at Ink 3, fret digits lift to Ink (`.fig`, 600), and any
digit within 0.16s of the playhead inverts to white-on-red (`.now`). The playhead
is a 2px red line with a small red triangle cap, transitioning `left` at 0.09s
linear across the active system. An `aria-live="polite"` region announces "Line
N, m:ss" once per system crossed. Empty result → six bare `e|---…---|` lines plus
an Overpass note, visually distinct from the red failure tag.

### Processing State (signature)
No progress bar. A ghost staff in `rule-2`; a 2px red `.scan` line with a 76px
`route-wash` gradient trail traveling on a 2.4s `cubic-bezier(0.65,0,0.35,1)`
loop; during `processing` (not `pending`) ~22 faint 1ch red `.tick` squares
(opacity ~0.28) scatter along the string lines on staggered pulse loops, reading
as notes being found. Label: Overpass tracked-caps stage name ("EXTRACTING
AUDIO") with the active phase in red, plus elapsed seconds in mono. `pending`
shows only "In queue".

### Failure State
An Overpass 10.5px / 0.2em uppercase "Transcription stopped" tag in red inside a
1px `route-line` border; the backend `error` string as a 15px Ink message; a
13px Ink 2 recovery hint; an inline ghost "Start over". Max 62ch.

### Idle State
The empty stage is the drop target. A ghost ASCII staff sits absolutely at
top-left in `rule` (labels in `rule-2`); a centered `idlePrompt` with a `paper`
background carries the tracked-caps Lead invitation, a mono format list in Ink 3,
and a ghost "Choose a file". On drag-over the stage body gets an inset 1px dashed
`route-line` frame over a `route-wash` fill, pulsing on a 1.4s loop.

### Navigation
None. Single route, no history, no nav chrome. The right column is the only
persistent control surface.

## Do's and Don'ts

### Do:
- **Do** keep red (`#cc4033`) to the three meanings — "now", the one action, and
  machine status — and give every other element an ink grey.
- **Do** divide surfaces with a single 1px line (`#dad8ce` in content, `#c4c2b6`
  at edges) and build depth from the three paper steps (`#fbfbf8`→`#edece4`).
- **Do** ship square corners (0 radius); the only curve is the 1px focus outline.
- **Do** route labels through tracked-caps Overpass, sentences through sentence-
  case Overpass, and every number through Overpass Mono with `tabular-nums`.
- **Do** keep the staff structure at Ink 3 and lift only fret digits to Ink;
  reserve white-on-red for the notes under the playhead.
- **Do** render empty readout values as `—`, never blank.
- **Do** make waiting diegetic — a scan line and a scatter that read as the
  machine working — never a fake percentage or progress bar.
- **Do** provide a non-color channel for every state: text tags, `×`/`○` glyphs,
  `aria-live` line announcements, `role="slider"` / `role="button"` on seek regions.
- **Do** keep `color-scheme: light`; graphite ink is `#20211c`, never `#000`.

### Don't:
- **Don't** add `box-shadow`, blur, or glow to any surface. There are none.
- **Don't** use gradients as fills. The only gradient is the `transparent`-stop
  alpha mask on the moving scan trail; the dev video hatch is a pattern, not a fill.
- **Don't** introduce a second hue or spend red on headings, structure, hover
  emphasis, or decoration.
- **Don't** wrap content in rounded cards or panels; use the hairline.
- **Don't** center a drop-card or add a stepper — the empty stage is the drop
  target and the staff is the hero.
- **Don't** mix the two faces across roles (no mono sentences, no sans numerics)
  or add a third family or italics.
- **Don't** set Overpass in title case or tracked lowercase — tracked-caps or
  sentence case only.
- **Don't** let the processing scan or the selection wash widen, brighten, or
  persist at rest.
