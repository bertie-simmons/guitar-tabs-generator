"""Shared test fixtures."""

import os
import socket
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from gtab import jobs, uploads
from gtab.pipeline.constants import SAMPLE_RATE

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def memory_backend(tmp_path: Path) -> None:
    """Give every test a fresh in-memory job store and queue, and its own
    upload directory so nothing leaks into the repo."""
    jobs.configure("memory")
    uploads.configure("memory", tmp_path / "uploads")


# Azurite's well-known development account - public, not a secret.
AZURITE = os.environ.get(
    "GTAB_TEST_AZURITE_CONNECTION_STRING",
    "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
    "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
    "QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;"
    "TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;",
)


@pytest.fixture(scope="session")
def azurite() -> str:
    """Azurite's connection string, or skip if it isn't running.

    Start it with ``docker compose up azurite``.
    """
    parts = dict(part.split("=", 1) for part in AZURITE.split(";") if "=" in part)
    for key in ("BlobEndpoint", "QueueEndpoint", "TableEndpoint"):
        url = parts[key]
        host, port = url.split("//", 1)[1].split("/", 1)[0].split(":")
        try:
            socket.create_connection((host, int(port)), timeout=0.5).close()
        except OSError:
            pytest.skip(f"Azurite not reachable at {url}")
    return AZURITE


@pytest.fixture
def azure_name() -> str:
    """A fresh table / queue / container name, so tests don't share state."""
    return f"t{uuid.uuid4().hex[:20]}"


@pytest.fixture
def azure_services(azurite: str, azure_name: str) -> Iterator[dict]:
    """Blob, queue and table clients for Azurite. Deletes what the test made."""
    from gtab import azure_storage
    from gtab import config

    config_before = config.AZURE_STORAGE_CONNECTION_STRING
    config.AZURE_STORAGE_CONNECTION_STRING = azurite
    services = {
        "blob": azure_storage.blob_service(),
        "queue": azure_storage.queue_service(),
        "table": azure_storage.table_service(),
    }
    yield services
    config.AZURE_STORAGE_CONNECTION_STRING = config_before
    for delete in (
        lambda: services["blob"].delete_container(azure_name),
        lambda: services["queue"].delete_queue(azure_name),
        lambda: services["table"].delete_table(azure_name),
    ):
        try:
            delete()
        except Exception:  # noqa: BLE001 - it may never have been created
            pass


@pytest.fixture
def run_worker() -> Callable[[], int]:
    """Drain the job queue the way `gtab.worker.run` would, and return how many
    times a job was claimed (a retried job counts once per attempt).

    Imported lazily so tests that do not need the pipeline (and CI jobs that do
    not install it) are unaffected.
    """
    from gtab.worker.runner import handle_claimed

    def _drain() -> int:
        claimed = 0
        while (job_id := jobs.job_queue.claim(timeout=0)) is not None:
            handle_claimed(job_id)
            claimed += 1
        return claimed

    return _drain


@pytest.fixture
def fixture_video() -> Path:
    return FIXTURES / "video.mp4"


@pytest.fixture
def sine_wav(tmp_path: Path) -> Path:
    """A 1-second A4 (440 Hz) tone written to a wav file."""
    t = np.linspace(0.0, 1.0, SAMPLE_RATE, endpoint=False)
    tone = 0.5 * np.sin(2 * np.pi * 440.0 * t)
    path = tmp_path / "a4.wav"
    sf.write(path, tone.astype(np.float32), SAMPLE_RATE)
    return path


@pytest.fixture
def silent_wav(tmp_path: Path) -> Path:
    path = tmp_path / "silence.wav"
    sf.write(path, np.zeros(SAMPLE_RATE, dtype=np.float32), SAMPLE_RATE)
    return path
