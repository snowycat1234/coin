"""Frozen request rejection and partial-terminal fixtures, never research wallets."""
import json,sys
from pathlib import Path
import numpy as np
import polars as pl
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'research/recover-frozen-runner-20261009'))
import q4_native92 as q4
MINUTE=q4.base.frozen.MINUTE;DAY=q4.base.frozen.DAY


def request_fixture(tmp_path,monkeypatch):
    public=tmp_path/'public';(public/'producer').mkdir(parents=True);monkeypatch.setattr(q4,'PUBLIC',public)
    tt=np.arange(q4.START,q4.REQUEST_CAL['end_exclusive'],DAY,dtype=np.int64)
    mask=np.ones((92,6),bool);mask[:,2:4]=False;targets=np.zeros((92,6,5));targets[:,1]=.03;targets[:,4]=-.01;targets[:,5]=-.02
    available=np.broadcast_to(tt[:,None],(92,6)).copy();past=np.full((92,30,5),.01)
    np.savez(public/'producer/CURRENT_EXPERT_INPUTS92.npz',expert_targets=targets,expert_eligible=mask,target_available_us=available,past_returns30=past,input_available_us=np.broadcast_to(tt[:,None],(92,18)))
    manifest=dict(expert_order=list(q4.base.E5+(q4.base.SHORT,)));(public/'producer/MANIFEST.json').write_text(json.dumps(manifest))
    requests=np.zeros((92,6));requests[:,1]=1
    a=dict(decision_us=tt,symbol_order=np.array(q4.base.frozen.SYMBOLS),expert_order=np.array(manifest['expert_order']),desired_expert_budget=requests,action_eligible=mask.copy(),feature_available_us=tt.copy(),request_available_us=tt.copy())
    q4.base.frozen.modules(ROOT.parent/'coin-recovery-state');fractions,budgets=q4.base.mapped(requests,q4.contexts(),q4.base.frozen.modules(ROOT.parent/'coin-recovery-state').mapper,q4.REQUEST_CAL)
    np.savez(public/'producer/PAIRED_PATHS.npz',FROZEN_VOL_requests=requests,FROZEN_VOL_targets=fractions,FROZEN_VOL_budget=budgets)
    np.savez(public/'producer/REQUESTS_FROZEN_VOL.npz',**a);return public,a


@pytest.mark.parametrize('bad',['none','terminal_cash','future_feature','wrong_mask','reordered_slots','changed_target','changed_budget'])
def test_frozen92_clocks_slots_mask_budget_and_terminal_request(tmp_path,monkeypatch,bad):
    public,a=request_fixture(tmp_path,monkeypatch)
    if bad=='terminal_cash':a['desired_expert_budget'][-1]=[1,0,0,0,0,0]
    elif bad=='future_feature':a['feature_available_us'][0]+=1
    elif bad=='wrong_mask':a['action_eligible'][0,2]=True
    elif bad=='reordered_slots':a['expert_order']=a['expert_order'][::-1]
    elif bad in ('changed_target','changed_budget'):
        paired=q4.arrays(public/'producer/PAIRED_PATHS.npz');paired['FROZEN_VOL_'+('targets' if bad=='changed_target' else 'budget')][1,1]+=.001;np.savez(public/'producer/PAIRED_PATHS.npz',**paired)
    np.savez(public/'producer/REQUESTS_FROZEN_VOL.npz',**a)
    if bad=='none':
        f,b,gate=q4.check(ROOT.parent/'coin-recovery-state','FROZEN_VOL');assert len(f)==len(b)==92 and not f[-1].any() and gate['terminal_request_preserved'] and gate['wallets_run']==0
    else:
        with pytest.raises(ValueError):q4.check(ROOT.parent/'coin-recovery-state','FROZEN_VOL')


