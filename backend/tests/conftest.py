"""Shared test fixtures."""

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from constants import SAMPLE_RATE

FIXTURES = Path(__file__).parent / "fixtures"


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
