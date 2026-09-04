import subprocess
import tempfile
import librosa
import soundfile as sf
from pathlib import Path
import numpy as np
from models import Note
from basic_pitch.inference import predict

class AudioExtractionError(Exception):
    def __init__(self, message="ffmpeg error"):
        """Exception raised when audio extraction fails with ffmpeg"""
        super().__init__(f"Audio extraction failed: {message}")


def extract_audio(video_path: Path, output_path: Path) -> None:
    """Extract mono 22050Hz WAV from video. Raises AudioExtractionError on failure."""

    if not video_path.exists():
        raise AudioExtractionError(f"Input file not found: {video_path}")
        
    try:
        subprocess.run([
            "ffmpeg",
            "-i", str(video_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "22050",
            "-ac", "1",
            str(output_path)
        ], check=True, capture_output=True, text=True)
        print("Audio extracted successfully")
    except subprocess.CalledProcessError as e:
        raise AudioExtractionError(e) from e

def load_audio(path: Path, sample_rate: int = 22050) -> tuple[np.ndarray, int]:
    audio_array, sample_rate = librosa.load(path)
    return audio_array, sample_rate

def detect_notes(audio: np.ndarray, sample_rate: int) -> list[Note]:
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp_wav:
        sf.write(tmp_wav.name, audio, sample_rate)
        _, _, note_events = predict(tmp_wav.name)

    notes = []
    for start_time, end_time, pitch_midi, amplitude, pitch_bend in note_events:
        notes.append(
            Note(
                pitch=float(pitch_midi),
                start_time=float(start_time),
                duration=float(end_time - start_time),
            )
        )
    return notes

if __name__ == "__main__":
    video_path = Path("./tests/fixtures/video.mp4")
    output_path = Path("./tests/fixtures/output.wav")

    extract_audio(video_path, output_path)