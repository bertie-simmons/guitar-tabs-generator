# Backend

Turns an uploaded guitar video into tablature.

```
video => ffmpeg => mono 22.05 kHz wav => basic-pitch => notes => (string, fret) positions
        extract_audio            detect_notes                notes_to_tab
```

## Layout

The code is the `gtab` package: an **API** and a **worker** that talk only
through a shared job store and queue. They are separate processes (and will be
separate container images) - the API never imports the pipeline.

| module               | responsibility                                                        |
| -------------------- | -------------------------------------------------------------------- |
| `gtab.api.main`      | HTTP endpoints; stores the upload, records the job, enqueues its id   |
| `gtab.worker.runner` | `process_job` (one job), `handle_claimed` (ack/release), `run` (loop) |
| `gtab.worker.__main__` | `python -m gtab.worker` - runs `run`                                |
| `gtab.pipeline`      | pure transforms: `extract_audio`, `detect_notes`, `notes_to_tab`      |
| `gtab.jobs`          | `JobStore` + `JobQueue` - the seam; `memory` and `file` backends      |
| `gtab.uploads`       | `UploadStore` - where uploads wait for the worker; `local` backend     |
| `gtab.azure_storage` | the `azure` backends: Table job store, Queue job queue, Blob uploads  |
| `gtab.models`        | pydantic models: `Note`, `TabPosition`, `Tab`, `Job`                  |
| `gtab.config`        | env-overridable paths, backend selection, CORS origins               |
| `main.py`            | thin shim so `uvicorn main:app` still resolves to the API app         |

Flow: `POST /upload` `put`s the video in the upload store, `job_store.create(...)`
a `pending` job whose `source_path` is the upload's name, `job_queue.enqueue(job_id)`,
and returns. A worker `claim`s the id, downloads the upload into a temp dir, runs
the pipeline, and `save`s `done` + the tab or `failed` + an error. The client
polls `/status` then fetches `/result`.

A queue entry is only `ack`ed once the job is finished - `done`, or `failed` on
input that can never work (no audio track, upload missing). An unexpected error
`release`s it back onto the queue for another go, up to `GTAB_MAX_ATTEMPTS` starts
(counted in `Job.attempts`, so a worker that dies mid-job counts too). The
upload is deleted only when the job is finished, since a retry needs it.

### Job store / queue backends

| backend  | store              | queue                          | use                                             |
| -------- | ------------------ | ------------------------------ | ---------------------------------------------- |
| `memory` | dict               | `queue.Queue`                  | tests; API + worker in one process             |
| `file`   | JSON under `STATE_DIR` | directory queue under `STATE_DIR` | **default** - API and worker as two processes on one machine |
| `azure`  | Table Storage      | Queue Storage                  | separate containers; Azurite locally, a storage account in Azure |

`memory` and `file` keep uploads in `GTAB_UPLOAD_DIR`, so the API and worker
must share it. `azure` keeps them in Blob Storage.

Notes on the `azure` backend (`gtab.azure_storage`):

- **Auth**: a connection string (Azurite) or a storage account name, in which
  case it signs in with `DefaultAzureCredential` - a managed identity in
  Container Apps (set `AZURE_CLIENT_ID` for a user-assigned one), `az login` on
  your machine. The identity needs Storage Blob / Queue / Table *Data
  Contributor* on the account.
- **Queue visibility timeout**: a claimed message is hidden, not removed, for
  `GTAB_AZURE_QUEUE_VISIBILITY_TIMEOUT` seconds. It must outlast the slowest
  job, or another worker picks the job up mid-run. A worker that dies leaves its
  message to reappear after that long.
- **Table size**: the job JSON is split over `data_0`, `data_1`, ... properties;
  an entity is capped at 1 MiB, which is tens of thousands of tab positions.
- The container, table and queue are created on first use if missing.

## API

| method | path               | purpose                                                            |
| ------ | ------------------ | ---------------------------------------------------------------- |
| GET    | `/health`          | liveness check                                                     |
| POST   | `/upload`          | multipart file upload, returns `{ "job_id": ... }`                 |
| GET    | `/status/{job_id}` | `{ status, error }`, status is pending / processing / done / failed |
| GET    | `/result/{job_id}` | the `Tab` (409 until the job is `done`)                            |

## Configuration

| env var             | default                 | purpose                                        |
| ------------------- | ----------------------- | -------------------------------------------- |
| `GTAB_JOBS_BACKEND` | `file`                  | `file`, `memory` or `azure` (see above); anything else fails at startup |
| `GTAB_STATE_DIR`    | `.gtab-state`            | where the `file` backend keeps store + queue   |
| `GTAB_UPLOAD_DIR`   | `uploads`               | where the `local` upload store keeps videos    |
| `GTAB_MAX_ATTEMPTS` | `3`                     | worker starts per job before it is `failed`    |
| `GTAB_CORS_ORIGINS` | `http://localhost:3000` | comma-separated allowed browser origins         |
| `GTAB_AZURE_STORAGE_CONNECTION_STRING` | -   | `azure`: connection string (Azurite)           |
| `GTAB_AZURE_STORAGE_ACCOUNT` | -             | `azure`: account name, with managed identity   |
| `GTAB_AZURE_UPLOAD_CONTAINER` | `uploads`    | `azure`: blob container for uploads            |
| `GTAB_AZURE_JOB_TABLE` | `jobs`              | `azure`: table for the job store               |
| `GTAB_AZURE_JOB_QUEUE` | `jobs`              | `azure`: queue of job ids                      |
| `GTAB_AZURE_QUEUE_VISIBILITY_TIMEOUT` | `900` | `azure`: seconds a claimed job stays hidden   |

## Running

Requires [ffmpeg](https://ffmpeg.org/) on `PATH` (worker only). Run from `backend/`.

```bash
python -m venv .venv && . .venv/Scripts/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt                  # or -api.txt / -worker.txt per process

# two terminals, sharing .gtab-state/
uvicorn gtab.api.main:app --reload                   # terminal 1  (or: uvicorn main:app)
python -m gtab.worker                                # terminal 2
```

Open http://localhost:8000/docs to try it.

### With Docker (Azure-shaped)

From the repo root, `docker compose up --build` runs Azurite, the API, the
worker and the frontend on the `azure` backend. Open http://localhost:3000.

### Requirements files

| file                     | contents                                        |
| ------------------------ | --------------------------------------------- |
| `requirements-base.txt`  | pydantic, Azure Storage + identity SDKs (shared) |
| `requirements-api.txt`   | base + fastapi, uvicorn, python-multipart        |
| `requirements-worker.txt`| base + basic-pitch, tensorflow, librosa, ...     |
| `requirements-dev.txt`   | api + worker + pytest, httpx                     |

## Tests

```bash
pytest -m "not slow"   # fast unit + route tests
pytest                 # also runs the basic-pitch model test
```

The `azure` backend runs the same contract tests as the others against Azurite
on `127.0.0.1:10000-10002` (`docker compose up azurite`), and skips them if it
isn't running. Point `GTAB_TEST_AZURITE_CONNECTION_STRING` elsewhere if needed.
