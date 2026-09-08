"""Audio stage of the pipeline: video -> audio -> detected notes

`extract_audio` uses ffmpeg.
`detect_notes` runs spotify basic-pitch model over the extracted audio (wav).
"""

import logging
import subprocess
from pathlib import Path

import librosa
import numpy as np

from constants import SAMPLE_RATE, SILENCE_THRESHOLD
from models import Note

logger = logging.getLogger(__name__)

# cached basic pitch model
# loading takes a couple secs; load once and resuse
_model = None


def _get_model():
    global _model
    if _model is None:
        from basic_pitch import ICASSP_2022_MODEL_PATH
        from basic_pitch.inference import Model

        _model = Model(ICASSP_2022_MODEL_PATH)
    return _model


class AudioExtractionError(Exception):
    """Raised when ffmpeg cannot produce an audio track from the input."""

    def __init__(self, message: str = "ffmpeg error"):
        super().__init__(f"Audio extraction failed: {message}")


def extract_audio(video_path: Path, output_path: Path) -> None:
    """Extract a mono, `SAMPLE_RATE` Hz WAV from `video_path` into `output_path`.

    Raises `AudioExtractionError` if the input is missing, ffmpeg is not
    installed, or ffmpeg exits non-zero (e.g. the file has no audio track).
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise AudioExtractionError(f"input file not found: {video_path}")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",  # overwrite output if it already exists
        "-i", str(video_path),
        "-vn",  # drop the video stream
        "-acodec", "pcm_s16le",
        "-ar", str(SAMPLE_RATE),
        "-ac", "1",  # mono
        str(output_path),
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:  # ffmpeg binary not on PATH
        raise AudioExtractionError("ffmpeg is not installed or not on PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise AudioExtractionError(exc.stderr.strip() or "ffmpeg exited non-zero") from exc

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise AudioExtractionError("ffmpeg produced an empty file (no audio track?)")


def load_audio(
    path: Path, sample_rate: int = SAMPLE_RATE
) -> tuple[np.ndarray, int]:
    """Load `path` as a mono float32 waveform resampled to `sample_rate`."""
    audio, sr = librosa.load(path, sr=sample_rate, mono=True)
    return audio, sr


def detect_notes(audio_path: Path) -> list[Note]:
    """Detect notes in the wav at `audio_path` using basic-pitch.

    Returns an empty list for silent or empty audio rather than raising.
    """
    audio, _ = load_audio(audio_path)
    if audio.size == 0 or float(np.max(np.abs(audio))) < SILENCE_THRESHOLD:
        return []

    # imported lazily - slow import
    from basic_pitch.inference import predict

    _, _, note_events = predict(
        str(audio_path), 
        _get_model(),
        onset_threshold=0.6,       # default 0.5 — ghosts have weaker onsets
        frame_threshold=0.4,       # default 0.3
        minimum_note_length=90.0,  # default ~128ms 
        minimum_frequency=78.0,    # E2 ≈ 82 Hz
        maximum_frequency=1400.0,  # 24th-fret high E ≈ 1319 Hz
    )

    notes: list[Note] = []
    for start_time, end_time, pitch_midi, _amplitude, _pitch_bend in note_events:
        notes.append(
            Note(
                pitch_midi=float(pitch_midi),
                start_time=float(start_time),
                duration=float(end_time - start_time),
            )
        )
    notes.sort(key=lambda n: n.start_time)
    return notes
