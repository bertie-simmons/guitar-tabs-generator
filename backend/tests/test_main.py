import io

import pytest
from fastapi.testclient import TestClient

import main
from audio import AudioExtractionError
from models import Note

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def clear_jobs():
    main.jobs.clear()
    yield
    main.jobs.clear()


def fake_upload(name: str = "clip.mp4") -> dict:
    return {"file": (name, io.BytesIO(b"not a real video"), "video/mp4")}


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_rejects_unsupported_file_type():
    resp = client.post("/upload", files=fake_upload("notes.txt"))
    assert resp.status_code == 400


def test_full_flow_success(monkeypatch, tmp_path):
    # TestClient runs BackgroundTasks synchronously, so processing finishes
    # before the /upload response returns.
    monkeypatch.setattr(main, "extract_audio", lambda v, a: a.write_bytes(b"wav"))
    monkeypatch.setattr(
        main,
        "detect_notes",
        lambda audio_path: [Note(pitch_midi=40, start_time=0.0, duration=0.5)],
    )

    job_id = client.post("/upload", files=fake_upload()).json()["job_id"]

    status = client.get(f"/status/{job_id}").json()
    assert status["status"] == "done"

    result = client.get(f"/result/{job_id}").json()
    assert result["positions"] == [{"string": 6, "fret": 0, "time": 0.0}]


def test_failed_job_reports_error(monkeypatch):
    def boom(video_path, audio_path):
        raise AudioExtractionError("no audio track")

    monkeypatch.setattr(main, "extract_audio", boom)

    job_id = client.post("/upload", files=fake_upload()).json()["job_id"]

    status = client.get(f"/status/{job_id}").json()
    assert status["status"] == "failed"
    assert "no audio track" in status["error"]

    assert client.get(f"/result/{job_id}").status_code == 409


def test_unknown_job_is_404():
    assert client.get("/status/nope").status_code == 404
    assert client.get("/result/nope").status_code == 404
