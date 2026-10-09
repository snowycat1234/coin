"""One fixed30-day absolute-momentum short rule over four predeclared windows."""
import argparse
from datetime import datetime,UTC
import hashlib,json,os
from pathlib import Path
import resource,shutil,signal,socket,subprocess,sys,time
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import native61 as frozen
import short_regimes
CASES={'MAYJUN2024':dict(start=frozen.START,end=frozen.END,days=61,venue='BINANCE_USDM_PROXY'),**short_regimes.CASES}


def window(state,case):
    return frozen.market(state) if case=='MAYJUN2024' else short_regimes.window(state,case)


def source_check():
    short_regimes.source_check()
    frozen.require(frozen.sha(frozen.REPO/'scripts/investment/momentum_cash_pool_target.py')=='9f2fe9aae324db2e5ccbcca0ca843b8612625f2aba1cece6937f5db09cb586a4','Established30-day momentum source differs')


def market_proof(state,case):
    source_check()
    if case=='OKX86':
        import execute_wallet
        return execute_wallet.proof_check(state,frozen.read(HERE/'EXECUTION_PLAN.json'))
    root=state/('h1_validation/original/h1_market' if case=='MAYJUN2024' else 'e5-bear-original/original/bear_recovery_data')
    m=frozen.read(root/'reports/DATASET_MANIFEST.json')
    expected=frozen.read(HERE/'NATIVE61_PLAN.json')['public_input']['data_manifest_sha256'] if case=='MAYJUN2024' else frozen.read(HERE/'SHORT_REGIMES_PREFLIGHT.json')['cases'][case]['source_proof']['manifest_sha256']
    frozen.require(frozen.sha(root/'reports/DATASET_MANIFEST.json')==expected,'Frozen source manifest differs')
    for r in m['artifacts']:
        p=root/r['relative_path'];frozen.require(p.stat().st_size==r['bytes'] and frozen.sha(p)==r['sha256'],'Retained actual market bytes differ')
    return dict(registered_files=len(m['artifacts']),manifest_sha256=expected,minute_completeness='REUSED_PREVIOUS_EXACT_INPUT_GRID_PROOF_WITH_CURRENT_IDENTICAL_SOURCE_BYTES')


def targets(bars,spec):
    import numpy as np
    import polars as pl
    from scripts.investment import momentum_short_pool_target as short
    from scripts.investment.regime_ranking_screen import bounded_path
    from scripts.research.conditional_selector_core import shared_targets
    if 'complete_kline' in bars.columns:bars=bars.filter(pl.col('complete_kline'))
    bars=bars.filter(pl.all_horizontal([pl.col(k).is_finite() for k in ('open','high','low','close','volume')])).select('symbol','open_us','close_us','available_us','open','high','low','close','volume')
    tt=np.arange(spec['start'],spec['end'],frozen.DAY,dtype=np.int64);frame,meta=short.fixed_targets(bars,tt,symbols=frozen.SYMBOLS)
    frozen.require(frame['eligibility_reason'].eq('ELIGIBLE').all(),'Missing actual200-bar context; no substitution')
    zero=frame.with_columns(pl.lit(0.).alias('target_weight'),pl.lit(0.).alias('raw_signed_target'))
    budgets=bounded_path(np.tile([0.,1.],(len(tt),1)),[1.,0.],.1)
    combined,_=shared_targets({'CASH':zero,'MOMENTUM30_SHORT_ONLY':frame},('CASH','MOMENTUM30_SHORT_ONLY'),tt,frozen.SYMBOLS,budgets)
    fractions=combined['target_weight'].to_numpy().reshape(-1,5).copy();fractions[-1]*=0
    states=np.zeros(5,bool);raw=np.zeros((len(tt),5));reference=np.zeros_like(raw);witnesses=[]
    histories={s:bars.filter(pl.col('symbol')==s).sort('close_us') for s in frozen.SYMBOLS}
    for i,t in enumerate(tt):
        past=[]
        for j,s in enumerate(frozen.SYMBOLS):
            d=histories[s];clock=d['close_us'].to_numpy();k=int(np.searchsorted(clock,t));available=d['available_us'].to_numpy()
            frozen.require(k>=199 and clock[k]==t and np.all(np.diff(clock[k-199:k+1])==frozen.DAY) and (available[k-199:k+1]<=t).all(),'Genuine causal200-bar warmup required')
            c=d['close'].to_numpy();before=bool(states[j])
            if states[j]:
                if c[k]>=c[k-30]:states[j]=False
            elif c[k]<c[k-30]:states[j]=True
            raw[i,j]=-.12 if states[j] else 0.;past.append(np.diff(c[k-30:k+1])/c[k-30:k])
            witnesses.append(dict(decision_us=int(t),symbol=s,current_completed_close=float(c[k]),close_30_days_earlier=float(c[k-30]),
                held_short_before=before,held_short_after=bool(states[j]),warmup_first_close_us=int(clock[k-199]),maximum_input_available_us=int(available[k-199:k+1].max())))
        cov=np.cov(np.column_stack(past),rowvar=False,ddof=1)*365;sigma=float(np.sqrt(max(0,raw[i]@cov@raw[i])))
        reference[i]=raw[i]*min(1,.1/sigma) if sigma else raw[i]
    actual_raw=frame['raw_signed_target'].to_numpy().reshape(-1,5);actual=frame['target_weight'].to_numpy().reshape(-1,5)
    frozen.require(np.array_equal(raw,actual_raw) and abs(actual-reference).max()<=1e-14,'Independent30-day signal/state/risk mismatch')
    report=dict(status='PASS_FIXED30_DAY_MOMENTUM_CAUSAL200_INDEPENDENT_STATE_AND_RISK',days=len(tt),asset_contexts=len(tt)*5,
        target_sha256=hashlib.sha256(fractions.tobytes()).hexdigest(),budget_sha256=hashlib.sha256(budgets.tobytes()).hexdigest(),
        raw_state_maximum_error=0,covariance_target_maximum_error=float(abs(actual-reference).max()),raw_active_asset_days=int((raw<0).sum()),
        maximum_gross_target=float(abs(fractions).sum(1).max()),maximum_asset_target=float(abs(fractions).max()),final_day_zero=True)
    return fractions,budgets,meta,witnesses,report


