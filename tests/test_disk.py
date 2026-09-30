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

