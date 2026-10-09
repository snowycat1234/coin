"""One predeclared short-only20/10 hypothesis in the unchanged native61 engine."""
import argparse
from datetime import datetime, UTC
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import socket
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import native61 as frozen


def targets(state):
    import numpy as np
    import polars as pl
    frozen.modules(state)
    from scripts.investment import donchian_short_daily_pool_target as short
    from scripts.investment.regime_ranking_screen import bounded_path
    from scripts.research.conditional_selector_core import shared_targets
    root=state/'h1_validation/original/h1_market';parts=[]
    for s in frozen.SYMBOLS:
        d=pl.read_parquet(root/'data/normalized'/(s+'_daily.parquet'))
        d=d.filter(pl.col('complete_kline')&pl.all_horizontal([pl.col(k).is_finite() for k in ('open','high','low','close','volume')])&(pl.col('available_us')<=frozen.END))
        parts.append(d.select('symbol','open_us','close_us','available_us','open','high','low','close','volume'))
    bars=pl.concat(parts);tt=np.arange(frozen.START,frozen.END,frozen.DAY,dtype=np.int64)
    frame,meta=short.fixed_targets(bars,tt,symbols=frozen.SYMBOLS)
    frozen.require(frame['eligibility_reason'].eq('ELIGIBLE').all(),'All305 actual200-bar contexts required')
    expert=frame['target_weight'].to_numpy().reshape(61,5)
    raw=frame['raw_signed_target'].to_numpy().reshape(61,5)
    # Independent direct windows/state plus sample covariance. Never call the
    # producer hook/kernel for this verification of actual305 contexts.
    states=np.zeros(5,bool);reference=np.zeros((61,5));reference_raw=np.zeros((61,5));witnesses=[]
    for i,t in enumerate(tt):
        past=[]
        for j,s in enumerate(frozen.SYMBOLS):
            d=bars.filter(pl.col('symbol')==s).sort('close_us');stamps=d['close_us'].to_numpy();k=int(np.searchsorted(stamps,t))
            frozen.require(stamps[k]==t and k>=199 and np.all(np.diff(stamps[k-199:k+1])==frozen.DAY),'Actual200 contiguous closed bars required')
            frozen.require((d['available_us'].to_numpy()[k-199:k+1]<=t).all(),'Independent future availability rejected')
            close=d['close'].to_numpy();high=d['high'].to_numpy();low=d['low'].to_numpy()
            prior_low=float(low[k-20:k].min());prior_high=float(high[k-10:k].max());before=bool(states[j])
            if states[j]:
                if close[k]>prior_high:states[j]=False
            elif close[k]<prior_low:states[j]=True
            reference_raw[i,j]=-.12 if states[j] else 0.
            past.append(np.diff(close[k-30:k+1])/close[k-30:k])
            witnesses.append(dict(decision_us=int(t),symbol=s,completed_close=float(close[k]),prior20_low=prior_low,
                prior10_high=prior_high,held_short_before=before,held_short_after=bool(states[j]),entry_filter_SMA200=False))
        covariance=np.cov(np.column_stack(past),rowvar=False,ddof=1)*365
        sigma=float(np.sqrt(max(0,reference_raw[i]@covariance@reference_raw[i])))
        reference[i]=reference_raw[i]*min(1.,.1/sigma) if sigma else reference_raw[i]
    frozen.require(np.array_equal(raw,reference_raw),'Independent exact signal/state/EQUAL allocation mismatch')
    difference=float(abs(expert-reference).max());frozen.require(difference<=1e-14,'Independent causal risk target mismatch')
    zero=frame.with_columns(pl.lit(0.).alias('target_weight'),pl.lit(0.).alias('raw_signed_target'))
    budgets=bounded_path(np.tile([0.,1.],(61,1)),[1.,0.],.1)
    combined,_=shared_targets({'CASH':zero,'DONCHIAN20_EXIT10_SHORT_ONLY':frame},('CASH','DONCHIAN20_EXIT10_SHORT_ONLY'),tt,frozen.SYMBOLS,budgets)
    fractions=combined['target_weight'].to_numpy().reshape(61,5).copy();fractions[-1]*=0
    frozen.require((fractions<=0).all() and abs(fractions).sum(1).max()<=.6 and abs(fractions).max()<=.3,'Original target bounds and short direction required')
    report=dict(status='PASS_REAL200_PRIOR20_ENTRY_PRIOR10_EXIT_NO_FILTER_AND_CAUSAL_RISK',days=61,actual_asset_contexts=305,
        mode='SHORT_ONLY',rules=short.RULES,independent_raw_state_maximum_error=0,
        independent_covariance_target_maximum_error=difference,target_sha256=hashlib.sha256(fractions.tobytes()).hexdigest(),
        budget_sha256=hashlib.sha256(budgets.tobytes()).hexdigest(),target_max_gross=float(abs(fractions).sum(1).max()),
        target_max_asset=float(abs(fractions).max()),raw_active_asset_weight=-.12,
        initial_budget=[1,0],requested_budget=[0,1],full_risky_budget_day='2024-05-20',final_day_zero=True,
        signal_initial_state='FRESH_FLAT_MAY1_NO_WARMUP_POSITIONS',selected_after_seeing_June2024=True)
    return fractions,budgets,meta,witnesses,report


