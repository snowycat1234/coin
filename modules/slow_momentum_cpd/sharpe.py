"""Attempt 2: frozen CPD crypto policy adaptation, gross signal probe only."""

import argparse
import csv
import hashlib
import json
import subprocess
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from scipy.stats import spearmanr
from torch import nn

from .core import DAY_US, SYMBOLS, FrozenGP, Scaler, sample_index, trend_features
from .run import ROOT, TrendLSTM, load_close, predict, recover_archive, sequences, sha, utc_us
from .run import write_json as exclusive_json

PREDECESSOR = ROOT / "research/slow-momentum-cpd-20261011"
EXPERIMENT = ROOT / "research/slow-momentum-cpd-sharpe-20261011"
PROPOSAL_SHA = "8895319f41a91ebdb44a87fe67959c5f45c62cd7ad7c325fe87e0875eadc816b"
RATE = 0.15 / np.sqrt(365)
ARMS = ("trend", "trend_cpd")


class InvalidScore(ValueError):
    """Missing outcomes or degenerate scored returns never become cash/zero."""


class PositionLSTM(TrendLSTM):
    def forward(self, x):
        return torch.tanh(super().forward(x))


def policy_loss(position, target):
    # Mathematically the frozen moment loss, evaluated in centered float64.
    # Avoid cancellation in E[z²]-E[z]²; retain exactly the frozen epsilon.
    z = position.to(torch.float64) * target.to(torch.float64)
    if not torch.isfinite(z).all():
        raise ValueError("Nonfinite captured training return")
    mean = z.mean()
    variance = ((z - mean) ** 2).mean()
    loss = -np.sqrt(365) * mean / torch.sqrt(variance + 1e-9)
    if not torch.isfinite(loss):
        raise ValueError("Nonfinite loss: stop without retry")
    return loss


def scored_sharpe(values):
    values = np.asarray(values, dtype=float)
    if len(values) < 2 or not np.isfinite(values).all():
        raise InvalidScore("Nonfinite/insufficient scored returns")
    mean = values.mean()
    variance = np.mean((values - mean) ** 2)
    if variance <= 0 or not np.isfinite(variance):
        raise InvalidScore("Zero/nonfinite scored variance; no epsilon or NaN substitution")
    score = np.sqrt(365) * mean / np.sqrt(variance)
    if not np.isfinite(score):
        raise InvalidScore("Nonfinite scored Sharpe")
    return float(score)


def decision_mask(features, vol, sequence=63):
    """Only <=t input observations and current causal vol; no outcome argument."""
    features = np.asarray(features)
    if features.ndim != 3 or vol.shape != features.shape[:2] or sequence < 1:
        raise ValueError("Invalid decision input axes")
    finite = np.isfinite(features).all(axis=2)
    prefix = np.vstack((np.zeros((1, finite.shape[1]), dtype=int), np.cumsum(~finite, axis=0)))
    out = np.zeros(finite.shape, dtype=bool)
    if len(finite) >= sequence:
        out[sequence - 1 :] = (prefix[sequence:] - prefix[:-sequence]) == 0
    return out & np.isfinite(vol) & (vol > 0)


def calendar_axis(available, start, end):
    # Strict maturity uses the known calendar, not future outcome availability.
    times = np.flatnonzero((available >= start) & (available + DAY_US < end))
    if not len(times) or np.any(np.diff(available[times]) != DAY_US):
        raise InvalidScore("Missing/noncontiguous calendar inside declared split")
    return times


def scaled_outcomes(times, mask, returns, vol):
    """Keep every decision. Missing eligible future outcome remains INVALID."""
    if mask.shape != (len(times), len(SYMBOLS)):
        raise ValueError("Wrong CORE5 mask axis")
    future = np.full(mask.shape, np.nan)
    inside = times + 1 < len(returns)
    future[inside] = returns[times[inside] + 1]
    missing = np.argwhere(mask & ~np.isfinite(future))
    out = np.zeros(mask.shape)  # Cash only for decision-time ineligible assets.
    with np.errstate(divide="ignore", invalid="ignore"):
        out[mask] = (RATE * future / vol[times])[mask]
    return out, missing


