"""Eight new Donchian2h accounts; frozen independent finances, new signal oracle.

No producer fixed_targets/simulate/account finance import, old account replay,
source QA or funding-unit certification. ACTUAL_BINDING is frozen after the
producer closes. July2h is signal warmup; covariance remains completed daily.
"""
from __future__ import annotations
import argparse, gc, hashlib, importlib.util, json, math, os, resource, sys, time
from datetime import UTC, datetime
from pathlib import Path
import numpy as np
import polars as pl
from quant import resources

ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
BASE='docs/archive/PERPETUAL_DIRECTIONAL_INDEPENDENT_AUDITOR_20261003_V1.py'
BASE_SHA='1c4b0bcb0b4dd954ae4cdb7f12b64426f2244ba554340ee23e7d73ddbac5c7bb'
HOOK='docs/archive/PUBLIC_DONCHIAN_DAILY_INDEPENDENT_TARGET_SOURCE_20261003_V1.py'
HOOK_SHA='3a944f46e89600c90886053376fe2224683664e30985f3a11b089d0fd51a4d85'
ACCOUNT_SHA='cf47ae9b889eab4506be2b22929322976a6833235eaab6459399bdec53de2261'
PROGRESS_PINS={
    'scripts/research_v8/funding_price_source_v2.py':'2f39c9803051373654094ee990474b3ebe9b241ef85fa9eb586b9bde92bb4cdb',
    'scripts/research_v7/oracle_flow_ceiling.py':'959f63f40c3294b6b2b75267b9138202df79223a7e7723397cf06b8d45a1477e'}
ACTUAL_STATUS='COMPLETE_D041_CONDITIONAL_PUBLIC_DONCHIAN_PERPETUAL_BENCHMARK_NOT_NATIVE_OR_LONG_TERM_APR'
STATUS='PASS_D041_EIGHT_PUBLIC_DONCHIAN_LONG_ONLY_PERPETUAL_ACCOUNTS_AND_2H_CAUSAL_SCOPE_NOT_NATIVE_OR_LONG_TERM_APR'
FAIL='FAIL_D041_PUBLIC_DONCHIAN_PERPETUAL_INDEPENDENT_AUDIT'
STRATEGY_ID='COIN_JESSE_DONCHIAN_2H_USDT_PERPETUAL_ADAPTER'
MIN=60_000_000;BAR=120*MIN;DAY=1440*MIN
JULY=1751328000000000;AUGUST=1754006400000000
SYMS=('BTCUSDT','ETHUSDT')
SELECTORS=[f'{p}_LONG_ONLY_{c}_{u}' for p in ('122D','90D')
    for c in ('BASE27','STRESS43') for u in ('RAW_AS_FRACTION','RAW_AS_PERCENT')]
BUDGET=dict(wall_seconds=1200,peak_RSS_bytes=1500000000,new_owned_bytes=5000000)

def need(ok,reason):
    if not bool(ok):raise ValueError(reason)

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def module(path,name,digest):
    p=ROOT/path;need(sha(p)==digest and not p.is_symlink(),'Exact accepted independent source '+path)
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m);return m

def proof(item):
    return dict(path=item.get('path',item.get('normalized_path')),
        sha256=item.get('sha256',item.get('normalized_sha256')),
        bytes=item.get('bytes',item.get('normalized_bytes')),rows=item['rows'])

def proof_set(items):
    rows=[proof(x) for x in items]
    need(len({r['path'] for r in rows})==len(rows),'No repeated signal source identities')
    return sorted(rows,key=lambda r:r['path'])

