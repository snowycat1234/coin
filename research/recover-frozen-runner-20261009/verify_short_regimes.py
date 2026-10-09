"""Frozen independent financial audit plus actual-source checks for three windows."""
import argparse
from collections import defaultdict
from datetime import datetime,UTC
from decimal import Decimal as D,localcontext
from functools import lru_cache
import json,os
from pathlib import Path
import resource,sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'verification_helpers'))
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
MINUTE=60000000


def require(ok,message):
    if not ok:raise ValueError(message)


def read(p):return json.loads(p.read_bytes())


def actual_bear(state,directory,start,end):
    """Same actual-source equations as verify_native61; calendar/root explicit."""
    import polars as pl
    base=state/'e5-bear-original/original/bear_recovery_data/data/normalized'
    @lru_cache(maxsize=12)
    def rows(s,month,kind):
        family='klines' if kind=='trade' else 'markPriceKlines'
        d=pl.read_parquet(base/'minute'/s/family/(month+'.parquet'));key='open_us' if kind=='trade' else 'timestamp_ms'
        return {int(r[key])*(1 if kind=='trade' else 1000):r for r in d.iter_rows(named=True)}
    def row(s,t,kind):return rows(s,datetime.fromtimestamp(t/1e6,UTC).strftime('%Y-%m'),kind)[t]
    rates={}
    for s in SYMBOLS:
        f=pl.read_parquet(base/(s+'_funding_events.parquet'))
        rates.update({(s,int(r['calc_time_ms'])*1000):float(r['last_funding_rate']) for r in f.iter_rows(named=True) if start<=int(r['calc_time_ms'])*1000<end})
    trades=read(directory/'account/trades.json');funds=read(directory/'account/funding.json');used=defaultdict(lambda:D(0));ordinary=0
    with localcontext() as c:
        c.prec=50
        for t in trades:
            if t.get('liquidation_takeover') or t.get('exchange_liquidation_instruction'):continue
            s,stamp,e=t['symbol'],t['event_us'],t['decimal_strings'];q,delta,mid,fill=(D(e[k]) for k in ('quantity','position_delta','execution_mid_price','fill_price'))
            require(stamp%MINUTE==1 and stamp>=start+MINUTE+1,'Original delayed minute-open fill required');op=stamp-1
            require(mid==D(str(float(row(s,op,'trade')['open']))),'Actual trade-open mid differs')
            require(q>0 and q%D('1e-8')==0 and abs(delta)==q and t['side']==('BUY' if delta>0 else 'SELL'),'Original lot/signed side differs')
            require(fill==mid*(1+(D(1) if delta>0 else D(-1))*D('.0008')),'Original8bp friction differs')
            require(abs(D(e['fee_amount'])-q*fill*D('.00055'))<=D('1e-18') and t['fee_asset']=='USDT','Original fee differs')
            require(t['leg']!='OPEN' or q*fill>=10,'Original opening minnotional differs')
            used[s,stamp]+=q
            require(used[s,stamp]<=D(str(float(row(s,op-MINUTE,'trade')['quote_volume'])))*D('.001')/mid+D('1e-12'),'Shared previous-minute quote capacity exceeded')
            require(D(e['mark_price'])==D(str(float(row(s,op-MINUTE,'mark')['close']))),'Actual completed fill mark differs')
            require(stamp>=((t['signal_us']+MINUTE-1)//MINUTE+1)*MINUTE+1,'Original signal latency differs');ordinary+=1
        for stamp in {r['event_us'] for r in trades}:
            legs=[r['leg'] for r in trades if r['event_us']==stamp and not r.get('liquidation_takeover')]
            require(legs==sorted(legs,key=lambda x:x!='CLOSE'),'Reductions must precede increases')
        seen=set()
        for f in funds:
            key=f['symbol'],f['event_us'];require(key not in seen and f['raw_rate']==rates[key] and f['conditional_rate_scale']==1,'Exact-once actual signed funding differs');seen.add(key)
            if f['event_us']==start:require(f['mark_price'] is None and not f['owned'],'Fresh first funding invented holdings/mark')
            elif f['mark_price'] is not None:
                prior=((f['event_us']-1)//MINUTE)*MINUTE
                require(f['mark_close_us']==prior<f['event_us'] and f['mark_price']==float(row(f['symbol'],prior-MINUTE,'mark')['close']),'Strictly prior actual funding mark differs')
        require(seen==set(rates),'Actual funding coverage differs')
    return dict(status='PASS_ACTUAL_FILLS_CAPACITY_FEES_MARKS_AND_FUNDING',ordinary_fill_legs=ordinary,funding_events=len(funds),actual_millisecond_offsets_preserved=True,independent_order_intents_reconstructed=False)


def verify(directory,state=None):
    from modules.transformer_v3.isolated_audit import verify as financial
    s=read(directory/'account/summary.json');e=read(directory/'EXECUTION.json');spec=e['calendar']
    audit=financial(directory/'account',list(SYMBOLS),1)
    require(audit['minutes']==s['completed_minutes']==s['required_minutes']==spec['days']*1440,'Full explicit regime account required')
    require(s['completion']==e['status']=='COMPLETE_CONDITIONAL_ACCOUNT','Incomplete account')
    require(s['terminal_cash_realized'] and s['terminal_not_forced_free_fill'] and all(p['quantity']==0 for p in s['positions'].values()),'Actual paid terminal flat required')
    trades=read(directory/'account/trades.json');funds=read(directory/'account/funding.json');liqs=read(directory/'account/liquidations.json')
    require(len(funds)==s['funding_original_events'] and len(liqs)==s['liquidation_count'],'Original funding/liquidation witnesses differ')
    require(e['elapsed_seconds']<=600 and e['peak_RSS_bytes']<=6000000000,'Frozen resource cap exceeded')
    require(not trades or any(t['leg']=='CLOSE' and t['fee_amount']>0 for t in trades),'Actual paid close required for traded account')
    require(all(t['quantity_before']<=0 and t['quantity_after']<=0 for t in trades),'Forbidden long fill inventory')
    audit.update(continuous_days=spec['days'],capital_USDT=10000,terminal_paid_flat=True,liquidations=len(liqs),account_stitching=False,activity='ACTIVELY_TRADED' if trades else 'INACTIVE_ZERO_TRADING_NOT_ALPHA')
    if state is not None:
        if e['case']=='OKX86':
            sys.path.insert(0,str(HERE));import verify_market_execution
            audit['actual_input_check']=verify_market_execution.verify(state,directory)
        else:audit['actual_input_check']=actual_bear(state,directory,spec['start'],spec['end'])
    return audit


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True);p.add_argument('--state',type=Path);p.add_argument('--write',action='store_true');a=p.parse_args()
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','POLARS_MAX_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6000000000,6000000000))
    r=verify(a.directory,a.state)
    if a.write:
        with (a.directory/'INDEPENDENT_AUDIT.json').open('x') as f:json.dump(r,f,indent=2);f.write('\n')
    print(json.dumps({k:r[k] for k in ('status','minutes','maximum_NAV_error_USDT','maximum_wallet_error_USDT','terminal_paid_flat','liquidations','activity')}|dict(actual_input_check=r.get('actual_input_check'))),flush=True)
