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


def test_stopped_bundle_preserves_partial_proof_without_certifying_it(tmp_path, monkeypatch):
    instrument = "BTC-USDT-SWAP"
    complete = dict(
        instrument_id=instrument,
        date="complete",
        status="COMPLETE",
        start_ms=0,
        end_ms_exclusive=60000,
        manifest=instrument + "/complete.manifest.json",
        bars_files={kind: instrument + "/complete." + kind for kind in ("trade", "mark")},
        responses_file=instrument + "/complete.responses",
        coverage={kind: dict(observed_bars=1) for kind in ("trade", "mark")},
    )
    partial = dict(
        complete,
        date="partial",
        status="INCOMPLETE_COVERAGE",
        start_ms=60000,
        end_ms_exclusive=120000,
        manifest=instrument + "/partial.manifest.json",
    )
    index = dict(shards=[complete, partial], witnesses=[], status="INCOMPLETE_COVERAGE")
    parent_manifest = str(transport.ROOT / instrument / "manifest.json")
    blobs = {
        str(transport.PUBLIC_PREFIX / "COVERAGE.json"): json.dumps(index).encode(),
        parent_manifest: json.dumps(dict(identity=dict(instrument_id=instrument))).encode(),
    }

    def git_read(repo, commit, path):
        return blobs.get(str(path), b"original fixture bytes")

    def git_command(command, **kwargs):
        return "fixture\n" if "rev-parse" in command else parent_manifest + "\n"

    monkeypatch.setattr(transport, "git_bytes", git_read)
    monkeypatch.setattr(transport.subprocess, "check_output", git_command)
    result = transport.build(tmp_path, "fixture", instrument, tmp_path / "out")
    manifest = json.loads((tmp_path / "out" / result["manifest"]).read_text())
    assert result["complete_instrument_date_shards"] == 1
    assert result["incomplete_instrument_date_shards"] == 1
    assert manifest["verified_minute_rows"] == 2
    assert manifest["incomplete_shards"][0]["status"] == "INCOMPLETE_COVERAGE"
    assert any(member["path"].endswith("partial.manifest.json") for member in manifest["members"])
