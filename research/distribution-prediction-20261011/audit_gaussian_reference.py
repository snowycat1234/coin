"""Pinned notebook Gaussian and actual TestDataset provenance, synthetic only."""
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.upstream.resolve()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    assert commit == "bf0a6554054735448ea02910e0ced335c7481969"
    source_files = ["results.ipynb", "utils/data_utils.py", "utils/result_utils.py", "LSTM.py"]
    for name in source_files:
        original = subprocess.check_output(["git", "show", f"{commit}:{name}"], cwd=root)
        assert original == (root/name).read_bytes(), f"modified official source {name}"
    notebook = json.loads((root/"results.ipynb").read_text())
    cells = ["".join(c.get("source", [])) for c in notebook["cells"]]
    assert "lookforward=30, test=True" in cells[17]
    assert 'observed_returns"].append(obs.cpu().numpy().squeeze())' in cells[16]
    assert 'future_returns"], axis=0)/100' in cells[16]
    assert "empirical_mean = np.mean(observed_returns[i])" in cells[21]
    assert "empirical_std = np.std(observed_returns[i])" in cells[21]
    assert "norm.ppf(np.array(taus), loc=empirical_mean, scale=empirical_std)" in cells[21]
    # Execute the actual pinned class; no copied or mocked data-generation logic.
    os.chdir(root)
    sys.path.insert(0, str(root))
    from utils.data_utils import TestDataset
    dates = pd.date_range("2017-01-01", periods=150, tz="UTC")
    returns = .001+np.arange(150)*.0001
    frame = pd.DataFrame({"return_2d": returns, "x": np.sin(np.arange(150))}, index=dates)
    market = pd.DataFrame({"m": np.cos(np.arange(150))}, index=dates)
    dataset = TestDataset({"crypto": [{"asset": "SYNTH", "data": frame}]}, market, 5,
                          "2017-01-06", "2017-05-30", lookforward=30, test=True)
    _, _, _, future_percent, observed = dataset[0]
    past_dates = pd.DatetimeIndex(dataset.z[0])
    future_dates = past_dates+pd.Timedelta(days=30)
    past_expected = frame.loc[past_dates, "return_2d"].values
    future_expected = frame.loc[future_dates, "return_2d"].values
    assert np.allclose(observed.cpu().numpy().ravel(), past_expected, rtol=1e-6, atol=1e-9)
    assert np.allclose(future_percent.cpu().numpy().ravel()/100, future_expected, rtol=1e-6, atol=1e-9)
    assert future_dates.min() == past_dates.max()+pd.Timedelta(days=1)
    assert (future_dates > past_dates.max()).all()
    out = {
        "status": "PASS", "upstream_commit": commit, "synthetic_only": True,
        "real_dataset_loaded": False, "neural_fit_or_inference": 0,
        "notebook_evidence": {"cell17": "TestDataset lookforward=30 test=True",
                              "cell16": "obs kept as raw daily log returns; future y divided by100",
                              "cell21": "Gaussian mean/std of past observed_returns; numpy std default ddof0"},
        "dataset_source_lines": {"future_shift": 469, "past_x_slice": 486, "past_timestamps": 488,
                                  "observed_return_lookup": 523},
        "witness": {"past_start": str(past_dates.min()), "past_end": str(past_dates.max()),
                    "future_start": str(future_dates.min()), "future_end": str(future_dates.max()),
                    "past_count": len(past_dates), "future_count": len(future_dates),
                    "obs_mean": float(past_expected.mean()), "obs_std_ddof0": float(past_expected.std()),
                    "future_mean": float(future_expected.mean()), "obs_is_past_not_future": True},
        "coin_differences": {"lookback_and_horizon": 22, "control_std_ddof": 1,
                             "model_scale": "causal origin sqrt EWMA variance, plus learned positive market multiplier",
                             "original_control": "rolling22 mean and sample std; causal but different volatility conditioning",
                             "primary_new_control": "zero mean and same known causal EWMA origin sigma; no learned multiplier",
                             "representation": "same37 quantiles, piecewise-linear quantile CDF with fixed endpoint atoms for all COIN arms",
                             "paper_scoring": "original notebook uses continuous Gaussian CDF and smoothed neural CDF; original CRPS routine not valid return-axis integration"},
        "conclusion": "original COIN pair is paired and causal, but not an exact notebook replication or architecture-isolating comparison",
        "source_sha256": {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in source_files},
    }
    args.output.write_text(json.dumps(out, indent=2)+"\n")
    print(json.dumps({"status": out["status"], "witness": out["witness"]}))


if __name__ == "__main__":
    main()
