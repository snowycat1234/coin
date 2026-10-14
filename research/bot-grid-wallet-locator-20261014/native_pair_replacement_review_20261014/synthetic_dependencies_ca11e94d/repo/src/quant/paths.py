import os
from pathlib import Path

ROOT = Path(os.environ.get("QUANT_ROOT", "/mnt/d/codex/coin")).resolve()
VHD = Path("/mnt/d/hpc/linux/ext4.vhdx")
STATE = Path(os.environ.get("QUANT_STATE", "/home/xflops/coin-state"))


def utc_now_us() -> int:
    import time

    return time.time_ns() // 1000

