"""Readiness/restore commands only; economic fitting requires explicit Python API."""

import argparse
import json

import numpy as np

from .exact import PROTOTYPE_SHA256, load_prototype, prepare_recovery
from .inputs import FEATURE_NAMES, Standardizer
from .model import FAMILIES, Selector


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "restore"))
    parser.add_argument(
        "--recovery",
        required=True,
        help="New recovery directory for restore, prototype.py path for check",
    )
    args = parser.parse_args()
    if args.mode == "restore":
        print(prepare_recovery(args.recovery))
        return
    load_prototype(args.recovery)
    # Architecture inspection only. This synthetic scale cannot pass train_steps.
    scale = Standardizer(
        np.zeros(24),
        np.ones(24),
        np.ones(24, dtype=np.int64),
        dict(role="architecture_inspection_only"),
    )
    models = {
        f + ("_WITH_CASH" if cash else "_NO_CASH"): Selector(
            scale, family=f, cash_enabled=cash
        ).parameter_count
        for f in FAMILIES
        for cash in (False, True)
    }
    print(
        json.dumps(
            dict(
                status="CODE_READY_DATA_NOT_READY",
                parameter_counts=models,
                features=list(FEATURE_NAMES),
                prototype_SHA256=PROTOTYPE_SHA256,
                real_daily_steps=64,
                economic_fits=0,
                needs="broader pre-May2024 bound features and real warmup, native validation",
            )
        )
    )


if __name__ == "__main__":
    main()
