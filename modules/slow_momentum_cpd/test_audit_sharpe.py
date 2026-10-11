"""Regression for the post-fit audit receipt failure; no model training."""

import json

import numpy as np

from .audit_sharpe import receipt_gates


def test_numpy_gate_comparisons_serialize_and_preserve_frozen_thresholds():
    gates = receipt_gates(
        np.array([0.073, 0.268, 0.394]),
        np.array([0.086, 0.677, -0.027]),
        np.float64(0.285),
        np.array([-0.181, 0.803]),
    )
    assert all(type(value) is bool for value in gates.values())
    assert json.loads(json.dumps(gates, allow_nan=False)) == {
        "positive_in_at_least_two_blocks": True,
        "positive_in_at_least_two_seeds": True,
        "aggregate_ensemble_increment_positive": True,
        "bootstrap_lower_positive": False,
    }
    assert receipt_gates([0, 1, -1], [0, 1, -1], 0, None) == dict.fromkeys(gates, False)
