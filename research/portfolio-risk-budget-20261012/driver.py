"""Bounded portfolio sizing comparison through the unchanged native shared wallet."""
import argparse, gc, importlib.util, json, sys, time
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('frozen_quantity_comparison', ROOT/'research/quantity-grid-sensitivity-20261012/driver.py')
old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
native, b, sha, save, source_window, Closing = old.native, old.b, old.sha, old.save, old.source_window, old.Closing
profile_sha = old.profile_sha
sys.path.insert(0, str(HERE))
from risk_budget import ARMS, SYMBOLS, DAY, allocate
from compact_state import checkpoint, restore_snapshot

def proto(): return json.loads((HERE/'PROTOCOL.json').read_text())
def verify():
    for line in (HERE/'SOURCE_SHA256.txt').read_text().splitlines():
        s, p = line.split(maxsplit=1); assert sha(ROOT/p) == s, p

def prepare(state, source):
    assert not state.exists() and not b.git('status', '--porcelain') and b.git('rev-parse', 'HEAD').decode().strip() == source
    verify(); state.mkdir(parents=True); began=time.monotonic(); P=proto()
    cube=ROOT/P['risk_source']['path']; assert sha(cube)==P['risk_source']['SHA256']
    with np.load(cube,allow_pickle=False) as z: t=z['close_available_us']; p=z['close']
    reports={}
    for key,W in P['windows'].items():
        d,base=old.targets(key); weights,cov,proof=allocate(t,p,d,base)
        risk_path=ROOT/W['existing_risk_path']; assert sha(risk_path)==W['existing_risk_SHA256']; previous=json.loads(risk_path.read_text()); assert len(previous)==len(proof)
        for i,row in enumerate(proof):
            assert row['decision_us']==previous[i]['decision_us'] and row['last_price_available_us']==previous[i]['last_price_available_us']
            for arm,field in zip(ARMS,('CS_sigma','HOLD_sigma','mix_sigma'),strict=True): assert abs(row['arms'][arm]['raw_sigma']-previous[i][field])<1e-12
        cut=native.utc('2022-01-01' if key=='P1' else '2023-07-01'); future=p.copy(); future[t>cut]*=np.arange(2,7); alt,altcov,altproof=allocate(t,future,d,base)
        np.testing.assert_array_equal(altcov[d<=cut],cov[d<=cut]); assert [r for r in altproof if r['decision_us']<=cut]==[r for r in proof if r['decision_us']<=cut]
        for arm in ARMS: np.testing.assert_array_equal(alt[arm][d<=cut],weights[arm][d<=cut])
        np.savez_compressed(state/(key+'.npz'),decision_us=d,symbol_order=np.array(SYMBOLS),annual_covariance=cov,**weights)
        save(state/(key+'_RISK.json'),proof)
        stats={}
        for arm in ARMS:
            rows=[r['arms'][arm] for r in proof];stats[arm]=dict(risk_target_met_days=sum(r['risk_target_met'] for r in rows),cap_bound_days=sum(r['cap_bound'] for r in rows),intrinsic_cash_days=sum(r['reason']=='INTRINSIC_CASH' for r in rows),mean_post_sigma=float(np.mean([r['post_sigma'] for r in rows])),maximum_post_sigma=max(r['post_sigma'] for r in rows),mean_factor=float(np.mean([r['factor'] for r in rows])),mean_shortfall=float(np.mean([r['shortfall'] for r in rows])),maximum_gross=max(r['gross'] for r in rows),maximum_asset=max(r['largest'] for r in rows),whole_target_exact_REUSED=bool(np.array_equal(weights[arm],base[arm])),changed_target_days=int(np.any(weights[arm]!=base[arm],axis=1).sum()))
        reports[key]=dict(days=len(d),target_SHA256=sha(state/(key+'.npz')),risk_SHA256=sha(state/(key+'_RISK.json')),arms=stats,all_three_forecast_risk_matched_days=sum(max(r['arms'][a]['post_sigma'] for a in ARMS)-min(r['arms'][a]['post_sigma'] for a in ARMS)<=1e-12 for r in proof),future_suffix_invariance='EXACT',existing_lagged_sigma_identity='EXACT_WITHIN_1E-12_NO_RETURN_OUTCOMES')
    save(state/'PREPARATION.json',dict(status='PASS_FROZEN_FIXED10_PORTFOLIO_RISK_TARGET_WITH_CAP_SHORTFALLS',source_commit=source,windows=reports,new_wallets=0,new_fits=0,provider_downloads=0,seconds=time.monotonic()-began));print(json.dumps(reports,indent=2),flush=True)

