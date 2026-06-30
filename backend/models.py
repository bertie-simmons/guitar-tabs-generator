from pydantic import BaseModel, field_validator
from typing import Literal

class Note(BaseModel):
    pitch : float
    start_time : float
    duration : float

    @field_validator("pitch")
    def validate_pitch(cls, value):
        if value < 0:
            raise ValueError(f"pitch must be positive: {value}")
        return value

    @field_validator("start_time")
    def validate_start_time(cls, value):
        if value < 0:
            raise ValueError(f"start-time must be postive: {value}")
        return value

    @field_validator("duration")
    def validate_duration(cls, value):
        if value < 0:
            raise ValueError(f"duration must be postive: {value}")
        return value


class TabData(BaseModel):
    string : int
    fret : int
    time : float

    # TODO add validtor for fret and string and time

class Job(BaseModel):
    id : str
    fret : Literal["pending","processing","done","failed"]
    result : TabData | None