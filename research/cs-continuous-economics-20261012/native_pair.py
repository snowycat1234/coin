"""Two frozen continuous wallets, preserving every stop/residual and real state."""
import argparse,gc,json,sys,time
from pathlib import Path
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(HERE))
from source_prepare import native,b,verify
from reference import save,sha
from core import DAY,SYMBOLS
from state_io import checkpoint,restore_snapshot
ARMS=('CS_MATCHED','VOL_MATCHED')

def window(prepared):
    index=json.loads((prepared/'SOURCE_INDEX.json').read_text());start,end=index['calendar']
    contract=json.loads((HERE/'PROTOCOL.json').read_text())
    assert index['status']=='PASS_EXACT_FIXED456DAY_CONTINUOUS_SOURCE' and index['symbol_order']==list(SYMBOLS) and index['calendar']==[native.utc(x) for x in contract['native_calendar']] and index['days']==456
    for name in ('EVENTS.json','DAILY.json'):
        r=index['files'][name];assert sha(prepared/name)==r['SHA256'] and (prepared/name).stat().st_size==r['bytes']
    events=json.loads((prepared/'EVENTS.json').read_text());daily=native.pl.DataFrame(json.loads((prepared/'DAILY.json').read_text()))
    def blocks():
        for rec in index['months']:
            p=prepared/'months'/(rec['month']+'.npz');assert sha(p)==rec['source_NPZ_SHA256']
            with np.load(p,allow_pickle=False) as z:
                times=z['times'];market={s:{k:z[s+'_'+k] for k in ('open','close','quote_volume','mark')} for s in SYMBOLS}
            for i in range(0,len(times),1440):yield dict(times=times[i:i+1440],market={s:{k:v[i:i+1440] for k,v in fields.items()} for s,fields in market.items()})
    return dict(start=start,end=end,symbols=SYMBOLS,daily=daily,events=events,minute_blocks=blocks)

