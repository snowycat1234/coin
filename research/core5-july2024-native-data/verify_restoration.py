"""Verify byte-identical canonical restoration from immutable remote originals."""

import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-root", type=Path, required=True)
    parser.add_argument("--restored-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    original = json.loads((args.original_root / "JULY2024/VALIDATION.json").read_text())
    restored = json.loads((args.restored_root / "JULY2024/VALIDATION.json").read_text())
    remote = json.loads((args.restored_root / "REMOTE_RECOVERY.json").read_text())
    assert remote["status"] == "REMOTE_IMMUTABLE_SHA_AND_ORIGINAL_BYTE_RECOVERY_VERIFIED"
    assert remote["every_original_official_SHA_and_ZIP_CRC_verified"] is True
    assert remote["recovered_original_archive_count"] == 60
    for key in (
        "derived_artifacts", "coverage", "supplement_checks", "protocol_SHA256",
        "normalization_source_SHA256", "execution_and_held_funding_ready",
        "native_minute_grid_complete", "paid_close_UTC", "symbols_order", "status",
    ):
        assert original[key] == restored[key], key
    assert restored["execution_and_held_funding_ready"] is True
    assert restored["native_minute_grid_complete"] is False
    for artifact in original["derived_artifacts"]:
        for root in (args.original_root, args.restored_root):
            path = root / "JULY2024" / artifact["path"]
            assert path.stat().st_size == artifact["bytes"], str(path)
            assert digest(path) == artifact["SHA256"], str(path)
    receipt = {
        "status": "REMOTE_CANONICAL_RESTORATION_BYTE_IDENTICAL",
        "immutable_source_commit": remote["commit"],
        "remote_parts_verified": remote["part_count"],
        "original_archives_verified": remote["recovered_original_archive_count"],
        "canonical_artifacts_verified": len(original["derived_artifacts"]),
        "every_canonical_artifact_size_and_SHA256_identical": True,
        "coverage_and_supplement_evidence_identical": True,
        "execution_and_held_funding_ready": True,
        "native_minute_grid_complete": False,
        "coverage": restored["coverage"],
        "economic_array_SHA256": next(
            a["SHA256"] for a in restored["derived_artifacts"] if a["path"] == "ECONOMICS.npz"
        ),
        "additional_official_archive_downloads": 0,
    }
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k != "coverage"}, indent=2))


if __name__ == "__main__":
    main()
