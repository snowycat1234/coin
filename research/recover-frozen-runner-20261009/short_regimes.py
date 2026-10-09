"""Three predeclared independent regime checks of the frozen short20/10 expert."""
import argparse
from datetime import datetime,UTC
import hashlib,json,os
from pathlib import Path
import resource,shutil,signal,socket,subprocess,sys,time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import native61 as frozen

CASES={
    'NOV2022':dict(start=1667260800000000,end=1669852800000000,days=30,venue='BINANCE_USDM_PROXY'),
    'JAN2023':dict(start=1672531200000000,end=1675209600000000,days=31,venue='BINANCE_USDM_PROXY'),
    'OKX86':dict(start=1784073600000000,end=1791504000000000,days=86,venue='OKX_PUBLIC_CONDITIONAL_ACCOUNT'),
}


def window(state,case):
    frozen.modules(state)
    spec=CASES[case]
    if case=='OKX86':
        import baseline
        root=state/'okx86/selected';index=baseline.shard_index(root)
        bars,_,_,events=baseline.daily_inputs(root)
        def blocks():
            for stamp in range(spec['start'],spec['end'],frozen.DAY):yield baseline.load_day(root,index,stamp)
        return dict(symbols=frozen.SYMBOLS,start=spec['start'],end=spec['end'],daily=bars,events=events,minute_blocks=blocks)
    from modules.collector_research.validation import runtime,data
    runtime.WORK=state/'e5-bear-original/original/bear_recovery_data';data.WORK=runtime.WORK
    return data.market_window(list(frozen.SYMBOLS),spec['start'],spec['end'])


def target_path(bars,spec):
    import numpy as np
    import polars as pl
    from scripts.investment import donchian_short_daily_pool_target as short
    from scripts.investment.regime_ranking_screen import bounded_path
    from scripts.research.conditional_selector_core import shared_targets
    decisions=np.arange(spec['start'],spec['end'],frozen.DAY,dtype=np.int64)
    if 'complete_kline' in bars.columns:bars=bars.filter(pl.col('complete_kline'))
    bars=bars.filter(pl.all_horizontal([pl.col(k).is_finite() for k in ('open','high','low','close','volume')])).select('symbol','open_us','close_us','available_us','open','high','low','close','volume')
    frame,meta=short.fixed_targets(bars,decisions,symbols=frozen.SYMBOLS)
    frozen.require(frame['eligibility_reason'].eq('ELIGIBLE').all(),'Missing genuine200-bar warmup; do not substitute flat')
    zero=frame.with_columns(pl.lit(0.).alias('target_weight'),pl.lit(0.).alias('raw_signed_target'))
    budgets=bounded_path(np.tile([0.,1.],(len(decisions),1)),[1.,0.],.1)
    targets,_=shared_targets({'CASH':zero,'DONCHIAN20_EXIT10_SHORT_ONLY':frame},('CASH','DONCHIAN20_EXIT10_SHORT_ONLY'),decisions,frozen.SYMBOLS,budgets)
    fractions=targets['target_weight'].to_numpy().reshape(len(decisions),5).copy();fractions[-1]*=0
    # Independent scalar prior windows, signal state and covariance risk.
    states=np.zeros(5,bool);raw=np.zeros((len(decisions),5));reference=np.zeros_like(raw);witnesses=[];warmups=[]
    histories={s:bars.filter(pl.col('symbol')==s).sort('close_us') for s in frozen.SYMBOLS}
    for i,t in enumerate(decisions):
        past=[]
        for j,s in enumerate(frozen.SYMBOLS):
            d=histories[s];clocks=d['close_us'].to_numpy();k=int(np.searchsorted(clocks,t));available=d['available_us'].to_numpy()
            frozen.require(k>=199 and clocks[k]==t and np.all(np.diff(clocks[k-199:k+1])==frozen.DAY) and (available[k-199:k+1]<=t).all(),'Incomplete causal200 bars')
            close=d['close'].to_numpy();prior_low=float(d['low'].to_numpy()[k-20:k].min());prior_high=float(d['high'].to_numpy()[k-10:k].max());before=bool(states[j])
            if states[j]:
                if close[k]>prior_high:states[j]=False
            elif close[k]<prior_low:states[j]=True
            raw[i,j]=-.12 if states[j] else 0.;past.append(np.diff(close[k-30:k+1])/close[k-30:k])
            witnesses.append(dict(decision_us=int(t),symbol=s,completed_close=float(close[k]),prior20_low=prior_low,prior10_high=prior_high,
                held_short_before=before,held_short_after=bool(states[j]),warmup_first_close_us=int(clocks[k-199]),maximum_input_available_us=int(available[k-199:k+1].max())))
            if i==0:warmups.append(dict(symbol=s,actual_contiguous_bars=200,first_close_us=int(clocks[k-199]),last_close_us=int(clocks[k]),maximum_available_us=int(available[k-199:k+1].max())))
        cov=np.cov(np.column_stack(past),rowvar=False,ddof=1)*365;sigma=float(np.sqrt(max(0,raw[i]@cov@raw[i])))
        reference[i]=raw[i]*min(1,.1/sigma) if sigma else raw[i]
    observed_raw=frame['raw_signed_target'].to_numpy().reshape(-1,5);observed=frame['target_weight'].to_numpy().reshape(-1,5)
    frozen.require(np.array_equal(raw,observed_raw) and np.max(abs(reference-observed))<=1e-14,'Independent frozen short state/risk mismatch')
    report=dict(status='PASS_CAUSAL200_FROZEN_SHORT_TARGETS',days=len(decisions),actual_asset_contexts=len(decisions)*5,
        warmup=warmups,target_sha256=hashlib.sha256(fractions.tobytes()).hexdigest(),budget_sha256=hashlib.sha256(budgets.tobytes()).hexdigest(),
        raw_state_maximum_error=0,covariance_target_maximum_error=float(abs(reference-observed).max()),raw_active_asset_days=int((raw<0).sum()),
        final_day_zero=True,maximum_gross_target=float(abs(fractions).sum(1).max()),maximum_asset_target=float(abs(fractions).max()))
    return fractions,budgets,meta,witnesses,report


