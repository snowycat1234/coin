"""Only prepare, one prescribed512 fit, frozen export and seen score."""

import argparse
import json
from pathlib import Path

import torch

from .export import export_native, score
from .stage import PROTOCOL, SUCCESS, prepare, train_slice


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("prepare", "fit", "export", "score"))
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--producer-commit")
    args = parser.parse_args()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    if args.operation == "prepare":
        result = prepare(args.state, args.output)
        summary = dict(
            status=result["status"],
            initial_train_loss=result["initial_diagnostic"]["date_mean_loss"],
        )
    elif args.operation == "fit":
        for _ in range(PROTOCOL["maximum_slices"]):
            result = train_slice(args.state, args.output)
            if result["status"] != "SLICE_EXHAUSTED_RESUME_REQUIRED":
                break
        summary = {
            key: result[key]
            for key in ("status", "completed_updates", "model_identity", "elapsed_seconds")
        }
        if result["status"] != SUCCESS:
            print(json.dumps(summary), flush=True)
            raise SystemExit(1)
    elif args.operation == "export":
        if args.destination is None or args.producer_commit is None:
            parser.error("export requires destination and published producer commit")
        summary = export_native(args.state, args.output, args.destination, args.producer_commit)
    else:
        if args.destination is None:
            parser.error("score requires the already exported native destination")
        result = score(args.state, args.output, args.destination)
        summary = dict(
            status="SEEN_INITIALIZATION_ABLATION_SCORED",
            training_loss=result["final_train_loss"],
            fresh_PnL=result["fresh"]["net_PnL"],
            difference_vs_warm=result["PnL_difference_vs_exact_warm"],
        )
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
