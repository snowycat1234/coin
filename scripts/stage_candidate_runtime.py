"""Copy exact source bytes into a D-hosted native immutable engineering runtime."""

from __future__ import annotations

import hashlib
import json

from quant import disk
from quant.paths import ROOT, STATE
from quant.resources import status


def main():
    status()
    disk.check(reserve=20_000_000)
    source = ROOT / "src/quant"
    files = sorted(source.glob("*.py"))
    if not files or any(path.is_symlink() for path in files):
        raise RuntimeError("Regular complete quant sources required")
    data = {path.name: path.read_bytes() for path in files}
    total = sum(map(len, data.values()))
    if total > 8_000_000 or len(data) > 200:
        raise RuntimeError("Native source snapshot exceeds bounded allocation")
    hashes = {name: hashlib.sha256(value).hexdigest() for name, value in data.items()}
    release = hashlib.sha256(
        json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    target = STATE / "candidate-runtime" / release
    manifest_path = target / "SOURCE_MANIFEST.json"
    manifest = {"scope": "exact_source_snapshot_engineering_only",
                "release_sha256": release, "source_root": str(source),
                "runtime_root": str(target), "files": hashes, "source_bytes": total,
                "no_training": True, "no_live_admission": True}
    if target.exists():
        if json.loads(manifest_path.read_text()) != manifest:
            raise RuntimeError("Existing native snapshot identity differs")
    else:
        package = target / "quant"
        package.mkdir(parents=True)
        for name, value in data.items():
            path = package / name
            with path.open("xb") as writer:
                writer.write(value)
            path.chmod(0o444)
        with manifest_path.open("x", encoding="utf-8") as writer:
            writer.write(json.dumps(manifest, indent=2) + "\n")
        manifest_path.chmod(0o444)
    for name, expected in hashes.items():
        for path in (source / name, target / "quant" / name):
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise RuntimeError("Source/runtime snapshot changed while staging")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
