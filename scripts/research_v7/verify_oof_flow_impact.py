"""Critical OOF chronology, raw past features, prediction and cash/NAV checks.

No model refits and no threshold search. This checks actual saved artifacts.
"""
import json
from pathlib import Path

import numpy as np
import polars as pl
from xgboost import XGBRegressor
from sklearn.preprocessing import StandardScaler

from quant import resources
from quant.paths import ROOT
from quant.research_fast.dataset import FastSequenceDataset, ShardSpec, BAR_US, PAST_BARS, STREAMS, feature_matrix, tabular_view, file_sha
from oracle_flow_ceiling import Progress, exclusive_json


def restored_scaler(receipt):
    scaler = StandardScaler()
    scaler.mean_ = np.asarray(receipt["mean"])
    scaler.scale_ = np.asarray(receipt["scale"])
    scaler.var_ = np.asarray(receipt["var"])
    scaler.n_samples_seen_ = receipt["n_samples_seen"]
    scaler.n_features_in_ = len(scaler.mean_)
    return scaler


def normalized(values, receipt):
    return restored_scaler(receipt).transform(values)


def inverse(values, receipt):
    return restored_scaler(receipt).inverse_transform(values)


def near(a, b, tolerance=1e-8):
    if not abs(float(a) - float(b)) <= tolerance:
        raise AssertionError(f"Arithmetic differs: {a}, {b}")


