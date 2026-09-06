"""FastAPI app: accept a video upload, run the pipeline in the background,
let the client poll for status and fetch the finished tab.

Note: Job state lives in an in-memory dict for now. 
"""

import logging
import shutil
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from audio import AudioExtractionError, detect_notes, extract_audio
from models import Job, Tab
from tabs import notes_to_tab

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Guitar Tabs Generator")

# next
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
AUDIO_DIR = Path("audio_cache")
UPLOAD_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)

ALLOWED_SUFFIXES = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v", ".wav", ".mp3"}

jobs: dict[str, Job] = {}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
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

    jobs[job_id] = Job(id=job_id, status="pending")
    background_tasks.add_task(process_video, job_id, video_path)
    return {"job_id": job_id}


def process_video(job_id: str, video_path: Path) -> None:
    """Extract -> detect -> tab. Runs in a worker thread via BackgroundTasks."""
    job = jobs[job_id]
    job.status = "processing"
    audio_path = AUDIO_DIR / f"{job_id}.wav"

    try:
        extract_audio(video_path, audio_path)
        notes = detect_notes(audio_path)
        job.result = notes_to_tab(notes)
        job.status = "done"
    except AudioExtractionError as exc:
        logger.warning("job %s failed during extraction: %s", job_id, exc)
        job.status = "failed"
        job.error = str(exc)
    except Exception as exc:  # noqa: BLE001 - any pipeline error -> failed job
        logger.exception("job %s failed", job_id)
        job.status = "failed"
        job.error = str(exc)
    finally:
        video_path.unlink(missing_ok=True)


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return {"job_id": job.id, "status": job.status, "error": job.error}


@app.get("/result/{job_id}")
async def get_result(job_id: str) -> Tab:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status != "done" or job.result is None:
        raise HTTPException(
            status_code=409, detail=f"job is not ready (status: {job.status})"
        )
    return job.result
