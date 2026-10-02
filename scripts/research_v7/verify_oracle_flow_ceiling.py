"""Independent raw-window, split and oracle arithmetic checks; no refitting."""
import json
from datetime import timedelta
from pathlib import Path

import numpy as np
import polars as pl
from xgboost import XGBRegressor

from quant import resources
from quant.paths import ROOT
from quant.research_fast.dataset import (
    START, DAY_US, STREAMS, ShardSpec, FastSequenceDataset, day_us, file_sha,
)


def main():
    resources.status()
    report_path = ROOT / "reports/fast_research/V7_ORACLE_FLOW_HORIZON_20261002_V1.json"
    report = json.loads(report_path.read_text())
    run = Path(report["run_dir"])
    complete = json.loads((run / "COMPLETE.json").read_text())
    assert complete["report_sha256"] == file_sha(report_path)
    for name, sha in report["artifacts"].items():
        assert file_sha(run / name) == sha, name
    for name, sha in report["binding"]["source_hashes"].items():
        assert file_sha(ROOT / name) == sha, name
    shards = [ShardSpec.from_manifest(ROOT / name) for name in report["binding"]["manifests"]]
    dataset = FastSequenceDataset(shards, mode="smoke")
    frame = pl.read_parquet(run / "oracle_common_endpoints.parquet")
    decisions = frame["decision_us"].to_numpy()
    first = day_us(START)
    train = decisions < first + 12 * DAY_US - 3_600_000_000 - 3_610_000_000
    validation = (decisions >= first + 12 * DAY_US) & (
        decisions + 3_610_000_000 <= first + 14 * DAY_US - 3_600_000_000)
    test_mask = (decisions >= first + 14 * DAY_US) & (
        decisions + 3_610_000_000 <= first + 21 * DAY_US)
    assert not np.any(train & validation) and not np.any(validation & test_mask)
    assert not np.any(train & test_mask)
    assert {"train": int(train.sum()), "validation": int(validation.sum()), "test": int(test_mask.sum())} == report["label_check"]["counts"]
    assert np.all(np.diff(decisions) > 0)
    probes = np.unique([0, len(frame) - 1, int(np.flatnonzero(train)[-1]),
                        int(np.flatnonzero(validation)[0]), int(np.flatnonzero(validation)[-1]),
                        int(np.flatnonzero(test_mask)[0]), int(np.flatnonzero(test_mask)[len(np.flatnonzero(test_mask)) // 2]),
                        int(np.flatnonzero(test_mask)[-1])])
    raw_checks = 0
    maximum_flow_error = 0.0
    for index in probes:
        decision = int(decisions[index])
        joint = dataset.joint_rows(decision - 3_600_000_000, decision + 3_610_000_000)
        row = frame.row(int(index), named=True)
        times = joint["timestamp"].to_numpy()
        for stream in STREAMS:
            for minutes in (5, 15, 30, 60):
                stop = decision + minutes * 60_000_000
                flow_slice = joint.filter(pl.col("timestamp").is_between(decision, stop, closed="left"))
                assert len(flow_slice) == minutes * 12
                buy = flow_slice[f"{stream}__aggressive_buy_notional"].to_numpy()
                sell = flow_slice[f"{stream}__aggressive_sell_notional"].to_numpy()
                expected_flow = (buy - sell).sum() / ((buy + sell).sum() + 1e-12)
                error = abs(expected_flow - row[f"{stream}__flow_{minutes}m"])
                maximum_flow_error = max(maximum_flow_error, error)
                assert error <= 1e-12
                entry_index = int(np.flatnonzero(times == decision + 5_000_000)[0])
                exit_index = int(np.flatnonzero(times == stop + 5_000_000)[0])
                entry = joint[f"{stream}__open"][entry_index]
                exit_price = joint[f"{stream}__open"][exit_index]
                assert abs(exit_price / entry - 1 - row[f"{stream}__return_{minutes}m_proxy"]) <= 1e-14
                assert joint[f"{stream}__first_trade_us"][entry_index] == row[f"{stream}__entry_{minutes}m_us"]
                assert joint[f"{stream}__first_trade_us"][exit_index] == row[f"{stream}__exit_{minutes}m_us"]
                assert row[f"mature_{minutes}m_us"] == stop + 10_000_000
                raw_checks += 1
        past = joint.filter(pl.col("timestamp") < decision)
        assert len(past) == 720
        assert max(past[f"{s}__available_us"].max() for s in STREAMS) <= decision
        for symbol in ("BTCUSDT", "ETHUSDT"):
            rv = np.log(np.nansum(past[f"spot_{symbol}__return_5s"].to_numpy() ** 2) + 1e-12)
            liquidity = np.log1p(past[f"spot_{symbol}__quote_notional"].to_numpy().sum())
            basis = past[f"perp_{symbol}__close"][-1] / past[f"spot_{symbol}__close"][-1] - 1
            assert abs(rv - row[f"{symbol}__past_logrv"]) <= 1e-12
            assert abs(liquidity - row[f"{symbol}__past_log_liquidity"]) <= 1e-12
            assert abs(basis - row[f"{symbol}__past_basis"]) <= 1e-12
    test = frame.filter(pl.Series(test_mask))
    arithmetic = []
    for result in report["oracle_impact_models"]:
        symbol, minutes = result["spot_target"], result["horizon_minutes"]
        prediction = np.load(run / f"oracle-{symbol}-{minutes}m-predictions.npy", allow_pickle=False)
        model = XGBRegressor()
        model.load_model(run / f"oracle-{symbol}-{minutes}m.json")
        names = [f"{s}__flow_{minutes}m" for s in STREAMS] + [
            f"{symbol}__{n}" for n in ("past_logrv", "past_log_liquidity", "past_basis")]
        reproduced = model.predict(test.select(names).to_numpy()) * result["training_only_target_scale"] + result["training_only_target_mean"]
        assert np.allclose(reproduced, prediction, rtol=1e-6, atol=1e-9)
        indices, last_exit = [], -1
        for i, value in enumerate(prediction):
            if value < .0035 or test[f"spot_{symbol}__entry_{minutes}m_us"][i] < last_exit:
                continue
            indices.append(i)
            last_exit = test[f"spot_{symbol}__exit_{minutes}m_us"][i]
        assert len(indices) == result["gross_edge_diagnostic"]["roundtrips"]
        actual = test[f"spot_{symbol}__return_{minutes}m_proxy"].to_numpy()[indices] * 10000
        diagnostic = result["gross_edge_diagnostic"]
        assert abs(float(actual.sum()) - diagnostic["gross_sum_equal_notional_bps_not_nav"]) <= 1e-10
        if len(indices):
            assert abs(float(actual.mean()) - diagnostic["break_even_equal_notional_roundtrip_cost_bps"]) <= 1e-12
            for cost in diagnostic["cost_sensitivity"]:
                assert abs(float(actual.mean() - cost["total_bps"]) - cost["oracle_net_mean_bps_not_apr"]) <= 1e-12
        else:
            assert diagnostic["break_even_equal_notional_roundtrip_cost_bps"] is None
        assert diagnostic["portfolio_net_apr"] is None
        arithmetic.append({"symbol": symbol, "minutes": minutes, "verified_roundtrips": len(indices),
                           "prediction_count": len(prediction), "maximum_prediction_reproduction_error": float(np.max(np.abs(reproduced - prediction)))})
    output = {"status": "ORACLE_V7_LEAKAGE_AND_DIAGNOSTIC_ARITHMETIC_CHECK_PASS",
        "scope": "raw-window sparse labels/current-state; all serialized model predictions; all fixed oracle edge/cost arithmetic; NO refit",
        "report_sha256": file_sha(report_path), "script_sha256": file_sha(Path(__file__)),
        "probed_common_indices": list(map(int, probes)), "raw_stream_horizon_probes": raw_checks,
        "maximum_flow_summation_difference": float(maximum_flow_error),
        "splits_disjoint_with_60m_embargo_and_max_maturity": True,
        "current_state_only_closed_past_bars": True,
        "model_and_arithmetic": arithmetic, "gpu_hours": 0, "shared_cgroup": resources.status()}
    target = ROOT / "reports/fast_research/V7_ORACLE_FLOW_HORIZON_CORRECTNESS_20261002_V1.json"
    with target.open("x") as handle:
        json.dump(output, handle, indent=2, allow_nan=False)
    print(json.dumps(output, indent=2), flush=True)


if __name__ == "__main__":
    main()
