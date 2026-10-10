"""Recompute compact evidence and contiguous winner runs from frozen row labels."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from modules.temporal_purged_supervised.inputs import install_io_guard, io_receipt
from modules.temporal_two_expert.inputs import DAY_US


def short_runs(decision, winner):
    """A non-SHORT label or a nonconsecutive calendar date starts a new run."""
    runs = []
    current = []
    for i, (d, y) in enumerate(zip(decision, winner, strict=True)):
        if y == 3:
            if current and d - decision[current[-1]] != DAY_US:
                runs.append(current)
                current = []
            current.append(i)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    details = [
        {
            "start": str(np.datetime64(int(decision[ix[0]]), "us").astype("datetime64[D]")),
            "end": str(np.datetime64(int(decision[ix[-1]]), "us").astype("datetime64[D]")),
            "rows": len(ix),
        }
        for ix in runs
    ]
    return {
        "run_count": len(runs),
        "SHORT_winner_rows": int(np.sum(np.asarray(winner) == 3)),
        "longest_run_rows": max((len(ix) for ix in runs), default=0),
        "runs": details,
        "meaning": "Label persistence only; run count is not a formal independent sample size.",
    }


def verify(state, output):
    io = install_io_guard(state)
    evidence = json.loads((output / "EVIDENCE.json").read_text())
    with (output / "ROWS.csv").open() as f:
        rows = list(csv.DictReader(f))
    runs = {}
    for role, r in evidence["records"].items():
        rr = [a for a in rows if a["role"] == role]
        assert len(rr) == r["rows"]
        chosen = [a for a in rr if a["predicted"] == "3"]
        assert len(chosen) == r["SHORT_picks"]
        for mechanism, states in r["groups"].items():
            assert sum(v["SHORT_picks"] for v in states.values()) == r["SHORT_picks"]
            assert sum(v["all_rows"] for v in states.values()) == r["rows"]
            for name, v in states.items():
                selected = [a for a in chosen if a[mechanism] == name]
                assert len(selected) == v["SHORT_picks"]
                assert sum(a["winner"] == "3" for a in selected) == v["correct"]
                assert (
                    abs(
                        sum(float(a["SHORT_minus_VOL"]) for a in selected)
                        - v["sum_SHORT_minus_VOL"]
                    )
                    < 1e-12
                )
        assert len(r["phase_grids"]) == 21
        assert sum(g["rows"] for g in r["phase_grids"]) == r["rows"]
        d = np.array([int(a["decision_us"]) for a in rr], dtype=np.int64)
        y = np.array([int(a["winner"]) for a in rr])
        assert np.all(np.diff(d) > 0)
        runs[role] = short_runs(d, y)
        print(role, runs[role]["run_count"], runs[role]["longest_run_rows"], flush=True)
    for name in ("FREEZE_IO.json", "DIAGNOSE_IO.json"):
        receipt = json.loads((output / name).read_text())
        assert not receipt["forbidden_2025_attempts"]
        assert all("2025" not in p for p in receipt["state_file_opens"])
    result = {
        "status": "COUNTS_MARGINS_MASK_GROUP_TOTALS_ALL_PHASES_RECOMPUTED_PASS",
        "SHORT_winner_runs": runs,
        "IO": io_receipt(io),
    }
    with (output / "VERIFY.json").open("x") as f:
        json.dump(result, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    verify(a.state, a.output)
