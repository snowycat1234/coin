"""Focused causal tests for the new feedback and shared training paths."""
import numpy as np
from scripts.research.calibrate_expert_following import label_available_at
from scripts.research.joint_expert_information import (
    DAY_US, WEEK_US, feedback_panel, train_mask, same_switch_random, signed_intents, reference_available_at, research_decision,
)


def test_reference_open_value_waits_for_its_source_minute_bar():
    start=1704067200000000
    assert reference_available_at(start)==start+7*DAY_US+120_000_001


def test_unmature_last_week_outcome_cannot_change_current_feedback():
    anchor=1704067200000000
    d=anchor+np.arange(120)*DAY_US
    av=np.array([label_available_at(int(t),7) for t in d])
    u=np.arange(480,dtype=float).reshape(120,4)
    before,last=feedback_panel(d,av,u,anchor)
    decision=105 # Monday; previous Monday outcome isn't available until00:01.
    altered=u.copy();altered[decision-7]=10000
    after,_=feedback_panel(d,av,altered,anchor)
    assert np.array_equal(before[decision],after[decision])
    assert last[decision] <= d[decision]
    assert not np.array_equal(before[decision+7],after[decision+7])


def test_missing_week_slot_is_not_skipped_to_manufacture_history():
    anchor=1704067200000000;d=anchor+np.arange(120)*DAY_US
    av=np.array([label_available_at(int(t),7) for t in d])
    u=np.zeros((120,4));u[91,0]=np.nan
    feedback,_=feedback_panel(d,av,u,anchor)
    assert np.isnan(feedback[105]).all()


def test_label_purge_plus_embargo_strict_time_boundary():
    cutoff=100*DAY_US
    d=np.arange(100)*DAY_US
    av=d+7*DAY_US+60_000_002
    mask=train_mask(d,av,np.ones(100,bool),cutoff,7)
    assert np.all(av[mask]<cutoff-7*DAY_US)
    assert mask[85] and not mask[86]


def test_same_frequency_random_preserves_all_switch_boundaries():
    chosen=np.array([0,0,1,1,1,3,0,0,0,2])
    placebo=same_switch_random(chosen,1729)
    assert np.array_equal(np.diff(chosen)!=0,np.diff(placebo)!=0)


def test_future_price_and_direction_perturbation_keeps_past_intents():
    rng=np.random.default_rng(42);n=230
    close=100*np.exp(np.cumsum(rng.normal(0,.01,(n,5)),axis=0))
    sma=np.ones((n,5));d=1704067200000000+np.arange(n)*DAY_US
    names=['BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT']
    first=signed_intents(close,sma,d,names)
    changed=close.copy();changed[220:]*=1.5
    other=sma.copy();other[220:]*=-1
    second=signed_intents(changed,other,d,names)
    assert np.array_equal(first[:220],second[:220])
    assert np.max(np.abs(first).sum(2))<=.6+1e-9


def test_combined_only_gate_cannot_claim_a_qualified_simpler_model():
    gates=dict(FEEDBACK=False,MARKET_INTENT=False,COMBINED=True)
    assert research_decision(gates,False)=='PAUSE_EXACT_RIDGE_INFORMATION_RECIPE'
    assert research_decision(gates,True)=='REGISTER_NATIVE_CANDIDATE_NEXT'
    gates['FEEDBACK']=True
    assert research_decision(gates,False)=='RETAIN_SIMPLER_INFORMATION_CANDIDATE'
