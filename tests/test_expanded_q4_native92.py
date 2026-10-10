"""Saved-request rejection fixtures; no account or simulator construction."""
import json,sys
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'research/recover-frozen-runner-20261009'))
import expanded_q4_native92 as ex


@pytest.mark.parametrize('bad',['none','future_feature','request_clock','symbol_order','expert_order','mask','request','target','budget','terminal_target'])
def test_exact_source_request_clock_mask_slots_mapping_and_terminal(bad):
    m=ex.read(ex.PUBLIC/'producer/MANIFEST.json');a=ex.arrays(ex.PUBLIC/'producer/REQUESTS.npz');path=ex.arrays(ex.PUBLIC/'producer/EXPANDED_PATH.npz');source=ex.arrays(ex.q4.PUBLIC/'producer/CURRENT_EXPERT_INPUTS92.npz');ctx=ex.q4.contexts();mapper=ex.q4.base.frozen.modules(ROOT.parent/'coin-recovery-state')
    if bad=='future_feature':a['feature_available_us'][0]+=1
    elif bad=='request_clock':a['request_available_us'][0]+=1
    elif bad=='symbol_order':a['symbol_order']=a['symbol_order'][::-1]
    elif bad=='expert_order':a['expert_order']=a['expert_order'][::-1]
    elif bad=='mask':a['action_eligible'][0,2]=True
    elif bad=='request':a['desired_expert_budget'][1,[0,1]]+=np.array([.001,-.001])
    elif bad=='target':path['targets'][1,0]+=.001
    elif bad=='budget':path['budget'][1,0]+=.001
    elif bad=='terminal_target':path['targets'][-1,0]=.001
    if bad=='none':
        f,b,g=ex.request_gate(m,a,path,ctx,source,mapper)
        assert np.array_equal(f,path['targets']) and np.array_equal(b,path['budget']) and not f[-1].any()
        assert g['terminal_request_preserved'] and g['wallets_run']==0 and g['model_inference']==0
    else:
        with pytest.raises(ValueError):ex.request_gate(m,a,path,ctx,source,mapper)


def test_new_binding_authorizes_one_and_preserves_original_contract():
    plan=ex.read(ex.PUBLIC/'EXECUTION_PLAN.json');c=ex.read(ex.PUBLIC/'ADAPTER_CONTRACT.json');original=ex.read(ex.q4.PUBLIC/'ADAPTER_CONTRACT.json')
    assert plan['authorization']==ex.AUTHORIZATION and plan['new_wallets']==1
    assert plan['terminal']==ex.q4.terminal_contract() and c['execution_calendar']==original['execution_calendar']
    assert c['financial_contract']==original['financial_contract'] and c['cost']==original['cost'] and c['limits']==original['limits']
    assert plan['comparator_commit']==ex.COMPARATORS and set(ex.read(ex.PUBLIC/'COMPARATORS.json'))==set(ex.q4.ARMS)
    assert plan['mapping_preflight']['request_sha256']!=ex.sha(ex.q4.PUBLIC/'producer/REQUESTS.npz')
    assert plan['mapping_preflight']['wallets_run']==0