def capture(position, mask, outcomes):
    if position.shape != mask.shape or outcomes.shape != mask.shape:
        raise ValueError("Wrong policy/mask/outcome axes")
    if not np.isfinite(position).all() or np.any(np.abs(position) > 1):
        raise InvalidScore("Nonfinite/out-of-bounds policy")
    if not np.isfinite(outcomes[mask]).all():
        raise InvalidScore("Eligible decision lacks realized return, even at zero position")
    return np.where(mask, position * outcomes, 0.0)


def joint_bootstrap(blocks, replicates=1000, width=14, seed=9901):
    """Joint arm/asset date draws; nonlinear Sharpe recomputed in every draw."""
    for dates, joint in blocks:
        if (
            joint.shape != (len(dates), 5, 2)
            or len(dates) < width
            or np.any(np.diff(dates) != DAY_US)
            or not np.isfinite(joint).all()
        ):
            raise InvalidScore("Bootstrap shape/calendar/outcome invalid")
    rng = np.random.default_rng(seed)
    differences = []
    invalid = []
    for replicate in range(replicates):
        pieces = []
        for dates, joint in blocks:
            starts = rng.integers(0, len(dates) - width + 1, size=int(np.ceil(len(dates) / width)))
            indices = np.concatenate([np.arange(s, s + width) for s in starts])[: len(dates)]
            pieces.append(joint[indices].sum(axis=1) / 5)
        draws = np.concatenate(pieces)
        try:
            differences.append(scored_sharpe(draws[:, 1]) - scored_sharpe(draws[:, 0]))
        except InvalidScore:
            invalid.append(replicate)
    return {
        "status": "INVALID_DEGENERATE_BOOTSTRAP" if invalid else "VALID",
        "ci95": None if invalid else np.quantile(differences, [0.025, 0.975]).tolist(),
        "replicates": replicates,
        "valid_replicates": len(differences),
        "invalid_replicates": len(invalid),
        "invalid_indices": invalid,
        "block_days": width,
        "seed": seed,
        "uncertainty_scope": "Conditional seen-development resampling; no independent OOS claim",
    }


def verify_predecessor():
    manifest = json.loads((PREDECESSOR / "DELIVERY_MANIFEST.json").read_text())
    for path, item in manifest["files"].items():
        raw = (ROOT / path).read_bytes()
        if sha(raw) != item["sha256"] or len(raw) != item["bytes"]:
            raise ValueError("Original frozen delivery changed: " + path)
    result = json.loads((PREDECESSOR / "results/RESULT.json").read_text())
    for path, identity in result["source_files"].items():
        if sha((ROOT / path).read_bytes()) != identity:
            raise ValueError("Original fit source changed: " + path)
    old_checkpoints_verified = 0
    unavailable = []
    for fit in result["fits"]:
        name = fit["arm"] + "-seed" + str(fit["seed"])
        checkpoint = Path("/workspace/slow-momentum-state") / (name + ".pt")
        if checkpoint.exists():
            if sha(checkpoint.read_bytes()) != fit["checkpoint_sha256"]:
                raise ValueError("Original external checkpoint changed: " + name)
            old_checkpoints_verified += 1
        else:
            unavailable.append(name)
    return {
        "manifest_files": len(manifest["files"]),
        "fit_source_files": len(result["source_files"]),
        "status": "BYTE_UNCHANGED",
        "old_checkpoint_files_verified": old_checkpoints_verified,
        "old_checkpoint_files_unavailable": unavailable,
        "old_fit_checkpoint_shas": {
            f["arm"] + "-seed" + str(f["seed"]): f["checkpoint_sha256"] for f in result["fits"]
        },
    }


