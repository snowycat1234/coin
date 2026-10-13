"""Exact mature recipe and causal directions; synthetic only before freeze."""
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from targets import weights
from native_apis import DAY,SYMBOLS
def fixture():
 t=1609459200000000+np.arange(250)*DAY;x=np.arange(250);p=np.column_stack([100+.01*x,100-.01*x,np.full(250,100.),100+.002*x,100-.002*x]);return t,p
def test_exact_up_down_flat_and_no_lowrisk_upscaling():
 t,p=fixture();d=t[199:];w,signal,mean,ids=weights(t,p,d);np.testing.assert_array_equal(signal,np.tile([1,-1,0,1,-1],(len(d),1)));np.testing.assert_allclose(w,signal*.12,rtol=0,atol=0);assert np.abs(w).sum(1).max()==.48;assert np.isfinite(mean).all()
def test_future_changes_do_not_change_past_and_unknown_warmup_rejected():
 t,p=fixture();d=t[199:220];a,*_=weights(t,p,d);alt=p.copy();alt[220:]=np.nan;b,*_=weights(t,alt,d);np.testing.assert_array_equal(a,b);alt=p.copy();alt[220:]*=1000;b,*_=weights(t,alt,d);np.testing.assert_array_equal(a,b)
 with pytest.raises(AssertionError):weights(t,p,t[198:199])
 alt=p.copy();alt[50,0]=np.nan
 with pytest.raises(AssertionError):weights(t,alt,t[199:200])
def test_high_covariance_only_reduces_raw_and_caps_hold():
 t,_=fixture();x=np.arange(250);p=np.tile((100*np.exp(.30*np.sin(.5*x)+.001*x))[:,None],(1,5));w,s,*_=weights(t,p,t[199:]);assert np.all(np.abs(w)<=np.abs(s)*.12+1e-15) and np.any(np.abs(w)<np.abs(s)*.12-1e-6);assert np.abs(w).max()<=.3 and np.abs(w).sum(1).max()<=.6
