---
version: 1
slug: "frontend-src-app-page-tsx"
primary_target: "frontend/src/app/page.tsx"
related_targets: []
---

## Scope

The transcription flow: one screen that moves through choose-file, upload, processing (poll), and result. Single route (`frontend/src/app/page.tsx`), no history, no accounts, no persistence. Visitor mode: **Operate**.

## Audience & task

A guitarist who found or filmed a video of a song with no tab, cannot read standard notation, and wants something playable. They bring one video file and a specific song in mind. The task: upload → wait → read and copy the tab, checking it against the video by scrubbing.

Proof to show: the machine read *their* performance — real detected notes at real times — not a generic tab lookup. No accuracy claims, no sample library, no job history (all uninventable per PRODUCT.md). Hand tracking is a backend disambiguation signal, never a user-facing feature.

## Direction contract

**THESIS** — A light, plain-text tab sheet, not an upload form and not a DAW: the readable payoff is a traditional six-line ASCII tablature block you can copy verbatim, made live by an accent-red playhead that runs with the video. It refuses the centered drop-card, the friendly stepper, and the dark audio-editor world it replaces.

**OWN-WORLD** — A warm paper-white ground (`#fbfbf8`), graphite ink (`#20211c`, never pure black), single 1px hairlines (`#dad8ce`) — no cards, no shadows, no gradients, no glow. Exactly one accent, a grease-pencil red (`#cc4033`), rationed to three meanings: the note(s) sounding now (inverted white-on-red in the staff), the live playhead, and the single primary action. Two faces only: Overpass for tracked-uppercase labels and prose, Overpass Mono for the tab staff and every numeric readout. Editor-shell topology is kept: a full-bleed stage (the tab), a right control dock (stamp, video, transport, ruled spec readouts with units, legend, action), and a bottom dock holding a to-scale chord-shape diagram.

**STORY** — The visitor understands the machine read their actual playing; believes it by scrubbing the tab against the video and watching the playhead and chord shape track their hands; acts by copying the plain-text tab.

**FIRST VIEWPORT** — Full-bleed light sheet. A thin header rule carries `TAB · filename` and, when done, `N notes · M:SS · E A D G B e`. The ASCII staff is anchored to the top-left of the stage and grows downward, systems stacked and hairline-separated, each system's start time set in the right margin as a dimension-style callout, all six string lines fixed-width so every trailing bar aligns. The right dock's primary action sits low where a transport lives. The bottom dock shows the chord-shape diagram, empty and captioned at rest. Idle state: a tracked-caps invitation centered in the empty stage, which is itself the drop target.

**SIGNATURE INTERACTION** — One playhead binds video time to the staff: as the video plays it sweeps the active system (`transition: left 0.09s linear`), the fret digits within ~0.16s of it invert to white-on-red, and the bottom-dock chord diagram redraws to the fretting-hand shape at that instant (dots for every note struck together, `○` open, `×` muted, base-fret label when up the neck). Clicking any column of the staff seeks the video. Reduced-motion drops the sweep and the processing scan to static.

**FORM** — Light plain-text tab sheet. Evolved from the assigned direction "The Fretboard Map" (seed key `9665ce27`, re-roll round 1) after the user removed the neck-map chart and the background grid in preview review, keeping the white ground, the one accent, the Overpass type pair, the top-anchored fixed-width staff, the synced playhead, and the chord-shape dock. Code-led: no comp; ambition audited at the finish review against this block and the approved preview `.impeccable/mocks/fretboard-map-preview.html`.

**FINISH** — unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.

## Result artifact

Primary: an **interactive plain-text tab block** — traditional six-line monospace staff, fret numbers spaced proportional to time, wrapped into stacked systems of fixed character width (`PLAYABLE = 72`), multi-digit frets column-aligned so all six string lines stay true and every trailing `|` aligns vertically. Copy-to-clipboard yields exactly the rendered text (`tab.text`). As the video plays, the current column's notes invert to the accent and a playhead line tracks position; clicking a column seeks the video; an `aria-live` region announces the crossed line. The piano-roll note layer is **cut**. The bottom-dock **chord-shape diagram** is a standard vertical chord box driven by `chordAt(positions, t)` — the union of notes still ringing under the hand, marked as a real grid when ≥2 were struck together, a single dot otherwise; no chord-name inference.

## Material states

- Empty / first-run: no file — the stage is a tracked-caps invitation and the drop target.
- File chosen → uploading → processing (`pending` / `processing` from polling `GET /status/{job_id}`): an honest "machine is working" treatment — a ghost staff with an accent scan line and resolving tick marks, the active pipeline stage named in accent, elapsed seconds. No fake progress bar.
- Done: fetch `GET /result/{job_id}`, render staff + video + chord diagram.
- Failed: unsupported type (mp4/mov/webm/mkv/avi/m4v/wav/mp3), ffmpeg extraction failure, no audio track, generic pipeline error — an accent-outlined "Transcription stopped" tag, the backend `error` string, a named recovery, Start over.
- Empty result (silent audio → empty tab): bare fixed-width string lines + a plain-prose "no notes detected" note, visually distinct from the failure tag.
- Backend unreachable: the dev backend allows CORS from `http://localhost:3000` only; a failed fetch surfaces the network hint without a dead screen.

## Constraints

- Next.js 16.2.6 App Router (fork — consult `frontend/node_modules/next/dist/docs/` before touching framework APIs), React 19. Heavily interactive → the flow is a Client Component.
- Type: Overpass + Overpass Mono via `next/font/google` (both variable, no weight array). Replaces Martian Mono / Geist / Geist Mono.
- API base URL configurable (env), default `http://localhost:8000`.
- Accessibility: non-color channel for state (text tags, `×`/`○` glyphs, `aria-live` line announcements, `role="slider"` scrub); transport + "Copy tab" keyboard-operable; focus rings themed to the accent.
- Backend contract is untouched: `POST /upload` (multipart `file`) → `{job_id}`; poll `GET /status/{job_id}`; `GET /result/{job_id}` (409 until done).

## Unresolved

- No demo / sample-video mode (user's call) — a portfolio visitor without a guitar video sees nothing run. Flag if a pre-baked example result should be added later.
- Alternate tunings, tab export to a file format, job persistence — all undecided in PRODUCT.md; do not build them in.
- A future "correct the tab" affordance is implied by the story but not built.
