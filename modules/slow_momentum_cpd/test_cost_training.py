"""Synthetic end-to-end calendar/position/VJP counterexamples, no optimizer."""
from decimal import Decimal, localcontext

import numpy as np
import pytest
import torch

from .cost_training import (objective, position_grid, output_vjp, model_outputs,
                            arm_inputs, build_episode, report, portfolio_bootstrap, step_receipt)
from .core import DAY_US
from .run import utc_us
from .sharpe import PositionLSTM, InvalidScore, scored_sharpe
from .audit_cost_training import verify_source_rows, verify_decision
from .core import SYMBOLS


def fixture():
    mask=np.array([[True, True], [True, False], [True, True]])
    scale=np.array([[.02,.03],[.025,0],[.022,.028]])
    future=np.array([[.12,-.08],[-.07,np.nan],[.03,.06]])
    ep=dict(mask=mask,scale=scale,future=future,local=np.argwhere(mask))
    values=np.array([.25,-.4,-.15,.3,.2])
    return ep,values


def decimal_daily(weights, returns):
    """Independent quantity-notional loop, adverse fills and separate terminal."""
    with localcontext() as context:
        context.prec=50
        D=lambda x:Decimal(str(float(x)))
        fee,spread,slip=Decimal('.00055'),Decimal('.0004'),Decimal('.0004')
        carry=[Decimal(0)]*weights.shape[1]
        out=[]
        def cost(trade):
            execution=(spread+slip)*abs(trade)
            fill=abs(trade)+(spread+slip)*trade
            return execution+fee*fill
        for t in range(len(weights)):
            gross,paid=Decimal(0),Decimal(0)
            for a in range(weights.shape[1]):
                w=D(weights[t,a]);r=D(returns[t,a]) if w else Decimal(0)
                paid+=cost(w-carry[a]);gross+=w*r;carry[a]=w*(1+r)
            out.append(gross-paid)
        out[-1]-=sum(cost(-c) for c in carry)
        return np.array([float(x) for x in out])


def test_decimal_daily_sign_drift_mask_entry_and_paid_terminal():
    ep,p=fixture();loss,net,w=objective(torch.tensor(p),ep)
    expected=decimal_daily(w.numpy(),ep['future'])
    np.testing.assert_allclose(net.numpy(),expected,rtol=0,atol=2e-18)
    assert np.isfinite(float(loss))
    stats,daily,_=report(position_grid(torch.tensor(p),ep).numpy(),ep)
    np.testing.assert_allclose(daily,expected,rtol=0,atol=2e-18)
    assert stats['financial']['entry_cost']>0 and stats['financial']['terminal_cost']>0


def test_full_net_sharpe_position_gradient_finite_difference():
    ep,p=fixture();leaf=torch.tensor(p,requires_grad=True)
    loss,_,_=objective(leaf,ep);loss.backward()
    for k in range(len(p)):
        plus,minus=p.copy(),p.copy();plus[k]+=1e-6;minus[k]-=1e-6
        left=objective(torch.tensor(plus),ep)[0].item()
        right=objective(torch.tensor(minus),ep)[0].item()
        assert leaf.grad[k].item()==pytest.approx((left-right)/2e-6,rel=2e-6,abs=1e-7)


def test_memory_bounded_vjp_equals_full_autograd_lstm():
    ep,_=fixture();x=np.random.default_rng(77).normal(size=(5,63,10)).astype('float32')
    torch.manual_seed(2001);model=PositionLSTM()
    loss,_,_,_=output_vjp(model,x,ep,batch=3)
    vjp=[p.grad.clone() for p in model.parameters()]
    model.zero_grad(set_to_none=True)
    values=torch.cat([model(torch.from_numpy(x[k:k+3])) for k in range(0,5,3)])
    full,_,_=objective(values,ep);full.backward()
    assert loss==pytest.approx(full.item(),abs=1e-12)
    for left,p in zip(vjp,model.parameters(),strict=True):
        torch.testing.assert_close(left,p.grad,atol=2e-6,rtol=3e-5)


def test_whole_calendar_includes_cash_and_maturity_purge():
    clock=utc_us('2021-01-01')+np.arange(80)*DAY_US
    features=np.ones((80,2,10));vol=np.full((80,2),.04);r=np.full((80,2),.01)
    features[64,1]=np.nan
    ep=build_episode(clock,features,features,r,vol,'2021-03-05','2021-03-15')
    assert len(ep['clock'])==9 and ep['clock'][-1]+DAY_US<utc_us('2021-03-15')
    assert not ep['mask'][1:,1].any() and ep['mask'][:,0].all()
    altered=features.copy();altered[78:]=np.nan
    same=build_episode(clock,altered,altered,r,vol,'2021-03-05','2021-03-15')
    np.testing.assert_array_equal(ep['mask'],same['mask'])


@pytest.mark.parametrize('bad',[np.nan,-1.])
def test_future_bad_outcome_stops_does_not_silently_change_mask(bad):
    clock=utc_us('2021-01-01')+np.arange(80)*DAY_US
    features=np.ones((80,2,10));vol=np.full((80,2),.04);r=np.full((80,2),.01);r[65,0]=bad
    with pytest.raises(InvalidScore,match='Missing eligible'):
        build_episode(clock,features,features,r,vol,'2021-03-05','2021-03-15')


