"""Fixture-only request validation and original-mapper parity; no wallets/fits."""
import importlib.util, json, os
from pathlib import Path
import sys
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('evaluate_requests61',ROOT/'research/recover-frozen-runner-20261009/evaluate_requests61.py')
adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)


def fixture(extended=False,full=False):
    order=(adapter.E5 if full else adapter.COMPACT)+((adapter.SHORT,) if extended else ())
    canonical=adapter.E5+((adapter.SHORT,) if extended else ());n=len(order);k=len(canonical)
    tt=np.arange(adapter.frozen.START,adapter.frozen.END,adapter.frozen.DAY,dtype=np.int64)
    a=dict(decision_us=tt,symbol_order=np.array(adapter.frozen.SYMBOLS),expert_order=np.array(order),
           action_eligible=np.ones((61,n),bool),desired_expert_budget=np.full((61,n),1/n),feature_available_us=tt.copy(),request_available_us=tt.copy())
    m=dict(expert_order=list(order),allowed_actions=list(order),uses_feedback_features=False)
    targets=np.zeros((61,k,5));targets[:,1]=.03;targets[:,2]=np.array([.02,-.02,.01,-.01,0]);targets[:,3]=.02;targets[:,4]=np.array([.02,-.02,.01,-.01,0])
    if extended:targets[:,5]=-.02
    past=np.sin(np.arange(30)[:,None]+np.arange(5)[None])*0.002
    c=dict(expert_order=canonical,expert_targets=targets,expert_eligible=np.ones((61,k),bool),target_available_us=np.broadcast_to(tt[:,None],(61,k)).copy(),past_returns30=np.broadcast_to(past,(61,30,5)).copy())
    return m,a,c


@pytest.mark.parametrize('extended,full,slots',[(False,False,[0,1,4]),(False,True,[0,1,2,3,4]),(True,False,[0,1,4,5]),(True,True,[0,1,2,3,4,5])])
def test_explicit_identity_preserving_layouts(extended,full,slots):
    m,a,c=fixture(extended,full);request,report=adapter.validate(m,a,c)
    assert report['explicit_E5_slots']==slots
    np.testing.assert_array_equal(request[:,slots],a['desired_expert_budget'])
    assert np.all(request[:,[i for i in range(request.shape[1]) if i not in slots]]==0)


@pytest.mark.parametrize('bad',['future_feature','future_request','float_clock','duplicate_day','reversed_symbols','old_slots_reordered','short_replaces_Donchian','negative_request','nonnormalized','nan_request','numeric_mask','changed_mask','future_context','unknown_field','missing_feedback','future_feedback','half_parity'])
def test_invalid_inputs_stop_before_account(bad):
    m,a,c=fixture()
    if bad=='future_feature':a['feature_available_us'][0]+=1
    elif bad=='future_request':a['request_available_us'][0]+=1
    elif bad=='float_clock':a['decision_us']=a['decision_us'].astype(float)
    elif bad=='duplicate_day':a['decision_us'][1]=a['decision_us'][0]
    elif bad=='reversed_symbols':a['symbol_order']=a['symbol_order'][::-1]
    elif bad=='old_slots_reordered':a['expert_order']=a['expert_order'][::-1];m['expert_order']=a['expert_order'].tolist()
    elif bad=='short_replaces_Donchian':a['expert_order']=np.array([adapter.E5[0],adapter.E5[1],adapter.SHORT,adapter.E5[3],adapter.E5[4]]);m['expert_order']=a['expert_order'].tolist()
    elif bad=='negative_request':a['desired_expert_budget'][0,0]=-.1
    elif bad=='nonnormalized':a['desired_expert_budget'][0]*=2
    elif bad=='nan_request':a['desired_expert_budget'][0,0]=np.nan
    elif bad=='numeric_mask':a['action_eligible']=a['action_eligible'].astype(int)
    elif bad=='changed_mask':a['action_eligible'][0,0]=False
    elif bad=='future_context':c['target_available_us'][0,1]+=1
    elif bad=='unknown_field':a['future_reward']=np.ones(61)
    elif bad=='missing_feedback':m['uses_feedback_features']=True
    elif bad=='future_feedback':m['uses_feedback_features']=True;a['feedback_available_us']=a['decision_us'].copy()
    elif bad=='half_parity':a['ramped_expert_budget']=a['desired_expert_budget'].copy()
    with pytest.raises(ValueError):adapter.validate(m,a,c)


