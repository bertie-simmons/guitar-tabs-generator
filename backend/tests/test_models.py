import pytest
from backend.models import Note, TabData, Job
from typing import Literal
from pydantic import BaseModel, ValidationError

# === Construction Validators ==============================================

def test_note_valid_construction():

    note = Note(
        pitch=85.2,
        start_time=0,
        duration=1.8
    )

    assert note.pitch ==  85.2
    assert note.start_time == 0
    assert note.duration == 1.8

def test_tabdata_valid_construction():
    tab = TabData(
        string=2,
        fret=5,
        time=1.5
    )

    assert tab.string == 2
    assert tab.fret == 5
    assert tab.time == 1.5

def test_job_valid_construction():
    job = Job(
        id="abc123",
        fret="pending",
        result=None
    )

    assert job.id == "abc123"
    assert job.fret == "pending"
    assert job.result is None

# valid_data = {
#         "id" : "job1",
#         "status" : "pending",
#         "result" : TabData(
#             string = 2,
#             fret = 5,
#             time = 25.4
#         )
#     }

# === Invalid Values =============================================

