"""When the worker acks, retries or gives up on a job, and what it cleans up."""

import io
from pathlib import Path

import pytest

from gtab import jobs, uploads
from gtab.config import MAX_ATTEMPTS
from gtab.models import Job, Note
from gtab.pipeline.audio import AudioExtractionError
from gtab.worker import runner
from gtab.worker.runner import Outcome, handle_claimed


def submit(job_id: str = "j1", **fields) -> str:
    """Do what the API does: store an upload, create the job, enqueue it."""
    name = f"{job_id}.mp4"
    uploads.upload_store.put(name, io.BytesIO(b"video"))
    jobs.job_store.create(Job(id=job_id, source_path=name, **fields))
    jobs.job_queue.enqueue(job_id)
    return job_id


def upload_exists(job_id: str, tmp_path: Path) -> bool:
    try:
        uploads.upload_store.download_to(f"{job_id}.mp4", tmp_path / "probe")
    except uploads.UploadNotFoundError:
        return False
    return True


@pytest.fixture
def working_pipeline(monkeypatch):
    """A pipeline that succeeds, recording the scratch paths it was given."""
    seen: dict[str, Path] = {}

    def extract(video_path, audio_path):
        assert video_path.read_bytes() == b"video"  # downloaded before use
        seen["video"], seen["audio"] = video_path, audio_path
        audio_path.write_bytes(b"wav")

    monkeypatch.setattr(runner, "extract_audio", extract)
    monkeypatch.setattr(
        runner, "detect_notes", lambda _: [Note(pitch_midi=40, start_time=0.0, duration=0.5)]
    )
    return seen


def flaky(monkeypatch, failures: int) -> None:
    """Make `detect_notes` raise an unexpected error `failures` times."""
    calls = {"n": 0}

    def detect(_):
        calls["n"] += 1
        if calls["n"] <= failures:
            raise RuntimeError("model blew up")
        return []

    monkeypatch.setattr(runner, "detect_notes", detect)


def test_success_acks_and_cleans_up(working_pipeline, run_worker, tmp_path):
    job_id = submit()

    assert run_worker() == 1

    job = jobs.job_store.get(job_id)
    assert job.status == "done"
    assert job.attempts == 1
    assert not upload_exists(job_id, tmp_path)
    # The scratch copy and the extracted audio went with the temp dir.
    assert not working_pipeline["video"].exists()
    assert not working_pipeline["audio"].exists()


def test_bad_input_fails_once_without_retry(monkeypatch, run_worker, tmp_path):
    def no_audio(video_path, audio_path):
        raise AudioExtractionError("no audio track")

    monkeypatch.setattr(runner, "extract_audio", no_audio)
    job_id = submit()

    assert run_worker() == 1  # not redelivered

    job = jobs.job_store.get(job_id)
    assert job.status == "failed"
    assert "no audio track" in job.error
    assert not upload_exists(job_id, tmp_path)


def test_missing_upload_fails_once(working_pipeline, run_worker):
    job_id = submit()
    uploads.upload_store.delete(f"{job_id}.mp4")

    assert run_worker() == 1

    job = jobs.job_store.get(job_id)
    assert job.status == "failed"
    assert "not found" in job.error


def test_unexpected_error_is_retried_then_succeeds(
    working_pipeline, monkeypatch, run_worker
):
    flaky(monkeypatch, failures=1)
    job_id = submit()

    assert run_worker() == 2

    job = jobs.job_store.get(job_id)
    assert job.status == "done"
    assert job.attempts == 2
    assert job.error is None


def test_retry_keeps_the_upload_and_resets_status(
    working_pipeline, monkeypatch, tmp_path
):
    flaky(monkeypatch, failures=1)
    job_id = submit()

    assert handle_claimed(jobs.job_queue.claim(timeout=0)) is Outcome.RETRY

    assert jobs.job_store.get(job_id).status == "pending"
    assert upload_exists(job_id, tmp_path)  # the next attempt needs it
    assert jobs.job_queue.claim(timeout=0) == job_id  # released, not acked


def test_unexpected_error_gives_up_after_max_attempts(
    working_pipeline, monkeypatch, run_worker, tmp_path
):
    flaky(monkeypatch, failures=MAX_ATTEMPTS)
    job_id = submit()

    assert run_worker() == MAX_ATTEMPTS

    job = jobs.job_store.get(job_id)
    assert job.status == "failed"
    assert job.error == "model blew up"
    assert job.attempts == MAX_ATTEMPTS
    assert not upload_exists(job_id, tmp_path)


def test_worker_that_died_every_time_is_given_up_on(working_pipeline, run_worker):
    # Every earlier start left the job mid-flight and never recorded an outcome.
    job_id = submit(status="processing", attempts=MAX_ATTEMPTS)

    assert run_worker() == 1

    job = jobs.job_store.get(job_id)
    assert job.status == "failed"
    assert job.error == f"gave up after {MAX_ATTEMPTS} attempts"


def test_crashed_job_is_picked_up_again(working_pipeline, run_worker):
    # A worker started it once and died; the queue delivered it again.
    job_id = submit(status="processing", attempts=1)

    assert run_worker() == 1

    job = jobs.job_store.get(job_id)
    assert job.status == "done"
    assert job.attempts == 2


def test_redelivered_finished_job_is_not_redone(monkeypatch, run_worker, tmp_path):
    def must_not_run(*_):
        raise AssertionError("pipeline ran for a finished job")

    monkeypatch.setattr(runner, "extract_audio", must_not_run)
    job_id = submit(status="done", attempts=1)

    assert run_worker() == 1

    assert jobs.job_store.get(job_id).status == "done"
    assert not upload_exists(job_id, tmp_path)


def test_store_error_releases_the_job(working_pipeline, monkeypatch):
    job_id = submit()

    def unreachable(job):
        raise ConnectionError("store unreachable")

    monkeypatch.setattr(jobs.job_store, "save", unreachable)

    assert handle_claimed(jobs.job_queue.claim(timeout=0)) is Outcome.RETRY
    assert jobs.job_queue.claim(timeout=0) == job_id
