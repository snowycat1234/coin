"""Independent saved-path accounting for126 rows; no model or wallet execution."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from modules.temporal_two_expert.exact import sha

from .protocol import OLD, ORDER, ROOT


def verify(output):
    output = Path(output)
    manifest = json.loads((output / "MANIFEST.json").read_text())
    for name, entry in manifest["files"].items():
        assert entry == dict(bytes=(output / name).stat().st_size, SHA256=sha(output / name)), name
    for name, value in manifest["sources"].items():
        assert sha(ROOT / name) == value, name
    result = json.loads((output / "RESULT.json").read_text())
    if result["status"] != "TWO_FIXED_DAILY_WALLETS_COMPLETE_NOT_NATIVE":
        return dict(status="PAIRED_FAILURE_RECORDED_AND_BYTES_VERIFIED", result=result)
    old = json.loads((OLD / "RESULT.json").read_text())
    for name, value in result["controls_reused"].items():
        assert value == old["policies"][name]
    with np.load(OLD / "CURRENT_CONTEXT.npz", allow_pickle=False) as z:
        price, coeff, decisions = (z[n].copy() for n in ("prices", "funding_coeff", "decision_us"))
    assert price.shape == (64, 5) and coeff.shape == (63, 5)
    maximum_error = 0.0
    contributions = {}
    for name in ORDER:
        with np.load(output / (name + "_PATH.npz"), allow_pickle=False) as z:
            nav, q, held, target, request = (
                z[n].copy()
                for n in ("nav", "quantity", "boundary_held_quantity", "targets", "request")
            )
        with np.load(output / (name + "_REQUESTS.npz"), allow_pickle=False) as z:
            np.testing.assert_array_equal(request, z["request"])
            np.testing.assert_array_equal(decisions, z["decision_us"])
            assert not np.any(request[~z["eligible"]])
        assert nav.shape == (64,) and q.shape == (63, 5) and nav[0] == 10000
        assert not np.any(target[-1]) and not np.any(q[-1]) and not np.any(held[-1])
        np.testing.assert_allclose(
            q, 0.99 * nav[:-1, None] * target / price[:-1], rtol=1e-13, atol=1e-12
        )
        carry = np.vstack((np.zeros(5), held[:-1]))
        opening, reduction = q - carry, held - q
        notional = np.abs(opening) * price[:-1] + np.abs(reduction) * price[1:]
        fees = 0.00055 * (notional + 0.0008 * (opening * price[:-1] + reduction * price[1:]))
        spread = 0.0004 * notional
        price_pnl = q * np.diff(price, axis=0)
        funding = -q * coeff
        net = price_pnl + funding - fees - 2 * spread
        error = float(np.max(np.abs(net.sum(1) - np.diff(nav))))
        maximum_error = max(maximum_error, error)
        assert error < 1e-8
        with (output / (name + "_DAILY.csv")).open() as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == 63 and rows[-1]["terminal_paid_flat"] == "True"
        for field, array in dict(
            price_PnL=price_pnl.sum(1),
            funding_PnL=funding.sum(1),
            fees=fees.sum(1),
            spread=spread.sum(1),
            slippage=spread.sum(1),
            end_nav=nav[1:],
        ).items():
            np.testing.assert_allclose(
                [float(r[field]) for r in rows], array, rtol=1e-12, atol=1e-10
            )
        metrics = result["policies"][name]
        returns = nav[1:] / nav[:-1] - 1
        utility = float(np.sum(np.log(nav[1:] / nav[:-1]) - 5 * np.minimum(returns, 0) ** 2))
        np.testing.assert_allclose(
            [metrics["net_PnL"], metrics["funding"], metrics["fees"], metrics["utility_sum"]],
            [net.sum(), funding.sum(), fees.sum(), utility],
            rtol=1e-12,
            atol=1e-8,
        )
        contributions[name] = net.sum(0).tolist()
    assert result["new_daily_wallets"] == result["model_inferences"] == 2
    assert result["fits"] == result["optimizer_updates"] == result["scaler_updates"] == 0
    assert result["control_wallets_rerun"] == result["native_wallets"] == 0
    return dict(
        status="PASS_TWO_SAVED_PATHS_IDENTITIES_AND_ACCOUNTING",
        rows=126,
        maximum_daily_PnL_error=maximum_error,
        per_asset_net_PnL=contributions,
        model_inferences=0,
        wallet_rollouts=0,
        fits=0,
        optimizer_updates=0,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = verify(args.output)
    with (args.output / "VERIFICATION.json").open("x") as stream:
        json.dump(receipt, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps(receipt), flush=True)