def check_finance(run, minutes, policy, spread, summary, observations):
    prefix = run / f"horizon-{minutes}m" / f"{policy}-{minutes}m-spread{spread}"
    trades = pl.read_parquet(prefix.with_name(prefix.name + "-trades.parquet")).to_dicts()
    daily = pl.read_parquet(prefix.with_name(prefix.name + "-daily.parquet")).to_dicts()
    symbols = ("spot_BTCUSDT", "spot_ETHUSDT")
    fee_rate, extra_rate = .001, (8 + spread) / 20000

    def mark(symbol, stamp, fills):
        times, prices = observations[symbol]
        index = np.searchsorted(times, stamp, side="right") - 1
        closed = (int(times[index]), float(prices[index])) if index >= 0 else None
        fill = fills.get(symbol)
        if fill is not None and (closed is None or fill[0] > closed[0]):
            closed = fill
        if closed is not None:
            assert closed[0] <= stamp
        return closed

    def state_before(stamp):
        cash, qty, fills = 10000., {s: 0. for s in symbols}, {}
        for row in trades:
            if row["event_us"] >= stamp:
                break
            s = row["symbol"]
            cash += ((-1 if row["side"] == "buy" else 1) * row["reference_notional"] - row["fee"] - row["execution_cost"])
            qty[s] += (1 if row["side"] == "buy" else -1) * row["quantity"]
            fills[s] = (row["event_us"], row["price_proxy"])
        return cash, qty, fills

    def nav_at(stamp, cash, qty, fills):
        value = cash
        for s in symbols:
            point = mark(s, stamp, fills)
            assert point is not None or abs(qty[s]) < 1e-12
            if point:
                value += qty[s] * point[1]
        return value

    cash, qty, fills, buys = 10000., {s: 0. for s in symbols}, {}, {}
    gross, cost, notional = 0., 0., 0.
    for row in trades:
        s, stamp = row["symbol"], row["event_us"]
        near(row["reference_notional"], row["quantity"] * row["price_proxy"])
        near(row["fee"], row["reference_notional"] * fee_rate)
        near(row["execution_cost"], row["reference_notional"] * extra_rate)
        assert row["decision_us"] < stamp
        if row["side"] == "buy":
            assert abs(qty[s]) < 1e-12 and s not in buys
            assert row["decision_us"] + 5_000_000 <= stamp <= row["decision_us"] + 7_000_000
            d_cash, d_qty, d_fills = state_before(row["decision_us"])
            near(row["decision_nav"], nav_at(row["decision_us"], d_cash, d_qty, d_fills))
            observed = mark(s, row["decision_us"], d_fills)
            assert observed[0] <= row["decision_us"]
            near(observed[1], row["decision_observed_price"])
            qty[s] = row["quantity"]
            buys[s] = row
            cash -= row["reference_notional"] + row["fee"] + row["execution_cost"]
            assert row["symbol_weight_after"] <= .3 + 1e-10
            assert row["gross_weight_after"] <= .6 + 1e-10
        else:
            assert s in buys
            entry = buys.pop(s)
            assert row["decision_us"] == entry["decision_us"] and row["sample_id"] == entry["sample_id"]
            assert row["decision_us"] + minutes * 60_000_000 + 5_000_000 <= stamp <= row["decision_us"] + minutes * 60_000_000 + 7_000_000
            near(qty[s], row["quantity"])
            gross += row["quantity"] * (row["price_proxy"] - entry["price_proxy"])
            cash += row["reference_notional"] - row["fee"] - row["execution_cost"]
            qty[s] = 0.
        fills[s] = (stamp, row["price_proxy"])
        near(row["cash_after"], cash)
        near(row["nav_after"], nav_at(stamp, cash, qty, fills))
        cost += row["fee"] + row["execution_cost"]
        notional += row["reference_notional"]
        assert cash >= -1e-8
    assert not buys and all(abs(value) < 1e-12 for value in qty.values())
    previous_nav, previous_stamp = 10000., daily[0]["valuation_us"] - 86_400_000_000
    for row in daily:
        stamp = row["valuation_us"]
        d_cash, d_qty, d_fills = state_before(stamp)
        near(row["cash"], d_cash)
        near(row["BTC_quantity"], d_qty[symbols[0]])
        near(row["ETH_quantity"], d_qty[symbols[1]])
        near(row["nav"], nav_at(stamp, d_cash, d_qty, d_fills))
        day_trades = [t for t in trades if previous_stamp <= t["event_us"] < stamp]
        near(row["fees"], sum(t["fee"] for t in day_trades))
        near(row["execution_costs"], sum(t["execution_cost"] for t in day_trades))
        near(row["turnover"], sum(t["reference_notional"] for t in day_trades) / previous_nav)
        previous_stamp, previous_nav = stamp, row["nav"]
    near(summary["final_nav"], cash)
    near(summary["gross_pnl"], gross)
    near(summary["cost"], cost)
    near(cash - 10000, gross - cost)
    near(summary["net_proxy_return"], cash / 10000 - 1)
    near(summary["gross_proxy_return"], gross / 10000)
    near(summary["estimated_cost"], cost / 10000)
    near(summary["actual_two_sided_reference_notional"], notional)
    if notional:
        near(summary["break_even_roundtrip_cost_bps"], 2 * gross / notional * 10000)
    else:
        assert summary["break_even_roundtrip_cost_bps"] is None
    navs = np.r_[10000., [r["nav"] for r in daily]]
    near(summary["max_drawdown"], -np.min(navs / np.maximum.accumulate(navs) - 1), 1e-12)
    near(summary["conditional_short_window_cagr_proxy"], (cash / 10000) ** (365 / 7) - 1, 1e-12)
    assert summary["long_term_net_apr_proven"] is False and summary["terminal_positions_flat"] is True
    return {"horizon_minutes": minutes, "policy": policy, "spread_bps": spread,
            "trade_events": len(trades), "closed_roundtrips": len(trades) // 2,
            "net_return": summary["net_proxy_return"], "net_cagr_proxy": summary["conditional_short_window_cagr_proxy"],
            "cash_nav_cost_turnover_drawdown_identity_verified": True}


