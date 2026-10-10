"""Publication transport exactness, not a dataset transformation."""

import hashlib
import json

import chunks
import pytest


def test_parts_restore_original_and_resume_identically(tmp_path):
    body = bytes(range(256)) * 11719
    original = tmp_path / "oi-daily-2022Q3-raw.zip"
    original.write_bytes(body)
    path, manifest = chunks.split(original)
    assert len(manifest["parts"]) == 3
    assert all(r["bytes"] <= 1_500_000 for r in manifest["parts"])
    restored = b"".join((tmp_path / r["filename"]).read_bytes() for r in manifest["parts"])
    assert restored == original.read_bytes() == body
    assert hashlib.sha256(restored).hexdigest() == manifest["original_SHA256"]
    assert json.loads(path.read_text()) == manifest
    assert chunks.split(original) == (path, manifest)


def test_conflicting_existing_part_is_never_overwritten(tmp_path):
    original = tmp_path / "oi-daily-2022Q3-raw.zip"
    original.write_bytes(b"original")
    part = tmp_path / "oi-daily-2022Q3-raw.zip.part000.bin"
    part.write_bytes(b"different")
    with pytest.raises(AssertionError):
        chunks.split(original)
    assert part.read_bytes() == b"different"
