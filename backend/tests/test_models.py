import pytest
from pydantic import ValidationError

from models import Job, Note, Tab, TabPosition

# === valid construction ==================================================


def test_note_valid_construction():
    note = Note(pitch_midi=85.2, start_time=0, duration=1.8)
    assert note.pitch_midi == 85.2
    assert note.start_time == 0
    assert note.duration == 1.8


def test_tabposition_valid_construction():
    pos = TabPosition(string=2, fret=5, time=1.5)
    assert (pos.string, pos.fret, pos.time) == (2, 5, 1.5)


def test_job_valid_construction():
    job = Job(id="abc123", status="pending")
    assert job.id == "abc123"
    assert job.status == "pending"
    assert job.result is None
    assert job.error is None


def test_job_with_result():
    tab = Tab(positions=[TabPosition(string=6, fret=0, time=0.0)])
    job = Job(id="j1", status="done", result=tab)
    assert job.result.positions[0].fret == 0


# === invalid Note =======================================================


@pytest.mark.parametrize(
    "kwargs",
    [
        {"pitch_midi": -1, "start_time": 0, "duration": 1.8},
        {"pitch_midi": 200, "start_time": 0, "duration": 1.8},
        {"pitch_midi": 60, "start_time": -1, "duration": 1.8},
        {"pitch_midi": 60, "start_time": 0, "duration": -1},
    ],
)
def test_note_invalid(kwargs):
    with pytest.raises(ValidationError):
        Note(**kwargs)


# === invalid TabPosition ================================================


@pytest.mark.parametrize(
    "kwargs",
    [
        {"string": 0, "fret": 5, "time": 1.5},
        {"string": 7, "fret": 5, "time": 1.5},
        {"string": 3, "fret": -1, "time": 1.5},
        {"string": 3, "fret": 25, "time": 1.5},
        {"string": 3, "fret": 5, "time": -0.1},
    ],
)
def test_tabposition_invalid(kwargs):
    with pytest.raises(ValidationError):
        TabPosition(**kwargs)


# === invalid Job ========================================================


def test_job_invalid_status():
    with pytest.raises(ValidationError):
        Job(id="j1", status="in-progress")
