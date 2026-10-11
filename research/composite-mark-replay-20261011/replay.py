"""One paired conditional wallet compatibility check; no new risk semantics."""
import argparse
from datetime import datetime,timezone
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import time
import zipfile
import numpy as np
import polars as pl
import pyarrow.parquet as pq
from composite_bars import composite_bars,minute_observation

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
NATIVE='research/native-mark-inputs-20261011/'
MARK='research/core5-continuous-mark-20261011/'
TRADE='research/core5-continuous-risk600-20261011/'
sys.path.insert(0,str(ROOT/NATIVE));sys.path.insert(0,str(ROOT/MARK))
from mark_bars import day_block,legacy_projection,DAY,MINUTE
from mark_source import configure,inventories,complete_month,SourceReader as MarkReader,git,digest,save,bind_current,SYMBOLS
from prepare import SourceReader as TradeReader,decoded_month
from scripts.investment.resumable_perpetual import NativeDailySimulator
from scripts.investment.perpetual_directional import COSTS,UNITS


def utc(s):return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())*1000000


def phase(commit,prefix,name):
    path=prefix+'phases/'+name+'/'
    c=json.loads(git('show',commit+':'+path+'PUBLIC_RESTORE.json'))
    assert c['status'] in ('PASS_PUBLIC_RAW_MARK_MINUTE_COLD_RESTORE','PASS_PUBLIC_GAPPED_MARK_SOURCE_RESTORE','PASS_PUBLIC_GIT_OBJECT_RAW_MINUTE_COLD_RESTORE')
    artifact=c['artifact_commit'];index=git('show',artifact+':'+path+'SOURCE_INDEX.json');raw=git('show',artifact+':'+path+'RECOVERY.json')
    assert digest(index)==c['source_index_SHA256'] and digest(raw)==json.loads(index)['proof_SHA256']
    return bind_current(json.loads(raw),artifact),dict(commit=artifact,index_SHA256=digest(index),proof_SHA256=digest(raw))


