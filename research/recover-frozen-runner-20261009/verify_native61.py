"""Independent native61 journal reconciliation and optional actual-input checks."""
import argparse
from collections import defaultdict
from datetime import datetime, UTC
from decimal import Decimal as D, localcontext
from functools import lru_cache
import json
import os
from pathlib import Path
import resource
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'verification_helpers'))
START, END, MINUTE = 1714521600000000, 1719792000000000, 60000000
SYMBOLS = ('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_bytes())


def verify(directory, state=None, *, calendar=None, market_work=None):
    start,end,days,minutes,funding=(START,END,61,87840,915) if calendar is None else tuple(calendar[k] for k in ('start','end_exclusive','days','minutes','funding_events'))
    require(end-start==days*86400000000 and minutes==days*1440,'Audit calendar dimensions differ')
    from modules.transformer_v3.isolated_audit import verify as financial
    account = directory / 'account'
    audit = financial(account, list(SYMBOLS), 1)
    summary, execution = read(account/'summary.json'), read(directory/'EXECUTION.json')
    require(audit['minutes'] == summary['completed_minutes'] == summary['required_minutes'] == minutes, 'Full61 minutes required')
    require(summary['completion'] == execution['status'] == 'COMPLETE_CONDITIONAL_ACCOUNT', 'Completed native account required')
    require(summary['terminal_cash_realized'] and summary['terminal_not_forced_free_fill'] and all(p['quantity']==0 for p in summary['positions'].values()), 'Paid actual terminal flat required')
    funds, trades, liqs = read(account/'funding.json'), read(account/'trades.json'), read(account/'liquidations.json')
    require(len(funds) == summary['funding_original_events'] == funding, 'Full actual funding calendar required')
    require(len(liqs) == summary['liquidation_count'], 'Liquidation witnesses differ')
    require(execution['elapsed_seconds'] <= 600 and execution['peak_RSS_bytes'] <= 6_000_000_000, 'Frozen wallet resource cap exceeded')
    require(any(t['leg']=='CLOSE' and t['fee_amount']>0 for t in trades), 'Actual paid closes required')
    require(all(not f['owned'] and f['quantity']==0 and f['signed_funding_USDT']==0 for f in funds if f['event_us']<start+MINUTE), 'Fresh first funding must be unheld')
    audit.update(continuous_days=days, capital_USDT=10000, terminal_paid_flat=True, liquidations=len(liqs), account_stitching=False)
    if state is not None:
        import polars as pl
        base = (market_work or state / 'h1_validation/original/h1_market') / 'data/normalized'
        @lru_cache(maxsize=12)
        def rows(symbol, month, kind):
            family = 'klines' if kind == 'trade' else 'markPriceKlines'
            d = pl.read_parquet(base/'minute'/symbol/family/(month+'.parquet'))
            key = 'open_us' if kind == 'trade' else 'timestamp_ms'
            return {int(r[key])*(1 if kind=='trade' else 1000): r for r in d.iter_rows(named=True)}
        def row(symbol, stamp, kind):
            month = datetime.fromtimestamp(stamp/1e6,UTC).strftime('%Y-%m')
            return rows(symbol,month,kind)[stamp]
        rates = {}
        for s in SYMBOLS:
            f = pl.read_parquet(base/(s+'_funding_events.parquet'))
            rates.update({(s,int(r['calc_time_ms'])*1000):float(r['last_funding_rate']) for r in f.iter_rows(named=True) if start<=int(r['calc_time_ms'])*1000<end})
        used = defaultdict(lambda:D(0)); ordinary = 0
        with localcontext() as c:
            c.prec = 50
            for t in trades:
                if t.get('liquidation_takeover') or t.get('exchange_liquidation_instruction'):
                    continue
                s, stamp, e = t['symbol'], t['event_us'], t['decimal_strings']
                q, delta, mid, fill = (D(e[k]) for k in ('quantity','position_delta','execution_mid_price','fill_price'))
                require(stamp%MINUTE==1 and stamp>=start+MINUTE+1, 'Native delayed minute-open fill required')
                open_us=stamp-1
                require(mid==D(str(float(row(s,open_us,'trade')['open']))), 'Actual trade-open mid differs')
                require(q>0 and q%D('1e-8')==0 and abs(delta)==q and t['side']==('BUY' if delta>0 else 'SELL'), 'Native lot/signed side differs')
                require(fill==mid*(1+(D(1) if delta>0 else D(-1))*D('.0008')), 'Original8bp execution friction differs')
                require(abs(D(e['fee_amount'])-q*fill*D('.00055'))<=D('1e-18') and t['fee_asset']=='USDT', 'Original fee differs')
                require(t['leg']!='OPEN' or q*fill>=10, 'Original minimum opening notional differs')
                used[s,stamp]+=q
                require(used[s,stamp]<=D(str(float(row(s,open_us-MINUTE,'trade')['quote_volume'])))*D('.001')/mid+D('1e-12'), 'Shared previous quote capacity exceeded')
                require(D(e['mark_price'])==D(str(float(row(s,open_us-MINUTE,'mark')['close']))), 'Actual prior completed fill mark differs')
                require(stamp>=((t['signal_us']+MINUTE-1)//MINUTE+1)*MINUTE+1, 'Original signal latency differs')
                ordinary+=1
            for stamp in {t['event_us'] for t in trades}:
                legs=[t['leg'] for t in trades if t['event_us']==stamp and not t.get('liquidation_takeover')]
                require(legs==sorted(legs,key=lambda leg:leg!='CLOSE'), 'Reductions must precede increases')
            seen=set()
            for f in funds:
                key=f['symbol'],f['event_us'];require(key not in seen and f['raw_rate']==rates[key] and f['conditional_rate_scale']==1, 'Exact-once actual signed funding differs');seen.add(key)
                if f['event_us']<start+MINUTE:
                    require(f['mark_price'] is None, 'Fresh first funding invented a mark')
                elif f['mark_price'] is not None:
                    # Actual Binance settlements retain their millisecond
                    # offsets. Select the latest completed grid mark strictly
                    # before the actual event; never round the event itself.
                    prior_close = ((f['event_us'] - 1) // MINUTE) * MINUTE
                    require(f['mark_close_us']==prior_close<f['event_us'] and f['mark_price']==float(row(f['symbol'],prior_close-MINUTE,'mark')['close']), 'Strictly prior completed funding mark differs')
            require(seen==set(rates), 'Actual funding event coverage differs')
        audit['actual_input_check']=dict(status='PASS_ACTUAL_FILLS_CAPACITY_FEES_MARKS_AND_FUNDING',ordinary_fill_legs=ordinary,funding_events=len(funds),actual_settlement_millisecond_offsets_preserved=True,independent_order_intents_reconstructed=False)
    return audit


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True);p.add_argument('--state',type=Path);p.add_argument('--write',action='store_true');a=p.parse_args()
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6_000_000_000,6_000_000_000))
    report=verify(a.directory,a.state)
    if a.write:
        with (a.directory/'INDEPENDENT_AUDIT.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({k:report[k] for k in ['status','minutes','maximum_NAV_error_USDT','maximum_wallet_error_USDT','terminal_paid_flat','liquidations'] }|dict(actual_input_check=report.get('actual_input_check'))),flush=True)


if __name__=='__main__':main()
