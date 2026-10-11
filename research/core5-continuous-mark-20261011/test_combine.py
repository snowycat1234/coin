import numpy as np
import pytest
from combine_mark import validate_masks


def fixture():
    missing=np.zeros((3,5),dtype=np.int64);missing[1,1]=1
    valid=missing==0;valid[0]=False
    full={'available_us':np.arange(3),'observed_minutes':1440-missing,
          'close':np.ones((3,5)),'high':np.where(missing==0,2.,np.nan),'low':np.where(missing==0,.5,np.nan)}
    for k in ('RV_1m','RV_5m','RSplus_1m','RSminus_1m','RSplus_5m','RSminus_5m','max_log_up','max_log_down'):
        full[k]=np.where(valid,.1,np.nan)
    return full,missing,valid


def test_sparse_source_mask_and_true_prior_close():
    full,missing,valid=fixture()
    np.testing.assert_array_equal(validate_masks(full,missing),valid)
    full['close'][1,1]=np.nan
    with pytest.raises(AssertionError):validate_masks(full,missing)


def test_filled_path_statistic_is_rejected():
    full,missing,_=fixture();full['RV_1m'][1,1]=0.
    with pytest.raises(AssertionError):validate_masks(full,missing)
