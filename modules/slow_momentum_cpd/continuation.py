"""Attempt3: one exact paired continuation, train-only common stop, no rescue."""

import argparse
import hashlib
import json
import subprocess
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from torch import nn

from . import sharpe
from .core import DAY_US, FrozenGP, Scaler, sample_index, trend_features
from .diagnose_training import read_training_close
from .run import ROOT, predict, sequences, sha, utc_us, write_json

PROPOSAL = (
    ROOT / "research/slow-momentum-cpd-training-diagnostic-20261011/CONTINUATION_PROPOSAL.json"
)
PROPOSAL_SHA = "33869fc5cf2d60951a6ed2fcd3b543df4849f8bb5dca4f47f9216247f9a2407b"
EXPERIMENT = ROOT / "research/slow-momentum-cpd-sharpe-continuation-20261011"
ORIGINAL_STATE = Path("/workspace/slow-momentum-sharpe-state")
ARCHIVE = Path("/workspace/slow-momentum-state/source/features.zip")
SEEDS = (2001, 2002, 2003)


def tensor_hash(values):
    return sha(b"".join(v.detach().cpu().numpy().tobytes() for v in values))


def verify_preservation():
    counts = {}
    for name in (
        "slow-momentum-cpd-20261011",
        "slow-momentum-cpd-sharpe-20261011",
        "slow-momentum-cpd-training-diagnostic-20261011",
    ):
        manifest = json.loads((ROOT / "research" / name / "DELIVERY_MANIFEST.json").read_text())
        for path, expected in manifest["files"].items():
            raw = (ROOT / path).read_bytes()
            if sha(raw) != expected["sha256"] or len(raw) != expected["bytes"]:
                raise ValueError("Preserved evidence changed: " + path)
        counts[name] = len(manifest["files"])
    lineage = load_proposal()["predecessor"]["model_checkpoint_lineage_sha256"]
    for name, identity in lineage.items():
        assert sha((ORIGINAL_STATE / name).read_bytes()) == identity
    return {
        "status": "BYTE_UNCHANGED",
        "manifest_file_counts": counts,
        "original_sharpe_checkpoint_files_verified": len(lineage),
        "original_mse": sharpe.verify_predecessor(),
    }


def load_proposal():
    if sha(PROPOSAL.read_bytes()) != PROPOSAL_SHA:
        raise ValueError("Frozen continuation proposal changed")
    return json.loads(PROPOSAL.read_text())


def training_data(archive):
    """Predicate-bound training-only reader; no prepare/validation/refit calls."""
    available, close = read_training_close(archive)
    trend, returns, vol = trend_features(close)
    old = sharpe.PREDECESSOR
    scoring_path = old / "SHARPE_CORRECTION_PROPOSAL.json"
    assert sha(scoring_path.read_bytes()) == sharpe.PROPOSAL_SHA
    scoring = json.loads(scoring_path.read_text())
    frozen_path = old / "results/FROZEN_TRAINING.json"
    assert sha(frozen_path.read_bytes()) == scoring["predecessor"]["frozen_training_sha256"]
    frozen = json.loads(frozen_path.read_text())
    cutoff = utc_us("2023-01-01")
    assert (
        max(frozen["latest_training_label_end_us"], frozen["scaler_latest_available_us"]) < cutoff
    )
    assert frozen["fit"]["latest_fit_available_us"] < cutoff - DAY_US
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
    features = np.concatenate((trend, gp.transform(returns)), axis=2)
    rows = sample_index(trend, returns, vol, available, utc_us("2021-01-01"), cutoff)
    proposal = load_proposal()
    assert len(rows) == proposal["frozen_inputs"]["train_endpoints"] == frozen["training_samples"]
    assert sha(rows.astype("<i8").tobytes()) == proposal["frozen_inputs"]["train_rows_sha256"]
    x = sequences(scaler.transform(features), rows)
    y = sharpe.RATE * returns[rows[:, 0] + 1, rows[:, 1]] / vol[rows[:, 0], rows[:, 1]]
    assert np.isfinite(x).all() and np.isfinite(y).all()
    assert available[rows[:, 0] + 1].max() < cutoff
    return (
        x,
        y,
        rows,
        {
            "train_samples": len(rows),
            "train_rows_sha256": sha(rows.astype("<i8").tobytes()),
            "training_inputs_sha256": sha(x.tobytes()),
            "training_targets_sha256": sha(y.tobytes()),
            "latest_training_label_end_us": int(available[rows[:, 0] + 1].max()),
            "frozen_training_sha256": sha(frozen_path.read_bytes()),
            "archive_sha256": sha(archive.read_bytes()),
            "validation_queries": 0,
            "new_gp_scaler_fits": 0,
        },
    )


