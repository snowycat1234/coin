"""Show the existing conservative guard's scan; persist only its final ledger."""
import json
import os
from pathlib import Path
import time

from quant import disk

if __name__ == "__main__":
    result = {"ledger": disk.check(), "measured_at": time.time()}
    folder = Path("/home/xflops/coin-state/task-progress")
    folder.mkdir(exist_ok=True)
    temporary = folder / "last-disk.tmp"
    temporary.write_text(json.dumps(result))
    os.replace(temporary, folder / "last-disk.json")
    print(json.dumps(result), flush=True)
