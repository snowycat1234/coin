import importlib.util
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location(
    "read_relevance", Path(__file__).with_name("READ_ECONOMIC_RELEVANCE.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_ties_and_constant_association_are_not_invented():
    a = module.association(np.array([1.0, 1.0, -1.0]), np.array([2.0, 0.0, -1.0]), 1.0)
    assert a["direction_agreement"] == 1 and a["contrast_ties"] == 1
    assert a["prefix_mean_direction_agreement"] == 0.5 and a["prefix_mean_association"] is None
    np.testing.assert_array_equal(module.ranks(np.array([2.0, 1.0, 1.0, 4.0])), [2, 0.5, 0.5, 3])


def test_path_windows_preserve_paid_boundary_no_reset_or_fee_omission():
    nav = 10000 * 1.001 ** np.arange(64)
    nav[-1] = nav[-2] - 5  # Paid terminal row, not a fabricated21st active interval.
    y = module.windows(nav)
    np.testing.assert_allclose(y[0], 1.001**21 - 1)
    assert y[-1] == nav[63] / nav[42] - 1 and y[-1] != 1.001**21 - 1


def test_prefix_endpoint_at_fold_is_not_mature_training_label():
    decisions = np.array([0, module.DAY_US])
    labels = decisions + 21 * module.DAY_US
    assert module.maturity(decisions, labels, labels[-1] + 1)["training_labels"] == 2
    with pytest.raises(ValueError, match="strictly before fold"):
        module.maturity(decisions, labels, labels[-1])
    with pytest.raises(ValueError, match="full21day"):
        module.maturity(decisions, labels - 1, labels[-1] + 1)