def source_check():
    old=frozen.read(HERE/'DONCHIAN_SHORT61_PLAN.json')
    for n,d in old['source_sha256'].items():frozen.require(frozen.sha(frozen.REPO/n)==d,'Frozen short/financial source differs: '+n)


def check_case(state,case):
    import numpy as np
    source_check();spec=CASES[case]
    if case=='OKX86':
        import execute_wallet
        proof=execute_wallet.proof_check(state,frozen.read(HERE/'EXECUTION_PLAN.json'))
    else:
        root=state/'e5-bear-original/original/bear_recovery_data';m=frozen.read(root/'reports/DATASET_MANIFEST.json')
        frozen.require(frozen.sha(state/'e5-bear-original/coin_e5_bear_recovery_native_increment_20261008_v2.zip')=='98e38bc3f0e6a16fd51a63be880371882d4e2b52df1d8ec5a39963721d2d2bb8','Original public bear/recovery archive differs')
        for r in m['artifacts']:
            p=root/r['relative_path'];frozen.require(p.stat().st_size==r['bytes'] and frozen.sha(p)==r['sha256'],'Registered recovered market bytes differ')
        proof=dict(registered_files=len(m['artifacts']),manifest_sha256=frozen.sha(root/'reports/DATASET_MANIFEST.json'),minute_Parquets='EXACT_ORIGINAL_SHA_RECONSTRUCTED_FROM_PUBLISHED_OFFICIAL_ARCHIVES_OFFLINE')
    w=window(state,case);targets=target_path(w['daily'],spec)[4];count=0
    for block in w['minute_blocks']():
        stamps=block['times'];frozen.require(np.array_equal(stamps,np.arange(spec['start']+count*frozen.MINUTE,spec['start']+(count+len(stamps))*frozen.MINUTE,frozen.MINUTE,dtype=np.int64)),'Actual continuous minute clocks required')
        frozen.require(set(block['market'])==set(frozen.SYMBOLS),'Missing asset trade or mark minute; stop before wallet')
        for s,rows in block['market'].items():
            frozen.require(all(np.isfinite(a).all() and (a>=0 if k=='quote_volume' else a>0).all() for k,a in rows.items()),'Invalid actual minute values')
        count+=len(stamps)
    frozen.require(count==spec['days']*1440,'Incomplete required minute calendar')
    counts={s:sum(r['symbol']==s for r in w['events']) for s in frozen.SYMBOLS}
    frozen.require(all(n>0 for n in counts.values()) and len({(r['symbol'],r['event_us']) for r in w['events']})==len(w['events']),'Missing/duplicate actual funding calendar')
    return dict(status='PASS_FROZEN_SOURCE_GENUINE_CAUSAL_WARMUP_AND_COMPLETE_ACTUAL_MARKET',case=case,calendar=spec,
        targets=targets,source_proof=proof,minute_observations_per_asset=count,funding_events=len(w['events']),funding_per_asset=counts,
        provider_downloads=0,wallets_run=0,fits=0)


