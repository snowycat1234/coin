"""Synthetic numerical tests, original182 reference parity; no fitting."""

import numpy as np
import pytest
import torch

from .proxy import BoundaryPlan, BoundaryStop, charged_boundary_path, require_native_resume_data


def case(branch="gross"):
    if branch == "gross":
        w = np.array([[0.118] * 5, [0.08] * 5, [0.0] * 5])
        p = np.array([[100.0] * 5, [120.0] * 5, [118.0] * 5, [117.0] * 5])
    else:
        w = np.array([[0.295, 0.04, 0.03, 0.02, 0.01], [0.15, 0.05, 0.04, 0.03, 0.02], [0.0] * 5])
        p = np.array(
            [
                [100.0] * 5,
                [130.0, 100.0, 100.0, 100.0, 100.0],
                [125.0, 101.0, 102.0, 99.0, 98.0],
                [124.0, 101.0, 102.0, 99.0, 98.0],
            ]
        )
    f = np.tile([0.011, -0.006, 0.004, -0.001, 0.003], (3, 1))
    return w, p, f


def evaluate(w, p, f, plan=None):
    w = torch.tensor(w, dtype=torch.float64, requires_grad=True)
    report = charged_boundary_path(w, p, f, plan=plan or BoundaryPlan.full_fill_diagnostic(len(w)))
    grad = torch.autograd.grad(report["utility_sum"], w)[0].detach().numpy()
    return report, grad


@pytest.mark.parametrize("branch", ["gross", "asset"])
def test_charged_reduction_vjp_finite_difference(branch):
    w, p, f = case(branch)
    report, grad = evaluate(w, p, f)
    assert report["risk_events"] and float(report["charged_reduction_cost"]) > 0
    for i, j in ((0, 0), (0, 1), (1, 0), (1, 3)):
        plus, minus = w.copy(), w.copy()
        plus[i, j] += 1e-6
        minus[i, j] -= 1e-6
        a, _ = evaluate(plus, p, f)
        b, _ = evaluate(minus, p, f)
        finite = (float(a["utility_sum"].detach()) - float(b["utility_sum"].detach())) / 2e-6
        np.testing.assert_allclose(grad[i, j], finite, rtol=3e-6, atol=3e-9)
        assert len(a["risk_events"]) == len(b["risk_events"]) == len(report["risk_events"])
    np.testing.assert_array_equal(grad[-1], np.zeros(5))
    assert report["terminal_cash_realized"]


def test_partial_fills_charge_only_executed_units_and_keep_frozen_intent():
    w, p, f = case()
    full, _ = evaluate(w, p, f)
    event = full["risk_events"][0]
    need = np.abs(np.array(event["quantity_before"]) - np.array(event["frozen_intent"]))
    capacity = np.full((3, 5, 5), 1e30, dtype=np.float64)
    capacity[0] = 0.0
    capacity[0, :4] = need / 4.0
    report, _ = evaluate(
        w, p, f, BoundaryPlan(capacity, "DECLARED_COARSE_CAPACITY_DIAGNOSTIC_ONLY")
    )
    assert report["risk_events"][0]["attempts"] >= 4
    np.testing.assert_allclose(report["nav"].detach(), full["nav"].detach(), rtol=0, atol=3e-12)
    np.testing.assert_allclose(
        float(report["charged_reduction_cost"]),
        float(full["charged_reduction_cost"]),
        rtol=0,
        atol=1e-12,
    )
    np.testing.assert_allclose(
        report["risk_events"][0]["frozen_intent"], event["frozen_intent"], rtol=0, atol=0
    )


def test_unexecuted_reduction_stops_after_five_without_fabricated_fill():
    w, p, f = case()
    cap = np.zeros((3, 5, 5), np.float64)
    with pytest.raises(BoundaryStop) as caught:
        evaluate(w, p, f, BoundaryPlan(cap, "DECLARED_COARSE_CAPACITY_DIAGNOSTIC_ONLY"))
    assert caught.value.reason == "UNEXECUTABLE_REQUIRED_REDUCTION_STOP"
    assert caught.value.reduction_cost == 0.0
    full, _ = evaluate(w, p, f)
    np.testing.assert_allclose(caught.value.quantity, full["quantity"][0].detach(), rtol=0, atol=0)