def restore(cp, factory=sharpe.PositionLSTM):
    """Construction/loading precedes RNG restoration; retain exact optimizer ages."""
    model = factory()
    model.load_state_dict(cp["model"])
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    optimizer.load_state_dict(cp["optimizer"])
    rng = np.random.default_rng()
    rng.bit_generator.state = cp["numpy_rng"]
    torch.set_rng_state(cp["torch_rng"])
    return {
        "model": model,
        "optimizer": optimizer,
        "rng": rng,
        "torch_rng": torch.get_rng_state().clone(),
        "updates": cp["updates"],
        "diagnostics": [],
    }


def finite_state(unit):
    for p in unit["model"].parameters():
        if not torch.isfinite(p).all() or (p.grad is not None and not torch.isfinite(p.grad).all()):
            raise ValueError("INVALID_NONFINITE_PARAMETERS_OR_GRADIENTS")
    for value in unit["optimizer"].state.values():
        if any(torch.is_tensor(v) and not torch.isfinite(v).all() for v in value.values()):
            raise ValueError("INVALID_NONFINITE_ADAM_STATE")
        if (value["exp_avg_sq"] < 0).any():
            raise ValueError("INVALID_NEGATIVE_ADAM_SECOND_MOMENT")


def verify_restored(cp, unit):
    for name, value in cp["model"].items():
        assert torch.equal(value, unit["model"].state_dict()[name])
    restored = unit["optimizer"].state_dict()
    assert restored["param_groups"] == cp["optimizer"]["param_groups"]
    for key, values in cp["optimizer"]["state"].items():
        for field, value in values.items():
            assert torch.equal(value, restored["state"][key][field])
    assert unit["rng"].bit_generator.state == cp["numpy_rng"]
    assert torch.equal(unit["torch_rng"], cp["torch_rng"])
    assert sorted({int(v["step"]) for v in restored["state"].values()}) == [cp["updates"]]
    finite_state(unit)


