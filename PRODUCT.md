# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

The primary user is a guitarist who wants to play a specific song that has no
tablature available for it. They typically cannot read standard sheet music, or
lack the ear-training, theory knowledge, or time to transcribe the song into tab
themselves. They arrive with a video of the song being played (their own
recording or one they found) and want usable tab in return.

This project is built as a portfolio piece for its maintainer, Bertie Simmons. It
is not intended to serve real production traffic or a real user base; the user
description above defines who the product is designed *for*, not an audience it
must currently support.

## Product Purpose

The product turns an uploaded guitar video into guitar tablature automatically.
It exists to remove the transcription barrier for players who can hear a song but
cannot write it down. Success is a generated tab that a guitarist could pick up
and play and that visibly corresponds to the performance in the video.

## Positioning

The differentiator is combining two signals from the same video: audio pitch
detection (which notes and when) and computer-vision hand / fretboard tracking
(where on the neck those notes were actually played). Pitch detection alone
leaves fret-vs-string ambiguity that has to be guessed; using the player's hands
to disambiguate position is the mechanism a purely audio-based transcriber could
not copy.

## Operating Context

- The user records or obtains a video of a guitar being played, uploads it, waits
  while it processes, and then reads or exports the resulting tab.
- Processing is asynchronous: the client uploads, then polls job status, then
  fetches the finished tab.
- Standard six-string guitar in standard tuning (E2 A2 D3 G3 B3 E4), frets 0–24.
- Tab is represented as an ordered list of fretboard positions, each with a
  string (1 = high E, 6 = low E), a fret (0 = open), and a timestamp in seconds.

## Capabilities and Constraints

Confirmed / working today:

- FastAPI backend pipeline: `video → ffmpeg → mono 22.05 kHz wav → basic-pitch
  note detection → notes mapped to the most playable fretboard positions`.
- Endpoints: `POST /upload` (returns a job id), `GET /status/{job_id}`,
  `GET /result/{job_id}`, `GET /health`.
- Job state is an in-memory dict in a single process — acceptable for a
  single-user demo, not for production or concurrent use.
- Frontend is a Next.js app (Next 16.2.6 / React 19). This is a fork with
  breaking changes from mainstream Next.js — consult `frontend/node_modules/next/dist/docs/`
  and heed deprecation notices before writing frontend code.
- Requires `ffmpeg` on `PATH`.

Planned / not yet built:

- Hand / fretboard computer-vision tracking to disambiguate note positions. This
  is committed to the product's positioning but is not implemented in the
  backend yet.

Undecided:

- Whether tuning other than standard is ever supported.
- Whether generated tabs are persisted or exportable to a file format, and which.
- Whether processed jobs survive a server restart.

## Brand Commitments

- Name: "Guitar Tablature Generator" (working title; the repo is
  `guitar-tabs-generator`).
- No logo, wordmark, established voice, or color/type commitments exist yet.
- Maintainer / attribution: Bertie Simmons.

## Evidence on Hand

- A working backend pipeline with a test suite (`backend/tests/`) including a
  sample video fixture.
- No testimonials, user counts, benchmarks, press, case studies, or accuracy
  metrics exist. Future work must not fabricate transcription-accuracy numbers,
  user quotes, or adoption claims.

## Product Principles

1. **Playability over literal accuracy.** A tab a guitarist can actually play in
   one position beats a technically-correct transcription scattered across the
   neck.
2. **The video is the source of truth.** Both audio and the player's hands are
   evidence; the output should be defensible against what the video shows.
3. **Respect the waiting.** Transcription is not instant; the experience must
   make asynchronous processing feel intentional and trustworthy, not broken.
4. **Built to be shown.** As a portfolio piece, every surface should read as
   finished and considered, even though it is a single-user demo.
5. **Honest about limits.** Where detection is uncertain or a feature is not yet
   built, say so rather than implying more than the pipeline delivers.
