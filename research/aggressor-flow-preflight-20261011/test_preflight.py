import numpy as np
import pytest
from preflight import imbalance


def test_zero_is_unknown_impossible_buy_not_clipped_and_sell_sign():
    x=imbalance([0,100,100,100],[0,100,0,50])
    assert np.isnan(x[0])
    np.testing.assert_array_equal(x[1:],[1,-1,0])
    with pytest.raises(ValueError,match='exceed'):imbalance([100],[101])
    with pytest.raises(ValueError,match='Complete'):imbalance([100],[np.nan])


def test_aggregate_quote_ratio_is_not_mean_of_minute_ratios():
    minute=imbalance([100,900],[100,0])
    aggregate=imbalance([1000],[100])[0]
    assert minute.mean()==0 and aggregate==-.8
