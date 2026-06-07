import pytest
import subprocess
from pathlib import Path
from backend.audio import extract_audio, AudioExtractionError
from unittest.mock import patch

def test_missing_file_raises():
    with pytest.raises(AudioExtractionError, match="not found"):
        extract_audio(Path("nonexistent.mp4"), Path("out.wav"))
