"""Deterministic small binary transport parts; source ZIP bytes stay immutable."""

import argparse
import hashlib
import json
from pathlib import Path

MAX_PART_BYTES = 1_500_000


def digest(body):
    return hashlib.sha256(body).hexdigest()


def split(path: Path):
    assert path.name.startswith("oi-daily-") and path.name.endswith("-raw.zip")
    body = path.read_bytes()
    parts = []
    for index, offset in enumerate(range(0, len(body), MAX_PART_BYTES)):
        part = body[offset : offset + MAX_PART_BYTES]
        target = path.with_name(f"{path.name}.part{index:03d}.bin")
        if target.exists():
            assert target.read_bytes() == part, "Never overwrite a conflicting existing part"
        else:
            temp = target.with_name(target.name + ".tmp")
            temp.write_bytes(part)
            temp.replace(target)
        parts.append(
            dict(
                index=index,
                filename=target.name,
                offset_bytes=offset,
                bytes=len(part),
                SHA256=digest(part),
            )
        )
    assert b"".join(path.with_name(r["filename"]).read_bytes() for r in parts) == body
    manifest = dict(
        schema="DETERMINISTIC_BINARY_ZIP_CONCAT_V1",
        original_filename=path.name,
        original_bytes=len(body),
        original_SHA256=digest(body),
        max_part_bytes=MAX_PART_BYTES,
        restore=(
            "Concatenate complete part bodies in ascending listed index. Verify each part "
            "SHA256 and the final original byte count/SHA256 before opening the restored ZIP."
        ),
        parts=parts,
    )
    target = path.with_name(path.name + ".PARTS.json")
    text = json.dumps(manifest, indent=2) + "\n"
    if target.exists():
        assert target.read_text() == text, "Never overwrite a conflicting manifest"
    else:
        target.write_text(text)
    return target, manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("zip", type=Path)
    args = parser.parse_args()
    path, result = split(args.zip)
    print(json.dumps(dict(manifest_path=str(path), **result), indent=2))
