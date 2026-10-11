"""Independent CSV arithmetic, joint bootstrap and fixed-inference audit, no fits."""

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import torch

from .core import DAY_US, SYMBOLS
from .run import ROOT, predict, sha, utc_us, write_json
from .sharpe import ARMS, PROPOSAL_SHA, PositionLSTM, prepare, verify_predecessor


def independent_sharpe(values):
    values = np.asarray(values, dtype=float)
    if len(values) < 2 or not np.isfinite(values).all() or values.std(ddof=0) <= 0:
        return None
    return float(values.mean() / values.std(ddof=0) * np.sqrt(365))


def assert_scalar(actual, expected, tolerance=1e-12):
    if actual is None or expected is None:
        assert actual is expected
        return 0.0
    residual = abs(actual - expected)
    assert residual < tolerance
    return residual


def receipt_gates(block_increments, increments, delta, ci):
    """Keep NumPy comparisons as JSON-safe booleans without changing thresholds."""
    return {
        "positive_in_at_least_two_blocks": bool(sum(x > 0 for x in block_increments) >= 2),
        "positive_in_at_least_two_seeds": bool(sum(x > 0 for x in increments) >= 2),
        "aggregate_ensemble_increment_positive": bool(delta > 0),
        "bootstrap_lower_positive": bool(ci is not None and ci[0] > 0),
    }


