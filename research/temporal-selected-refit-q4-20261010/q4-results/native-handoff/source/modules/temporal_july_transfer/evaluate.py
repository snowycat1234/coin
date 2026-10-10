"""Frozen inference and exactly four full charged daily wallets; no training."""

import argparse
import csv
import json
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import torch

from modules.temporal_expert_input.gradient import predict_episode
from modules.temporal_prequential_transfer.model import initialize, parameter_identity
from modules.temporal_risk_proxy_v2.proxy import BoundaryPlan, charged_boundary_path
from modules.temporal_short_expansion.adapter import compress, expand
from modules.temporal_short_expansion.checkpoint import (
    _validate_model_state,
    _validate_saved_optimizer,
    _validate_rng,
)
from modules.temporal_short_expansion.model import E6
from modules.temporal_two_expert.checkpoint import model_identity
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import CORE5, array_digest, digest

from .data import EXECUTION_DELAY_US, FROZEN, PROTOCOL_SHA, REPO, load, protocol


def frozen_model(scaler):
    specification = protocol()["policies"]["APRIL_PREFIX_GRU512"]
    path = FROZEN / "MODEL_ADAM_RNG.pt"
    if sha(path) != specification["checkpoint_SHA256"]:
        raise ValueError("Exact frozen checkpoint required before deserialization")
    model, optimizer = initialize(scaler)
    snapshot = torch.load(path, map_location="cpu", weights_only=True)
    binding = snapshot["binding"]
    config = binding["specification"]
    if (
        snapshot["step"] != 512
        or config["model_contract"] != model.contract
        or digest(config) != binding["run_id"]
        or config["torch_version"] != str(torch.__version__)
        or config["numpy_version"] != str(np.__version__)
        or not config["deterministic_algorithms"]
        or not torch.are_deterministic_algorithms_enabled()
        or torch.get_num_threads() != 1
        or not config["cpu_only"]
        or snapshot["model_identity"] != specification["model_identity"]
    ):
        raise ValueError("Unchanged source/runtime/model/exact512 checkpoint binding required")
    births = {name: 0 for name, _ in model.named_parameters()}
    _validate_model_state(model, snapshot["model"], specification["model_identity"])
    _validate_saved_optimizer(model, optimizer, snapshot["optimizer"], 512, births)
    _validate_rng(snapshot["rng"])
    model.load_state_dict(snapshot["model"], strict=True)
    if model_identity(model) != specification["model_identity"] or model.parameter_count != 13699:
        raise ValueError("Exact model identity/count required")
    np.testing.assert_array_equal(model.mean.numpy(), scaler.mean)
    np.testing.assert_array_equal(model.base.scale.numpy(), scaler.scale)
    np.testing.assert_array_equal(model.base.normalization_count.numpy(), scaler.count)
    model.eval()
    # Validate saved Adam, but no optimizer state is needed for frozen inference.
    return model


def cost(delta, price):
    fees = float((0.00055 * price * (np.abs(delta) + 0.0008 * delta)).sum())
    spread = float((0.0004 * price * np.abs(delta)).sum())
    return fees, spread, spread


