"""Azure Storage backends for the seams in `gtab.jobs` and `gtab.uploads`.

* `TableJobStore`  - one Table Storage entity per job.
* `QueueJobQueue`  - job ids as Queue Storage messages.
* `BlobUploadStore` - uploads as blobs in one container.

Selected with ``GTAB_JOBS_BACKEND=azure``. Locally they talk to Azurite through
a connection string; in Azure they sign in with a managed identity (see
`gtab.config`). `gtab.jobs` and `gtab.uploads` import this module only when the
azure backend is picked, so the other backends never load the SDK.

The container, table and queue are created on first use if they are missing,
so a fresh Azurite needs no setup. In Azure, Terraform should own them; if the
identity isn't allowed to create them that step is skipped.
"""

from __future__ import annotations

import logging
import threading
import time
from functools import cache
from pathlib import Path
from typing import BinaryIO

from azure.core.exceptions import (
    HttpResponseError,
    ResourceExistsError,
    ResourceNotFoundError,
)
from azure.data.tables import TableServiceClient, UpdateMode
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueServiceClient

from gtab import config
from gtab.jobs import JobQueue, JobStore
from gtab.models import Job
from gtab.uploads import UploadNotFoundError, UploadStore, check_upload_name

logger = logging.getLogger(__name__)

# The SDK logs every request and response at INFO - with a worker polling the
# queue that drowns out everything else.
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)


# === clients ==============================================================


@cache
def _credential():
    # Imported here: only needed without a connection string.
    from azure.identity import DefaultAzureCredential

    return DefaultAzureCredential()


def _account_url(service: str) -> str:
    if not config.AZURE_STORAGE_ACCOUNT:
        raise ValueError(
            "GTAB_JOBS_BACKEND=azure needs GTAB_AZURE_STORAGE_CONNECTION_STRING "
            "or GTAB_AZURE_STORAGE_ACCOUNT"
        )
    return f"https://{config.AZURE_STORAGE_ACCOUNT}.{service}.core.windows.net"


def blob_service() -> BlobServiceClient:
    if config.AZURE_STORAGE_CONNECTION_STRING:
        return BlobServiceClient.from_connection_string(config.AZURE_STORAGE_CONNECTION_STRING)
    return BlobServiceClient(_account_url("blob"), credential=_credential())


def queue_service() -> QueueServiceClient:
    if config.AZURE_STORAGE_CONNECTION_STRING:
        return QueueServiceClient.from_connection_string(config.AZURE_STORAGE_CONNECTION_STRING)
    return QueueServiceClient(_account_url("queue"), credential=_credential())


def table_service() -> TableServiceClient:
    if config.AZURE_STORAGE_CONNECTION_STRING:
        return TableServiceClient.from_connection_string(config.AZURE_STORAGE_CONNECTION_STRING)
    return TableServiceClient(endpoint=_account_url("table"), credential=_credential())


def _create_if_missing(create, what: str) -> None:
    try:
        create()
    except ResourceExistsError:
        pass
    except HttpResponseError as exc:
        if exc.status_code != 403:
            raise
        # Allowed to use it but not to create it - it has to exist already.
        logger.info("not allowed to create %s - assuming it exists", what)


# === job store ============================================================


class TableJobStore(JobStore):
    """One entity per job, in a single partition.

    The job is stored as its JSON, split over ``data_0``, ``data_1``, ... because
    a string property holds at most 32K characters and a long clip's tab can be
    bigger than that (an entity tops out at 1 MiB). ``status`` is copied into its
    own property so the table is readable in the portal / Storage Explorer.
    """

    PARTITION = "job"
    CHUNK = 30_000

    def __init__(self, service: TableServiceClient, table: str) -> None:
        _create_if_missing(lambda: service.create_table(table), f"table {table!r}")
        self._table = service.get_table_client(table)

    def create(self, job: Job) -> None:
        try:
            self._table.create_entity(self._entity(job))
        except ResourceExistsError:
            raise ValueError(f"job {job.id} already exists") from None

    def get(self, job_id: str) -> Job | None:
        try:
            entity = self._table.get_entity(self.PARTITION, job_id)
        except ResourceNotFoundError:
            return None
        chunks = []
        while (chunk := entity.get(f"data_{len(chunks)}")) is not None:
            chunks.append(chunk)
        return Job.model_validate_json("".join(chunks))

    def save(self, job: Job) -> None:
        # REPLACE, not MERGE, so a shorter job doesn't keep stale chunks.
        self._table.upsert_entity(self._entity(job), mode=UpdateMode.REPLACE)

    def _entity(self, job: Job) -> dict[str, str]:
        data = job.model_dump_json()
        entity = {"PartitionKey": self.PARTITION, "RowKey": job.id, "status": job.status}
        for i in range(0, len(data), self.CHUNK):
            entity[f"data_{i // self.CHUNK}"] = data[i : i + self.CHUNK]
        return entity


