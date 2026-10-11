"""Reproduce the boundary/target audit with synthetic data and a pinned checkout."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--upstream", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    root = args.upstream.resolve()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if commit != "bf0a6554054735448ea02910e0ced335c7481969":
        raise ValueError("wrong upstream commit")
    os.chdir(root)
    sys.path.insert(0, str(root))
    from utils.data_utils import DistDataset
    from utils.ta_utils import calculate_log_return
    idx = pd.date_range("2017-01-01", "2024-01-01", tz="UTC")
    rng = np.random.default_rng(271198)
    df = pd.DataFrame({"return_2d": rng.normal(0, .02, len(idx)), "x": rng.normal(size=len(idx))}, index=idx)
    market = pd.DataFrame({"m": rng.normal(size=len(idx))}, index=idx)
    config = json.loads((root/"config.json").read_text())
    periods = config["general"]["dates"]
    labels = {}
    for name, key in [("validation", "validation_period"), ("test", "test_period")]:
        np.random.seed(271198)
        dataset = DistDataset({"crypto": [{"asset": "SYNTH", "data": df}]}, market, 5,
                              periods[key]["start_date"], periods[key]["end_date"], lookahead=22)
        labels[name] = {t for series in dataset.y for t in series.index}
    price = pd.DataFrame({"Adj Close": [1., 2., 8.]})
    source = ["config.json", "LSTM.py", "utils/data_utils.py", "utils/ta_utils.py", "utils/train_utils.py", "utils/result_utils.py"]
    result = {
        "upstream_commit": commit, "fixture_only": True,
        "paper_validation_text": "2018 through end 2019, while test begins 2019",
        "code_config": periods, "inclusive_slice_shared_boundary": "2019-01-01",
        "synthetic_label_overlap": len(labels["validation"] & labels["test"]),
        "validation_labels_max": str(max(labels["validation"])), "test_labels_min": str(min(labels["test"])),
        "return_2d_actual_one_day": bool(np.allclose(calculate_log_return(price, 2).iloc[1:], np.log([2., 4.]))),
        "source_sha256": {s: hashlib.sha256((root/s).read_bytes()).hexdigest() for s in source},
        "crps_audit": "calculate_crps uses linspace(0,1) instead of the return grid and mean instead of integration; paper values are not validated standard CRPS",
    }
    args.output.write_text(json.dumps(result, indent=2)+"\n")


if __name__ == "__main__":
    main()
