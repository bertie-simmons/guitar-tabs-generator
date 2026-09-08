// Client for the FastAPI transcription backend.
//
// Pipeline: POST /upload -> { job_id }; poll GET /status/{job_id} until the
// status leaves pending/processing; then GET /result/{job_id} for the Tab.

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || "http://localhost:8000";

export type JobStatus = "pending" | "processing" | "done" | "failed";

/** One detected note placed on the fretboard. `string` 1 = high E, 6 = low E. */
export interface TabPosition {
  string: number;
  fret: number;
  time: number;
}

export interface Tab {
  positions: TabPosition[];
}

export interface StatusResponse {
  job_id: string;
  status: JobStatus;
  error: string | null;
}

/** Suffixes the backend accepts (see ALLOWED_SUFFIXES in main.py). */
export const ACCEPTED_SUFFIXES = [
  ".mp4",
  ".mov",
  ".webm",
  ".mkv",
  ".avi",
  ".m4v",
  ".wav",
  ".mp3",
] as const;

export const ACCEPT_ATTR = ACCEPTED_SUFFIXES.join(",");

export class ApiError extends Error {
  constructor(
    message: string,
    readonly kind: "network" | "rejected" | "server" = "server",
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function hasAcceptedSuffix(name: string): boolean {
  const lower = name.toLowerCase();
  return ACCEPTED_SUFFIXES.some((s) => lower.endsWith(s));
}

async function readDetail(res: Response): Promise<string | null> {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    /* not JSON */
  }
  return null;
}

export async function uploadVideo(
  file: File,
  signal?: AbortSignal,
): Promise<string> {
  const form = new FormData();
  form.append("file", file);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}/upload`, {
      method: "POST",
      body: form,
      signal,
    });
  } catch (err) {
    if ((err as Error).name === "AbortError") throw err;
    throw new ApiError(
      `Can't reach the transcription service at ${API_BASE}.`,
      "network",
    );
  }

  if (!res.ok) {
    const detail = await readDetail(res);
    if (res.status === 400) {
      throw new ApiError(
        detail ?? "That file type isn't supported.",
        "rejected",
      );
    }
    throw new ApiError(detail ?? `Upload failed (${res.status}).`, "server");
  }

  const body = (await res.json()) as { job_id: string };
  return body.job_id;
}

export async function getStatus(
  jobId: string,
  signal?: AbortSignal,
): Promise<StatusResponse> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/status/${jobId}`, { signal });
  } catch (err) {
    if ((err as Error).name === "AbortError") throw err;
    throw new ApiError("Lost contact with the transcription service.", "network");
  }
  if (!res.ok) {
    const detail = await readDetail(res);
    throw new ApiError(detail ?? `Status check failed (${res.status}).`, "server");
  }
  return (await res.json()) as StatusResponse;
}

export async function getResult(
  jobId: string,
  signal?: AbortSignal,
): Promise<Tab> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/result/${jobId}`, { signal });
  } catch (err) {
    if ((err as Error).name === "AbortError") throw err;
    throw new ApiError("Lost contact with the transcription service.", "network");
  }
  if (!res.ok) {
    const detail = await readDetail(res);
    throw new ApiError(detail ?? `Couldn't fetch the tab (${res.status}).`, "server");
  }
  return (await res.json()) as Tab;
}

const POLL_INTERVAL_MS = 1200;

/**
 * Poll `/status` until the job finishes. Calls `onTick` with each status so the
 * UI can show progress. Resolves with the final status; never throws for a
 * `failed` job (the caller reads `.error`).
 */
export async function pollUntilSettled(
  jobId: string,
  onTick: (status: StatusResponse) => void,
  signal?: AbortSignal,
): Promise<StatusResponse> {
  for (;;) {
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
    const status = await getStatus(jobId, signal);
    onTick(status);
    if (status.status === "done" || status.status === "failed") return status;
    await new Promise<void>((resolve, reject) => {
      const t = setTimeout(resolve, POLL_INTERVAL_MS);
      signal?.addEventListener(
        "abort",
        () => {
          clearTimeout(t);
          reject(new DOMException("Aborted", "AbortError"));
        },
        { once: true },
      );
    });
  }
}