def prepare(archive):
    frozen_source = PREDECESSOR / "results/FROZEN_TRAINING.json"
    proposal_path = PREDECESSOR / "SHARPE_CORRECTION_PROPOSAL.json"
    if sha(proposal_path.read_bytes()) != PROPOSAL_SHA:
        raise ValueError("Published proposal changed")
    proposal = json.loads(proposal_path.read_text())
    if sha(frozen_source.read_bytes()) != proposal["predecessor"]["frozen_training_sha256"]:
        raise ValueError("Frozen training artifact changed")
    old_protocol = json.loads((PREDECESSOR / "PROTOCOL.json").read_text())
    if (
        sha((PREDECESSOR / "PROTOCOL.json").read_bytes())
        != proposal["predecessor"]["original_protocol_sha256"]
    ):
        raise ValueError("Original protocol changed")
    recover_archive(ROOT, archive, old_protocol)
    available, close, source = load_close(archive, old_protocol)
    trend, returns, vol = trend_features(close)
    frozen = json.loads(frozen_source.read_text())
    cutoff = utc_us("2023-01-01")
    if max(frozen["latest_training_label_end_us"], frozen["scaler_latest_available_us"]) >= cutoff:
        raise ValueError("Future-fitted original artifact")
    if frozen["fit"]["latest_fit_available_us"] >= cutoff - DAY_US:
        raise ValueError("Future-fitted GP")
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
    inputs = scaler.transform(features)
    train_rows = sample_index(
        trend,
        returns,
        vol,
        available,
        *map(utc_us, proposal["frozen_inputs"]["training_available_time"]),
    )
    if len(train_rows) != frozen["training_samples"]:
        raise ValueError("Original train sample axis changed")
    train_x = sequences(inputs, train_rows)
    train_y = (
        RATE
        * returns[train_rows[:, 0] + 1, train_rows[:, 1]]
        / vol[train_rows[:, 0], train_rows[:, 1]]
    )
    if not np.isfinite(train_x).all() or not np.isfinite(train_y).all():
        raise ValueError("Nonfinite training inputs/outcomes")
    masks = decision_mask(features, vol)
    blocks = []
    for dates in proposal["frozen_inputs"]["validation_available_time"]:
        times = calendar_axis(available, *map(utc_us, dates))
        mask = masks[times]
        rows = np.argwhere(mask)
        rows[:, 0] = times[rows[:, 0]]
        outcomes, missing = scaled_outcomes(times, mask, returns, vol)
        blocks.append(
            {
                "dates": dates,
                "times": times,
                "clock": available[times],
                "mask": mask,
                "rows": rows,
                "x": sequences(inputs, rows),
                "outcomes": outcomes,
                "missing": missing,
                "position": {arm: [] for arm in ARMS},
            }
        )
    return proposal, available, returns, vol, train_rows, train_x, train_y, blocks, source


def training_diagnostic(model, inputs, target, update, loss=None, gradient=None):
    position = predict(model, inputs)
    z = position * target
    variance = float(np.mean((z - z.mean()) ** 2))
    try:
        score = scored_sharpe(z)
    except InvalidScore:
        score = None
    return {
        "update": update,
        "full_train_pooled_sharpe": score,
        "captured_mean": float(z.mean()),
        "captured_variance": variance,
        "epsilon_denominator_fraction": 1e-9 / (variance + 1e-9),
        "position_variance": float(position.var()),
        "position_saturated_fraction": float((np.abs(position) > 0.95).mean()),
        "last_minibatch_loss": loss,
        "last_preclip_gradient_norm": gradient,
    }


