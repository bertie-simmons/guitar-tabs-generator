"""The job store + queue backends, and the seam contract both sides rely on."""

import pytest

from gtab import jobs
from gtab.jobs import FileJobQueue, FileJobStore, InMemoryJobQueue, InMemoryJobStore
from gtab.models import Job, Tab, TabPosition


def a_job(job_id: str = "j1") -> Job:
    return Job(id=job_id, status="pending", source_path=f"/uploads/{job_id}.mp4")


# === store contract, both backends =======================================


@pytest.fixture(params=["memory", "file", "azure"])
def store(request, tmp_path):
    if request.param == "azure":
        from gtab.azure_storage import TableJobStore

        services = request.getfixturevalue("azure_services")
        return TableJobStore(services["table"], request.getfixturevalue("azure_name"))
    return InMemoryJobStore() if request.param == "memory" else FileJobStore(tmp_path)


def test_create_then_get_roundtrips(store):
    store.create(a_job())
    got = store.get("j1")
    assert got is not None
    assert got.id == "j1"
    assert got.status == "pending"


def test_get_unknown_is_none(store):
    assert store.get("nope") is None


def test_create_rejects_duplicate(store):
    store.create(a_job())
    with pytest.raises(ValueError, match="already exists"):
        store.create(a_job())


def test_save_persists_result_and_status(store):
    store.create(a_job())
    job = store.get("j1")
    job.status = "done"
    job.result = Tab(positions=[TabPosition(string=6, fret=0, time=0.0)])
    store.save(job)

    reloaded = store.get("j1")
    assert reloaded.status == "done"
    assert reloaded.result.positions[0].fret == 0


def test_get_returns_a_snapshot_not_a_live_handle(store):
    store.create(a_job())
    job = store.get("j1")
    job.status = "processing"  # mutate the copy, don't save
    assert store.get("j1").status == "pending"


# === queue contract, both backends =======================================


@pytest.fixture(params=["memory", "file", "azure"])
def jq(request, tmp_path):
    if request.param == "azure":
        from gtab.azure_storage import QueueJobQueue

        services = request.getfixturevalue("azure_services")
        name = request.getfixturevalue("azure_name")
        return QueueJobQueue(services["queue"], name, visibility_timeout=30)
    return InMemoryJobQueue() if request.param == "memory" else FileJobQueue(tmp_path)


def test_claim_returns_none_when_empty(jq):
    assert jq.claim(timeout=0) is None


def test_enqueue_then_claim_is_fifo(jq):
    jq.enqueue("a")
    jq.enqueue("b")
    assert jq.claim(timeout=0) == "a"
    assert jq.claim(timeout=0) == "b"
    assert jq.claim(timeout=0) is None


def test_claim_then_ack_does_not_redeliver(jq):
    jq.enqueue("a")
    claimed = jq.claim(timeout=0)
    jq.ack(claimed)
    assert jq.claim(timeout=0) is None


def test_release_redelivers(jq):
    jq.enqueue("a")
    jq.release(jq.claim(timeout=0))
    assert jq.claim(timeout=0) == "a"


def test_release_goes_to_the_back(jq):
    jq.enqueue("a")
    jq.enqueue("b")
    jq.release(jq.claim(timeout=0))  # "a" had a go and failed
    assert jq.claim(timeout=0) == "b"
    assert jq.claim(timeout=0) == "a"


def test_claim_waits_up_to_timeout(jq):
    assert jq.claim(timeout=0.3) is None


# === azure-specific behaviour ============================================


def test_table_store_holds_a_tab_bigger_than_one_property(azure_services, azure_name):
    from gtab.azure_storage import TableJobStore

    store = TableJobStore(azure_services["table"], azure_name)
    store.create(a_job())
    job = store.get("j1")
    job.status = "done"
    job.result = Tab(
        positions=[TabPosition(string=1 + i % 6, fret=i % 20, time=i * 0.1) for i in range(3000)]
    )
    assert len(job.model_dump_json()) > TableJobStore.CHUNK * 2
    store.save(job)
    assert store.get("j1") == job

    # Saving a smaller job again must not leave stale chunks behind.
    job.result = None
    store.save(job)
    assert store.get("j1") == job


def test_queue_message_reappears_after_visibility_timeout(azure_services, azure_name):
    """A worker that dies mid-job (never acks) doesn't lose the job."""
    from gtab.azure_storage import QueueJobQueue

    dead_worker = QueueJobQueue(azure_services["queue"], azure_name, visibility_timeout=1)
    dead_worker.enqueue("a")
    assert dead_worker.claim(timeout=0) == "a"

    other = QueueJobQueue(azure_services["queue"], azure_name, visibility_timeout=30)
    assert other.claim(timeout=0) is None
    assert other.claim(timeout=5) == "a"
    other.ack("a")
    dead_worker.ack("a")  # stale receipt - logged, not raised
    assert other.claim(timeout=0) is None


def test_configure_azure_uses_the_azure_backends(azure_services, azure_name, monkeypatch):
    from gtab import config
    from gtab.azure_storage import QueueJobQueue, TableJobStore

    monkeypatch.setattr(config, "AZURE_JOB_TABLE", azure_name)
    monkeypatch.setattr(config, "AZURE_JOB_QUEUE", azure_name)
    jobs.configure("azure")
    assert isinstance(jobs.job_store, TableJobStore)
    assert isinstance(jobs.job_queue, QueueJobQueue)


def test_configure_rejects_unknown_backend():
    with pytest.raises(ValueError, match="unknown jobs backend"):
        jobs.configure("azrue")


# === file backend survives a "restart" ===================================


def test_file_backend_persists_across_instances(tmp_path):
    FileJobStore(tmp_path).create(a_job())
    FileJobQueue(tmp_path).enqueue("j1")

    # A fresh process would build new objects over the same directory.
    assert FileJobStore(tmp_path).get("j1") is not None
    assert FileJobQueue(tmp_path).claim(timeout=0) == "j1"


# === configure() rebinds the module singletons ==========================


def test_configure_switches_backend(tmp_path):
    jobs.configure("file", tmp_path)
    assert isinstance(jobs.job_store, FileJobStore)
    jobs.configure("memory")
    assert isinstance(jobs.job_store, InMemoryJobStore)
