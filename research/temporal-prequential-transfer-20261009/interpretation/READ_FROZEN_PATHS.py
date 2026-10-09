"""Read saved forward paths; no inference, optimizer or economic rollout.

The zero-risk-event model and primary paths admit exact ledger algebra from
saved NAV/targets/prices. Expert-leg price/funding attribution uses actual
mapped budgets and each wallet's own saved NAV. Transaction costs stay netted
at account level. The symmetric exposure/composition split is descriptive,
not a causal estimate or a hypothetical switching strategy.
"""

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

FOLDS = ("FOLD_20230703", "FOLD_20231002", "FOLD_20240101")
ACTIVE = (0, 1, 4, 5)
LEG_NAMES = ("CASH", "VOL", "CS", "SHORT")
MODEL, PRIMARY = "FRESH_GRU", "VOL50_CS50"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(a, b, tolerance=2e-8):
    np.testing.assert_allclose(a, b, atol=tolerance, rtol=0)


def stats(a):
    return dict(
        mean=float(np.mean(a)),
        median=float(np.median(a)),
        minimum=float(np.min(a)),
        maximum=float(np.max(a)),
    )


def concentration(a):
    a = np.asarray(a)
    order = np.argsort(a)[::-1]
    positive = float(a[a > 0].sum())
    negative = float(a[a < 0].sum())
    return dict(
        positive_dates=int((a > 0).sum()),
        negative_dates=int((a < 0).sum()),
        positive_total=positive,
        negative_total=negative,
        top3_positive_sum=float(a[order[:3]].sum()),
        top5_positive_sum=float(a[order[:5]].sum()),
        top10_positive_sum=float(a[order[:10]].sum()),
        top5_share_of_positive_mass=float(np.maximum(a[order[:5]], 0).sum() / positive)
        if positive
        else None,
        attribution_remaining_without_top3=float(a.sum() - a[order[:3]].sum()),
        attribution_remaining_without_top5=float(a.sum() - a[order[:5]].sum()),
        omission_is_read_only_attribution_not_a_replayed_wallet=True,
    )