def fixture_window():
    n=1446;start=q4.START;symbols=q4.base.frozen.SYMBOLS
    market={s:dict(open=np.full(n,100.),close=np.full(n,100.),mark=np.full(n,100.),quote_volume=np.full(n,1000000.)) for s in symbols}
    for a in market.values():a['quote_volume'][1440]=0;a['quote_volume'][1441]=1000.;a['open'][1441:]=np.arange(101.,106.)
    daily=pl.DataFrame([dict(symbol=s,close_us=t,close=100.) for t in (start,start+DAY) for s in symbols])
    events=[dict(symbol=s,event_us=start+offset,raw_rate=.001,reported_interval_hours=8.) for offset in (0,DAY//3,2*DAY//3,DAY+1) for s in symbols]
    return dict(symbols=symbols,start=start,end=start+n*MINUTE,daily=daily,market=market,events=events)


def simulator(monkeypatch):
    q4.base.frozen.modules(ROOT.parent/'coin-recovery-state')
    from scripts.investment.resumable_perpetual import NativeDailySimulator
    from scripts.investment.perpetual_directional import COSTS
    from quant.bybit_isolated_account import BybitIsolatedAccount
    win=fixture_window();monkeypatch.setattr(q4,'END',win['end']);monkeypatch.setattr(q4,'EXECUTION_CAL',dict(decisions=2,full_held_days=1,terminal_minutes=6,minutes=1446))
    return NativeDailySimulator(win,'LONG_SHORT',COSTS[0],dict(id='RAW_AS_FRACTION',scale=1.),account_factory=BybitIsolatedAccount,persist_cash_close=True,final_day_target_zero=True),win


def test_six_minute_terminal_partial_paid_close_and_exact_recovery(tmp_path,monkeypatch):
    sim,win=simulator(monkeypatch);binding={'fixture':'partial-terminal'};sim.budget=[1.,0.,0.,0.,0.,0.];target=dict.fromkeys(sim.symbols,.02)
    q4.save_checkpoint(tmp_path,sim,binding,0.);fresh,_=q4.restore(tmp_path,binding,win);assert fresh.previous_quote is None and fresh.account.snapshot()==sim.account.snapshot()
    assert sim.advance_day(target)['completed'];q4.save_checkpoint(tmp_path,sim,binding,1.);other,_=q4.restore(tmp_path,binding,win)
    for obj in (sim,other):assert obj.advance_day(target)['completed']
    assert other.snapshot()==sim.snapshot() and sim.rows_written==1446 and sim.cursor==win['end'] and all(not p.quantity for p in sim.account.positions.values())
    q4.save_checkpoint(tmp_path,sim,binding,2.);final,pointer=q4.restore(tmp_path,binding,win);assert pointer['completed_decisions']==2 and final.snapshot()==sim.snapshot() and final.minute_chunks[-1].shape==(6,36)
    fills=[t for t in sim.account.trades if t['event_us']>=q4.START+DAY];assert len(fills)==10 and all(t['leg']=='CLOSE' and t['fee_amount']>0 for t in fills)
    assert {t['event_us'] for t in fills}=={q4.START+DAY+2*MINUTE+1,q4.START+DAY+3*MINUTE+1}
    assert all(not f['owned'] for f in sim.funding_journal if f['event_us']==q4.START)
    assert all(f['owned'] and f['mark_close_us']<f['event_us'] for f in sim.funding_journal if f['event_us']==q4.START+DAY+1)
    assert all(v==0 for v in sim.weights[q4.START+DAY].values())
    with pytest.raises(ValueError):sim.advance_day(target)


def test_zero_capacity_five_attempt_expiry_cannot_become_free_flat(monkeypatch):
    sim,win=simulator(monkeypatch)
    for a in win['market'].values():a['quote_volume'][1440:]=0
    target=dict.fromkeys(sim.symbols,.02);assert sim.advance_day(target)['completed'];assert sim.advance_day(target)['completed']
    assert sim.rows_written==1446 and not sim.result()['summary']['terminal_cash_realized'] and any(p.quantity for p in sim.account.positions.values())
    assert not any(t['event_us']>=q4.START+DAY for t in sim.account.trades)
    with pytest.raises(ValueError):q4.require(all(p.quantity==0 for p in sim.account.positions.values()),'Paid-flat requirement')
    with pytest.raises(ValueError):sim.advance_day(target)


@pytest.mark.parametrize('bad',['binding','state_bytes','minute_bytes','partial_count'])
def test_reject_changed_partial_terminal_checkpoint(tmp_path,monkeypatch,bad):
    sim,win=simulator(monkeypatch);binding={'fixture':True};q4.save_checkpoint(tmp_path,sim,binding,0.);sim.advance_day(dict.fromkeys(sim.symbols,.02));q4.save_checkpoint(tmp_path,sim,binding,1.);sim.advance_day(dict.fromkeys(sim.symbols,.02));q4.save_checkpoint(tmp_path,sim,binding,2.);p=q4.read(tmp_path/'CHECKPOINT.json')
    if bad=='binding':binding={'fixture':False}
    elif bad=='state_bytes':(tmp_path/p['snapshot']['path']).write_bytes(b'changed')
    elif bad=='minute_bytes':(tmp_path/p['minute_chunks'][-1]['path']).write_bytes(b'changed')
    else:p['completed_minutes']=2880;(tmp_path/'CHECKPOINT.json').write_text(json.dumps(p))
    with pytest.raises(ValueError):q4.restore(tmp_path,binding,win)