def fit_pair(inputs, target, proposal, state, seed):
    pair = {}
    initial_shas = []
    batch_shas = []
    for arm in ARMS:
        checkpoint = state / f"{arm}-seed{seed}.pt"
        if checkpoint.exists():
            raise FileExistsError("No checkpoint overwrite or hidden scientific retry")
        torch.manual_seed(seed)
        rng = np.random.default_rng(seed)
        model = PositionLSTM()
        initial = sha(b"".join(v.detach().numpy().tobytes() for v in model.state_dict().values()))
        initial_shas.append(initial)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        x = inputs.copy()
        if arm == "trend":
            x[:, :, 8:] = 0
        tx = torch.from_numpy(x)
        ty = torch.tensor(target, dtype=torch.float64)
        curve = [training_diagnostic(model, x, target, 0)]
        batch_hash = hashlib.sha256()
        started = time.monotonic()
        for update in range(1024):
            selected = rng.integers(0, len(x), size=128)
            batch_hash.update(selected.astype("<i8").tobytes())
            model.train()
            optimizer.zero_grad()
            loss = policy_loss(model(tx[selected]), ty[selected])
            loss.backward()
            gradient = nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
            optimizer.step()
            if any(not torch.isfinite(p).all() for p in model.parameters()):
                raise ValueError("Nonfinite parameters: stop without retry")
            if (update + 1) % 128 == 0:
                curve.append(
                    training_diagnostic(
                        model, x, target, update + 1, float(loss.detach()), float(gradient)
                    )
                )
                print(
                    f"FIT {arm} seed={seed} updates={update + 1}/1024 "
                    f"train_SR={curve[-1]['full_train_pooled_sharpe']}",
                    flush=True,
                )
        batch_shas.append(batch_hash.hexdigest())
        torch.save(
            {
                "model": model.state_dict(),
                "optimizer": optimizer.state_dict(),
                "torch_rng": torch.get_rng_state(),
                "numpy_rng": rng.bit_generator.state,
                "seed": seed,
                "updates": 1024,
                "batch_indices_sha256": batch_shas[-1],
            },
            checkpoint,
        )
        scores = {item["update"]: item["full_train_pooled_sharpe"] for item in curve}
        drift = (
            None if scores[768] is None or scores[1024] is None else abs(scores[1024] - scores[768])
        )
        fit = {
            "arm": arm,
            "seed": seed,
            "updates": 1024,
            "parameters": sum(p.numel() for p in model.parameters()),
            "initial_sha256": initial,
            "checkpoint_sha256": sha(checkpoint.read_bytes()),
            "batch_indices_sha256": batch_shas[-1],
            "adam_ages": sorted({int(v["step"]) for v in optimizer.state.values()}),
            "seconds": time.monotonic() - started,
            "diagnostics": curve,
            "tail_sharpe_absolute_drift": drift,
            "tail_drift_exceeds_002": None if drift is None else drift > 0.02,
            "convergence": "NOT_ESTABLISHED_BY_FIXED_BUDGET",
        }
        exclusive_json(state / f"FIT_{arm}_{seed}.json", fit)
        pair[arm] = (model, fit)
    if initial_shas[0] != initial_shas[1] or batch_shas[0] != batch_shas[1]:
        raise AssertionError("Paired initialization/minibatches differ")
    return pair


def proxy_stats(captured):
    daily = captured.sum(axis=1) / 5
    return {
        "days": len(daily),
        "sharpe": scored_sharpe(daily),
        "mean_daily_proxy_return": float(daily.mean()),
        "daily_proxy_std": float(daily.std()),
        "annual_proxy_vol": float(daily.std() * np.sqrt(365)),
        "downside_daily_rms": float(np.sqrt(np.mean(np.minimum(daily, 0) ** 2))),
    }


def policy_diagnostics(block, positions, vol):
    eligible = block["mask"]
    target = block["outcomes"][eligible] / RATE
    position = positions[eligible]
    finite = np.isfinite(target)
    ic = []
    for p, y, mask in zip(positions, block["outcomes"] / RATE, eligible, strict=True):
        if (
            mask.sum() >= 3
            and np.isfinite(y[mask]).all()
            and p[mask].std() > 0
            and y[mask].std() > 0
        ):
            ic.append(float(spearmanr(p[mask], y[mask]).statistic))
    risk_weight = np.zeros_like(positions)
    risk_weight[eligible] = (RATE * positions / vol[block["times"]] / 5)[eligible]
    return {
        "position_vs_r_over_vol_mse_not_forecast_accuracy": None
        if not finite.all()
        else float(np.mean((position - target) ** 2)),
        "mean_daily_rank_ic": float(np.mean(ic)) if ic else None,
        "rank_days": len(ic),
        "position_saturated_fraction": float((np.abs(position) > 0.95).mean()),
        "maximum_uncapped_signal_gross": float(np.abs(risk_weight).sum(axis=1).max()),
        "mean_uncapped_signal_turnover_per_day": float(
            np.abs(np.diff(risk_weight, axis=0)).sum(axis=1).mean()
        ),
        "risk_weights": (
            "Raw volatility-scaled signals, not cap-constrained wallet positions; "
            "no free-exit or fill claim"
        ),
    }


