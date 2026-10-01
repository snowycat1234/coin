import math
import tempfile
from pathlib import Path

import pytest

from quant.paths import ROOT, STATE
from quant.replay import (
    DAY_MS,
    MINUTE_MS,
    HistoricalShadowAdapter,
    ReplayBudget,
    _feed_row,
    _health,
    _ms,
    _open_feed,
    _run_scenario,
    run_historical_replay,
)
from quant.shadow import ShadowConfig, ShadowEngine


@pytest.fixture
def lab():
    STATE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="replay-test-", dir=STATE) as folder:
        directory = Path(folder)
        yield directory, ReplayBudget(directory, directory / "reports", {"status": "OK"})


def test_replay_refuses_holdout_before_opening_inputs(lab):
    folder, _ = lab
    with pytest.raises(ValueError, match="before the sealed"):
        run_historical_replay("2026-01-01", "2026-09-01", state_dir=folder / "blocked")
    assert not (folder / "blocked").exists()


def test_covariance_cache_matches_frozen_engine_and_ignores_future(lab):
    folder, budget = lab
    feed = _open_feed(folder / "feed.sqlite3")
    start = _ms("2024-01-01")
    now = start + 31 * DAY_MS + 500
    def rows():
        for index in range(31 * 1440):
            for symbol, factor in (("BTCUSDT", 1), ("ETHUSDT", 2)):
                opened = start + index * MINUTE_MS
                price = 100 + factor * math.sin(index / 1440)
                yield _feed_row(symbol, {
                    "open_us": opened * 1000, "close_us": (opened + MINUTE_MS) * 1000,
                    "open": price, "high": price, "low": price, "close": price,
                    "volume": 100000, "quote_volume": 10000000, "trade_count": 100,
                })
    feed.executemany("INSERT INTO closed_bars VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows())
    feed.commit()
    obj = HistoricalShadowAdapter(
        folder / "feed.sqlite3", folder / "account.sqlite3", budget=budget,
        config=ShadowConfig(mode="engineering_simulation"), started_ms=now,
        initial_disk=budget.ledger,
    )
    try:
        for raw in ({"BTCUSDT": .3, "ETHUSDT": .3}, {"BTCUSDT": 0, "ETHUSDT": .3}):
            expected = ShadowEngine._risk_weights(obj, raw, now)
            assert obj._risk_weights(raw, now) == expected
        # A future source row is queryable but must never change known covariance.
        future = now + DAY_MS
        row = {"open_us": future * 1000, "close_us": (future + MINUTE_MS) * 1000,
               "open": 999999, "high": 999999, "low": 999999, "close": 999999,
               "volume": 1, "quote_volume": 1, "trade_count": 1}
        feed.execute("INSERT INTO closed_bars VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     _feed_row("BTCUSDT", row))
        feed.commit()
        assert obj._risk_weights(raw, now) == ShadowEngine._risk_weights(obj, raw, now)
    finally:
        obj.close()
        feed.close()


def test_real_history_restart_fills_reconciliation_and_clock_freeze(lab):
    folder, budget = lab
    start = _ms("2024-01-01")
    config = ShadowConfig(version="replay_acceptance_test", mode="engineering_simulation")
    result = _run_scenario(
        root=ROOT, directory=folder / "clock", name="clock", start=start,
        end=start + 3 * DAY_MS, warmup=start - 31 * DAY_MS, config=config,
        budget=budget, restart_ms=start + 2 * DAY_MS + 14 * 3600000 + 30 * MINUTE_MS,
        fault="clock",
    )
    assert result["fill_count"] > 0
    assert result["restart_verified"]
    assert result["fault_cancelled_orders"] > 0
    assert result["hash_chain_verified"] and result["all_days_observable"]
    assert result["real_healthy_seconds"] == 0
    assert result["metrics"]["B0"]["total_return"] == 0
    assert result["metrics"]["B2"]["days"] == 3
    assert _health(start)["source"] == "engineering_simulation_no_real_qualification"