def test_partial_expiry_inside_hard_caps_preserves_cost_and_gradient():
    w, p, f = case()
    full, _ = evaluate(w, p, f)
    event = full["risk_events"][0]
    need = np.abs(np.array(event["quantity_before"]) - np.array(event["frozen_intent"]))
    capacity = np.full((3, 5, 5), 1e30, np.float64)
    capacity[0] = need * 0.18  # five fixed partial fills: hard cap met, buffer unfinished
    plan = BoundaryPlan(capacity, "DECLARED_COARSE_CAPACITY_DIAGNOSTIC_ONLY")
    report, gradient = evaluate(w, p, f, plan)
    cut = report["risk_events"][0]
    assert cut["attempts"] == 5 and not cut["unresolved_mark_breach"]
    assert np.any(np.abs(cut["quantity_after"]) > np.abs(cut["frozen_intent"]))
    assert 0 < cut["charged_reduction_cost"] < event["charged_reduction_cost"]
    for i, j in ((0, 0), (0, 2), (1, 1)):
        plus, minus = w.copy(), w.copy()
        plus[i, j] += 1e-6
        minus[i, j] -= 1e-6
        a, _ = evaluate(plus, p, f, plan)
        b, _ = evaluate(minus, p, f, plan)
        fd = (float(a["utility_sum"].detach()) - float(b["utility_sum"].detach())) / 2e-6
        np.testing.assert_allclose(gradient[i, j], fd, rtol=3e-6, atol=3e-9)


def test_funding_before_reduction_and_separate_next_rebalance_cost():
    w, p, f = case()
    report, _ = evaluate(w, p, f)
    quantity = report["quantity"].detach().numpy()
    np.testing.assert_allclose(float(report["funding"]), -np.sum(quantity * f), rtol=0, atol=1e-12)
    event = report["risk_events"][0]
    assert event["equity_before"] - event["equity_after"] == pytest.approx(
        event["charged_reduction_cost"], abs=2e-12
    )
    assert report["fees"] > 0 and report["spread"] > 0 and report["slippage"] > 0
    # No netting away the paid risk reduction against a subsequent target.
    assert not np.array_equal(quantity[1], np.array(event["quantity_after"]))


def test_explicit_boundaries_no_cap_relaxation_or_implicit_execution():
    w, p, f = case()
    for bad in ("target", "terminal", "negative_capacity"):
        q = w.copy()
        if bad == "target":
            q[0, 0] = 0.30000001
        if bad == "terminal":
            q[-1, 0] = 0.01
        with pytest.raises(ValueError):
            if bad == "negative_capacity":
                BoundaryPlan(
                    np.full((3, 5, 5), -1.0, np.float64), "DECLARED_COARSE_CAPACITY_DIAGNOSTIC_ONLY"
                )
            else:
                evaluate(q, p, f)
    with pytest.raises(ValueError, match="explicit boundary"):
        charged_boundary_path(torch.tensor(w, dtype=torch.float64), p, f, plan=None)
    with pytest.raises(ValueError, match="NATIVE_RESUME_NOT_READY"):
        require_native_resume_data(dict(prices=p, funding_coeff=f))


def test_exact_182_reference_parity_without_reductions(prototype, recovery):
    count = 0
    for name in ("H1_TRAIN", "BEAR2022NOV", "RECOVERY2023JAN"):
        with np.load(recovery / "direct_path_fragments" / (name + ".npz"), allow_pickle=False) as z:
            a = {k: z[k].copy() for k in z.files}
        contexts = tuple(
            prototype.Context(
                int(d),
                int(d),
                a["expert_targets"][i],
                a["expert_eligible"][i],
                a["past_returns30"][i],
                a["market_state13"][i],
                a["target_available_us"][i],
            )
            for i, d in enumerate(a["decision_us"])
        )
        request = np.tile([0.0, 0.5, 0.0, 0.0, 0.5], (len(contexts), 1))
        targets, records = prototype.mapped_path(request, contexts)
        original = prototype.daily_proxy(targets, a["prices"], a["funding_coeff"])
        report, grad = evaluate(targets, a["prices"], a["funding_coeff"])
        assert not report["risk_events"]
        np.testing.assert_allclose(report["nav"].detach(), original["nav"], rtol=0, atol=1e-9)
        np.testing.assert_allclose(
            float(report["utility_sum"].detach()), original["utility_sum"], rtol=0, atol=2e-14
        )
        np.testing.assert_allclose(grad, original["target_gradient"], rtol=5e-11, atol=5e-13)
        old = prototype.mapping_vjp(original["target_gradient"], records, contexts)
        new = prototype.mapping_vjp(grad, records, contexts)
        np.testing.assert_allclose(new, old, rtol=5e-11, atol=5e-13)
        count += len(contexts)
    assert count == 182