def run(state,case,output,commit):
    import numpy as np
    plan_path=HERE/'SHORT_REGIMES_PLAN.json';plan=frozen.read(plan_path)
    frozen.require(subprocess.check_output(['git','-C',str(frozen.REPO),'show',commit+':research/recover-frozen-runner-20261009/SHORT_REGIMES_PLAN.json'])==plan_path.read_bytes(),'Published regime plan required')
    for n,d in plan['source_sha256'].items():frozen.require(frozen.sha(frozen.REPO/n)==d,'Published source differs: '+n)
    check=check_case(state,case);frozen.require(check==frozen.read(HERE/'SHORT_REGIMES_PREFLIGHT.json')['cases'][case],'Published readiness differs')
    w=window(state,case);spec=CASES[case];fractions,budgets,meta,witnesses,_=target_path(w['daily'],spec)
    from scripts.investment import perpetual_directional as old
    from scripts.investment.resumable_perpetual import NativeDailySimulator
    from quant.bybit_isolated_account import BybitIsolatedAccount
    frozen.require(old.COSTS[0]==plan['cost'],'Frozen BASE27 cost differs')
    sim=NativeDailySimulator(w,'SHORT_ONLY',old.COSTS[0],dict(id='RAW_AS_FRACTION',scale=1.),account_factory=BybitIsolatedAccount,persist_cash_close=True,final_day_target_zero=True)
    sim.meta=meta;sim.budget=[1.,0.]
    frozen.require(float(sim.account.nav())==10000 and not output.exists(),'Fresh immutable account identity required');output.mkdir(parents=True,exist_ok=False)
    receipt=dict(policy='DONCHIAN20_EXIT10_SHORT_ONLY',case=case,calendar=spec,plan_commit=commit,started_UTC=datetime.now(UTC).isoformat(),limits=plan['limits'])
    (output/'STARTED.json').write_text(json.dumps(receipt,indent=2)+'\n');(output/'INDEPENDENT_SIGNAL_WITNESSES.json').write_text(json.dumps(witnesses,indent=2)+'\n')
    status='RUNNING';error=None;start=time.monotonic()
    def alarm(s,f):raise TimeoutError('600-second regime wallet cap')
    signal.signal(signal.SIGALRM,alarm);signal.setitimer(signal.ITIMER_REAL,600)
    try:
        for i in range(spec['days']):
            frozen.require(shutil.disk_usage(output).free>=15*2**30,'15GiB reserve required');sim.budget=budgets[i].tolist()
            frozen.require(sim.advance_day(dict(zip(frozen.SYMBOLS,fractions[i],strict=True)))['completed'],'Incomplete wallet must stop')
            frozen.require(all(p.quantity<=0 for p in sim.account.positions.values()),'Forbidden long inventory')
            if (i+1)%10==0 or i+1==spec['days']:print(json.dumps(dict(case=case,completed_days=i+1,total_days=spec['days'],NAV=float(sim.account.nav()))),flush=True)
        frozen.require(sim.rows_written==spec['days']*1440 and all(p.quantity==0 for p in sim.account.positions.values()),'Complete paid-flat account required');status='COMPLETE_CONDITIONAL_ACCOUNT'
    except BaseException as e:
        status='FAILED_PREFIX_RETAINED';error=dict(type=type(e).__name__,message=str(e));raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);saved=old.save_case(sim.result(),output/'account');(output/'account/summary.json').write_text(json.dumps(saved['summary'],indent=2)+'\n')
        receipt.update(status=status,error=error,finished_UTC=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            completed_minutes=sim.rows_written,original_engine_sha256=frozen.sha(frozen.REPO/'scripts/investment/resumable_perpetual.py'),audit='PENDING_POSTRUN_INDEPENDENT_RECONCILIATION')
        (output/'EXECUTION.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:saved['summary'][k] for k in ('NAV','net_PnL','gross_PnL_same_quantities','fees_USDT','execution_cost_USDT','funding_USDT','trade_legs','terminal_cash_realized')}),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('check','run'));p.add_argument('--case',choices=CASES,required=True)
    p.add_argument('--state',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--plan-commit');a=p.parse_args()
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','POLARS_MAX_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6000000000,6000000000));resource.setrlimit(resource.RLIMIT_CPU,(600,600))
    def blocked(*a,**kw):raise RuntimeError('Offline regime research forbids network')
    socket.create_connection=blocked;socket.socket.connect=blocked
    if a.command=='check':
        r=check_case(a.state,a.case);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
    else:run(a.state,a.case,a.output,a.plan_commit)


if __name__=='__main__':main()
