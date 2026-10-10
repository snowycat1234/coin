"""Source request rejection and durable original-engine fixture recovery; no research wallets."""
import importlib.util,json,sys
from copy import deepcopy
from pathlib import Path
import numpy as np
import polars as pl
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'research/recover-frozen-runner-20261009'))
import prefix_static_native63 as runner
import durable_native_checkpoint as durable


def fixture_request():
    tt=np.arange(63,dtype=np.int64)*86400000000+1688342400000000
    request=np.zeros((63,6));request[:,5]=1;eligible=np.ones((63,6),bool);eligible[:,2:4]=False
    c=dict(expert_order=runner.base.E5+(runner.base.SHORT,),expert_targets=np.zeros((63,6,5)),expert_eligible=eligible,target_available_us=np.broadcast_to(tt[:,None],(63,6)).copy(),past_returns30=np.zeros((63,30,5)))
    a=dict(decision_us=tt,symbol_order=np.array(runner.base.frozen.SYMBOLS),expert_order=np.array(c['expert_order']),desired_expert_budget=request,action_eligible=eligible.copy(),feature_available_us=tt.copy(),request_available_us=tt.copy())
    producer={k:v.copy() for k,v in c.items() if isinstance(v,np.ndarray)};producer['expert_input_available_us']=np.broadcast_to(tt[:,None],(63,18)).copy()
    surrogate=dict(decision_us=tt,targets=np.zeros((63,5)),mapped_expert_budget=request.copy(),nav=np.full(64,10000.))
    paired={'SHORT_requests':request.copy(),'SHORT_targets':surrogate['targets'].copy(),'SHORT_budget':request.copy(),'SHORT_nav':surrogate['nav'].copy()}
    choice=dict(E6_slot=5,selected_control='SHORT',latest_label_available_us=int(tt[0]-1))
    cal=dict(start=int(tt[0]),end_exclusive=int(tt[-1]+86400000000),days=63,minutes=90720,funding_events=945)
    return a,c,choice,producer,paired,surrogate,cal


@pytest.mark.parametrize('bad',['terminal_CASH','future_feature','wrong_mask','reordered_E6','changed_covariance'])
def test_reject_changed_request_or_context_before_wallet(bad):
    a,c,choice,producer,paired,surrogate,cal=fixture_request()
    assert runner.request_parity(a,c,choice,producer,paired,surrogate,cal)[-1,5]==1
    if bad=='terminal_CASH':a['desired_expert_budget'][-1]=[1,0,0,0,0,0]
    elif bad=='future_feature':a['feature_available_us'][0]+=1
    elif bad=='wrong_mask':a['action_eligible'][1,5]=False
    elif bad=='reordered_E6':a['expert_order']=a['expert_order'][::-1]
    else:c['past_returns30'][1,1,1]=.01
    with pytest.raises(ValueError):runner.request_parity(a,c,choice,producer,paired,surrogate,cal)


def window():
    start=1688342400000000;n=2880;symbols=runner.base.frozen.SYMBOLS
    market={s:dict(open=np.full(n,100.),close=np.full(n,100.),mark=np.full(n,100.),quote_volume=np.full(n,1000000.)) for s in symbols}
    market[symbols[0]]['quote_volume'][0]=1000. # partial fill followed by completion
    daily=pl.DataFrame([dict(symbol=s,close_us=t,close=100.) for t in (start,start+86400000000) for s in symbols])
    events=[dict(symbol=s,event_us=start+i*28800000000,raw_rate=(-.001 if j%2 else .001),reported_interval_hours=8.) for i in range(6) for j,s in enumerate(symbols)]
    return dict(symbols=symbols,start=start,end=start+n*60000000,daily=daily,market=market,events=events)


def original_sim():
    runner.base.frozen.modules(ROOT.parent/'coin-recovery-state')
    from scripts.investment.resumable_perpetual import NativeDailySimulator
    from scripts.investment.perpetual_directional import COSTS
    from quant.bybit_isolated_account import BybitIsolatedAccount
    return NativeDailySimulator(window(),'LONG_SHORT',COSTS[0],dict(id='RAW_AS_FRACTION',scale=1.),account_factory=BybitIsolatedAccount,persist_cash_close=True,final_day_target_zero=True)


def test_checkpoint_resume_preserves_partial_orders_prior_capacity_funding_and_paid_terminal(tmp_path):
    sim=original_sim();binding=dict(engine_sha256=runner.ENGINE_SHA,fixture=True);sim.budget=[1.,0.,0.,0.,0.,0.]
    durable.save(tmp_path,sim,binding,0.);fresh,_=durable.restore(tmp_path,binding,window())
    assert fresh.previous_quote is None and fresh.account.snapshot()==sim.account.snapshot()
    target=dict.fromkeys(sim.symbols,.02);target[sim.symbols[0]]=-.1
    assert sim.advance_day(target)['completed'];durable.save(tmp_path,sim,binding,1.)
    recovered,pointer=durable.restore(tmp_path,binding,window());assert pointer['completed_days']==1 and recovered.state_hash()==sim.state_hash() and recovered.previous_quote==sim.previous_quote
    for account in (sim,recovered):assert account.advance_day(target)['completed']
    assert recovered.snapshot()==sim.snapshot()
    assert all(not p.quantity for p in recovered.account.positions.values())
    assert any(t['leg']=='CLOSE' and t['fee_amount']>0 for t in recovered.account.trades)
    assert all(not f['owned'] for f in recovered.funding_journal if f['event_us']==recovered.start)
    assert all(v==0 for v in recovered.weights[recovered.start+86400000000].values())


@pytest.mark.parametrize('bad',['binding','state_bytes','minute_bytes','chunk_count'])
def test_checkpoint_tampering_rejected(tmp_path,bad):
    sim=original_sim();binding=dict(fixture=True);durable.save(tmp_path,sim,binding,0.)
    sim.advance_day(dict.fromkeys(sim.symbols,.02));durable.save(tmp_path,sim,binding,1.);pointer=runner.read(tmp_path/'CHECKPOINT.json')
    if bad=='binding':binding={'fixture':False}
    elif bad=='state_bytes':(tmp_path/pointer['snapshot']['path']).write_bytes(b'changed')
    elif bad=='minute_bytes':(tmp_path/pointer['minute_chunks'][0]['path']).write_bytes(b'changed')
    else:pointer['completed_days']=2;(tmp_path/'CHECKPOINT.json').write_text(json.dumps(pointer))
    with pytest.raises(ValueError):durable.restore(tmp_path,binding,window())
