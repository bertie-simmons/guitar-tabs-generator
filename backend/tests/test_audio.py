import pytest
import subprocess
from pathlib import Path
from backend.audio import extract_audio, AudioExtractionError
from unittest.mock import patch

def test_missing_file_raises():
    with pytest.raises(AudioExtractionError, match="not found"):
        extract_audio(Path("nonexistent.mp4"), Path("out.wav"))

def test_ffmpeg_failure_raises():
    with patch("backend.audio.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "ffmpeg", stderr="some error")
        with pytest.raises(AudioExtractionError):
            extract_audio(Path(__file__), Path("out.wav"))  # __file__ exists, so it passes the existence check

def test_calls_ffmpeg_with_correct_args():
    with patch("backend.audio.subprocess.run") as mock_run:
        extract_audio(Path(__file__), Path("out.wav"))
        args = mock_run.call_args[0][0] 
        assert "-ar" in args
        assert "22050" in args
        assert "-ac" in args
        assert "1" in args