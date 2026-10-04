"""The job store and job queue - the seam between the API and the worker.

The API creates a `Job`, persists it, and enqueues its id. The worker claims an
id off the queue, looks the job up, runs the pipeline, and writes status and
result back. Neither side imports the other; they meet only here.

Three backends:

* ``memory`` - a dict and a ``queue.Queue`` in one process. Used by the tests,
  and fine if you run the API and worker in the same process.
* ``file``   - JSON files under ``GTAB_STATE_DIR``. State survives a restart and
  is visible to a separate worker process on the same machine, so you can run
  ``uvicorn`` in one terminal and ``python -m gtab.worker`` in another.
* ``azure``  - Table Storage (the store) + Queue Storage (the queue), in
  `gtab.azure_storage`. Azurite locally, a storage account in Azure.

Selected by ``GTAB_JOBS_BACKEND`` (default ``file``). Tests call `configure()`.
"""

from __future__ import annotations

import os
import queue
import threading
import time
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from gtab.config import JOBS_BACKEND, STATE_DIR
from gtab.models import Job


# === interfaces ===========================================================


class JobStore(ABC):
    """Create, read and update `Job` records by id."""

    @abstractmethod
    def create(self, job: Job) -> None:
        """Store a new job. Raises `ValueError` if the id already exists."""

    @abstractmethod
    def get(self, job_id: str) -> Job | None:
        """Return a snapshot of the job, or `None` if there is no such id."""

    @abstractmethod
    def save(self, job: Job) -> None:
        """Persist the current state of an existing job."""


class JobQueue(ABC):
    """A one-way channel of job ids from the API to the worker."""

    @abstractmethod
    def enqueue(self, job_id: str) -> None:
        """Add a job id for a worker to pick up."""

    @abstractmethod
    def claim(self, timeout: float | None = None) -> str | None:
        """Take the next job id.

        Blocks up to `timeout` seconds (forever if `None`, not at all if `0`).
        Returns `None` if nothing became available in time.
        """

    @abstractmethod
    def ack(self, job_id: str) -> None:
        """Remove a claimed job id for good, so it is not redelivered.

        Only called once the job is finished - ``done``, or ``failed`` in a way
        a retry would not fix. Until then the id stays claimed, so a worker
        that dies mid-job leaves it to be delivered again.
        """

    @abstractmethod
    def release(self, job_id: str) -> None:
        """Give a claimed job id back so a worker picks it up again later.

        Called when the job hit a problem that might pass (an unexpected error
        in the pipeline, a failed download). `Job.attempts` in the store is
        what stops it being retried forever.
        """


# === in-memory backend ====================================================


