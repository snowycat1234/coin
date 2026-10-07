import numpy as np
import pytest
from scripts.research.fixed_trend_blend import compose_targets,FAMILIES


def test_map_cancel_without_relevering_and_suffix_causality():
    w=np.array([[[.12,-.12],[-.15,.15]],[[.1,-.1],[.15,-.15]]])
    targets,cs,d=compose_targets(w,['A','B'],['B','X','A'])
    assert np.array_equal(cs,np.array([[.15,0,-.15],[-.15,0,.15]]))
    assert np.allclose(targets[FAMILIES[1]][0],[.015,0,-.015])
    assert d['mean_netted_target_gross']<d['mean_pre_net_sleeve_intent_gross']
    changed=w.copy();changed[1]*=-1
    other,_,_=compose_targets(changed,['A','B'],['B','X','A'])
    for family in FAMILIES:assert np.array_equal(targets[family][0],other[family][0])


@pytest.mark.parametrize('core,full,w',[
    (['A','A'],['A','B'],np.zeros((1,2,2))),
    (['A','B'],['A','X'],np.zeros((1,2,2))),
    (['A','B'],['A','B'],np.array([[[.31,0],[0,0]]])),
    (['A','B'],['A','B'],np.full((1,2,2),np.nan)),
])
def test_invalid_identity_or_caps_rejected(core,full,w):
    with pytest.raises(ValueError):compose_targets(w,core,full)