def ledger(name, paths, context, result):
    record = result["policies"][name]
    assert record["risk_events"] == 0 and record["charged_reduction_cost"] == 0
    nav, targets, budget = (paths[name + "_" + field] for field in ("nav", "targets", "budget"))
    price, funding = context["surrogate_prices"], context["surrogate_funding_coeff"]
    assert nav.shape == (64,) and targets.shape == (63, 5) and budget.shape == (63, 6)
    assert np.all(targets[-1] == 0) and nav[0] == 10000
    quantity = 0.99 * nav[:-1, None] * targets / price[:-1]
    delta = quantity - np.concatenate((np.zeros((1, 5)), quantity[:-1]))
    fee_asset = 0.00055 * price[:-1] * (np.abs(delta) + 0.0008 * delta)
    spread_asset = 0.0004 * price[:-1] * np.abs(delta)
    slippage_asset = spread_asset.copy()
    cost_asset = fee_asset + spread_asset + slippage_asset
    price_asset = quantity * np.diff(price, axis=0)
    funding_asset = -quantity * funding
    net = np.diff(nav)
    close(net, (price_asset + funding_asset - cost_asset).sum(1))
    for key, array in (
        ("fees", fee_asset),
        ("spread", spread_asset),
        ("slippage", slippage_asset),
        ("funding", funding_asset),
    ):
        close(array.sum(), record[key])
    close(net.sum(), record["net_PnL"])
    returns = net / nav[:-1]
    utility = np.log1p(returns) - 5 * np.minimum(returns, 0) ** 2
    close(utility.sum(), record["utility_sum"], 2e-14)
    legs = budget[:, :, None] * context["expert_targets"]
    legs[-1] = 0  # Forced paid cash, not the model's final unconstrained request.
    close(legs.sum(1), targets, 1e-14)
    leg_quantity = 0.99 * nav[:-1, None, None] * legs / price[:-1, None, :]
    leg_price = (leg_quantity * np.diff(price, axis=0)[:, None, :]).sum(2)
    leg_funding = -(leg_quantity * funding[:, None, :]).sum(2)
    close(leg_price.sum(1), price_asset.sum(1))
    close(leg_funding.sum(1), funding_asset.sum(1))
    allocated = np.abs(legs).sum((1, 2))
    allocated_asset = np.abs(legs).sum(1)
    close(allocated[:-1].max(), record["maximum_allocated_gross"], 1e-14)
    close(allocated_asset[:-1].max(), record["maximum_allocated_asset_gross"], 1e-14)
    after_cost = nav[:-1] - cost_asset.sum(1)
    fill_gross = (np.abs(quantity) * price[:-1]).sum(1) / after_cost
    end_gross = (np.abs(quantity) * price[1:]).sum(1) / nav[1:]
    actual_short = (np.maximum(-quantity, 0) * price[:-1]).sum(1) / after_cost
    actual_long = (np.maximum(quantity, 0) * price[:-1]).sum(1) / after_cost
    covariance = np.stack(
        [np.cov(x, rowvar=False, ddof=1) * 365 for x in context["past_returns30"]]
    )
    expected_vol = np.sqrt(np.maximum(np.einsum("ti,tij,tj->t", targets, covariance, targets), 0))
    flat_targets = np.all(context["expert_targets"][:-1] == 0, axis=2)
    flat_budget = np.where(flat_targets[:, (1, 4, 5)], budget[:-1, (1, 4, 5)], 0).sum(1)
    flat_experts = {
        LEG_NAMES[k]: dict(
            flat_target_days=int(flat_targets[:, j].sum()),
            eligible_days=int(context["expert_eligible"][:-1, j].sum()),
            mean_budget_allocated_to_flat_target=float(
                np.where(flat_targets[:, j], budget[:-1, j], 0).mean()
            ),
            mean_budget_when_target_flat=float(budget[:-1, j][flat_targets[:, j]].mean())
            if flat_targets[:, j].any()
            else None,
        )
        for k, j in enumerate(ACTIVE)
        if j != 0
    }
    summary = dict(
        net_PnL=float(net.sum()),
        price_PnL=float(price_asset.sum()),
        funding=float(funding_asset.sum()),
        execution_cost=float(cost_asset.sum()),
        fees=float(fee_asset.sum()),
        spread=float(spread_asset.sum()),
        slippage=float(slippage_asset.sum()),
        terminal_close_cost=float(cost_asset[-1].sum()),
        absolute_turnover_USDT=float((np.abs(delta) * price[:-1]).sum()),
        maximum_drawdown=record["maximum_drawdown"],
        daily_net_return_std=float(np.std(returns, ddof=1)),
        expected_annual_vol_active=stats(expected_vol[:-1]),
        allocated_gross_active=stats(allocated[:-1]),
        allocated_asset_gross_max=float(allocated_asset.max()),
        actual_fill_gross_active=stats(fill_gross[:-1]),
        actual_end_gross_active=stats(end_gross[:-1]),
        actual_long_gross_active=stats(actual_long[:-1]),
        actual_short_gross_active=stats(actual_short[:-1]),
        cancellation_gross_active=stats(allocated[:-1] - np.abs(targets[:-1]).sum(1)),
        signed_target_net_active=stats(targets[:-1].sum(1)),
        mean_zero_target_risky_expert_budget=float(flat_budget.mean()),
        flat_expert_targets=flat_experts,
        expert_leg_price_PnL={
            LEG_NAMES[i]: float(leg_price[:, j].sum()) for i, j in enumerate(ACTIVE)
        },
        expert_leg_funding={
            LEG_NAMES[i]: float(leg_funding[:, j].sum()) for i, j in enumerate(ACTIVE)
        },
        asset_price_PnL=dict(
            zip(context["symbol_order"].tolist(), price_asset.sum(0).tolist(), strict=True)
        ),
        positive_net_dates=int((net > 0).sum()),
        negative_net_dates=int((net < 0).sum()),
        net_PnL_concentration=concentration(net),
    )
    return dict(
        nav=nav,
        targets=targets,
        budget=budget,
        quantity=quantity,
        returns=returns,
        utility=utility,
        cost=cost_asset.sum(1),
        price=price_asset.sum(1),
        funding=funding_asset.sum(1),
        net=net,
        leg_price=leg_price,
        leg_funding=leg_funding,
        price_asset=price_asset,
        allocated=allocated,
        fill_gross=fill_gross,
        actual_short=actual_short,
        actual_long=actual_long,
        summary=summary,
    )


