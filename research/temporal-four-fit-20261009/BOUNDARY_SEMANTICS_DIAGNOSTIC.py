"""Read-only classification tests on the existing stop; no wallets or fitting."""

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.training_packet import load_packet
from quant.perpetual_account import HALTS, ZERO, D, USDTLinearPerpetualAccount


def native_classification(quantities, entry_prices, marked_prices, equity):
    """Invoke unchanged native risk method on a frame, not an executed account."""
    names = tuple(str(i) for i in range(len(quantities)))
    positions = {
        name: SimpleNamespace(
            quantity=D(str(q)), entry_price=D(str(p)), isolated_balance=abs(D(str(q))) * D(str(p))
        )
        for name, q, p in zip(names, quantities, entry_prices, strict=True)
    }
    marks = dict(zip(names, map(lambda p: D(str(p)), marked_prices), strict=True))
    frame = SimpleNamespace(
        status="ACTIVE",
        positions=positions,
        unpaid_liability=ZERO,
        clock_us=0,
        config=SimpleNamespace(
            maintenance_margin_rate=D(".005"), max_asset_weight=D(".3"), max_gross_weight=D(".6")
        ),
        nav=lambda: D(str(equity)),
        _mark=marks.__getitem__,
    )
    USDTLinearPerpetualAccount._risk(frame, "READ_ONLY_WITNESS_CLASSIFICATION")
    return frame.status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    state = args.state
    stop = json.loads((state / "EXPOSURE_STOP_WITNESS.json").read_text())
    train, _, prototype, _ = load_packet(
        state / "FROZEN_PACKET.json",
        sha(state / "FROZEN_PACKET.json"),
        state / "recovery/source/modules/direct_path/prototype.py",
    )
    episode = next(e for e in train if e.wallet_id == stop["wallet_id"])
    day = stop["day_index"]
    with np.load(state / "EXPOSURE_STOP_REQUESTS.npz", allow_pickle=False) as z:
        target = z["net_targets"][day]
    start, end = episode.prices[day : day + 2]
    exposures = np.array(stop["exposure"])
    quantity = np.sign(target) * exposures / end
    before_values = quantity * start / (0.99 * target)
    assert np.max(before_values) - np.min(before_values) < 1e-8
    before_equity = float(np.mean(before_values))
    gross_return = float(quantity @ (end - start))
    funding = -float(quantity @ episode.funding_coeff[day])
    after_fill_equity = stop["equity"] - gross_return - funding
    filled = np.abs(quantity) * start / after_fill_equity
    marked = exposures / stop["equity"]
    assert stop["boundary_index"] == day + 1
    assert np.abs(target).sum() <= 0.6 and np.abs(target).max() <= 0.3
    assert stop["allocated_leg_gross"] <= 0.6 and max(stop["allocated_asset_gross"]) <= 0.3
    assert filled.sum() <= 0.6 and filled.max() <= 0.3
    assert marked.sum() > 0.6 and marked.max() <= 0.3
    status = native_classification(quantity, start, end, stop["equity"])
    assert status == "BOUND_BREACH_REDUCTION_REQUIRED" and status not in HALTS
    assert native_classification(quantity, start, start, after_fill_equity) == "ACTIVE"
    # Original hard target check remains mandatory; no economic code is changed.
    invalid = np.zeros((2, 5))
    invalid[0, 0] = 0.6001
    try:
        prototype.daily_proxy(invalid, np.ones((3, 5)) * 100.0, np.zeros((2, 5)))
    except ValueError as error:
        assert str(error) == "Target caps exceeded"
    else:
        raise AssertionError("Hard target caps must still reject")
    scale = min(1.0, 0.99 * 0.3 / marked.max(), 0.99 * 0.6 / marked.sum())
    root = Path(__file__).resolve().parents[2]
    sources = [
        "src/quant/perpetual_account.py",
        "src/quant/bybit_isolated_account.py",
        "scripts/investment/resumable_perpetual.py",
        "scripts/investment/perpetual_directional.py",
    ]
    receipt = dict(
        schema="PROXY_NATIVE_BOUNDARY_SEMANTICS_DIAGNOSTIC_V1",
        status="PASS_MARK_DRIFT_NOT_REQUESTED_OR_FILLED_TARGET_CAP_BREACH",
        witness_model_identity=stop["model_identity"],
        decision_us=stop["decision_us"],
        requested_net_target_gross=float(np.abs(target).sum()),
        allocated_leg_gross=stop["allocated_leg_gross"],
        post_fill_gross=float(filled.sum()),
        post_fill_max_asset=float(filled.max()),
        marked_gross=float(marked.sum()),
        marked_max_asset=float(marked.max()),
        inferred_before_fill_equity=before_equity,
        after_fill_equity=after_fill_equity,
        implied_paid_trade_cost=before_equity - after_fill_equity,
        unchanged_native_risk_status=status,
        immediate_native_halt=False,
        native_required_quantity_reduction_scale=scale,
        native_source_SHA256={name: sha(root / name) for name in sources},
        tests_passed=[
            "requested_and_allocated_target_caps_hold",
            "filled_opening_caps_hold",
            "exact_native_risk_method_classifies_drift_as_reduction_required_not_halt",
            "same_position_without_mark_drift_active",
            "original_hard_target_violation_still_rejected",
        ],
        proposal=(
            "Replace following-mark immediate proxy exception with explicit REDUCTION_REQUIRED "
            "state; keep pre-net target and opening caps. Implement charged mandatory "
            "reductions and their exact VJP before a revised economic fit."
        ),
        correction_integrated=False,
        correction_economic_gradients_tested=False,
        additional_fits=0,
        native_wallets=0,
        original_runs_and_math_unchanged=True,
        limits=(
            "Risk-method frame tests only; no native execution/funding/liquidation certification "
            "or risk-order PnL is claimed. Simply suppressing the exception would not implement "
            "native required reductions."
        ),
    )
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                k: receipt[k]
                for k in (
                    "status",
                    "requested_net_target_gross",
                    "post_fill_gross",
                    "marked_gross",
                    "unchanged_native_risk_status",
                    "native_required_quantity_reduction_scale",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