class InMemoryJobStore(JobStore):
    """A process-local `JobStore` backed by a dict.

    `get` returns a deep copy, so callers mutate their own snapshot and only
    `save` makes changes visible - the same contract an out-of-process store
    has.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, job: Job) -> None:
        with self._lock:
            if job.id in self._jobs:
                raise ValueError(f"job {job.id} already exists")
            self._jobs[job.id] = job.model_copy(deep=True)

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return job.model_copy(deep=True) if job is not None else None

    def save(self, job: Job) -> None:
        with self._lock:
            self._jobs[job.id] = job.model_copy(deep=True)

    def clear(self) -> None:
        """Drop every job. Used by tests."""
        with self._lock:
            self._jobs.clear()


class InMemoryJobQueue(JobQueue):
    """A process-local `JobQueue` backed by ``queue.Queue``."""

    def __init__(self) -> None:
        self._q: queue.Queue[str] = queue.Queue()

    def enqueue(self, job_id: str) -> None:
        self._q.put(job_id)

    def claim(self, timeout: float | None = None) -> str | None:
        try:
            if timeout == 0:
                return self._q.get_nowait()
            return self._q.get(timeout=timeout)
        except queue.Empty:
            return None

    def ack(self, job_id: str) -> None:  # nothing to do - get() already removed it
        pass

    def release(self, job_id: str) -> None:
        self._q.put(job_id)


# === file backend =========================================================


class FileJobStore(JobStore):
    """One JSON file per job under ``<root>/jobs/``. Writes are atomic."""

    def __init__(self, root: Path | str) -> None:
        self._dir = Path(root) / "jobs"
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_id: str) -> Path:
        return self._dir / f"{job_id}.json"

    def create(self, job: Job) -> None:
        if self._path(job.id).exists():
            raise ValueError(f"job {job.id} already exists")
        self._write(job)

    def get(self, job_id: str) -> Job | None:
        path = self._path(job_id)
        if not path.exists():
            return None
        return Job.model_validate_json(path.read_text("utf-8"))

    def save(self, job: Job) -> None:
        self._write(job)

    def _write(self, job: Job) -> None:
        path = self._path(job.id)
        tmp = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
        tmp.write_text(job.model_dump_json(indent=2), "utf-8")
        tmp.replace(path)  # atomic on the same filesystem

    def clear(self) -> None:
        """Drop every job. Used by tests."""
        for path in self._dir.glob("*.json"):
            path.unlink(missing_ok=True)


class FileJobQueue(JobQueue):
    """A directory queue under ``<root>/queue/``.

    ``enqueue`` writes a file into ``ready/`` named with a nanosecond timestamp
    so listing sorts oldest-first. ``claim`` renames one file into ``inflight/``;
    the rename is atomic, so if two workers race, exactly one wins. ``ack``
    deletes the inflight file; ``release`` moves it to the back of ``ready/``.

    Unlike Queue Storage there is no visibility timeout: an id claimed by a
    worker that is killed stays in ``inflight/`` until someone moves it back.
    """

    def __init__(self, root: Path | str) -> None:
        base = Path(root) / "queue"
        self._ready = base / "ready"
        self._inflight = base / "inflight"
        self._last_ns = 0
        self._ready.mkdir(parents=True, exist_ok=True)
        self._inflight.mkdir(parents=True, exist_ok=True)

    def enqueue(self, job_id: str) -> None:
        entry = self._ready / self._entry_name(job_id)
        entry.write_text(job_id, "utf-8")

    def _entry_name(self, job_id: str) -> str:
        # The clock can be coarse (Windows), so keep this process's names
        # strictly increasing - otherwise same-tick entries sort by job id.
        self._last_ns = max(time.time_ns(), self._last_ns + 1)
        return f"{self._last_ns:020d}-{job_id}"

    def claim(self, timeout: float | None = None) -> str | None:
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            for entry in sorted(self._ready.iterdir()):
                target = self._inflight / entry.name
                try:
                    entry.rename(target)
                except OSError:
                    continue  # another worker took it, or it vanished
                return target.read_text("utf-8")
            if timeout == 0 or (deadline is not None and time.monotonic() >= deadline):
                return None
            time.sleep(0.2)

    def ack(self, job_id: str) -> None:
        for entry in self._inflight_entries(job_id):
            entry.unlink(missing_ok=True)

    def release(self, job_id: str) -> None:
        # A fresh timestamp puts it behind jobs that haven't had a go yet.
        for entry in self._inflight_entries(job_id):
            entry.rename(self._ready / self._entry_name(job_id))

    def _inflight_entries(self, job_id: str) -> list[Path]:
        return [e for e in self._inflight.iterdir() if e.name.endswith(f"-{job_id}")]

    def clear(self) -> None:
        """Drop every queued and in-flight id. Used by tests."""
        for folder in (self._ready, self._inflight):
            for entry in folder.iterdir():
                entry.unlink(missing_ok=True)


# === selection ============================================================


def _make_store(backend: str, state_dir: Path | str) -> JobStore:
    if backend == "azure":
        from gtab.azure_storage import make_job_store  # loads the Azure SDK

        return make_job_store()
    if backend == "file":
        return FileJobStore(state_dir)
    if backend == "memory":
        return InMemoryJobStore()
    raise ValueError(f"unknown jobs backend {backend!r}")


def _make_queue(backend: str, state_dir: Path | str) -> JobQueue:
    if backend == "azure":
        from gtab.azure_storage import make_job_queue  # loads the Azure SDK

        return make_job_queue()
    if backend == "file":
        return FileJobQueue(state_dir)
    if backend == "memory":
        return InMemoryJobQueue()
    raise ValueError(f"unknown jobs backend {backend!r}")


_store: JobStore | None = None
_queue: JobQueue | None = None


def configure(backend: str, state_dir: Path | str | None = None) -> None:
    """(Re)build the module-level store and queue. Used by tests and entrypoints."""
    global _store, _queue
    target = STATE_DIR if state_dir is None else state_dir
    _store = _make_store(backend, target)
    _queue = _make_queue(backend, target)


def __getattr__(name: str) -> object:
    # Lazily build the default store/queue on first access, so importing this
    # module has no side effects (the file backend would otherwise mkdir on
    # import, including during unrelated tests).
    global _store, _queue
    if name == "job_store":
        if _store is None:
            _store = _make_store(JOBS_BACKEND, STATE_DIR)
        return _store
    if name == "job_queue":
        if _queue is None:
            _queue = _make_queue(JOBS_BACKEND, STATE_DIR)
        return _queue
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