def score_blocks(blocks, proposal, vol):
    reports = []
    captured_blocks = []
    seed_blocks = [([], []) for _ in range(3)]
    any_invalid = False
    for block in blocks:
        report = {
            "dates": block["dates"],
            "days": len(block["times"]),
            "eligible_decisions": int(block["mask"].sum()),
            "cash_decisions": int((~block["mask"]).sum()),
            "missing_eligible_outcomes": len(block["missing"]),
            "arms": {},
        }
        try:
            captured = {}
            for arm_index, arm in enumerate(ARMS):
                positions = np.asarray(block["position"][arm])
                ensemble = positions.mean(axis=0)
                c = capture(ensemble, block["mask"], block["outcomes"])
                captured[arm] = c
                seeds = []
                for seed_index, p in enumerate(positions):
                    per_seed = capture(p, block["mask"], block["outcomes"])
                    seeds.append(proxy_stats(per_seed))
                    seed_blocks[seed_index][arm_index].append(per_seed.sum(axis=1) / 5)
                report["arms"][arm] = {
                    "ensemble": proxy_stats(c),
                    "seeds": seeds,
                    "diagnostics": policy_diagnostics(block, ensemble, vol),
                }
            report["ensemble_sharpe_increment"] = (
                report["arms"]["trend_cpd"]["ensemble"]["sharpe"]
                - report["arms"]["trend"]["ensemble"]["sharpe"]
            )
            captured_blocks.append((block["clock"], np.stack([captured[a] for a in ARMS], axis=2)))
            report["status"] = "VALID_RAW_POLICY_PROXY"
        except InvalidScore as error:
            report["status"] = "INVALID_POLICY_EVALUATION"
            report["reason"] = str(error)
            report["ensemble_sharpe_increment"] = None
            any_invalid = True
        reports.append(report)
    if any_invalid:
        return {
            "status": "INVALID_POLICY_EVALUATION",
            "blocks": reports,
            "bootstrap": {"status": "NOT_RUN_INVALID_INPUT", "replicates": 0},
            "gates": None,
            "aggregate": None,
        }
    joined = np.concatenate([item[1] for item in captured_blocks])
    aggregate = {arm: proxy_stats(joined[:, :, i]) for i, arm in enumerate(ARMS)}
    aggregate["ensemble_sharpe_increment"] = (
        aggregate["trend_cpd"]["sharpe"] - aggregate["trend"]["sharpe"]
    )
    seed_increments = [
        scored_sharpe(np.concatenate(cpd)) - scored_sharpe(np.concatenate(trend))
        for trend, cpd in seed_blocks
    ]
    aggregate["seed_sharpe_increments"] = seed_increments
    bs = proposal["scoring"]["bootstrap"]
    bootstrap = joint_bootstrap(captured_blocks, bs["replicates"], bs["block_days"], bs["seed"])
    gates = {
        "positive_in_at_least_two_blocks": sum(r["ensemble_sharpe_increment"] > 0 for r in reports)
        >= 2,
        "positive_in_at_least_two_seeds": sum(x > 0 for x in seed_increments) >= 2,
        "aggregate_ensemble_increment_positive": aggregate["ensemble_sharpe_increment"] > 0,
        "bootstrap_lower_positive": bootstrap["status"] == "VALID" and bootstrap["ci95"][0] > 0,
    }
    status = (
        "INVALID_POLICY_EVALUATION"
        if bootstrap["status"] != "VALID"
        else "RAW_POLICY_INCREMENT_ESTABLISHED_NATIVE_REQUIRED"
        if all(gates.values())
        else "STOP_RAW_POLICY_INCREMENT_NOT_ESTABLISHED"
    )
    return {
        "status": status,
        "blocks": reports,
        "aggregate": aggregate,
        "bootstrap": bootstrap,
        "gates": gates,
    }