def reconcile(request, episode, targets, mapped, report):
    """Independent algebra on the frozen path; no second wallet or optimizer."""
    nav = report["nav"].detach().numpy()
    quantity = report["quantity"].detach().numpy()
    held = report["boundary_held_quantity"].detach().numpy()
    prices, coeff = episode.prices, episode.funding_coeff
    budget = np.stack([r["budget"] for r in mapped])
    released = np.stack([r["released_prior"] for r in mapped])
    distance = np.abs(budget - released).sum(1)
    masks = np.stack([c.eligible for c in episode.internal.contexts])
    if (
        np.any(distance > 0.1 + 1e-12)
        or np.any(budget[~masks])
        or np.any(request[:, 2:4])
        or np.any(targets[-1])
        or np.any(quantity[-1])
        or np.any(held[-1])
    ):
        raise ValueError("Original masks, post-release ramp and paid forced-flat contract failed")
    np.testing.assert_allclose(budget.sum(1), 1, rtol=0, atol=1e-12)
    np.testing.assert_allclose(request.sum(1), 1, rtol=0, atol=1e-12)
    if min(budget.min(), request.min()) < 0:
        raise ValueError("Simplex budget required")
    np.testing.assert_allclose(
        quantity, 0.99 * nav[:-1, None] * targets / prices[:-1], rtol=1e-13, atol=1e-12
    )
    rows, carry = [], np.zeros(5)
    totals = np.zeros(3)
    funding_total, price_total, turnover_total, reduction_total, residual = 0.0, 0.0, 0.0, 0.0, 0.0
    for t in range(len(targets)):
        opening = cost(quantity[t] - carry, prices[t])
        reduction = cost(held[t] - quantity[t], prices[t + 1])
        payment, reduction_payment = sum(opening), sum(reduction)
        funding = -float(quantity[t] @ coeff[t])
        price_pnl = float(quantity[t] @ (prices[t + 1] - prices[t]))
        expected = nav[t] - payment + price_pnl + funding - reduction_payment
        residual = max(residual, abs(expected - nav[t + 1]))
        opening_nav = nav[t] - payment
        before_reduction_nav = nav[t + 1] + reduction_payment
        opening_abs = np.abs(quantity[t]) * prices[t]
        before_abs = np.abs(quantity[t]) * prices[t + 1]
        boundary_abs = np.abs(held[t]) * prices[t + 1]
        if (
            opening_abs.sum() > 0.6 * opening_nav + 1e-8
            or np.any(opening_abs > 0.3 * opening_nav + 1e-8)
            or boundary_abs.sum() > 0.6 * nav[t + 1] + 1e-8
            or np.any(boundary_abs > 0.3 * nav[t + 1] + 1e-8)
        ):
            raise ValueError("Original opening/post-reduction position caps failed")
        covariance = np.cov(episode.contexts[t].past_returns30, rowvar=False, ddof=1) * 365
        annual_risk = math_sqrt(float(targets[t] @ covariance @ targets[t]))
        if (
            annual_risk > 0.1 + 1e-12
            or mapped[t]["allocated_leg_gross"] > 0.6 + 1e-12
            or mapped[t]["allocated_underlier_gross"].max() > 0.3 + 1e-12
        ):
            raise ValueError("Original allocation/covariance caps failed")
        turnover = float(
            (np.abs(quantity[t] - carry) * prices[t]).sum()
            + (np.abs(held[t] - quantity[t]) * prices[t + 1]).sum()
        )
        totals += np.asarray(opening) + reduction
        funding_total += funding
        price_total += price_pnl
        turnover_total += turnover
        reduction_total += reduction_payment
        row = dict(
            decision_us=int(episode.windows.decision_us[t]),
            execution_us=int(episode.windows.decision_us[t] + EXECUTION_DELAY_US),
            start_nav=float(nav[t]),
            end_nav=float(nav[t + 1]),
            price_PnL=price_pnl,
            funding_PnL=funding,
            fees=opening[0] + reduction[0],
            spread=opening[1] + reduction[1],
            slippage=opening[2] + reduction[2],
            charged_reduction_cost=reduction_payment,
            turnover_USDT=turnover,
            opening_actual_gross=float(opening_abs.sum() / opening_nav),
            opening_actual_net=float(quantity[t] @ prices[t] / opening_nav),
            opening_maximum_asset_gross=float(opening_abs.max() / opening_nav),
            before_reduction_actual_gross=float(before_abs.sum() / before_reduction_nav),
            before_reduction_maximum_asset_gross=float(before_abs.max() / before_reduction_nav),
            boundary_actual_gross=float(boundary_abs.sum() / nav[t + 1]),
            boundary_actual_net=float(held[t] @ prices[t + 1] / nav[t + 1]),
            boundary_maximum_asset_gross=float(boundary_abs.max() / nav[t + 1]),
            allocated_leg_gross=float(mapped[t]["allocated_leg_gross"]) if t < 62 else 0.0,
            allocated_maximum_asset_gross=float(mapped[t]["allocated_underlier_gross"].max())
            if t < 62
            else 0.0,
            covariance_annual_vol=annual_risk,
            ramp_L1_after_eligibility_release=float(distance[t]),
            terminal_paid_flat=bool(t == 62),
        )
        for j, name in enumerate(CORE5):
            row["held_" + name] = float(held[t, j])
        rows.append(row)
        carry = held[t]
    np.testing.assert_allclose(
        totals,
        [float(report[n].detach()) for n in ("fees", "spread", "slippage")],
        rtol=1e-12,
        atol=1e-10,
    )
    np.testing.assert_allclose(
        funding_total, float(report["funding"].detach()), rtol=1e-12, atol=1e-10
    )
    np.testing.assert_allclose(
        reduction_total, float(report["charged_reduction_cost"].detach()), rtol=1e-12, atol=1e-10
    )
    if (
        residual > 1e-8
        or abs(price_total + funding_total - totals.sum() - (nav[-1] - 10000)) > 1e-8
    ):
        raise ValueError("Complete independent PnL algebra failed")
    daily_return = nav[1:] / nav[:-1] - 1
    utility = float(np.sum(np.log(nav[1:] / nav[:-1]) - 5 * np.minimum(daily_return, 0) ** 2))
    np.testing.assert_allclose(
        utility, float(report["utility_sum"].detach()), rtol=1e-12, atol=1e-14
    )
    active = rows[:62]
    metrics = dict(
        capital=10000.0,
        decisions=63,
        active_intervals=62,
        net_PnL=float(nav[-1] - 10000),
        return_fraction=float(nav[-1] / 10000 - 1),
        utility_sum=utility,
        mean_loss=-utility / 63,
        maximum_daily_drawdown=float(np.max(1 - nav / np.maximum.accumulate(nav))),
        fees=float(totals[0]),
        spread=float(totals[1]),
        slippage=float(totals[2]),
        total_cost=float(totals.sum()),
        funding=funding_total,
        price_PnL=price_total,
        turnover_USDT=turnover_total,
        charged_reduction_cost=reduction_total,
        risk_events=len(report["risk_events"]),
        terminal_paid_cost=sum(cost(-held[-2], prices[-2])),
        paid_terminal_cash=bool(report["terminal_cash_realized"]),
        terminal_NAV=float(nav[-1]),
        request_mean=request.mean(0).tolist(),
        applied_budget_mean=expand(budget).mean(0).tolist(),
        maximum_ramp_L1_after_release=float(distance.max()),
        accounting_maximum_NAV_error=residual,
        cost_funding_utility_independent_algebra_pass=True,
        status="CHARGED_DAILY_SURROGATE_NOT_NATIVE",
    )
    for name in (
        "opening_actual_gross",
        "opening_maximum_asset_gross",
        "before_reduction_actual_gross",
        "before_reduction_maximum_asset_gross",
        "boundary_actual_gross",
        "boundary_maximum_asset_gross",
        "allocated_leg_gross",
        "allocated_maximum_asset_gross",
        "covariance_annual_vol",
    ):
        metrics["maximum_" + name] = max(r[name] for r in active)
        metrics["mean_active_" + name] = float(np.mean([r[name] for r in active]))
    for name in ("opening_actual_net", "boundary_actual_net"):
        metrics["mean_active_" + name] = float(np.mean([r[name] for r in active]))
        metrics["minimum_" + name], metrics["maximum_" + name] = (
            min(r[name] for r in active),
            max(r[name] for r in active),
        )
    return metrics, rows


