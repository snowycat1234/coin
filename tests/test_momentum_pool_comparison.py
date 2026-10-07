"""Reject changed financial semantics in the one-pool causal comparison."""
from copy import deepcopy
import pytest
from scripts.research.check_momentum_pool import verify_pool_only


def pair():
    old=dict(task=dict(window=dict(id='same',start=1,end=2,days=1,active_symbols=['A','B','C','D','E','F']),
                      work='same',collector_root='same',source_run='same',funding_scale=1,profile='FULL',mapping='NEUTRAL',family='same',seed=0),
             summary=dict(contract={'capital':10000,'gross_cap':.6},cost_scenario={'fee_bp':5.5},unit_scenario={'scale':1},symbols=list('ABCDEF')),
             binding=dict(wallet_source_sha256='same',storage_source_sha256='same',observed_mark_reference_sha256='same',
                          financial_sources={'account':'same'},frozen_wallet_sources={'wallet':'same'}))
    new=deepcopy(old);new['task']['window']['active_symbols']=list('ABCDE')
    return old,new


def test_only_pool_and_derived_target_change_allowed():
    old,new=pair();new['task']['target_sha256']='new';new['task']['protocol_sha256']='new'
    verify_pool_only(old,new)


@pytest.mark.parametrize('scope,key,value',[
    ('summary','cost_scenario',{'fee_bp':0}),
    ('summary','contract',{'capital':10000,'gross_cap':.7}),
    ('summary','symbols',list('BACDEF')),
    ('task','funding_scale',.01),
    ('binding','financial_sources',{'account':'changed'}),
])
def test_financial_or_ordering_change_rejected(scope,key,value):
    old,new=pair();new[scope][key]=value
    with pytest.raises(AssertionError):verify_pool_only(old,new)
