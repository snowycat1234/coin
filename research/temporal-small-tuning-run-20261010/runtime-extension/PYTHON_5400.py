#!/workspace/coin/.venv/bin/python
"""Route the unchanged resident guard to Python, and only its worker to the overlay."""

import os
import sys
from pathlib import Path

from RUNTIME_EXTENSION import (
    REAL_PYTHON,
    REPO,
    verify_permission,
    verify_prepared,
    worker,
)


def main():
    arguments = sys.argv[1:]
    guard = REPO / "research/temporal-april-transfer-20261009/BOUNDED_RESIDENT_RUNTIME.py"
    if arguments and Path(arguments[0]).resolve() == guard:
        # Verification of the worker belongs inside the unchanged resident/wall
        # guard, rather than adding unmetered Torch setup before its clock.
        os.execv(REAL_PYTHON, [REAL_PYTHON, *arguments])
    required = (
        "COIN_TUNING_EXTENSION_PERMISSION",
        "COIN_TUNING_EXTENSION_COMMIT",
        "COIN_TUNING_EXTENSION_PUBLIC_PATH",
    )
    if any(not os.environ.get(k) for k in required):
        raise ValueError("No implicitly enabled runtime extension")
    permission = verify_permission(*(os.environ[k] for k in required))
    prepared_keys = (
        "COIN_TUNING_EXTENSION_PREPARED",
        "COIN_TUNING_EXTENSION_PREPARED_COMMIT",
        "COIN_TUNING_EXTENSION_PREPARED_PUBLIC_PATH",
    )
    if any(not os.environ.get(k) for k in prepared_keys):
        raise ValueError("Published tested-overlay receipt required")
    prepared = verify_prepared(*(os.environ[k] for k in prepared_keys), permission)
    if arguments[:3] == ["-m", "modules.temporal_small_tuning", "worker"]:
        worker(arguments[3:], permission, prepared)
        return
    raise ValueError("Proxy admits only the original resident guard and approved worker")


if __name__ == "__main__":
    main()