def audit(state, archive, run_number=None):
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.set_grad_enabled(False)
    result = json.loads((state / "RESULT.json").read_text())
    assert result["lstm_fits_this_attempt"] == 6 and result["updates_this_attempt"] == 6144
    assert (
        result["wallet_accounts"]
        == result["new_gp_fit_calls"]
        == result["new_scaler_fit_calls"]
        == 0
    )
    assert sha((state / "POSITIONS.csv").read_bytes()) == result["positions_sha256"]
    assert sha(archive.read_bytes()) == result["source_archive_sha256"]
    assert result["proposal_sha256"] == PROPOSAL_SHA
    audit_path = "modules/slow_momentum_cpd/audit_sharpe.py"
    for path, identity in result["source_files"].items():
        published = subprocess.check_output(
            ["git", "show", result["source_commit"] + ":" + path], cwd=ROOT
        )
        assert sha(published) == identity
        if path != audit_path:
            assert sha((ROOT / path).read_bytes()) == identity
    publication = json.loads((state / "PREFIT_PUBLICATION.json").read_text())
    assert publication["remote_sha"] == publication["local_sha"] == result["source_commit"]
    assert publication["remote_verified_before_fit"] is True
    preserved = verify_predecessor()
    proposal, available, _, vol, train_rows, train_x, target, blocks, _ = prepare(archive)
    assert len(train_rows) == result["train_samples"] == 2526
    assert result["preflight"]["latest_training_label_end_us"] < utc_us("2023-01-01")
    with (state / "POSITIONS.csv").open() as file:
        records = list(csv.DictReader(file))
    assert len(records) == sum(len(b["times"]) * 5 for b in blocks) == 2415
    assert len({(r["block"], r["available_us"], r["symbol"]) for r in records}) == len(records)
    expected_order = [
        (b["dates"][0], str(available[t]), symbol)
        for b in blocks
        for t in b["times"]
        for symbol in SYMBOLS
    ]
    assert [(r["block"], r["available_us"], r["symbol"]) for r in records] == expected_order
    maximum_inference_residual = 0.0
    maximum_metric_residual = 0.0
    loaded = {}
    pairs = {}
    for fit in result["fits"]:
        arm, seed = fit["arm"], fit["seed"]
        rng = np.random.default_rng(seed)
        index_hash = hashlib.sha256()
        for _ in range(1024):
            index_hash.update(rng.integers(0, len(train_rows), size=128).astype("<i8").tobytes())
        torch.manual_seed(seed)
        model = PositionLSTM()
        initial = sha(b"".join(v.detach().numpy().tobytes() for v in model.state_dict().values()))
        assert initial == fit["initial_sha256"]
        assert fit["parameters"] == 1809 and fit["updates"] == 1024 and fit["adam_ages"] == [1024]
        path = state / f"{arm}-seed{seed}.pt"
        assert sha(path.read_bytes()) == fit["checkpoint_sha256"]
        cp = torch.load(path, map_location="cpu", weights_only=True)
        assert cp["updates"] == 1024 and cp["seed"] == seed
        assert cp["batch_indices_sha256"] == fit["batch_indices_sha256"] == index_hash.hexdigest()
        assert sorted({int(v["step"]) for v in cp["optimizer"]["state"].values()}) == [1024]
        pairs.setdefault(seed, []).append(cp)
        model.load_state_dict(cp["model"])
        loaded[(arm, seed)] = model
        x = train_x.copy()
        if arm == "trend":
            x[:, :, 8:] = 0
        position = predict(model, x)
        z = position * target
        final = fit["diagnostics"][-1]
        assert final["update"] == 1024
        maximum_metric_residual = max(
            maximum_metric_residual,
            assert_scalar(independent_sharpe(z), final["full_train_pooled_sharpe"]),
        )
        assert_scalar(float(z.mean()), final["captured_mean"], 1e-15)
        assert_scalar(float(z.var()), final["captured_variance"], 1e-15)
        assert_scalar(float(position.var()), final["position_variance"], 1e-15)
        a, b = final["full_train_pooled_sharpe"], fit["diagnostics"][-3]["full_train_pooled_sharpe"]
        drift = None if a is None or b is None else abs(a - b)
        assert_scalar(drift, fit["tail_sharpe_absolute_drift"])
        assert fit["tail_drift_exceeds_002"] == (None if drift is None else drift > 0.02)
    for pair in pairs.values():
        assert len(pair) == 2 and torch.equal(pair[0]["torch_rng"], pair[1]["torch_rng"])
        assert pair[0]["numpy_rng"] == pair[1]["numpy_rng"]
    joint_blocks = []
    seed_days = {arm: [[] for _ in result["seeds"]] for arm in ARMS}
    block_increments = []
    invalid_blocks = []
    for block, report in zip(blocks, result["blocks"], strict=True):
        selected = [r for r in records if r["block"] == block["dates"][0]]
        shape = block["mask"].shape
        eligible = np.array([int(r["eligible"]) for r in selected], dtype=bool).reshape(shape)
        np.testing.assert_array_equal(eligible, block["mask"])
        assert int(eligible.sum()) == report["eligible_decisions"]
        expected_clock = np.arange(
            utc_us(block["dates"][0]), utc_us(block["dates"][1]) - DAY_US, DAY_US
        )
        np.testing.assert_array_equal(block["clock"], expected_clock)
        assert all(int(r["label_end_us"]) == int(r["available_us"]) + DAY_US for r in selected)
        assert all(int(r["label_end_us"]) < utc_us(block["dates"][1]) for r in selected)
        labels = np.array(
            [
                float(r["scaled_next_return"]) if r["scaled_next_return"] else np.nan
                for r in selected
            ]
        ).reshape(shape)
        current_vol = np.array(
            [float(r["daily_vol"]) if r["daily_vol"] else np.nan for r in selected]
        ).reshape(shape)
        np.testing.assert_array_equal(current_vol, vol[block["times"]])
        np.testing.assert_array_equal(labels[eligible], block["outcomes"][eligible])
        missing_count = int((eligible & ~np.isfinite(labels)).sum())
        assert missing_count == report["missing_eligible_outcomes"]
        block_invalid = missing_count > 0
        captured = {}
        computed_scores = {}
        for arm in ARMS:
            seed_position = np.array(
                [
                    [float(r[arm + "_seed" + str(seed)]) for r in selected]
                    for seed in result["seeds"]
                ]
            ).reshape((3, *shape))
            assert np.isfinite(seed_position).all() and np.max(np.abs(seed_position)) <= 1
            assert np.count_nonzero(seed_position[:, ~eligible]) == 0
            ensemble = np.array([float(r[arm + "_ensemble"]) for r in selected]).reshape(shape)
            np.testing.assert_array_equal(ensemble, seed_position.mean(axis=0))
            for si, seed in enumerate(result["seeds"]):
                x = block["x"].copy()
                if arm == "trend":
                    x[:, :, 8:] = 0
                repeated = predict(loaded[(arm, seed)], x)
                maximum_inference_residual = max(
                    maximum_inference_residual,
                    float(np.max(np.abs(repeated - seed_position[si][eligible]))),
                )
                z = np.zeros(shape)
                z[eligible] = seed_position[si][eligible] * labels[eligible]
                daily = z.sum(axis=1) / 5
                seed_days[arm][si].append(daily)
                score = independent_sharpe(daily)
                block_invalid |= score is None
                if report["status"] == "VALID_RAW_POLICY_PROXY":
                    maximum_metric_residual = max(
                        maximum_metric_residual,
                        assert_scalar(score, report["arms"][arm]["seeds"][si]["sharpe"]),
                    )
            z = np.zeros(shape)
            z[eligible] = ensemble[eligible] * labels[eligible]
            captured[arm] = z
            daily = z.sum(axis=1) / 5
            computed_scores[arm] = independent_sharpe(daily)
            block_invalid |= computed_scores[arm] is None
            if report["status"] == "VALID_RAW_POLICY_PROXY":
                expected = report["arms"][arm]["ensemble"]
                for key, actual in (
                    ("sharpe", computed_scores[arm]),
                    ("mean_daily_proxy_return", float(daily.mean())),
                    ("daily_proxy_std", float(daily.std())),
                ):
                    maximum_metric_residual = max(
                        maximum_metric_residual, assert_scalar(actual, expected[key])
                    )
        if block_invalid:
            assert report["status"] == "INVALID_POLICY_EVALUATION"
            assert report["ensemble_sharpe_increment"] is None
            invalid_blocks.append(block["dates"])
        else:
            assert report["status"] == "VALID_RAW_POLICY_PROXY"
            delta = computed_scores["trend_cpd"] - computed_scores["trend"]
            block_increments.append(delta)
            assert_scalar(delta, report["ensemble_sharpe_increment"])
        joint_blocks.append((block["clock"], np.stack([captured[a] for a in ARMS], axis=2)))
    if invalid_blocks:
        assert result["status"] == "INVALID_POLICY_EVALUATION"
        assert result["aggregate"] is result["gates"] is None
        assert result["bootstrap"]["status"] == "NOT_RUN_INVALID_INPUT"
        gates = None
    else:
        joined = np.concatenate([joint for _, joint in joint_blocks])
        delta = independent_sharpe(joined[:, :, 1].sum(axis=1) / 5) - independent_sharpe(
            joined[:, :, 0].sum(axis=1) / 5
        )
        assert_scalar(delta, result["aggregate"]["ensemble_sharpe_increment"])
        increments = [
            independent_sharpe(np.concatenate(seed_days["trend_cpd"][i]))
            - independent_sharpe(np.concatenate(seed_days["trend"][i]))
            for i in range(3)
        ]
        np.testing.assert_allclose(
            increments, result["aggregate"]["seed_sharpe_increments"], atol=1e-12
        )
        bs = proposal["scoring"]["bootstrap"]
        rng = np.random.default_rng(bs["seed"])
        draws, invalid = [], []
        for replicate in range(bs["replicates"]):
            segments = []
            for dates, joint in joint_blocks:
                assert np.all(np.diff(dates) == DAY_US)
                starts = rng.integers(
                    0,
                    len(dates) - bs["block_days"] + 1,
                    size=int(np.ceil(len(dates) / bs["block_days"])),
                )
                index = np.concatenate([np.arange(s, s + bs["block_days"]) for s in starts])[
                    : len(dates)
                ]
                segments.append(joint[index].sum(axis=1) / 5)
            sampled = np.concatenate(segments)
            a, b = independent_sharpe(sampled[:, 0]), independent_sharpe(sampled[:, 1])
            if a is None or b is None:
                invalid.append(replicate)
            else:
                draws.append(b - a)
        assert invalid == result["bootstrap"]["invalid_indices"]
        assert len(draws) == result["bootstrap"]["valid_replicates"]
        ci = None if invalid else np.percentile(draws, [2.5, 97.5])
        if ci is None:
            assert result["bootstrap"]["ci95"] is None
        else:
            np.testing.assert_allclose(ci, result["bootstrap"]["ci95"], atol=1e-12)
        gates = receipt_gates(block_increments, increments, delta, ci)
        assert gates == result["gates"]
        expected_status = (
            "INVALID_POLICY_EVALUATION"
            if invalid
            else "RAW_POLICY_INCREMENT_ESTABLISHED_NATIVE_REQUIRED"
            if all(gates.values())
            else "STOP_RAW_POLICY_INCREMENT_NOT_ESTABLISHED"
        )
        assert result["status"] == expected_status
    assert maximum_inference_residual == 0 and maximum_metric_residual < 1e-12
    receipt = {
        "status": "PASS",
        "auditor_revision": "JSON_SAFE_GATE_RECEIPT_V2",
        "auditor_fit_source_sha256": result["source_files"][audit_path],
        "auditor_executed_sha256": sha((ROOT / audit_path).read_bytes()),
        "auditor_execution_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "readonly_audit_run_number": run_number,
        "auditor_change": (
            "Builtin bool receipt conversion and explicit auditor identity; "
            "scientific source/results unchanged"
        ),
        "predecessor_before": preserved,
        "declared_result_status": result["status"],
        "result_sha256": sha((state / "RESULT.json").read_bytes()),
        "record_count": len(records),
        "decision_mask": "RECONCILED",
        "strict_label_maturity": "PASS",
        "current_vol_next_return_alignment": "PASS",
        "fixed_five_asset_cash_denominator": "PASS",
        "validation_repeated_inference_sets": 18,
        "training_repeated_inference_sets": 6,
        "maximum_inference_residual": maximum_inference_residual,
        "maximum_metric_residual": maximum_metric_residual,
        "paired_initial_rng_batches_and_adam1024": "PASS",
        "bootstrap": "INDEPENDENT_JOINT_DATE_NONLINEAR_RECOMPUTATION",
        "invalid_input_blocks": invalid_blocks,
        "gates": gates,
        "new_fits": 0,
        "wallets": 0,
        "predecessor_after": verify_predecessor(),
        "native_economic_audit": "NOT_RUN_NO_NATIVE_ACCOUNT",
    }
    write_json(state / "SAVED_POLICY_AUDIT.json", receipt)
    print(json.dumps(receipt, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--run-number", type=int, default=None)
    parser.add_argument(
        "--archive", type=Path, default=Path("/workspace/slow-momentum-state/source/features.zip")
    )
    args = parser.parse_args()
    audit(args.state, args.archive, args.run_number)


if __name__ == "__main__":
    main()
