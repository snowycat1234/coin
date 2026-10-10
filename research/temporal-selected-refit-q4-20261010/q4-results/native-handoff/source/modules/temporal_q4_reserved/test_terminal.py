import numpy as np
import pytest
import torch

from modules.temporal_risk_proxy_v2.proxy import BoundaryPlan, BoundaryStop, charged_boundary_path

from .terminal import charged_terminal_path


@pytest.mark.parametrize("jump", (1.0, 6.0))
def test_no_padding_paid_terminal_parity_including_gradients(jump):
    targets = np.array(
        [[0.18, 0.08, -0.06, 0, 0], [0.2, 0.04, -0.08, 0, 0], [0, 0, 0, 0, 0]], dtype=np.float64
    )
    prices = np.array(
        [[100, 80, 60, 40, 20], [105, 79, 61, 40, 21], [105 * jump, 78, 60, 41, 22]],
        dtype=np.float64,
    )
    funding = np.array([[0.01, -0.02, 0.03, 0, 0], [0.02, 0, -0.01, 0, 0]], dtype=np.float64)
    plan = BoundaryPlan.full_fill_diagnostic(3)
    a = torch.tensor(targets, requires_grad=True)
    b = torch.tensor(targets, requires_grad=True)
    actual = charged_terminal_path(a, prices, funding, plan=plan)
    original = charged_boundary_path(
        b, np.vstack((prices, prices[-1:])), np.vstack((funding, np.zeros((1, 5)))), plan=plan
    )
    for key in (
        "utility_sum",
        "nav",
        "net_return",
        "quantity",
        "boundary_held_quantity",
        "net_PnL",
        "fees",
        "spread",
        "slippage",
        "funding",
        "charged_reduction_cost",
    ):
        torch.testing.assert_close(actual[key], original[key], rtol=0, atol=0)
    torch.testing.assert_close(
        torch.autograd.grad(actual["utility_sum"], a)[0],
        torch.autograd.grad(original["utility_sum"], b)[0],
        rtol=0,
        atol=0,
    )
    assert actual["risk_events"] == original["risk_events"]
    assert actual["terminal_cash_realized"]
    assert actual["nav"].shape == (4,)
    assert bool(actual["quantity"][-1].eq(0).all())
    if jump > 1:
        assert actual["risk_events"][-1]["day_index"] == 1
    # Arbitrary future ABI values cannot change the original CASH identity;
    # adapter accepts no future row at all.
    other = charged_boundary_path(
        torch.tensor(targets),
        np.vstack((prices, np.full((1, 5), 99999.0))),
        np.vstack((funding, np.full((1, 5), 99.0))),
        plan=plan,
    )
    torch.testing.assert_close(actual["nav"], other["nav"], rtol=0, atol=0)
    with pytest.raises(ValueError, match="Complete original"):
        charged_terminal_path(a, np.vstack((prices, prices[-1:])), funding, plan=plan)


def test_terminal_requires_real_known_economics():
    targets = torch.zeros((2, 5), dtype=torch.float64)
    plan = BoundaryPlan.full_fill_diagnostic(2)
    with pytest.raises(ValueError, match="Complete original"):
        charged_terminal_path(targets, np.ones((2, 5)), np.full((1, 5), np.nan), plan=plan)


def test_unexecutable_boundary_reduction_stops_without_free_exit():
    targets = torch.tensor(
        [[0.25, 0, 0, 0, 0], [0.25, 0, 0, 0, 0], [0, 0, 0, 0, 0]], dtype=torch.float64
    )
    prices = np.ones((3, 5))
    prices[-1, 0] = 10
    funding = np.zeros((2, 5))
    plan = BoundaryPlan(
        np.zeros((3, 5, 5), dtype=np.float64), "DECLARED_COARSE_CAPACITY_DIAGNOSTIC_ONLY"
    )
    with pytest.raises(BoundaryStop, match="UNEXECUTABLE_REQUIRED_REDUCTION_STOP") as actual:
        charged_terminal_path(targets, prices, funding, plan=plan)
    with pytest.raises(BoundaryStop, match="UNEXECUTABLE_REQUIRED_REDUCTION_STOP") as original:
        charged_boundary_path(
            targets,
            np.vstack((prices, prices[-1:])),
            np.vstack((funding, np.zeros((1, 5)))),
            plan=plan,
        )
    assert actual.value.day_index == original.value.day_index == 1
    assert actual.value.equity == original.value.equity
    np.testing.assert_array_equal(actual.value.quantity, original.value.quantity)
    assert actual.value.reduction_cost == original.value.reduction_cost == 0
