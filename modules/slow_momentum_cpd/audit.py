"""Read-only saved-forecast reconciliation and repeat frozen inference, no fitting."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import torch
from scipy.stats import rankdata

from .core import DAY_US, SYMBOLS, FrozenGP, Scaler, sample_index, trend_features
from .run import EXPERIMENT, ROOT, TrendLSTM, load_close, sha, utc_us, write_json


def rank_correlation(a, b):
    # Independent rank-centering formula rather than the experiment metrics helper.
    ra = rankdata(a) - (len(a) + 1) / 2
    rb = rankdata(b) - (len(b) + 1) / 2
    return float(np.dot(ra, rb) / np.sqrt(np.dot(ra, ra) * np.dot(rb, rb)))


def audit(state, repeat_inference=True):
    result = json.loads((state / "RESULT.json").read_text())
    protocol = json.loads((EXPERIMENT / "PROTOCOL.json").read_text())
    frozen = json.loads((state / "FROZEN_TRAINING.json").read_text())
    assert result["protocol_sha256"] == sha((EXPERIMENT / "PROTOCOL.json").read_bytes())
    assert result["frozen_training_sha256"] == sha((state / "FROZEN_TRAINING.json").read_bytes())
    assert result["prediction_sha256"] == sha((state / "PREDICTIONS.csv").read_bytes())
    for source, identity in result["source_files"].items():
        assert sha((ROOT / source).read_bytes()) == identity
    cutoff = utc_us("2023-01-01")
    assert frozen["latest_training_label_end_us"] < cutoff
    assert frozen["scaler_latest_available_us"] < cutoff
    assert frozen["fit"]["latest_fit_available_us"] < cutoff - DAY_US
    assert len(frozen["fit"]["identities"]) == 320
    assert result["lstm_fits"] == 6 and result["scientific_attempts"] == 1
    assert result["validation_fit_calls"] == 0 and result["wallet_accounts"] == 0
    available, close, _ = load_close(state / "source/features.zip", protocol)
    trend, returns, vol = trend_features(close)
    gp = FrozenGP(
        frozen["mean"],
        frozen["scale"],
        np.asarray(frozen["stationary_log_parameters"]),
        np.asarray(frozen["change_log_parameters"]),
        np.asarray(frozen["locations"]),
        21,
        frozen["fit"],
    )
    scaler = Scaler(np.asarray(frozen["scaler_mean"]), np.asarray(frozen["scaler_scale"]))
    all_features = np.concatenate((trend, gp.transform(returns)), axis=2)
    inputs = scaler.transform(all_features)
    train_rows = sample_index(
        trend, returns, vol, available, *map(utc_us, protocol["training"]["dates"])
    )
    assert len(train_rows) == frozen["training_samples"] == result["train_samples"]
    assert int(available[train_rows[:, 0] + 1].max()) == frozen["latest_training_label_end_us"]
    used = np.zeros(close.shape, dtype=bool)
    for t, asset in train_rows:
        used[t - 62 : t + 1, asset] = True
    assert int(used.sum()) == frozen["scaler_unique_rows"]
    np.testing.assert_array_equal(all_features[used].mean(axis=0), scaler.mean)
    np.testing.assert_array_equal(all_features[used].std(axis=0), scaler.scale)
    gp_used = np.zeros(close.shape, dtype=bool)
    gp_axis = np.asarray(frozen["fit"]["identities"])
    assert np.bincount(gp_axis[:, 1], minlength=5).tolist() == [64] * 5
    assert int(available[gp_axis[:, 0]].max()) == frozen["fit"]["latest_fit_available_us"]
    for t, asset in gp_axis:
        assert utc_us("2021-01-01") <= available[t] < cutoff - DAY_US
        assert np.isfinite(returns[t - 21 : t + 1, asset]).all()
        gp_used[t - 21 : t + 1, asset] = True
    assert int(gp_used.sum()) == frozen["fit"]["scaler_unique_return_rows"]
    assert float(returns[gp_used].mean()) == frozen["mean"]
    assert float(returns[gp_used].std()) == frozen["scale"]
    with (state / "PREDICTIONS.csv").open() as file:
        records = list(csv.DictReader(file))
    assert [b["dates"] for b in result["blocks"]] == protocol["validation"]
    assert {r["block"] for r in records} == {dates[0] for dates in protocol["validation"]}
    checked = []
    maximum_metric_residual = 0.0
    maximum_prediction_residual = 0.0
    blocks_differences = []
    block_skills = []
    rank_increments = []
    seed_loss_differences = np.zeros(3)
    for block in result["blocks"]:
        subset = [r for r in records if r["block"] == block["dates"][0]]
        expected_rows = sample_index(trend, returns, vol, available, *map(utc_us, block["dates"]))
        row_map = {int(stamp): t for t, stamp in enumerate(available)}
        identities = np.array(
            [(row_map[int(r["available_us"])], SYMBOLS.index(r["symbol"])) for r in subset]
        )
        np.testing.assert_array_equal(identities, expected_rows)
        assert len(subset) == len({(r["available_us"], r["symbol"]) for r in subset})
        assert all(int(r["label_end_us"]) - int(r["available_us"]) == DAY_US for r in subset)
        assert all(int(r["label_end_us"]) < utc_us(block["dates"][1]) for r in subset)
        y = np.array([float(r["scaled_next_return"]) for r in subset])
        independent_y = (
            returns[identities[:, 0] + 1, identities[:, 1]]
            / vol[identities[:, 0], identities[:, 1]]
        )
        np.testing.assert_array_equal(y, independent_y)
        ensemble = {}
        loss_per_seed = {}
        independent_metrics = {}
        for arm, prefix in (("trend", "trend"), ("trend_cpd", "cpd")):
            p = np.array(
                [
                    [float(r[f"{prefix}_seed{seed}"]) for r in subset]
                    for seed in protocol["training"]["seeds"]
                ]
            )
            ensemble[arm] = p.mean(axis=0)
            loss_per_seed[arm] = np.sum((p - y) ** 2, axis=1)
            measured_mse = float(np.dot(ensemble[arm] - y, ensemble[arm] - y) / len(y))
            residual = abs(measured_mse - block[arm]["mse"])
            maximum_metric_residual = max(maximum_metric_residual, residual)
            assert residual < 1e-12
            daily_ic = []
            for stamp in np.unique(identities[:, 0]):
                selected = identities[:, 0] == stamp
                if selected.sum() >= 3:
                    daily_ic.append(rank_correlation(y[selected], ensemble[arm][selected]))
            residual = abs(float(np.mean(daily_ic)) - block[arm]["mean_daily_rank_ic"])
            maximum_metric_residual = max(maximum_metric_residual, residual)
            assert residual < 1e-12
            independent_metrics[arm] = (measured_mse, float(np.mean(daily_ic)))
            assert block[arm]["n"] == len(y)
            assert block[arm]["days"] == len(np.unique(identities[:, 0]))
            assert block[arm]["rank_days"] == len(daily_ic)
            # Direct model call independent of the experiment's predict()/sequences().
            for index, seed in enumerate(protocol["training"]["seeds"]):
                checkpoint = state / f"{arm}-seed{seed}.pt"
                receipt = next(f for f in result["fits"] if f["arm"] == arm and f["seed"] == seed)
                assert sha(checkpoint.read_bytes()) == receipt["checkpoint_sha256"]
                saved = torch.load(checkpoint, map_location="cpu", weights_only=False)
                assert saved["updates"] == 256 and saved["seed"] == seed
                assert {int(v["step"]) for v in saved["optimizer"]["state"].values()} == {256}
                if not repeat_inference:
                    continue
                model = TrendLSTM()
                model.load_state_dict(saved["model"])
                model.eval()
                repeated = []
                for start in range(0, len(identities), 256):
                    axis = identities[start : start + 256]
                    x = np.stack([inputs[t - 62 : t + 1, a] for t, a in axis]).astype("float32")
                    if arm == "trend":
                        x[:, :, 8:] = 0
                    with torch.no_grad():
                        repeated.extend(model(torch.from_numpy(x)).tolist())
                delta = float(np.max(np.abs(np.asarray(repeated) - p[index])))
                maximum_prediction_residual = max(maximum_prediction_residual, delta)
                assert delta == 0
        seed_loss_differences += loss_per_seed["trend"] - loss_per_seed["trend_cpd"]
        error_a = (ensemble["trend"] - y) ** 2
        error_b = (ensemble["trend_cpd"] - y) ** 2
        differences = error_a - error_b
        daily = np.array(
            [differences[identities[:, 0] == t].mean() for t in np.unique(identities[:, 0])]
        )
        assert np.all(np.diff(np.unique(identities[:, 0])) == 1)
        blocks_differences.append(daily)
        skill = 1 - independent_metrics["trend_cpd"][0] / independent_metrics["trend"][0]
        rank_increment = independent_metrics["trend_cpd"][1] - independent_metrics["trend"][1]
        assert abs(skill - block["relative_mse_skill"]) < 1e-12
        assert abs(rank_increment - block["daily_rank_ic_increment"]) < 1e-12
        block_skills.append(skill)
        rank_increments.append(rank_increment)
        checked.append({"dates": block["dates"], "forecast_rows": len(y), "days": len(daily)})
    # Independent moving-window table bootstrap, same predeclared RNG/cadence.
    rng = np.random.default_rng(9901)
    bootstrap = []
    for _ in range(1000):
        samples = []
        for values in blocks_differences:
            table = np.lib.stride_tricks.sliding_window_view(values, 14)
            index = rng.integers(0, len(table), int(np.ceil(len(values) / 14)))
            samples.append(table[index].reshape(-1)[: len(values)])
        bootstrap.append(float(np.mean(np.concatenate(samples))))
    np.testing.assert_array_equal(
        np.quantile(bootstrap, [0.025, 0.975]), result["bootstrap"]["ci95"]
    )
    assert sum(b["forecast_rows"] for b in checked) == len(records)
    mean_improvement = float(np.mean(np.concatenate(blocks_differences)))
    assert mean_improvement == result["bootstrap"]["mean_daily_loss_improvement"]
    conditions = {
        "positive_skill_in_at_least_two_blocks": int((np.asarray(block_skills) > 0).sum()) >= 2,
        "positive_skill_for_at_least_two_seeds": int((seed_loss_differences > 0).sum()) >= 2,
        "aggregate_date_mean_improvement_positive": mean_improvement > 0,
        "bootstrap_lower_bound_positive": float(np.quantile(bootstrap, 0.025)) > 0,
        "mean_rank_ic_increment_at_least_001": float(np.mean(rank_increments)) >= 0.01,
    }
    assert conditions == result["gate_conditions"]
    expected_status = (
        "PREDICTION_GATE_PASS_NATIVE_REQUIRED"
        if all(conditions.values())
        else "STOP_PREDICTION_INCREMENT_NOT_ESTABLISHED"
    )
    assert result["status"] == expected_status
    for seed in protocol["training"]["seeds"]:
        pair = [f for f in result["fits"] if f["seed"] == seed]
        assert len(pair) == 2 and pair[0]["initial_sha256"] == pair[1]["initial_sha256"]
        a = torch.load(state / f"trend-seed{seed}.pt", weights_only=False)
        b = torch.load(state / f"trend_cpd-seed{seed}.pt", weights_only=False)
        assert a["numpy_rng"] == b["numpy_rng"]  # identical consumed minibatch RNG
        assert torch.equal(a["torch_rng"], b["torch_rng"])
    return {
        "status": "PASS",
        "source_identity": "ALL_REAL_FIT_SOURCES_UNCHANGED",
        "checked_rows": len(records),
        "blocks": checked,
        "maximum_metric_residual": maximum_metric_residual,
        "maximum_repeat_prediction_residual": maximum_prediction_residual
        if repeat_inference
        else None,
        "independent_seed_loss_improvement_sums": seed_loss_differences.tolist(),
        "maturity_scalers_GP": "TRAINING_ONLY_PASS",
        "same_axis_initialization_RNG_updates": "PASS",
        "bootstrap_reconciliation": "EXACT",
        "gate_reconciliation": conditions,
        "gate_decision": expected_status,
        "native_financial_audit": "NOT_APPLICABLE_ZERO_WALLETS",
        "new_fit_calls": 0,
        "new_wallets": 0,
        "new_provider_downloads": 0,
        "repeat_frozen_inference_sets": 18 if repeat_inference else 0,
        "audit_source_sha256": sha(Path(__file__).read_bytes()),
        "GP_training_status": {k: frozen["fit"][k] for k in ("stationary", "change")},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--metrics-only", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    result = audit(args.state, repeat_inference=not args.metrics_only)
    write_json(args.output or args.state / "SAVED_RESULT_AUDIT.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
