"""Recorded short-episode first-trigger trace; never an altered wallet/PnL."""
import argparse,json,os,time,resource
from pathlib import Path
from datetime import UTC,datetime
import polars as pl
import numpy as np
from quant.paths import ROOT,STATE
from scripts.investment.chandelier_short_levels import levels,RULES,PACKAGE
from scripts.investment.multi_asset_data import load_portfolio_window
from scripts.investment.run_cta_leaderboard import stamp,sha
from scripts.research_v7.oracle_flow_ceiling import Progress

DAY=86400000000;MINUTE=60000000
DEFAULT_PRODUCER='reports/fast_research/SHORT_CONFIRMATION_BASE27_20261006_V1.json'

def episodes_from_trades(trades):
    episodes=[];active={}
    assert all(a['event_us']<=b['event_us'] for a,b in zip(trades,trades[1:]))
    for v in trades:
        if v['quantity_before']==0 and v['quantity_after']<0:
            assert v['symbol'] not in active
            z=dict(symbol=v['symbol'],first_fill_us=v['event_us'],entry_mid=v['mid_price'],first_signal_us=v['signal_us'])
            episodes.append(z);active[v['symbol']]=z
        if v['quantity_before']<0 and v['quantity_after']==0:
            active.pop(v['symbol'])['actual_flat_us']=v['event_us']
        assert not (v['quantity_before']<0 and v['quantity_after']>0),'Reversal must contain paid flatten leg'
    assert not active,'Open recorded episodes cannot be silently dropped'
    return episodes