def save_positions(state, blocks, available, returns, vol, seeds):
    path = state / "POSITIONS.csv"
    columns = (
        [
            "block",
            "available_us",
            "label_end_us",
            "symbol",
            "eligible",
            "scaled_next_return",
            "daily_vol",
        ]
        + [arm + "_seed" + str(seed) for arm in ARMS for seed in seeds]
        + [arm + "_ensemble" for arm in ARMS]
    )
    with path.open("x", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for block in blocks:
            positions = {arm: np.asarray(block["position"][arm]) for arm in ARMS}
            for date_index, t in enumerate(block["times"]):
                for asset, symbol in enumerate(SYMBOLS):
                    observed = (
                        t + 1 < len(returns)
                        and np.isfinite(returns[t + 1, asset])
                        and np.isfinite(vol[t, asset])
                        and vol[t, asset] > 0
                    )
                    record = {
                        "block": block["dates"][0],
                        "available_us": int(available[t]),
                        "label_end_us": int(available[t] + DAY_US),
                        "symbol": symbol,
                        "eligible": int(block["mask"][date_index, asset]),
                        "scaled_next_return": float(RATE * returns[t + 1, asset] / vol[t, asset])
                        if observed
                        else "",
                        "daily_vol": float(vol[t, asset]) if np.isfinite(vol[t, asset]) else "",
                    }
                    for arm in ARMS:
                        for index, seed in enumerate(seeds):
                            record[arm + "_seed" + str(seed)] = float(
                                positions[arm][index, date_index, asset]
                            )
                        record[arm + "_ensemble"] = float(
                            positions[arm][:, date_index, asset].mean()
                        )
                    writer.writerow(record)
    return sha(path.read_bytes())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    state = args.state.resolve()
    if not state.is_relative_to(Path("/workspace")) or state.is_relative_to(
        Path("/workspace/slow-momentum-state")
    ):
        raise ValueError("Separate writable workspace state required")
    state.mkdir(parents=True, exist_ok=True)
    before = verify_predecessor()
    archive = args.archive or state / "source/features.zip"
    data = prepare(archive)
    proposal, available, returns, vol, rows, inputs, target, blocks, source = data
    preflight = {
        "train_samples": len(rows),
        "latest_training_label_end_us": int(available[rows[:, 0] + 1].max()),
        "real_fits": 0,
        "new_gp_scaler_fits": 0,
        "proposal_sha256": PROPOSAL_SHA,
        "predecessor": before,
        "blocks": [
            {
                "dates": b["dates"],
                "days": len(b["times"]),
                "eligible": int(b["mask"].sum()),
                "missing_eligible_outcomes": b["missing"].tolist(),
                "latest_label_end_us": int(b["clock"][-1] + DAY_US),
            }
            for b in blocks
        ],
    }
    if args.preflight:
        exclusive_json(state / "PREFLIGHT.json", preflight)
        print(json.dumps(preflight["blocks"], indent=2), flush=True)
        return
    if (state / "ATTEMPT.json").exists():
        raise FileExistsError("Attempt2 already started; no silent rerun")
    if not (EXPERIMENT / "prefit/TESTS.xml").exists():
        raise ValueError("Publish reviewed prefit tests before fitting")
    suites = ET.parse(EXPERIMENT / "prefit/TESTS.xml").findall(".//testsuite")
    if not suites or any(int(s.get("failures", "0")) or int(s.get("errors", "0")) for s in suites):
        raise ValueError("Prefit test failure/errors: stop before scientific fit")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    start = time.monotonic()
    source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    publication = json.loads((state / "PREFIT_PUBLICATION.json").read_text())
    if (
        publication["remote_sha"] != source_commit
        or publication["local_sha"] != source_commit
        or not publication["remote_verified_before_fit"]
    ):
        raise ValueError("Publish exact runner/source and verify remote before fitting")
    for path in (
        "modules/slow_momentum_cpd/sharpe.py",
        "modules/slow_momentum_cpd/test_sharpe.py",
        "modules/slow_momentum_cpd/audit_sharpe.py",
        "research/slow-momentum-cpd-sharpe-20261011/PROTOCOL.json",
        "research/slow-momentum-cpd-sharpe-20261011/prefit/TESTS.xml",
    ):
        published = subprocess.check_output(["git", "show", source_commit + ":" + path], cwd=ROOT)
        if (ROOT / path).read_bytes() != published:
            raise ValueError("Dirty or unpublished fit source: " + path)
    exclusive_json(
        state / "ATTEMPT.json",
        {
            "scientific_attempt": 2,
            "start_utc": datetime.now(timezone.utc).isoformat(),
            "source_commit": source_commit,
            "proposal_sha256": PROPOSAL_SHA,
            "updates_per_fit": 1024,
            "fits_budget": 6,
            "retries": 0,
            "wallets": 0,
        },
    )
    fits = []
    for seed in proposal["training"]["seeds"]:
        pair = fit_pair(inputs, target, proposal, state, seed)
        for arm, (model, receipt) in pair.items():
            fits.append(receipt)
            for block in blocks:
                x = block["x"].copy()
                if arm == "trend":
                    x[:, :, 8:] = 0
                position = np.zeros(block["mask"].shape)
                position[block["mask"]] = predict(model, x)
                block["position"][arm].append(position)
    result = score_blocks(blocks, proposal, vol)
    result.update(
        {
            "evidence": "REAL_SEEN_DEVELOPMENT_RAW_CAPTURED_RETURN_POLICY_PROBE",
            "scientific_attempt": 2,
            "lstm_fits_this_attempt": 6,
            "updates_this_attempt": 6144,
            "cumulative_scientific_attempts": 2,
            "cumulative_lstm_fits": 12,
            "cumulative_updates": 7680,
            "new_gp_fit_calls": 0,
            "new_scaler_fit_calls": 0,
            "validation_fit_calls": 0,
            "seeds": proposal["training"]["seeds"],
            "searches": 0,
            "recipe_retries": 0,
            "train_samples": len(rows),
            "fits": fits,
            "preflight": preflight,
            "proposal_sha256": PROPOSAL_SHA,
            "source_commit": source_commit,
            "source_archive_sha256": sha(archive.read_bytes()),
            "source_audit": source,
            "positions_sha256": save_positions(
                state, blocks, available, returns, vol, proposal["training"]["seeds"]
            ),
            "source_files": {
                p: sha((ROOT / p).read_bytes())
                for p in (
                    "modules/slow_momentum_cpd/sharpe.py",
                    "modules/slow_momentum_cpd/test_sharpe.py",
                    "modules/slow_momentum_cpd/audit_sharpe.py",
                )
            },
            "predecessor_after": verify_predecessor(),
            "wall_seconds": time.monotonic() - start,
            "paper_exact_reproduction": "NOT_RUN",
            "profitable_fast_reversion": "NOT_ESTABLISHED",
            "native_wallet": "NOT_RUN_NOT_BOUND",
            "wallet_accounts": 0,
            "costs_slippage_funding_risk_terminal_closure": "NOT_MEASURED",
            "financial_net_profit_or_apr": "UNKNOWN",
            "economic_follow_on": (
                "Require source-bound native trade/mark/funding, actual profile/units, "
                "executable decision timing and masks, cap/risk handling and charged "
                "terminal closure; raw Sharpe is insufficient"
            ),
        }
    )
    exclusive_json(state / "RESULT.json", result)
    output_bytes = sum(p.stat().st_size for p in state.rglob("*") if p.is_file())
    if output_bytes > proposal["resource_budget"]["extra_output_disk_budget_bytes"]:
        raise ValueError("Independent state exceeds frozen 10MiB budget")
    exclusive_json(state / "OUTPUT_BUDGET.json", {"bytes": output_bytes, "limit": 10485760})
    print(
        json.dumps(
            {
                "status": result["status"],
                "aggregate": result["aggregate"],
                "gates": result["gates"],
                "wall_seconds": result["wall_seconds"],
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
