"""Read-only result/checkpoint/request/accounting verification; no inference/rollout."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from modules.temporal_short_expansion.model import E6
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import CORE5, DAY_US, array_digest

from .data import END, EXECUTION_DELAY_US, ROOT, START
from .evaluate import CONTROLS, ORDER
from .reconcile import cost


def verify(output):
    output = Path(output)
    m = json.loads((output / "MANIFEST.json").read_text())
    for name, expected in m["files"].items():
        p = output / name
        if expected != dict(bytes=p.stat().st_size, SHA256=sha(p)):
            raise ValueError("Saved result file bytes differ:" + name)
    for name, expected in m["versioned_sources"].items():
        if sha(ROOT / name) != expected:
            raise ValueError("Bound source bytes differ:" + name)
    result = json.loads((output / "RESULT.json").read_text())
    assert result["daily_wallets"] == 4 and result["reserve_model_scores"] == 1
    assert result["optimizer_updates"] == result["scaler_updates"] == result["native_wallets"] == 0
    assert result["synthetic_input_rows"] == 0 and result["training_updates"] == 256
    bundle = output / "native-handoff"
    native = json.loads((bundle / "MANIFEST.json").read_text())
    for name, expected in native["files"].items():
        p = bundle / name
        assert expected == dict(bytes=p.stat().st_size, SHA256=sha(p))
    assert sha(bundle / "MODEL_ADAM_RNG.pt") == result["checkpoint_SHA256"]
    saved = torch.load(bundle / "MODEL_ADAM_RNG.pt", map_location="cpu", weights_only=True)
    assert saved["step"] == 256 and saved["model_identity"] == result["model_identity"]
    ages = [int(v["step"]) for v in saved["optimizer"]["state"].values()]
    assert len(ages) == 13 and set(ages) == {256}
    assert saved["optimizer"]["param_groups"][0]["lr"] == 0.0003
    for name, expected in native["source_files"].items():
        assert sha(bundle / "source" / name) == expected
    with np.load(output / "FEATURE_ROWS.npz", allow_pickle=False) as z:
        assert z["values"].shape == (155, 5, 24) and len(z["completed_us"]) == 155
        np.testing.assert_array_equal(
            z["completed_us"], np.arange(START - 63 * DAY_US, END, DAY_US)
        )
        assert array_digest(z["values"]) == m["feature_rows_identity"]
        assert array_digest(z["completed_us"]) == m["completed_us_identity"]
    with np.load(output / "CURRENT_CONTEXT.npz", allow_pickle=False) as z:
        prices, coeff = z["prices"].copy(), z["funding_coeff"].copy()
        assert prices.shape == (92, 5) and coeff.shape == (91, 5)
        assert z["expert_state"].shape == (92, 18)
        assert np.all(z["input_available_us"] <= z["decision_us"][:, None])
        context = {name: z[name].copy() for name in z.files}
        with np.load(bundle / "CURRENT_EXPERT_INPUTS92.npz", allow_pickle=False) as native_context:
            for name in (
                "decision_us",
                "expert_targets",
                "expert_eligible",
                "target_available_us",
                "past_returns30",
                "expert_state",
                "input_available_us",
            ):
                np.testing.assert_array_equal(native_context[name], z[name])
            np.testing.assert_array_equal(native_context["symbol_order"], CORE5)
            np.testing.assert_array_equal(native_context["expert_order"], E6)
    table = pd.read_csv(output / "DAILY_ACCOUNTING.csv")
    maximum_error = 0.0
    with np.load(output / "PAIRED_PATHS.npz", allow_pickle=False) as z:
        decisions = z["decision_us"]
        np.testing.assert_array_equal(decisions, np.arange(START, END, DAY_US))
        with np.load(bundle / "REQUESTS.npz", allow_pickle=False) as native_requests:
            np.testing.assert_array_equal(
                native_requests["desired_expert_budget"], z[ORDER[0] + "_requests"]
            )
            np.testing.assert_array_equal(native_requests["decision_us"], decisions)
            np.testing.assert_array_equal(native_requests["request_available_us"], decisions)
            np.testing.assert_array_equal(native_requests["symbol_order"], CORE5)
            np.testing.assert_array_equal(native_requests["expert_order"], E6)
            allowed = np.array(
                [
                    n in saved["binding"]["specification"]["model_contract"]["allowed_actions"]
                    for n in E6
                ]
            )
            np.testing.assert_array_equal(
                native_requests["action_eligible"], context["expert_eligible"] & allowed
            )
            assert not native_requests["desired_expert_budget"][
                ~native_requests["action_eligible"]
            ].any()
            assert np.all(native_requests["feature_available_us"] <= decisions)
        for name in ORDER:
            if name in result.get("failed_policies", []):
                assert result["policies"][name]["paid_terminal_cash"] is False
                assert name + "_nav" not in z.files
                continue
            requests, nav, target, budget, quantity, held = [
                z[name + "_" + k]
                for k in (
                    "requests",
                    "nav",
                    "targets",
                    "budget",
                    "quantity",
                    "boundary_held_quantity",
                )
            ]
            assert requests.shape == budget.shape == (92, 6) and nav.shape == (93,)
            assert not requests[:, 2:4].any() and not target[-1].any()
            assert not quantity[-1].any() and not held[-1].any()
            np.testing.assert_allclose(requests.sum(1), 1, rtol=0, atol=1e-12)
            np.testing.assert_allclose(budget.sum(1), 1, rtol=0, atol=1e-12)
            np.testing.assert_allclose(
                quantity, 0.99 * nav[:-1, None] * target / prices, rtol=1e-13, atol=1e-12
            )
            if name in CONTROLS:
                np.testing.assert_array_equal(requests, np.tile(CONTROLS[name], (92, 1)))
                with np.load(
                    bundle / ("REQUESTS_" + name + ".npz"), allow_pickle=False
                ) as control_requests:
                    np.testing.assert_array_equal(
                        control_requests["desired_expert_budget"], requests
                    )
                    np.testing.assert_array_equal(control_requests["decision_us"], decisions)
            rows = table[table.policy == name]
            assert len(rows) == 92
            np.testing.assert_array_equal(rows.execution_us, decisions + EXECUTION_DELAY_US)
            carry = np.zeros(5)
            totals = np.zeros(3)
            funding = price_pnl = 0.0
            for t in range(92):
                active = t < 91
                boundary = prices[t + 1] if active else prices[t]
                opening = cost(quantity[t] - carry, prices[t])
                reduction = cost(held[t] - quantity[t], boundary)
                payment = sum(opening) + sum(reduction)
                funded = -float(quantity[t] @ coeff[t]) if active else 0.0
                movement = float(quantity[t] @ (boundary - prices[t])) if active else 0.0
                maximum_error = max(
                    maximum_error, abs(nav[t] - payment + funded + movement - nav[t + 1])
                )
                totals += np.array(opening) + reduction
                funding += funded
                price_pnl += movement
                carry = held[t]
            metrics = result["policies"][name]
            np.testing.assert_allclose(
                totals, [metrics[k] for k in ("fees", "spread", "slippage")], rtol=1e-12, atol=1e-10
            )
            np.testing.assert_allclose(
                [funding, price_pnl, nav[-1] - 10000],
                [metrics[k] for k in ("funding", "price_PnL", "net_PnL")],
                rtol=1e-12,
                atol=1e-10,
            )
            utility = float(
                np.sum(np.log(nav[1:] / nav[:-1]) - 5 * np.minimum(nav[1:] / nav[:-1] - 1, 0) ** 2)
            )
            np.testing.assert_allclose(utility, metrics["utility_sum"], rtol=1e-12, atol=1e-14)
            np.testing.assert_allclose(
                max(1 - nav / np.maximum.accumulate(nav)), metrics["maximum_daily_drawdown"]
            )
            assert metrics["paid_terminal_cash"]
    assert maximum_error < 1e-8
    selected, vol = [result["policies"][n] for n in (ORDER[0], "FROZEN_VOL")]
    if "net_PnL" in selected and "net_PnL" in vol:
        assert result["primary_PnL_excess"] == selected["net_PnL"] - vol["net_PnL"]
        assert result["primary_utility_excess"] == selected["utility_sum"] - vol["utility_sum"]
    else:
        assert result["primary_PnL_excess"] is result["primary_utility_excess"] is None
    receipt = dict(
        status="PASS",
        verified_policies=4,
        verified_daily_rows=len(table),
        failed_policies=result.get("failed_policies", []),
        native_requests=92,
        feature_rows=155,
        real_prices=92,
        real_funding_intervals=91,
        model_and_all13_Adam_ages=256,
        maximum_accounting_NAV_error=maximum_error,
        model_inferences=0,
        economic_rollouts=0,
        optimizer_updates=0,
        result_SHA256=sha(output / "RESULT.json"),
    )
    with (output / "VERIFICATION.json").open("x") as stream:
        stream.write(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    verify(parser.parse_args().output)
