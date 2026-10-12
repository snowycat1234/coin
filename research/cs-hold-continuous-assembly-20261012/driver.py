"""Existing fixed arithmetic, existing exact targets, one genuine shared account."""
import argparse,gc,json,sys,time
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'research/cs-dual-speed-ranking-20261012'))
from experiment import native,b,sha,save,source_window,checkpoint,restore_snapshot
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
DAY=86400000000
def proto():return json.loads((HERE/'PROTOCOL.json').read_text())
def verify():
    for line in (HERE/'SOURCE_SHA256.txt').read_text().splitlines():s,p=line.split(maxsplit=1);assert sha(ROOT/p)==s,p
def compose(cs,hold):
    cs=np.asarray(cs,float);hold=np.asarray(hold,float)
    if cs.shape!=hold.shape or cs.ndim!=2 or cs.shape[1]!=5 or not np.isfinite(cs).all() or not np.isfinite(hold).all():raise ValueError('Exact finite two-intent CORE5 shape')
    for w in (cs,hold):
        if np.abs(w).max()>.3+1e-12 or np.abs(w).sum(1).max()>.6+1e-12:raise ValueError('Original input caps')
    mix=.5*cs+.5*hold;assert np.all(np.abs(mix).sum(1)<=.5*(np.abs(cs).sum(1)+np.abs(hold).sum(1))+1e-12);return mix
def risk(t,p,d,cs,hold,mix):
    proof=[]
    for i,at in enumerate(d):
        k=int(np.searchsorted(t,at));assert k>=30 and t[k]==at and np.all(np.diff(t[k-30:k+1])==DAY) and np.isfinite(p[k-30:k+1]).all() and (p[k-30:k+1]>0).all()
        r=np.diff(p[k-30:k+1],axis=0)/p[k-30:k];cov=np.cov(r,rowvar=False,ddof=1)*365;sig=[float(np.sqrt(max(0.,w@cov@w))) for w in (cs[i],hold[i],mix[i])];assert sig[2]<=.5*(sig[0]+sig[1])+1e-12
        proof.append(dict(decision_us=int(at),last_price_available_us=int(t[k]),CS_sigma=sig[0],HOLD_sigma=sig[1],mix_sigma=sig[2],gross=float(np.abs(mix[i]).sum()),cancelled_intent_gross=float(.5*(np.abs(cs[i]).sum()+np.abs(hold[i]).sum())-np.abs(mix[i]).sum()),not_relevered=True))
    return proof
def controls(key):
    W=proto()['windows'][key];prefix=W['control_prefix'];out={}
    for name in ('RESULT.json','BINDINGS.json'):
        p=ROOT/prefix/'native-summary'/name;assert p.read_bytes()==b.git('show',W['control_artifact']+':'+str(p.relative_to(ROOT)));out[name]=json.loads(p.read_text())
    return out
def compare_control(summary,old,full):
    out=dict(scope='REUSED_EXACT_SINGLE_CONTROL_DIFFERENT_JOINT_EXPOSURE_NOT_EQUAL_RISK_ALPHA',control_paid_flat=old['paid_flat'],control_terminal_marked_notional=old['summary']['terminal_marked_notional'],control_net_USDT=old['summary']['net_PnL'])
    out.update(status='SAME_COMPLETE_CALENDAR_DESCRIPTIVE' if full else 'NOT_EVALUABLE_INCOMPLETE_NEW_CALENDAR',marked_net_increment_USDT=summary['net_PnL']-old['summary']['net_PnL'] if full else None);return out
