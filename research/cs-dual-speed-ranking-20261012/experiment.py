"""Bounded direct-score economic ablation; exact existing financial/state APIs."""
import argparse,gc,importlib.util,json,sys,time
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(HERE))
from mechanism import targets,ARMS,SYMBOLS,DAY
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
sys.path.insert(0,str(ROOT/'research/cs-continuous-economics-20261012'));import native_pair as old1
old2=load('published_cs2023',ROOT/'research/cs-2023-continuous-economics-20261012/native_run.py');native=old1.native
from state_io import checkpoint,restore_snapshot
from source_prepare import b
def save(p,x):Path(p).write_text(json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n')
def sha(p):return old1.sha(p)
def proto():return json.loads((HERE/'PROTOCOL.json').read_text())
def verify():
    for line in (HERE/'SOURCE_SHA256.txt').read_text().splitlines():s,p=line.split(maxsplit=1);assert sha(ROOT/p)==s,p
def prepare(state,source):
    assert not state.exists() and not b.git('status','--porcelain') and b.git('rev-parse','HEAD').decode().strip()==source;verify();state.mkdir();began=time.monotonic();P=proto();path=ROOT/'research/monetary-policy-information-20261012/input/INPUTS.npz';assert sha(path)=='e33cc15bd53167078252f7d58b406960d543ccb92421f430214e5360971f12f4'
    with np.load(path,allow_pickle=False) as a:t=a['close_available_us'];p=a['close']
    reports={}
    for key,W in P['windows'].items():
        start,end=map(native.utc,W['calendar']);d=np.arange(start,end,DAY);w,score,proof=targets(t,p,d);np.savez_compressed(state/(key+'.npz'),decision_us=d,symbol_order=np.array(SYMBOLS),**w,**{a+'_score':score[a] for a in ARMS});save(state/(key+'_RISK.json'),proof)
        # Actualfutureperturbation provescausal prefix; targets compared bitexact.
        cut=native.utc('2022-01-01') if key=='P1' else native.utc('2023-07-01');future=p.copy();future[t>cut]*=np.arange(2,7);v,_,_=targets(t,future,d)
        for a in ARMS:np.testing.assert_array_equal(v[a][d<=cut],w[a][d<=cut])
        reports[key]=dict(days=len(d),target_SHA256=sha(state/(key+'.npz')),risk_SHA256=sha(state/(key+'_RISK.json')),future_suffix_invariance='EXACT',intrinsic_cash_dates={a:int((w[a]==0).all(1).sum()) for a in ARMS},different_DUAL_SKIP_targets=int((w['DUAL']!=w['SKIP']).any(1).sum()))
    save(state/'PREPARATION.json',dict(status='PASS_FIXED_CAUSAL_RANK_TARGETS',source_commit=source,windows=reports,new_models=0,new_wallets=0,provider_downloads=0,seconds=time.monotonic()-began));print(json.dumps(reports,indent=2),flush=True)
def source_window(key,prepared):
    W=proto()['windows'][key];path='research/cs-continuous-economics-20261012/source-result/SOURCE_INDEX.json' if key=='P1' else 'research/cs-2023-continuous-economics-20261012/source-result/SOURCE_INDEX.json'
    assert (prepared/'SOURCE_INDEX.json').read_bytes()==b.git('show',W['source_artifact']+':'+path)
    return old1.window(prepared) if key=='P1' else old2.window(prepared)
def run(state,key,prepared,source):
    assert not state.exists() and not b.git('status','--porcelain') and b.git('rev-parse','HEAD').decode().strip()==source;verify();state.mkdir();began=time.monotonic();P=proto();W=P['windows'][key];win=source_window(key,prepared);start,end=win['start'],win['end'];path=HERE/'input'/(key+'.npz')
    with np.load(path,allow_pickle=False) as a:d=a['decision_us'];w={arm:a[arm].copy() for arm in ARMS};assert tuple(a['symbol_order'])==SYMBOLS
    np.testing.assert_array_equal(d,np.arange(start,end,DAY));reports={};returns={};bindings={}
    for arm in ARMS:native.targets(d,w[arm],start,end,start,SYMBOLS)
    for arm in ARMS:
        arm_at=time.monotonic();casepath=state/arm;casepath.mkdir();binding=dict(science_source_commit=source,window=key,arm=arm,target_SHA256=sha(path),source_index_SHA256=sha(prepared/'SOURCE_INDEX.json'),protocol_SHA256=sha(HERE/'PROTOCOL.json'));bindings[arm]=binding
        def factory(_daily,clocks,mode):
            np.testing.assert_array_equal(clocks,d);return native.pl.DataFrame([dict(available_us=int(at),symbol=s,target_weight=float(w[arm][i,j])) for i,at in enumerate(d) for j,s in enumerate(SYMBOLS)]),dict(kind='DIRECT_FIXED_RANK_SCORE_NOT_EXPERTAGGREGATION',binding=binding)
        sim=native.NativeDailySimulator(win,'LONG_SHORT',native.COSTS[0],native.UNITS[0],target_factory=factory);checkpoint(casepath/'recovery',sim,binding)
        while sim.cursor<end and sim.stop is None:
            sim.advance_day();days=len(sim.minute_chunks)
            if days%30==0 or sim.cursor==end or sim.stop is not None:checkpoint(casepath/'recovery',sim,binding);print('ACTUAL_DUAL_SPEED_WALLET',key,arm,days,W['days'],'NAV',float(sim.account.nav()),'status',sim.account.status,flush=True)
            assert time.monotonic()-arm_at<600 and time.monotonic()-began<1100 and sum(p.stat().st_size for p in state.rglob('*') if p.is_file())<2_000_000_000
        case=sim.result();saved=native.save_case(case,casepath/'account');summary=saved['summary'];finance=None;inventory='PASS';error=None
        try:
            _,q=native.episodes(case['trades'],SYMBOLS)
            for s in SYMBOLS:assert q[s]==sim.account.positions[s].quantity
            finance=native.nav_bridge(case['trades'],case['funding'],q,summary['terminal_mark_prices'],sim.account.nav())
        except (ValueError,AssertionError) as exc:inventory='FAIL';error=str(exc)
        pointer=json.loads((casepath/'recovery/POINTER.json').read_text());assert pointer['completed_minutes']==summary['completed_minutes']
        minute=case['minute'];daily=minute.filter(native.pl.col('close_us')%DAY==0);nav=np.r_[10000.,daily['nav'].to_numpy()];r=np.diff(nav)/nav[:-1];returns[arm]=r
        roll=nav[30:]/nav[:-30]-1 if len(nav)>30 else np.array([]);metrics=dict(actual_daily_observations=len(r),actual_daily_annual_vol=float(r.std(ddof=1)*np.sqrt(365)) if len(r)>1 else None,worst30=float(roll.min()) if len(roll) else None)
        body={k:case[k] for k in ('trades','funding','rejections','breaches','extrema','target_meta')};body['summary']=summary;body['targets']=case['targets'].to_dicts();body['liquidations']=case.get('liquidations',[]);save(casepath/'ACCOUNT.json',body);daily.write_csv(casepath/'DAILY.csv');reports[arm]=dict(summary=summary,metrics=metrics,paid_flat=bool(summary['terminal_cash_realized']),full_calendar=summary['completed_minutes']==W['days']*1440,liquidations=len(body['liquidations']),independent_decimal_NAV_bridge=finance,inventory_audit=inventory,audit_error=error,genuine_checkpoint_state_hash=pointer['state_hash'],checkpoint_rows=pointer['completed_minutes'],rejections=native.rejection_counts(case['rejections']));save(casepath/'RESULT.json',reports[arm]);del sim,case,saved,minute,daily;gc.collect();print('DUAL_SPEED_ARM_COMPLETE',key,arm,summary['net_PnL'],'paidflat',reports[arm]['paid_flat'],flush=True)
    gates=dict(full_paid_audited=all(r['full_calendar'] and r['paid_flat'] and not r['liquidations'] and r['inventory_audit']=='PASS' for r in reports.values()));comparisons={}
    if all(r['full_calendar'] for r in reports.values()):
        for control in ('SLOW','SKIP'):
            delta=returns['DUAL']-returns[control];rng=np.random.default_rng(811720);draws=[]
            for _ in range(1000):
                starts=rng.integers(0,len(delta),int(np.ceil(len(delta)/14)));ids=np.concatenate([(s+np.arange(14))%len(delta) for s in starts])[:len(delta)];draws.append(float(delta[ids].mean()))
            lo,hi=np.quantile(draws,[.025,.975]);candidate,reference=reports['DUAL'],reports[control];increment=candidate['summary']['net_PnL']-reference['summary']['net_PnL'];comparisons[control]=dict(marked_net_increment_USDT=increment,mean_actual_daily_return_difference=float(delta.mean()),bootstrap95CI=[float(lo),float(hi)])
            gates[control+'_positive']=candidate['summary']['net_PnL']>0 and increment>0;gates[control+'_CI']=lo>0;gates[control+'_risk']=candidate['metrics']['actual_daily_annual_vol']<=1.1*reference['metrics']['actual_daily_annual_vol'] and candidate['summary']['all_observation_max_drawdown']<=reference['summary']['all_observation_max_drawdown'] and candidate['metrics']['worst30']>=reference['metrics']['worst30']
    report=dict(status='PASS_FIXED_DUAL_SPEED_WINDOW_GATES' if all(gates.values()) and comparisons else 'STOP_FIXED_DUAL_SPEED_WINDOW_GATES',window=key,calendar=W['calendar'],science_source_commit=source,arms=reports,comparisons=comparisons,gates=gates,new_native_wallets=3,new_model_fits=0,old_wallet_reruns=0,provider_downloads=0,authority='CONDITIONAL_DEFAULT_FEE_FUNDUNIT_CHARGE_MARK_MMR_ARRIVAL',independent_windows_not_stitched=True);save(state/'RESULT.json',report);save(state/'BINDINGS.json',bindings);save(state/'TIMING.json',dict(seconds=time.monotonic()-began));print(json.dumps(dict(window=key,status=report['status'],gates=gates,comparisons=comparisons),indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True);a=s.add_parser('prepare');a.add_argument('--state',type=Path,required=True);a.add_argument('--source-commit',required=True);a=s.add_parser('run');a.add_argument('--state',type=Path,required=True);a.add_argument('--window',choices=['P1','P2'],required=True);a.add_argument('--prepared',type=Path,required=True);a.add_argument('--source-commit',required=True);a=p.parse_args()
    if a.command=='prepare':prepare(a.state,a.source_commit)
    else:run(a.state,a.window,a.prepared,a.source_commit)
