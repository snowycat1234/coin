import importlib.util
from pathlib import Path
import numpy as np
spec=importlib.util.spec_from_file_location('cal',Path(__file__).with_name('calibration_core.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_reward_completeness_must_mature_before_fit_and_validation_end():
    d=np.array([1,2,3,4]);a=np.array([2,4,4,6]);tr,va=m.split(d,a,np.ones(4,bool),4,6)
    assert tr.tolist()==[True,False,False,False] and va.tolist()==[False]*4

def test_negative_target_is_not_misclassified_as_rank_omission():
    a=np.ones((6,2),bool);a[2]=False;a[5,1]=False
    out=m.omission(*a);assert out[0]=='NEGATIVE_TARGET_PRESENT_NATIVE_FILL_UNKNOWN' and out[1]=='RANK_NOT_BEST_WITH_NO_NEGATIVE_TARGET'

def test_negative_calibrated_utility_does_not_force_short_and_preserves_other_scores():
    p=np.array([[0.,.01,.02],[0.,-.01,.03]]);q=m.utility_scores(p,np.array([-.03,-.02]))
    np.testing.assert_array_equal(q[:,:2],p[:,:2]);assert np.all(q[:,2]<q[:,:2].max(1))
