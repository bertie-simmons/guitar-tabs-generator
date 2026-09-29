"""Shared test fixtures."""

from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from gtab import jobs, uploads
from gtab.pipeline.constants import SAMPLE_RATE

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def memory_backend(tmp_path: Path) -> None:
    """Give every test a fresh in-memory job store and queue, and its own
    upload directory so nothing leaks into the repo."""
    jobs.configure("memory")
    uploads.configure("memory", tmp_path / "uploads")


@pytest.fixture
def run_worker() -> Callable[[], int]:
    """Drain the job queue the way `gtab.worker.run` would, and return how many
    times a job was claimed (a retried job counts once per attempt).

    Imported lazily so tests that do not need the pipeline (and CI jobs that do
    not install it) are unaffected.
    """
    from gtab.worker.runner import handle_claimed

    def _drain() -> int:
        claimed = 0
        while (job_id := jobs.job_queue.claim(timeout=0)) is not None:
            handle_claimed(job_id)
            claimed += 1
        return claimed

    return _drain


@pytest.fixture
def fixture_video() -> Path:
    return FIXTURES / "video.mp4"


@pytest.fixture
def sine_wav(tmp_path: Path) -> Path:
    """A 1-second A4 (440 Hz) tone written to a wav file."""
    t = np.linspace(0.0, 1.0, SAMPLE_RATE, endpoint=False)
    tone = 0.5 * np.sin(2 * np.pi * 440.0 * t)
    path = tmp_path / "a4.wav"
    sf.write(path, tone.astype(np.float32), SAMPLE_RATE)
    return path


@pytest.fixture
def silent_wav(tmp_path: Path) -> Path:
    path = tmp_path / "silence.wav"
    sf.write(path, np.zeros(SAMPLE_RATE, dtype=np.float32), SAMPLE_RATE)
    return path
