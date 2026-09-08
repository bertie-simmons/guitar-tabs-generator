"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  ACCEPT_ATTR,
  ApiError,
  hasAcceptedSuffix,
  pollUntilSettled,
  uploadVideo,
  getResult,
  type TabPosition,
} from "@/src/lib/api";
import { renderTab, chordAt, type RenderedTab } from "@/src/lib/tab";
import { MOCK_TAB, MOCK_TAB_EMPTY } from "@/src/lib/mockTab";
import TabView from "./components/TabView";
import FretboardStrip from "./components/FretboardStrip";
import styles from "./editor.module.css";

type Phase = "idle" | "uploading" | "processing" | "done" | "failed";

const PIPELINE_STAGES = [
  "Extracting audio",
  "Detecting notes",
  "Mapping the fretboard",
];

const GHOST_STAFF = ["e", "B", "G", "D", "A", "E"].map(
  (s) => `${s}|${"—".repeat(58)}|`,
);

function fmtClock(t: number): string {
  if (!Number.isFinite(t)) return "0:00";
  const m = Math.floor(t / 60);
  const s = Math.floor(t % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function errorHint(err: unknown): { message: string; hint: string } {
  if (err instanceof ApiError) {
    if (err.kind === "network")
      return {
        message: err.message,
        hint: "Start the backend (uvicorn main:app) and check NEXT_PUBLIC_API_BASE, then try again.",
      };
    if (err.kind === "rejected")
      return {
        message: err.message,
        hint: "Upload a video or audio file: mp4, mov, webm, mkv, avi, m4v, wav, or mp3.",
      };
    return {
      message: err.message,
      hint: "This one is on the pipeline. Try a shorter clip or a different file.",
    };
  }
  return {
    message: "Something went wrong during transcription.",
    hint: "Try another file.",
  };
}

const isDev = process.env.NODE_ENV !== "production";

export default function Transcriber() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [file, setFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [positions, setPositions] = useState<TabPosition[]>([]);
  const [videoDuration, setVideoDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [pollStatus, setPollStatus] = useState<"pending" | "processing">(
    "pending",
  );
  const [elapsed, setElapsed] = useState(0);
  const [stageIndex, setStageIndex] = useState(0);
  const [error, setError] = useState<{ message: string; hint: string } | null>(
    null,
  );
  const [dragging, setDragging] = useState(false);
  const [copied, setCopied] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const rafRef = useRef<number | null>(null);

  // --- dev-only: jump straight to a phase with synthetic data ---
  /* eslint-disable react-hooks/set-state-in-effect -- one-shot dev harness, never in production */
  useEffect(() => {
    if (!isDev) return;
    const state = new URLSearchParams(window.location.search).get("state");
    if (!state) return;
    if (state === "processing") {
      setFile(new File([], "am-riff-take-2.mp4"));
      setPhase("processing");
      setPollStatus("processing");
    } else if (state === "failed") {
      setFile(new File([], "practice-take.mp4"));
      setPhase("failed");
      setError({
        message: "ffmpeg produced an empty file — no audio track in the clip.",
        hint: "Upload a clip that actually contains sound.",
      });
    } else if (state === "empty") {
      setFile(new File([], "quiet-room.mp4"));
      setPositions(MOCK_TAB_EMPTY);
      setVideoDuration(12);
      setPhase("done");
    } else if (state === "done") {
      setFile(new File([], "am-riff-take-2.mp4"));
      setPositions(MOCK_TAB);
      setVideoDuration(14);
      setPhase("done");
    }
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  const tab: RenderedTab | null = useMemo(() => {
    if (phase !== "done") return null;
    return renderTab(positions, videoDuration);
  }, [phase, positions, videoDuration]);

  const chord = useMemo(
    () => (phase === "done" ? chordAt(positions, currentTime) : null),
    [phase, positions, currentTime],
  );

  // elapsed + stage cycling during processing
  useEffect(() => {
    if (phase !== "processing" && phase !== "uploading") return;
    const start = Date.now();
    const id = window.setInterval(() => {
      const secs = (Date.now() - start) / 1000;
      setElapsed(secs);
      if (pollStatus === "processing") {
        setStageIndex(Math.min(2, Math.floor(secs / 4) % 3));
      }
    }, 250);
    return () => window.clearInterval(id);
  }, [phase, pollStatus]);

  // playhead follows the video
  useEffect(() => {
    if (!isPlaying) return;
    const tick = () => {
      const v = videoRef.current;
      if (v) setCurrentTime(v.currentTime);
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [isPlaying]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      if (videoUrl) URL.revokeObjectURL(videoUrl);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startTranscription = useCallback(async (picked: File) => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    setError(null);
    setPositions([]);
    setCurrentTime(0);
    setIsPlaying(false);
    setVideoDuration(0);
    setElapsed(0);
    setStageIndex(0);
    setFile(picked);
    setVideoUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return URL.createObjectURL(picked);
    });
    setPhase("uploading");

    try {
      const jobId = await uploadVideo(picked, ac.signal);
      setPhase("processing");
      setPollStatus("pending");
      const final = await pollUntilSettled(
        jobId,
        (s) => {
          if (s.status === "pending" || s.status === "processing")
            setPollStatus(s.status);
        },
        ac.signal,
      );
      if (final.status === "failed") {
        setError(
          errorHint(new ApiError(final.error ?? "Transcription failed.")),
        );
        setPhase("failed");
        return;
      }
      const result = await getResult(jobId, ac.signal);
      setPositions(result.positions ?? []);
      setPhase("done");
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setError(errorHint(err));
      setPhase("failed");
    }
  }, []);

  const onPick = useCallback(
    (f: File | null | undefined) => {
      if (!f) return;
      if (!hasAcceptedSuffix(f.name)) {
        setError({
          message: `"${f.name}" isn't a supported file type.`,
          hint: "Upload a video or audio file: mp4, mov, webm, mkv, avi, m4v, wav, or mp3.",
        });
        setPhase("failed");
        return;
      }
      void startTranscription(f);
    },
    [startTranscription],
  );

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setPhase("idle");
    setFile(null);
    setPositions([]);
    setError(null);
    setCurrentTime(0);
    setIsPlaying(false);
    setVideoUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return null;
    });
  }, []);

  const togglePlay = useCallback(() => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) {
      void v.play();
      setIsPlaying(true);
    } else {
      v.pause();
      setIsPlaying(false);
    }
  }, []);

  const seek = useCallback((t: number) => {
    const v = videoRef.current;
    if (v) {
      v.currentTime = t;
      setCurrentTime(t);
    } else {
      setCurrentTime(t);
    }
  }, []);

  const copyTab = useCallback(async () => {
    if (!tab) return;
    try {
      await navigator.clipboard.writeText(tab.text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard blocked; ignore */
    }
  }, [tab]);

  const busy = phase === "uploading" || phase === "processing";
  const headStats =
    phase === "done"
      ? `${positions.length} notes · ${fmtClock(videoDuration)} · E A D G B e`
      : "";

  return (
    <div
      className={`${styles.shell} ${dragging ? styles.dropArmed : ""}`}
      onDragOver={(e) => {
        if (phase === "idle" || phase === "failed") {
          e.preventDefault();
          setDragging(true);
        }
      }}
      onDragLeave={(e) => {
        if (e.currentTarget === e.target) setDragging(false);
      }}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        onPick(e.dataTransfer.files?.[0]);
      }}
    >
      <section className={styles.stage} aria-label="Tablature">
        {phase !== "idle" && (
          <div className={styles.stageHead}>
            <span className={styles.headKick}>
              Tab&nbsp;&nbsp;<b>{file?.name ?? "—"}</b>
            </span>
            <span className={styles.headRule} />
            {headStats && <span className={styles.headDim}>{headStats}</span>}
          </div>
        )}

        <div className={styles.stageBody}>
          {(phase === "idle" || phase === "uploading") && (
            <IdleView phase={phase} onBrowse={onPick} />
          )}

          {phase === "processing" && (
            <ProcessingView
              status={pollStatus}
              stageIndex={stageIndex}
              elapsed={elapsed}
            />
          )}

          {phase === "failed" && error && (
            <div className={styles.failure} role="alert">
              <p className={styles.failureTag}>Transcription stopped</p>
              <p className={styles.failureMsg}>{error.message}</p>
              <p className={styles.failureHint}>{error.hint}</p>
              <button
                className={styles.ghost}
                style={{ width: "auto", padding: "0 20px", marginTop: 8 }}
                onClick={reset}
              >
                Start over
              </button>
            </div>
          )}

          {phase === "done" && tab && (
            <TabView tab={tab} time={currentTime} onSeek={seek} />
          )}
        </div>
      </section>

      <aside className={styles.side} aria-label="Controls">
        <div className={styles.stamp}>
          <span className={styles.stampMark}>GTAB</span>
          <span className={styles.stampSub}>ASCII tab · read from video</span>
        </div>

        {phase === "done" ? (
          <>
            {videoUrl ? (
              <video
                ref={videoRef}
                className={styles.video}
                src={videoUrl}
                playsInline
                onLoadedMetadata={(e) =>
                  setVideoDuration(e.currentTarget.duration || 0)
                }
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                onTimeUpdate={(e) =>
                  !isPlaying && setCurrentTime(e.currentTarget.currentTime)
                }
                onEnded={() => setIsPlaying(false)}
              />
            ) : (
              <div className={styles.videoPlaceholder}>preview · dev mock</div>
            )}
            <div className={styles.transport}>
              <button
                className={styles.transportBtn}
                onClick={togglePlay}
                aria-label={isPlaying ? "Pause" : "Play"}
              >
                {isPlaying ? <PauseIcon /> : <PlayIcon />}
              </button>
              <div
                className={styles.scrub}
                role="slider"
                tabIndex={0}
                aria-label="Seek"
                aria-valuemin={0}
                aria-valuemax={Math.round(videoDuration)}
                aria-valuenow={Math.round(currentTime)}
                onClick={(e) => {
                  const r = e.currentTarget.getBoundingClientRect();
                  seek(((e.clientX - r.left) / r.width) * videoDuration);
                }}
                onKeyDown={(e) => {
                  if (e.key === "ArrowRight") seek(currentTime + 2);
                  if (e.key === "ArrowLeft") seek(Math.max(0, currentTime - 2));
                }}
              >
                <div
                  className={styles.scrubFill}
                  style={{
                    width: `${
                      videoDuration ? (currentTime / videoDuration) * 100 : 0
                    }%`,
                  }}
                />
              </div>
              <span className={styles.transportTime}>
                {fmtClock(currentTime)}
              </span>
            </div>
          </>
        ) : null}

        <dl className={styles.readouts}>
          <div className={styles.readout}>
            <dt>Specimen</dt>
            <dd title={file?.name}>{file ? file.name : "—"}</dd>
          </div>
          <div className={styles.readout}>
            <dt>Length</dt>
            <dd>{videoDuration ? fmtClock(videoDuration) : "—"}</dd>
          </div>
          <div className={styles.readout}>
            <dt>Notes</dt>
            <dd>{phase === "done" ? positions.length : "—"}</dd>
          </div>
          <div className={styles.readout}>
            <dt>Tuning</dt>
            <dd>E A D G B e</dd>
          </div>
        </dl>

        {phase === "done" && (
          <div className={styles.legend}>
            <p className={styles.legendHead}>Legend</p>
            <div className={styles.legendRow}>
              <span className={styles.glyph}>
                <span className={styles.glyphDot} />
              </span>
              note sounding now
            </div>
            <div className={styles.legendRow}>
              <span className={styles.glyph}>
                <span className={styles.glyphOpen} />
              </span>
              open string
            </div>
            <div className={styles.legendRow}>
              <span className={styles.glyph}>
                <span className={styles.glyphMute}>×</span>
              </span>
              muted / not played
            </div>
            <div className={styles.legendRow}>
              <span className={styles.glyph}>
                <span className={styles.glyphChord} />
              </span>
              chord — struck together
            </div>
          </div>
        )}

        <div className={styles.actions}>
          {phase === "done" ? (
            <>
              <button className={styles.primary} onClick={copyTab}>
                {copied ? "Copied" : "Copy tab"}
              </button>
              <button className={styles.ghost} onClick={reset}>
                New file
              </button>
            </>
          ) : (
            <>
              <label
                className={`${styles.primary} ${busy ? styles.primaryBusy : ""}`}
              >
                {busy
                  ? phase === "uploading"
                    ? "Uploading"
                    : "Transcribing"
                  : "Transcribe"}
                <input
                  type="file"
                  accept={ACCEPT_ATTR}
                  disabled={busy}
                  onChange={(e) => onPick(e.target.files?.[0])}
                />
              </label>
              <p className={styles.actionsHint}>
                {busy
                  ? "Processing runs on the server. Keep this tab open."
                  : "Drop a clip anywhere, or choose one here."}
              </p>
            </>
          )}
        </div>
      </aside>

      <footer className={styles.dock}>
        <FretboardStrip
          shape={chord}
          time={currentTime}
          active={phase === "done"}
        />
        <div className={styles.dockNote}>
          <p className={styles.dockNoteK}>Reading the diagram</p>
          <p>
            {phase === "done"
              ? "The diagram tracks the notes detected at the current instant — a full grid when several are struck together, a single marked fret otherwise. Each note is mapped to the most playable place on the neck; there is no chord-name guessing."
              : "Once a tab is read, this shows the notes ringing at each moment of the video — the ones struck together, drawn on the neck as a shape."}
          </p>
        </div>
      </footer>
    </div>
  );
}

