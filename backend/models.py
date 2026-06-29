from pydantic import BaseModel, field_validator
from typing import Literal

class Note(BaseModel):
    pitch : float
    start_time : float
    duration : float

    @field_validator("pitch")
    def validate_pitch(cls, value):
        if value <= 0:
            raise ValueError(f"pitch must be positive: {value}")
        return value
    
    # TODO add validator for time and duration

class TabData(BaseModel):
    string : int
    fret : int
    time : float

    # TODO add validtor for fret and string and time

class Job(BaseModel):
    id : str
    fret : Literal["pending","processing","done","failed"]
    result : TabData | None