import subprocess
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from audio import AudioExtractionError, detect_notes, extract_audio, load_audio
from constants import SAMPLE_RATE

# === extract_audio ========================================================


def test_missing_file_raises():
    with pytest.raises(AudioExtractionError, match="not found"):
        extract_audio(Path("nonexistent.mp4"), Path("out.wav"))


def test_ffmpeg_failure_raises(tmp_path):
    with patch("audio.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "ffmpeg", stderr="some error"
        )
        with pytest.raises(AudioExtractionError, match="some error"):
            extract_audio(Path(__file__), tmp_path / "out.wav")


def test_ffmpeg_missing_binary_raises(tmp_path):
    with patch("audio.subprocess.run", side_effect=FileNotFoundError()):
        with pytest.raises(AudioExtractionError, match="ffmpeg is not installed"):
            extract_audio(Path(__file__), tmp_path / "out.wav")


def test_calls_ffmpeg_with_correct_args(tmp_path):
    out = tmp_path / "out.wav"
    with patch("audio.subprocess.run") as mock_run:
        out.write_bytes(b"fake wav data")  # so the empty-output check passes
        extract_audio(Path(__file__), out)
        args = mock_run.call_args[0][0]
    assert args[0] == "ffmpeg"
    assert "-ar" in args and str(SAMPLE_RATE) in args
    assert "-ac" in args and "1" in args
    assert "-vn" in args


def test_extract_audio_from_fixture(fixture_video, tmp_path):
    out = tmp_path / "audio.wav"
    extract_audio(fixture_video, out)
    assert out.exists() and out.stat().st_size > 0


# === load_audio ===========================================================


def test_load_audio_returns_mono_array(sine_wav):
    audio, sr = load_audio(sine_wav)
    assert sr == SAMPLE_RATE
    assert audio.ndim == 1
    assert audio.shape[0] > 0


# === detect_notes =========================================================


def test_detect_notes_silent_returns_empty(silent_wav):
    assert detect_notes(silent_wav) == []


@pytest.mark.slow
def test_detect_notes_on_tone(sine_wav):
    notes = detect_notes(sine_wav)
    assert notes, "expected at least one note from a sustained 440 Hz tone"
    # 440 Hz is MIDI 69; allow a semitone of slack.
    assert min(abs(n.pitch_midi - 69) for n in notes) <= 1