def signal_reader(b,manifest,july_receipt,w):
    """Only necessary accepted OHLCV columns, full Aug-to-end for90d warmup.

    Independent Polars complete120-minute aggregation. No raw ZIP, old QA,
    mark/index/funding signal, provider aggregation or fixed_targets call.
    """
    fields=['symbol','open_us','close_us','available_us','open','high','low','close','volume']
    july_items=july_receipt['sources'];need(len(july_items)==2,'Two July2h warmup archives only')
    all_frames=[];proofs=[]
    for s in SYMS:
        source=next(x for x in july_items if x['symbol']==s)
        need(source['interval']=='2h' and source['month']=='2025-07' and source['rows']==372,'Fixed full July2h warmup')
        p=b.payload(source);warm=pl.read_parquet(p,columns=fields).sort('open_us');proofs.append(proof(source))
        need(warm['symbol'].eq(s).all() and np.array_equal(warm['open_us'],np.arange(JULY,AUGUST,BAR,dtype=np.int64)),
            'Every paired July2h signal bar, no shorter or selected warmup')
        identities=[]
        for window in manifest['windows']:
            for identity in window['symbols'][s]['source_ids']['trade_1m']:
                item=manifest['source_files'][identity]
                if item['month']<=datetime.fromtimestamp((w['end']-1)/1e6,UTC).strftime('%Y-%m'):
                    identities.append(identity)
        identities=list(dict.fromkeys(identities));frames=[]
        for identity in identities:
            item=manifest['source_files'][identity];p=b.payload(item)
            frames.append(pl.read_parquet(p,columns=fields));proofs.append(proof(item))
        minutes=pl.concat(frames,how='vertical').sort('open_us')
        need(minutes['symbol'].eq(s).all() and np.array_equal(minutes['open_us'],np.arange(AUGUST,w['end'],MIN,dtype=np.int64)),
            'Signal includes all Aug-to-end minutes, including pre-Dec90d warmup')
        need(not minutes.null_count().select(pl.sum_horizontal(pl.all())).item()
            and np.isfinite(minutes.select('open','high','low','close','volume').to_numpy()).all(),
            'Aggregation may not conceal unknown or nonfinite signal primitives')
        need(minutes['close_us'].eq(minutes['open_us']+MIN).all()
            and minutes['available_us'].ge(minutes['close_us']).all(),'Known completed-minute signal availability')
        grouped=minutes.with_columns((pl.col('open_us')//BAR*BAR).alias('bar_open')).group_by('bar_open',maintain_order=True).agg(
            pl.len().alias('count'),pl.col('open_us').first().alias('first'),pl.col('open_us').last().alias('last'),
            pl.col('available_us').max(),pl.col('open').first(),pl.col('high').max(),pl.col('low').min(),
            pl.col('close').last(),pl.col('volume').sum())
        need(grouped['count'].eq(120).all() and grouped['first'].eq(grouped['bar_open']).all()
            and grouped['last'].eq(grouped['bar_open']+BAR-MIN).all(),'Full120 complete minute bars without dropping gaps')
        scored=grouped.select(pl.lit(s).alias('symbol'),pl.col('bar_open').alias('open_us'),
            (pl.col('bar_open')+BAR).alias('close_us'),'available_us','open','high','low','close','volume')
        all_frames.append(pl.concat([warm,scored],how='vertical').sort('close_us'))
        del minutes,grouped,frames;gc.collect()
    return pl.concat(all_frames,how='vertical'),proof_set(proofs)

def target_reference(b,w,signal,hook_module):
    """Independent scalar prior20/current200 hooks +30 completed daily returns."""
    Public=hook_module.original_rules();times=np.arange(w['start'],w['end'],BAR,dtype=np.int64)
    context={};state=dict.fromkeys(SYMS,False);rows=[];witness=[]
    for s in SYMS:
        frame=signal.filter(pl.col('symbol')==s).sort('close_us')
        need(all(frame.schema[k]==pl.Int64 and frame[k].null_count()==0 for k in ('open_us','close_us','available_us')),
            'Known integer signal timestamps')
        values=frame.select('open','close','high','low','volume').to_numpy()
        need(np.isfinite(values).all() and np.all(values[:,:4]>0) and np.all(values[:,4]>=0)
            and np.all(values[:,3]<=np.minimum(values[:,0],values[:,1])) and np.all(values[:,2]>=np.maximum(values[:,0],values[:,1])),
            'Finite coherent actual signal OHLCV')
        stamps=frame['close_us'].to_numpy();available=frame['available_us'].to_numpy()
        need(np.array_equal(stamps,frame['open_us'].to_numpy()+BAR) and np.all(np.diff(stamps)==BAR)
            and np.all(stamps%BAR==0) and np.all(available>=stamps),'Complete UTC2h exclusiveclose availability')
        context[s]=(stamps,available,np.column_stack((frame['open_us'].to_numpy()/1000,values)))
    for t in times:
        raw=[];returns=[];local=[]
        for s in SYMS:
            stamps,available,candles=context[s];i=int(np.searchsorted(stamps,t,side='right')-1)
            need(i>=199 and stamps[i]==t and np.all(available[i-199:i+1]<=t),'200 completed consecutive available2h bars')
            selected=candles[i-199:i+1];close=float(selected[-1,2])
            upper=max(map(float,selected[-21:-1,3]));lower=min(map(float,selected[-21:-1,4]))
            mean=math.fsum(map(float,selected[:,2]))/200
            entry=close>upper and close>mean;exit_=close<lower
            rules=Public();rules.candles=selected;rules.close=close;rules.is_long=state[s];rules.is_short=False
            closed=[];rules.liquidate=lambda:closed.append(True)
            need(rules.should_short() is False and (rules.should_long() and all(f() for f in rules.filters()))==entry,
                'Original strict Donchian/filter hooks match independent scalar arithmetic')
            rules.update_position();need(bool(closed)==exit_,'Original strict lower-channel held exit')
            before=state[s]
            if before:
                if exit_:state[s]=False
            elif entry:state[s]=True
            raw.append(.3 if state[s] else 0.)
            daily=w['bars'][s];day=int(t)//DAY*DAY;j=int(np.searchsorted(daily['close_us'].to_numpy(),day,side='right')-1)
            need(j>=30 and daily['close_us'][j]==day and np.all(np.diff(daily['close_us'][j-30:j+1])==DAY)
                and np.all(daily['available_us'][j-30:j+1].to_numpy()<=t),'Separate31 completed available UTCdaily prices for30 risk returns')
            prices=daily['close'][j-30:j+1].to_numpy();returns.append(np.diff(prices)/prices[:-1])
            local.append(dict(decision_us=int(t),symbol=s,signal_close=close,previous20_upper=upper,previous20_lower=lower,
                SMA200=mean,held_before=before,held_after=state[s],risk_last_completed_day_us=day,
                maximum_signal_available_us=int(available[i-199:i+1].max()),maximum_daily_available_us=int(daily['available_us'][j-30:j+1].max())))
        r=np.column_stack(returns);center=r-r.mean(axis=0);cov=center.T@center/29*365
        weights=np.asarray(raw);sigma=math.sqrt(max(float(weights@cov@weights),0.))
        if sigma>.10:weights=weights*(.10/sigma)
        for s,weight,direction,info in zip(SYMS,weights,raw,local,strict=True):
            rows.append((int(t),s,float(weight),float(direction),'LONG_ONLY'));witness.append(info)
    return pl.DataFrame(rows,schema=['available_us','symbol','target_weight','raw_signed_target','mode'],orient='row'),witness

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('protocol','actual','run-dir','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();b=module(BASE,'d041_independent_financial',BASE_SHA)
    g=b.module(b.GUARD,'d041_guards',b.GUARD_SHA);hand=b.module(b.REFERENCE,'d041_hand',b.REFERENCE_SHA)
    hook=module(HOOK,'d041_independent_raw_donchian',HOOK_SHA)
    need(os.getenv('COIN_TASK_ID') and sys.prefix==str(STATE/'v8-clean-env-20261002-v2') and pl.thread_pool_size()<=2,'Bounded clean CPU2 task')
    need(a.run_dir.parent==STATE and a.run_dir.is_dir() and not a.run_dir.is_symlink()
        and {x.name for x in a.run_dir.iterdir()}=={'ACTUAL_BINDING.json'}
        and a.output.parent==ROOT/'reports/fast_research' and not a.output.exists(),'Fresh manifest-only audit paths')
    plan,plan_sha=g.small(a.run_dir/'ACTUAL_BINDING.json');own=sha(__file__)
    need(plan['ready_to_execute'] is True and plan['checker_sha256']==own and plan['protocol_path']==str(a.protocol.relative_to(ROOT))
        and plan['actual_report']==str(a.actual.relative_to(ROOT)) and plan['budgets']==BUDGET
        and plan['tolerances']==dict(cash_USDT=b.CASH_TOL,ratio=b.RATIO_TOL),'Prebound exact invocation/budget/original tolerances')
    binding=dict(task_id=os.environ['COIN_TASK_ID'],checker_sha256=own,ACTUAL_BINDING_sha256=plan_sha,
        actual_reports={str(a.actual):plan['actual_report_sha256']},source_hashes=plan['source_hashes'])
    g.write(a.run_dir/'RUN_BINDING.json',binding);started=time.monotonic();before=resources.status();rows=[];maximum=dict(cash=0.,ratio=0.)
    report=dict(status=FAIL,binding=binding,run_dir=str(a.run_dir),run_binding_sha256=sha(a.run_dir/'RUN_BINDING.json'),
        independent_source_sha256=own,cases=rows,tolerances=plan['tolerances'],maximum_errors=maximum,
        financial_method='EXACT_1C4B_AUDIT_CASE_REUSE_PLUS_NEW_SCALAR_RAW_DONCHIAN_2H_REFERENCE',
        funding_rate_unit='UNCONFIRMED',unit_certified=False,native_market_certified=False,long_term_APR='NOT_EVALUABLE',
        candidate='NO_QUALIFIED_CANDIDATE',old_financial_accounts_replayed=False,source_QA_repeated=False,
        full_market_frozen_order_quantity_sizing_independently_rebuilt=False,models_fit=0,orders_sent=0,GPU=0,locked_consumed=False)
    error=None;progress=None
    try:
        g.bounded(before);spec,proto_sha=g.small(a.protocol,plan['protocol_sha256']);actual,actual_sha=g.small(a.actual,plan['actual_report_sha256'])
        need(spec['contract_id']=='D041_PUBLIC_DONCHIAN_TWO_HOUR_PERPETUAL_BENCHMARK_20261003_V1'
            and actual['status']==ACTUAL_STATUS and actual['required_cases']==actual['completed_cases']==8
            and actual['binding']['task_id']==plan['actual_task_id'] and actual['binding']['protocol_sha256']==proto_sha
            and actual['binding']['source_hashes']==spec['frozen_sources'] and actual['unit_certified'] is False
            and actual['native_market_certified'] is False,'Eight actual fixed conditional scenarios')
        report['actual_task']=g.closed(plan['actual_task_id']);run=Path(spec['run_dir'])
        rb,rb_sha=g.small(run/'RUN_BINDING.json',actual['run_binding_sha256']);need(rb==actual['binding'],'Exact actual producer RUN_BINDING')
        hashes={str(a.protocol.relative_to(ROOT)):proto_sha,str(a.actual.relative_to(ROOT)):actual_sha}
        for path,digest in [(BASE,BASE_SHA),(HOOK,HOOK_SHA),(b.GUARD,b.GUARD_SHA),(b.REFERENCE,b.REFERENCE_SHA)]:
            need(plan['source_hashes'].get(path)==digest,'All imported independent functions explicitly pinned')
        need(all(plan['source_hashes'].get(p)==h for p,h in PROGRESS_PINS.items()),'Progress-only dependency explicitly bound')
        need(spec['frozen_sources']['src/quant/perpetual_account.py']==ACCOUNT_SHA,'Accepted exact-settlement account source')
        for path,digest in [*spec['frozen_sources'].items(),*plan['source_hashes'].items()]:
            need(path not in hashes or hashes[path]==digest,'No conflicting source pins');g.small(b.project(g,path),digest,False);hashes[path]=digest
        need(all(spec['rules'][k]==v for k,v in dict(initial_capital_USDT=10000.,annual_vol_target=.10,
            past_covariance_completed_days=30,asset_abs_cap=.3,gross_cap=.6,leverage=1,MMR=.005,sizing_buffer=.99,
            taker_fee_bps_per_side=5.5,participation_rate=.001,maximum_attempts=5).items()),'Same capital/risk/cost/capacity')
        need([(c['id'],c['half_spread_bps'],c['slippage_bps'],c['roundtrip_bps']) for c in spec['cost_scenarios']]==[(k,*v) for k,v in b.COSTS.items()]
            and [(u['id'],b.dec(u['scale'])) for u in spec['unit_scenarios']]==list(b.UNITS.items()),'Two fixed cost and unconfirmed unit scenarios')
        need([c['id'] for c in actual['cases']]==SELECTORS and all(c['mode']=='LONG_ONLY' for c in actual['cases']),
            'Exactly eight long-only selectors without result selection')
        mref=spec['input_manifest'];manifest,_=g.small(b.project(g,mref['path']),mref['sha256'])
        need(manifest['funding_rate_unit']=='UNCONFIRMED' and not manifest['funding_unit_certified'],'No unit certification')
        jref=spec['july_signal_source_receipt'];july,_=g.small(b.project(g,jref['path']),jref['sha256'])
        need(july['status']==jref['required_status'],'Exact new July signal-source format receipt');report['july_source_task']=g.closed(july['binding']['task_id'])
        for key in ('july_signal_independent_receipt','original_root'):
            receipt_ref=spec[key];receipt,_=g.small(b.project(g,receipt_ref['path']),receipt_ref['sha256'])
            need(receipt['status']==receipt_ref['required_status'],'Actual accepted prerequisite '+key)
            report[key+'_task']=g.closed(receipt['binding']['task_id'])
        smoke_ref=spec['required_new_tests'];smoke,_=g.small(b.project(g,smoke_ref['path']),smoke_ref['sha256'])
        need(smoke['status']==smoke_ref['required_status'] and smoke['test_exit_code']==0 and smoke['source_bytes_unchanged'] is True,'Sole new causality/controller route receipt')
        report['synthetic_task']=g.closed(smoke['binding']['task_id'])
        from scripts.research_v8.funding_price_source_v2 import progress_writer
        progress=progress_writer(8)
        need(len(actual['input_windows'])==len(manifest['windows'])==2,'Exactly two fixed source windows')
        for window_spec,inputs in zip(manifest['windows'],actual['input_windows'],strict=True):
            w=b.window_reader(manifest,window_spec)
            need(inputs['id']==window_spec['id'] and inputs['input_proofs']==w['proofs'],'Same accepted necessary financial inputs')
            signal,source_proofs=signal_reader(b,manifest,july,w)
            need(proof_set(inputs['signal_source_proofs'])==source_proofs,'Exact original July2h and all Aug-to-end signal-source identities')
            feature=inputs['feature_receipt'];need(feature['rows']==signal.height and feature['interval_us']==BAR
                and feature['begin_us']==JULY and feature['end_exclusive_us']==w['end'] and feature['raw_source_QA_repeated'] is False,
                'Complete independently reconstructed signal feature calendar')
            target,witness=target_reference(b,w,signal,hook)
            for case in [c for c in actual['cases'] if c['period']==window_spec['id']]:
                progress.update('原Donchian2h · 新八账户独立因果与资金',len(rows),8,'账户',selector=case['id'])
                item=b.audit_case(w,case,g,hand,run,target,witness,maximum)
                need(item['complete_calendar_verified'] and b.exact(case['summary'],'unpaid_liability')==0,
                    'Every planned new account is complete with no unpaid debt')
                item['signal_reference']=dict(strategy_id=STRATEGY_ID,decision_rows=target.height,
                    timeframe_minutes=120,raw_hooks_pinned=True,independent_scalar_prior20_current200=True,
                    daily_covariance_observations=30,warmup_positions=False,source_proofs=source_proofs,
                    closed_bar_proxy_is_not_publication_certification=True)
                rows.append(item);gc.collect()
                need(time.monotonic()-started<=1200 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=1500000000,'Fixed audit process budget')
            del w,signal,target,witness;gc.collect()
        for path,digest in hashes.items():g.small(b.project(g,path),digest,False)
        report.update(status=STATUS,verified_source_hashes=hashes,actual_report_sha256=actual_sha,actual_run_binding_sha256=rb_sha,
            required_cases=8,completed_cases_verified=8,completed_full_calendar_cases_verified=sum(c['complete_calendar_verified'] for c in rows),
            incomplete_or_halted_cases_verified=sum(not c['complete_calendar_verified'] for c in rows),
            original32_and_corrected2_financial_replayed=False,realized_risk_matched_claimed=False)
    except Exception as caught:error=caught;report['failure']=dict(type=type(caught).__name__,reason=str(caught))
    finally:
        if progress:progress.stop.set();progress.thread.join(timeout=3)
        report.update(completed_cases_verified=len(rows),elapsed_seconds=time.monotonic()-started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            resources_before=before,resources_after=resources.status(),own_completion='LIVE_CALLER_NOT_SELF_CERTIFIED')
        try:g.bounded(report['resources_after'])
        except Exception as caught:error=error or caught;report['budget_error']=str(caught)
        if report['elapsed_seconds']>1200 or report['peak_RSS_bytes']>1500000000:error=error or RuntimeError('Fixed audit process budget')
        if error:report['status']=FAIL
        digest,size=g.write(a.output,report);need(sum(p.stat().st_size for p in a.run_dir.iterdir() if p.is_file())+size<=5000000,'Small metadata output budget')
        print(json.dumps(dict(status=report['status'],sha256=digest,completed_cases=len(rows))),flush=True)
    if error:raise error

if __name__=='__main__':main()
