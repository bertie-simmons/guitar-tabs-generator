"use client";

import type { ChordShape } from "@/src/lib/tab";
import styles from "../editor.module.css";

interface Props {
  shape: ChordShape | null;
  /** Current playback time, for the caption. */
  time: number;
  active: boolean;
}

const STRINGS = 6; // columns, left = low E (string 6), right = high e (string 1)
const FRET_ROWS = 4;

const VIEW_W = 108;
const VIEW_H = 132;
const COL_X = [14, 30, 46, 62, 78, 94]; // low E .. high e
const NUT_Y = 24;
const ROW_H = 24;

function fmtClock(t: number): string {
  const m = Math.floor(t / 60);
  const s = Math.floor(t % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

/** Left-to-right: string 6 (low E) first, so index maps to frets[5..0]. */
function voicingText(shape: ChordShape): string {
  return [5, 4, 3, 2, 1, 0]
    .map((i) => {
      const f = shape.frets[i];
      return f === null ? "x" : String(f);
    })
    .join(" ");
}

export default function FretboardStrip({ shape, time, active }: Props) {
  const live = active && shape !== null && shape.count > 0;
  const startFret = live && shape.baseFret > 3 ? shape.baseFret : 1;
  const showNut = startFret === 1;

  const fretLineYs = Array.from({ length: FRET_ROWS + 1 }, (_, r) => NUT_Y + r * ROW_H);

  const label = live
    ? shape.isChord
      ? `${shape.count} notes struck together`
      : shape.count === 1
        ? "one note"
        : `${shape.count} notes ringing`
    : "waiting for playback";

  return (
    <div className={styles.chordBox}>
      <svg
        className={styles.chordDiagram}
        width={VIEW_W}
        height={VIEW_H}
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        role="img"
        aria-label={
          live
            ? `Chord shape ${voicingText(shape)}, ${label}`
            : "Chord shape, nothing sounding"
        }
      >
        {/* base-fret marker when the shape sits up the neck */}
        {!showNut && (
          <text
            x={COL_X[0] - 8}
            y={NUT_Y + ROW_H / 2 + 3}
            textAnchor="end"
            fontSize="8.5"
            fontFamily="var(--font-tab)"
            fill="var(--ink-3)"
          >
            {startFret}fr
          </text>
        )}

        {/* nut / top fret */}
        <line
          x1={COL_X[0]}
          y1={NUT_Y}
          x2={COL_X[STRINGS - 1]}
          y2={NUT_Y}
          stroke={showNut ? "var(--ink)" : "var(--rule-2)"}
          strokeWidth={showNut ? 3 : 1}
        />

        {/* frets */}
        {fretLineYs.slice(1).map((y) => (
          <line
            key={y}
            x1={COL_X[0]}
            y1={y}
            x2={COL_X[STRINGS - 1]}
            y2={y}
            stroke="var(--rule-2)"
            strokeWidth={1}
          />
        ))}

        {/* strings */}
        {COL_X.map((x, i) => (
          <line
            key={x}
            x1={x}
            y1={NUT_Y}
            x2={x}
            y2={fretLineYs[FRET_ROWS]}
            stroke="var(--ink-3)"
            strokeWidth={0.6 + (STRINGS - 1 - i) * 0.18}
          />
        ))}

        {/* markers per string */}
        {COL_X.map((x, col) => {
          const stringIndex = STRINGS - 1 - col; // frets[] index: 5..0
          const fret = live ? shape.frets[stringIndex] : null;

          if (fret === null) {
            return (
              <text
                key={`m${col}`}
                x={x}
                y={NUT_Y - 7}
                textAnchor="middle"
                fontSize="9"
                fontFamily="var(--font-tab)"
                fill="var(--ink-3)"
              >
                ×
              </text>
            );
          }
          if (fret === 0) {
            return (
              <circle
                key={`m${col}`}
                cx={x}
                cy={NUT_Y - 10}
                r={3.4}
                fill="none"
                stroke="var(--ink-2)"
                strokeWidth={1.3}
              />
            );
          }
          const row = fret - startFret;
          const cy = NUT_Y + (row + 0.5) * ROW_H;
          return (
            <g key={`m${col}`}>
              <circle cx={x} cy={cy} r={6.5} fill="var(--route)" />
              <text
                x={x}
                y={cy + 3}
                textAnchor="middle"
                fontSize="8"
                fontWeight="600"
                fontFamily="var(--font-tab)"
                fill="var(--route-ink)"
              >
                {fret}
              </text>
            </g>
          );
        })}
      </svg>

      <div className={styles.chordMeta}>
        <span className={styles.chordMetaK}>
          Chord shape{live ? ` · ${fmtClock(time)}` : ""}
        </span>
        <span className={styles.chordMetaV}>
          {live ? voicingText(shape) : "— — — — — —"}
        </span>
        <span className={styles.chordMetaN}>{label}</span>
      </div>
    </div>
  );
}
