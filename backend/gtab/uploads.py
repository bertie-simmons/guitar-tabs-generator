"""Where uploaded videos live between the API receiving them and the Worker
processing them.

API `put`s the upload under name and records that name in `Job.source_path`.
The Worker `download_to`s a temp file, and `delete`s the upload once the job is finished. 
Neither side knows whether the name is a file on a shared volume or a blob in a container.
"""

from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO

from gtab.config import JOBS_BACKEND, UPLOAD_DIR


class UploadNotFoundError(LookupError):
    """There is no upload with that name. Retrying will not make one appear."""


class UploadStore(ABC):
    """Store, fetch and remove uploaded files by name."""

    @abstractmethod
    def put(self, name: str, data: BinaryIO) -> None:
        """Store the contents of `data` under `name`, streaming it."""

    @abstractmethod
    def download_to(self, name: str, dest: Path) -> None:
        """Copy the upload `name` to the local file `dest`.

        Raises `UploadNotFoundError` if there is no such upload.
        """

    @abstractmethod
    def delete(self, name: str) -> None:
        """Remove the upload `name`. Does nothing if it is already gone."""


class LocalUploadStore(UploadStore):
    """Uploads as plain files in one directory."""

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, name: str) -> Path:
        # Names are built by the API from a uuid, but refuse anything that
        # would step outside the directory all the same.
        if not name or Path(name).name != name:
            raise ValueError(f"invalid upload name {name!r}")
        return self._root / name

    def put(self, name: str, data: BinaryIO) -> None:
        with self._path(name).open("wb") as out:
            shutil.copyfileobj(data, out)

    def download_to(self, name: str, dest: Path) -> None:
        try:
            with self._path(name).open("rb") as src, dest.open("wb") as out:
                shutil.copyfileobj(src, out)
        except FileNotFoundError:
            raise UploadNotFoundError(f"upload {name!r} not found") from None

    def delete(self, name: str) -> None:
        self._path(name).unlink(missing_ok=True)


# === selection ============================================================


def _make_store(backend: str, root: Path | str) -> UploadStore:
    # "memory" and "file" both keep uploads on local disk
    return LocalUploadStore(root)


_store: UploadStore | None = None


def configure(backend: str, root: Path | str | None = None) -> None:
    """Build the module-level upload store. Used by tests and entrypoints."""
    global _store
    _store = _make_store(backend, UPLOAD_DIR if root is None else root)


def __getattr__(name: str) -> object:
    # lazy load
    global _store
    if name == "upload_store":
        if _store is None:
            _store = _make_store(JOBS_BACKEND, UPLOAD_DIR)
        return _store
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
