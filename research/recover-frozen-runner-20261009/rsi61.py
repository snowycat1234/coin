"""One fixed original RSI2 LONG_SHORT signal in the exact native61 wallet."""
import argparse
from datetime import datetime,UTC
import hashlib,json,os
from pathlib import Path
import resource,shutil,signal,socket,subprocess,sys,time
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import native61 as frozen


def targets(state):
    import numpy as np
    import polars as pl
    mapper=frozen.modules(state)
    from scripts.investment import rsi2_daily_pool_target as rsi
    from scripts.investment import public_rsi2_indicator as indicator
    from scripts.investment.regime_ranking_screen import bounded_path
    from scripts.research.conditional_selector_core import shared_targets
    os.environ['COIN_RSI2_KERNEL_TARGET']=str(state/'rsi2-kernel-recovery/installed')
    frozen.require(frozen.sha(frozen.REPO/'scripts/investment/rsi2_daily_pool_target.py')=='c3e1c9c6b1d24b15b30f0e5014a3d3e3f4b13b3c998dde86d2aff687ba4af344','Pinned RSI strategy adapter differs')
    root=state/'h1_validation/original/h1_market';parts=[]
    for s in frozen.SYMBOLS:
        d=pl.read_parquet(root/'data/normalized'/(s+'_daily.parquet'))
        d=d.filter(pl.col('complete_kline')&pl.all_horizontal([pl.col(k).is_finite() for k in ('open','high','low','close','volume')])&(pl.col('available_us')<=frozen.END))
        parts.append(d.select('symbol','open_us','close_us','available_us','open','high','low','close','volume'))
    bars=pl.concat(parts);tt=np.arange(frozen.START,frozen.END,frozen.DAY,dtype=np.int64)
    frame,meta=rsi.fixed_targets(bars,tt,'LONG_SHORT',symbols=frozen.SYMBOLS)
    frozen.require(frame['eligibility_reason'].eq('ELIGIBLE').all(),'All61 real240-bar contexts required')
    zero=frame.with_columns(pl.lit(0.).alias('target_weight'),pl.lit(0.).alias('raw_signed_target'))
    budgets=bounded_path(np.tile([0.,1.],(61,1)),[1.,0.],.1)
    combined,_=shared_targets({'CASH':zero,'RSI2_LONG_SHORT':frame},('CASH','RSI2_LONG_SHORT'),tt,frozen.SYMBOLS,budgets)
    fractions=combined['target_weight'].to_numpy().reshape(61,5).copy()
    original=np.load(root/'inputs/H1_E5_INPUTS.npz',allow_pickle=False);ix=np.searchsorted(original['decision_us'],tt)
    # Test the new named2-slot bridge against the original E5 mapping math.
    # Test slots are temporary; no original expert identity is relabeled in
    # the emitted target provenance or production financial account.
    from types import SimpleNamespace
    prior=np.array([1.,0.,0.,0.,0.]);difference=0.
    expert=frame['target_weight'].to_numpy().reshape(61,5)
    for i,t in enumerate(tt):
        cube=np.zeros((5,5));cube[1]=expert[i]
        context=SimpleNamespace(decision_us=int(t),expert_eligible=np.ones(5,bool),expert_targets=cube,past_returns30=original['past_returns30'][ix[i]],binding={'symbol_order':list(frozen.SYMBOLS)})
        p=mapper.mapper(prior,[0,1,0,0,0],context);prior=np.asarray(p.budget)
        frozen.require(np.array_equal(prior[[0,1]],budgets[i]),'Original budget ramp math differs')
        difference=max(difference,float(np.max(abs(np.asarray(p.targets)-fractions[i]))))
    frozen.require(difference==0,'Original mixture/risk bridge parity required')
    fractions[-1]*=0
    receipt=indicator.kernel_receipt()
    receipt={k:v for k,v in receipt.items() if k not in ('package_file','extension_file')}
    report=dict(status='PASS_REAL240_ORIGINAL_RSI_RULES_KERNEL_AND_BRIDGE',days=61,actual_asset_contexts=305,mode='LONG_SHORT',
        parameters=rsi.PARAMETERS,rules=rsi.rules_for_mode('LONG_SHORT'),kernel=receipt,budget_initial=[1,0],budget_request=[0,1],
        original_E5_mixture_budget_math_maximum_error=difference,target_sha256=hashlib.sha256(fractions.tobytes()).hexdigest(),budget_sha256=hashlib.sha256(budgets.tobytes()).hexdigest(),
        target_max_gross=float(abs(fractions).sum(1).max()),target_max_asset=float(abs(fractions).max()),final_day_zero=True,fresh_signal_flat_at_window_start=True)
    return fractions,budgets,report


