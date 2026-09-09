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
| `gtab.api.main`      | HTTP endpoints; saves the upload, records the job, enqueues its id    |
| `gtab.worker.runner` | `process_job` (one job) and `run` (the claim loop)                    |
| `gtab.worker.__main__` | `python -m gtab.worker` - runs `run`                                |
| `gtab.pipeline`      | pure transforms: `extract_audio`, `detect_notes`, `notes_to_tab`      |
| `gtab.jobs`          | `JobStore` + `JobQueue` - the seam; `memory` and `file` backends      |
| `gtab.models`        | pydantic models: `Note`, `TabPosition`, `Tab`, `Job`                  |
| `gtab.config`        | env-overridable paths, backend selection, CORS origins               |
| `main.py`            | thin shim so `uvicorn main:app` still resolves to the API app         |

Flow: `POST /upload` writes the video, `job_store.create(...)` a `pending` job,
`job_queue.enqueue(job_id)`, and returns. A worker `claim`s the id, runs the
pipeline, and `save`s `done` + the tab or `failed` + an error. The client polls
`/status` then fetches `/result`.

### Job store / queue backends

| backend  | store              | queue                          | use                                             |
| -------- | ------------------ | ------------------------------ | ---------------------------------------------- |
| `memory` | dict               | `queue.Queue`                  | tests; API + worker in one process             |
| `file`   | JSON under `STATE_DIR` | directory queue under `STATE_DIR` | **default** - API and worker as two processes |

The `file` backend is the local stand-in for **Azure Table Storage** (the store)
and **Azure Queue Storage** (the queue). Going to Azure means adding
`AzureTableJobStore` / `AzureQueueJobQueue` classes and a `configure()` branch -
nothing in `gtab.api` or `gtab.worker` changes.

> Not yet cross-container: the upload is still a local file path in
> `Job.source_path`. Separate containers need it in blob storage (the API
> uploads, the worker downloads). That is the next step, with the Azure backends.

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
| `GTAB_JOBS_BACKEND` | `file`                  | `file` or `memory` (see above)                 |
| `GTAB_STATE_DIR`    | `.gtab-state`            | where the `file` backend keeps store + queue   |
| `GTAB_UPLOAD_DIR`   | `uploads`               | where uploaded videos are written              |
| `GTAB_AUDIO_DIR`    | `audio_cache`           | where extracted WAV audio is written           |
| `GTAB_CORS_ORIGINS` | `http://localhost:3000` | comma-separated allowed browser origins         |

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

### Requirements files

| file                     | contents                                        |
| ------------------------ | --------------------------------------------- |
| `requirements-base.txt`  | pydantic (shared)                               |
| `requirements-api.txt`   | base + fastapi, uvicorn, python-multipart        |
| `requirements-worker.txt`| base + basic-pitch, tensorflow, librosa, ...     |
| `requirements-dev.txt`   | api + worker + pytest, httpx                     |

## Tests

```bash
pytest -m "not slow"   # fast unit + route tests
pytest                 # also runs the basic-pitch model test
```
