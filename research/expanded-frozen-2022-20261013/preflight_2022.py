"""Read-only 2022 source/warmup preflight. Never creates targets or accounts."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DAY = 86_400_000_000
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
Y2023_SHA = "1c500e9d5b0244a1daaabc597d7cc5ae97a21a156cc42d8a44a1504b821e599f"
Y2025_SHA = "88a698ceed87603a36ca2bcf4ae76d805aa90085b344bbeee47e58a8c9770add"


def us(year, month=1, day=1):
    return int(datetime(year, month, day, tzinfo=timezone.utc).timestamp() * 1_000_000)


def iso(clock):
    return datetime.fromtimestamp(int(clock) / 1_000_000, timezone.utc).isoformat()


def inspect(inputs: Path):
    a, b = inputs / "Y2023.npz", inputs / "Y2025.npz"
    assert hashlib.sha256(a.read_bytes()).hexdigest() == Y2023_SHA
    assert hashlib.sha256(b.read_bytes()).hexdigest() == Y2025_SHA
    with np.load(a, allow_pickle=False) as z:
        t, p, names = z["close_available_us"], z["close"], tuple(z["symbol_order"])
    with np.load(b, allow_pickle=False) as z:
        tb, pb, namesb = z["close_available_us"], z["close"], tuple(z["symbol_order"])
    assert names == namesb == SYMBOLS and p.shape == (len(t), 5)
    assert np.all(np.diff(t) == DAY) and np.array_equal(t, tb[:len(t)])
    decision = np.arange(us(2022), us(2023), DAY, dtype=np.int64)
    assert len(decision) == 365
    positions = np.searchsorted(t, decision)
    assert np.array_equal(t[positions], decision)
    good_200 = np.array([np.all(np.diff(t[k-199:k+1]) == DAY)
                         and np.isfinite(p[k-199:k+1]).all()
                         and (p[k-199:k+1] > 0).all()
                         for k in positions], dtype=bool)
    # The fixed Monday anchor is also applied backwards; Jan 1 is Saturday.
    anchor = us(2024)
    first_rank = anchor + ((int(decision[0]) - anchor) // (7 * DAY)) * (7 * DAY)
    rk = int(np.searchsorted(t, first_rank))
    assert t[rk] == first_rank and np.isfinite(p[rk-30:rk+1]).all()
    assert (p[rk-30:rk+1] > 0).all() and np.all(np.diff(t[rk-30:rk+1]) == DAY)
    both = np.isfinite(p) & np.isfinite(pb[:len(t)])
    mismatches = np.argwhere(~both | (p != pb[:len(t)]))
    discrepant_2022 = [(iso(t[i]), SYMBOLS[j], None if not np.isfinite(pb[i,j]) else float(pb[i,j]))
                       for i,j in mismatches if us(2022) <= t[i] < us(2023)]
    return {
        "status": "DAILY_TARGET_SOURCE_ADMISSIBLE_ONLY_NATIVE_MINUTE_SOURCE_NOT_ADMITTED",
        "source_cube": "Y2023.npz", "source_SHA256": Y2023_SHA,
        "comparison_cube": "Y2025.npz", "comparison_SHA256": Y2025_SHA,
        "source_first_close_available_utc": iso(t[0]),
        "source_last_close_available_utc": iso(t[-1]),
        "decision_first_utc": iso(decision[0]), "decision_end_exclusive_utc": iso(us(2023)),
        "decision_days": len(decision), "complete_full_five_200_close_days": int(good_200.sum()),
        "oldest_200_close_first_decision_utc": iso(t[positions[0]-199]),
        "first_pre_window_scheduled_rank_utc": iso(first_rank),
        "first_rank_all_five_31_close_admissible": True,
        "later_cube_different_2022_cells": discrepant_2022,
        "later_cube_2022_discrepancy_count": len(discrepant_2022),
        "targets_created": 0, "financial_wallets_started": 0,
    }


if __name__ == "__main__":
    report = inspect(ROOT / "coin_cs_sma_recovery_20261013/inputs")
    (HERE / "DAILY_PREFLIGHT.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "decision_days",
          "complete_full_five_200_close_days", "later_cube_2022_discrepancy_count")}))