def check(state):
    plan=frozen.read(HERE/'NATIVE61_PLAN.json')
    for n,d in plan['source_sha256'].items():frozen.require(frozen.sha(frozen.REPO/n)==d,'Original financial dependency differs: '+n)
    root=state/'h1_validation/original/h1_market'
    frozen.require(frozen.sha(root/'reports/DATASET_MANIFEST.json')==plan['public_input']['data_manifest_sha256'],'Exact H1 market manifest required')
    for r in frozen.read(root/'reports/DATASET_MANIFEST.json')['artifacts']:
        p=root/r['relative_path'];frozen.require(p.stat().st_size==r['bytes'] and frozen.sha(p)==r['sha256'],'Retained actual H1 source differs')
    return targets(state)[2]


def run(state,output,commit):
    plan_path=HERE/'RSI61_PLAN.json';plan=frozen.read(plan_path)
    frozen.require(subprocess.check_output(['git','-C',str(frozen.REPO),'show',commit+':research/recover-frozen-runner-20261009/RSI61_PLAN.json'])==plan_path.read_bytes(),'Published single-wallet plan required')
    for n,d in plan['source_sha256'].items():frozen.require(frozen.sha(frozen.REPO/n)==d,'Published source differs: '+n)
    frozen.require(check(state)==frozen.read(HERE/'RSI61_PREFLIGHT.json'),'Published readiness differs')
    fractions,budgets,_=targets(state)
    from scripts.investment import perpetual_directional as old
    from scripts.investment.resumable_perpetual import NativeDailySimulator
    from quant.bybit_isolated_account import BybitIsolatedAccount
    frozen.require(old.COSTS[0]==plan['cost'],'Original BASE27 cost differs')
    sim=NativeDailySimulator(frozen.market(state),'LONG_SHORT',old.COSTS[0],dict(id='RAW_AS_FRACTION',scale=1.),account_factory=BybitIsolatedAccount,persist_cash_close=True,final_day_target_zero=True)
    sim.budget=[1.,0.];frozen.require(float(sim.account.nav())==10000 and not output.exists(),'Fresh independent wallet required');output.mkdir(parents=True)
    r=dict(policy='RSI2_LONG_SHORT',plan_commit=commit,started_UTC=datetime.now(UTC).isoformat(),limits=plan['limits']);(output/'STARTED.json').write_text(json.dumps(r,indent=2)+'\n')
    start=time.monotonic();status='RUNNING';error=None
    def alarm(s,f):raise TimeoutError('600-second RSI wallet cap')
    signal.signal(signal.SIGALRM,alarm);signal.setitimer(signal.ITIMER_REAL,600)
    try:
        for i in range(61):
            frozen.require(shutil.disk_usage(output).free>=15*2**30,'15GiB reserve required');sim.budget=budgets[i].tolist()
            frozen.require(sim.advance_day(dict(zip(frozen.SYMBOLS,fractions[i],strict=True)))['completed'],'Incomplete wallet must stop')
            if (i+1)%10==0 or i==60:print(json.dumps(dict(completed_days=i+1,total_days=61,NAV=float(sim.account.nav()))),flush=True)
        frozen.require(sim.rows_written==87840 and all(p.quantity==0 for p in sim.account.positions.values()),'Paid full61 terminal flat required');status='COMPLETE_CONDITIONAL_ACCOUNT'
    except BaseException as e:
        status='FAILED_PREFIX_RETAINED';error=dict(type=type(e).__name__,message=str(e));raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);saved=old.save_case(sim.result(),output/'account');(output/'account/summary.json').write_text(json.dumps(saved['summary'],indent=2)+'\n')
        r.update(status=status,error=error,finished_UTC=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,completed_minutes=sim.rows_written,original_engine_sha256=frozen.sha(frozen.REPO/'scripts/investment/resumable_perpetual.py'),audit='PENDING_POST_RUN_RECONCILIATION');(output/'EXECUTION.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:saved['summary'][k] for k in ('NAV','net_PnL','gross_PnL_same_quantities','fees_USDT','execution_cost_USDT','funding_USDT','trade_legs','terminal_cash_realized')}),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('check','run'));p.add_argument('--state',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--plan-commit');a=p.parse_args()
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','POLARS_MAX_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6_000_000_000,6_000_000_000));resource.setrlimit(resource.RLIMIT_CPU,(600,600))
    def blocked(*args,**kwargs):raise RuntimeError('Offline native RSI wallet forbids network')
    socket.create_connection=blocked;socket.socket.connect=blocked
    frozen.modules(a.state)
    if a.command=='check':
        r=check(a.state);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
    else:run(a.state,a.output,a.plan_commit)


if __name__=='__main__':main()
