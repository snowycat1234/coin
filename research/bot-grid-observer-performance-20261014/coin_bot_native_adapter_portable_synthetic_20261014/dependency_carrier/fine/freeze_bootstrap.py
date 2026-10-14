"""Stdlib-only code identity check; runs before financial/transport imports.

The freeze manifest hashes the reviewed module. The separate publication
receipt pins the manifest hash, avoiding a self-referential hash cycle.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = frozenset({"fine_account.py", "run_cases.py", "preflight.py",
                   "PROTOCOL.md", "FINE_PROFILE.json", "CASE_BINDINGS.json",
                   "test_pure.py"})


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root: Path = HERE) -> dict:
    root = Path(root).resolve()
    receipt_path = root / "REVIEW_RECEIPT.json"
    manifest_path = root / "FROZEN_CODE.json"
    receipt = json.loads(receipt_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    if (receipt.get("status") != "REVIEW_ONLY_NO_FINE_HISTORICAL_WALLET"
            or receipt.get("new_fine_wallets_executed") != 0
            or receipt.get("bootstrap_SHA256") != sha(root / "freeze_bootstrap.py")
            or manifest.get("status") != "REVIEWED_CODE_AND_INPUT_BINDING_PRE_GO"
            or set(manifest.get("files_SHA256", {})) != FILES
            or receipt.get("freeze_manifest_SHA256") != sha(manifest_path)):
        raise ValueError("Quantity-resolution reviewed manifest/receipt mismatch")
    for name, expected in manifest["files_SHA256"].items():
        path = root / name
        if path.is_symlink() or sha(path) != expected:
            raise ValueError(f"Quantity-resolution reviewed bytes changed: {name}")
    return {"freeze_manifest_SHA256": sha(manifest_path),
            "files_SHA256": manifest["files_SHA256"],
            "receipt_SHA256": sha(receipt_path)}
