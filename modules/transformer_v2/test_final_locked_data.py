import numpy as np
import pandas as pd
from .final_fit import final_indices
from .locked_data import actual_funding_coverage

def test_final_fit_excludes_immature_labels_and_unobserved_assets():
    dates=pd.date_range('2022-01-01','2026-02-28',tz='UTC');n=len(dates)
    d=dict(symbols=['A','B'],ready=np.ones((n,2),bool),availability=np.ones((n,2),bool),
           utility=[np.ones((n,2,2))],label_end=dates+pd.Timedelta(days=61))
    d['availability'][:,1]=False;d['ready'][:,1]=False
    indices,active,cutoff=final_indices(d,0)
    assert active.tolist()==[True,False] and indices.min()==255
    assert (d['label_end'][indices]<cutoff).all() and dates[indices].max()<pd.Timestamp('2026-01-01',tz='UTC')

def test_actual_funding_boundary_needs_no_future_september_event():
    stamps=pd.date_range('2026-02-28','2026-08-31 16:00:00',freq='8h',tz='UTC')
    events=pd.DataFrame(dict(calc_time_ms=stamps.as_unit('ms').asi8,funding_interval_hours=8.))
    assert actual_funding_coverage(events)
    assert not actual_funding_coverage(events.iloc[:-1])
    assert not actual_funding_coverage(events.drop(index=100))
    assert not actual_funding_coverage(events.iloc[:0])
