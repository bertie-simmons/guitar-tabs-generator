"use client";

import { Fragment, useEffect, useMemo, useRef, type ReactNode } from "react";
import {
  LEAD,
  PLAYABLE,
  timeToLocation,
  locationToTime,
  type PlacedNote,
  type RenderedTab,
} from "@/src/lib/tab";
import styles from "../editor.module.css";

interface Props {
  tab: RenderedTab;
  time: number;
  onSeek: (t: number) => void;
}

/** A note counts as sounding "now" within this many seconds of the playhead. */
const NOW_WINDOW = 0.16;

function fmt(t: number): string {
  const m = Math.floor(t / 60);
  const s = Math.floor(t % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

/**
 * Rebuild one string line from its raw text plus the notes on that string, so
 * fret digits read brighter than the staff and the note(s) under the playhead
 * invert to the accent. The structure (dashes, bars, label) stays recessed.
 */
function buildLine(line: string, notes: PlacedNote[], time: number): ReactNode {
  const label = line.slice(0, LEAD); // "e|"
  const body = line.slice(LEAD, LEAD + PLAYABLE);
  const close = line.slice(LEAD + PLAYABLE); // "|"

  const ordered = [...notes].sort((a, b) => a.col - b.col);
  const out: ReactNode[] = [];
  let cursor = 0;

  ordered.forEach((n, i) => {
    const start = Math.max(n.col, cursor);
    const end = Math.min(n.col + n.len, PLAYABLE);
    if (end <= start) return;
    if (start > cursor) {
      out.push(<Fragment key={`g${i}`}>{body.slice(cursor, start)}</Fragment>);
    }
    const active = Math.abs(n.time - time) < NOW_WINDOW;
    out.push(
      <span key={`n${i}`} className={active ? styles.now : styles.fig}>
        {body.slice(start, end)}
      </span>,
    );
    cursor = end;
  });
  if (cursor < PLAYABLE) {
    out.push(<Fragment key="tail">{body.slice(cursor)}</Fragment>);
  }

  return (
    <>
      <span className={styles.lbl}>{label}</span>
      {out}
      <span className={styles.lbl}>{close}</span>
    </>
  );
}

function notesByString(notes: PlacedNote[]): PlacedNote[][] {
  const rows: PlacedNote[][] = [[], [], [], [], [], []];
  for (const n of notes) {
    if (n.string >= 1 && n.string <= 6) rows[n.string - 1].push(n);
  }
  return rows;
}

export default function TabView({ tab, time, onSeek }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const activeSystemRef = useRef<HTMLDivElement>(null);

  const loc = useMemo(() => timeToLocation(time, tab), [time, tab]);

  // Only changes when the playhead crosses into a new system, so the live
  // region announces once per line rather than every frame.
  const announce = useMemo(() => {
    const sys = tab.systems[loc.system];
    return sys ? `Line ${loc.system + 1}, ${fmt(sys.startTime)}` : "";
  }, [loc.system, tab]);

  // keep the active system in view as playback advances
  useEffect(() => {
    const el = activeSystemRef.current;
    const scroll = scrollRef.current;
    if (!el || !scroll) return;
    const elTop = el.offsetTop;
    const elBottom = elTop + el.offsetHeight;
    if (
      elTop < scroll.scrollTop ||
      elBottom > scroll.scrollTop + scroll.clientHeight
    ) {
      scroll.scrollTo({ top: Math.max(0, elTop - 24), behavior: "smooth" });
    }
  }, [loc.system]);

  const isEmpty = tab.noteCount === 0;

  function seekFromEvent(
    e: React.MouseEvent<HTMLDivElement>,
    systemIndex: number,
  ) {
    const firstLine = e.currentTarget.querySelector<HTMLElement>(
      `.${styles.systemLine}`,
    );
    if (!firstLine) return;
    const rect = firstLine.getBoundingClientRect();
    const charWidth = rect.width / (PLAYABLE + LEAD + 1);
    const col = (e.clientX - rect.left) / charWidth - LEAD;
    onSeek(locationToTime(systemIndex, col, tab));
  }

  return (
    <div className={styles.tabScroll} ref={scrollRef}>
      <p className={styles.srOnly} aria-live="polite">
        {announce}
      </p>
      <div className={styles.tabInner}>
        {tab.systems.map((sys, si) => {
          const activeHere = si === loc.system;
          const rows = notesByString(sys.notes);
          return (
            <div
              key={si}
              ref={activeHere ? activeSystemRef : undefined}
              className={styles.system}
              onClick={(e) => seekFromEvent(e, si)}
              role="button"
              tabIndex={0}
              aria-label={`Tab line ${si + 1}, ${fmt(sys.startTime)} to ${fmt(
                sys.endTime,
              )}. Click to seek the video.`}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSeek(sys.startTime);
                }
              }}
            >
              <span className={styles.systemTime}>{fmt(sys.startTime)}</span>

              {activeHere && (
                <span
                  className={styles.playhead}
                  style={{ left: `${LEAD + loc.col}ch` }}
                  aria-hidden
                />
              )}

              {sys.lines.map((line, li) => (
                <span key={li} className={styles.systemLine}>
                  {buildLine(line, rows[li], time)}
                </span>
              ))}
            </div>
          );
        })}

        {isEmpty && (
          <p className={styles.emptyNote}>
            No notes detected. The clip may be silent, very quiet, or too short
            for the detector to lock on. Try a section with clear playing.
          </p>
        )}
      </div>
    </div>
  );
}