def resume_units(n):
    proposal = load_proposal()
    units, receipts = {}, []
    for seed in SEEDS:
        replay = np.random.default_rng(seed)
        batch_hash = hashlib.sha256()
        for _ in range(1024):
            batch_hash.update(replay.integers(0, n, size=128).astype("<i8").tobytes())
        next_rng = np.random.default_rng()
        next_rng.bit_generator.state = replay.bit_generator.state
        next_batch_hash = sha(next_rng.integers(0, n, size=128).astype("<i8").tobytes())
        for arm in sharpe.ARMS:
            name = f"{arm}-seed{seed}.pt"
            path = ORIGINAL_STATE / name
            identity = sha(path.read_bytes())
            assert identity == proposal["predecessor"]["model_checkpoint_lineage_sha256"][name]
            cp = torch.load(path, map_location="cpu", weights_only=True)
            assert cp["seed"] == seed and cp["updates"] == 1024
            assert cp["numpy_rng"] == replay.bit_generator.state
            assert cp["batch_indices_sha256"] == batch_hash.hexdigest()
            group = cp["optimizer"]["param_groups"][0]
            assert group["lr"] == 0.001 and tuple(group["betas"]) == (0.9, 0.999)
            assert group["eps"] == 1e-8 and group["weight_decay"] == 0
            assert not group["amsgrad"] and not group["maximize"]
            unit = restore(cp)
            verify_restored(cp, unit)
            unit.update(
                {
                    "arm": arm,
                    "seed": seed,
                    "source_checkpoint_sha256": identity,
                    "batch_hash": batch_hash.copy(),
                    "continuation_batch_hash": hashlib.sha256(),
                }
            )
            fit = json.loads((ORIGINAL_STATE / f"FIT_{arm}_{seed}.json").read_text())
            assert fit["checkpoint_sha256"] == identity
            unit["predecessor_final_diagnostic"] = fit["diagnostics"][-1]
            units[(arm, seed)] = unit
            receipts.append(
                {
                    "arm": arm,
                    "seed": seed,
                    "source_checkpoint_sha256": identity,
                    "model_parameter_sha256": tensor_hash(cp["model"].values()),
                    "adam_state_tensors_sha256": tensor_hash(
                        v for s in cp["optimizer"]["state"].values() for v in s.values()
                    ),
                    "torch_rng_sha256": sha(cp["torch_rng"].numpy().tobytes()),
                    "numpy_rng": cp["numpy_rng"],
                    "adam_ages": [1024],
                    "source_batch_indices_sha256": cp["batch_indices_sha256"],
                    "next_update1025_batch_sha256": next_batch_hash,
                    "exact_restoration": "PASS",
                }
            )
        a, b = units[("trend", seed)], units[("trend_cpd", seed)]
        assert a["rng"].bit_generator.state == b["rng"].bit_generator.state
        assert torch.equal(a["torch_rng"], b["torch_rng"])
    return units, receipts


def full_diagnostic(unit, x, y):
    point = sharpe.training_diagnostic(unit["model"], x, y, unit["updates"])
    point["full_train_loss"] = float(
        -np.sqrt(365) * point["captured_mean"] / np.sqrt(point["captured_variance"] + 1e-9)
    )
    if not np.isfinite(point["full_train_loss"]):
        raise ValueError("INVALID_NONFINITE_TRAINING_MONITOR")
    return point


def common_stop(curves, k):
    if k >= 2048:
        return "COMMON_HARD_CAP2048"
    if k < 1408:
        return None
    if all(
        len(c) >= 4
        and all(
            abs(c[-i]["full_train_loss"] - c[-i - 1]["full_train_loss"]) <= 0.02 for i in (1, 2, 3)
        )
        for c in curves
    ):
        return "COMMON_LOCAL_TRAIN_LOSS_FLAT"
    return None


def advance(unit, x, y, count=128, batch_size=128):
    torch.set_rng_state(unit["torch_rng"])
    tx, ty = torch.from_numpy(x), torch.tensor(y, dtype=torch.float64)
    gradients, update_norms, relative, coordinate = [], [], [], []
    for _ in range(count):
        selected = unit["rng"].integers(0, len(x), size=batch_size)
        raw = selected.astype("<i8").tobytes()
        unit["batch_hash"].update(raw)
        unit["continuation_batch_hash"].update(raw)
        unit["model"].train()
        unit["optimizer"].zero_grad()
        loss = sharpe.policy_loss(unit["model"](tx[selected]), ty[selected])
        loss.backward()
        gradient = nn.utils.clip_grad_norm_(
            unit["model"].parameters(), 1.0, error_if_nonfinite=True
        )
        before = torch.cat([p.detach().flatten() for p in unit["model"].parameters()]).clone()
        unit["optimizer"].step()
        # Count completed optimizer calls before any post-step failure.
        unit["updates"] += 1
        finite_state(unit)
        after = torch.cat([p.detach().flatten() for p in unit["model"].parameters()])
        movement = (after - before).double()
        gradients.append(float(gradient))
        update_norms.append(float(torch.linalg.vector_norm(movement)))
        relative.append(update_norms[-1] / float(torch.linalg.vector_norm(before.double())))
        coordinate.append(float(movement.abs().max()))
    unit["torch_rng"] = torch.get_rng_state().clone()
    return {
        "preclip_gradient_norm_min_mean_max": [
            min(gradients),
            float(np.mean(gradients)),
            max(gradients),
        ],
        "gradient_clipped_fraction": float(np.mean(np.asarray(gradients) > 1)),
        "actual_update_l2_min_mean_max": [
            min(update_norms),
            float(np.mean(update_norms)),
            max(update_norms),
        ],
        "actual_update_to_weight_l2_min_mean_max": [
            min(relative),
            float(np.mean(relative)),
            max(relative),
        ],
        "actual_max_coordinate_update_min_mean_max": [
            min(coordinate),
            float(np.mean(coordinate)),
            max(coordinate),
        ],
        "last_minibatch_loss": float(loss.detach()),
        "last_preclip_gradient_norm": float(gradient),
    }


