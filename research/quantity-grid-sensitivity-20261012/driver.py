"""Six fixed conditional accounts; existing targets and existing closing factory."""
import argparse, gc, importlib.util, json, sys, time
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('completed_fixed_assembly',ROOT/'research/cs-hold-continuous-assembly-20261012/driver.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
native,b,sha,save,source_window,checkpoint,restore_snapshot=old.native,old.b,old.sha,old.save,old.source_window,old.checkpoint,old.restore_snapshot
sys.path.insert(0,str(HERE))
from grid_account import QuantityGridAccount as Closing,profile_sha
SYMBOLS=old.SYMBOLS;DAY=old.DAY;ARMS=('CS_MATCHED','VOL_MATCHED','STATIC50')
def proto():return json.loads((HERE/'PROTOCOL.json').read_text())
def verify():
    for line in (HERE/'SOURCE_SHA256.txt').read_text().splitlines():
        s,p=line.split(maxsplit=1);assert sha(ROOT/p)==s,p
def targets(key):
    P=proto();W=P['windows'][key];path=ROOT/P['targets']['path'];assert sha(path)==P['targets']['SHA256']
    with np.load(path,allow_pickle=False) as a:
        t=a['decision_us'];cs=a['CS_MATCHED'];hold=a['VOL_MATCHED'];assert tuple(a['symbol_order'])==SYMBOLS
    start,end=map(native.utc,W['calendar']);d=np.arange(start,end,DAY);ids=np.searchsorted(t,d);np.testing.assert_array_equal(t[ids],d)
    mixpath=ROOT/W['mixture_path'];assert sha(mixpath)==W['mixture_SHA256']
    with np.load(mixpath,allow_pickle=False) as a:
        np.testing.assert_array_equal(a['decision_us'],d);assert tuple(a['symbol_order'])==SYMBOLS;mix=a['STATIC50']
    np.testing.assert_array_equal(mix,old.compose(cs[ids],hold[ids]))
    out=dict(CS_MATCHED=cs[ids],VOL_MATCHED=hold[ids],STATIC50=mix)
    for w in out.values():native.targets(d,w,start,end,start,SYMBOLS)
    return d,out
def run(state,key,prepared,source):
    assert not state.exists() and not b.git('status','--porcelain') and b.git('rev-parse','HEAD').decode().strip()==source
    verify();state.mkdir(parents=True);began=time.monotonic();P=proto();W=P['windows'][key];d,weights=targets(key);win=source_window(key,prepared)
    save(state/'RUN_IDENTITY.json',dict(source_commit=source,window=key,arms=list(ARMS),contract='FROM_INCEPTION_FIXED_QUANTITY_GRID_CLOSING_EXEMPT_V1',new_wallet_budget=3,fits=0))
    for arm in ARMS:
        arm_began=time.monotonic();dest=state/arm;dest.mkdir();w=weights[arm]
        binding=dict(science_source_commit=source,window=key,arm=arm,target_archive_SHA256=P['targets']['SHA256'],mixture_SHA256=W['mixture_SHA256'],source_index_SHA256=sha(prepared/'SOURCE_INDEX.json'),protocol_SHA256=sha(HERE/'PROTOCOL.json'),account_class=Closing.VERSION,contract_from_initial_capital=True,quantity_profile_SHA256=profile_sha())
        save(dest/'BINDING.json',binding)
        def factory(_daily,clocks,mode):
            np.testing.assert_array_equal(clocks,d)
            return native.pl.DataFrame([dict(available_us=int(at),symbol=s,target_weight=float(w[i,j])) for i,at in enumerate(d) for j,s in enumerate(SYMBOLS)]),dict(kind='REUSED_FIXED_TARGETS_UNCHANGED_RISK',binding=binding)
        sim=native.NativeDailySimulator(win,'LONG_SHORT',native.COSTS[0],native.UNITS[0],target_factory=factory,account_factory=Closing)
        assert type(sim.account) is Closing and sim.account.closing_min_notional_exempt and sim.account.nav()==10000
        checkpoint(dest/'recovery',sim,binding)
        while sim.cursor<win['end'] and sim.stop is None:
            sim.advance_day();days=len(sim.minute_chunks)
            if days%30==0 or sim.cursor==win['end'] or sim.stop is not None:
                checkpoint(dest/'recovery',sim,binding);print('ACTUAL_UNIFIED_EXIT',key,arm,days,W['days'],'NAV',float(sim.account.nav()),'status',sim.account.status,flush=True)
            assert time.monotonic()-arm_began<P['budget']['wallet_seconds']
            assert sum(p.stat().st_size for p in state.rglob('*') if p.is_file())<P['budget']['STATE_window_bytes']
        case=sim.result();saved=native.save_case(case,dest/'account');summary=saved['summary'];audit='PASS';error=None;finance=None
        try:
            _,q=native.episodes(case['trades'],SYMBOLS)
            for s in SYMBOLS:assert q[s]==sim.account.positions[s].quantity
            finance=native.nav_bridge(case['trades'],case['funding'],q,summary['terminal_mark_prices'],sim.account.nav())
        except (AssertionError,ValueError) as e:audit='FAIL';error=str(e)
        minute=case['minute'];daily=minute.filter(native.pl.col('close_us')%DAY==0);nav=np.r_[10000.,daily['nav'].to_numpy()];r=np.diff(nav)/nav[:-1];roll=nav[30:]/nav[:-30]-1 if len(nav)>30 else np.array([])
        metrics=dict(days=len(r),actual_daily_annual_vol=float(r.std(ddof=1)*np.sqrt(365)) if len(r)>1 else None,worst30=float(roll.min()) if len(roll) else None)
        body={k:case[k] for k in ('trades','funding','rejections','breaches','extrema','target_meta')};body.update(summary=summary,targets=case['targets'].to_dicts(),liquidations=case.get('liquidations',[]))
        save(dest/'ACCOUNT.json',body);daily.write_csv(dest/'DAILY.csv');full=summary['completed_minutes']==W['days']*1440;ci=None
        if full:
            rng=np.random.default_rng(P['bootstrap']['seed']);draws=[]
            for _ in range(P['bootstrap']['draws']):
                starts=rng.integers(0,len(r),int(np.ceil(len(r)/14)));ids=np.concatenate([(s+np.arange(14))%len(r) for s in starts])[:len(r)];draws.append(float(r[ids].mean()))
            ci=[float(x) for x in np.quantile(draws,[.025,.975])]
        gates=dict(full_paid_audited=bool(full and summary['terminal_cash_realized'] and not body['liquidations'] and audit=='PASS'),net_positive=bool(full and summary['net_PnL']>0),daily_cash_CI=bool(ci is not None and ci[0]>0),risk=bool(full and metrics['actual_daily_annual_vol']<=.12 and summary['all_observation_max_drawdown']<=.12 and metrics['worst30']>=-.10))
        ptr=json.loads((dest/'recovery/POINTER.json').read_text());assert ptr['completed_minutes']==summary['completed_minutes']
        report=dict(status='PASS_CONDITIONAL_SEEN_PATH_GATES' if all(gates.values()) else 'STOP_CONDITIONAL_SEEN_PATH_GATES',window=key,arm=arm,calendar=W['calendar'],science_source_commit=source,summary=summary,metrics=metrics,gates=gates,bootstrap_actual_daily_cash95CI=ci,inventory_audit=audit,audit_error=error,independent_decimal_NAV_bridge=finance,genuine_state_hash=ptr['state_hash'],new_wallets=1,new_fits=0,provider_downloads=0,authority='CONDITIONAL_PROXY_FILTERS_FUNDING_MMR_ARRIVAL_NOT_NATIVE_CERTIFIED',scope='FRESH10K_FULL_FIXED_WINDOW_NOT_STITCHED')
        baseline_path=ROOT/W['fine_step_baseline_prefix']/arm/'RESULT.json';assert baseline_path.read_bytes()==b.git('show','fca3aafd6943d12be0110e7b50ac02f4be55b269:'+str(baseline_path.relative_to(ROOT)));fine=json.loads(baseline_path.read_text());oldsummary=fine['summary']
        report['fine_step_comparison']=dict(status='SAME_COMPLETE_CALENDAR_ONE_QUANTITY_PROFILE_FACTOR_CHANGED_REALIZED_EXPOSURE' if full else 'NOT_EVALUABLE_PARTIAL_NEW_CALENDAR',reference_commit='fca3aafd6943d12be0110e7b50ac02f4be55b269',old_net_USDT=oldsummary['net_PnL'],net_increment_USDT=summary['net_PnL']-oldsummary['net_PnL'] if full else None,old_vol=fine['metrics']['actual_daily_annual_vol'],old_DD=oldsummary['all_observation_max_drawdown'],old_terminal_notional=oldsummary['terminal_marked_notional'])
        report['rejection_counts']=native.rejection_counts(case['rejections'])
        report['quantity_profile_SHA256']=profile_sha()
        save(dest/'RESULT.json',report);save(dest/'TIMING.json',dict(seconds=time.monotonic()-arm_began));print(json.dumps(dict(window=key,arm=arm,status=report['status'],net_USDT=summary['net_PnL'],paid_flat=summary['terminal_cash_realized'],gates=gates)),flush=True)
        del sim,case,minute,daily;gc.collect()
    reports={arm:json.loads((state/arm/'RESULT.json').read_text()) for arm in ARMS};comparisons={}
    for control in ARMS[:2]:
        x=reports['STATIC50'];y=reports[control];complete=x['metrics']['days']==y['metrics']['days']==W['days'];comparisons[control]=dict(status='DESCRIPTIVE_SAME_CONTRACT_DIFFERENT_JOINT_RISK' if complete else 'NOT_EVALUABLE_PARTIAL_CALENDAR',marked_net_increment_USDT=x['summary']['net_PnL']-y['summary']['net_PnL'] if complete else None)
    save(state/'RESULT.json',dict(window=key,arms=reports,comparison=comparisons,new_wallets=3,new_fits=0,provider_downloads=0,seconds=time.monotonic()-began))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--window',choices=['P1','P2'],required=True);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--source-commit',required=True);a=p.parse_args();run(a.state,a.window,a.prepared,a.source_commit)