def run(state,prepared,source):
    assert not state.exists() and not b.git('status','--porcelain') and b.git('rev-parse','HEAD').decode().strip()==source
    verify()
    published=b.git('show',source+':research/cs-continuous-economics-20261012/source-result/SOURCE_INDEX.json')
    assert (prepared/'SOURCE_INDEX.json').read_bytes()==published,'Immutable prepublished source/rate/day index required before account'
    state.mkdir();started=time.monotonic();win=window(prepared);start,end=win['start'],win['end'];d=np.arange(start,end,DAY);assert len(d)==456
    target=HERE/'reference-result/TARGETS.npz'
    with np.load(target,allow_pickle=False) as z:
        assert tuple(z['symbol_order'])==SYMBOLS;ids=np.searchsorted(z['decision_us'],d);np.testing.assert_array_equal(z['decision_us'][ids],d);w={a:z[a][ids] for a in ARMS};states=z['state'][ids]
    reports={};returns={};daily_nav={};bindings={}
    for arm in ARMS:
        weights=w[arm];native.targets(d,weights,start,end,start,SYMBOLS)
        binding=dict(science_source_commit=source,arm=arm,source_index_SHA256=sha(prepared/'SOURCE_INDEX.json'),target_archive_SHA256=sha(target),protocol_SHA256=sha(HERE/'PROTOCOL.json'))
        bindings[arm]=binding;casepath=state/arm;casepath.mkdir()
        def factory(_daily,clocks,mode):
            np.testing.assert_array_equal(clocks,d)
            return native.pl.DataFrame([dict(available_us=int(at),symbol=s,target_weight=float(weights[i,j])) for i,at in enumerate(d) for j,s in enumerate(SYMBOLS)]),dict(arm=arm,source='FIXED_ORIGINAL_DIRECTIONS_COMMON_PAST_RISK_ONLY',binding=binding)
        sim=native.NativeDailySimulator(win,'LONG_SHORT',native.COSTS[0],native.UNITS[0],target_factory=factory);arm_started=time.monotonic();checkpoint(casepath/'recovery',sim,binding)
        while sim.cursor<end and sim.stop is None:
            sim.advance_day();days=len(sim.minute_chunks)
            if days%30==0 or sim.cursor==end or sim.stop is not None:
                checkpoint(casepath/'recovery',sim,binding)
                print('CONTINUOUS_ACTUAL_WALLET',arm,days,456,'NAV',float(sim.account.nav()),'status',sim.account.status,flush=True)
            assert time.monotonic()-arm_started<600 and time.monotonic()-started<1100
            assert sum(p.stat().st_size for p in state.rglob('*') if p.is_file())<2_000_000_000
        case=sim.result();saved=native.save_case(case,casepath/'account');summary=saved['summary'];finance=None;inventory='PASS';error=None
        try:
            episodes,q=native.episodes(case['trades'],SYMBOLS)
            for s in SYMBOLS:assert q[s]==sim.account.positions[s].quantity
            finance=native.nav_bridge(case['trades'],case['funding'],q,summary['terminal_mark_prices'],sim.account.nav())
        except (ValueError,AssertionError) as exc:inventory='FAIL';error=str(exc)
        minute=case['minute'];daily=minute.filter(native.pl.col('close_us')%DAY==0);nav=np.r_[10000.,daily['nav'].to_numpy()];r=np.diff(nav)/nav[:-1];returns[arm]=r;daily_nav[arm]=nav
        metrics=dict(actual_daily_observations=len(r),realized_annual_daily_vol=float(r.std(ddof=1)*np.sqrt(365)) if len(r)>1 else None)
        if len(r)>=30:
            roll=nav[30:]/nav[:-30]-1;i=int(np.argmin(roll));metrics.update(worst_rolling30day_return=float(roll[i]),worst30_start_us=int(start+i*DAY),worst30_end_us=int(start+(i+30)*DAY))
        body={k:case[k] for k in ('trades','funding','rejections','breaches','extrema','target_meta')};body['summary']=summary;body['targets']=case['targets'].to_dicts();body['liquidations']=case.get('liquidations',[]);save(casepath/'ACCOUNT.json',body)
        pointer=json.loads((casepath/'recovery/POINTER.json').read_text());assert pointer['completed_minutes']==summary['completed_minutes']
        report=dict(summary=summary,metrics=metrics,inventory_NAV_audit=inventory,independent_decimal_NAV_bridge=finance,audit_error=error,paid_flat=bool(summary['terminal_cash_realized']),full_calendar=summary['completed_minutes']==456*1440,liquidation_events=len(case.get('liquidations',[])),rejection_reasons=native.rejection_counts(case['rejections']),genuine_checkpoint_state_hash=pointer['state_hash'],checkpoint_rows=pointer['completed_minutes'])
        reports[arm]=report;save(casepath/'RESULT.json',report);daily.write_csv(casepath/'DAILY.csv');del sim,case,saved,minute,daily;gc.collect()
        print('CONTINUOUS_WALLET_RESULT',arm,'completed',summary['completed_minutes'],'net',summary['net_PnL'],'paidflat',report['paid_flat'],flush=True)
    full=all(r['full_calendar'] for r in reports.values());comparison=dict(status='NOT_EVALUABLE_INCOMPLETE_CALENDAR');gates=dict(full_paid_audited=all(r['full_calendar'] and r['paid_flat'] and not r['liquidation_events'] and r['inventory_NAV_audit']=='PASS' for r in reports.values()))
    if full:
        cs,vol=reports['CS_MATCHED'],reports['VOL_MATCHED'];delta=returns['CS_MATCHED']-returns['VOL_MATCHED'];rng=np.random.default_rng(811720);draws=[]
        for _ in range(1000):
            starts=rng.integers(0,len(delta),int(np.ceil(len(delta)/14)));ix=np.concatenate([(s+np.arange(14))%len(delta) for s in starts])[:len(delta)];draws.append(float(delta[ix].mean()))
        lo,hi=np.quantile(draws,[.025,.975]);periods=[]
        for a,c in [('2021-04-01','2021-07-01'),('2021-07-01','2022-01-01'),('2022-01-01','2022-07-01')]:
            left=(native.utc(a)-start)//DAY;right=(native.utc(c)-start)//DAY;cn=float(daily_nav['CS_MATCHED'][right]-daily_nav['CS_MATCHED'][left]);vn=float(daily_nav['VOL_MATCHED'][right]-daily_nav['VOL_MATCHED'][left]);periods.append(dict(calendar=[a,c],CS_continuous_NAV_change_USDT=cn,VOL_continuous_NAV_change_USDT=vn,increment_USDT=cn-vn,no_reset_or_independent_wallet=True))
        description=[]
        for label in ('UP','PULLBACK','REBOUND','DOWN','SIDEWAYS','UNKNOWN'):
            mask=states==label;description.append(dict(past_only_state=label,days=int(mask.sum()),CS_mean_actual_daily_return=float(returns['CS_MATCHED'][mask].mean()) if mask.any() else None,VOL_mean_actual_daily_return=float(returns['VOL_MATCHED'][mask].mean()) if mask.any() else None,selection_gate=False))
        volratio=cs['metrics']['realized_annual_daily_vol']/vol['metrics']['realized_annual_daily_vol'];gates.update(CS_net_positive=cs['summary']['net_PnL']>0,increment_positive=cs['summary']['net_PnL']>vol['summary']['net_PnL'],daily_bootstrap_lower_positive=float(lo)>0,all_fixed_block_increments_positive=all(p['increment_USDT']>0 for p in periods),actual_vol_ratio=volratio<=1.10,drawdown=cs['summary']['all_observation_max_drawdown']<=vol['summary']['all_observation_max_drawdown'],worst30=cs['metrics']['worst_rolling30day_return']>=vol['metrics']['worst_rolling30day_return'])
        comparison=dict(status='COMPLETE_SEEN_CONTINUOUS_PAIR',marked_net_increment_USDT=cs['summary']['net_PnL']-vol['summary']['net_PnL'],mean_actual_daily_return_difference=float(delta.mean()),bootstrap95CI=[float(lo),float(hi)],realized_vol_ratio=float(volratio),fixed_continuous_blocks=periods,past_only_state_description=description)
    report=dict(status='PASS_FIXED_CS_CONTINUOUS_GATES' if full and all(gates.values()) else 'STOP_FIXED_CS_CONTINUOUS_GATES',science_source_commit=source,attempts=1,new_native_wallets=2,new_supervised_fits=0,old_wallet_reruns=0,provider_downloads=0,planned_continuous_days=456,arms=reports,comparison=comparison,gates=gates,authority='DEFAULT_USDT_CONDITIONAL_KERNEL_FUND_UNIT_CHARGE_MARK_MMR_ARRIVAL_UNCERTIFIED',investment_candidate='NONE')
    save(state/'RESULT.json',report);save(state/'BINDINGS.json',bindings);save(state/'TIMING.json',dict(seconds=time.monotonic()-started));print(json.dumps(dict(status=report['status'],gates=gates,comparison=comparison),indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--source-commit',required=True);a=p.parse_args();run(a.state,a.prepared,a.source_commit)