def funding_sources(state,start,end):
    path=ROOT/'research/short-funding-residual-20261011/experiment.py'
    spec=importlib.util.spec_from_file_location('published_funding_source',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    raw=m.source_archive(ROOT,state);events=[];records=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        members=json.loads(z.read('MEMBERS.json'))['files']
        for s in SYMBOLS:
            name=f'source_tables_not_model_inputs/economics/{s}_funding_events.parquet';b=z.read(name)
            assert len(b)==members[name]['bytes'] and digest(b)==members[name]['SHA256']
            table=pq.read_table(io.BytesIO(b),columns=['calc_time_ms','last_funding_rate','funding_interval_hours'],
                filters=[('calc_time_ms','>=',start//1000),('calc_time_ms','<',end//1000)]).sort_by([('calc_time_ms','ascending')])
            f=table.to_pandas();ts=f.calc_time_ms.to_numpy(dtype=np.int64)*1000
            assert len(ts)==len(np.unique(ts)) and np.all((ts>=start)&(ts<end)) and np.isfinite(f.to_numpy()).all()
            assert len(f)==9,'Exactly three real days, actual original funding events required'
            for r in f.itertuples(index=False):events.append(dict(symbol=s,event_us=int(r.calc_time_ms)*1000,raw_rate=float(r.last_funding_rate),reported_interval_hours=float(r.funding_interval_hours)))
            records.append(dict(symbol=s,member=name,member_SHA256=digest(b),original_events=len(f),first_event_us=int(ts[0]),last_event_us=int(ts[-1])))
    events.sort(key=lambda r:(r['event_us'],r['symbol']))
    return events,dict(commit=m.SOURCE_COMMIT,archive_SHA256=m.ARCHIVE_SHA,members=records,raw_rate_unit='UNKNOWN; explicit RAW_AS_FRACTION compatibility scenario only')


def run(state,source,expected=None):
    assert not state.exists() and state.resolve().is_relative_to(Path('/workspace')) and not git('status','--porcelain')
    if expected is None:assert git('rev-parse','HEAD').decode().strip()==source
    for line in (HERE/'SOURCE_SHA256.txt').read_text().splitlines():
        sha,p=line.split(maxsplit=1);assert digest(git('show',source+':'+p))==digest((ROOT/p).read_bytes())==sha,p
    state.mkdir();configure(state,'REUSE_OCTNOV2022');start_clock=time.monotonic()
    protocol=json.loads((HERE/'PROTOCOL.json').read_text());start,end=utc('2022-10-01'),utc('2022-10-04')
    def bounded():
        assert time.monotonic()-start_clock<600 and shutil.disk_usage(state).free>=16106127360
        assert sum(p.stat().st_size for p in state.rglob('*') if p.is_file())<1000000000
    inv,_,_,_=inventories();treader=TradeReader(inv,state,local=False);mreader=MarkReader(inv,state,local=False)
    tp,tcert=phase(protocol['trade_source'],TRADE,'OCTNOV2022_REUSE');mp,mcert=phase(protocol['mark_source'],MARK,'REUSE_OCTNOV2022')
    from modules.collector_research.pipeline.normalize import month_limits
    left,right=month_limits(2022,10);trade={};mark={};oldframes={};certs=[];daily=[]
    for s in SYMBOLS:
        tr=next(r for r in tp['sources'] if r['source']['month']=='2022-10' and r['source']['symbol']==s)
        mr=next(r for r in mp['sources'] if r['source']['month']=='2022-10' and r['source']['symbol']==s)
        tc=[r for r in inv['reusable_price_archives'] if r['frequency']=='daily' and r['month']=='2022-10' and r['family']=='klines' and r['symbol']==s]
        mc=[r for r in inv['reusable_price_archives'] if r['frequency']=='daily' and r['month']=='2022-10' and r['family']=='markPriceKlines' and r['symbol']==s]
        tb,tf=composite_bars(treader,tr['source'],left,right,tc);mb,mf=composite_bars(mreader,mr['source'],left,right,mc)
        ot,_=decoded_month(treader,tr['source'],left,right);om,_=complete_month(mreader,mr['source'],left,right)
        np.testing.assert_array_equal(tf.to_numpy(),ot.to_numpy());np.testing.assert_array_equal(mf.to_numpy(),om.to_numpy())
        trade[s]=tb;mark[s]=mb;oldframes[s]=(ot,om)
        for at in range(start,end,DAY):
            price=tr['past_boundary']['close'] if at==start else float(tf.loc[tf.timestamp_ms==at//1000-60000,'close'].iloc[0])
            daily.append(dict(symbol=s,close_us=at,close=price))
        certs.append(dict(symbol=s,trade_manifest=json.loads(tb.provenance['manifest_json']),mark_manifest=json.loads(mb.provenance['manifest_json']),
            trade_receipts=list(tb.provenance['receipts']),mark_receipts=list(mb.provenance['receipts']),
            added_mark_rows=sum(r['added_actual_rows'] for r in mb.provenance['receipts'][1:]),
            minute_owner_SHA256=digest(mb.provenance['minute_owner_index'].tobytes()),minute_support_SHA256=digest(mb.provenance['minute_support_bits'].tobytes())))
        bounded();print('COMPOSITE_OCTOBER',s,len(tf),len(mf),'addedmark',certs[-1]['added_mark_rows'],flush=True)
    treader.close()
    target_raw=git('show',protocol['frozen_target_source']+':research/joint-correlation-risk-20261011/result/TARGETS.npz')
    with np.load(io.BytesIO(target_raw),allow_pickle=False) as a:
        assert tuple(a['symbol_order'])==SYMBOLS
        target_name=list(a['target_names']).index('BASE');ids=np.flatnonzero((a['decision_us']>=start)&(a['decision_us']<end))
        decisions=a['decision_us'][ids].copy();targets=a['targets'][ids,target_name].copy()
    np.testing.assert_array_equal(decisions,np.arange(start,end,DAY,dtype=np.int64))
    assert targets.shape==(3,5) and np.abs(targets).max()<=.3 and np.abs(targets).sum(1).max()<=.6
    events,funding_proof=funding_sources(state,start,end)
    def target_factory(daily,clocks,mode):
        np.testing.assert_array_equal(clocks,decisions)
        return pl.DataFrame([dict(available_us=int(at),symbol=s,target_weight=float(targets[i,j])) for i,at in enumerate(decisions) for j,s in enumerate(SYMBOLS)]),dict(kind='REUSED_FROZEN_BASE_TARGETS',archive_SHA256=digest(target_raw))
    def original_blocks():
        for at in range(start,end,DAY):
            market={};times=np.arange(at,at+DAY,MINUTE,dtype=np.int64)
            for s,(tf,mf) in oldframes.items():
                t=tf[(tf.timestamp_ms*1000>=at)&(tf.timestamp_ms*1000<at+DAY)];m=mf[(mf.timestamp_ms*1000>=at)&(mf.timestamp_ms*1000<at+DAY)]
                market[s]=dict(open=t.open.to_numpy(),close=t.close.to_numpy(),quote_volume=t.quote_volume.to_numpy(),mark=m.close.to_numpy())
            yield dict(times=times,market=market)
    def adapted_blocks():
        for at in range(start,end,DAY):yield legacy_projection(day_block(SYMBOLS,trade,mark,at))
    cases={};timings={}
    for name,blocks in [('OLD_CLOSE',original_blocks),('COMPOSITE_OHLC',adapted_blocks)]:
        begin=time.monotonic();window=dict(start=start,end=end,symbols=SYMBOLS,daily=pl.DataFrame(daily),events=events,minute_blocks=blocks)
        sim=NativeDailySimulator(window,'LONG_SHORT',COSTS[0],UNITS[0],target_factory=target_factory)
        while sim.cursor<end and sim.stop is None:sim.advance_day();bounded()
        result=sim.result();assert result['summary']['completion']=='COMPLETE_CONDITIONAL_ACCOUNT' and result['summary']['terminal_cash_realized']
        cases[name]=result;timings[name]=time.monotonic()-begin
        body={k:result[k] for k in ('summary','trades','funding','rejections','breaches','extrema','target_meta')}
        body['targets']=result['targets'].to_dicts();save(state/(name+'.json'),body)
        np.savez_compressed(state/(name+'.npz'),**{k:result['minute'][k].to_numpy() for k in result['minute'].columns})
        print('PAIRED_NATIVE_COMPATIBILITY',name,'4320minutes',timings[name],flush=True)
    for key in ('summary','trades','funding','rejections','breaches','extrema','target_meta'):assert cases['OLD_CLOSE'][key]==cases['COMPOSITE_OHLC'][key],key
    assert cases['OLD_CLOSE']['minute'].equals(cases['COMPOSITE_OHLC']['minute']) and cases['OLD_CLOSE']['targets'].equals(cases['COMPOSITE_OHLC']['targets'])
    # Known genuine July holes are inspected at their completion clocks, never
    # converted into prior-day selector masks or silently removed held periods.
    jp,jcert=phase(protocol['mark_source'],MARK,'Q32022');gap_reader=mreader;gaps=[]
    left,right=month_limits(2022,7)
    for s in SYMBOLS:
        row=next(r['source'] for r in jp['sources'] if r['source']['month']=='2022-07' and r['source']['symbol']==s)
        companions=[r for r in inv['reusable_price_archives'] if r['frequency']=='daily' and r['month']=='2022-07' and r['family']=='markPriceKlines' and r['symbol']==s]
        bars,_=composite_bars(gap_reader,row,left,right,companions)
        for ms in bars.provenance['missing_open_ms']:
            at=int(ms)*1000
            assert minute_observation(bars,at,at)['status']=='NOT_YET_KNOWN'
            status=minute_observation(bars,at,at+MINUTE);assert status['price'] is None and not status['path_certifiable']
            gaps.append(dict(symbol=s,missing_open_ms=int(ms),first_source_clock_detection_us=at+MINUTE,path_status='NOT_CERTIFIABLE_IF_OWNED_NO_POSTHOC_INTERVAL_DELETE'))
        bounded()
    gap_reader.close();assert len(gaps)==27
    report=dict(status='PASS_COMPOSITE_SOURCES_AND_SAME_KERNEL_CONDITIONAL_REPLAY',source_commit=source,
        source_certificates=dict(trade=tcert,mark=mcert,gapped_july=jcert,funding=funding_proof),composites=certs,
        frozen_targets=dict(commit=protocol['frozen_target_source'],archive_SHA256=digest(target_raw),selected_TARGET='BASE',decision_us=decisions.tolist(),targets=targets.tolist()),
        real_days=3,minutes_per_wallet=4320,wallets=2,old_wallets_rerun=0,complete_input_market_fields_and_all_account_outputs_exact=True,
        conditional_cost=COSTS[0],conditional_funding_unit=UNITS[0],actual_funding_events=45,
        scope='Finite input compatibility under unchanged conditional kernel. Not a new strategy profit/risk study or native charge/liquidation certification.',
        new_risk_semantics_enabled=False,extreme_tick_path_created=False,range_availability='Only after completed minute; intraminute order UNKNOWN',
        actual_gap_probes=gaps,remaining_real_holes=27,no_fill_or_trade_substitute=True,no_forward_missing_selector_mask=True,
        final_old_summary=cases['OLD_CLOSE']['summary'],case_seconds=timings,elapsed_seconds=time.monotonic()-start_clock,
        provider_downloads=0,fits=0,model_trials=0,labels=0,artifacts={p.name:digest(p.read_bytes()) for p in state.glob('OLD_CLOSE.*')})
    if expected:
        saved=json.loads(git('show',expected+':research/composite-mark-replay-20261011/result/RESULT.json'))
        for k in saved:
            if k not in ('case_seconds','elapsed_seconds'):assert saved[k]==report[k],k
        save(state/'PUBLIC_RESTORE.json',dict(status='PASS_PUBLIC_COMPOSITE_REPLAY_RESTORE',artifact_commit=expected,all_source_and_account_outputs_exact=True,
            provider_downloads=0,new_strategy_trials=0,wallet_compatibility_replays=2,elapsed_seconds=time.monotonic()-start_clock))
    save(state/'RESULT.json',report);print(json.dumps({k:report[k] for k in ('status','real_days','minutes_per_wallet','wallets','remaining_real_holes','elapsed_seconds')}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True);p.add_argument('--expected-commit')
    a=p.parse_args();run(a.state,a.source_commit,a.expected_commit)
