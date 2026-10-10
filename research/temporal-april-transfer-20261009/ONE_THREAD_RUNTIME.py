"""Resource-only launcher: initialize serial Arrow readers before large inputs."""

import importlib
import json
import os
import runpy
import sys

if os.environ.get("COIN_CLOUD_BOUNDED") != "1":
    raise SystemExit("Existing bounded launcher required")
import pyarrow as pa  # noqa: E402
import torch  # noqa: E402

torch.set_num_threads(1)
torch.use_deterministic_algorithms(True)
importlib.import_module("torch._dynamo")
pa.set_cpu_count(1)
pa.set_io_thread_count(1)
for name in ("pyarrow.dataset", "pyarrow.parquet", "polars"):
    importlib.import_module(name)
print(
    json.dumps(
        dict(
            stage="resource_only_serial_reader_preload",
            Arrow_CPU_threads=pa.cpu_count(),
            Arrow_IO_threads=pa.io_thread_count(),
            MALLOC_ARENA_MAX=os.environ.get("MALLOC_ARENA_MAX"),
        )
    ),
    flush=True,
)
module = sys.argv.pop(1)
if module.endswith(".py"):
    runpy.run_path(module, run_name="__main__")
else:
    runpy.run_module(module, run_name="__main__")