def test_no_cash_mask_preserves_cash_ramp_identity():
    m,a,c=fixture();m['allowed_actions']=list(adapter.COMPACT[1:]);a['action_eligible'][:,0]=False;a['desired_expert_budget'][:]=[0,.5,.5]
    request,report=adapter.validate(m,a,c);assert (request[:,0]==0).all() and report['explicit_E5_slots']==[0,1,4]


def bundle(tmp_path):
    m,a,c=fixture();np.savez_compressed(tmp_path/'request.npz',**a);(tmp_path/'producer.py').write_text('# Validation fixture only; no model or wallet.\n')
    files={n:dict(bytes=(tmp_path/n).stat().st_size,sha256=adapter.frozen.sha(tmp_path/n)) for n in ('request.npz','producer.py')}
    m.update(schema=adapter.SCHEMA,arm_id='FIXTURE',objective_version=2,prediction_role='HISTORICAL_FROZEN_REPLAY_NOT_LIVE_PREDICTIONS',source_files=['producer.py'],files=files,request_file='request.npz',
             model_sha256='1'*64,scaler_sha256='2'*64,training_plan_sha256='3'*64,producer_commit='4'*40,training_cutoff_us=adapter.frozen.START,maximum_training_label_available_us=adapter.frozen.START-1,
             maximum_scaler_input_available_us=adapter.frozen.START,actual_fit_completed_UTC='2026-10-01T00:00:00+00:00')
    path=tmp_path/'manifest.json';path.write_text(json.dumps(m));return path,m


def test_hashed_fixture_bundle(tmp_path):
    path,m=bundle(tmp_path);loaded,a=adapter.load_bundle(path,adapter.frozen.sha(path));assert loaded==m and len(a['decision_us'])==61
    (tmp_path/'producer.py').write_text('changed source')
    with pytest.raises(ValueError):adapter.load_bundle(path,adapter.frozen.sha(path))


@pytest.mark.parametrize('bad',['manifest_sha','path_escape','no_source','old_objective','future_labels','future_scaler','fake_fit_clock'])
def test_bound_provenance_rejection(tmp_path,bad):
    path,m=bundle(tmp_path)
    if bad=='manifest_sha':
        with pytest.raises(ValueError):adapter.load_bundle(path,'0'*64)
        return
    if bad=='path_escape':m['files']['../escaped.py']=m['files']['producer.py']
    elif bad=='no_source':m['source_files']=[]
    elif bad=='old_objective':m['objective_version']=1
    elif bad=='future_labels':m['maximum_training_label_available_us']=adapter.frozen.START
    elif bad=='future_scaler':m['maximum_scaler_input_available_us']=adapter.frozen.START+1
    elif bad=='fake_fit_clock':m['actual_fit_completed_UTC']='2026-10-01T00:00:00'
    path.write_text(json.dumps(m))
    with pytest.raises(ValueError):adapter.load_bundle(path,adapter.frozen.sha(path))


def test_original_E5_parity_and_zero_append_extension_on_fixtures(monkeypatch):
    # Import unchanged recovered mapper; all market/context arrays here are
    # synthetic fixtures. Never instantiate its simulator or run a day.
    mapper=adapter.frozen.modules(Path(os.environ.get('COIN_RECOVERED_STATE',ROOT.parent/'coin-recovery-state')))
    def forbidden(*args,**kwargs):raise AssertionError('Fixture validation must not create a wallet')
    monkeypatch.setattr(mapper,'NativeDailySimulator',forbidden)
    m,a,c=fixture(full=True);full,_=adapter.validate(m,a,c);targets,budgets=adapter.mapped(full,c,mapper.mapper)
    m6,a6,c6=fixture(extended=True,full=True);a6['desired_expert_budget'][:]=0;a6['desired_expert_budget'][:,:5]=a['desired_expert_budget']
    full6,_=adapter.validate(m6,a6,c6);targets6,budgets6=adapter.mapped(full6,c6,mapper.mapper)
    np.testing.assert_array_equal(targets6,targets);np.testing.assert_array_equal(budgets6[:,:5],budgets);assert (budgets6[:,5]==0).all()
    assert (targets[-1]==0).all() and abs(budgets[0]-[1,0,0,0,0]).sum()<=.1+1e-12


