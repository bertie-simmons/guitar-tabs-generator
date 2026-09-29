"""Turn queued jobs into finished tabs.

`process_job` is the unit of work: given a job id it reads the job from the
store, downloads the upload into a temp dir, runs `extract_audio ->
detect_notes -> notes_to_tab`, and writes `done` + the tab or `failed` + an
error message back. It returns whether the job is finished, or should go back
on the queue for another attempt.

`handle_claimed` acts on that: ack a finished job's queue entry, release an
unfinished one. `run` is the consumer loop around it - claim, handle, repeat,
until SIGINT/SIGTERM. `python -m gtab.worker` calls it.

A job is retried when something unexpected goes wrong (a pipeline bug, a
flaky download, a worker killed mid-job), up to `MAX_ATTEMPTS` starts. Input
that can never work - no audio track, upload missing - fails on the first go.

`extract_audio` and `detect_notes` are imported by name so tests can monkeypatch
them on this module.
"""

import logging
import signal
import tempfile
from enum import Enum
from pathlib import Path

from gtab import jobs, uploads
from gtab.config import MAX_ATTEMPTS
from gtab.jobs import JobStore
from gtab.models import Job
from gtab.pipeline.audio import AudioExtractionError, detect_notes, extract_audio
from gtab.pipeline.tabs import notes_to_tab
from gtab.uploads import UploadNotFoundError

logger = logging.getLogger(__name__)


class Outcome(Enum):
    FINISHED = "finished"  # done or failed for good - ack the queue entry
    RETRY = "retry"  # might work next time - release the queue entry


def process_job(job_id: str, store: JobStore | None = None) -> Outcome:
    """Process the job with `job_id`, updating its status in `store`.

    `store` defaults to the shared `job_store`; it is a parameter so a test or a
    standalone worker can pass its own. Pipeline errors never escape; errors
    talking to the store itself do, and the caller should retry the job.
    """
    store = store or jobs.job_store

    job = store.get(job_id)
    if job is None:
        logger.warning("worker asked for unknown job %s", job_id)
        return Outcome.FINISHED
    if job.status in ("done", "failed"):
        # Delivered again after it finished - a worker saved the result but
        # died before acking. Nothing to redo.
        logger.info("job %s is already %s - skipping", job_id, job.status)
        _discard_upload(job)
        return Outcome.FINISHED
    if not job.source_path:
        _fail(store, job, "job has no source video")
        return

    job.status = "processing"
    store.save(job)

    try:
        with tempfile.TemporaryDirectory(prefix=f"gtab-{job_id}-") as scratch:
            video_path = Path(scratch) / Path(job.source_path).name
            audio_path = Path(scratch) / "audio.wav"
            uploads.upload_store.download_to(job.source_path, video_path)
            extract_audio(video_path, audio_path)
            job.result = notes_to_tab(detect_notes(audio_path))
    except (UploadNotFoundError, AudioExtractionError) as exc:
        logger.warning("job %s failed: %s", job_id, exc)
        _fail(store, job, str(exc))
        _discard_upload(job)
        return Outcome.FINISHED
    except Exception as exc:  # noqa: BLE001 - unexpected -> retry, then fail
        if job.attempts >= MAX_ATTEMPTS:
            logger.exception("job %s failed on its last attempt", job_id)
            _fail(store, job, str(exc))
            _discard_upload(job)
            return Outcome.FINISHED
        logger.exception(
            "job %s failed on attempt %d of %d - will retry",
            job_id, job.attempts, MAX_ATTEMPTS,
        )
        job.status = "pending"
        store.save(job)
        return Outcome.RETRY

    job.status = "done"
    store.save(job)
    _discard_upload(job)
    return Outcome.FINISHED


def _fail(store: JobStore, job: Job, message: str) -> None:
    job.status = "failed"
    job.error = message
    store.save(job)


def _discard_upload(job: Job) -> None:
    """Delete a finished job's upload. Only once it is finished - a retry
    needs it."""
    if not job.source_path:
        return
    try:
        uploads.upload_store.delete(job.source_path)
    except Exception:  # noqa: BLE001 - an orphaned upload beats a failed job
        logger.exception("could not delete upload for job %s", job.id)


def handle_claimed(job_id: str) -> Outcome:
    """Process a claimed job, then ack or release its queue entry."""
    try:
        outcome = process_job(job_id)
    except Exception:  # noqa: BLE001 - e.g. the store is unreachable
        logger.exception("job %s: worker error - releasing it for another go", job_id)
        outcome = Outcome.RETRY
    if outcome is Outcome.FINISHED:
        jobs.job_queue.ack(job_id)
    else:
        jobs.job_queue.release(job_id)
    return outcome


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
        handle_claimed(job_id)
    logger.info("worker stopped")
