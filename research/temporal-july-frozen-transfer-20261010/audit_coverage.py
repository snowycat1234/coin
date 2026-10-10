"""Read-only coverage audit; never imports a policy, optimizer or wallet runner."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from modules.collector_research.pipeline.normalize import funding_windows
from modules.temporal_two_expert.inputs import CORE5, DAY_US, MARKET_CONTEXT


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def date(value):
    return str(np.datetime64(int(value), "us"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    protocol = json.loads((Path(__file__).parent / "PROTOCOL.json").read_text())
    start, end = protocol["calendar"]["start_us"], protocol["calendar"]["end_exclusive_us"]
    decisions = np.arange(start, end, DAY_US, dtype=np.int64)
    completed = np.arange(start - 63 * DAY_US, end, DAY_US, dtype=np.int64)
    assert len(decisions) == 63 and len(completed) == 126
    root = args.state / "feature-input/verified"
    members = json.loads((root / "MEMBERS.json").read_text())["files"]
    primitive, economic, sources = {}, {}, {}
    for symbol in MARKET_CONTEXT:
        name = "source_tables_not_model_inputs/daily_features/" + symbol + ".parquet"
        path = root / name
        assert sha(path) == members[name]["SHA256"]
        sources[name] = sha(path)
        frame = pq.read_table(path).to_pandas()
        clocks = pd.DatetimeIndex(frame.dt).as_unit("us").asi8 + DAY_US
        assert np.all(np.diff(clocks) == DAY_US)
        selected = np.isin(clocks, completed)
        close = frame.close.to_numpy(float)
        trade = frame.complete_kline.to_numpy(bool) & np.isfinite(close) & (close > 0)
        primitive[symbol] = dict(
            required_completed_steps=126,
            present=int(selected.sum()),
            observed_trade_close=int((selected & trade).sum()),
            complete_premium=int((selected & frame.complete_premium.to_numpy(bool)).sum()),
            complete_funding=int((selected & frame.complete_funding.to_numpy(bool)).sum()),
            missing_trade_completed_us=completed[~np.isin(completed, clocks[trade])].tolist(),
        )
        if symbol not in CORE5:
            continue
        paths = ["source_tables_not_model_inputs/economics/" + symbol + suffix
                 for suffix in ("_daily.parquet", "_funding_events.parquet")]
        for name in paths:
            assert sha(root / name) == members[name]["SHA256"]
            sources[name] = sha(root / name)
        daily, events = [pq.read_table(root / name).to_pandas() for name in paths]
        clocks = pd.DatetimeIndex(daily.dt).as_unit("us").asi8
        price = daily.exec_price.to_numpy(float)
        good = (daily.complete_kline.to_numpy(bool)
                & (daily.unique_minutes.to_numpy() == 1440)
                & np.isfinite(price) & (price > 0))
        available = clocks[good]
        actual = funding_windows(events, pd.to_datetime(decisions[:-1], unit="us", utc=True))
        economic[symbol] = dict(
            required_execution_prices=63,
            present_execution_rows=int(np.isin(decisions, clocks).sum()),
            usable_actual_execution_prices=int(np.isin(decisions, available).sum()),
            missing_execution_decisions_us=decisions[~np.isin(decisions, available)].tolist(),
            required_active_funding_intervals=62,
            complete_actual_mark_funding_intervals=int(actual.funding_interval_complete.sum()),
            funding_event_last_us=int(events.calc_time_ms.max()) * 1000,
            missing_funding_interval_decisions_us=decisions[:-1][
                ~actual.funding_interval_complete.to_numpy(bool)
            ].tolist(),
        )
    feature_clocks = []
    for name in ("feature-input/verified/features/CORE5_PRE_MAY2024.npz",
                 "development-features/FEATURES.npz"):
        path = args.state / name
        sources[name] = sha(path)
        with np.load(path, allow_pickle=False) as z:
            feature_clocks.extend(z["completed_day_available_us"].tolist())
    feature_clocks = np.asarray(feature_clocks, dtype=np.int64)
    missing = completed[~np.isin(completed, feature_clocks)]
    assert len(missing) == 63
    assert any(p["usable_actual_execution_prices"] < 63 for p in economic.values())
    frozen_checks = {}
    repo = Path(__file__).resolve().parents[2]
    for name, expected in protocol["frozen_artifacts"].items():
        actual = sha(repo / name)
        assert actual == expected
        frozen_checks[name] = actual
    manifest = json.loads((repo / protocol["original_source_manifest"]["path"]).read_text())
    original_sources = {name: sha(repo / name) for name in manifest["versioned_sources"]}
    assert original_sources == manifest["versioned_sources"]
    report = dict(
        schema="FIXED_JULY63_FROZEN_POLICY_TRANSFER_COVERAGE_V1",
        status="BLOCKED_FAITHFUL_DAILY_ECONOMIC_RECONSTRUCTION",
        protocol_SHA256=sha(Path(__file__).parent / "PROTOCOL.json"),
        required_completed_step_first=date(completed[0]),
        required_completed_step_last=date(completed[-1]),
        cached_serialized_feature_steps_present=int(np.isin(completed, feature_clocks).sum()),
        missing_serialized_feature_completed_us=missing.tolist(),
        primitive_daily_tables=primitive,
        economic_inputs=economic,
        source_table_SHA256=sources,
        frozen_artifact_checks=frozen_checks,
        original_versioned_source_count=len(original_sources),
        original_versioned_sources_byte_verified=True,
        official_market_download_bytes=0,
        new_model_fits=0,
        scaler_updates=0,
        policy_inference_calls=0,
        daily_wallets_run=0,
        native_wallets_run=0,
        reason="Daily candles cannot reproduce observed00:01 trade opens or strictly-prior minute funding marks. No allowed minute-archive acquisition; no silent substitute.",
        feature_reconstruction="Primitive counts reported independently of outcomes; original10asset feature/mask builder must be reused. Missing serialized rows were not built or certified here.",
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as file:
        json.dump(report, file, indent=2, sort_keys=True)
        file.write("\n")
    print(json.dumps(dict(status=report["status"], economic_inputs={
        s: {k: v for k, v in p.items() if not k.startswith("missing")}
        for s, p in economic.items()
    })))


if __name__ == "__main__":
    main()