def test_baseline_zero_after_scaler_and_paired_model_identity():
    x=np.arange(2*63*10,dtype='float32').reshape(2,63,10)+1
    baseline=arm_inputs(x,'trend');cpd=arm_inputs(x,'trend_cpd')
    assert (baseline[:,:,8:]==0).all()
    np.testing.assert_array_equal(baseline[:,:,:8],cpd[:,:,:8]);np.testing.assert_array_equal(cpd,x)
    for seed in (2001,2002,2003):
        torch.manual_seed(seed);a=PositionLSTM()
        torch.manual_seed(seed);b=PositionLSTM()
        assert all(torch.equal(x,y) for x,y in zip(a.parameters(),b.parameters(),strict=True))


def test_caps_stop_without_silent_projection():
    ep,p=fixture();ep['scale'][:]=2
    with pytest.raises(ValueError,match='CAP_STOP'):
        objective(torch.tensor(p),ep)


def test_cash_invalid_and_small_position_explicit_near_cash():
    ep,p=fixture()
    stats,_,_=report(position_grid(torch.zeros_like(torch.tensor(p)),ep).numpy(),ep)
    assert stats['net_price_cost_sharpe'] is None and stats['score_status'].startswith('INVALID')
    assert stats['near_cash_flag']
    tiny,_,_=report(position_grid(torch.tensor(p*1e-5),ep).numpy(),ep)
    assert tiny['near_cash_flag'] and tiny['position_abs_mean']<.001


def test_bootstrap_original_net_series_no_retrading_and_no_cash_draw_drop():
    clock=np.arange(42,dtype='int64')*DAY_US
    x=np.arange(42);pair=np.column_stack((.001*np.sin(x)+.0001,.001*np.cos(x)+.0002))
    actual=portfolio_bootstrap([(clock,pair)])
    rng=np.random.default_rng(9901);diff=[]
    for _ in range(1000):
        starts=rng.integers(0,29,size=3);index=np.concatenate([np.arange(s,s+14) for s in starts])[:42]
        diff.append(scored_sharpe(pair[index,1])-scored_sharpe(pair[index,0]))
    np.testing.assert_allclose(actual['ci95'],np.quantile(diff,[.025,.975]),rtol=0,atol=2e-14)
    invalid=portfolio_bootstrap([(clock,np.zeros((42,2)))])
    assert invalid['status']=='INVALID_DEGENERATE_BOOTSTRAP' and invalid['invalid_replicates']==1000


def test_post_step_nonfinite_counts_actual_call_before_failure():
    model=torch.nn.Linear(1,1)
    class InvalidFakeStep:
        state={}
        def step(self):
            with torch.no_grad():model.weight.fill_(float('nan'))
    progress=dict(completed_updates=7,fits={'toy':7},validation_calls=0)
    saved=[]
    with pytest.raises(ValueError,match='NONFINITE'):
        step_receipt(InvalidFakeStep(),model,progress,'toy',lambda:saved.append(progress['completed_updates']))
    assert progress['completed_updates']==progress['fits']['toy']==8 and saved==[8]
    assert progress['validation_calls']==0


@pytest.mark.parametrize('field',['daily_vol','scaled_next_return'])
def test_source_derived_wrong_vol_or_label_is_rejected(field):
    clock=utc_us('2021-03-05')+np.arange(2)*DAY_US
    risk=np.full((3,5),.04);returns=np.full((3,5),.01)
    block=dict(dates=['2021-03-05','2021-03-10'],clock=clock,times=np.arange(2),mask=np.ones((2,5),bool))
    rows=[dict(block='2021-03-05',symbol=SYMBOLS[a],available_us=str(clock[t]),label_end_us=str(clock[t]+DAY_US),eligible='1',daily_vol='.04',scaled_next_return=str((.15/np.sqrt(365))*.01/.04)) for t in range(2) for a in range(5)]
    verify_source_rows(rows,[block],returns,risk)
    rows[0][field]=str(float(rows[0][field])+.01)
    with pytest.raises(AssertionError):verify_source_rows(rows,[block],returns,risk)


@pytest.mark.parametrize('field',['gates','decision'])
def test_corrupt_adoption_gate_or_decision_is_rejected(field):
    base=.001*np.sin(np.arange(42))+.0001;cpd=base+.0001
    joint=[np.column_stack((base,cpd)) for _ in range(3)]
    series={a+'_'+s:[base if a=='trend' else cpd]*3 for a in ('trend','trend_cpd') for s in ('seed2001','seed2002','seed2003','ensemble')}
    delta=scored_sharpe(np.tile(cpd,3))-scored_sharpe(np.tile(base,3))
    per=scored_sharpe(cpd)-scored_sharpe(base)
    result=dict(aggregate_ensemble_increment=delta,seed_increments=[delta]*3,block_ensemble_increments=[per]*3,
                gates=dict(absolute_CPD_cost_adjusted_positive=True,aggregate_net_sharpe_increment_positive=True,all_three_blocks_increment_positive=True,at_least_two_seeds_increment_positive=True,conditional_bootstrap_lower_positive=True),all_frozen_statistical_gates_pass=True,all_required_scores_valid=True,near_cash_flag=False,decision='PASS_PROXY_GATES_ONLY_NO_WALLET')
    verify_decision(result,series,joint,[.1,.4],[],np.full(10,.1))
    if field=='gates':result['gates']['absolute_CPD_cost_adjusted_positive']=False
    else:result['decision']='STOP_NO_FURTHER_RECIPE'
    with pytest.raises(AssertionError):verify_decision(result,series,joint,[.1,.4],[],np.full(10,.1))
