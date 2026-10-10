import argparse
from pathlib import Path

import pyarrow as pa
import torch

from .stage import prepare, worker

parser = argparse.ArgumentParser(description="One controlled expanded1137 fixed907 fresh256 fit")
parser.add_argument("action", choices=["prepare", "worker"])
for name in ("state", "economics", "output"):
    parser.add_argument("--" + name, type=Path, required=True)
parser.add_argument("--publication", type=Path)
args = parser.parse_args()
torch.set_num_threads(1)
torch.use_deterministic_algorithms(True)
pa.set_cpu_count(1)
pa.set_io_thread_count(1)
if args.action == "prepare":
    prepare(args.state, args.economics, args.output)
else:
    if args.publication is None:
        parser.error("Verified public prefit readback required")
    worker(args.state, args.economics, args.output, args.publication)
