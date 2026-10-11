"""Attribution conservation and exact cost gradients; no models/optimizers."""
import numpy as np
import pytest
import torch

from .cost_feasibility import FEE, SPREAD, SLIP, arithmetic
from .objective_diagnostic import tensor_cost_returns, turnover_attribution


def test_constant_position_vol_change_attributed_to_scale():
    out = turnover_attribution([[.1], [.1]], [[.02], [.04]], [[True], [True]], [[0], [0]])
    assert out["components"]["signal"]["absolute_component"] == 0
    assert out["components"]["vol_scaling"]["absolute_component"] > 0
    assert out["categories"]["SIGN_REVERSAL"]["events"] == 0


def test_signal_flip_fixed_vol_and_drift_exact_components():
    out = turnover_attribution([[.1], [-.1]], [[.02], [.02]], [[True], [True]], [[.1], [0]])
    assert out["categories"]["SIGN_REVERSAL"]["events"] == 1
    assert out["components"]["vol_scaling"]["absolute_component"] == 0
    assert out["components"]["price_drift"]["absolute_component"] > 0
    assert sum(c["signed_trade_projection"] for c in out["components"].values()) == pytest.approx(out["financial"]["drift_trade_turnover"])


def test_unavailable_exit_retains_drift_and_cash_nan():
    out = turnover_attribution([[.1], [0]], [[.02], [np.nan]], [[True], [False]], [[.1], [np.nan]])
    assert out["categories"]["ELIGIBILITY_EXIT"]["fixed_cost"] > 0
    assert out["categories"]["TERMINAL_EXIT"]["fixed_cost"] == 0


def test_exact_tensor_cost_value_and_finite_difference_gradient():
    raw = np.array([[.1, -.04], [-.08, .06], [.03, .01]])
    r = np.array([[.1, -.2], [-.03, .02], [.04, -.01]])
    w = torch.tensor(raw, dtype=torch.float64, requires_grad=True)
    net, _ = tensor_cost_returns(w, torch.tensor(r), torch.ones_like(w, dtype=torch.bool))
    expected, _ = arithmetic(raw, r)
    assert float(net.sum().detach()) == pytest.approx(expected["fixed_cost_adjusted_price_proxy"], abs=1e-14)
    net.sum().backward()
    for index in np.ndindex(raw.shape):
        plus, minus = raw.copy(), raw.copy()
        plus[index] += 1e-6
        minus[index] -= 1e-6
        fplus = arithmetic(plus, r)[0]["fixed_cost_adjusted_price_proxy"]
        fminus = arithmetic(minus, r)[0]["fixed_cost_adjusted_price_proxy"]
        assert w.grad[index].item() == pytest.approx((fplus - fminus) / 2e-6, abs=1e-10)


def test_masked_tensor_exit_has_zero_current_target_gradient():
    w = torch.tensor([[.1], [.5]], dtype=torch.float64, requires_grad=True)
    mask = torch.tensor([[True], [False]])
    net, _ = tensor_cost_returns(w, torch.tensor([[.1], [np.nan]], dtype=torch.float64), mask)
    assert torch.isfinite(net).all()
    net.sum().backward()
    assert w.grad[1, 0] == 0


def test_eligible_missing_outcome_invalid_even_zero_target():
    with pytest.raises(ValueError, match="outcomes"):
        tensor_cost_returns(torch.tensor([[0.]]), torch.tensor([[np.nan]]), torch.tensor([[True]]))


def test_cost_kink_declared_subgradient_and_positive_homogeneity():
    w = torch.tensor([[0.]], dtype=torch.float64, requires_grad=True)
    net, _ = tensor_cost_returns(w, torch.tensor([[.1]], dtype=torch.float64), torch.tensor([[True]]))
    net.sum().backward()
    expected = .1 * (1 + FEE * (SPREAD + SLIP))  # abs(0) selects valid subgradient0
    assert w.grad.item() == pytest.approx(expected)
    raw, r = np.array([[.1], [-.08]]), np.array([[.1], [-.03]])
    a, _ = arithmetic(raw, r)
    b, _ = arithmetic(raw * 2, r)
    assert b["fixed_cost_adjusted_price_proxy"] == pytest.approx(2 * a["fixed_cost_adjusted_price_proxy"])
    assert b["break_even_nominal_per_side_bps"] == pytest.approx(a["break_even_nominal_per_side_bps"])
