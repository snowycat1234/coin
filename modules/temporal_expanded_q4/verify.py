"""Read-only identity and independent saved-path accounting; zero policy/wallet calls."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(output):
    output = Path(output)
    manifest = json.loads((output / "MANIFEST.json").read_text())
    for name, entry in manifest["files"].items():
        path = output / name
        assert entry == dict(bytes=path.stat().st_size, SHA256=sha(path)), name
    for name, value in manifest["source_files"].items():
        assert sha(ROOT / name) == value, name
    score = json.loads((output / "RESULT.json").read_text())
    if score["status"] != "CHARGED_DAILY_SURROGATE_NOT_NATIVE":
        return dict(status="FAILURE_RECORDED_AND_BYTES_VERIFIED", result=score)
    arm = "EXPANDED1137_FIXED907_FRESH256"
    metrics = score["policies"][arm]
    saved = ROOT / "research/temporal-selected-refit-q4-20261010/q4-results"
    old = json.loads((saved / "RESULT.json").read_text())
    assert sha(saved / "RESULT.json") == score["old_result_SHA256"]
    for name, value in old["policies"].items():
        assert score["policies"][name] == value
    native = json.loads((output / "native-handoff/MANIFEST.json").read_text())
    assert (
        sha(ROOT / native["checkpoint_public_path"])
        == native["checkpoint_SHA256"]
        == score["checkpoint_SHA256"]
    )
    assert sha(ROOT / native["current_context_reference"]) == native["current_context_SHA256"]
    for name, entry in native["files"].items():
        path = output / "native-handoff" / name
        assert entry == dict(bytes=path.stat().st_size, SHA256=sha(path))
    with np.load(output / "EXPANDED_PATH.npz", allow_pickle=False) as z:
        nav, q, held, target, request = (
            z[n].copy() for n in ("nav", "quantity", "boundary_held_quantity", "targets", "request")
        )
        decisions = z["decision_us"].copy()
    with np.load(output / "native-handoff/REQUESTS.npz", allow_pickle=False) as z:
        np.testing.assert_array_equal(request, z["desired_expert_budget"])
        np.testing.assert_array_equal(decisions, z["decision_us"])
        assert not np.any(request[~z["action_eligible"]])
        assert np.all(z["feature_available_us"] <= decisions)
    with np.load(saved / "CURRENT_CONTEXT.npz", allow_pickle=False) as z:
        price, coeff = z["prices"].copy(), z["funding_coeff"].copy()
        np.testing.assert_array_equal(decisions, z["decision_us"])
    assert nav.shape == (93,) and q.shape == (92, 5) and nav[0] == 10000
    assert not np.any(q[-1]) and not np.any(held[-1]) and not np.any(target[-1])
    np.testing.assert_allclose(q, 0.99 * nav[:-1, None] * target / price, rtol=1e-13, atol=1e-12)
    carry = np.vstack((np.zeros(5), held[:-1]))
    boundary = np.vstack((price[1:], price[-1]))
    opening, reduction = q - carry, held - q
    fees = (0.00055 * price * (np.abs(opening) + 0.0008 * opening)).sum(1)
    fees += (0.00055 * boundary * (np.abs(reduction) + 0.0008 * reduction)).sum(1)
    spread = (0.0004 * price * np.abs(opening)).sum(1) + (
        0.0004 * boundary * np.abs(reduction)
    ).sum(1)
    funding = np.r_[-(q[:-1] * coeff).sum(1), 0.0]
    price_pnl = (q * (boundary - price)).sum(1)
    expected = nav[:-1] + price_pnl + funding - fees - 2 * spread
    error = float(np.max(np.abs(expected - nav[1:])))
    assert error < 1e-8
    with (output / "DAILY_ACCOUNTING.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 92 and rows[-1]["terminal_paid_flat"] == "True"
    for name, array in dict(
        price_PnL=price_pnl,
        funding_PnL=funding,
        fees=fees,
        spread=spread,
        slippage=spread,
        end_nav=nav[1:],
    ).items():
        np.testing.assert_allclose([float(r[name]) for r in rows], array, rtol=1e-12, atol=1e-10)
    returns = nav[1:] / nav[:-1] - 1
    utility = float(np.sum(np.log(nav[1:] / nav[:-1]) - 5 * np.minimum(returns, 0) ** 2))
    np.testing.assert_allclose(
        [metrics["net_PnL"], metrics["utility_sum"], metrics["fees"], metrics["funding"]],
        [nav[-1] - 10000, utility, fees.sum(), funding.sum()],
        rtol=1e-12,
        atol=1e-10,
    )
    assert score["new_model_scores"] == score["new_daily_wallets"] == 1
    assert score["new_native_wallets"] == 0 and score["model_Adam_all_RNG_unchanged"]
    return dict(
        status="PASS_SAVED_PATH_IDENTITIES_AND_ACCOUNTING",
        rows=92,
        maximum_NAV_residual=error,
        native_requests=92,
        old_comparators_reused=4,
        model_inferences=0,
        wallet_rollouts=0,
        optimizer_updates=0,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.output)
    with (args.output / "VERIFICATION.json").open("x") as stream:
        json.dump(report, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps(report), flush=True)