function IdleView({
  phase,
  onBrowse,
}: {
  phase: Phase;
  onBrowse: (f: File | null | undefined) => void;
}) {
  return (
    <div className={styles.idle}>
      <pre className={styles.idleStaff} aria-hidden>
        {GHOST_STAFF.map((line, i) => (
          <span key={i}>
            <span className={styles.lbl}>{line.slice(0, 2)}</span>
            {line.slice(2)}
            {"\n"}
          </span>
        ))}
      </pre>
      <div className={styles.idlePrompt}>
        <p className={styles.idleHead}>
          {phase === "uploading"
            ? "Sending the clip to the transcription service"
            : "Drop a guitar video to read its tab"}
        </p>
        {phase !== "uploading" && (
          <>
            <p className={styles.idleFormats}>
              mp4 · mov · webm · mkv · wav · mp3
            </p>
            <label className={`${styles.ghost} ${styles.idleBrowse}`}>
              Choose a file
              <input
                type="file"
                accept={ACCEPT_ATTR}
                onChange={(e) => onBrowse(e.target.files?.[0])}
              />
            </label>
          </>
        )}
      </div>
    </div>
  );
}

function ProcessingView({
  status,
  stageIndex,
  elapsed,
}: {
  status: "pending" | "processing";
  stageIndex: number;
  elapsed: number;
}) {
  const ticks = useMemo(() => {
    const rows = [0, 1, 2, 3, 4, 5];
    const out: { left: string; top: string; delay: string }[] = [];
    let seed = 7;
    for (let i = 0; i < 22; i++) {
      seed = (seed * 1103515245 + 12345) & 0x7fffffff;
      const row = rows[i % 6];
      out.push({
        left: `calc(2ch + ${4 + (seed % 52)}ch)`,
        top: `calc(24px + ${row} * 1.9em + 0.85em)`,
        delay: `${((seed >> 5) % 20) * 0.13}s`,
      });
    }
    return out;
  }, []);

  return (
    <div className={styles.processing}>
      <p className={styles.processLabel} role="status">
        {status === "pending" ? (
          <span>In queue</span>
        ) : (
          <>
            <b>{PIPELINE_STAGES[stageIndex]}</b>
            <span className={styles.processElapsed}>
              {elapsed.toFixed(0)}s elapsed
            </span>
          </>
        )}
      </p>

      <div style={{ position: "relative" }}>
        <div className={styles.scanTrail} aria-hidden />
        <div className={styles.scan} aria-hidden />
        {status === "processing" &&
          ticks.map((t, i) => (
            <span
              key={i}
              className={styles.tick}
              style={{ left: t.left, top: t.top, animationDelay: t.delay }}
              aria-hidden
            />
          ))}
        <pre className={styles.ghostStaff} aria-hidden>
          {GHOST_STAFF.map((line, i) => (
            <span key={i}>
              <span className={styles.lbl}>{line.slice(0, 2)}</span>
              {line.slice(2)}
              {"\n"}
            </span>
          ))}
        </pre>
      </div>
    </div>
  );
}

function PlayIcon() {
  return (
    <svg width="11" height="13" viewBox="0 0 11 13" aria-hidden>
      <path d="M0 0v13l11-6.5z" fill="currentColor" />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg width="11" height="13" viewBox="0 0 11 13" aria-hidden>
      <path d="M0 0h4v13H0zM7 0h4v13H7z" fill="currentColor" />
    </svg>
  );
}
