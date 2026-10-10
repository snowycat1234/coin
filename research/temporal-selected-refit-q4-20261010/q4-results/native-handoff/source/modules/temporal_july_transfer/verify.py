"""Read-only252-row verification of saved requests/exposure/PnL; no wallets."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import torch

from modules.temporal_short_expansion.adapter import compress, expand
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import array_digest

from .data import EXECUTION_DELAY_US, FROZEN, REPO, load, protocol


def verify(state, economics, result_directory):
    root = Path(result_directory)
    manifest = json.loads((root / "MANIFEST.json").read_text())
    for name, expected in manifest["files"].items():
        if (
            sha(root / name) != expected["SHA256"]
            or (root / name).stat().st_size != expected["bytes"]
        ):
            raise ValueError("Result bytes changed")
    for name, expected in manifest["versioned_sources"].items():
        if sha(REPO / name) != expected:
            raise ValueError("Producer source changed")
    episode, prototype, _, inputs = load(state, economics)
    result = json.loads((root / "RESULT.json").read_text())
    if (
        result["daily_wallets"] != 4
        or result["native_wallets"]
        or result["optimizer_updates"]
        or result["model_refits"]
        or result["scaler_updates"]
        or result["checkpoint_SHA256"] != sha(FROZEN / "MODEL_ADAM_RNG.pt")
        or manifest["episode_identity"] != episode.identity
    ):
        raise ValueError("Exact four frozen daily wallets required")
    with np.load(root / "CURRENT_CONTEXT.npz", allow_pickle=False) as z:
        for name, actual in (
            ("prices", episode.prices),
            ("funding_coeff", episode.funding_coeff),
            ("expert_targets", episode.expert_targets),
            ("expert_eligible", episode.eligible),
            ("target_available_us", episode.target_available_us),
            ("past_returns30", np.stack([c.past_returns30 for c in episode.contexts])),
            ("expert_state", episode.expert_state),
        ):
            np.testing.assert_array_equal(z[name], actual)
    with np.load(root / "FEATURE_ROWS.npz", allow_pickle=False) as z:
        if (
            array_digest(z["values"]) != manifest["feature_rows_identity"]
            or array_digest(z["completed_us"]) != manifest["completed_us_identity"]
        ):
            raise ValueError("Unique input rows changed")
        for i in range(63):
            np.testing.assert_array_equal(z["values"][i : i + 64], episode.windows.values[i])
            np.testing.assert_array_equal(z["valid"][i : i + 64], episode.windows.valid[i])
            np.testing.assert_array_equal(
                z["step_valid"][i : i + 64], episode.windows.step_valid[i]
            )
    table = pd.read_csv(root / "DAILY_ACCOUNTING.csv")
    frozen = protocol()
    maximum_error = 0.0
    per_asset = {}
    with np.load(root / "PAIRED_PATHS.npz", allow_pickle=False) as z:
        np.testing.assert_array_equal(z["decision_us"], episode.windows.decision_us)
        for name in frozen["policy_order"]:
            request, nav, target, budget, quantity, held = [
                z[name + "_" + key]
                for key in (
                    "requests",
                    "nav",
                    "targets",
                    "budget",
                    "quantity",
                    "boundary_held_quantity",
                )
            ]
            if name != "APRIL_PREFIX_GRU512":
                np.testing.assert_array_equal(
                    request, np.tile(frozen["policies"][name]["request"], (63, 1))
                )
            repeated, mapped = prototype.mapped_path(compress(request), episode.internal.contexts)
            np.testing.assert_array_equal(target, repeated)
            np.testing.assert_array_equal(budget, expand(np.stack([r["budget"] for r in mapped])))
            rows = table[table.policy == name]
            np.testing.assert_array_equal(rows.decision_us, episode.windows.decision_us)
            np.testing.assert_array_equal(
                rows.execution_us, episode.windows.decision_us + EXECUTION_DELAY_US
            )
            np.testing.assert_allclose(rows.start_nav, nav[:-1], rtol=1e-15, atol=2e-12)
            np.testing.assert_allclose(rows.end_nav, nav[1:], rtol=1e-15, atol=2e-12)
            previous = np.vstack((np.zeros((1, 5)), held[:-1]))
            opening_delta = quantity - previous
            reduction_delta = held - quantity
            price = episode.prices
            notional = np.abs(opening_delta) * price[:-1] + np.abs(reduction_delta) * price[1:]
            fees = 0.00055 * (
                notional + 0.0008 * (opening_delta * price[:-1] + reduction_delta * price[1:])
            )
            spread = 0.0004 * notional
            asset_price = quantity * np.diff(price, axis=0)
            asset_funding = -quantity * episode.funding_coeff
            net_contribution = asset_price + asset_funding - fees - 2 * spread
            daily = net_contribution.sum(1)
            np.testing.assert_allclose(daily, np.diff(nav), rtol=1e-10, atol=1e-8)
            maximum_error = max(maximum_error, float(np.max(np.abs(daily - np.diff(nav)))))
            metrics = result["policies"][name]
            np.testing.assert_allclose(
                net_contribution.sum(), metrics["net_PnL"], rtol=1e-11, atol=1e-8
            )
            np.testing.assert_allclose(
                [fees.sum(), spread.sum(), asset_funding.sum()],
                [metrics["fees"], metrics["spread"], metrics["funding"]],
                rtol=1e-12,
                atol=1e-10,
            )
            for field in (
                "fees",
                "spread",
                "slippage",
                "funding_PnL",
                "price_PnL",
                "charged_reduction_cost",
                "turnover_USDT",
            ):
                key = {"funding_PnL": "funding"}.get(field, field)
                np.testing.assert_allclose(rows[field].sum(), metrics[key], rtol=1e-12, atol=1e-9)
            drawdown = float(np.max(1 - nav / np.maximum.accumulate(nav)))
            returns = nav[1:] / nav[:-1] - 1
            utility = float(np.sum(np.log1p(returns) - 5 * np.minimum(returns, 0) ** 2))
            np.testing.assert_allclose(
                [drawdown, utility],
                [metrics["maximum_daily_drawdown"], metrics["utility_sum"]],
                atol=1e-12,
                rtol=1e-12,
            )
            if (
                np.any(held[-1])
                or np.any(quantity[-1])
                or np.any(target[-1])
                or not metrics["paid_terminal_cash"]
                or rows.iloc[-1][["fees", "spread", "slippage"]].sum() <= 0
            ):
                raise ValueError("Paid common terminal flatten required")
            if (
                rows.opening_actual_gross.max() > 0.6 + 1e-12
                or rows.boundary_actual_gross.max() > 0.6 + 1e-12
                or rows.opening_maximum_asset_gross.max() > 0.3 + 1e-12
                or rows.boundary_maximum_asset_gross.max() > 0.3 + 1e-12
                or rows.covariance_annual_vol.max() > 0.1 + 1e-12
                or rows.ramp_L1_after_eligibility_release.max() > 0.1 + 1e-12
            ):
                raise ValueError("Exposure/risk/ramp bounds failed")
            per_asset[name] = net_contribution.sum(0).tolist()
    if len(table) != 252:
        raise ValueError("All252 rows required")
    return dict(
        status="PASS",
        verified_daily_rows=252,
        feature_windows=63,
        faithful_source_feature_parity_rows=inputs["source_feature_parity_rows"],
        target_budget_parity="BIT_IDENTICAL_ALL252_ROWS",
        accounting_maximum_daily_PnL_error=maximum_error,
        net_PnL_by_CORE5_asset=per_asset,
        economic_wallets_rerun=0,
        native_wallets=0,
        inference_calls=0,
        fits=0,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--economics", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    pa.set_cpu_count(1)
    pa.set_io_thread_count(1)
    receipt = verify(args.state, args.economics, args.results)
    with args.output.open("x") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(receipt))