def stability(request, budget):
    request, budget = request[:-1], budget[:-1]
    s = 1 - request[:, 0]
    r = request[:, 5] / s
    w = request[:, 4] / (request[:, 1] + request[:, 4])
    gates = {}
    for name, values in (("investment_s", s), ("pair_w", w), ("short_r", r)):
        gates[name] = dict(
            **stats(values),
            near_extreme_fraction=float(((values < 0.01) | (values > 0.99)).mean()),
            derivative_below001_fraction=float((values * (1 - values) < 0.001).mean()),
            mean_absolute_daily_change=float(np.abs(np.diff(values)).mean()),
            median_absolute_daily_change=float(np.median(np.abs(np.diff(values)))),
        )
    req_diff, budget_diff = (
        np.abs(np.diff(request, axis=0)).sum(1),
        np.abs(np.diff(budget, axis=0)).sum(1),
    )
    return dict(
        active_decisions=62,
        forced_terminal_excluded=True,
        gates=gates,
        request_daily_L1=stats(req_diff),
        mapped_budget_daily_L1_including_releases=stats(budget_diff),
        request_L1_gt1_dates=int((req_diff > 1).sum()),
        dominant_request_gt95_fraction=float((request.max(1) > 0.95).mean()),
        dominant_request_switches=int((request.argmax(1)[1:] != request.argmax(1)[:-1]).sum()),
        dominant_mapped_budget_switches=int((budget.argmax(1)[1:] != budget.argmax(1)[:-1]).sum()),
        mean_request_active=dict(zip(LEG_NAMES, request[:, ACTIVE].mean(0).tolist(), strict=True)),
        mean_mapped_budget_active=dict(
            zip(LEG_NAMES, budget[:, ACTIVE].mean(0).tolist(), strict=True)
        ),
        stability_scope=(
            "Exact same-snapshot repeatability checked earlier; temporal variation described here. "
            "No seed or input perturbation test."
        ),
    )


