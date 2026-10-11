"""Read-only independent checkpoint/CSV/stop/bootstrap audit for attempt3."""

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import torch

from . import sharpe
from .audit_sharpe import assert_scalar, independent_sharpe, receipt_gates
from .continuation import PROPOSAL_SHA, SEEDS, training_data, verify_preservation
from .core import DAY_US, SYMBOLS
from .run import ROOT, predict, sha, utc_us, write_json


def independent_stop(losses, k):
    if k < 1408:
        return False
    return all(len(c) >= 4 and np.all(np.abs(np.diff(c[-4:])) <= 0.02) for c in losses)


def reconcile_statistics(joint_blocks, block_deltas, seed_days, scoring, result, invalid_blocks):
    if invalid_blocks:
        assert result["status"] == "INVALID_POLICY_EVALUATION"
        assert result["aggregate"] is result["gates"] is None
        assert result["bootstrap"]["status"] == "NOT_RUN_INVALID_INPUT"
        assert result["bootstrap"]["replicates"] == 0
        return None
    joined = np.concatenate(joint_blocks).sum(axis=1) / 5
    delta = independent_sharpe(joined[:, 1]) - independent_sharpe(joined[:, 0])
    assert_scalar(delta, result["aggregate"]["ensemble_sharpe_increment"])
    increments = [
        independent_sharpe(np.concatenate(seed_days["trend_cpd"][i]))
        - independent_sharpe(np.concatenate(seed_days["trend"][i]))
        for i in range(3)
    ]
    np.testing.assert_allclose(
        increments, result["aggregate"]["seed_sharpe_increments"], atol=1e-12
    )
    bs = scoring["scoring"]["bootstrap"]
    rng = np.random.default_rng(bs["seed"])
    draws, invalid = [], []
    for replicate in range(bs["replicates"]):
        pieces = []
        for joint in joint_blocks:
            width = bs["block_days"]
            starts = rng.integers(0, len(joint) - width + 1, size=int(np.ceil(len(joint) / width)))
            index = np.concatenate([np.arange(s, s + width) for s in starts])[: len(joint)]
            pieces.append(joint[index].sum(axis=1) / 5)
        sampled = np.concatenate(pieces)
        a, b = independent_sharpe(sampled[:, 0]), independent_sharpe(sampled[:, 1])
        if a is None or b is None:
            invalid.append(replicate)
        else:
            draws.append(b - a)
    assert invalid == result["bootstrap"]["invalid_indices"]
    assert len(draws) == result["bootstrap"]["valid_replicates"]
    assert len(invalid) == result["bootstrap"]["invalid_replicates"]
    ci = None if invalid else np.percentile(draws, [2.5, 97.5])
    if ci is None:
        assert result["bootstrap"]["ci95"] is None
    else:
        np.testing.assert_allclose(ci, result["bootstrap"]["ci95"], atol=1e-12)
    gates = receipt_gates(block_deltas, increments, delta, ci)
    assert gates == result["gates"]
    expected_status = (
        "INVALID_POLICY_EVALUATION"
        if invalid
        else "RAW_POLICY_INCREMENT_ESTABLISHED_NATIVE_REQUIRED"
        if all(gates.values())
        else "STOP_RAW_POLICY_INCREMENT_NOT_ESTABLISHED"
    )
    assert result["status"] == expected_status
    return gates


