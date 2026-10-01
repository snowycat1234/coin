from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from quant.disk import GB, enforce, tree_bytes


def test_reservations_preserve_emergency_buffer():
    assert enforce(31 * GB, 0, 10 * GB) == "OK"
    assert enforce(32 * GB, 0, 10 * GB) == "WARNING"
    with pytest.raises(RuntimeError, match="36 GB"):
        enforce(35 * GB, GB, 10 * GB)
    with pytest.raises(RuntimeError, match="40 GB"):
        enforce(39 * GB, GB, 10 * GB)
    with pytest.raises(RuntimeError, match="free-space"):
        enforce(4 * GB, GB, 4 * GB)


def test_disk_guard_rejects_external_symlink(tmp_path):
    external = tmp_path.parent / "external-disk-test.txt"
    external.write_text("abc")
    (tmp_path / "escape").symlink_to(external)
    with pytest.raises(RuntimeError, match="symlink"):
        tree_bytes(tmp_path)
    external.unlink()


def test_atomic_file_replacement_during_ledger_scan_is_not_fatal(tmp_path, monkeypatch):
    class Entry:
        def __init__(self, vanished):
            self.vanished = vanished

        def is_symlink(self):
            return False

        def is_dir(self, **kwargs):
            return False

        def is_file(self, **kwargs):
            return True

        def stat(self, **kwargs):
            if self.vanished:
                raise FileNotFoundError("atomic temporary renamed")
            return SimpleNamespace(st_size=123)

    @contextmanager
    def scan(path):
        yield [Entry(True), Entry(False)]

    monkeypatch.setattr("quant.disk.os.scandir", scan)
    assert tree_bytes(tmp_path) == 123


def test_permission_error_is_still_fail_closed(tmp_path, monkeypatch):
    @contextmanager
    def scan(path):
        raise PermissionError("permission failure")
        yield []

    monkeypatch.setattr("quant.disk.os.scandir", scan)
    with pytest.raises(PermissionError):
        tree_bytes(tmp_path)