def main():
    resources.status()
    progress = Progress()
    try:
        report_path = ROOT / "reports/fast_research/V7_OOF_FLOW_IMPACT_20261002_V2.json"
        report = json.loads(report_path.read_text())
        run = Path(report["run_dir"])
        assert json.loads((run / "COMPLETE.json").read_text())["report_sha256"] == file_sha(report_path)
        for name, sha in report["artifacts"].items():
            assert file_sha(run / name) == sha, name
        for name, sha in report["binding"]["source_hashes"].items():
            assert file_sha(ROOT / name) == sha, name
        oracle = json.loads((ROOT / "reports/fast_research/V7_ORACLE_FLOW_HORIZON_20261002_V1.json").read_text())
        frame = pl.read_parquet(Path(oracle["run_dir"]) / "oracle_common_endpoints.parquet")
        decisions = np.load(run / "decision_us.npy", allow_pickle=False)
        train = np.load(run / "train_indices.npy", allow_pickle=False)
        validation = np.load(run / "validation_indices.npy", allow_pickle=False)
        test = np.load(run / "test_indices.npy", allow_pickle=False)
        oof_rows = np.load(run / "OOF_indices.npy", allow_pickle=False)
        x = np.load(run / "past_features210.npy", allow_pickle=False)
        assert x.shape == (len(frame), 210) and np.isfinite(x).all()
        assert np.array_equal(decisions, frame["decision_us"].to_numpy())
        assert not set(train) & set(validation) and not set(train) & set(test) and not set(validation) & set(test)
        assert set(oof_rows) <= set(train)
        dataset = FastSequenceDataset([ShardSpec.from_manifest(ROOT / name) for name in oracle["binding"]["manifests"]], mode="smoke")
        for index in (0, int(train[-1]), int(validation[0]), int(test[0]), int(test[len(test)//2]), len(frame)-1):
            d = int(decisions[index])
            joint = dataset.joint_rows(d - PAST_BARS * BAR_US, d)
            assert max(joint[f"{s}__available_us"].max() for s in STREAMS) <= d
            assert np.array_equal(tabular_view(feature_matrix(joint)), x[index, :204])
            state = [frame[f"{s}__{n}"][index] for s in ("BTCUSDT", "ETHUSDT") for n in ("past_logrv", "past_log_liquidity", "past_basis")]
            assert np.array_equal(np.asarray(state, np.float32), x[index, 204:])
        model_checks = []
        for number, record in enumerate(report["model_receipts"]):
            path = run / record["path"]
            receipt = json.loads((path / "FIT_RECEIPT.json").read_text())
            fit = np.load(path / "fit_indices.npy", allow_pickle=False)
            forecast = np.load(path / "forecast_indices.npy", allow_pickle=False)
            assert np.isin(fit, train).all() and np.all(decisions[fit] + 3_610_000_000 <= receipt["label_deadline_us"])
            assert len(fit) == receipt["input_scaler"]["n_samples_seen"]
            assert np.allclose(np.mean(x[fit], axis=0, dtype=np.float64), receipt["input_scaler"]["mean"], rtol=1e-10, atol=1e-12)
            model = XGBRegressor()
            model.load_model(path / "model.json")
            h, role = receipt["horizon_minutes"], receipt["role"]
            inputs = normalized(x[forecast], receipt["input_scaler"])
            if role.startswith("M1-OOF"):
                assert not set(fit) & set(forecast)
                assert np.max(decisions[fit] + 3_610_000_000) + 3_600_000_000 <= np.min(decisions[forecast])
                actual = np.load(path / "forecast_original_units.npy", allow_pickle=False)
            elif role == "M1-final":
                assert np.array_equal(fit, train) and np.array_equal(forecast, np.r_[validation, test])
                actual = np.concatenate([np.load(run / f"horizon-{h}m" / f"M1-{split}-predicted-flow.npy", allow_pickle=False) for split in ("validation", "test")])
            else:
                assert np.array_equal(fit, oof_rows) and np.array_equal(forecast, np.r_[validation, test])
                if role == "M2-OOF-flow-impact":
                    predicted_scaler = json.loads((run / f"horizon-{h}m" / "PREDICTED_FLOW_SCALER.json").read_text())
                    flows = np.concatenate([np.load(run / f"horizon-{h}m" / f"M1-{split}-predicted-flow.npy", allow_pickle=False) for split in ("validation", "test")])
                    inputs = np.column_stack([inputs, normalized(flows, predicted_scaler)])
                    entire_oof = np.load(run / f"horizon-{h}m" / "OOF-predicted-flow.npy", allow_pickle=False)
                    fitted_flow = np.load(run / f"horizon-{h}m" / "M2-train-predicted-flow.npy", allow_pickle=False)
                    assert np.array_equal(entire_oof[oof_rows], fitted_flow)
                    outside = np.setdiff1d(np.arange(len(frame)), oof_rows)
                    assert np.isnan(entire_oof[outside]).all()
                    assert np.allclose(fitted_flow.mean(axis=0), predicted_scaler["mean"], rtol=1e-10, atol=1e-12)
                    seen_rows = []
                    for block in range(3):
                        block_path = run / f"horizon-{h}m" / f"M1-OOF-{block}"
                        rows = np.load(block_path / "forecast_indices.npy", allow_pickle=False)
                        predictions = np.load(block_path / "forecast_original_units.npy", allow_pickle=False)
                        assert np.array_equal(predictions, entire_oof[rows])
                        seen_rows.extend(rows.tolist())
                    assert np.array_equal(np.sort(seen_rows), oof_rows)
                policy = "OOF_TWO_STAGE" if role.startswith("M2") else "DIRECT"
                actual = np.concatenate([np.load(run / f"horizon-{h}m" / f"{policy}-{split}-return-predictions.npy", allow_pickle=False) for split in ("validation", "test")])
            reproduced = inverse(model.predict(inputs), receipt["target_scaler"])
            assert np.allclose(reproduced, actual, rtol=1e-6, atol=1e-9)
            model_checks.append({"role": role, "horizon_minutes": h, "predictions": len(actual), "max_reproduction_error": float(np.max(np.abs(reproduced - actual))),
                                 "preceding_mature_fit_and_saved_model_verified": True})
            progress.update("核对 OOF 时间/真实预测来源", number + 1, 24, "模型")
        observations = {f"spot_{s}": (np.load(run / f"observed-{s}-times.npy", allow_pickle=False), np.load(run / f"observed-{s}-closes.npy", allow_pickle=False)) for s in ("BTCUSDT", "ETHUSDT")}
        ledgers = []
        for horizon in report["horizons"]:
            for branch in horizon["direct_two_stage_comparison"]:
                for spread, summary in branch["economics"].items():
                    ledgers.append(check_finance(run, horizon["horizon_minutes"], branch["policy"], int(spread), summary, observations))
                    progress.update("核对真实现金/NAV/成本账本", len(ledgers), 24, "账本")
        output = {"status": "V7_OOF_CHRONOLOGY_PREDICTION_AND_FINANCE_CORRECTNESS_PASS",
            "report_sha256": file_sha(report_path), "script_sha256": file_sha(Path(__file__)),
            "source_feature_probes": 6, "actual_model_fits_refit": 0,
            "M2_uses_only_union_of_three_preceding_mature_OOF_predictions": True,
            "direct_and_M2_exact_same_training_rows_and_past_state_scaler": True,
            "model_checks": model_checks, "economic_ledger_checks": ledgers,
            "claim": "Development conditional NAV/CAGR proxies only; no unseen or long-term APR qualification",
            "shared_cgroup": resources.status(), "gpu_hours": 0}
        exclusive_json(ROOT / "reports/fast_research/V7_OOF_FLOW_IMPACT_CORRECTNESS_20261002_V2.json", output)
        print(json.dumps(output, indent=2), flush=True)
    finally:
        progress.stop.set()
        progress.thread.join(timeout=3)


if __name__ == "__main__":
    main()
