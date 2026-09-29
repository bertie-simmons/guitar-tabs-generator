"""The upload store contract the API and worker rely on."""

import io

import pytest

from gtab.uploads import LocalUploadStore, UploadNotFoundError


@pytest.fixture
def store(tmp_path):
    return LocalUploadStore(tmp_path / "uploads")


def test_put_then_download_roundtrips(store, tmp_path):
    store.put("j1.mp4", io.BytesIO(b"video bytes"))
    store.download_to("j1.mp4", tmp_path / "copy.mp4")
    assert (tmp_path / "copy.mp4").read_bytes() == b"video bytes"


def test_download_missing_raises(store, tmp_path):
    with pytest.raises(UploadNotFoundError):
        store.download_to("nope.mp4", tmp_path / "copy.mp4")


def test_delete_removes_and_tolerates_missing(store, tmp_path):
    store.put("j1.mp4", io.BytesIO(b"x"))
    store.delete("j1.mp4")
    store.delete("j1.mp4")  # already gone - no error
    with pytest.raises(UploadNotFoundError):
        store.download_to("j1.mp4", tmp_path / "copy.mp4")


@pytest.mark.parametrize("name", ["", "../escape.mp4", "sub/dir.mp4"])
def test_rejects_names_outside_the_directory(store, name):
    with pytest.raises(ValueError, match="invalid upload name"):
        store.put(name, io.BytesIO(b"x"))