def targets(key):
    path=HERE/'input'/(key+'.npz'); prep=json.loads((HERE/'input/PREPARATION.json').read_text()); assert sha(path)==prep['windows'][key]['target_SHA256']
    with np.load(path,allow_pickle=False) as z:
        d=z['decision_us']; weights={a:z[a].copy() for a in ARMS}; assert tuple(z['symbol_order'])==SYMBOLS
    W=proto()['windows'][key]; start,end=map(native.utc,W['calendar']);np.testing.assert_array_equal(d,np.arange(start,end,DAY))
    for w in weights.values(): native.targets(d,w,start,end,start,SYMBOLS)
    return d,weights

def run(state,key,arm,prepared,source):
    assert not state.exists() and not b.git('status','--porcelain') and b.git('rev-parse','HEAD').decode().strip()==source
    verify();state.mkdir(parents=True);began=time.monotonic();P=proto();W=P['windows'][key];d,weights=targets(key);w=weights[arm]; prep=json.loads((HERE/'input/PREPARATION.json').read_text()); assert not prep['windows'][key]['arms'][arm]['whole_target_exact_REUSED'],'Exact original path must be reused, never rerun'
    win=source_window(key,prepared)
    binding=dict(science_source_commit=source,window=key,arm=arm,target_archive_SHA256=sha(HERE/'input'/(key+'.npz')),risk_proof_SHA256=sha(HERE/'input'/(key+'_RISK.json')),component_targets_SHA256=P['targets']['SHA256'],source_index_SHA256=sha(prepared/'SOURCE_INDEX.json'),protocol_SHA256=sha(HERE/'PROTOCOL.json'),account_class=Closing.VERSION,contract_from_initial_capital=True,quantity_profile_SHA256=profile_sha(),annual_risk_budget=.10)
    save(state/'BINDING.json',binding)
    def factory(_daily,clocks,mode):
        np.testing.assert_array_equal(clocks,d)
        return native.pl.DataFrame([dict(available_us=int(at),symbol=s,target_weight=float(w[i,j])) for i,at in enumerate(d) for j,s in enumerate(SYMBOLS)]),dict(kind='FIXED10_CAUSAL_PORTFOLIO_RISK_SCALING_CAP_CONSTRAINED_NOT_NEW_PREDICTION',binding=binding)
    sim=native.NativeDailySimulator(win,'LONG_SHORT',native.COSTS[0],native.UNITS[0],target_factory=factory,account_factory=Closing)
    assert type(sim.account) is Closing and sim.account.closing_min_notional_exempt and sim.account.nav()==10000
    checkpoint(state/'recovery',sim,binding); print('ACTUAL_PORTFOLIO_RISK_WALLET_STARTED',key,arm,'capital',float(sim.account.nav()),flush=True)
    while sim.cursor<win['end'] and sim.stop is None:
        sim.advance_day();days=len(sim.minute_chunks)
        if days%30==0 or sim.cursor==win['end'] or sim.stop is not None:
            checkpoint(state/'recovery',sim,binding);print('ACTUAL_PORTFOLIO_RISK',key,arm,days,W['days'],'NAV',float(sim.account.nav()),'status',sim.account.status,flush=True)
        assert time.monotonic()-began<P['budget']['wallet_seconds'] and sum(p.stat().st_size for p in state.rglob('*') if p.is_file())<P['budget']['STATE_case_bytes']
    case=sim.result();summary=case['summary']; finance=None;audit='PASS';error=None
    try:
        _,q=native.episodes(case['trades'],SYMBOLS)
        for s in SYMBOLS: assert q[s]==sim.account.positions[s].quantity
        finance=native.nav_bridge(case['trades'],case['funding'],q,summary['terminal_mark_prices'],sim.account.nav())
    except (AssertionError,ValueError) as exc: audit='FAIL';error=str(exc)
    minute=case['minute'];daily=minute.filter(native.pl.col('close_us')%DAY==0);nav=np.r_[10000.,daily['nav'].to_numpy()];r=np.diff(nav)/nav[:-1];roll=nav[30:]/nav[:-30]-1 if len(nav)>30 else np.array([])
    metrics=dict(days=len(r),actual_daily_annual_vol=float(r.std(ddof=1)*np.sqrt(365)) if len(r)>1 else None,worst30=float(roll.min()) if len(roll) else None,mean_actual_gross=float(minute['gross_weight'].mean()),maximum_actual_gross=float(minute['gross_weight'].max()))
    body={k:case[k] for k in ('trades','funding','rejections','breaches','extrema','target_meta')};body.update(summary=summary,targets=case['targets'].to_dicts(),liquidations=case.get('liquidations',[]));save(state/'ACCOUNT.json',body);daily.write_csv(state/'DAILY.csv')
    # Keep all real minute values in the exact existing column codec, rather than a redundant Parquet container.
    spec=importlib.util.spec_from_file_location('existing_minute_fingerprint',ROOT/'research/cs-continuous-economics-20261012/persistence.py'); fingerprints=importlib.util.module_from_spec(spec);spec.loader.exec_module(fingerprints)
    save(state/'MINUTE_NUMERIC.json',dict(columns=fingerprints.minute_fingerprint(minute),Parquet_container='NOT_CREATED_ALL_ORIGINAL_VALUE_BITS_RETAINED'))
    full=summary['completed_minutes']==W['days']*1440;ci=None
    if full:
        rng=np.random.default_rng(P['bootstrap']['seed']);draws=[]
        for _ in range(P['bootstrap']['draws']):
            starts=rng.integers(0,len(r),int(np.ceil(len(r)/14)));ids=np.concatenate([(s+np.arange(14))%len(r) for s in starts])[:len(r)];draws.append(float(r[ids].mean()))
        ci=[float(x) for x in np.quantile(draws,[.025,.975])]
    paid=bool(summary['terminal_cash_realized']);gates=dict(full_paid_audited=bool(full and paid and not body['liquidations'] and audit=='PASS'),net_positive=bool(full and paid and summary['net_PnL']>0),daily_paid_path_CI=bool(paid and ci is not None and ci[0]>0),risk=bool(full and metrics['actual_daily_annual_vol']<=.12 and summary['all_observation_max_drawdown']<=.12 and metrics['worst30']>=-.10))
    ptr=json.loads((state/'recovery/POINTER.json').read_text());assert ptr['completed_minutes']==summary['completed_minutes']
    baseline_path=ROOT/W['quantity_baseline_prefix']/arm/'RESULT.json';assert baseline_path.read_bytes()==b.git('show',P['quantity_baseline_commit']+':'+str(baseline_path.relative_to(ROOT)));baseline=json.loads(baseline_path.read_text());bs=baseline['summary'];both_paid=full and paid and bs['terminal_cash_realized']
    report=dict(status='PASS_CONDITIONAL_SEEN_PATH_GATES' if all(gates.values()) else 'STOP_CONDITIONAL_SEEN_PATH_GATES',window=key,arm=arm,calendar=W['calendar'],science_source_commit=source,summary=summary,metrics=metrics,gates=gates,bootstrap_marked_path95CI=ci,bootstrap_paid_path95CI=ci if paid else None,inventory_audit=audit,audit_error=error,independent_decimal_NAV_bridge=finance,genuine_state_hash=ptr['state_hash'],new_wallets=1,new_fits=0,provider_downloads=0,quantity_profile_SHA256=profile_sha(),forecast_risk=prep['windows'][key]['arms'][arm],comparison=dict(reference_commit=P['quantity_baseline_commit'],baseline_net_USDT=bs['net_PnL'],baseline_paid_flat=bs['terminal_cash_realized'],marked_net_difference_USDT=summary['net_PnL']-bs['net_PnL'] if full else None,paid_net_difference_USDT=summary['net_PnL']-bs['net_PnL'] if both_paid else None,scope='FIXED_FORECAST_BUDGET_WITH_CAP_SHORTFALLS_CHANGED_EXPOSURE_NOT_PREDICTION_ALPHA'),authority='CONDITIONAL_QUANTITY_FUNDING_MMR_ARRIVAL_NOT_NATIVE_CERTIFIED',scope='FRESH10K_COMPLETE_SEEN_WINDOW_NOT_STITCHED')
    save(state/'RESULT.json',report);save(state/'TIMING.json',dict(seconds=time.monotonic()-began));print(json.dumps(dict(window=key,arm=arm,status=report['status'],net_USDT=summary['net_PnL'],paid_flat=paid,gates=gates)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();subs=p.add_subparsers(dest='command',required=True)
    q=subs.add_parser('prepare');q.add_argument('--state',type=Path,required=True);q.add_argument('--source-commit',required=True)
    q=subs.add_parser('run');q.add_argument('--state',type=Path,required=True);q.add_argument('--window',choices=['P1','P2'],required=True);q.add_argument('--arm',choices=ARMS,required=True);q.add_argument('--prepared',type=Path,required=True);q.add_argument('--source-commit',required=True)
    a=p.parse_args()
    if a.command=='prepare':prepare(a.state,a.source_commit)
    else:run(a.state,a.window,a.arm,a.prepared,a.source_commit)