def save_checkpoint(unit, state):
    path = state / f"{unit['arm']}-seed{unit['seed']}-step{unit['updates']}.pt"
    if path.exists():
        raise FileExistsError("No checkpoint overwrite")
    cp = {
        "model": unit["model"].state_dict(),
        "optimizer": unit["optimizer"].state_dict(),
        "torch_rng": unit["torch_rng"],
        "numpy_rng": unit["rng"].bit_generator.state,
        "seed": unit["seed"],
        "updates": unit["updates"],
        "batch_indices_sha256": unit["batch_hash"].hexdigest(),
        "continuation_batch_indices_sha256": unit["continuation_batch_hash"].hexdigest(),
        "source_checkpoint_sha256": unit["source_checkpoint_sha256"],
    }
    with path.open("xb") as file:
        torch.save(cp, file)
    return {
        "checkpoint_file": path.name,
        "checkpoint_sha256": sha(path.read_bytes()),
        "batch_indices_sha256": cp["batch_indices_sha256"],
        "continuation_batch_indices_sha256": cp["continuation_batch_indices_sha256"],
        "torch_rng_sha256": sha(cp["torch_rng"].numpy().tobytes()),
        "numpy_rng": cp["numpy_rng"],
        "adam_ages": sorted({int(v["step"]) for v in cp["optimizer"]["state"].values()}),
    }


def final_validation(units, archive, stop_receipt, state=None):
    if stop_receipt is None or stop_receipt.get("status") != "COMMON_TRAIN_STOP_FIXED":
        raise ValueError("Validation forbidden before common training stop")
    k = stop_receipt["common_update"]
    assert all(u["updates"] == k for u in units.values())
    if state is not None:
        assert json.loads((state / "TRAIN_STOP.json").read_text()) == stop_receipt
        write_json(
            state / "VALIDATION_STARTED.json",
            {
                "common_update": k,
                "start_utc": datetime.now(timezone.utc).isoformat(),
                "evaluation_budget": 1,
                "partial_if_interrupted": True,
            },
        )
    data = sharpe.prepare(archive)  # First validation-producing call, after immutable stop.
    scoring, available, returns, vol, rows, x, y, blocks, source = data
    for seed in SEEDS:
        for arm in sharpe.ARMS:
            model = units[(arm, seed)]["model"]
            for block in blocks:
                inputs = block["x"].copy()
                if arm == "trend":
                    inputs[:, :, 8:] = 0
                positions = np.zeros(block["mask"].shape)
                positions[block["mask"]] = predict(model, inputs)
                block["position"][arm].append(positions)
    return sharpe.score_blocks(blocks, scoring, vol), data


