"""Turn queued jobs into finished tabs.

`process_job` is the unit of work: given a job id it reads the job from the
store, runs `extract_audio -> detect_notes -> notes_to_tab`, and writes `done` +
the tab or `failed` + an error message back. It never raises - a broken job
becomes a failed job.

`run` is the consumer loop: claim an id off the queue, process it, ack it,
repeat, until SIGINT/SIGTERM. `python -m gtab.worker` calls it.

`extract_audio` and `detect_notes` are imported by name so tests can monkeypatch
them on this module.
"""

import logging
import signal
from pathlib import Path

from gtab import jobs
from gtab.config import AUDIO_DIR
from gtab.jobs import JobStore
from gtab.models import Job
from gtab.pipeline.audio import AudioExtractionError, detect_notes, extract_audio
from gtab.pipeline.tabs import notes_to_tab

logger = logging.getLogger(__name__)


def process_job(job_id: str, store: JobStore | None = None) -> None:
    """Process the job with `job_id`, updating its status in `store`.

    `store` defaults to the shared `job_store`; it is a parameter so a test or a
    standalone worker can pass its own.
    """
    store = store or jobs.job_store

    job = store.get(job_id)
    if job is None:
        logger.warning("worker asked for unknown job %s", job_id)
        return
    if not job.source_path:
        _fail(store, job, "job has no source video")
        return

    job.status = "processing"
    store.save(job)

    video_path = Path(job.source_path)
    audio_path = AUDIO_DIR / f"{job_id}.wav"
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    try:
        extract_audio(video_path, audio_path)
        notes = detect_notes(audio_path)
        job.result = notes_to_tab(notes)
        job.status = "done"
        store.save(job)
    except AudioExtractionError as exc:
        logger.warning("job %s failed during extraction: %s", job_id, exc)
        _fail(store, job, str(exc))
    except Exception as exc:  # noqa: BLE001 - any pipeline error -> failed job
        logger.exception("job %s failed", job_id)
        _fail(store, job, str(exc))
    finally:
        video_path.unlink(missing_ok=True)


def _fail(store: JobStore, job: Job, message: str) -> None:
    job.status = "failed"
    job.error = message
    store.save(job)


def run(poll_timeout: float = 2.0) -> None:
    """Claim and process jobs until interrupted.

    Finishes the job in hand before stopping on SIGINT/SIGTERM.
    """
    stopping = False

    def _stop(signum, _frame):
        nonlocal stopping
        logger.info("signal %s received - finishing current job then stopping", signum)
        stopping = True

    signal.signal(signal.SIGINT, _stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _stop)

    logger.info("worker started")
    while not stopping:
        job_id = jobs.job_queue.claim(timeout=poll_timeout)
        if job_id is None:
            continue
        logger.info("processing job %s", job_id)
        try:
            process_job(job_id)
        finally:
            jobs.job_queue.ack(job_id)
    logger.info("worker stopped")