def test_nonzero_short_append_uses_same_budget_and_signed_target_combiner(monkeypatch):
    mapper=adapter.frozen.modules(Path(os.environ.get('COIN_RECOVERED_STATE',ROOT.parent/'coin-recovery-state')))
    monkeypatch.setattr(mapper,'NativeDailySimulator',lambda *a,**k:pytest.fail('No fixture wallet'))
    m,a,c=fixture(extended=True);full,_=adapter.validate(m,a,c);target,budget=adapter.mapped(full,c,mapper.mapper)
    # This fixture's low covariance needs no extra risk scale. The independent
    # scalar sum preserves both old named slots and the appended short leg.
    expected=np.array([[sum(budget[i,e]*c['expert_targets'][i,e,j] for e in range(6)) for j in range(5)] for i in range(61)])
    expected[-1]=0
    np.testing.assert_allclose(target,expected,atol=1e-17,rtol=0)
    assert (budget[:,2:4]==0).all() and (budget[:,5]>0).all()


@pytest.mark.parametrize('full', [False, True])
@pytest.mark.parametrize('replacement', ['CASH', 'VOL_MANAGED_HOLD'])
def test_forced_short_eligibility_release_precedes_discretionary_ramp(full, replacement, monkeypatch):
    source = ROOT / 'research/recover-frozen-runner-20261009/auxiliary/conditional_selector_core.py'
    spec = importlib.util.spec_from_file_location('scripts.research.conditional_selector_core', source)
    core = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, core)
    spec.loader.exec_module(core)
    m, a, c = fixture(extended=True, full=full)
    short = list(a['expert_order']).index(adapter.SHORT)
    destination = list(a['expert_order']).index(replacement)
    c['expert_eligible'][3:, 5] = False
    a['action_eligible'][3:, short] = False
    a['desired_expert_budget'][:] = 0
    a['desired_expert_budget'][:3, short] = 1
    a['desired_expert_budget'][3:, destination] = 1
    requests, _ = adapter.validate(m, a, c)

    def forbidden(*args):
        raise AssertionError('Six-slot fixture must use the actual append-only mapper')

    targets, budgets = adapter.mapped(requests, c, forbidden)
    # Three allowed 0.1-L1 transfers independently imply a .15 short budget.
    np.testing.assert_allclose(budgets[2], [.85, 0, 0, 0, 0, .15], atol=1e-15, rtol=0)
    released = np.array([1., 0, 0, 0, 0, 0])
    expected = released if replacement == 'CASH' else np.array([.95, .05, 0, 0, 0, 0])
    np.testing.assert_allclose(budgets[3], expected, atol=1e-15, rtol=0)
    assert abs(budgets[3] - budgets[2]).sum() > .1
    assert abs(budgets[3] - released).sum() <= .1 + 1e-15
    assert (budgets[3:, 5] == 0).all() and (targets[-1] == 0).all()


def test_release_exemption_does_not_allow_excess_discretionary_turnover(monkeypatch):
    from types import SimpleNamespace
    source = ROOT / 'research/recover-frozen-runner-20261009/auxiliary/conditional_selector_core.py'
    spec = importlib.util.spec_from_file_location('scripts.research.conditional_selector_core', source)
    core = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, core)
    spec.loader.exec_module(core)
    m, a, c = fixture(full=True)
    requests, _ = adapter.validate(m, a, c)

    def invalid_mapper(prior, desired, context):
        return SimpleNamespace(budget=np.array([0., 1., 0, 0, 0]), targets=np.zeros(5))

    with pytest.raises(ValueError, match='Original daily simplex/ramp violated'):
        adapter.mapped(requests, c, invalid_mapper)
