"""Pydantic models shared across the pipeline and the API.

Two kinds of object live here:

* domain objects that flow between pipeline stages (`Note`, `TabPosition`, `Tab`)
* an API/state object (`Job`) that tracks one upload through processing
"""

from typing import Literal

from pydantic import BaseModel, Field

JobStatus = Literal["pending", "processing", "done", "failed"]


class Note(BaseModel):
    """A single detected note.

    `pitch_midi` is a MIDI note number
    """

    pitch_midi: float = Field(ge=0, le=127)
    start_time: float = Field(ge=0, description="seconds from the start of the clip")
    duration: float = Field(ge=0, description="seconds")


class TabPosition(BaseModel):
    """Where a single note is played on the fretboard."""

    string: int = Field(ge=1, le=6, description="1 = high E, 6 = low E")
    fret: int = Field(ge=0, le=24, description="0 = open string")
    time: float = Field(ge=0, description="seconds from the start of the clip")


class Tab(BaseModel):
    """A finished tab - an ordered list of fretboard positions."""

    positions: list[TabPosition] = Field(default_factory=list)


class Job(BaseModel):
    """Tracks one uploaded video through the pipeline."""

    id: str
    status: JobStatus = "pending"
    result: Tab | None = None
    error: str | None = None
