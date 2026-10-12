"""One fixed conditional minute account to observe real short activity."""
import argparse,importlib.util,io,json,sys,time,zipfile
from pathlib import Path
import numpy as np
import polars as pl
import pyarrow.parquet as pq
from activity import targets,episodes,nav_bridge,rejection_counts

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];NATIVE=ROOT/'research/native-mark-inputs-20261011'
sys.path.insert(0,str(NATIVE));spec=importlib.util.spec_from_file_location('input_bridge',NATIVE/'inspect_phase.py');bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)
from mark_bars import source_bars,day_block,legacy_projection,exact_boundary,DAY
from scripts.investment.resumable_perpetual import NativeDailySimulator
from scripts.investment.perpetual_directional import COSTS,UNITS,save_case
import pandas as pd
SYMBOLS=tuple(bridge.SYMBOLS)

def utc(s):return int(pd.Timestamp(s,tz='UTC').value//1000)
def verify():
    for line in (HERE/'ACTIVE_SOURCE_SHA256.txt').read_text().splitlines():
        sha,name=line.split(maxsplit=1);assert bridge.digest((ROOT/name).read_bytes())==sha,name

def fund_events(state,start,end):
    spec=importlib.util.spec_from_file_location('fund',ROOT/'research/short-funding-residual-20261011/experiment.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
    raw=f.source_archive(ROOT,state);events=[];proof=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        members=json.loads(z.read('MEMBERS.json'))['files']
        for s in SYMBOLS:
            name=f'source_tables_not_model_inputs/economics/{s}_funding_events.parquet';b=z.read(name);assert bridge.digest(b)==members[name]['SHA256']
            frame=pq.read_table(io.BytesIO(b),columns=['calc_time_ms','last_funding_rate','funding_interval_hours'],filters=[('calc_time_ms','>=',start//1000),('calc_time_ms','<',end//1000)]).to_pandas().sort_values('calc_time_ms')
            assert not frame.calc_time_ms.duplicated().any() and np.isfinite(frame.to_numpy()).all()
            for r in frame.itertuples(index=False):events.append(dict(symbol=s,event_us=int(r.calc_time_ms)*1000,raw_rate=float(r.last_funding_rate),reported_interval_hours=float(r.funding_interval_hours)))
            proof.append(dict(symbol=s,member_SHA256=bridge.digest(b),events=len(frame)))
    return sorted(events,key=lambda r:(r['event_us'],r['symbol'])),dict(source_commit=f.SOURCE_COMMIT,archive_SHA256=f.ARCHIVE_SHA,members=proof)

def run(state,source_commit,expected=None):
    assert not state.exists() and state.resolve().is_relative_to(Path('/workspace')) and not bridge.git('status','--porcelain')
    if not expected:assert bridge.git('rev-parse','HEAD').decode().strip()==source_commit
    verify();state.mkdir();began=time.monotonic();bridge.configure(state,'Q12022');start,end=utc('2022-01-01'),utc('2022-02-01')
    protocol=json.loads((NATIVE/'PROTOCOL.json').read_text())
    tp,tc=bridge.certificate(protocol['trade_source_commit'],bridge.TRADE,'Q12022');mp,mc=bridge.certificate(protocol['mark_source_commit'],bridge.MARK,'Q12022')
    prevt,pt=bridge.certificate(protocol['trade_source_commit'],bridge.TRADE,'Y2021');prevm,pm=bridge.certificate(protocol['mark_source_commit'],bridge.MARK,'DEC2021')
    inv,*_=bridge.inventories();reader=bridge.SourceReader(inv,state,local=False);trade={};mark={};daily=[];sources=[]
    for s in SYMBOLS:
        tr=next(r for r in tp['sources'] if r['source']['symbol']==s and r['source']['month']=='2022-01');mr=next(r for r in mp['sources'] if r['source']['symbol']==s and r['source']['month']=='2022-01')
        assert tr['past_boundary']==prevt['end_boundaries'][s] and mr['past_boundary']==prevm['end_boundaries'][s]
        assert tr['past_boundary']['available_us']==mr['past_boundary']['available_us']==start
        tf,te=bridge.decoded_month(reader,tr['source'],start//1000,end//1000);mf,me=bridge.complete_month(reader,mr['source'],start//1000,end//1000)
        trade[s]=source_bars(tf,tr['source'],'klines',added_repair_rows=sum(r['added_actual_rows'] for r in te['repairs']))
        mark[s]=source_bars(mf,mr['source'],'markPriceKlines',added_repair_rows=sum(r['added_actual_rows'] for r in me['repairs']))
        for at in range(start,end,DAY):daily.append(dict(symbol=s,close_us=at,close=tr['past_boundary']['close'] if at==start else exact_boundary(trade[s],at)['price']))
        sources.append(dict(symbol=s,trade_ZIP_SHA256=tr['source']['ZIP_SHA256'],mark_ZIP_SHA256=mr['source']['ZIP_SHA256'],minutes=len(tf)))
        print('JANUARY_SOURCE_REUSED',s,len(tf),len(mf),flush=True)
    reader.close();events,funding=fund_events(state,start,end)
    path=ROOT/'research/minute-conditional-selector-20261011/result/VECTORS.npz'
    with np.load(path,allow_pickle=False) as z:
        selected=(z['eval_decision_us']>=start)&(z['eval_decision_us']<end);d=z['eval_decision_us'][selected];w=z['A_targets'][selected]
    with np.load(ROOT/'research/minute-conditional-selector-20261011/input/SOURCE_PREPARED.npz',allow_pickle=False) as z:
        assert tuple(z['symbol_order'])==SYMBOLS,'Exact saved target column identity'
    targets(d,w,start,end,utc('2022-01-01'),SYMBOLS)
    def factory(daily,clocks,mode):
        np.testing.assert_array_equal(clocks,d)
        return pl.DataFrame([dict(available_us=int(t),symbol=s,target_weight=float(w[i,j])) for i,t in enumerate(d) for j,s in enumerate(SYMBOLS)]),dict(source='UNCHANGED_SAVED_CAUSAL_A181_TARGETS',model_fit_available_us=start,target_archive_SHA256=bridge.digest(path.read_bytes()))
    def blocks():
        for at in range(start,end,DAY):yield legacy_projection(day_block(SYMBOLS,trade,mark,at))
    window=dict(start=start,end=end,symbols=SYMBOLS,daily=pl.DataFrame(daily),events=events,minute_blocks=blocks)
    sim=NativeDailySimulator(window,'LONG_SHORT',COSTS[0],UNITS[0],target_factory=factory)
    while sim.cursor<end and sim.stop is None:
        sim.advance_day();assert time.monotonic()-began<600
        print('ACTUAL_ACCOUNT_DAY',sim.rows_written//1440,'shortfilllegs',sum(r['leg']=='OPEN' and r['position_delta']<0 for r in sim.account.trades),flush=True)
    case=sim.result();ep,q=episodes(case['trades'],SYMBOLS);summary=case['summary']
    for s in SYMBOLS:assert q[s]==sim.account.positions[s].quantity,'Independent per-asset inventory bridge'
    financial=nav_bridge(case['trades'],case['funding'],q,summary['terminal_mark_prices'],sim.account.nav())
    saved=save_case(case,state/'ACCOUNT');summary=saved['summary']
    assert abs(sum(v['net_contribution'] for v in summary['long_short_marked_contribution'].values())-(summary['NAV']-10000))<1e-7
    minute=case['minute'];short=np.zeros(minute.height,bool)
    for s in SYMBOLS:short|=minute[s+'_quantity'].to_numpy()<0
    shortdays=len(np.unique((minute['close_us'].to_numpy()[short]-1)//DAY));reasons=rejection_counts(case['rejections'])
    report=dict(status='COMPLETE_CONDITIONAL_SHORT_ACTIVITY' if summary['terminal_cash_realized'] and summary['completed_minutes']==44640 else 'STOP_CONDITIONAL_ACTIVITY_ACCOUNT_WITH_RESIDUAL_OR_HALT',source_commit=source_commit,
        target_dates=31,negative_target_dates=int((w<-1e-12).any(1).sum()),actual_short_open_fill_legs=sum(r['leg']=='OPEN' and r['position_delta']<0 for r in case['trades']),
        actual_short_unique_entry_episodes=len(ep),actual_negative_inventory_minutes=int(short.sum()),actual_negative_inventory_UTC_days=shortdays,
        episodes=ep,rejection_reasons=reasons,independent_decimal_NAV_bridge=financial,summary=summary,sources=sources,
        source_certificates=dict(trade=tc,mark=mc,priortrade=pt,priormark=pm,funding=funding),new_strategy_activity_accounts=1,new_model_fits=0,provider_downloads=0,
        native_authority='BLOCKED_CONDITIONAL_FEE_UNIT_PASTMARK_MMR_ARRIVAL_NOT_NATIVE_CERTIFIED',external59_used=False,forced_short=False,
        scope='SEEN_TRAINING_ACTIVITY_UNDER_EXISTING_CONDITIONAL_NATIVE_SOFTWARE_KERNEL_NOT_INVESTMENT_QUALIFICATION')
    body={k:case[k] for k in ('trades','funding','rejections','breaches','extrema','target_meta')};body['summary']=summary;body['targets']=case['targets'].to_dicts()
    bridge.save(state/'ACCOUNT.json',body);np.savez_compressed(state/'MINUTE.npz',**{k:minute[k].to_numpy() for k in minute.columns});bridge.save(state/'RESULT.json',report)
    bridge.save(state/'TIMING.json',dict(total_seconds=time.monotonic()-began))
    if expected:
        for name in ('ACCOUNT.json','MINUTE.npz','RESULT.json'):
            assert bridge.git('show',expected+':research/short-native-activity-20261012/result/'+name)==(state/name).read_bytes(),'Exactaccountrestore '+name
        bridge.save(state/'PUBLIC_RESTORE.json',dict(status='PASS_EXACT_PUBLIC_CONDITIONAL_SHORT_ACCOUNT_RESTORE',artifact_commit=expected,verification_accounts=1,new_model_fits=0,provider_downloads=0))
    print(json.dumps({k:report[k] for k in ('status','negative_target_dates','actual_short_open_fill_legs','actual_short_unique_entry_episodes','actual_negative_inventory_minutes','actual_negative_inventory_UTC_days','rejection_reasons')},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True);p.add_argument('--expected-commit');a=p.parse_args();run(a.state,a.source_commit,a.expected_commit)
