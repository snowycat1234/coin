import argparse
from pathlib import Path

import torch

from .stage import emit, prepare, select, train_slice

parser = argparse.ArgumentParser(description="Only six reviewed fresh fits; no reserved scoring")
parser.add_argument("action", choices=("prepare", "worker", "select"))
parser.add_argument("--state", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--task")
parser.add_argument("--seconds", type=float, default=1100.0)
args = parser.parse_args()
torch.set_num_threads(1)
torch.use_deterministic_algorithms(True)
if args.action == "prepare":
    prepare(args.state, args.output)
elif args.action == "worker":
    if not args.task:
        parser.error("worker requires one approved task")
    train_slice(args.state, args.output, args.task, seconds=args.seconds)
else:
    result = select(args.output)
    emit(
        dict(
            status=result["status"],
            selected=result["selected"]["candidate"],
            steps=result["later_full773_refit_steps"],
            updates=result["total_completed_updates"],
        )
    )
