"""Recover pinned public Git bytes locally. No exchange HTTP or wallet execution."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import zipfile

DATA_COMMIT = "542ce02443810b9feaa15e3114b3af8d6583dc4f"
RESULT_COMMIT = "b021710e1aa3d798352a01c763825be21e1558e8"
DATA_PATH = "research/okx-forward-coverage-20261009"
LAYERS = ("transport-prefix-d15-768k", "transport-delta-after-d15-768k",
          "transport-gap-resolution-768k")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git_bytes(repo, commit, path):
    return subprocess.check_output(["git", "-C", str(repo), "show", f"{commit}:{path}"])


def checked(data, sha256, size=None):
    if digest(data) != sha256 or (size is not None and len(data) != size):
        raise ValueError("Published byte identity differs")
    return data


def safe(root, relative):
    p = PurePosixPath(relative)
    if p.is_absolute() or not p.parts or ".." in p.parts:
        raise ValueError("Relative archive paths required")
    path = root.joinpath(*p.parts)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Archive path escapes destination")
    return path


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"Recovery refuses to overwrite different bytes: {path}")
    else:
        with path.open("xb") as stream:
            stream.write(data)


def recover_data(repo, destination):
    root = destination / "okx86"
    active = root / "selected"
    records = []
    # Original bytes stay separately in each layer. Only the two declared
    # shared metadata files change in the selected view; main shards never do.
    overlays = {"minute-intake/COVERAGE.json", "minute-intake/FINAL_AUDIT.json"}
    selected_hashes = {}
    for layer in LAYERS:
        base = f"{DATA_PATH}/minute-intake/{layer}"
        raw_index = git_bytes(repo, DATA_COMMIT, base + "/INDEX.json")
        index = json.loads(raw_index)
        save(root / "transport" / layer / "INDEX.json", raw_index)
        bundles = index.get("bundles", index.get("delta_bundles"))
        for entry in bundles:
            relative_manifest = entry["manifest"]
            raw = checked(git_bytes(repo, DATA_COMMIT, base + "/" + relative_manifest),
                          entry["manifest_sha256"])
            manifest = json.loads(raw)
            save(safe(root / "transport" / layer, relative_manifest), raw)
            parent = str(PurePosixPath(relative_manifest).parent)
            parts = sorted(manifest["parts"], key=lambda p: p["order"])
            if [p["order"] for p in parts] != list(range(len(parts))):
                raise ValueError("Transport part ordering differs")
            archive = b"".join(checked(git_bytes(repo, DATA_COMMIT,
                base + "/" + parent + "/" + p["path"]), p["sha256"], p["bytes"])
                for p in parts)
            checked(archive, entry["bundle_sha256"], entry["compressed_bytes"])
            expected = {m["path"]: m for m in manifest["members"]}
            if len(expected) != len(manifest["members"]):
                raise ValueError("Duplicate member binding")
            seen = set()
            with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
                for member in tar:
                    if not member.isfile() or member.name not in expected or member.name in seen:
                        raise ValueError("Only exact declared ordinary archive members allowed")
                    proof = expected[member.name]
                    data = checked(tar.extractfile(member).read(), proof["sha256"], proof["bytes"])
                    save(safe(root / "layers" / layer, member.name), data)
                    path = safe(active, member.name)
                    previous = selected_hashes.get(member.name)
                    conflict = path.exists() and digest(path.read_bytes()) != proof["sha256"]
                    if conflict or (previous is not None and previous != proof["sha256"]):
                        if member.name not in overlays:
                            raise ValueError("Normalized input overlap is prohibited")
                        path.unlink()  # layer copy above remains immutable
                    save(path, data)
                    selected_hashes[member.name] = proof["sha256"]
                    seen.add(member.name)
            if seen != set(expected):
                raise ValueError("Transport archive member set differs")
            records.append(dict(layer=layer, instrument_id=entry["instrument_id"],
                manifest=relative_manifest, manifest_sha256=entry["manifest_sha256"],
                bundle_sha256=entry["bundle_sha256"], verified_parts=len(parts),
                verified_members=len(seen), compressed_bytes=len(archive)))
            print(json.dumps(records[-1]), flush=True)
    # Use current public metadata without replacing any original layer copy.
    names = subprocess.check_output(["git", "-C", str(repo), "ls-tree", "-r", "--name-only",
                                     DATA_COMMIT, DATA_PATH], text=True).splitlines()
    extra = []
    for name in names:
        relative = str(PurePosixPath(name).relative_to(DATA_PATH))
        if "/transport" in relative:
            continue
        # Direct public files include the official retained archive, receipts,
        # policy, complete-window audit and daily/funding provenance.
        data = git_bytes(repo, DATA_COMMIT, name)
        save(safe(root / "published", relative), data)
        path = safe(active, relative)
        if path.exists() and path.read_bytes() != data:
            if relative not in overlays and relative not in {"minute-intake/SHA256SUMS"}:
                raise ValueError("Unexpected direct-file/transport conflict: " + relative)
            path.unlink()
        save(path, data)
        extra.append(dict(path=relative, sha256=digest(data), bytes=len(data)))
    report = dict(schema="OFFLINE_OKX86_BYTE_RECOVERY_V1", repository="snowycat1234/coin",
                  data_commit=DATA_COMMIT, bundles=records, direct_files=extra,
                  original_layers_preserved=True, provider_downloads=0,
                  selected_path="okx86/selected", wallets_run=0)
    save(root / "RECOVERY.json", (json.dumps(report, indent=2) + "\n").encode())
    return report


def recover_results(repo, destination):
    reports = []
    for days in (44, 41):
        base = f"research/okx{days}-native-results-20261009"
        root = destination / f"reference{days}"
        artifact_raw = git_bytes(repo, RESULT_COMMIT, base + "/ARTIFACT.json")
        artifact = json.loads(artifact_raw)
        data = b"".join(checked(git_bytes(repo, RESULT_COMMIT, base + "/" + p["path"]),
                               p["sha256"], p["bytes"]) for p in artifact["parts"])
        checked(data, artifact["sha256"], artifact["bytes"])
        save(root / "ARTIFACT.json", artifact_raw)
        manifest_raw = git_bytes(repo, RESULT_COMMIT, base + "/MANIFEST.json")
        manifest = json.loads(manifest_raw)
        save(root / "MANIFEST.json", manifest_raw)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if z.testzip() is not None:
                raise ValueError("Result archive CRC differs")
            for n in z.namelist():
                if not n.endswith("/"):
                    save(safe(root, n), z.read(n))
        for entry in manifest["files"]:
            checked(safe(root, entry["path"]).read_bytes(), entry["public_sha256"], entry["bytes"])
        for n in ("README.md", "FINANCIAL_CONFIG.json", "SOURCE_REFERENCES.json", "verify_results.py"):
            save(root / n, git_bytes(repo, RESULT_COMMIT, base + "/" + n))
        reports.append(dict(days=days, artifact_sha256=artifact["sha256"],
                            verified_members=len(manifest["files"]), result_path=f"reference{days}"))
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    data = recover_data(args.repo, args.destination)
    references = recover_results(args.repo, args.destination)
    print(json.dumps(dict(bundles=len(data["bundles"]), references=references, wallets_run=0)))


if __name__ == "__main__":
    main()
