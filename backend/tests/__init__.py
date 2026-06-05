from pathlib import Path
import pytest
from audio import extract_audio, AudioExtractionError

def test_missing_file_raises():
    with pytest.raises(AudioExtractionError, match="not found"):
        extract_audio(Path("nonexistent.mp4"), Path("out.wav"))