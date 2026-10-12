import numpy as np
from core import DAY,FIT,START,weekday,fit,predict,losses
def fixture():
    d=START+np.arange(760,dtype=np.int64)*DAY;y=np.sin(np.arange(760)[:,None]*.41+np.arange(5))*.02+weekday(d)[:,None]*.001
    return d,y,d+2*DAY
def test_execution_weekday_not_previous_completed_day():
    d=np.array([np.datetime64('2023-01-01','us').astype('int64'),np.datetime64('2023-01-02','us').astype('int64')]);np.testing.assert_array_equal(weekday(d),[6,0]);assert weekday(d-DAY)[1]==6
def test_strict_maturity_purge_and_train_only_normalizer():
    d,y,m=fixture();model=fit(d,y,m);ix=np.array(model['train_indices']);assert d[ix[-1]]==int(np.datetime64('2022-12-29','us').astype('int64')) and m[ix].max()<FIT
    np.testing.assert_array_equal(model['training_std'],y[ix].std(0,ddof=1));assert len(ix)==728
def test_future_labels_nan_cannot_refit_calendar_coefficients():
    d,y,m=fixture();base=fit(d,y,m);y[d>=FIT]=1e9;assert fit(d,y,m)==base;y[d>=FIT]=np.nan;assert fit(d,y,m)==base
def test_unknown_training_date_not_zero_and_equal_support_control():
    d,y,m=fixture();y[40,2]=np.nan;model=fit(d,y,m);assert 40 not in model['train_indices'] and len(model['train_indices'])==727
    evald=d[d>=FIT];a,b=predict(model,evald);x=np.zeros_like(a);la,lb=losses(model,evald,x);assert a.shape==b.shape==la.shape==lb.shape==(30,5)
