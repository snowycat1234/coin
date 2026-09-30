"""One-time SQLite relocation from DrvFs to the D-hosted WSL ext4 filesystem."""
import sqlite3
from pathlib import Path

source = Path("/mnt/d/codex/coin/state/archive_manifest.sqlite3")
destination = Path("/home/xflops/coin-state/archive_manifest.sqlite3")
destination.parent.mkdir(parents=True, exist_ok=True)
if source.exists() and not destination.exists():
    old = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    new = sqlite3.connect(destination)
    try:
        old.backup(new)
    finally:
        old.close()
        new.close()
    print("Archive manifest migrated into D-hosted WSL ext4")
