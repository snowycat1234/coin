"""Restricted calendar conditional means, mature training only."""
import numpy as np
DAY=86_400_000_000;FIT=int(np.datetime64('2023-01-01','us').astype('int64'));START=int(np.datetime64('2021-01-01','us').astype('int64'))
def weekday(d):return (np.asarray(d,np.int64)//DAY+3)%7
def fit(d,y,mature):
    d=np.asarray(d,np.int64);y=np.asarray(y,float);mature=np.asarray(mature,np.int64)
    assert y.shape==(len(d),5) and mature.shape==d.shape and np.all(np.diff(d)==DAY)
    valid=(d>=START)&(d<FIT)&(mature<FIT)&np.isfinite(y).all(1);ix=np.flatnonzero(valid);assert len(ix)>=600
    days=weekday(d[ix]);counts=np.bincount(days,minlength=7);assert (counts>=60).all()
    values=y[ix];sigma=values.std(0,ddof=1);assert np.isfinite(sigma).all() and (sigma>0).all()
    means=np.stack([values[days==k].mean(0) for k in range(7)]);constant=values.mean(0)
    return dict(status='FROZEN_CALENDAR_MEANS_MATURE_2021_2022',mean_by_weekday=means.tolist(),constant_mean=constant.tolist(),training_std=sigma.tolist(),train_indices=ix.tolist(),actual_train_dates=d[ix].tolist(),weekday_train_counts=counts.tolist(),maximum_train_maturity_us=int(mature[ix].max()),fit_available_us=FIT,candidate_parameter_count=35,control_parameter_count=5,normalizer_parameter_count=5)
def predict(model,d):
    assert model['maximum_train_maturity_us']<model['fit_available_us']==FIT
    return np.array(model['mean_by_weekday'])[weekday(d)],np.broadcast_to(np.array(model['constant_mean']),(len(d),5)).copy()
def losses(model,d,y):
    a,b=predict(model,d);sigma=np.array(model['training_std']);assert np.isfinite(y).all()
    candidate=((y-a)/sigma)**2;control=((y-b)/sigma)**2
    return candidate,control
