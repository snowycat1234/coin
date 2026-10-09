"""Content-addressed transport of existing verified OKX research bytes; no HTTP."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

from .common import dump, sha256
from .okx_minute_intake import ASSETS, BRANCH, PARENT_COMMIT, PUBLIC_PREFIX
from .public_supplement import fingerprint

PART_BYTES = 4 * 1024 * 1024
ROOT = PUBLIC_PREFIX.parent


def safe_path(name):
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or any(p in ("", ".", "..") for p in path.parts):
        raise ValueError("Transport members require relative paths without traversal")
    if str(path) != name:
        raise ValueError("Noncanonical transport member path")
    return path


def git_bytes(repo, commit, path):
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=repo)


def verify_and_extract(folder, output=None):
    """Check ordered parts, aggregate and every extracted member in one pass."""
    folder = Path(folder)
    manifest = json.loads((folder / "manifest.json").read_text())
    members = manifest["members"]
    expected = {str(safe_path(m["path"])): m for m in members}
    if len(expected) != len(members):
        raise ValueError("Duplicate member")
    total = hashlib.sha256()
    with tempfile.TemporaryFile() as assembled:
        for number, part in enumerate(manifest["parts"]):
            name = str(safe_path(part["path"]))
            if "/" in name or part["order"] != number:
                raise ValueError("Part order/path mismatch")
            raw = (folder / name).read_bytes()
            if (
                not 0 < len(raw) <= PART_BYTES
                or len(raw) != part["bytes"]
                or hashlib.sha256(raw).hexdigest() != part["sha256"]
            ):
                raise ValueError("Part checksum/size mismatch")
            total.update(raw)
            assembled.write(raw)
        if total.hexdigest() != manifest["bundle_sha256"]:
            raise ValueError("Reassembled bundle checksum mismatch")
        assembled.seek(0)
        seen, verified_bytes = set(), 0
        with tarfile.open(fileobj=assembled, mode="r|gz") as archive:
            for member in archive:
                name = str(safe_path(member.name))
                if not member.isfile() or name not in expected or name in seen:
                    raise ValueError("Unexpected, duplicate or nonregular transport member")
                source = archive.extractfile(member)
                assert source is not None
                raw = source.read(expected[name]["bytes"] + 1)
                if (
                    len(raw) != expected[name]["bytes"]
                    or member.size != len(raw)
                    or hashlib.sha256(raw).hexdigest() != expected[name]["sha256"]
                ):
                    raise ValueError("Extracted source member checksum/size mismatch")
                if output is not None:
                    destination = Path(output) / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(raw)
                seen.add(name)
                verified_bytes += len(raw)
        if seen != set(expected):
            raise ValueError("Missing transport member")
    return dict(
        members=len(seen),
        verified_member_bytes=verified_bytes,
        parts=len(manifest["parts"]),
        bundle_sha256=total.hexdigest(),
    )


def build(repo, commit, instrument, output):
    """Snapshot only this public dataset from a fixed commit; never reread providers."""
    repo, output = Path(repo), Path(output)
    if instrument not in [asset + "-USDT-SWAP" for asset in ASSETS]:
        raise ValueError("Only authorized CORE5 native instruments")
    commit = subprocess.check_output(
        ["git", "rev-parse", "--verify", commit + "^{commit}"], cwd=repo, text=True
    ).strip()
    index = json.loads(git_bytes(repo, commit, PUBLIC_PREFIX / "COVERAGE.json"))
    shards = [s for s in index["shards"] if s["instrument_id"] == instrument]
    if not shards or any(s["status"] != "COMPLETE" for s in shards):
        raise ValueError("Bundle requires completed verified shards")
    for previous, current in zip(shards, shards[1:], strict=False):
        if previous["end_ms_exclusive"] != current["start_ms"]:
            raise ValueError("Bundle source shards are not contiguous")
    paths = [
        ROOT / "COVERAGE.json",
        ROOT / "SCHEMA.json",
        PUBLIC_PREFIX / "COVERAGE.json",
        PUBLIC_PREFIX / "SCHEMA.json",
    ]
    # Preserve the existing daily/funding/probe/native-metadata proofs as well.
    paths.extend(
        Path(name)
        for name in subprocess.check_output(
            ["git", "ls-tree", "-r", "--name-only", commit, "--", str(ROOT / instrument)],
            cwd=repo,
            text=True,
        ).splitlines()
    )
    for shard in shards:
        paths.extend(
            PUBLIC_PREFIX / name
            for name in (shard["manifest"], *shard["bars_files"].values(), shard["responses_file"])
        )
    for witness in index["witnesses"]:
        if witness["instrument_id"] == instrument:
            name = witness["manifest"]
            proof = json.loads(git_bytes(repo, commit, PUBLIC_PREFIX / name))
            paths.extend(
                PUBLIC_PREFIX / path
                for path in (name, *proof["bars_files"].values(), proof["responses_file"])
            )
    identity = json.loads(git_bytes(repo, commit, ROOT / instrument / "manifest.json"))["identity"]
    output.mkdir(parents=True, exist_ok=True)
    # Build outside the published artifacts tree, then atomically expose a verified bundle.
    with tempfile.TemporaryDirectory(dir=output.parent.parent) as scratch:
        scratch = Path(scratch)
        archive_path = scratch / "bundle.tar.gz"
        members = []
        with archive_path.open("wb") as stream:
            with gzip.GzipFile(fileobj=stream, mode="wb", filename="", mtime=0) as compressed:
                with tarfile.open(fileobj=compressed, mode="w|") as archive:
                    for path in sorted(set(paths)):
                        raw = git_bytes(repo, commit, path)
                        relative = str(path.relative_to(ROOT))
                        safe_path(relative)
                        info = tarfile.TarInfo(relative)
                        info.size, info.mode, info.mtime = len(raw), 0o644, 0
                        archive.addfile(info, io.BytesIO(raw))
                        members.append(
                            dict(
                                path=relative,
                                bytes=len(raw),
                                sha256=hashlib.sha256(raw).hexdigest(),
                                repository_path=str(path),
                                source_commit=commit,
                            )
                        )
        digest = sha256(archive_path)
        staged = scratch / digest
        staged.mkdir()
        parts = []
        with archive_path.open("rb") as stream:
            while raw := stream.read(PART_BYTES):
                name = f"{digest}.tar.gz.part{len(parts):04d}"
                (staged / name).write_bytes(raw)
                parts.append(
                    dict(
                        order=len(parts),
                        path=name,
                        bytes=len(raw),
                        sha256=hashlib.sha256(raw).hexdigest(),
                    )
                )
        manifest = dict(
            version="okx-minute-transport-1",
            dataset_role="OKX_ONLY_PUBLIC_OFFLINE_RESEARCH",
            repository="https://github.com/snowycat1234/coin",
            branch=BRANCH,
            snapshot_commit=commit,
            reused_input_commit=PARENT_COMMIT,
            transport_source_sha256=sha256(Path(__file__)),
            instrument_id=instrument,
            identity=identity,
            identity_sha256=fingerprint(identity),
            start_ms=shards[0]["start_ms"],
            end_ms_exclusive=shards[-1]["end_ms_exclusive"],
            complete_instrument_date_shards=len(shards),
            verified_minute_rows=sum(
                s["coverage"][kind]["observed_bars"] for s in shards for kind in ("trade", "mark")
            ),
            member_paths_relative_to="research/okx-forward-coverage-20261009",
            global_index_contains_other_instruments=True,
            provided_instruments=[instrument],
            bundle_format="ORDERED_BYTE_PARTS_OF_ONE_TAR_GZIP",
            bundle_sha256=digest,
            compressed_bytes=archive_path.stat().st_size,
            max_part_bytes=PART_BYTES,
            parts=parts,
            members=members,
            historical_publication_certified=False,
            historical_instrument_rules_certified=False,
            account_settlement_verified=False,
            frozen_selector_certified=False,
            training=False,
            wallet_backtest=False,
        )
        dump(manifest, staged / "manifest.json")
        verify_and_extract(staged)
        target = output / instrument / digest
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            verify_and_extract(target)
        else:
            shutil.move(str(staged), target)
    return dict(
        instrument_id=instrument,
        snapshot_commit=commit,
        manifest=str(target.relative_to(output) / "manifest.json"),
        manifest_sha256=sha256(target / "manifest.json"),
        bundle_sha256=digest,
        parts=len(parts),
        compressed_bytes=manifest["compressed_bytes"],
        complete_instrument_date_shards=len(shards),
        verified_minute_rows=manifest["verified_minute_rows"],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    receipts = [
        build(args.repo, args.commit, asset + "-USDT-SWAP", args.output) for asset in ASSETS
    ]
    dump(
        dict(
            version="okx-minute-transport-1",
            bundles=receipts,
            relative_path_basis="TRANSPORT_INDEX_DIRECTORY",
        ),
        args.output / "INDEX.json",
    )
    print(json.dumps(receipts), flush=True)


if __name__ == "__main__":
    main()
