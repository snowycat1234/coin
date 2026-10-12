import numpy as np
import pytest
from core import DAY,persistence,fit,predict,ranks,paired_gain

def test_prefix_future_price_changes_leave_past_features_exact_and_ties_identity():
 t=np.arange(80,dtype=np.int64)*DAY;p=np.exp(np.arange(80)[:,None]*np.linspace(.001,.005,5))
 original=persistence(t,p,t[28:]);p[t>50*DAY]*=np.linspace(2,8,5)
 changed=persistence(t,p,t[28:]);np.testing.assert_array_equal(original[:23],changed[:23]);np.testing.assert_array_equal(ranks([3,1,1,2,4]),[3,.5,.5,2,4])
 assert np.all(persistence(t,np.ones((80,5)),t[28:])==0)
 with pytest.raises(ValueError,match='clocks'):persistence(t[::2],p[::2],t[28:])

def test_maturity_purge_and_future_label_tampering_never_change_training_fit():
 d=np.arange(220,dtype=np.int64)*DAY;x=np.tile([-.5,.5],110);y=np.where(x>0,.002,-.001);m=d+DAY+60000001
 model,owned=fit(d,x,y,m,151*DAY,0);assert not owned[150] and model['maximum_maturity_us']<151*DAY
 y[~owned]=999;other,_=fit(d,x,y,m,151*DAY,0);assert model==other
 forecast,const=predict(model,x);assert forecast[0]==pytest.approx(-.001) and forecast[1]==pytest.approx(.002) and np.all(const==model['constant'])

def test_natural_calendar_block_resampling_keeps_missing_dates_and_negative_gain():
 gain=np.full(181,-.1);known=np.ones(181,bool);known[10:30]=False;gain[~known]=np.nan
 assert paired_gain(gain,known)==pytest.approx([-.1,-.1])
 with pytest.raises(ValueError,match='Insufficient'):paired_gain(gain,known&False)