def check(state,case):
    frozen.modules(state);proof=market_proof(state,case);w=window(state,case);spec=CASES[case]
    return dict(status='PASS_REUSED_EXACT_ACTUAL_MARKET_AND_NEW_FIXED_MOMENTUM_TARGETS',case=case,calendar=spec,
        source_proof=proof,targets=targets(w['daily'],spec)[4],actual_funding_events=len(w['events']),provider_downloads=0,wallets_run=0,fits=0)


def run(state,case,output,commit):
    plan_path=HERE/'MOMENTUM_SHORT_PLAN.json';plan=frozen.read(plan_path)
    frozen.require(subprocess.check_output(['git','-C',str(frozen.REPO),'show',commit+':research/recover-frozen-runner-20261009/MOMENTUM_SHORT_PLAN.json'])==plan_path.read_bytes(),'Published one-recipe/four-window plan required')
    for n,d in plan['source_sha256'].items():frozen.require(frozen.sha(frozen.REPO/n)==d,'Published source differs: '+n)
    frozen.require(check(state,case)==frozen.read(HERE/'MOMENTUM_SHORT_PREFLIGHT.json')['cases'][case],'Published readiness differs')
    w=window(state,case);spec=CASES[case];fractions,budgets,meta,witnesses,_=targets(w['daily'],spec)
    from scripts.investment import perpetual_directional as old
    from scripts.investment.resumable_perpetual import NativeDailySimulator
    from quant.bybit_isolated_account import BybitIsolatedAccount
    frozen.require(old.COSTS[0]==plan['cost'],'Frozen cost differs')
    sim=NativeDailySimulator(w,'SHORT_ONLY',old.COSTS[0],dict(id='RAW_AS_FRACTION',scale=1.),account_factory=BybitIsolatedAccount,persist_cash_close=True,final_day_target_zero=True)
    sim.meta=meta;sim.budget=[1.,0.]
    frozen.require(float(sim.account.nav())==10000 and not output.exists(),'Fresh immutable account identity required');output.mkdir(parents=True,exist_ok=False)
    receipt=dict(policy='MOMENTUM30_SHORT_ONLY',case=case,calendar=spec,plan_commit=commit,started_UTC=datetime.now(UTC).isoformat(),limits=plan['limits'])
    (output/'STARTED.json').write_text(json.dumps(receipt,indent=2)+'\n');(output/'INDEPENDENT_SIGNAL_WITNESSES.json').write_text(json.dumps(witnesses,indent=2)+'\n')
    status='RUNNING';error=None;start=time.monotonic()
    def alarm(s,f):raise TimeoutError('600-second momentum-short wallet cap')
    signal.signal(signal.SIGALRM,alarm);signal.setitimer(signal.ITIMER_REAL,600)
    try:
        for i in range(spec['days']):
            frozen.require(shutil.disk_usage(output).free>=15*2**30,'15GiB reserve required');sim.budget=budgets[i].tolist()
            frozen.require(sim.advance_day(dict(zip(frozen.SYMBOLS,fractions[i],strict=True)))['completed'],'Incomplete wallet must stop')
            frozen.require(all(p.quantity<=0 for p in sim.account.positions.values()),'Forbidden long inventory')
            if (i+1)%10==0 or i+1==spec['days']:print(json.dumps(dict(case=case,completed_days=i+1,total_days=spec['days'],NAV=float(sim.account.nav()))),flush=True)
        frozen.require(sim.rows_written==spec['days']*1440 and all(p.quantity==0 for p in sim.account.positions.values()),'Complete paid-flat account required');status='COMPLETE_CONDITIONAL_ACCOUNT'
    except BaseException as e:status='FAILED_PREFIX_RETAINED';error=dict(type=type(e).__name__,message=str(e));raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);saved=old.save_case(sim.result(),output/'account');(output/'account/summary.json').write_text(json.dumps(saved['summary'],indent=2)+'\n')
        receipt.update(status=status,error=error,finished_UTC=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            completed_minutes=sim.rows_written,original_engine_sha256=frozen.sha(frozen.REPO/'scripts/investment/resumable_perpetual.py'),audit='PENDING_POSTRUN_INDEPENDENT_RECONCILIATION',selected_after_seeing_June2024=True)
        (output/'EXECUTION.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:saved['summary'][k] for k in ('NAV','net_PnL','gross_PnL_same_quantities','fees_USDT','execution_cost_USDT','funding_USDT','trade_legs','terminal_cash_realized')}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('check','run'));p.add_argument('--case',choices=CASES,required=True)
    p.add_argument('--state',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--plan-commit');a=p.parse_args()
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','POLARS_MAX_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6000000000,6000000000));resource.setrlimit(resource.RLIMIT_CPU,(600,600))
    def blocked(*a,**kw):raise RuntimeError('Offline momentum-short research forbids network')
    socket.create_connection=blocked;socket.socket.connect=blocked
    if a.command=='check':
        r=check(a.state,a.case);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
    else:run(a.state,a.case,a.output,a.plan_commit)
