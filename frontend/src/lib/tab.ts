// Render detected fretboard positions into a plain-text tab block.
//
// The backend gives us { string (1 = high E .. 6 = low E), fret, time }. There
// is no rhythm or bar information, so horizontal position is proportional to
// time, wrapped into stacked systems of a fixed character width. Every string
// line stays column-aligned even when fret numbers are two digits.

import type { TabPosition } from "./api";

/** Playable character columns per system (excludes the `e|` prefix and trailing `|`). */
export const PLAYABLE = 72;
/** Width of the `e|` prefix on every line. */
export const LEAD = 2;

/** String label by string number, index 0 = string 1 (high E), drawn top line. */
const STRING_LABELS = ["e", "B", "G", "D", "A", "E"];

export interface PlacedNote {
  string: number; // 1..6
  fret: number;
  time: number;
  system: number;
  col: number; // starting playable column, 0..PLAYABLE-1
  len: number; // characters the fret number occupies
}

export interface TabSystem {
  /** Six lines, string 1 (high e) first. Includes prefix and trailing bar. */
  lines: string[];
  /** Seconds represented by this system's first and last playable column. */
  startTime: number;
  endTime: number;
  notes: PlacedNote[];
}

export interface RenderedTab {
  systems: TabSystem[];
  /** The whole block as copyable text. */
  text: string;
  secondsPerSystem: number;
  duration: number;
  noteCount: number;
}

function clamp(n: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, n));
}

export function renderTab(
  positions: TabPosition[],
  durationHint = 0,
): RenderedTab {
  const valid = positions
    .filter(
      (p) =>
        Number.isFinite(p.time) &&
        p.time >= 0 &&
        p.string >= 1 &&
        p.string <= 6 &&
        p.fret >= 0,
    )
    .sort((a, b) => a.time - b.time || a.string - b.string);

  const lastNoteTime = valid.length ? valid[valid.length - 1].time : 0;
  const duration = Math.max(durationHint, lastNoteTime + 1, 4);

  const systemsWanted = clamp(Math.round(duration / 8), 1, 60);
  const secondsPerSystem = duration / systemsWanted;

  // Per system: six rows of playable cells, plus the rightmost column filled
  // on each string line.
  const grids: string[][][] = Array.from({ length: systemsWanted }, () =>
    Array.from({ length: 6 }, () => Array<string>(PLAYABLE).fill("-")),
  );
  const placed: PlacedNote[][] = Array.from({ length: systemsWanted }, () => []);

  for (const p of valid) {
    const system = clamp(
      Math.floor(p.time / secondsPerSystem),
      0,
      systemsWanted - 1,
    );
    const localT = p.time - system * secondsPerSystem;
    let col = clamp(
      Math.round((localT / secondsPerSystem) * (PLAYABLE - 1)),
      0,
      PLAYABLE - 1,
    );
    const token = String(p.fret);
    const len = token.length;
    const row = grids[system][p.string - 1];

    // Shift right only if this exact string line already has ink in the span
    // (chords on other strings share the column and must stay aligned).
    let guard = 0;
    while (guard++ < PLAYABLE) {
      let free = col + len <= PLAYABLE;
      for (let i = 0; free && i < len; i++) {
        if (row[col + i] !== "-") free = false;
      }
      // keep one dash of separation from a prior token on this line
      if (free && col > 0 && row[col - 1] !== "-") free = false;
      if (free) break;
      col += 1;
      if (col + len > PLAYABLE) {
        col = PLAYABLE - len;
        break;
      }
    }

    for (let i = 0; i < len; i++) row[col + i] = token[i];
    placed[system].push({
      string: p.string,
      fret: p.fret,
      time: p.time,
      system,
      col,
      len,
    });
  }

  const systems: TabSystem[] = grids.map((grid, s) => ({
    lines: grid.map(
      (row, i) => `${STRING_LABELS[i]}|${row.join("")}|`,
    ),
    startTime: s * secondsPerSystem,
    endTime: (s + 1) * secondsPerSystem,
    notes: placed[s].sort((a, b) => a.time - b.time),
  }));

  const text = systems
    .map((sys) => sys.lines.join("\n"))
    .join("\n\n");

  return {
    systems,
    text,
    secondsPerSystem,
    duration,
    noteCount: valid.length,
  };
}

export interface PlayheadLocation {
  system: number;
  /** Fractional playable column, 0..PLAYABLE-1. */
  col: number;
}

export function timeToLocation(
  t: number,
  rendered: RenderedTab,
): PlayheadLocation {
  const { secondsPerSystem, systems } = rendered;
  const system = clamp(
    Math.floor(t / secondsPerSystem),
    0,
    systems.length - 1,
  );
  const localT = t - system * secondsPerSystem;
  const col = clamp(
    (localT / secondsPerSystem) * (PLAYABLE - 1),
    0,
    PLAYABLE - 1,
  );
  return { system, col };
}

export function locationToTime(
  system: number,
  col: number,
  rendered: RenderedTab,
): number {
  const { secondsPerSystem } = rendered;
  const frac = clamp(col, 0, PLAYABLE - 1) / (PLAYABLE - 1);
  return clamp(
    system * secondsPerSystem + frac * secondsPerSystem,
    0,
    rendered.duration,
  );
}

/** How long a note is treated as still ringing under the hand, in seconds. */
const RING_WINDOW = 2.4;
/** Notes within this gap of each other count as one struck-together voicing. */
const CHORD_GAP = 0.14;

export interface ChordShape {
  /** Fret per string, index 0 = string 1 (high e) .. 5 = string 6 (low E). null = not sounding. */
  frets: (number | null)[];
  /** Strings struck within CHORD_GAP of the latest onset — the ones "just played". */
  struck: boolean[];
  /** Lowest fretted position (>0) in the shape; 0 when the shape is open or empty. */
  baseFret: number;
  /** How many strings are sounding. */
  count: number;
  /** True once two or more strings were struck together — a real chord, not a single note. */
  isChord: boolean;
}

const EMPTY_SHAPE: ChordShape = {
  frets: [null, null, null, null, null, null],
  struck: [false, false, false, false, false, false],
  baseFret: 0,
  count: 0,
  isChord: false,
};

/**
 * The fretting-hand shape at time `t`: the most recent note on each string that
 * is still ringing. When several strings were struck together (within
 * CHORD_GAP) it reads as a chord; a lone note reads as a single marked fret.
 */
export function chordAt(positions: TabPosition[], t: number): ChordShape {
  const latest = new Map<number, TabPosition>();
  for (const p of positions) {
    if (p.string < 1 || p.string > 6 || p.fret < 0) continue;
    const dt = t - p.time;
    if (dt < -0.06 || dt > RING_WINDOW) continue;
    const current = latest.get(p.string);
    if (!current || p.time > current.time) latest.set(p.string, p);
  }
  if (latest.size === 0) return EMPTY_SHAPE;

  const voices = [...latest.values()];
  const lastOnset = Math.max(...voices.map((v) => v.time));

  const frets: (number | null)[] = [null, null, null, null, null, null];
  const struck: boolean[] = [false, false, false, false, false, false];
  const fretted: number[] = [];
  for (const v of voices) {
    const i = v.string - 1;
    frets[i] = v.fret;
    struck[i] = lastOnset - v.time <= CHORD_GAP;
    if (v.fret > 0) fretted.push(v.fret);
  }

  return {
    frets,
    struck,
    baseFret: fretted.length ? Math.min(...fretted) : 0,
    count: voices.length,
    isChord: struck.filter(Boolean).length >= 2,
  };
}
