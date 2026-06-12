"""Valida StorageBackend y StorageManager."""

import pytest

from pds_core.config.schema.clients_schema import StorageConfig, StorageLocation
from pds_core.integration.storage import LocalBackend, StorageManager


@pytest.fixture
def local_backend(tmp_path):
    return LocalBackend(tmp_path)


def test_local_backend_write_read(local_backend):
    local_backend.write("test/data.txt", b"hello")
    assert local_backend.read("test/data.txt") == b"hello"


def test_local_backend_exists_list_delete(local_backend):
    local_backend.write("a.txt", b"1")
    local_backend.write("b.txt", b"2")
    assert local_backend.exists("a.txt")
    assert "a.txt" in local_backend.list("")
    local_backend.delete("a.txt")
    assert not local_backend.exists("a.txt")


def test_local_backend_read_missing_raises(local_backend):
    with pytest.raises(FileNotFoundError):
        local_backend.read("missing.txt")


def test_storage_manager_delegates(tmp_path):
    base = tmp_path / "storage"
    config = StorageConfig(
        entrada_canonica=StorageLocation(nombre="e", provider="local", local_path=str(base / "in")),
        entrada_materializada=StorageLocation(nombre="m", provider="local", local_path=str(base / "mat")),
        salidas=StorageLocation(nombre="s", provider="local", local_path=str(base / "out")),
        logs=StorageLocation(nombre="l", provider="local", local_path=str(base / "logs")),
    )
    mgr = StorageManager(config)
    mgr.write_salidas("tracker.txt", b"data")
    assert mgr.read_salidas("tracker.txt") == b"data"
    assert mgr.salidas.exists("tracker.txt")