def published_source(state):
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    publication = json.loads((state / "PREFIT_PUBLICATION.json").read_text())
    assert publication["remote_sha"] == publication["local_sha"] == commit
    assert publication["remote_verified_before_fit"] is True
    paths = [
        "modules/slow_momentum_cpd/" + p
        for p in (
            "continuation.py",
            "test_continuation.py",
            "audit_continuation.py",
            "sharpe.py",
            "audit_sharpe.py",
            "core.py",
            "run.py",
            "diagnose_training.py",
        )
    ]
    paths += [
        str((EXPERIMENT / p).relative_to(ROOT))
        for p in ("PROTOCOL.json", "prefit/TESTS.xml", "prefit/PREFLIGHT.json")
    ]
    identities = {}
    for path in paths:
        raw = (ROOT / path).read_bytes()
        assert raw == subprocess.check_output(["git", "show", commit + ":" + path], cwd=ROOT)
        identities[path] = sha(raw)
    suites = ET.parse(EXPERIMENT / "prefit/TESTS.xml").findall(".//testsuite")
    assert suites and all(
        not int(s.get("errors", "0")) and not int(s.get("failures", "0")) for s in suites
    )
    return commit, identities


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--archive", type=Path, default=ARCHIVE)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    state = args.state.resolve()
    assert state == Path("/workspace/slow-momentum-sharpe-continuation-state")
    state.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    load_proposal()
    preserved = verify_preservation()
    x, y, rows, source = training_data(args.archive)
    units, restoration = resume_units(len(rows))
    preflight = {
        "status": "PASS",
        "proposal_sha256": PROPOSAL_SHA,
        "source": source,
        "restoration": restoration,
        "preservation": preserved,
        "optimizer_updates_added": 0,
        "validation_queries": 0,
    }
    if args.preflight:
        write_json(state / "PREFLIGHT.json", preflight)
        print(
            json.dumps({"status": "PASS", "train_samples": len(rows), "exact_restored_models": 6})
        )
        return
    assert preflight == json.loads((state / "PREFLIGHT.json").read_text())
    commit, identities = published_source(state)
    write_json(
        state / "ATTEMPT.json",
        {
            "scientific_attempt": 3,
            "start_utc": datetime.now(timezone.utc).isoformat(),
            "source_commit": commit,
            "proposal_sha256": PROPOSAL_SHA,
            "retry_budget": 0,
            "max_additional_updates": 6144,
            "fresh_training_initializations": 0,
            "wallets": 0,
        },
    )
    write_json(state / "TRAINING_PRESTART.json", preflight)
    start = time.monotonic()
    try:
        for unit in units.values():
            inputs = x.copy()
            if unit["arm"] == "trend":
                inputs[:, :, 8:] = 0
            unit["x"] = inputs
            point = full_diagnostic(unit, inputs, y)
            old = unit["predecessor_final_diagnostic"]
            for field in ("captured_mean", "captured_variance", "position_variance"):
                assert point[field] == old[field]
            unit["diagnostics"].append(point)
        stop = None
        for k in range(1152, 2049, 128):
            for unit in units.values():
                statistics = advance(unit, unit["x"], y)
                point = full_diagnostic(unit, unit["x"], y)
                point.update(statistics)
                point.update(save_checkpoint(unit, state))
                unit["diagnostics"].append(point)
                write_json(state / f"MONITOR_{unit['arm']}_{unit['seed']}_{k}.json", point)
                print(
                    f"TRAIN {unit['arm']} seed={unit['seed']} k={k} "
                    f"J={point['full_train_loss']:.6f}",
                    flush=True,
                )
            for seed in SEEDS:
                a, b = units[("trend", seed)], units[("trend_cpd", seed)]
                assert a["updates"] == b["updates"] == k
                assert a["batch_hash"].hexdigest() == b["batch_hash"].hexdigest()
                assert a["rng"].bit_generator.state == b["rng"].bit_generator.state
                assert torch.equal(a["torch_rng"], b["torch_rng"])
            reason = common_stop([u["diagnostics"] for u in units.values()], k)
            if reason:
                stop = {
                    "status": "COMMON_TRAIN_STOP_FIXED",
                    "reason": reason,
                    "common_update": k,
                    "validation_queries_before_stop": 0,
                    "stop_utc": datetime.now(timezone.utc).isoformat(),
                    "last_four_losses": {
                        f"{a}-{s}": [p["full_train_loss"] for p in u["diagnostics"][-4:]]
                        for (a, s), u in units.items()
                    },
                }
                write_json(state / "TRAIN_STOP.json", stop)
                break
        assert stop is not None
        fits = []
        for unit in units.values():
            fit = {
                key: unit[key]
                for key in ("arm", "seed", "updates", "source_checkpoint_sha256", "diagnostics")
            }
            fit.update(
                {
                    "additional_updates": unit["updates"] - 1024,
                    **{
                        key: unit["diagnostics"][-1][key]
                        for key in (
                            "checkpoint_file",
                            "checkpoint_sha256",
                            "batch_indices_sha256",
                            "continuation_batch_indices_sha256",
                            "adam_ages",
                        )
                    },
                }
            )
            write_json(state / f"FIT_{unit['arm']}_{unit['seed']}.json", fit)
            fits.append(fit)
        result, data = final_validation(units, args.archive, stop, state)
        scoring, available, returns, vol, _, _, _, blocks, source_audit = data
        positions_sha = sharpe.save_positions(state, blocks, available, returns, vol, SEEDS)
        result.update(
            {
                "scientific_attempt": 3,
                "evidence": "REAL_SEEN_DEVELOPMENT_CONTINUED_RAW_POLICY_PROBE",
                "original_1024_status": "STOP_RAW_POLICY_INCREMENT_NOT_ESTABLISHED",
                "common_stop": stop,
                "fits": fits,
                "seeds": list(SEEDS),
                "train_samples": len(rows),
                "updates_this_attempt": 6 * (stop["common_update"] - 1024),
                "cumulative_updates": 7680 + 6 * (stop["common_update"] - 1024),
                "cumulative_scientific_attempts": 3,
                "fresh_lstm_fits_this_attempt": 0,
                "cumulative_fresh_lstm_fits": 12,
                "continuation_segments": 6,
                "new_gp_fit_calls": 0,
                "new_scaler_fit_calls": 0,
                "validation_fit_calls": 0,
                "final_validation_evaluations": 1,
                "validation_queries_before_stop": 0,
                "searches": 0,
                "recipe_retries": 0,
                "source_commit": commit,
                "source_files": identities,
                "proposal_sha256": PROPOSAL_SHA,
                "preflight": preflight,
                "source_archive_sha256": sha(args.archive.read_bytes()),
                "source_audit": source_audit,
                "positions_sha256": positions_sha,
                "wall_seconds": time.monotonic() - start,
                "paper_exact_reproduction": "NOT_RUN",
                "native_wallet": "NOT_RUN_NOT_BOUND",
                "wallet_accounts": 0,
                "costs_slippage_funding_risk_terminal_closure": "NOT_MEASURED",
                "financial_net_profit_or_apr": "UNKNOWN",
                "predecessor_after": verify_preservation(),
                "additional_training_authorized_after_this_attempt": False,
            }
        )
        write_json(state / "RESULT.json", result)
        output_bytes = sum(p.stat().st_size for p in state.rglob("*") if p.is_file())
        assert output_bytes <= 10485760
        write_json(state / "OUTPUT_BUDGET.json", {"bytes": output_bytes, "limit": 10485760})
        print(
            json.dumps(
                {
                    key: result[key]
                    for key in (
                        "status",
                        "common_stop",
                        "aggregate",
                        "bootstrap",
                        "gates",
                        "wall_seconds",
                    )
                },
                indent=2,
            )
        )
    except Exception as error:
        failure = {
            "status": "INVALID_STOP_NO_RETRY",
            "error_type": type(error).__name__,
            "error": str(error),
            "per_segment_confirmed_updates": {
                f"{a}-{s}": u["updates"] - 1024 for (a, s), u in units.items()
            },
            "validation_started": (state / "VALIDATION_STARTED.json").exists(),
            "validation_complete": (state / "RESULT.json").exists(),
            "unlogged_tail_on_external_resource_kill": "UNKNOWN",
            "retry_allowed": False,
        }
        write_json(state / "FAILURE.json", failure)
        raise


if __name__ == "__main__":
    main()
