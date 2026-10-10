"""Prepare one April63 prefix; one fixed512 fit; terminal export plus allfold aggregate."""

import argparse
import json
import os
from pathlib import Path

import torch

from .data import FOLD
from .export import aggregate, export_fold
from .protocol import PROTOCOL
from .stage import SUCCESS, prepare, train_fold


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("prepare", "fit", "export"))
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--producer-commit")
    args = parser.parse_args()
    if os.environ.get("COIN_CLOUD_BOUNDED") != "1":
        parser.error("Use the existing bounded resource launcher")
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    if args.operation == "prepare":
        ready = prepare(args.state, args.output)
        summary = dict(status=ready["status"], folds=list(ready["folds"]), planned_fits=1)
    elif args.operation == "fit":
        for _ in range(PROTOCOL["maximum_slices"]):
            result = train_fold(args.state, args.output, FOLD)
            if result["status"] != "SLICE_EXHAUSTED_RESUME_REQUIRED":
                break
        summary = {k: result[k] for k in ["status", "completed_updates", "model_identity"]}
        if result["status"] != SUCCESS:
            print(json.dumps(summary), flush=True)
            raise SystemExit(1)
    else:
        if args.destination is None or args.producer_commit is None:
            parser.error("export requires destination and exact published producer commit")
        score = export_fold(
            args.state, args.output, FOLD, args.destination / FOLD, args.producer_commit
        )
        total = aggregate(args.destination)
        summary = dict(
            status=total["status"],
            new_fold_PnL=score["policies"]["FRESH_GRU"]["net_PnL"],
            primary_PnL_excess=score["primary_PnL_excess"],
            screen_pass=total["screen_pass"],
        )
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
