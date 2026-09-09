"""FastAPI app: accept a video upload, hand the job to the worker, let the
client poll for status and fetch the finished tab.

The API does HTTP and bookkeeping only. It saves the upload, records a `Job` in
the shared store, and enqueues its id; `gtab.worker` picks it up and does the
processing. Nothing here imports `gtab.pipeline`, so the API image carries no
ffmpeg, TensorFlow or librosa - `tests/test_import_boundary.py` enforces that.
"""

import logging
import shutil
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from gtab import jobs
from gtab.config import CORS_ORIGINS, UPLOAD_DIR, ensure_dirs
from gtab.models import Job, Tab

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_dirs()
    yield


app = FastAPI(title="Guitar Tabs Generator", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_SUFFIXES = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v", ".wav", ".mp3"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported file type '{suffix or file.filename}'",
        )

    job_id = str(uuid.uuid4())
    video_path = UPLOAD_DIR / f"{job_id}{suffix}"
    with video_path.open("wb") as out_file:
        shutil.copyfileobj(file.file, out_file)

    jobs.job_store.create(Job(id=job_id, status="pending", source_path=str(video_path)))
    jobs.job_queue.enqueue(job_id)
    return {"job_id": job_id}


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    job = jobs.job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return {"job_id": job.id, "status": job.status, "error": job.error}


@app.get("/result/{job_id}")
async def get_result(job_id: str) -> Tab:
    job = jobs.job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status != "done" or job.result is None:
        raise HTTPException(
            status_code=409, detail=f"job is not ready (status: {job.status})"
        )
    return job.result
