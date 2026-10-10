"""Causal summary, mask, boundary and arithmetic checks without economic fitting."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np

spec = importlib.util.spec_from_file_location(
    "short_inputs", Path(__file__).with_name("diagnose.py")
)
diag = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diag)


def windows(n=1):
    x = np.ones((n, 64, 5, 24), dtype=float)
    return SimpleNamespace(values=x, valid=np.ones_like(x, dtype=bool))


def test_observed_only_missing_is_unknown_not_zero():
    w = windows()
    w.valid[:, -1, :3, diag.FEATURE_NAMES.index("mom20")] = False
    w.valid[:, -4, :3, diag.FEATURE_NAMES.index("funding")] = False
    s = diag.summaries(w)
    assert np.isnan(s["mom20"][0]) and np.isnan(s["funding7"][0])
    g = diag.classify(s, 1.2)
    assert g["trend_rebound"][0] == g["funding_premium"][0] == "UNKNOWN"


def test_last_step_and_seven_day_means_ignore_earlier_values():
    w = windows()
    for name in ("funding", "premium"):
        j = diag.FEATURE_NAMES.index(name)
        w.values[:, :-7, :, j] = -1e12
        w.values[:, -7:, :, j] = np.arange(1, 8)[None, :, None]
    s = diag.summaries(w)
    assert s["funding7"][0] == s["premium7"][0] == 4
    assert s["mom20"][0] == 1
    w.values[:, :-1, :, diag.FEATURE_NAMES.index("mom20")] = -1e12
    assert diag.summaries(w)["mom20"][0] == 1


def test_financial_zero_and_fixed_quantile_boundary():
    s = {
        "mom20": np.array([-1.0, -1.0, 0.0, np.nan]),
        "mom5": np.array([0.0, 0.1, -0.1, 0.1]),
        "vol10_over_vol60": np.array([1.2, 1.20001, 0.0, np.nan]),
        "funding7": np.array([-1.0, 1.0, 0.0, np.nan]),
        "premium7": np.array([-1.0, 1.0, -1.0, 1.0]),
    }
    g = diag.classify(s, 1.2)
    assert g["trend_rebound"].tolist() == [
        "CONTINUING_FALL",
        "REBOUND_WITHIN_FALL",
        "NONFALLING20",
        "UNKNOWN",
    ]
    assert g["volatility_shock"].tolist() == ["ORDINARY", "HIGH_SHOCK", "ORDINARY", "UNKNOWN"]
    assert g["funding_premium"].tolist() == [
        "NEGATIVE_BOTH",
        "POSITIVE_BOTH",
        "MIXED_OR_ZERO",
        "UNKNOWN",
    ]


def test_false_positive_to_other_expert_can_still_beat_vol():
    y, pred = np.array([3, 2, 1, 0]), np.array([3, 3, 3, 1])
    gap, best = np.array([0.04, 0.01, -0.1, 0]), np.array([0.02, -0.01, -0.1, 0])
    s = diag.state_stats(y, gap, best, np.ones(4, dtype=bool), pred)
    assert s["SHORT_picks"] == 3 and s["correct"] == 1 and s["incorrect"] == 2
    assert s["SHORT_beats_VOL_count"] == 2
    assert s["false_positive_winner_counts_CASH_VOL_CS"] == [0, 1, 1]
    assert abs(s["sum_SHORT_minus_VOL"] + 0.05) < 1e-15


def test_contrast_retains_empty_states_and_all_phases():
    y, pred, gap = np.array([3, 1]), np.array([3, 3]), np.array([0.1, -0.1])
    groups = np.array(["HIGH_SHOCK", "HIGH_SHOCK"])
    assert diag.difference(y, gap, pred, groups, "HIGH_SHOCK", "ORDINARY") is None
    assert (
        diag.contrast(y, gap, pred, groups, "HIGH_SHOCK", "ORDINARY")["status"]
        == "INSUFFICIENT_STATES"
    )


def test_winner_runs_break_on_other_labels_and_calendar_gaps():
    spec = importlib.util.spec_from_file_location(
        "run_verify", Path(__file__).with_name("verify.py")
    )
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    d = np.array([0, 1, 2, 4, 5, 6], dtype=np.int64) * diag.DAY_US
    y = np.array([3, 3, 1, 3, 3, 3])
    r = verifier.short_runs(d, y)
    assert r["run_count"] == 2 and r["longest_run_rows"] == 3
    y = np.array([3, 3, 3, 3, 3, 3])
    r = verifier.short_runs(d, y)
    assert r["run_count"] == 2 and r["longest_run_rows"] == 3
