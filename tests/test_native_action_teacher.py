"""Synthetic teacher, local actual-action regret, causality and fixed H1 fit."""
from copy import deepcopy
from dataclasses import replace
import json
import numpy as np
import pytest
from quant.bybit_isolated_account import BybitIsolatedAccount
from scripts.investment import perpetual_directional as old
from scripts.investment.resumable_perpetual import NativeDailySimulator
from modules.native_action.teacher import (E6,DayContext,Proposal,causal_features,
    linear_ramp_risk_mapper,replay_candidates,training_state_relabel)
from modules.native_action.train import fit,NativeRewardModel,TRAIN_END,EVAL_START,label_metrics
from modules.native_action.runner import NativeExperiment,run
from test_resumable_perpetual import synthetic,CORE5


def context(stamp):
    targets=np.zeros((6,5))
    targets[1,:]=[.12,.12,.12,.12,.12]
    targets[2,:]=[-.12,.12,-.12,.12,.12]
    targets[3,:]=[.3,0,0,0,0]
    targets[4,:]=[0,.2,-.2,.2,0]
    targets[5,:]=[0,0,0,-.3,.3]
    return DayContext(stamp,stamp,(.02,-.01),('ret21','vol30'),targets,np.full(6,stamp,dtype=np.int64),
                      np.tile([.001,-.001,.002,.0005,-.0005],(30,1)),
                      dict(expert_order=list(E6),rank_checkpoint_sha256='1'*64,
                           mapper_sha256='2'*64,market_binding_sha256='3'*64))


def simulator():
    sim=NativeDailySimulator(synthetic(),'LONG_SHORT',old.COSTS[0],old.UNITS[0],
                            account_factory=BybitIsolatedAccount,persist_cash_close=True,
                            final_day_target_zero=True)
    sim.budget=[0.,1.,0.,0.,0.,0.]
    return sim


@pytest.fixture(scope='module')
def teacher_rows():
    sim=simulator()
    rows=[]
    for _ in range(3):
        row,sim,actual=replay_candidates(sim,context(sim.cursor),linear_ramp_risk_mapper)
        assert actual is None
        rows.append(row)
    return rows,sim


def test_greedy_has_six_native_ramped_candidates_and_no_free_cash(teacher_rows):
    rows,sim=teacher_rows
    assert len(rows)==3 and sim.rows_written==4320
    for row in rows:
        assert len(row['candidates'])==6
        assert row['label_available_us']>=row['interval_end_us']
        assert not row['global_native_upper_bound']
        for c in row['candidates']:
            assert sum(abs(a-b) for a,b in zip(c['budget'],row['budget_before']))<=.1+1e-10
    assert rows[1]['candidates'][0]['net_increment_USDT']!=0.
    terminal=rows[-1]
    assert terminal['forced_terminal_day'] and not terminal['optimization_allowed']
    assert terminal['e6_winner'] is None
    assert all(c['applied_targets']==[0.]*5 for c in terminal['candidates'])
    assert sim.account.fees>0 and all(p.quantity==0 for p in sim.account.positions.values())


def test_exact_actual_candidate_is_included_and_retained_on_local_path():
    sim=simulator()
    c=context(sim.cursor)
    desired=np.array([0.,.4,.1,.2,.1,.2])
    p=linear_ramp_risk_mapper(np.asarray(sim.budget),desired,c)
    actual=Proposal('STATE_EXACT',p.request,p.budget,p.targets,'SAVED_ORIGINAL_FEASIBLE_PROPOSAL')
    before=sim.state_hash()
    row,winner,baseline=replay_candidates(sim,c,linear_ramp_risk_mapper,baseline=actual,
                                          state_role='ACTUAL_SELECTOR_STATE')
    assert len(row['candidates'])==7 and row['actual_candidate']==6
    assert row['candidates'][6]['targets']==list(actual.targets)
    assert row['local_regret_USDT']>=0 and row['local_regret_must_not_be_summed_as_NAV']
    assert baseline.budget==list(actual.budget)
    assert sim.state_hash()==before and baseline.cursor==sim.cursor+old.DAY
    assert len(row['e6_rewards_USDT'])==6
    direct=sim.fork()
    direct.budget=list(actual.budget)
    direct.advance_day(dict(zip(CORE5,actual.targets)))
    assert baseline.account.snapshot()==direct.account.snapshot()