def verify_public_lines(indicator,bars,symbols):
    """Scalar audit of installed SMA-seeded Wilder ATR, not a trading kernel."""
    error=0.;lookup={(v['available_us'],v['symbol']):v['short_exit_line'] for v in indicator.iter_rows(named=True)}
    for s in symbols:
        b=list(bars.filter(pl.col('symbol')==s).sort('close_us').iter_rows(named=True));trs=[];atr=None
        for j,r in enumerate(b):
            if j:
                tr=max(r['high']-r['low'],abs(r['high']-b[j-1]['close']),abs(r['low']-b[j-1]['close']))
                assert tr>0
                trs.append(tr)
                if j==22:atr=sum(trs)/22
                elif j>22:atr=atr*21/22+tr/22
            expected=None if atr is None else min(v['low'] for v in b[j-21:j+1])+3*atr
            actual=lookup[r['available_us'],s]
            assert (actual is None)==(expected is None)
            if expected is not None:error=max(error,abs(actual-expected)/max(1.,abs(expected)))
    assert error<1e-12,error
    return dict(status='PASS_INDEPENDENT_SCALAR_CE_WILDER22_SMA_SEED',maximum_relative_error=error)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--producer',default=DEFAULT_PRODUCER)
    ap.add_argument('--output',default='reports/SHORT_CHANDELIER_EPISODE_TRACE_20261006_V1.json')
    ap.add_argument('--protocol');a=ap.parse_args();out=(ROOT/a.output).resolve()
    assert out.is_relative_to(ROOT/'reports') and not out.exists()
    p=(ROOT/a.producer).resolve();assert p.is_relative_to(ROOT/'reports/fast_research')
    raw=json.loads(p.read_bytes());s=raw['protocol'];started=time.monotonic();progress=Progress()
    try:
        if a.protocol:
            spec=json.loads((ROOT/a.protocol).read_bytes())
            assert spec['producer']==dict(path=a.producer,sha256=sha(p)) and spec['rule']==RULES
            assert spec['configurations']==1 and spec['new_accounts']==0 and spec['models_fit']==0
        assert sha(ROOT/'state/dataset_lock.json')==s['locked_sha256']
        assert sha(s['data_manifest']['path'])==s['data_manifest']['sha256']
        task=json.loads((STATE/'task-progress'/('task-'+raw['binding']['task_id']+'.json')).read_bytes())
        assert task['status']=='completed' and task['exit_code']==0
        c=next(c for c in raw['cases'] if c['mode']=='LONG_SHORT' and c['unit']=='RAW_AS_PERCENT')
        assert c['summary']['terminal_cash_realized']
        ref=c['artifacts']['trades.json'];assert sha(ref['path'])==ref['sha256']
        episodes=episodes_from_trades(json.loads(Path(ref['path']).read_bytes()))
        old=ROOT/'reports/fast_research/SHORT_CONFIRMATION_BASE27_20261006_V1.json'
        old_raw=json.loads(old.read_bytes());old_c=next(v for v in old_raw['cases'] if v['unit']=='RAW_AS_PERCENT')
        old_ref=old_c['artifacts']['trades.json'];assert sha(old_ref['path'])==old_ref['sha256']
        saved=json.loads((ROOT/'reports/SHORT_CHANDELIER_EPISODE_TRACE_20261006_V1.json').read_bytes())
        assert episodes_from_trades(json.loads(Path(old_ref['path']).read_bytes()))==[
            {k:z[k] for k in ('symbol','first_fill_us','entry_mid','first_signal_us','actual_flat_us')} for z in saved['episodes']]
        begin=stamp(s['economics_start']);end=stamp(s['economics_end_exclusive']);symbols=tuple(s['symbols'])
        cycle=s.get('input_adapter')=='FIXED_BTC_ETH_2022_2023_CYCLE'
        if cycle:
            from scripts.investment.cta_cycle_window import load_window
            whole=load_window(s['data_manifest']['path'],symbols,stamp(s['preparation_start']),end)
        else:whole=load_portfolio_window(s['data_manifest']['path'],symbols,begin,end)
        bars=whole['daily'];indicator=levels(bars,symbols);line_audit=verify_public_lines(indicator,bars,symbols)
        cutoff=begin+(end-begin)//2//DAY*DAY
        changed=bars.with_columns(*[pl.when(pl.col('close_us')>cutoff).then(pl.col(k)*1.8).otherwise(pl.col(k)).alias(k) for k in ('open','high','low','close')])
        future=levels(changed,symbols)
        assert indicator.filter(pl.col('available_us')<=cutoff).equals(future.filter(pl.col('available_us')<=cutoff))
        old_runtime=json.loads((ROOT/'reports/SHORT_CHANDELIER_PROBE_20261006_V1.json').read_bytes())['supplementary_runtime']
        for name,digest in old_runtime['installed_file_sha256'].items():assert sha(PACKAGE/name)==digest,name
        lookup={(v['available_us'],v['symbol']):v['short_exit_line'] for v in indicator.iter_rows(named=True)}
        manifest=json.loads(Path(s['data_manifest']['path']).read_bytes())
        records={(v['symbol'],v['month']):v for v in manifest['market_records'] if v['kind']=='klines'}
        signal=pl.read_parquet(Path(raw['run_dir'])/'frozen_signals.parquet')
        family=c['strategy'];signal_lookup={(v['close_us'],v['symbol']):v[family] for v in signal.iter_rows(named=True)}
        for i,z in enumerate(episodes):
            first=z['first_fill_us'];last=z['actual_flat_us'];symbol=z['symbol'];trail=None
            for day in range(first//DAY*DAY,last//DAY*DAY+1,DAY):
                line=lookup[day,symbol];assert line is not None and line>0
                trail=min(trail,line) if trail is not None else line
                month=datetime.fromtimestamp(day//1000000,UTC).strftime('%Y-%m');r=records[symbol,month]
                left=max(day,(first//MINUTE+1)*MINUTE);right=min(day+DAY,last//MINUTE*MINUTE)
                if right<=left:continue
                prices=pl.scan_parquet(r['normalized_path']).filter((pl.col('open_us')>=left)&(pl.col('close_us')<=right)).select('open_us','close_us','available_us','close').sort('open_us').collect()
                assert np.array_equal(prices['open_us'].to_numpy(),np.arange(left,right,MINUTE))
                assert prices['available_us'].equals(prices['close_us'])
                cross=prices.filter(pl.col('close')>trail)
                if cross.height:
                    trigger=int(cross['close_us'][0]);next_decision=(trigger//DAY+1)*DAY
                    next_signal=signal_lookup.get((next_decision,symbol))
                    z.update(first_public_trailing_trigger_us=trigger,known_stop_line=trail,trigger_trade_close=float(cross['close'][0]),
                        earliest_eligible_open_us=trigger+MINUTE,days_before_actual_flat=(last-trigger)/DAY,
                        original_next_daily_forecast=next_signal,
                        immediate_reentry_intent_if_no_latch=bool(next_signal is not None and next_signal<0))
                    break
            z.setdefault('first_public_trailing_trigger_us',None)
            progress.update('完整原空头持仓：CE保护与原重入意图',i+1,len(episodes),'持仓')
            assert time.monotonic()-started<180 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<800000000
        worst=[] if cycle else [stamp(v['date']) for v in json.loads((ROOT/'reports/SHORT_REBOUND_TIMING_20261006_V1.json').read_bytes())['days']]
        covered=[]
        for day in worst:
            held=[z for z in episodes if z['first_fill_us']<day and z['actual_flat_us']>day]
            covered.append(dict(date=datetime.fromtimestamp(day//1000000,UTC).date().isoformat(),actual_episode_symbols=[z['symbol'] for z in held],
                earlier_CE_trigger_symbols=[z['symbol'] for z in held if z['first_public_trailing_trigger_us'] is not None and z['first_public_trailing_trigger_us']<day],
                scope='ORIGINAL_POSITION_TRAJECTORY_SHADOW_TRIGGER; NEW_CE_WALLET_OR_REENTRY_NOT_EVALUATED'))
        result=dict(status='PASS_FULL_RECORDED_EPISODE_CAUSAL_CE_TRACE_NOT_ECONOMIC_REPLAY',task_id=os.environ['COIN_TASK_ID'],
            created_utc=datetime.now(UTC).isoformat(),source_sha256=sha(__file__),producer_sha256=sha(p),producer=a.producer,public_rule=RULES,
            adapter='SHORT_STOP_RATCHETS_MIN_CLOSED_DAILY_CE; FIRST_FULL_MINUTE_AFTER_FILL; CLOSE_OBSERVATION_NEXT_DELAYED_OPEN_REQUIRED',
            input_manifest=s['data_manifest'],input_role=s['data_role'],episodes=episodes,worst_day_earlier_triggers=covered,
            public_library=old_runtime,independent_line_audit=line_audit,old_episode_extraction_golden='PASS_ALL24_ORIGINAL_RECORDS',
            future_perturbation='PASS_ALL_LINES_BEFORE_CUTOFF_UNCHANGED',new_accounts=0,new_net_return='NOT_RUN',fits=0,new_downloads=0,
            elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            limitation='SHADOW_TRIGGER_NEVER_FILTERED_PNL; REENTRY_INTENT_NOT_FILL; COMPLETE_NEW_ACCOUNT_REQUIRED_FOR_IMPROVEMENT')
        with out.open('x') as f:json.dump(result,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
        print(json.dumps(dict(status=result['status'],episodes=len(episodes),triggered=sum(z['first_public_trailing_trigger_us'] is not None for z in episodes),
            next_day_reentry_intents=sum(z.get('immediate_reentry_intent_if_no_latch',False) for z in episodes))))
    finally:progress.stop.set();progress.thread.join(timeout=3)

if __name__=='__main__':main()
