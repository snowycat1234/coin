"""Conservative physical-file ledger including the D-hosted WSL VHD."""
import argparse
import json
import os
import shutil
from pathlib import Path

from .paths import ROOT, VHD

GB = 1_000_000_000


def tree_bytes(root: Path) -> int:
    total = 0
    resolved_root = root.resolve()
    pending = [root]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                if entry.is_symlink():
                    item = Path(entry.path)
                    # The interpreter is in the D-hosted distro, counted in VHD.
                    distro_python = (item.parent == root / ".venv/bin"
                                     and item.name in {"python", "python3", "python3.12"}
                                     and item.resolve() == Path("/usr/bin/python3.12"))
                    if not item.resolve().is_relative_to(resolved_root) and not distro_python:
                        raise RuntimeError(f"External project symlink rejected: {item}")
                elif entry.is_dir(follow_symlinks=False):
                    pending.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    total += entry.stat(follow_symlinks=False).st_size
    return total


def enforce(used: int, reserve: int, free: int) -> str:
    if reserve < 0:
        raise ValueError("Reservation cannot be negative")
    if used + reserve >= 40 * GB:
        raise RuntimeError("40 GB hard limit would be reached")
    if used + reserve >= 36 * GB:
        raise RuntimeError("36 GB intake limit: preserve the 4 GB emergency buffer")
    if free < reserve + 4 * GB:
        raise RuntimeError("D drive emergency free-space buffer would be consumed")
    return "WARNING" if used + reserve >= 32 * GB else "OK"


def check(reserve: int = 0, root: Path = ROOT, vhd: Path = VHD) -> dict:
    if not str(root.resolve()).startswith("/mnt/d/"):
        raise RuntimeError("Project must be on D: via /mnt/d")
    project_bytes = tree_bytes(root)
    vhd_bytes = vhd.stat().st_size
    used = project_bytes + vhd_bytes
    free = shutil.disk_usage(root).free
    return {"project_bytes": project_bytes, "wsl_vhd_bytes": vhd_bytes,
            "total_bytes": used, "reserved_bytes": reserve, "d_free_bytes": free,
            "status": enforce(used, reserve, free), "hard_limit_bytes": 40 * GB}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reserve", type=int, default=0)
    args = parser.parse_args()
    print(json.dumps(check(args.reserve), indent=2))