def test_future_outcomes_never_enter_features_and_availability_fails_closed():
    sim=simulator()
    c=context(sim.cursor)
    before=causal_features(sim,c)
    # Arbitrarily change all future prices and rates; current-state X stays fixed.
    for m in sim.window['market'].values():m['mark'][:]*=1.05
    for rate in sim.window['events']:rate['raw_rate']*=7
    assert before==causal_features(sim,c)
    with pytest.raises(ValueError,match='available'):
        causal_features(sim,replace(c,available_us=c.decision_us+1))
    with pytest.raises(ValueError,match='Outcome'):
        causal_features(sim,replace(c,market_feature_names=('next_reward','vol30')))
    with pytest.raises(ValueError,match='expert targets causally'):
        causal_features(sim,replace(c,expert_available_us=np.full(6,c.decision_us+1,dtype=np.int64)))


def test_h1_fit_maturity_freeze_and_future_outcome_invariance(teacher_rows,tmp_path):
    rows,_=teacher_rows
    model=fit(rows)
    assert model.metadata['admitted_rows']==2  # Common forced terminal day is not an action label.
    future=deepcopy(rows[0])
    future['decision_us']=EVAL_START
    future['features']=[1e6]*len(future['features'])
    future['e6_rewards_USDT']=[1e9,2e9,3e9,4e9,5e9,6e9]
    again=fit(rows+[future])
    np.testing.assert_array_equal(model.coefficients,again.coefficients)
    immature=deepcopy(rows[0]);immature['label_available_us']=TRAIN_END+1
    with pytest.raises(ValueError,match='At least two'):fit([immature,rows[1]])
    bad=deepcopy(rows[1]);bad['binding']['rank_checkpoint_sha256']='4'*64
    with pytest.raises(ValueError,match='identity'):fit([rows[0],bad])
    path=tmp_path/'student.npz';model.save(path)
    restored=NativeRewardModel.load(path)
    np.testing.assert_array_equal(restored.coefficients,model.coefficients)
    sim=simulator()
    request,pred=model.request(sim,context(sim.cursor))
    assert request.sum()==1 and np.count_nonzero(request)==1 and pred.shape==(6,)
    bad_context=replace(context(sim.cursor),binding=dict(context(sim.cursor).binding,rank_checkpoint_sha256='5'*64))
    with pytest.raises(ValueError,match='frozen'):model.request(sim,bad_context)
    changed=deepcopy(rows)
    changed[0]['feature_names'][0]='market.future_winner'
    with pytest.raises(ValueError,match='whitelist'):fit(changed)
    assert label_metrics(model,rows)['label_state_rows']==2


def test_training_state_relabel_rejects_evaluation_before_branch_replay(monkeypatch):
    sim=simulator();sim.cursor=EVAL_START
    monkeypatch.setattr(sim,'fork',lambda:pytest.fail('evaluation relabel replay forbidden'))
    with pytest.raises(ValueError,match='training intervals'):
        training_state_relabel(sim,context(sim.cursor),linear_ramp_risk_mapper,training_end_us=TRAIN_END)


def test_student_self_run_and_runner_deliver_actual_native_artifacts(teacher_rows,tmp_path):
    rows,_=teacher_rows
    model=fit(rows)
    sim=simulator()
    exp=NativeExperiment(sim,context,linear_ramp_risk_mapper,binding={'role':'SYNTHETIC_ONLY'})
    result=run(exp,tmp_path/'student','student',model=model,limit_seconds=60)
    report=json.loads((tmp_path/'student/RUN.json').read_text())
    predictions=[json.loads(line) for line in (tmp_path/'student/predictions.jsonl').read_text().splitlines()]
    assert report['status']=='COMPLETE' and result.rows_written==4320
    assert report['replica_of_old_v3_teacher'] is False
    assert len(predictions)==3 and predictions[-1]['forced_terminal_day']
    assert all(p['request'].count(1.)==1 for p in predictions)
    assert result.result()['summary']['terminal_cash_realized']
