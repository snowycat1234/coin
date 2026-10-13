"""Counterexamples for target clocks, symbol order, caps and sign netting."""
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from targets import mix,clock,DAY,SYMBOLS
CAL=('2023-01-01','2024-01-01');D=np.arange(clock(CAL[0]),clock(CAL[1]),DAY,dtype=np.int64);O=np.array(SYMBOLS)
def test_opposite_signed_legs_netted_once_and_not_rebudgeted():
 a=np.tile([.3,.3,0,0,0],(365,1));b=np.tile([-.3,.3,0,0,0],(365,1));w=mix(D,O,a,D,O,b,CAL)
 np.testing.assert_array_equal(w[0],[0,.3,0,0,0]);assert np.abs(w[0]).sum()==.3
def test_clocks_and_order_fail_closed():
 a=np.tile([.1,0,0,0,0],(365,1))
 with pytest.raises(AssertionError):mix(D,O,a,D+DAY,O,a,CAL)
 with pytest.raises(AssertionError):mix(D,O,a,D,O[::-1],a,CAL)
def test_no_rescale_and_invalid_inputs_stop():
 a=np.tile([.01,0,0,0,0],(365,1));w=mix(D,O,a,D,O,a,CAL);assert w[0,0]==.01
 bad=a.copy();bad[-1,0]=float('nan')
 with pytest.raises(AssertionError):mix(D,O,a,D,O,bad,CAL)
