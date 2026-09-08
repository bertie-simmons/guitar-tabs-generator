// Development-only synthetic data, so every phase of the flow can be built and
// inspected without running the Python pipeline. Never reachable in a
// production build — Transcriber only wires the `?state=` shortcut when
// process.env.NODE_ENV !== "production".

import type { TabPosition } from "./api";

// A short riff: open-position Am pentatonic-ish phrase, ~14s, standard tuning.
// string 1 = high E ... 6 = low E.
const RIFF: Array<[number, number, number]> = [
  // time, string, fret
  [0.0, 5, 0],
  [0.0, 3, 2],
  [0.45, 4, 2],
  [0.9, 3, 2],
  [1.35, 2, 1],
  [1.8, 1, 0],
  [2.25, 1, 3],
  [2.7, 2, 1],
  [3.15, 3, 2],
  [3.6, 4, 2],
  [4.2, 5, 0],
  [4.2, 4, 2],
  [4.2, 3, 2],
  [5.1, 6, 3],
  [5.6, 5, 5],
  [6.1, 4, 5],
  [6.6, 4, 7],
  [7.1, 3, 5],
  [7.6, 2, 5],
  [8.1, 1, 5],
  [8.6, 1, 8],
  [9.1, 1, 5],
  [9.6, 2, 5],
  [10.1, 3, 7],
  [10.1, 4, 7],
  [11.0, 5, 7],
  [11.0, 6, 5],
  [12.0, 5, 3],
  [12.6, 5, 0],
  [12.6, 4, 2],
  [12.6, 3, 2],
  [12.6, 2, 3],
  [12.6, 1, 0],
];

export const MOCK_TAB: TabPosition[] = RIFF.map(([time, string, fret]) => ({
  time,
  string,
  fret,
}));

export const MOCK_TAB_EMPTY: TabPosition[] = [];