# === job queue ============================================================


class QueueJobQueue(JobQueue):
    """Job ids as Queue Storage messages.

    ``claim`` receives a message, which hides it from other workers for
    `visibility_timeout` seconds rather than removing it. ``ack`` deletes it;
    ``release`` puts the id back at the end of the queue. If the worker dies, the
    message reappears by itself once the timeout runs out - the redelivery the
    `JobQueue` contract asks for.

    Deleting or updating a message needs the pop receipt from the receive, so
    this object remembers the receipts of the ids it has claimed. Only the
    worker that claimed an id can ack or release it, as with the other backends.

    Queue Storage has no blocking receive, so ``claim`` polls.
    """

    POLL_INTERVAL = 1.0

    def __init__(self, service: QueueServiceClient, queue: str, visibility_timeout: int) -> None:
        _create_if_missing(lambda: service.create_queue(queue), f"queue {queue!r}")
        self._queue = service.get_queue_client(queue)
        self._visibility_timeout = visibility_timeout
        self._claimed: dict[str, tuple[str, str]] = {}  # job id -> (message id, pop receipt)
        self._lock = threading.Lock()

    def enqueue(self, job_id: str) -> None:
        self._queue.send_message(job_id)

    def claim(self, timeout: float | None = None) -> str | None:
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            msg = self._queue.receive_message(visibility_timeout=self._visibility_timeout)
            if msg is not None:
                with self._lock:
                    self._claimed[msg.content] = (msg.id, msg.pop_receipt)
                return msg.content
            if timeout == 0:
                return None
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                time.sleep(min(self.POLL_INTERVAL, remaining))
            else:
                time.sleep(self.POLL_INTERVAL)

    def ack(self, job_id: str) -> None:
        receipt = self._take(job_id)
        if receipt is None:
            return
        try:
            self._queue.delete_message(*receipt)
        except HttpResponseError as exc:
            self._lost(job_id, exc)

    def release(self, job_id: str) -> None:
        # Re-send then delete, rather than just un-hiding the message, so the
        # id goes to the back of the queue behind jobs that haven't had a go.
        # Send first: dying in between means a duplicate (the worker skips a
        # finished job), not a lost job.
        receipt = self._take(job_id)
        if receipt is None:
            return
        self._queue.send_message(job_id)
        try:
            self._queue.delete_message(*receipt)
        except HttpResponseError as exc:
            self._lost(job_id, exc)

    def _take(self, job_id: str) -> tuple[str, str] | None:
        with self._lock:
            receipt = self._claimed.pop(job_id, None)
        if receipt is None:
            logger.warning("job %s was not claimed by this worker - ignoring", job_id)
        return receipt

    @staticmethod
    def _lost(job_id: str, exc: HttpResponseError) -> None:
        # The visibility timeout ran out mid-job, so the message was handed to
        # someone else (new pop receipt) or they already finished it.
        if exc.status_code in (400, 404):
            logger.warning(
                "job %s: queue message changed hands before we finished (%s) - "
                "raise GTAB_AZURE_QUEUE_VISIBILITY_TIMEOUT if jobs run this long",
                job_id, exc.error_code,
            )
            return
        raise exc

    def clear(self) -> None:
        """Drop every message. Used by tests."""
        self._queue.clear_messages()
        with self._lock:
            self._claimed.clear()


# === upload store =========================================================


class BlobUploadStore(UploadStore):
    """Uploads as blobs in one container, named as the API names them."""

    def __init__(self, service: BlobServiceClient, container: str) -> None:
        _create_if_missing(
            lambda: service.create_container(container), f"container {container!r}"
        )
        self._container = service.get_container_client(container)

    def put(self, name: str, data: BinaryIO) -> None:
        check_upload_name(name)
        self._container.upload_blob(name, data, overwrite=True)

    def download_to(self, name: str, dest: Path) -> None:
        check_upload_name(name)
        try:
            downloader = self._container.download_blob(name)
        except ResourceNotFoundError:
            raise UploadNotFoundError(f"upload {name!r} not found") from None
        with dest.open("wb") as out:
            downloader.readinto(out)

    def delete(self, name: str) -> None:
        check_upload_name(name)
        try:
            self._container.delete_blob(name)
        except ResourceNotFoundError:
            pass


# === factories used by gtab.jobs / gtab.uploads ===========================


def make_job_store() -> TableJobStore:
    return TableJobStore(table_service(), config.AZURE_JOB_TABLE)


def make_job_queue() -> QueueJobQueue:
    return QueueJobQueue(
        queue_service(), config.AZURE_JOB_QUEUE, config.AZURE_QUEUE_VISIBILITY_TIMEOUT
    )


def make_upload_store() -> BlobUploadStore:
    return BlobUploadStore(blob_service(), config.AZURE_UPLOAD_CONTAINER)