def math_sqrt(value):
    if value < -1e-15:
        raise ValueError("Invalid covariance variance")
    return float(np.sqrt(max(0.0, value)))


def run(state, economic_directory, output):
    began = time.monotonic()
    output = Path(output)
    if output.exists():
        raise FileExistsError("Exclusive immutable result destination required")
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    pa.set_io_thread_count(1)
    pa.set_cpu_count(1)
    episode, prototype, scaler, inputs = load(state, economic_directory)
    model = frozen_model(scaler)
    identity, parameters, rng = (
        model_identity(model),
        parameter_identity(model),
        torch.get_rng_state().clone(),
    )
    with torch.no_grad():
        requests = predict_episode(model, episode, feature_batch_size=32).numpy()
        repeat = predict_episode(model, episode, feature_batch_size=32).numpy()
    np.testing.assert_array_equal(requests, repeat)
    if (
        model_identity(model) != identity
        or parameter_identity(model) != parameters
        or not torch.equal(rng, torch.get_rng_state())
    ):
        raise ValueError("Deterministic eval must preserve model/scaler/RNG")
    if (
        requests.shape != (63, 6)
        or np.any(requests[~episode.eligible])
        or not np.isfinite(requests).all()
    ):
        raise ValueError("Exact masked canonical E6 output required")
    output.mkdir(parents=True)
    records, arrays, daily_rows, events = {}, {}, [], {}
    fixed = protocol()
    for name in fixed["policy_order"]:
        request = (
            requests
            if name == "APRIL_PREFIX_GRU512"
            else np.tile(fixed["policies"][name]["request"], (63, 1))
        )
        targets, mapped = prototype.mapped_path(compress(request), episode.internal.contexts)
        with torch.no_grad():
            report = charged_boundary_path(
                torch.tensor(targets, dtype=torch.float64),
                episode.prices,
                episode.funding_coeff,
                plan=BoundaryPlan.full_fill_diagnostic(63),
            )
        record, rows = reconcile(request, episode, targets, mapped, report)
        records[name], events[name] = record, report["risk_events"]
        daily_rows.extend([dict(policy=name, **r) for r in rows])
        arrays.update(
            {
                name + "_requests": request,
                name + "_targets": targets,
                name + "_budget": expand(np.stack([r["budget"] for r in mapped])),
                name + "_nav": report["nav"].numpy(),
                name + "_quantity": report["quantity"].numpy(),
                name + "_boundary_held_quantity": report["boundary_held_quantity"].numpy(),
            }
        )
    np.savez_compressed(
        output / "PAIRED_PATHS.npz",
        decision_us=episode.windows.decision_us,
        symbol_order=np.array(CORE5),
        expert_order=np.array(E6),
        **arrays,
    )
    np.savez_compressed(
        output / "CURRENT_CONTEXT.npz",
        decision_us=episode.windows.decision_us,
        symbol_order=np.array(CORE5),
        expert_order=np.array(E6),
        expert_targets=episode.expert_targets,
        expert_eligible=episode.eligible,
        target_available_us=episode.target_available_us,
        past_returns30=np.stack([c.past_returns30 for c in episode.contexts]),
        expert_state=episode.expert_state,
        expert_input_available_us=episode.expert_input_available_us,
        prices=episode.prices,
        funding_coeff=episode.funding_coeff,
        outcome_available_us=episode.label_available_us,
    )
    # Save126 unique source rows from overlapping windows, including original real warmup.
    values = np.concatenate((episode.windows.values[0], episode.windows.values[1:, -1]))
    valid = np.concatenate((episode.windows.valid[0], episode.windows.valid[1:, -1]))
    steps = np.concatenate((episode.windows.step_valid[0], episode.windows.step_valid[1:, -1]))
    clocks = np.r_[episode.windows.completed_us[0], episode.windows.completed_us[1:, -1]]
    np.savez_compressed(
        output / "FEATURE_ROWS.npz",
        completed_us=clocks,
        values=values,
        valid=valid,
        step_valid=steps,
        symbol_order=np.array(CORE5),
        feature_order=np.array(inputs["feature_order"]),
        aggregate_order=np.array(inputs["aggregate_order"]),
    )
    with (output / "DAILY_ACCOUNTING.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(daily_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(daily_rows)
    learned, control = (records[n] for n in ("APRIL_PREFIX_GRU512", "PREFIX_STATIC_VOL"))
    score = dict(
        schema="FIXED_JULY2024_FROZEN_POLICY_DAILY_RESULTS_V1",
        classification=fixed["classification"],
        protocol_SHA256=PROTOCOL_SHA,
        calendar=fixed["calendar"],
        policy_order=fixed["policy_order"],
        expert_order=E6,
        policies=records,
        primary_control="PREFIX_STATIC_VOL",
        primary_PnL_excess=learned["net_PnL"] - control["net_PnL"],
        primary_utility_excess=learned["utility_sum"] - control["utility_sum"],
        primary_drawdown_difference=learned["maximum_daily_drawdown"]
        - control["maximum_daily_drawdown"],
        model_identity=identity,
        checkpoint_SHA256=sha(FROZEN / "MODEL_ADAM_RNG.pt"),
        scaler_identity=scaler.identity,
        parameters=model.parameter_count,
        completed_training_updates_in_frozen_checkpoint=512,
        model_refits=0,
        optimizer_updates=0,
        scaler_updates=0,
        daily_wallets=4,
        native_wallets=0,
        provider_downloads=0,
        eval_repeat_requests_bit_identical=True,
        Torch_RNG_unchanged=True,
        no_model_promotion=True,
        no_native_OOS_APR_or_stitched_claim=True,
        native_mark_gap=inputs["economics"]["missing_mark_open_UTC"],
        elapsed_seconds=time.monotonic() - began,
    )
    for name, value in (
        ("RESULT.json", score),
        ("INPUT_RECEIPT.json", inputs),
        ("RISK_EVENTS.json", events),
    ):
        (output / name).write_text(
            json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
        )
    if (
        sha(FROZEN / "MODEL_ADAM_RNG.pt") != score["checkpoint_SHA256"]
        or model_identity(model) != identity
    ):
        raise ValueError("Frozen model changed during score")
    paths = list(Path(__file__).parent.glob("*.py")) + list(
        (Path(__file__).parent / "upstream").glob("*.py")
    )
    manifest = dict(
        schema="FIXED_JULY2024_FROZEN_POLICY_RESULT_MANIFEST_V1",
        files={
            p.name: dict(bytes=p.stat().st_size, SHA256=sha(p))
            for p in output.iterdir()
            if p.is_file()
        },
        versioned_sources={str(p.relative_to(REPO)): sha(p) for p in sorted(paths)},
        frozen_model_reference=str(FROZEN.relative_to(REPO)),
        economics_source_commit=inputs["economics"]["source_commit"],
        episode_identity=episode.identity,
        feature_rows_identity=array_digest(values),
        completed_us_identity=array_digest(clocks),
    )
    (output / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            dict(
                primary_PnL_excess=score["primary_PnL_excess"],
                policies={
                    n: dict(
                        net_PnL=r["net_PnL"], maximum_daily_drawdown=r["maximum_daily_drawdown"]
                    )
                    for n, r in records.items()
                },
            )
        )
    )
    return score


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--economics", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.state, args.economics, args.output)