def analyze(root, destination):
    assert not destination.exists(), "Create a new immutable interpretation destination"
    destination.mkdir(parents=True)
    folds, input_hashes = {}, {}
    daily_rows = []
    for fold in FOLDS:
        directory = root / "forward" / fold
        manifest = json.loads((directory / "MANIFEST.json").read_text())
        assert manifest["status"] == "COMPLETE" and manifest["completed_updates"] == 512
        for name, entry in manifest["files"].items():
            assert digest(directory / name) == entry["SHA256"]
        input_hashes[fold] = {
            name: digest(directory / name)
            for name in (
                "MANIFEST.json",
                "PAIRED_PATHS.npz",
                "CURRENT_CONTEXT63.npz",
                "RESULT.json",
                "MODEL_ADAM_RNG.pt",
            )
        }
        result = json.loads((directory / "RESULT.json").read_text())
        with np.load(directory / "PAIRED_PATHS.npz", allow_pickle=False) as loaded:
            paths = {key: loaded[key].copy() for key in loaded.files}
        with np.load(directory / "CURRENT_CONTEXT63.npz", allow_pickle=False) as loaded:
            context = {key: loaded[key].copy() for key in loaded.files}
        close(paths["decision_us"], context["decision_us"], 0)
        model, primary = (ledger(name, paths, context, result) for name in (MODEL, PRIMARY))
        target_m, target_c = model["targets"], primary["targets"]
        gross_m, gross_c = np.abs(target_m).sum(1), np.abs(target_c).sum(1)
        unit_m = np.divide(
            target_m, gross_m[:, None], out=np.zeros_like(target_m), where=gross_m[:, None] > 0
        )
        unit_c = np.divide(
            target_c, gross_c[:, None], out=np.zeros_like(target_c), where=gross_c[:, None] > 0
        )
        asset_return = (
            np.diff(context["surrogate_prices"], axis=0) / context["surrogate_prices"][:-1]
        )
        average_nav = 0.5 * (model["nav"][:-1] + primary["nav"][:-1])
        scale = (
            0.99
            * average_nav
            * 0.5
            * (gross_m - gross_c)
            * ((unit_m + unit_c) * asset_return).sum(1)
        )
        composition = (
            0.99
            * average_nav
            * 0.5
            * (gross_m + gross_c)
            * ((unit_m - unit_c) * asset_return).sum(1)
        )
        wallet = (
            0.99
            * 0.5
            * (model["nav"][:-1] - primary["nav"][:-1])
            * ((target_m + target_c) * asset_return).sum(1)
        )
        close(scale + composition + wallet, model["price"] - primary["price"])
        excess = model["net"] - primary["net"]
        utility_excess = model["utility"] - primary["utility"]
        close(excess.sum(), result["primary_PnL_excess"])
        close(utility_excess.sum(), result["primary_utility_excess"], 2e-14)
        fixed_daily = {
            name: np.diff(paths[name + "_nav"]) for name in result["policies"] if name != MODEL
        }
        for name, daily in fixed_daily.items():
            close(daily.sum(), result["policies"][name]["net_PnL"])
        date_records = []
        for index in range(63):
            date = (
                datetime.fromtimestamp(int(context["decision_us"][index]) / 1000000, timezone.utc)
                .date()
                .isoformat()
            )
            row = dict(
                fold=fold,
                decision_date=date,
                terminal_paid_close=index == 62,
                model_net_PnL=float(model["net"][index]),
                primary_net_PnL=float(primary["net"][index]),
                PnL_excess=float(excess[index]),
                utility_excess=float(utility_excess[index]),
                model_price_PnL=float(model["price"][index]),
                primary_price_PnL=float(primary["price"][index]),
                model_funding=float(model["funding"][index]),
                primary_funding=float(primary["funding"][index]),
                model_execution_cost=float(model["cost"][index]),
                primary_execution_cost=float(primary["cost"][index]),
                exposure_magnitude_price_excess=float(scale[index]),
                signed_composition_price_excess=float(composition[index]),
                own_NAV_scale_price_excess=float(wallet[index]),
                model_allocated_gross=float(model["allocated"][index]),
                model_actual_fill_gross=float(model["fill_gross"][index]),
                model_actual_long_gross=float(model["actual_long"][index]),
                model_actual_short_gross=float(model["actual_short"][index]),
                model_net_target=float(target_m[index].sum()),
            )
            row.update(
                {
                    "request_" + LEG_NAMES[k]: float(paths[MODEL + "_requests"][index, j])
                    for k, j in enumerate(ACTIVE)
                }
            )
            row.update(
                {
                    "mapped_" + LEG_NAMES[k]: float(model["budget"][index, j])
                    for k, j in enumerate(ACTIVE)
                }
            )
            row.update(
                {
                    "price_PnL_" + LEG_NAMES[k]: float(model["leg_price"][index, j])
                    for k, j in enumerate(ACTIVE)
                }
            )
            row.update(
                {
                    "return_" + symbol: float(asset_return[index, j])
                    for j, symbol in enumerate(context["symbol_order"])
                }
            )
            row.update(
                {
                    "target_" + symbol: float(target_m[index, j])
                    for j, symbol in enumerate(context["symbol_order"])
                }
            )
            row.update(
                {
                    "fixed_" + name + "_net_PnL": float(daily[index])
                    for name, daily in fixed_daily.items()
                }
            )
            date_records.append(row)
        daily_rows.extend(date_records)
        top = np.argsort(excess)[::-1][:5]
        worst = np.argsort(excess)[:5]
        top_profit = np.argsort(model["net"])[::-1][:5]
        dominant = model["budget"][:-1, ACTIVE].argmax(1)
        boundaries = np.r_[0, np.flatnonzero(np.diff(dominant) != 0) + 1, 62]
        segments = []
        for start, stop in zip(boundaries[:-1], boundaries[1:], strict=True):
            segments.append(
                dict(
                    first=date_records[int(start)]["decision_date"],
                    last=date_records[int(stop - 1)]["decision_date"],
                    leading_mapped_budget=LEG_NAMES[int(dominant[start])],
                    decisions=int(stop - start),
                    model_PnL=float(model["net"][start:stop].sum()),
                    excess=float(excess[start:stop].sum()),
                    mean_actual_fill_gross=float(model["fill_gross"][start:stop].mean()),
                    mean_actual_short_gross=float(model["actual_short"][start:stop].mean()),
                )
            )
        weekly = []
        for start in range(0, 63, 7):
            stop = min(start + 7, 63)
            weekly.append(
                dict(
                    first=date_records[start]["decision_date"],
                    last=date_records[stop - 1]["decision_date"],
                    model_PnL=float(model["net"][start:stop].sum()),
                    primary_PnL=float(primary["net"][start:stop].sum()),
                    excess=float(excess[start:stop].sum()),
                    mean_mapped_budget=dict(
                        zip(
                            LEG_NAMES,
                            model["budget"][start:stop, ACTIVE].mean(0).tolist(),
                            strict=True,
                        )
                    ),
                )
            )
        # Requested fixed-control summaries use saved complete account results.
        controls = {}
        for name, record in result["policies"].items():
            cost = record["fees"] + record["spread"] + record["slippage"]
            nav = paths[name + "_nav"]
            controls[name] = dict(
                net_PnL=record["net_PnL"],
                price_PnL=record["net_PnL"] + cost - record["funding"],
                execution_cost=cost,
                funding=record["funding"],
                maximum_drawdown=record["maximum_drawdown"],
                maximum_allocated_gross=record["maximum_allocated_gross"],
                daily_net_return_std=float(np.std(np.diff(nav) / nav[:-1], ddof=1)),
            )
        folds[fold] = dict(
            model=model["summary"],
            primary=primary["summary"],
            controls=controls,
            PnL_excess=float(excess.sum()),
            utility_excess=float(utility_excess.sum()),
            price_excess_split=dict(
                exposure_magnitude=float(scale.sum()),
                signed_asset_composition=float(composition.sum()),
                own_NAV_scale=float(wallet.sum()),
            ),
            funding_excess=float((model["funding"] - primary["funding"]).sum()),
            execution_cost_saving=float((primary["cost"] - model["cost"]).sum()),
            excess_concentration=concentration(excess),
            utility_excess_concentration=concentration(utility_excess),
            top5_excess_dates=[date_records[int(index)] for index in top],
            worst5_excess_dates=[date_records[int(index)] for index in worst],
            top5_model_profit_dates=[date_records[int(index)] for index in top_profit],
            leading_budget_segments=segments,
            weeks=weekly,
            prediction_stability=stability(paths[MODEL + "_requests"], model["budget"]),
        )
    metrics = {}
    for name in ("PnL_excess", "utility_excess"):
        metrics[name] = stats([folds[fold][name] for fold in FOLDS])
    for role in ("model", "primary"):
        for name in (
            "net_PnL",
            "maximum_drawdown",
            "daily_net_return_std",
            "execution_cost",
            "funding",
        ):
            metrics[role + "_" + name] = stats([folds[fold][role][name] for fold in FOLDS])
        for name in (
            "allocated_gross_active",
            "actual_fill_gross_active",
            "actual_short_gross_active",
        ):
            metrics[role + "_" + name + "_mean"] = stats(
                [folds[fold][role][name]["mean"] for fold in FOLDS]
            )
    report = dict(
        schema="READ_ONLY_FROZEN_PREQUENTIAL_PATH_INTERPRETATION_V1",
        created_UTC=datetime.now(timezone.utc).isoformat(),
        optimizer_updates=0,
        model_inferences=0,
        economic_rollouts=0,
        provider_downloads=0,
        native_wallets=0,
        independent_wallets_not_stitched=True,
        APR_not_computed=True,
        input_SHA256=input_hashes,
        equal_fold_weight_summary=metrics,
        folds=folds,
        ledger_checks=(
            "All 63 daily rows and component totals reconciled to saved NAV/results "
            "within 2e-8 USDT; utility within 2e-14."
        ),
        limitations=[
            "Historical seen-project-data daily proxy;original publication clocks uncertified.",
            "Both attributed paths have zero boundary risk events; "
            "no minute/lot/liquidation reconstruction.",
            "Expert-leg price/funding attribution uses actual budgets/own NAV; "
            "net trade cost cannot uniquely be charged to experts.",
            "Exposure/composition/NAV split is symmetric descriptive algebra, "
            "not causal attribution.",
            "Top-date omission sums existing contributions only; "
            "does not execute an alternate wallet.",
            "Standalone account returns are complete separate wallets, "
            "not executable switching labels.",
        ],
    )
    (destination / "RESULT.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    with (destination / "DAILY_ATTRIBUTION.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(daily_rows[0]))
        writer.writeheader()
        writer.writerows(daily_rows)
    print(
        json.dumps(
            dict(
                status="READ_ONLY_FROZEN_LEDGER_ATTRIBUTION_RECONCILED",
                folds=3,
                dates=189,
                mean_PnL_excess=metrics["PnL_excess"]["mean"],
                median_PnL_excess=metrics["PnL_excess"]["median"],
            )
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.root.resolve(), args.destination.resolve())