def check(state):
    plan=frozen.read(HERE/'NATIVE61_PLAN.json')
    for n,d in plan['source_sha256'].items():frozen.require(frozen.sha(frozen.REPO/n)==d,'Original dependency differs: '+n)
    root=state/'h1_validation/original/h1_market'
    frozen.require(frozen.sha(root/'reports/DATASET_MANIFEST.json')==plan['public_input']['data_manifest_sha256'],'Exact market manifest required')
    for r in frozen.read(root/'reports/DATASET_MANIFEST.json')['artifacts']:
        p=root/r['relative_path'];frozen.require(p.stat().st_size==r['bytes'] and frozen.sha(p)==r['sha256'],'Retained actual market bytes differ')
    return targets(state)[4]


def run(state,output,commit):
    plan_path=HERE/'DONCHIAN_SHORT61_PLAN.json';plan=frozen.read(plan_path)
    frozen.require(subprocess.check_output(['git','-C',str(frozen.REPO),'show',commit+':research/recover-frozen-runner-20261009/DONCHIAN_SHORT61_PLAN.json'])==plan_path.read_bytes(),'Published single-wallet plan required')
    for n,d in plan['source_sha256'].items():frozen.require(frozen.sha(frozen.REPO/n)==d,'Published source differs: '+n)
    frozen.require(check(state)==frozen.read(HERE/'DONCHIAN_SHORT61_PREFLIGHT.json'),'Published readiness differs')
    fractions,budgets,meta,witnesses,_=targets(state)
    from scripts.investment import perpetual_directional as old
    from scripts.investment.resumable_perpetual import NativeDailySimulator
    from quant.bybit_isolated_account import BybitIsolatedAccount
    frozen.require(old.COSTS[0]==plan['cost'],'Original BASE27 costs differ')
    sim=NativeDailySimulator(frozen.market(state),'SHORT_ONLY',old.COSTS[0],dict(id='RAW_AS_FRACTION',scale=1.),
        account_factory=BybitIsolatedAccount,persist_cash_close=True,final_day_target_zero=True)
    sim.meta=meta;sim.budget=[1.,0.]
    frozen.require(float(sim.account.nav())==10000 and not output.exists(),'Fresh independent wallet required');output.mkdir(parents=True)
    receipt=dict(policy='DONCHIAN20_EXIT10_SHORT_ONLY',plan_commit=commit,started_UTC=datetime.now(UTC).isoformat(),limits=plan['limits'])
    (output/'STARTED.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (output/'INDEPENDENT_SIGNAL_WITNESSES.json').write_text(json.dumps(witnesses,indent=2)+'\n')
    start=time.monotonic();status='RUNNING';error=None
    def alarm(s,f):raise TimeoutError('600-second short Donchian account cap')
    signal.signal(signal.SIGALRM,alarm);signal.setitimer(signal.ITIMER_REAL,600)
    try:
        for i in range(61):
            frozen.require(shutil.disk_usage(output).free>=15*2**30,'15GiB reserve required');sim.budget=budgets[i].tolist()
            frozen.require(sim.advance_day(dict(zip(frozen.SYMBOLS,fractions[i],strict=True)))['completed'],'Incomplete wallet must stop')
            frozen.require(all(p.quantity<=0 for p in sim.account.positions.values()),'Forbidden long inventory')
            if (i+1)%10==0 or i==60:print(json.dumps(dict(completed_days=i+1,total_days=61,NAV=float(sim.account.nav()))),flush=True)
        frozen.require(sim.rows_written==87840 and all(p.quantity==0 for p in sim.account.positions.values()),'Paid full61 terminal flat required');status='COMPLETE_CONDITIONAL_ACCOUNT'
    except BaseException as e:
        status='FAILED_PREFIX_RETAINED';error=dict(type=type(e).__name__,message=str(e));raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);saved=old.save_case(sim.result(),output/'account');(output/'account/summary.json').write_text(json.dumps(saved['summary'],indent=2)+'\n')
        receipt.update(status=status,error=error,finished_UTC=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-start,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,completed_minutes=sim.rows_written,
            original_engine_sha256=frozen.sha(frozen.REPO/'scripts/investment/resumable_perpetual.py'),audit='PENDING_POSTRUN_INDEPENDENT_RECONCILIATION',
            hypothesis_selected_after_seeing_June2024=True,June1_wallet_reset=False)
        (output/'EXECUTION.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:saved['summary'][k] for k in ('NAV','net_PnL','gross_PnL_same_quantities','fees_USDT','execution_cost_USDT','funding_USDT','trade_legs','terminal_cash_realized')}),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('check','run'));p.add_argument('--state',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--plan-commit');a=p.parse_args()
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','POLARS_MAX_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6_000_000_000,6_000_000_000));resource.setrlimit(resource.RLIMIT_CPU,(600,600))
    def blocked(*args,**kwargs):raise RuntimeError('Offline short Donchian wallet forbids network')
    socket.create_connection=blocked;socket.socket.connect=blocked
    frozen.modules(a.state)
    if a.command=='check':
        r=check(a.state);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
    else:run(a.state,a.output,a.plan_commit)


if __name__=='__main__':main()
