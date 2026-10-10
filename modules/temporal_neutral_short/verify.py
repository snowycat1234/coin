"""Independent saved-path verification, with zero model/optimizer/wallet calls."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from modules.temporal_two_expert.exact import sha

from .protocol import ROOT


def verify(output):
    p = Path(output)
    m = json.loads((p / "MANIFEST.json").read_text())
    for n, v in m["files"].items():
        assert v == dict(bytes=(p / n).stat().st_size, SHA256=sha(p / n))
    for n, v in m["sources"].items():
        assert sha(ROOT / n) == v
    result = json.loads((p / "RESULT.json").read_text())
    assert result["status"] == "TWO_FIXED_PERIODS_COMPLETE_DAILY_NOT_NATIVE"
    maximum = 0.0
    count = 0
    for label, folder in [
        ("July", "temporal-july-frozen-transfer-20261010/results"),
        ("Q4", "temporal-selected-refit-q4-20261010/q4-results"),
    ]:
        with np.load(ROOT / "research" / folder / "CURRENT_CONTEXT.npz", allow_pickle=False) as z:
            prices = z["prices"]
            coeff = z["funding_coeff"]
            decisions = z["decision_us"]
        n = len(decisions)
        with np.load(p / (label + "_PATH.npz"), allow_pickle=False) as z:
            nav = z["nav"]
            q = z["quantity"]
            held = z["boundary_held_quantity"]
            request = z["request"]
            targets = z["targets"]
        with np.load(p / (label + "_REQUESTS.npz"), allow_pickle=False) as z:
            np.testing.assert_array_equal(request, z["request"])
            np.testing.assert_array_equal(decisions, z["decision_us"])
            assert not np.any(request[~z["eligible"]])
        opening = prices[:n]
        end = prices[1:] if len(prices) == n + 1 else np.vstack((prices[1:], prices[-1:]))
        funding = coeff if len(coeff) == n else np.vstack((coeff, np.zeros((1, 5))))
        assert (
            len(nav) == n + 1
            and nav[0] == 10000
            and not np.any(q[-1])
            and not np.any(held[-1])
            and not np.any(targets[-1])
        )
        np.testing.assert_allclose(
            q, 0.99 * nav[:-1, None] * targets / opening, atol=1e-12, rtol=1e-13
        )
        carry = np.vstack((np.zeros((1, 5)), held[:-1]))
        entry = q - carry
        reduce = held - q
        notional = np.abs(entry) * opening + np.abs(reduce) * end
        fee = 0.00055 * (notional + 0.0008 * (entry * opening + reduce * end))
        spread = 0.0004 * notional
        price = q * (end - opening)
        fund = -q * funding
        net = price + fund - fee - 2 * spread
        err = float(np.max(np.abs(np.diff(nav) - net.sum(1))))
        assert err < 1e-8
        maximum = max(maximum, err)
        with (p / (label + "_DAILY.csv")).open() as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == n and rows[-1]["terminal_paid_flat"] == "True"
        for key, a in dict(
            price_PnL=price.sum(1),
            funding_PnL=fund.sum(1),
            fees=fee.sum(1),
            spread=spread.sum(1),
            slippage=spread.sum(1),
            end_nav=nav[1:],
        ).items():
            np.testing.assert_allclose([float(r[key]) for r in rows], a, atol=1e-10, rtol=1e-12)
        record = result["policies"][label]
        np.testing.assert_allclose(
            [
                record["net_PnL"],
                record["total_cost"],
                record["funding"],
                record["maximum_daily_drawdown"],
            ],
            [
                net.sum(),
                (fee + 2 * spread).sum(),
                fund.sum(),
                np.max(1 - nav / np.maximum.accumulate(nav)),
            ],
            atol=1e-8,
            rtol=1e-12,
        )
        count += n
    receipt = dict(
        status="PASS_SAVED_TWO_PERIODS_AND_ACCOUNTING",
        rows=count,
        maximum_PnL_error=maximum,
        wallet_runs=0,
        model_inferences=0,
        optimizer_updates=0,
    )
    with (p / "VERIFICATION.json").open("x") as f:
        json.dump(receipt, f, indent=2)
    print(json.dumps(receipt))
    return receipt


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    verify(p.parse_args().output)
