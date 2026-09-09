"""The pure transcription pipeline: ``video -> audio -> notes -> tab``.

Nothing in here knows about HTTP, jobs, or storage - every function takes its
inputs and returns its outputs. `gtab.worker` is what strings the stages
together for a real job.
"""

from gtab.pipeline.audio import (
    AudioExtractionError,
    detect_notes,
    extract_audio,
    load_audio,
)
from gtab.pipeline.tabs import notes_to_tab

__all__ = [
    "AudioExtractionError",
    "detect_notes",
    "extract_audio",
    "load_audio",
    "notes_to_tab",
]
