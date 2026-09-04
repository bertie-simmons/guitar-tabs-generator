from pydantic import BaseModel, Field, field_validator
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
    string : Literal[ 1, 2, 3, 4, 5, 6 ]
    fret: int = Field(ge=0, le=24)
    time : float

    @field_validator("time")
    def validate_time(cls, value):
        if value < 0:
            raise ValueError(f"time must be postive: {value}")
        return value
    

class Job(BaseModel):
    id : str
    status : Literal["pending","processing","done","failed"]
    result : list[TabData] | None