def audit(state, archive):
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.set_grad_enabled(False)
    result = json.loads((state / "RESULT.json").read_text())
    assert result["scientific_attempt"] == 3 and result["proposal_sha256"] == PROPOSAL_SHA
    stop = json.loads((state / "TRAIN_STOP.json").read_text())
    assert stop == result["common_stop"] and stop["status"] == "COMMON_TRAIN_STOP_FIXED"
    k = stop["common_update"]
    assert 1408 <= k <= 2048 and (k - 1024) % 128 == 0
    assert result["updates_this_attempt"] == 6 * (k - 1024)
    assert result["cumulative_updates"] == 7680 + result["updates_this_attempt"]
    assert result["fresh_lstm_fits_this_attempt"] == result["wallet_accounts"] == 0
    assert (
        result["new_gp_fit_calls"]
        == result["new_scaler_fit_calls"]
        == result["validation_fit_calls"]
        == 0
    )
    assert (
        result["validation_queries_before_stop"] == 0
        and result["final_validation_evaluations"] == 1
    )
    publication = json.loads((state / "PREFIT_PUBLICATION.json").read_text())
    assert publication["remote_sha"] == publication["local_sha"] == result["source_commit"]
    assert publication["remote_verified_before_fit"] is True
    for path, identity in result["source_files"].items():
        assert sha((ROOT / path).read_bytes()) == identity
        assert (
            sha(
                subprocess.check_output(
                    ["git", "show", result["source_commit"] + ":" + path], cwd=ROOT
                )
            )
            == identity
        )
    preserved = verify_preservation()
    assert sha(archive.read_bytes()) == result["source_archive_sha256"]
    train_x, target, rows, source = training_data(archive)
    assert source == result["preflight"]["source"]
    assert (state / "TRAINING_PRESTART.json").read_bytes() == (
        state / "PREFLIGHT.json"
    ).read_bytes()
    scoring, available, returns, vol, rows2, x2, y2, blocks, _ = sharpe.prepare(archive)
    np.testing.assert_array_equal(rows, rows2)
    np.testing.assert_array_equal(train_x, x2)
    np.testing.assert_array_equal(target, y2)
    maximum_metric_residual = 0.0
    maximum_inference_residual = 0.0
    final_models, all_losses, cp_pairs = {}, {}, {}
    checkpoint_count = 0
    for fit in result["fits"]:
        arm, seed = fit["arm"], fit["seed"]
        assert fit["updates"] == k and fit["additional_updates"] == k - 1024
        replay = np.random.default_rng(seed)
        digest, extra = hashlib.sha256(), hashlib.sha256()
        curves = fit["diagnostics"]
        assert [p["update"] for p in curves] == list(range(1024, k + 1, 128))
        losses = []
        inputs = train_x.copy()
        if arm == "trend":
            inputs[:, :, 8:] = 0
        for point in curves:
            step = point["update"]
            if step == 1024:
                cp_path = Path("/workspace/slow-momentum-sharpe-state") / f"{arm}-seed{seed}.pt"
                assert sha(cp_path.read_bytes()) == fit["source_checkpoint_sha256"]
            else:
                cp_path = state / point["checkpoint_file"]
                assert sha(cp_path.read_bytes()) == point["checkpoint_sha256"]
                checkpoint_count += 1
                saved_point = json.loads((state / f"MONITOR_{arm}_{seed}_{step}.json").read_text())
                assert saved_point == point
            cp = torch.load(cp_path, map_location="cpu", weights_only=True)
            assert cp["updates"] == step and cp["seed"] == seed
            previous = 0 if step == 1024 else step - 128
            for update in range(previous, step):
                raw = replay.integers(0, len(rows), size=128).astype("<i8").tobytes()
                digest.update(raw)
                if update >= 1024:
                    extra.update(raw)
            assert cp["numpy_rng"] == replay.bit_generator.state
            assert cp["batch_indices_sha256"] == digest.hexdigest()
            if step > 1024:
                assert cp["continuation_batch_indices_sha256"] == extra.hexdigest()
                assert cp["source_checkpoint_sha256"] == fit["source_checkpoint_sha256"]
                assert point["adam_ages"] == [step]
            assert sorted({int(v["step"]) for v in cp["optimizer"]["state"].values()}) == [step]
            for values in cp["optimizer"]["state"].values():
                assert all(torch.isfinite(v).all() for v in values.values())
                assert (values["exp_avg_sq"] >= 0).all()
            model = sharpe.PositionLSTM()
            model.load_state_dict(cp["model"])
            p = predict(model, inputs)
            z = p * target
            loss = float(-np.sqrt(365) * z.mean() / np.sqrt(z.var() + 1e-9))
            losses.append(loss)
            for actual, expected in (
                (loss, point["full_train_loss"]),
                (independent_sharpe(z), point["full_train_pooled_sharpe"]),
                (float(z.mean()), point["captured_mean"]),
                (float(z.var()), point["captured_variance"]),
                (float(p.var()), point["position_variance"]),
            ):
                maximum_metric_residual = max(
                    maximum_metric_residual, assert_scalar(actual, expected)
                )
            cp_pairs.setdefault((seed, step), []).append(cp)
        assert fit["checkpoint_file"] == curves[-1]["checkpoint_file"]
        assert fit["checkpoint_sha256"] == curves[-1]["checkpoint_sha256"]
        final_models[(arm, seed)] = model
        all_losses[(arm, seed)] = losses
    assert len(all_losses) == 6 and checkpoint_count == 6 * ((k - 1024) // 128)
    for pair in cp_pairs.values():
        assert len(pair) == 2 and torch.equal(pair[0]["torch_rng"], pair[1]["torch_rng"])
        assert pair[0]["numpy_rng"] == pair[1]["numpy_rng"]
    for earlier in range(1408, k, 128):
        size = (earlier - 1024) // 128 + 1
        assert not independent_stop([c[:size] for c in all_losses.values()], earlier)
    local_flat = independent_stop(list(all_losses.values()), k)
    expected_reason = "COMMON_HARD_CAP2048" if k == 2048 else "COMMON_LOCAL_TRAIN_LOSS_FLAT"
    assert stop["reason"] == expected_reason and (k == 2048 or local_flat)
    for key, curve in all_losses.items():
        np.testing.assert_array_equal(curve[-4:], stop["last_four_losses"][f"{key[0]}-{key[1]}"])
    assert sha((state / "POSITIONS.csv").read_bytes()) == result["positions_sha256"]
    with (state / "POSITIONS.csv").open() as file:
        records = list(csv.DictReader(file))
    expected_order = [
        (b["dates"][0], str(available[t]), symbol)
        for b in blocks
        for t in b["times"]
        for symbol in SYMBOLS
    ]
    assert [(r["block"], r["available_us"], r["symbol"]) for r in records] == expected_order
    assert len(records) == len(set(expected_order)) == 2415
    joint_blocks, block_deltas, invalid_blocks = [], [], []
    seed_days = {arm: [[] for _ in SEEDS] for arm in sharpe.ARMS}
    for block, report in zip(blocks, result["blocks"], strict=True):
        selected = [r for r in records if r["block"] == block["dates"][0]]
        shape = block["mask"].shape
        mask = np.array([int(r["eligible"]) for r in selected], dtype=bool).reshape(shape)
        np.testing.assert_array_equal(mask, block["mask"])
        assert report["eligible_decisions"] == int(mask.sum())
        assert report["days"] == len(block["clock"])
        assert all(
            int(r["label_end_us"]) == int(r["available_us"]) + DAY_US < utc_us(block["dates"][1])
            for r in selected
        )
        labels = np.array(
            [
                float(r["scaled_next_return"]) if r["scaled_next_return"] else np.nan
                for r in selected
            ]
        ).reshape(shape)
        csv_vol = np.array(
            [float(r["daily_vol"]) if r["daily_vol"] else np.nan for r in selected]
        ).reshape(shape)
        np.testing.assert_array_equal(csv_vol, vol[block["times"]])
        np.testing.assert_array_equal(labels[mask], block["outcomes"][mask])
        missing_count = int((mask & ~np.isfinite(labels)).sum())
        assert missing_count == report["missing_eligible_outcomes"]
        block_invalid = missing_count > 0
        captured, scores = {}, {}
        for arm in sharpe.ARMS:
            positions = np.array(
                [[float(r[f"{arm}_seed{s}"]) for r in selected] for s in SEEDS]
            ).reshape((3, *shape))
            assert np.isfinite(positions).all() and np.max(np.abs(positions)) <= 1
            assert np.count_nonzero(positions[:, ~mask]) == 0
            ensemble = np.array([float(r[f"{arm}_ensemble"]) for r in selected]).reshape(shape)
            np.testing.assert_array_equal(ensemble, positions.mean(axis=0))
            for index, seed in enumerate(SEEDS):
                x = block["x"].copy()
                if arm == "trend":
                    x[:, :, 8:] = 0
                repeated = predict(final_models[(arm, seed)], x)
                maximum_inference_residual = max(
                    maximum_inference_residual,
                    float(np.abs(repeated - positions[index][mask]).max()),
                )
                z = np.zeros(shape)
                z[mask] = positions[index][mask] * labels[mask]
                daily = z.sum(axis=1) / 5
                seed_days[arm][index].append(daily)
                seed_score = independent_sharpe(daily)
                block_invalid |= seed_score is None
                if report["status"] == "VALID_RAW_POLICY_PROXY":
                    assert_scalar(seed_score, report["arms"][arm]["seeds"][index]["sharpe"])
            z = np.zeros(shape)
            z[mask] = ensemble[mask] * labels[mask]
            captured[arm] = z
            daily = z.sum(axis=1) / 5
            scores[arm] = independent_sharpe(daily)
            block_invalid |= scores[arm] is None
            if report["status"] == "VALID_RAW_POLICY_PROXY":
                expected = report["arms"][arm]["ensemble"]
                for actual, expected_value in (
                    (scores[arm], expected["sharpe"]),
                    (float(daily.mean()), expected["mean_daily_proxy_return"]),
                    (float(daily.std()), expected["daily_proxy_std"]),
                ):
                    maximum_metric_residual = max(
                        maximum_metric_residual, assert_scalar(actual, expected_value)
                    )
        if block_invalid:
            assert report["status"] == "INVALID_POLICY_EVALUATION"
            assert report["ensemble_sharpe_increment"] is None
            invalid_blocks.append(block["dates"])
        else:
            assert report["status"] == "VALID_RAW_POLICY_PROXY"
            delta = scores["trend_cpd"] - scores["trend"]
            block_deltas.append(delta)
            assert_scalar(delta, report["ensemble_sharpe_increment"])
        joint_blocks.append(np.stack([captured[a] for a in sharpe.ARMS], axis=2))
    gates = reconcile_statistics(
        joint_blocks, block_deltas, seed_days, scoring, result, invalid_blocks
    )
    assert maximum_inference_residual == 0 and maximum_metric_residual < 1e-12
    receipt = {
        "status": "PASS",
        "result_status": result["status"],
        "common_update": k,
        "common_stop_reason": stop["reason"],
        "train_local_flat_at_final": bool(local_flat),
        "earlier_common_flat_stop_skipped": False,
        "record_count": len(records),
        "training_checkpoint_inference_sets": len(result["fits"]) + checkpoint_count,
        "validation_repeated_inference_sets": 18,
        "maximum_inference_residual": maximum_inference_residual,
        "maximum_metric_residual": maximum_metric_residual,
        "paired_rng_batches_adam_ages": "PASS",
        "bootstrap": "INDEPENDENT_JOINT_DATE_NONLINEAR_RECOMPUTATION",
        "gates": gates,
        "invalid_input_blocks": invalid_blocks,
        "source_commit": result["source_commit"],
        "result_sha256": sha((state / "RESULT.json").read_bytes()),
        "preservation_before": preserved,
        "preservation_after": verify_preservation(),
        "new_fits": 0,
        "optimizer_updates": 0,
        "wallets": 0,
        "native_economic_audit": "NOT_RUN_NO_NATIVE_ACCOUNT",
    }
    write_json(state / "SAVED_POLICY_AUDIT.json", receipt)
    print(json.dumps(receipt, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument(
        "--archive", type=Path, default=Path("/workspace/slow-momentum-state/source/features.zip")
    )
    args = parser.parse_args()
    audit(args.state, args.archive)


if __name__ == "__main__":
    main()
