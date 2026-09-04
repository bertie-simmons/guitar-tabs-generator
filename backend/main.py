import shutil
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile

from audio import AudioExtractionError, detect_notes, extract_audio, load_audio
from models import Job
from tabs import notes_to_tab

app = FastAPI()

UPLOAD_DIR = Path("uploads")
AUDIO_DIR = Path("audio_cache")
UPLOAD_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)

# Stateless backend, in-memory job store (per the project's architecture notes).
jobs: dict[str, Job] = {}


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/upload")
async def upload(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    video_path = UPLOAD_DIR / f"{job_id}_{file.filename}"

    with video_path.open("wb") as out_file:
        shutil.copyfileobj(file.file, out_file)

    jobs[job_id] = Job(id=job_id, status="pending", result=None)
    background_tasks.add_task(process_video, job_id, video_path)

    return {"job_id": job_id}


def process_video(job_id: str, video_path: Path) -> None:
    """Extract -> detect -> tab pipeline, run as a FastAPI background task."""
    jobs[job_id].status = "processing"
    audio_path = AUDIO_DIR / f"{job_id}.wav"

    try:
        extract_audio(video_path, audio_path)
        audio_array, sample_rate = load_audio(audio_path)
        notes = detect_notes(audio_array, sample_rate)
        jobs[job_id].result = notes_to_tab(notes)
        jobs[job_id].status = "done"
    except AudioExtractionError:
        jobs[job_id].status = "failed"
    except Exception:
        # any failure in the pipeline (bad video, model error, etc.) should surface as a failed job
        jobs[job_id].status = "failed"


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job.id, "status": job.status}


@app.get("/result/{job_id}")
async def get_result(job_id: str):
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "done":
        raise HTTPException(
            status_code=409, detail=f"Job is not ready (status: {job.status})"
        )
    return job.result