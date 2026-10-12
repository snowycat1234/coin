import importlib.util
from pathlib import Path
import numpy as np
import pytest
from scripts.research.conditional_selector_core import nonoverlap_indices,DAY_US

spec=importlib.util.spec_from_file_location('owned_dates',Path(__file__).with_name('dates.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def clock_set(n=610,horizon=1):
    d=1_600_000_000_000_000+np.arange(n,dtype=np.int64)*DAY_US
    return d,d+60_000_001,d+horizon*DAY_US+60_000_001,d+horizon*DAY_US+8*3_600_000_000


def test_daily_true_owned_intervals_touch_without_overlap_maturity_is_not_backdated():
    d,s,e,a=clock_set();ok=np.ones(len(d),bool);cutoff=int(a[-1]+1)
    full=m.owned_indices(d,s,e,a,ok,cutoff);old=nonoverlap_indices(d,a,ok)
    assert len(full)==610 and len(old)==305 and np.array_equal(a,d+DAY_US+8*3_600_000_000)
    assert np.all(s[full[1:]]>=e[full[:-1]])


def test_funding_event_at_touching_boundary_is_charged_only_to_ending_interval():
    d,s,e,a=clock_set(2);events=np.array([s[0],e[0],e[1]],np.int64)
    first=m.interval_events(events,s[0],e[0]);second=m.interval_events(events,s[1],e[1])
    assert first.tolist()==[1] and second.tolist()==[2] and not set(first)&set(second)


def test_seven_day_holding_cannot_be_shortened_or_called610_disjoint():
    d,s,e,a=clock_set(horizon=7);ix=m.owned_indices(d,s,e,a,np.ones(len(d),bool),int(a[-1]+1))
    assert len(ix)<100 and np.all(s[ix[1:]]>=e[ix[:-1]])


def test_reward_coverage_after_cutoff_is_not_hidden_by_earlier_ownedend():
    d,s,e,a=clock_set(2);cutoff=int(e[-1]+1)
    with pytest.raises(ValueError,match='mature beforecutoff'):m.owned_indices(d,s,e,a,np.ones(2,bool),cutoff)
    duplicate=d.copy();duplicate[1]=duplicate[0]
    with pytest.raises(ValueError,match='Exactunique'):m.owned_indices(duplicate,s,e,a,np.ones(2,bool),int(a[-1]+1))