def prepare(state,source):
    assert not state.exists() and not b.git('status','--porcelain') and b.git('rev-parse','HEAD').decode().strip()==source;verify();state.mkdir();began=time.monotonic();P=proto();path=ROOT/P['targets']['path'];assert sha(path)==P['targets']['SHA256']
    with np.load(path,allow_pickle=False) as a:tgt=a['decision_us'];cs=a['CS_MATCHED'];hold=a['VOL_MATCHED'];assert tuple(a['symbol_order'])==SYMBOLS
    path=ROOT/'research/monetary-policy-information-20261012/input/INPUTS.npz';assert sha(path)=='e33cc15bd53167078252f7d58b406960d543ccb92421f430214e5360971f12f4'
    with np.load(path,allow_pickle=False) as a:t=a['close_available_us'];p=a['close']
    reports={}
    for key,W in P['windows'].items():
        prior=controls(key)
        for arm in ('CS_MATCHED','VOL_MATCHED'):assert prior['BINDINGS.json'][arm]['target_archive_SHA256']==P['targets']['SHA256'] and prior['BINDINGS.json'][arm]['science_source_commit']==W['source_artifact']
        start,end=map(native.utc,W['calendar']);d=np.arange(start,end,DAY);ids=np.searchsorted(tgt,d);np.testing.assert_array_equal(tgt[ids],d);c,h=cs[ids],hold[ids];m=compose(c,h);proof=risk(t,p,d,c,h,m)
        assert all(abs(x['CS_sigma']-x['HOLD_sigma'])<1e-10 and x['mix_sigma']<=.10+1e-10 for x in proof)
        cut=native.utc('2022-01-01' if key=='P1' else '2023-07-01');future=p.copy();future[t>cut]*=np.arange(2,7);v=risk(t,future,d,c,h,m);assert [x for x in v if x['decision_us']<=cut]==[x for x in proof if x['decision_us']<=cut]
        np.savez_compressed(state/(key+'.npz'),decision_us=d,symbol_order=np.array(SYMBOLS),STATIC50=m);save(state/(key+'_RISK.json'),proof);reports[key]=dict(days=len(d),target_SHA256=sha(state/(key+'.npz')),risk_SHA256=sha(state/(key+'_RISK.json')),source_component_target_identity='EXACT_REUSED4CONTROL_BINDINGS',future_risk_suffix_invariance='EXACT',mean_mixture_exante_sigma=float(np.mean([x['mix_sigma'] for x in proof])),mean_component_exante_sigma=float(np.mean([x['CS_sigma'] for x in proof])))
    save(state/'PREPARATION.json',dict(status='PASS_EXACT_FIXED_HALF_COMPONENT_TARGETS',source_commit=source,windows=reports,new_wallets=0,new_fits=0,provider_downloads=0,seconds=time.monotonic()-began));print(json.dumps(reports,indent=2),flush=True)
