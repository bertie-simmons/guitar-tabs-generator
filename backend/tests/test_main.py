import io

from fastapi.testclient import TestClient

from gtab import jobs, uploads
from gtab.api import main as api_main
from gtab.models import Note
from gtab.pipeline.audio import AudioExtractionError
from gtab.worker import runner

client = TestClient(api_main.app)


def fake_upload(name: str = "clip.mp4") -> dict:
    return {"file": (name, io.BytesIO(b"not a real video"), "video/mp4")}


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_rejects_unsupported_file_type():
    resp = client.post("/upload", files=fake_upload("notes.txt"))
    assert resp.status_code == 400


def test_upload_enqueues_without_processing(tmp_path):
    job_id = client.post("/upload", files=fake_upload()).json()["job_id"]

    # The job points at the stored upload by name, not by a local path.
    source = jobs.job_store.get(job_id).source_path
    assert source == f"{job_id}.mp4"
    uploads.upload_store.download_to(source, tmp_path / "copy.mp4")
    assert (tmp_path / "copy.mp4").read_bytes() == b"not a real video"

    # The API only enqueues - nothing runs until a worker claims the job.
    assert client.get(f"/status/{job_id}").json()["status"] == "pending"
    assert client.get(f"/result/{job_id}").status_code == 409


def test_full_flow_success(monkeypatch, run_worker):
    # Patch the pipeline stages on the worker module, where process_job looks
    # them up.
    monkeypatch.setattr(runner, "extract_audio", lambda v, a: a.write_bytes(b"wav"))
    monkeypatch.setattr(
        runner,
        "detect_notes",
        lambda audio_path: [Note(pitch_midi=40, start_time=0.0, duration=0.5)],
    )

    job_id = client.post("/upload", files=fake_upload()).json()["job_id"]

    assert run_worker() == 1

    assert client.get(f"/status/{job_id}").json()["status"] == "done"
    result = client.get(f"/result/{job_id}").json()
    assert result["positions"] == [{"string": 6, "fret": 0, "time": 0.0}]


def test_failed_job_reports_error(monkeypatch, run_worker):
    def boom(video_path, audio_path):
        raise AudioExtractionError("no audio track")

    monkeypatch.setattr(runner, "extract_audio", boom)

    job_id = client.post("/upload", files=fake_upload()).json()["job_id"]
    run_worker()

    status = client.get(f"/status/{job_id}").json()
    assert status["status"] == "failed"
    assert "no audio track" in status["error"]

    assert client.get(f"/result/{job_id}").status_code == 409


def test_unknown_job_is_404():
    assert client.get("/status/nope").status_code == 404
    assert client.get("/result/nope").status_code == 404
