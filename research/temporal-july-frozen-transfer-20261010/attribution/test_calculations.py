import importlib.util
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location("attribution", Path(__file__).with_name("CALCULATE.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_carried_short_units_and_current_change_are_additive():
    price = np.array([[10.], [8.], [6.], [6.]])
    quantity = np.array([[-2.], [-3.], [0.]])
    inherited, changed = module.carry_split(quantity, price)
    np.testing.assert_array_equal(inherited, [0., 4., 0.])
    np.testing.assert_array_equal(changed, [4., 2., 0.])
    np.testing.assert_array_equal(inherited + changed, [4., 6., 0.])


def test_concentration_counts_positive_mass_without_deleting_rows():
    values = np.array([20., -30., 10., 5., -2., 1.])
    result = module.concentration(values)
    assert result["positive_mass"] == 36 and result["negative_mass"] == -32
    assert result["largest3_contribution_sum"] == 35
    assert result["positive_intervals"] == 4 and len(values) == 6
    assert not any("without" in k or "omit" in k for k in result)
