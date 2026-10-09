"""Economic witnesses for charged reductions and signed boundary funding."""
import importlib.util
from pathlib import Path
import numpy as np
import pytest

path=Path(__file__).resolve().parents[1]/'research/recover-frozen-runner-20261009/v2_same_path_diagnostic.py'
spec=importlib.util.spec_from_file_location('v2_same_path_diagnostic',path)
v2=importlib.util.module_from_spec(spec);spec.loader.exec_module(v2)


def test_required_reduction_is_charged_before_separate_terminal_close():
    w=np.array([[.3,.3,0,0,0],[0,0,0,0,0]],dtype=np.float64)
    p=np.array([[100]*5,[200]*5,[200]*5],dtype=np.float64)
    f=np.zeros((2,5))
    r=v2.boundary_reference(w,p,f)
    assert len(r['risk_events'])==1 and r['risk_events'][0]['day_index']==0
    assert r['charged_reduction_cost']>0 and (r['held'][0][:2]<r['quantities'][0][:2]).all()
    assert (r['held'][-1]==0).all() and r['nav'][2]<r['nav'][1]
    assert v2.decimal_check(w,p,f,r)['status'].startswith('PASS_')
    # Rising held units must trigger a paid reduction even when tomorrow is cash.
    assert r['risk_events'][0]['attempts']==1


def test_signed_funding_and_adverse_fill_fees():
    w=np.array([[.1,-.1,0,0,0],[0,0,0,0,0]],dtype=np.float64)
    p=np.full((3,5),100.,dtype=np.float64)
    f=np.array([[1.,2.,0,0,0],[0,0,0,0,0]],dtype=np.float64)
    r=v2.boundary_reference(w,p,f)
    assert r['funding']==pytest.approx(9.9)
    assert not r['risk_events']
    assert r['fees']==pytest.approx(2*.00055*1980)
    assert r['nav'][-1]-10000==pytest.approx(9.9-2*.00135*1980)
    v2.decimal_check(w,p,f,r)


def test_hard_post_fill_breach_stops():
    w=np.array([[.31,0,0,0,0],[0,0,0,0,0]],dtype=np.float64)
    with pytest.raises(ValueError,match='post-fill hard stop'):
        v2.boundary_reference(w,np.full((3,5),100.),np.zeros((2,5)))


def test_flat_path_has_no_fabricated_paid_activity():
    w=np.zeros((2,5));p=np.full((3,5),100.);f=np.full((2,5),1.)
    r=v2.boundary_reference(w,p,f)
    assert np.array_equal(r['nav'],np.full(3,10000.))
    assert r['fees']==r['spread']==r['slippage']==r['funding']==0
    v2.decimal_check(w,p,f,r)
