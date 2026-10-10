"""Partial-terminal calendar entry point around the unchanged financial auditor."""
from collections import defaultdict
from datetime import datetime,UTC
from decimal import Decimal as D,localcontext
from functools import lru_cache
from pathlib import Path
import sys
import q4_native92 as run
read=run.read;require=run.require;START=run.START;LAST=run.LAST;END=run.END;MINUTE=run.base.frozen.MINUTE;SYMBOLS=run.base.frozen.SYMBOLS


def verify(directory,state):
    sys.path.insert(0,str(run.HERE/'verification_helpers'))
    from modules.transformer_v3.isolated_audit import verify as financial
    import polars as pl
    audit=financial(directory/'account',list(SYMBOLS),1);s=read(directory/'account/summary.json');e=read(directory/'EXECUTION.json');trades=read(directory/'account/trades.json');funds=read(directory/'account/funding.json');liqs=read(directory/'account/liquidations.json')
    require(audit['minutes']==s['completed_minutes']==s['required_minutes']==131046 and e['execution_calendar']==run.EXECUTION_CAL and s['completion']==e['status']=='COMPLETE_CONDITIONAL_ACCOUNT','Exact91days plus original six-minute terminal required')
    require(s['terminal_cash_realized'] and s['terminal_not_forced_free_fill'] and all(p['quantity']==0 for p in s['positions'].values()) and len(liqs)==s['liquidation_count'],'Paid actual terminal flat/known liquidation witnesses required')
    require(e['elapsed_seconds']<=600 and e['peak_RSS_bytes']<=6000000000 and len(funds)==s['funding_original_events']==1370,'Frozen execution resource/funding count differs')
    work=run.locations(state)[2]/'data/normalized'
    @lru_cache(maxsize=12)
    def rows(symbol,month,kind):
        family='klines' if kind=='trade' else 'markPriceKlines';d=pl.read_parquet(work/'minute'/symbol/family/(month+'.parquet'));key='open_us' if kind=='trade' else 'timestamp_ms';return {int(r[key])*(1 if kind=='trade' else 1000):r for r in d.iter_rows(named=True)}
    def row(symbol,stamp,kind):return rows(symbol,datetime.fromtimestamp(stamp/1e6,UTC).strftime('%Y-%m'),kind)[stamp]
    rates={}
    for symbol in SYMBOLS:
        d=pl.read_parquet(work/(symbol+'_funding_events.parquet'));rates.update({(symbol,int(r['calc_time_ms'])*1000):float(r['last_funding_rate']) for r in d.iter_rows(named=True) if START<=int(r['calc_time_ms'])*1000<END})
    used=defaultdict(lambda:D(0));ordinary=0
    with localcontext() as ctx:
        ctx.prec=50
        for t in trades:
            if t.get('liquidation_takeover') or t.get('exchange_liquidation_instruction'):continue
            symbol,stamp,x=t['symbol'],t['event_us'],t['decimal_strings'];q,delta,mid,fill=(D(x[k]) for k in ('quantity','position_delta','execution_mid_price','fill_price'))
            require(stamp%MINUTE==1 and START+MINUTE+1<=stamp<END,'Original delayed actual-minute fill clock required');open_us=stamp-1
            require(mid==D(str(float(row(symbol,open_us,'trade')['open']))) and q>0 and q%D('1e-8')==0 and abs(delta)==q and t['side']==('BUY' if delta>0 else 'SELL'),'Original actual price, lot and signed side required')
            require(fill==mid*(1+(D(1) if delta>0 else D(-1))*D('.0008')) and abs(D(x['fee_amount'])-q*fill*D('.00055'))<=D('1e-18') and t['fee_asset']=='USDT','Original8bp friction and5.5bp fee required')
            require(t['leg']!='OPEN' or q*fill>=10,'Original minimum opening notional differs');used[symbol,stamp]+=q
            require(used[symbol,stamp]<=D(str(float(row(symbol,open_us-MINUTE,'trade')['quote_volume'])))*D('.001')/mid+D('1e-12') and D(x['mark_price'])==D(str(float(row(symbol,open_us-MINUTE,'mark')['close']))),'Original previous-minute capacity/mark differs')
            require(stamp>=((t['signal_us']+MINUTE-1)//MINUTE+1)*MINUTE+1,'Original signal latency differs');ordinary+=1
            if stamp>=LAST:require(t['leg']=='CLOSE' and t['signal_us']==LAST and LAST+MINUTE+1<=stamp<=LAST+5*MINUTE+1,'Terminal may only reduce in the five original eligible minutes')
        for stamp in {t['event_us'] for t in trades}:
            legs=[t['leg'] for t in trades if t['event_us']==stamp and not t.get('liquidation_takeover')];require(legs==sorted(legs,key=lambda v:v!='CLOSE'),'Original reductions-first ordering required')
        seen=set()
        for f in funds:
            key=f['symbol'],f['event_us'];require(key not in seen and f['raw_rate']==rates[key] and f['conditional_rate_scale']==1,'Original signed funding exact-once receipt differs');seen.add(key)
            if f['event_us']<START+MINUTE:require(not f['owned'] and f['quantity']==0 and f['signed_funding_USDT']==0 and f['mark_price'] is None,'Fresh first funding must remain unheld with no fabricated mark')
            elif f['mark_price'] is not None:
                prior=((f['event_us']-1)//MINUTE)*MINUTE;require(f['mark_close_us']==prior<f['event_us'] and f['mark_price']==float(row(f['symbol'],prior-MINUTE,'mark')['close']),'Actual strictly prior funding mark differs')
        require(seen==set(rates) and len(seen)==1370,'Actual scored funding domain differs')
    terminal_trades=[t for t in trades if t['event_us']>=LAST];require(terminal_trades and all(t['fee_amount']>0 for t in terminal_trades),'Actual charged terminal close required')
    terminal=dict(signal_us=LAST,producer_epsilon_close_us=LAST+MINUTE+1,first_actual_close_us=min(t['event_us'] for t in terminal_trades),last_actual_close_us=max(t['event_us'] for t in terminal_trades),close_legs=len(terminal_trades),completed_at_or_before_fifth_attempt=True,final_flat=True,additional_full_day_exposure=False,epsilon_time_daily_fill_parity_claimed=False)
    minute=pl.read_parquet(directory/'account/minute.parquet');require(minute['close_us'][0]==START+MINUTE and minute['close_us'][-1]==END and minute.height==131046,'Exact native marked minute domain required')
    lastfill=max(t['event_us'] for t in terminal_trades);after=minute.filter(pl.col('close_us')>lastfill)
    require(all(after[symbol+'_quantity'].eq(0).all() for symbol in SYMBOLS),'No residual ownership after actual paid close')
    audit.update(status='PASS_ORIGINAL_FINANCIAL_AND_ACTUAL_INPUT_PARTIAL_Q4_TERMINAL_AUDIT',capital_USDT=10000,decisions=92,held_intervals=91,terminal_minutes=6,terminal_paid_flat=True,liquidations=len(liqs),account_stitching=False,actual_input_check=dict(status='PASS_ACTUAL_FILLS_CAPACITY_FEES_MARKS_AND_FUNDING',ordinary_fill_legs=ordinary,funding_events=1370,actual_millisecond_offsets_preserved=True,independent_order_intents_reconstructed=False),terminal=terminal);return audit
