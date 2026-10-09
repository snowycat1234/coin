"""One-pass transport verification with bounded parts and path rejection."""

import gzip
import hashlib
import io
import json
import tarfile

import pytest
from pipeline import okx_minute_transport as transport


def fixture_bundle(folder, name="BTC-USDT-SWAP/funding.jsonl"):
    content = b'{"realizedRate":"0.0001"}\n'
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        info = tarfile.TarInfo(name)
        info.size = len(content)
        archive.addfile(info, io.BytesIO(content))
    raw = gzip.compress(stream.getvalue(), mtime=0)
    digest = hashlib.sha256(raw).hexdigest()
    (folder / "part0000").write_bytes(raw)
    manifest = dict(
        bundle_sha256=digest,
        parts=[dict(order=0, path="part0000", bytes=len(raw), sha256=digest)],
        members=[dict(path=name, bytes=len(content), sha256=hashlib.sha256(content).hexdigest())],
    )
    (folder / "manifest.json").write_text(json.dumps(manifest))
    return content


def test_one_pass_extract_preserves_original_member(tmp_path):
    content = fixture_bundle(tmp_path)
    result = transport.verify_and_extract(tmp_path, tmp_path / "extracted")
    assert result["members"] == 1 and result["parts"] == 1
    assert (tmp_path / "extracted/BTC-USDT-SWAP/funding.jsonl").read_bytes() == content


def test_changed_transport_part_is_rejected_before_extraction(tmp_path):
    fixture_bundle(tmp_path)
    (tmp_path / "part0000").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        transport.verify_and_extract(tmp_path, tmp_path / "extracted")
    assert not (tmp_path / "extracted").exists()


def test_multiple_parts_reassembly_and_order_bound(tmp_path, monkeypatch):
    fixture_bundle(tmp_path)
    raw = (tmp_path / "part0000").read_bytes()
    monkeypatch.setattr(transport, "PART_BYTES", 64)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    parts = []
    for order, start in enumerate(range(0, len(raw), 64)):
        block, name = raw[start : start + 64], f"part{order:04d}"
        (tmp_path / name).write_bytes(block)
        parts.append(
            dict(order=order, path=name, bytes=len(block), sha256=hashlib.sha256(block).hexdigest())
        )
    manifest["parts"] = parts
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    assert transport.verify_and_extract(tmp_path)["parts"] == len(parts)
    manifest["parts"] = list(reversed(parts))
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="order"):
        transport.verify_and_extract(tmp_path)


@pytest.mark.parametrize("name", ["/absolute", "../outside", "a/../outside", "a//b"])
def test_traversal_and_noncanonical_member_paths_are_rejected(tmp_path, name):
    fixture_bundle(tmp_path, name)
    with pytest.raises(ValueError, match="path"):
        transport.verify_and_extract(tmp_path)
