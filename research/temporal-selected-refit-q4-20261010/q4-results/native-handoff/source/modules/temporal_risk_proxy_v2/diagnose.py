"""Read-only original-stop reproduction and charged-surrogate numerical receipt."""

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.training_packet import load_packet

from .native_contract import NATIVE_SHA256
from .proxy import CONTRACT, BoundaryPlan, charged_path_loss, request_loss_and_gradient_v2


def diagnostic(state):
    stop = json.loads((state / "EXPOSURE_STOP_WITNESS.json").read_text())
    train, _, prototype, identity = load_packet(
        state / "FROZEN_PACKET.json",
        sha(state / "FROZEN_PACKET.json"),
        state / "recovery/source/modules/direct_path/prototype.py",
    )
    episode = next(e for e in train if e.wallet_id == stop["wallet_id"])
    with np.load(state / "EXPOSURE_STOP_REQUESTS.npz", allow_pickle=False) as z:
        requests, saved_targets = z["requests"].copy(), z["net_targets"].copy()
    targets, _ = prototype.mapped_path(requests, episode.contexts)
    np.testing.assert_array_equal(targets, saved_targets)
    try:
        prototype.daily_proxy(targets, episode.prices, episode.funding_coeff)
    except prototype.ProxyExposureBreach as error:
        assert error.day_index == stop["day_index"]
        original_equity = error.equity
        original_exposure = error.exposure
    else:
        raise AssertionError("The saved original stochastic witness must still stop")
    plan = BoundaryPlan.full_fill_diagnostic(len(requests))
    loss, grad, report = request_loss_and_gradient_v2(requests, episode, prototype, plan=plan)
    neural_requests = torch.tensor(requests, dtype=torch.float64, requires_grad=True)
    neural_loss = charged_path_loss(neural_requests, episode, prototype, plan=plan)
    neural_grad = torch.autograd.grad(neural_loss, neural_requests)[0].detach().numpy()
    np.testing.assert_array_equal(neural_grad, grad)
    assert float(neural_loss.detach()) == loss
    event = report["risk_events"][0]
    assert event["day_index"] == stop["day_index"]
    np.testing.assert_allclose(event["equity_before"], original_equity, rtol=0, atol=2e-9)
    quantity = np.array(event["quantity_before"])
    price = episode.prices[stop["day_index"] + 1]
    np.testing.assert_allclose(np.abs(quantity) * price, original_exposure, rtol=0, atol=3e-10)
    after_gross = np.sum(np.abs(event["quantity_after"]) * price) / event["equity_after"]
    after_asset = np.max(np.abs(event["quantity_after"]) * price) / event["equity_after"]
    assert event["charged_reduction_cost"] > 0 and after_gross <= 0.6 and after_asset <= 0.3
    checks = []
    for day in (47, 49, 50):
        plus, minus = requests.copy(), requests.copy()
        eps = 1e-6
        plus[day, 1] += eps
        plus[day, 4] -= eps
        minus[day, 1] -= eps
        minus[day, 4] += eps
        a, _, ra = request_loss_and_gradient_v2(plus, episode, prototype, plan=plan)
        b, _, rb = request_loss_and_gradient_v2(minus, episode, prototype, plan=plan)
        fd, vjp = (a - b) / (2 * eps), float(grad[day, 1] - grad[day, 4])
        assert (
            [e["day_index"] for e in ra["risk_events"]]
            == [e["day_index"] for e in rb["risk_events"]]
            == [e["day_index"] for e in report["risk_events"]]
        )
        np.testing.assert_allclose(vjp, fd, rtol=2e-5, atol=2e-10)
        checks.append(
            dict(
                day_index=day,
                direction="VOL+eps_CS-eps",
                epsilon=eps,
                finite_difference=fd,
                request_vjp=vjp,
                absolute_error=abs(vjp - fd),
            )
        )
    with np.load(state / "economic-contexts/CONTEXTS.npz", allow_pickle=False) as z:
        fields = sorted(z.files)
    sources = sorted(
        str(p.relative_to(state))
        for p in (state / "feature-input/verified/source_tables_not_model_inputs/economics").glob(
            "*.parquet"
        )
    )
    return dict(
        schema="CHARGED_BOUNDARY_PROXY_NUMERICAL_RECEIPT_V1",
        status="PASS_DIAGNOSTIC_SURROGATE_NATIVE_RESUME_BLOCKED",
        contract=CONTRACT,
        native_scheduler_SHA256=NATIVE_SHA256,
        source_identity=identity["identity_SHA256"],
        witness_model_identity=stop["model_identity"],
        original_requests_SHA256=sha(state / "EXPOSURE_STOP_REQUESTS.npz"),
        plan_identity=plan.identity,
        capacity_declaration=plan.declaration,
        original_stop_reproduced=True,
        original_stop_day=stop["day_index"],
        original_marked_gross=stop["gross_fraction"],
        original_stop_equity=original_equity,
        first_charged_reduction=event,
        after_reduction_gross=after_gross,
        after_reduction_max_asset=after_asset,
        complete_surrogate_wallet_days=len(requests),
        forced_paid_terminal_cash=report["terminal_cash_realized"],
        surrogate_metrics={
            k: float(report[k].detach())
            for k in ("net_PnL", "fees", "spread", "slippage", "funding", "charged_reduction_cost")
        },
        surrogate_mean_loss=loss,
        request_gradient_checks=checks,
        original_runs_and_checkpoints_unchanged=True,
        optimizer_updates=0,
        historical_native_wallets=0,
        synthetic_native_contract_tests_only=True,
        daily_packet_fields=fields,
        available_existing_economic_tables=sources,
        missing_native_inputs=[
            "minute trade opens/midpoints",
            "minute marks",
            "preceding-minute quote volumes",
        ],
        existing_funding_event_tables_available=True,
        native_profile_scope=(
            "The existing declared quantity steps, filters and .005 research MMR can "
            "remain source-bound; historical exchange certification is not an added resume gate."
        ),
        native_resume_ready=False,
        neural_request_bridge_exact=True,
        resume_assessment=(
            "Saved Adam moments and RNG can warm-start a versioned corrected objective; "
            "this would be a resumed experiment, not the clean original comparison. "
            "The continuous diagnostic proxy is differentiated exactly, but is not a "
            "minute-native correction. No resumed optimizer step is authorized by the "
            "native-exact feasibility condition with the present packet."
        ),
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    receipt = diagnostic(args.state)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                k: receipt[k]
                for k in (
                    "status",
                    "original_marked_gross",
                    "after_reduction_gross",
                    "optimizer_updates",
                    "native_resume_ready",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