def run(state,key,prepared,source):
    assert not state.exists() and not b.git('status','--porcelain') and b.git('rev-parse','HEAD').decode().strip()==source;verify();state.mkdir();began=time.monotonic();P=proto();W=P['windows'][key];prior=controls(key);win=source_window(key,prepared);start,end=win['start'],win['end'];path=HERE/'input'/(key+'.npz')
    with np.load(path,allow_pickle=False) as a:d=a['decision_us'];w=a['STATIC50'];assert tuple(a['symbol_order'])==SYMBOLS
    native.targets(d,w,start,end,start,SYMBOLS);binding=dict(science_source_commit=source,window=key,arm='STATIC50',target_SHA256=sha(path),component_targets_SHA256=P['targets']['SHA256'],source_index_SHA256=sha(prepared/'SOURCE_INDEX.json'),protocol_SHA256=sha(HERE/'PROTOCOL.json'));save(state/'BINDING.json',binding)
    def factory(_daily,clocks,mode):
        np.testing.assert_array_equal(clocks,d);return native.pl.DataFrame([dict(available_us=int(at),symbol=s,target_weight=float(w[i,j])) for i,at in enumerate(d) for j,s in enumerate(SYMBOLS)]),dict(kind='EXISTING_FIXED_HALF_NETTED_SHARED_WALLET_NOT_NEW_SELECTOR',binding=binding)
    sim=native.NativeDailySimulator(win,'LONG_SHORT',native.COSTS[0],native.UNITS[0],target_factory=factory);checkpoint(state/'recovery',sim,binding)
    while sim.cursor<end and sim.stop is None:
        sim.advance_day();days=len(sim.minute_chunks)
        if days%30==0 or sim.cursor==end or sim.stop is not None:checkpoint(state/'recovery',sim,binding);print('ACTUAL_STATIC50_CONTINUOUS',key,days,W['days'],'NAV',float(sim.account.nav()),'status',sim.account.status,flush=True)
        assert time.monotonic()-began<P['budget']['wallet_seconds'] and sum(p.stat().st_size for p in state.rglob('*') if p.is_file())<P['budget']['STATE_each_bytes']
    case=sim.result();saved=native.save_case(case,state/'account');summary=saved['summary'];finance=None;audit='PASS';error=None
    try:
        _,q=native.episodes(case['trades'],SYMBOLS)
        for s in SYMBOLS:assert q[s]==sim.account.positions[s].quantity
        finance=native.nav_bridge(case['trades'],case['funding'],q,summary['terminal_mark_prices'],sim.account.nav())
    except (AssertionError,ValueError) as e:audit='FAIL';error=str(e)
    minute=case['minute'];daily=minute.filter(native.pl.col('close_us')%DAY==0);nav=np.r_[10000.,daily['nav'].to_numpy()];r=np.diff(nav)/nav[:-1];roll=nav[30:]/nav[:-30]-1 if len(nav)>30 else np.array([]);metrics=dict(days=len(r),actual_daily_annual_vol=float(r.std(ddof=1)*np.sqrt(365)) if len(r)>1 else None,worst30=float(roll.min()) if len(roll) else None)
    body={k:case[k] for k in ('trades','funding','rejections','breaches','extrema','target_meta')};body.update(summary=summary,targets=case['targets'].to_dicts(),liquidations=case.get('liquidations',[]));save(state/'ACCOUNT.json',body);daily.write_csv(state/'DAILY.csv');full=summary['completed_minutes']==W['days']*1440
    ci=None
    if full:
        rng=np.random.default_rng(P['bootstrap']['seed']);draws=[]
        for _ in range(1000):
            starts=rng.integers(0,len(r),int(np.ceil(len(r)/14)));ids=np.concatenate([(s+np.arange(14))%len(r) for s in starts])[:len(r)];draws.append(float(r[ids].mean()))
        ci=[float(x) for x in np.quantile(draws,[.025,.975])]
    gates=dict(full_paid_audited=bool(full and summary['terminal_cash_realized'] and not body['liquidations'] and audit=='PASS'),net_positive=bool(full and summary['net_PnL']>0),daily_cash_CI=bool(ci is not None and ci[0]>0),risk=bool(full and metrics['actual_daily_annual_vol']<=.12 and summary['all_observation_max_drawdown']<=.12 and metrics['worst30']>=-.10));comparison={}
    for arm,old in prior['RESULT.json']['arms'].items():comparison[arm]=compare_control(summary,old,full)
    pointer=json.loads((state/'recovery/POINTER.json').read_text());assert pointer['completed_minutes']==summary['completed_minutes'];report=dict(status='PASS_FIXED_STATIC50_SEEN_PATH_GATES' if all(gates.values()) else 'STOP_FIXED_STATIC50_SEEN_PATH_GATES',window=key,calendar=W['calendar'],science_source_commit=source,summary=summary,metrics=metrics,gates=gates,bootstrap_actual_daily_cash95CI=ci,comparison=comparison,inventory_audit=audit,audit_error=error,independent_decimal_NAV_bridge=finance,genuine_state_hash=pointer['state_hash'],new_wallets=1,new_fits=0,old_wallet_replays=0,provider_downloads=0,authority='CONDITIONAL_DEFAULT_FUNDUNIT_CHARGE_MARK_MMR_ARRIVAL',new_algorithm=False,scope='SEPARATE_SEEN_WINDOW_SHARED10K_NOT_STITCHED');save(state/'RESULT.json',report);save(state/'TIMING.json',dict(seconds=time.monotonic()-began));print(json.dumps(dict(window=key,status=report['status'],net_USDT=summary['net_PnL'],paid_flat=summary['terminal_cash_realized'],gates=gates),indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True);a=s.add_parser('prepare');a.add_argument('--state',type=Path,required=True);a.add_argument('--source-commit',required=True);a=s.add_parser('run');a.add_argument('--state',type=Path,required=True);a.add_argument('--window',choices=['P1','P2'],required=True);a.add_argument('--prepared',type=Path,required=True);a.add_argument('--source-commit',required=True);a=p.parse_args()
    if a.command=='prepare':prepare(a.state,a.source_commit)
    else:run(a.state,a.window,a.prepared,a.source_commit)
