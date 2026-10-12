import importlib.util
from pathlib import Path
import numpy as np
import pytest
spec=importlib.util.spec_from_file_location('attr',Path(__file__).with_name('core.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_funnel_assigns_each_opportunity_once_and_preserves_target_unknown():
    flags=np.ones((6,7),bool)
    for i in range(6):flags[i,i]=False
    result=m.partition(*flags)
    assert len(set(result))==7 and result[-1]=='NEGATIVE_TARGET_PRESENT_NATIVE_FILL_UNKNOWN'

def test_calendar_gap_does_not_create_an_independent_run_or_adjacency():
    d=np.array([1,2,4,5])*86400000000
    r=m.runs(d,np.ones(4,bool));assert [x['dates'] for x in r]==[2,2]
    with pytest.raises(ValueError):m.runs(np.array([1,1]),np.ones(2,bool))

def test_allocation_probability_bins_cover_boundaries_without_double_count():
    b=np.array([0,.2,.4,.6,.8,1.]);r=m.reliability(b,np.ones(6,bool),np.ones(6,bool))
    assert sum(x['dates'] for x in r)==6 and r[-1]['dates']==2
