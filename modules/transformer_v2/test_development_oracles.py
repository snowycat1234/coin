import numpy as np
from .development_oracles import same_executed_targets

def test_reuse_compares_only_exact_executed_window_and_paid_close():
    dates=np.arange(4);old=np.ones((4,2));new=old.copy();window=dict(start=1,end=3,days=2)
    new[0]=7;new[2]=8;new[3]=9
    assert same_executed_targets(dates,old,new,window)
    new[1,0]=.9
    assert not same_executed_targets(dates,old,new,window)
