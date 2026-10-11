"""Bind a fresh reproduction to published source; no training or data download."""

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATHS = (
    "modules/slow_momentum_cpd/sharpe.py",
    "modules/slow_momentum_cpd/test_sharpe.py",
    "modules/slow_momentum_cpd/audit_sharpe.py",
    "research/slow-momentum-cpd-sharpe-20261011/PROTOCOL.json",
    "research/slow-momentum-cpd-sharpe-20261011/prefit/TESTS.xml",
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    state = args.state.resolve()
    if not state.is_relative_to(Path("/workspace")) or state.is_relative_to(
        Path("/workspace/slow-momentum-state")
    ):
        raise ValueError("Fresh independent workspace state required")
    if (state / "ATTEMPT.json").exists():
        raise FileExistsError("Never relabel an existing scientific attempt")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    remote = subprocess.check_output(
        ["git", "ls-remote", "origin", "refs/heads/research/slow-momentum-cpd-20261011"],
        cwd=ROOT,
        text=True,
    ).split()[0]
    if head != remote:
        raise ValueError("Checkout must match the published research branch")
    hashes = {}
    for path in SOURCE_PATHS:
        published = subprocess.check_output(["git", "show", head + ":" + path], cwd=ROOT)
        if (ROOT / path).read_bytes() != published:
            raise ValueError("Unpublished source: " + path)
        hashes[path] = hashlib.sha256(published).hexdigest()
    original = json.loads(
        (ROOT / "research/slow-momentum-cpd-sharpe-20261011/results/RESULT.json").read_text()
    )
    for path in SOURCE_PATHS[:2]:
        if hashes[path] != original["source_files"][path]:
            raise ValueError("Frozen training implementation changed: " + path)
    state.mkdir(parents=True, exist_ok=True)
    receipt = {
        "local_sha": head,
        "remote_sha": remote,
        "remote_verified_before_fit": True,
        "published_source_sha256": hashes,
        "verified_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": (
            "User-invoked reproduction, same frozen training with disclosed repaired auditor"
        ),
    }
    with (state / "PREFIT_PUBLICATION.json").open("x") as file:
        json.dump(receipt, file, indent=2, allow_nan=False)
        file.write("\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
