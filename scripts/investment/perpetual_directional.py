"""Fixed conditional four-direction research using supplied target/account APIs.

Binance trade opens are latency/capacity proxies; Bybit fees and assumed risk
tiers are not native execution. No account transport, fitting or rate inference.
"""
from __future__ import annotations
import argparse, gc, hashlib, json, math, os, resource, shlex, subprocess, sys, time
from bisect import bisect_left
from datetime import UTC, datetime
from pathlib import Path
import numpy as np
import polars as pl
from quant import disk, resources
from quant.execution_contract import ExecutionContractV2
from quant.metrics import daily_metrics
from quant.paths import ROOT, STATE
from quant.perpetual_account import PerpetualConfig, USDTLinearPerpetualAccount, SYMBOLS, D, ZERO, HALTS
from scripts.investment import public_sma_perpetual as strategy
from scripts.research_v8 import funding_price_source_v2 as support
from scripts.research_v8.registry import FIELDS, append_event

MINUTE=60_000_000
DAY=86_400_000_000
CONTRACT='USDM_DIRECTIONAL_TWO_PERIOD_CONDITIONAL_20261003_V1'
STATUS='COMPLETE_CONDITIONAL_USDM_FOUR_DIRECTION_SCREENING_NOT_NATIVE_OR_LONG_TERM_APR'
MANIFEST_STATUS='BOUND_LONG_SHORT_USDM_INPUT_METADATA_ONLY_NOT_SOURCE_OR_ECONOMIC_ACCEPTANCE'
COSTS=[dict(id='BASE27',half_spread_bps=4,slippage_bps=4,roundtrip_bps=27),
       dict(id='STRESS43',half_spread_bps=8,slippage_bps=8,roundtrip_bps=43)]
UNITS=[dict(id='RAW_AS_FRACTION',scale=1.0),dict(id='RAW_AS_PERCENT',scale=.01)]
RULES=dict(initial_capital_USDT=10000.,symbols=list(SYMBOLS),modes=list(strategy.MODES),
    annual_vol_target=.10,past_covariance_completed_days=30,asset_abs_cap=.3,gross_cap=.6,
    leverage=1,margin_mode='ISOLATED',MMR=.005,MMR_native_certified=False,
    sizing_buffer=.99,quantity_step_assumption=1e-8,min_notional_assumption_USDT=10.,
    taker_fee_bps_per_side=5.5,signal='ORIGINAL_SMA50_200_COMPLETE_DAILY_HOOKS',
    sizing='FROZEN_SIGNAL_NAV_AND_CLOSED_DAILY_TRADE_PRICE',
    fill='FIRST_TRADE_OPEN_AT_OR_AFTER_EXECUTION_V2_ONE_MINUTE_LATENCY_PLUS_1US',
    capacity='PREVIOUS_COMPLETED_MINUTE_QUOTE_VOLUME_TIMES_0.001_DIVIDED_BY_FILL_MID',
    maximum_attempts=5,participation_rate=.001,
    order_sequence='FUNDING_THEN_ALL_REDUCTIONS_THEN_INCREASES_AT_OPEN_PLUS_1US',
    risk='NEXT_ELIGIBLE_OPEN_REDUCE_EXISTING_GROSS_TO_BUFFERED_CAPS_NO_TOP_UP',
    risk_unfilled='STOP_INCOMPLETE_CASE_AFTER_FIVE_UNEXECUTABLE_RISK_ATTEMPTS',
    terminal='SIGNAL_END_MINUS_6_MINUTES_FIVE_CAPACITY_LIMITED_ATTEMPTS_NO_FREE_CLOSE',
    funding='SIGNED_ACTUAL_OWNED_QUANTITY_TIMES_STRICTLY_PAST_MARK_NEG_RATE',
    funding_unit='UNCONFIRMED_TWO_PREDECLARED_CONDITIONAL_SCALES',
    fresh_flat_missing_mark='NO_POSITION_NO_PAST_MARK_KNOWN_ZERO_OWNERSHIP',
    halt='STOP_NOT_SIMULATED_LIQUIDATION_NO_RESCUE_OR_COMPLETED_NAV_CLAIM',
    windows_independent=True,monthly_reset=False,locked_consumed=False,native_market_certified=False)

def need(ok,message):
    if not bool(ok):raise ValueError(message)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def small(path):
    p=Path(path);need(p.stat().st_size<=2_000_000,'Small metadata only')
    return json.loads(p.read_bytes())

def write(path,value):
    with Path(path).open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')

def relative_proof(entry):
    p=(ROOT/entry['path']).resolve()
    need(p.is_relative_to(ROOT) and sha(p)==entry['sha256'],'Exact project proof bytes')
    v=small(p)
    if 'required_status' in entry:need(v['status']==entry['required_status'],'Required actual proof status')
    return v

def source_frame(manifest,ids):
    frames=[];proofs=[]
    for key in ids:
        entry=manifest['source_files'][key];p=Path(entry['normalized_path']).resolve()
        need(p.is_relative_to(STATE) and p.stat().st_size==entry['normalized_bytes']
            and sha(p)==entry['normalized_sha256'],'Accepted input byte binding, not repeated data QA')
        frames.append(pl.read_parquet(p))
        proofs.append(dict(id=key,path=str(p),sha256=entry['normalized_sha256'],bytes=p.stat().st_size,
            rows=entry['rows'],format_evidence_role=entry['format_evidence_role']))
    return pl.concat(frames,how='vertical'),proofs

def load_window(manifest,window,*,trade_ranges=False):
    """Read each required economic input once; no old QA, index or raw archive."""
    start=int(datetime.fromisoformat(window['start']).timestamp()*1_000_000)
    end=int(datetime.fromisoformat(window['end_exclusive']).timestamp()*1_000_000)
    need(end<=int(datetime(2026,3,1,tzinfo=UTC).timestamp()*1_000_000),'Locked boundary')
    symbols=strategy.symbol_order(tuple(window['symbols']))
    market={};daily=[];funding=[];proofs=[]
    for symbol in symbols:
        ids=window['symbols'][symbol]['source_ids']
        traded,p=source_frame(manifest,ids['trade_1m']);proofs+=p
        marks,p=source_frame(manifest,ids['mark_1m']);proofs+=p
        bars,p=source_frame(manifest,ids['trade_1d_warmup']+ids['trade_1d_score']);proofs+=p
        rates,p=source_frame(manifest,ids['funding']);proofs+=p
        traded=traded.sort('open_us');marks=marks.sort('timestamp_ms');rates=rates.sort('calc_time_ms')
        times=traded['open_us'].to_numpy()
        need(np.array_equal(times,np.arange(start,end,MINUTE,dtype=np.int64))
            and np.array_equal(marks['timestamp_ms'].to_numpy()*1000,times),
            'Required shared complete score calendar, no dropping or filling rows')
        need(traded['close_us'].eq(traded['open_us']+MINUTE).all()
            and traded['available_us'].eq(traded['close_us']).all()
            and marks['close_time_ms'].eq(marks['timestamp_ms']+59999).all(),
            'Required execution and mark closure semantics')
        trade_columns=['open','close','quote_volume']
        if trade_ranges:trade_columns+=['high','low','volume']
        selected=traded.select(trade_columns).to_numpy()
        mark_values=marks['close'].to_numpy()
        need(np.isfinite(selected).all() and np.isfinite(mark_values).all()
            and np.all(selected[:,:2]>0) and np.all(selected[:,2]>=0) and np.all(mark_values>0),
            'Finite actual prices and capacity; no substitution')
        market[symbol]=dict(open=selected[:,0],close=selected[:,1],quote_volume=selected[:,2],mark=mark_values)
        if trade_ranges:
            need(np.all(selected[:,3:5]>0) and np.all(selected[:,5]>=0),
                 'Observed positive stop ranges and nonnegative official volume')
            market[symbol].update(high=selected[:,3],low=selected[:,4],volume=selected[:,5])
        daily.append(bars.sort('close_us'))
        for row in rates.iter_rows(named=True):
            e=int(row['calc_time_ms'])*1000;raw=float(row['last_funding_rate'])
            need(start<=e<end and math.isfinite(raw),'Original signed funding and allowed event time')
            funding.append(dict(symbol=symbol,event_us=e,raw_rate=raw,
                reported_interval_hours=float(row['funding_interval_hours'])))
        del traded,marks,bars,rates
    funding.sort(key=lambda r:(r['event_us'],r['symbol']))
    need(len({(r['symbol'],r['event_us']) for r in funding})==len(funding),'Funding event exact-once identities')
    need(len(funding)==sum(window['symbols'][s]['rows_inherited_from_receipts']['funding'] for s in symbols),
         'All accepted signed events included once; unknown never filled with zero')
    return dict(symbols=symbols,start=start,end=end,times=np.arange(start,end,MINUTE,dtype=np.int64),
        market=market,daily=pl.concat(daily).sort(['symbol','close_us']),events=funding,input_proofs=proofs)

def empty_frame(schema):return pl.DataFrame(schema=schema)

def journals_frame(rows,schema):
    if not rows:return empty_frame(schema)
    # Exact Decimal strings remain in the JSON journal, simple columns in Parquet.
    return pl.DataFrame([{k:r.get(k) for k in schema} for r in rows],schema=schema)

def simulate(window,mode,cost,unit,progress=None,guard=None,*,target_factory=None,account_factory=None,event_strategy=None):
    """Only event scheduling and output bookkeeping; finances belong to account."""
    symbols=strategy.symbol_order(window.get('symbols',SYMBOLS))
    start,end=window['start'],window['end']
    times=np.arange(start,end,MINUTE,dtype=np.int64);n=len(times)
    target_factory=target_factory or (lambda b,d,m:strategy.fixed_targets(b,d,m,symbols=symbols))
    account_factory=account_factory or USDTLinearPerpetualAccount
    decisions=np.arange(start,end,DAY,dtype=np.int64)
    if event_strategy is None:
        targets,meta=target_factory(window['daily'],decisions,mode)
        need(targets.height==len(symbols)*len(decisions),'Complete ordered portfolio target calendar')
    else:
        need(mode in strategy.MODES,'Explicit event direction')
        histories=event_strategy.prepare_signal_context(window)
        targets,meta=None,None
    weights={}
    decision_kinds={}
    for t in decisions if event_strategy is None else ():
        rows=targets.filter(pl.col('available_us')==t)
        need(rows.height==len(symbols) and set(rows['symbol'].to_list())==set(symbols),
             'Every decision has each configured symbol exactly once')
        weights[int(t)]={row['symbol']:row['target_weight'] for row in rows.iter_rows(named=True)}
        decision_kinds[int(t)]={}
        for row in rows.iter_rows(named=True):
            reason=row.get('eligibility_reason','ELIGIBLE')
            kind=('POOL_EXIT' if reason=='POOL_EXIT' else
                  'DATA_GAP_EXIT' if reason=='WARMUP_OR_DATA_GAP' else 'DAILY_TARGET')
            need(kind=='DAILY_TARGET' or row['target_weight']==0,'Exit targets cannot add risk')
            decision_kinds[int(t)][row['symbol']]=kind
    daily_prices={s:dict(zip(window['daily'].filter(pl.col('symbol')==s)['close_us'].to_list(),
        window['daily'].filter(pl.col('symbol')==s)['close'].to_list(),strict=True)) for s in symbols}
    config=PerpetualConfig(half_spread_bps=D(str(cost['half_spread_bps'])),slippage_bps=D(str(cost['slippage_bps'])))
    account=account_factory(config,symbols=symbols)
    bridge=None if event_strategy is None else event_strategy.bridge_factory(account,mode)
    # Array columns: NAV/free/margin/gross/net, cumulative fees/cost/funding/turnover,
    # N signed quantities/marks/isolated balances/equities and asset weights.
    values=np.empty((n,11+5*len(symbols)),dtype=np.float64)
    rows_written=0;event_cursor=0;pending={};sequence=0;terminal=False
    funding_journal=[];rejections=[];breaches=[];extrema=[]
    peak=10000.;mdd=0.;min_nav=10000.;min_free=10000.;max_gross=0.;max_asset={s:0. for s in symbols}
    completion='COMPLETE_CONDITIONAL_ACCOUNT';stop=None
    first_entry=None;nearest_funding_ties=[]

    def observe(stamp,cause):
        nonlocal peak,mdd,min_nav,min_free,max_gross
        nav=float(account.nav());need(math.isfinite(nav),'Finite account NAV')
        min_free=min(min_free,float(account.free_cash))
        before=(peak,min_nav,mdd);peak=max(peak,nav);min_nav=min(min_nav,nav)
        if peak>0:mdd=max(mdd,1-nav/peak)
        signed={s:float(account.positions[s].quantity)*float(account.marks[s][-1]['price'])
                if account.positions[s].quantity else 0. for s in symbols}
        gross=sum(abs(x) for x in signed.values())/nav if nav>0 else None
        if gross is not None:
            max_gross=max(max_gross,gross)
            for s in symbols:max_asset[s]=max(max_asset[s],abs(signed[s])/nav)
        if before!=(peak,min_nav,mdd):
            # Only final extrema witnesses, not a second unbounded minute ledger.
            for label,changed in [('MAX_PEAK',before[0]!=peak),('MIN_NAV',before[1]!=min_nav),('MAX_DRAWDOWN',before[2]!=mdd)]:
                if changed:
                    extrema[:]=[r for r in extrema if r['kind']!=label]
                    extrema.append(dict(kind=label,event_us=int(stamp),cause=cause,NAV=nav,
                        peak_NAV=peak,max_drawdown=mdd,account_status=account.status))
        return nav

    def schedule(target,signal,kind):
        nonlocal sequence
        if bridge is not None:
            bridge.force_targets(target,int(signal),kind)
            return
        for s in symbols:
            order_kind=kind[s] if isinstance(kind,dict) else kind
            if s in pending:rejections.append(dict(symbol=s,event_us=int(signal),
                reason='SUPERSEDED_BY_'+order_kind,old_signal_us=pending[s]['signal_us']))
            sequence+=1
            pending[s]=dict(target=D(str(target[s])),signal_us=int(signal),kind=order_kind,attempts=0,
                order_id=f'{mode}-{cost["id"]}-{unit["id"]}-{sequence}')

    def risk_schedule(stamp):
        if account.status!='BOUND_BREACH_REDUCTION_REQUIRED' or terminal:return
        if bridge is None:
            if any(o['kind']=='RISK_REDUCTION' for o in pending.values()):return
        elif any(o and o['kind'] in ('RISK_REDUCTION','STOP','EXIT','TERMINAL')
                 for o in bridge.summary_orders().values()):return
        nav=account.nav();notionals=[abs(account.positions[s].quantity)*account.marks[s][-1]['price']
                                   if account.positions[s].quantity else ZERO for s in symbols]
        scale=min(D(1),D('.297')*nav/max(notionals) if max(notionals)>0 else D(1),
                  D('.594')*nav/sum(notionals,ZERO) if sum(notionals,ZERO)>0 else D(1))
        breaches.append(dict(signal_us=int(stamp),gross_weight=float(sum(notionals,ZERO)/nav),
            asset_weights={s:float(v/nav) for s,v in zip(symbols,notionals,strict=True)},
            phase='ACTUAL_DRIFT_BEFORE_CAPACITY_LIMITED_REDUCTION',scale=float(scale)))
        schedule({s:account.positions[s].quantity*scale for s in symbols},stamp,'RISK_REDUCTION')

    def funding_through(limit,inclusive):
        nonlocal event_cursor,completion,stop
        while event_cursor<len(window['events']):
            raw=window['events'][event_cursor];e=raw['event_us']
            if e>limit or not inclusive and e==limit:break
            s=raw['symbol'];quantity=account.positions[s].quantity
            rate=D(str(raw['raw_rate']))*D(str(unit['scale']))
            observe(e,'BEFORE_FUNDING')
            if not account.marks[s]:
                need(quantity==0,
                     'No past mark permits only this instrument\'s verified zero ownership')
                receipt=dict(symbol=s,event_us=e,event_id=f'{s}:{e}',owned=False,quantity=0.,
                    signed_funding_USDT=0.,mark_price=None,mark_close_us=None,
                    status='NO_POSITION_NO_PAST_MARK',account_status=account.status)
            else:
                receipt=account.apply_funding(s,f'{s}:{e}',e,rate,e)
            funding_journal.append({**receipt,**raw,'conditional_rate_scale':unit['scale'],
                'assumed_fraction_decimal':str(rate),'raw_rate_unit':'UNCONFIRMED',
                'rate_publication_assumption':'EVENT_TIME_CONDITIONAL_NOT_CERTIFIED'})
            event_cursor+=1;observe(e,'AFTER_FUNDING')
            if account.status in HALTS:
                completion='NOT_EVALUABLE_ACCOUNT_HALT_NO_LIQUIDATION_SIMULATED';stop=e;return
            risk_schedule(e)

    def attempt(open_us,market_row,previous_quote):
        nonlocal first_entry,completion,stop
        if bridge is not None:
            event=int(open_us)+1
            mids={s:D(str(market_row[s]['open'])) for s in symbols if s in market_row}
            need(set(mids)==set(symbols),'Event strategy needs all configured real trade opens')
            capacity={s:D(str(previous_quote[s]))*D('.001')/mids[s]
                      if previous_quote is not None else ZERO for s in symbols}
            due=sorted(bridge.due_orders(int(open_us),mids),
                       key=lambda o:(not o['reduce_only'],symbols.index(o['symbol']),o['id']))
            for order in due:
                s=order['symbol'];before=len(account.trades)
                receipt=account.execute_fill(s,order['side'],order['quantity'],event,order['signal_us'],
                    order['id']+':'+str(order['attempts']),execution_mid_price=mids[s],
                    quote_available_us=int(open_us),available_quantity=capacity[s],reduce_only=order['reduce_only'])
                used=sum((D(r['decimal_strings']['quantity']) for r in account.trades[before:]),ZERO)
                capacity[s]=max(ZERO,capacity[s]-used)
                bridge.on_fill(order['id'],receipt)
                bridge.note_attempt(order['id'],event,receipt)
                if used>0 and order['kind']=='RISK_REDUCTION':
                    matching=[r for r in reversed(breaches) if r['signal_us']==order['signal_us']]
                    if matching and 'first_reduction_fill_us' not in matching[0]:
                        matching[0].update(first_reduction_fill_us=event,
                            reduction_latency_us=event-order['signal_us'])
                if account.trades[before:] and first_entry is None:first_entry=event
                if receipt['status']!='FILLED':
                    rejections.append(dict(symbol=s,event_us=event,order_id=order['id'],kind=order['kind'],
                        **{k:v for k,v in receipt.items() if k!='fills'}))
                observe(event,'AFTER_TURTLE_'+order['kind'])
                if account.status in HALTS:
                    completion='NOT_EVALUABLE_ACCOUNT_HALT_NO_LIQUIDATION_SIMULATED';stop=event;return
                if bridge.halt_reason:
                    completion=bridge.halt_reason;stop=event;return
            return
        event=int(open_us)+1;due={s:o for s,o in pending.items()
            if event>=ExecutionContractV2().earliest_execution_us(o['signal_us'])+1}
        capacity={s:D(str(previous_quote[s]))*D('.001')/D(str(market_row[s]['open']))
                  if previous_quote is not None and s in market_row else ZERO for s in symbols}
        # Every symbol gets at most one attempt-minute; reductions precede every increase.
        for phase in ('REDUCE','INCREASE'):
            for s in symbols:
                if s not in due or s not in market_row:continue
                order=due[s];position=account.positions[s].quantity;target=order['target'];delta=target-position
                if delta==0:continue
                reducing=position!=0 and position*delta<0
                if phase=='REDUCE':
                    if not reducing:continue
                    requested=min(abs(delta),abs(position));reduce_only=True
                    if order['kind']=='RISK_REDUCTION':
                        from decimal import ROUND_CEILING
                        step=account.instrument_profiles[s].quantity_step
                        requested=min(abs(position),(requested/step).to_integral_value(rounding=ROUND_CEILING)*step)
                else:
                    if reducing or order['kind'] in ('RISK_REDUCTION','TERMINAL','POOL_EXIT','DATA_GAP_EXIT'):continue
                    if account.status!='ACTIVE':
                        rejections.append(dict(symbol=s,event_us=event,reason='RISK_PRIORITY_NO_INCREASE',order_id=order['order_id']));continue
                    requested=abs(delta);reduce_only=False
                if requested==0:continue
                side='BUY' if delta>0 else 'SELL'
                fill_id=f'{order["order_id"]}:{order["attempts"]}:{phase}'
                before=len(account.trades)
                receipt=account.execute_fill(s,side,requested,event,order['signal_us'],fill_id,
                    execution_mid_price=D(str(market_row[s]['open'])),quote_available_us=int(open_us),
                    available_quantity=capacity[s],reduce_only=reduce_only)
                used=sum((D(r['decimal_strings']['quantity']) for r in account.trades[before:]),ZERO)
                capacity[s]=max(ZERO,capacity[s]-used)
                if used>0 and order['kind']=='RISK_REDUCTION':
                    witness=next(r for r in reversed(breaches) if r['signal_us']==order['signal_us'])
                    if 'first_reduction_fill_us' not in witness:
                        witness.update(first_reduction_fill_us=event,reduction_latency_us=event-order['signal_us'])
                if account.trades[before:] and first_entry is None:first_entry=event
                if receipt['status']!='FILLED':rejections.append(dict(symbol=s,event_us=event,
                    order_id=order['order_id'],phase=phase,**{k:v for k,v in receipt.items() if k!='fills'}))
                observe(event,'AFTER_'+phase)
                if account.status in HALTS:
                    completion='NOT_EVALUABLE_ACCOUNT_HALT_NO_LIQUIDATION_SIMULATED';stop=event;return
        for s,order in due.items():
            order['attempts']+=1
            remaining=order['target']-account.positions[s].quantity
            reached=(remaining==0 or order['kind'] in ('RISK_REDUCTION','TERMINAL','POOL_EXIT','DATA_GAP_EXIT')
                and (account.positions[s].quantity==0 or order['target']*account.positions[s].quantity>0
                     and abs(account.positions[s].quantity)<=abs(order['target'])))
            if reached:pending.pop(s,None)
            elif order['attempts']>=5:
                rejections.append(dict(symbol=s,event_us=event,order_id=order['order_id'],reason='FIVE_ATTEMPTS_EXPIRED',
                    remaining_signed_quantity=float(remaining),kind=order['kind']))
                pending.pop(s,None)
                if order['kind']=='RISK_REDUCTION' and account.status=='BOUND_BREACH_REDUCTION_REQUIRED':
                    completion='NOT_EVALUABLE_UNEXECUTABLE_RISK_REDUCTION';stop=event;return
                if order['kind'] in ('POOL_EXIT','DATA_GAP_EXIT') and account.positions[s].quantity:
                    completion='NOT_EVALUABLE_UNEXECUTABLE_ASSET_EXIT';stop=event;return

    def market_rows():
        if 'minute_blocks' not in window:
            columns=('open','close','quote_volume','mark')
            if bridge is not None:columns+=('high','low','volume')
            for i,t in enumerate(times):
                yield int(t),{s:{k:window['market'][s][k][i] for k in
                    columns} for s in symbols}
            return
        expected=start
        for block in window['minute_blocks']():
            stamps=np.asarray(block['times'])
            need(stamps.dtype.kind in ('i','u') and len(stamps)>0 and len(stamps)<=1440,
                'One UTC day or smaller real execution block')
            need(np.array_equal(stamps,np.arange(expected,expected+len(stamps)*MINUTE,MINUTE)),
                'Execution blocks cover scoring dates without deletions or imputation')
            need(set(block['market'])<=set(symbols),'Block symbol outside configured account')
            for s,values_for_asset in block['market'].items():
                columns={'open','close','quote_volume','mark'}
                if bridge is not None:columns|={'high','low','volume'}
                need(set(values_for_asset)==columns
                    and all(len(v)==len(stamps) for v in values_for_asset.values()),
                    'Actual execution block schema and lengths')
            for j,t in enumerate(stamps):
                row={s:{k:v[j] for k,v in values_for_asset.items()}
                     for s,values_for_asset in block['market'].items()}
                yield int(t),row
            expected+=len(stamps)*MINUTE
        need(expected==end,'All required minutes, no hidden truncated calendar')

    previous_quote=None
    for i,(t,market_row) in enumerate(market_rows()):
        need(i<n and t==int(times[i]),'Complete synchronous portfolio clock')
        absent=set(symbols)-set(market_row)
        if any(account.positions[s].quantity for s in absent):
            completion='NOT_EVALUABLE_MISSING_HELD_ASSET_EXECUTION_OR_MARK';stop=t
            rejections.append(dict(event_us=t,reason='MISSING_HELD_MARK_OR_EXECUTION',symbols=sorted(absent)))
            break
        need(all(math.isfinite(float(v)) and (v>=0 if k in ('quote_volume','volume') else v>0)
                 for row in market_row.values() for k,v in row.items()),'Finite actual block values')
        t=int(t);close=t+MINUTE
        if t in weights and not terminal:
            # All signal quantities freeze before rates later than this decision and future opens.
            nav=account.nav()
            desired={s:D(str(weights[t][s]))*D('.99')*nav/D(str(daily_prices[s][t]))
                     if weights[t][s]!=0 else ZERO for s in symbols}
            if account.status=='ACTIVE':schedule(desired,t,decision_kinds[t])
        if bridge is not None and t%event_strategy.FOUR_HOURS==0 and not terminal:
            event_strategy.decision(bridge,histories,t)
        if t==end-6*MINUTE:
            terminal=True;schedule(dict.fromkeys(symbols,ZERO),t,'TERMINAL')
        funding_through(t+1,True)
        if stop is not None:break
        attempt(t,market_row,previous_quote)
        if stop is not None:break
        funding_through(close,False)
        if stop is not None:break
        account.update_marks(close,{s:dict(price=D(str(market_row[s]['mark'])),
            close_us=close,available_us=close) for s in market_row})
        observe(close,'MINUTE_MARK')
        if account.status in HALTS:
            completion='NOT_EVALUABLE_ACCOUNT_HALT_NO_LIQUIDATION_SIMULATED';stop=close;break
        funding_through(close,True)
        if stop is not None:break
        risk_schedule(close)
        if bridge is not None and not terminal:
            bridge.observe_stop(close,{s:dict(open_us=t,available_us=close,
                high=market_row[s]['high'],low=market_row[s]['low']) for s in symbols})
        nav=account.nav();signed={s:account.positions[s].quantity*account.marks[s][-1]['price']
                                 if account.positions[s].quantity else ZERO for s in symbols}
        equities={s:account.positions[s].isolated_balance+account.positions[s].quantity*
            (account.marks[s][-1]['price']-account.positions[s].entry_price)
            if account.positions[s].quantity else account.positions[s].isolated_balance for s in symbols}
        values[i]=[float(nav),float(account.free_cash),float(sum((p.isolated_balance for p in account.positions.values()),ZERO)),
            float(sum((abs(v) for v in signed.values()),ZERO)),float(sum(signed.values(),ZERO)),float(account.fees),
            float(account.execution_cost),float(account.funding_cash),float(account.gross_fill_turnover),
            *[float(account.positions[s].quantity) for s in symbols],*[float(signed[s]) for s in symbols],
            *[float(account.positions[s].isolated_balance) for s in symbols],*[float(equities[s]) for s in symbols],
            *[float(signed[s]/nav) if nav>0 else 0. for s in symbols],
            float(sum((abs(v) for v in signed.values()),ZERO)/nav) if nav>0 else 0.,
            float(sum(signed.values(),ZERO)/nav) if nav>0 else 0.]
        rows_written=i+1
        previous_quote={s:market_row[s]['quote_volume'] if s in market_row else 0. for s in symbols}
        if i%1440==0 and progress:
            progress.update('实际逐分钟独立账户',i+1,n,'分钟',direction=mode,cost=cost['id'],funding_unit=unit['id'])
            if guard:guard()
    for r in funding_journal:
        near=[f['event_us'] for f in account.trades if f['symbol']==r['symbol']
              and abs(f['event_us']-r['event_us'])<=5_000_000]
        if near:nearest_funding_ties.append(dict(symbol=r['symbol'],event_us=r['event_us'],nearby_fill_us=near,
            ownership_native_certified=False))
    columns=['nav','free_cash','isolated_balance','gross_notional','net_signed_notional','cumulative_fees',
        'cumulative_execution_costs','cumulative_funding','cumulative_turnover',
        *[s+'_quantity' for s in symbols],*[s+'_signed_marked_notional' for s in symbols],
        *[s+'_isolated_balance' for s in symbols],*[s+'_isolated_equity' for s in symbols],
        *[s+'_signed_weight' for s in symbols],'gross_weight','net_signed_weight']
    minute=pl.DataFrame(values[:rows_written],schema=columns,orient='row').with_columns(
        pl.Series('close_us',times[:rows_written]+MINUTE))
    summary=account.summary()
    terminal_prices={s:float(account.marks[s][-1]['price']) if account.marks[s] else None for s in symbols}
    terminal_signed={s:float(account.positions[s].quantity)*terminal_prices[s]
                     if account.positions[s].quantity else 0. for s in symbols}
    summary.update(symbols=list(symbols),completion=completion,mode=mode,cost_scenario=cost,unit_scenario=unit,
        funding_rate_unit='UNCONFIRMED',unit_certified=False,publication_certified=False,
        completed_minutes=rows_written,required_minutes=n,stop_us=stop,all_observation_max_drawdown=mdd,
        maximum_actual_gross_weight=max_gross,maximum_actual_asset_weights=max_asset,
        funding_original_events=len(window['events']),funding_observed_events=len(funding_journal),
        funding_account_applied_events=len(account.funding),
        fresh_flat_no_past_mark_events=sum(r.get('status')=='NO_POSITION_NO_PAST_MARK' for r in funding_journal),
        funding_owned_events=sum(bool(r['owned']) for r in funding_journal),
        funding_deferred_after_halt_events=len(window['events'])-event_cursor,
        first_entry_us=first_entry,terminal_marked_notional=summary['gross_notional'],
        terminal_mark_prices=terminal_prices,terminal_signed_marked_notional=terminal_signed,
        terminal_cash_realized=all(p.quantity==0 for p in account.positions.values()),
        terminal_not_forced_free_fill=True,pending_orders_at_stop=(bridge.summary_orders() if bridge is not None
            else {s:{**r,'target':str(r['target'])} for s,r in pending.items()}),
        funding_fill_5second_uncertainty_witnesses=nearest_funding_ties,candidate='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE')
    summary['minimum_actual_free_cash_all_observations_USDT']=min_free
    summary['actual_caps_instantaneously_guaranteed']=False
    summary['margin_risk_observation_scope']='CAUSALLY_AVAILABLE_MINUTE_CLOSE_MARKS_PLUS_FILLS_AND_FUNDING_NOT_INTRAMINUTE_MARK_EXTREMES_OR_NATIVE_RISK_TIERS'
    summary['risk_reduction_signal_count']=len(breaches)
    delays=[r['reduction_latency_us'] for r in breaches if 'reduction_latency_us' in r]
    summary['maximum_observed_first_risk_reduction_latency_us']=max(delays) if delays else None
    if bridge is not None:
        targets,meta=bridge.targets_frame(),bridge.meta()
    return dict(summary=summary,targets=targets,target_meta=meta,minute=minute,trades=account.trades,
        funding=funding_journal,rejections=rejections,breaches=breaches,extrema=extrema)

def save_case(case,directory):
    directory.mkdir();artifacts={}
    symbols=strategy.symbol_order(case['summary'].get('symbols',tuple(case['summary']['positions'])))
    minute=case['minute'];summary=case['summary'];complete=summary['completed_minutes']==summary['required_minutes']
    daily=empty_frame({'day_end_us':pl.Int64,'nav':pl.Float64,'fees':pl.Float64,'execution_costs':pl.Float64,'turnover':pl.Float64})
    if minute.height:
        daily=minute.filter(pl.col('close_us')%DAY==0).select(pl.col('close_us').alias('day_end_us'),'nav',
            pl.col('cumulative_fees').diff().fill_null(pl.col('cumulative_fees')).alias('fees'),
            pl.col('cumulative_execution_costs').diff().fill_null(pl.col('cumulative_execution_costs')).alias('execution_costs'),
            pl.col('cumulative_turnover').diff().fill_null(pl.col('cumulative_turnover')).alias('turnover'))
    if complete:
        summary['daily_metrics']=daily_metrics(daily,10000.)
        summary['annual_return_role']='DESCRIPTIVE_EXTRAPOLATION_NOT_LONG_TERM_APR'
        full=np.r_[10000.,minute['nav'].to_numpy()]
        summary['minute_max_drawdown']=float(np.max(1-full/np.maximum.accumulate(full)))
        summary['normalized_total_turnover']=float(summary['gross_fill_turnover_USDT']/10000.)
        summary['net_return_on_full_initial_capital_percent']=100*summary['net_PnL']/10000.
        gross=minute['gross_weight'].to_numpy();net=minute['net_signed_weight'].to_numpy()
        collateral=minute['isolated_balance'].to_numpy();navs=minute['nav'].to_numpy()
        summary['realized_exposure']=dict(minute_mean_gross_weight=float(np.mean(gross)),minute_max_gross_weight=float(np.max(gross)),
            minute_mean_net_signed_weight=float(np.mean(net)),minute_min_net_signed_weight=float(np.min(net)),
            minute_max_net_signed_weight=float(np.max(net)),
            minute_mean_isolated_collateral_over_initial_capital=float(np.mean(collateral/10000.)),
            minute_max_isolated_collateral_over_initial_capital=float(np.max(collateral/10000.)),
            minute_mean_isolated_collateral_over_NAV=float(np.mean(collateral/navs)),
            minute_max_isolated_collateral_over_NAV=float(np.max(collateral/navs)),
            minimum_recorded_minute_free_cash_USDT=float(min(10000.,minute['free_cash'].min())),
            scope='COMPLETE_MINUTE_SNAPSHOTS_REALIZED_RISK_NOT_EQUALIZED_BY_COMMON_CAPS')
        daily_delta=np.diff(np.r_[10000.,daily['nav'].to_numpy()]);positive=daily_delta[daily_delta>0]
        absolute=float(np.abs(daily_delta).sum());positive_sum=float(positive.sum())
        summary['daily_net_gain_concentration']=dict(positive_days=int(len(positive)),total_days=len(daily_delta),
            top5_positive_day_share=float(np.sort(positive)[-5:].sum()/positive_sum) if positive_sum>0 else None,
            largest_absolute_day_share=float(np.abs(daily_delta).max()/absolute) if absolute>0 else None,
            positive_gain_USDT=positive_sum,absolute_daily_net_delta_USDT=absolute)
    else:summary.update(daily_metrics=None,minute_max_drawdown=None,metrics_NOT_EVALUABLE_reason=summary['completion'])
    month_rows=[];previous_nav=10000.;previous_cost=previous_fee=previous_fund=0.
    for month,frame in daily.with_columns(pl.from_epoch('day_end_us',time_unit='us').dt.offset_by('-1us').dt.strftime('%Y-%m').alias('month')).partition_by('month',as_dict=True).items():
        endpoint=int(frame['day_end_us'][-1]);row=minute.filter(pl.col('close_us')==endpoint).row(0,named=True)
        net=float(row['nav'])-previous_nav;fee=row['cumulative_fees']-previous_fee;cost=row['cumulative_execution_costs']-previous_cost
        funding=row['cumulative_funding']-previous_fund
        month_rows.append(dict(month=month[0],days=frame.height,net_PnL=net,fees=fee,
            spread_cost=cost/2,slippage_cost=cost/2,funding_USDT=funding,gross_PnL=net+fee+cost-funding,
            ending_NAV=row['nav'],ending_signed_quantities={s:row[s+'_quantity'] for s in symbols}))
        previous_nav=row['nav'];previous_fee=row['cumulative_fees'];previous_cost=row['cumulative_execution_costs'];previous_fund=row['cumulative_funding']
    summary['months']=month_rows
    summary['monthly_table_scope']='COMPLETE_UTC_DAY_ENDPOINTS_ONLY_NO_PARTIAL_DAY_INVENTION'
    summary['positive_month_count']=sum(r['net_PnL']>0 for r in month_rows) if complete else None
    summary['total_month_count']=len(month_rows) if complete else None
    attribution={direction:dict(gross=0.,fees=0.,execution_cost=0.,funding=0.) for direction in ('LONG','SHORT')}
    for r in case['trades']:
        q0=r['quantity_before'];owner=q0 if r['leg']=='CLOSE' else r['position_delta'];label='LONG' if owner>0 else 'SHORT'
        attribution[label]['gross']-=r['position_delta']*r['mid_price'];attribution[label]['fees']+=r['fee_USDT_mid']
        attribution[label]['execution_cost']+=r['execution_cost']
    for s,r in summary['positions'].items():
        if r['quantity']:
            label='LONG' if r['quantity']>0 else 'SHORT'
            attribution[label]['gross']+=summary['terminal_signed_marked_notional'][s]
    for r in case['funding']:
        if r['quantity']:attribution['LONG' if r['quantity']>0 else 'SHORT']['funding']+=r['signed_funding_USDT']
    for r in attribution.values():r['net_contribution']=r['gross']-r['fees']-r['execution_cost']+r['funding']
    summary['long_short_marked_contribution']=attribution
    summary['spread_cost_USDT']=summary['execution_cost_USDT']/2
    summary['slippage_cost_USDT']=summary['execution_cost_USDT']/2
    for name,frame in [('minute_nav_inventory',minute),('daily_nav',daily),('targets',case['targets'])]:
        path=directory/(name+'.parquet');frame.write_parquet(path,compression='zstd')
        artifacts[path.name]=dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size,rows=frame.height)
    for name in ('trades','funding','rejections','breaches','extrema','target_meta'):
        path=directory/(name+'.json');write(path,case[name]);artifacts[path.name]=dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size)
    trade_schema={'symbol':pl.String,'side':pl.String,'leg':pl.String,'event_us':pl.Int64,'signal_us':pl.Int64,
        'quantity':pl.Float64,'position_delta':pl.Float64,'mid_price':pl.Float64,'fill_price':pl.Float64,
        'fee_USDT_mid':pl.Float64,'execution_cost':pl.Float64,'quantity_before':pl.Float64,'quantity_after':pl.Float64}
    funding_schema={'symbol':pl.String,'event_us':pl.Int64,'raw_rate':pl.Float64,'quantity':pl.Float64,
        'owned':pl.Boolean,'signed_funding_USDT':pl.Float64,'mark_price':pl.Float64,'mark_close_us':pl.Int64}
    for name,schema in [('trades',trade_schema),('funding',funding_schema)]:
        path=directory/(name+'.parquet');frame=journals_frame(case[name],schema);frame.write_parquet(path,compression='zstd')
        artifacts[path.name]=dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size,rows=frame.height)
    return dict(summary=summary,artifacts=artifacts)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ('protocol','run-dir','output'):parser.add_argument('--'+arg,type=Path,required=True)
    parser.add_argument('--experiment-id',required=True);parser.add_argument('--period',choices=['122D','90D','BOTH'],default='BOTH')
    args=parser.parse_args();run=args.run_dir.resolve();out=args.output.resolve();spec=small(args.protocol)
    need(os.getenv('COIN_TASK_ID') and run.is_relative_to(STATE) and not run.exists()
        and out.is_relative_to(ROOT/'reports/fast_research') and not out.exists(),'Fresh bounded/progress task paths')
    need(spec['contract_id']==CONTRACT and spec['rules']==RULES and spec['cost_scenarios']==COSTS
        and spec['unit_scenarios']==UNITS and spec['period_ids']==['122D','90D'],'Fixed full declared scenario design')
    need(run==Path(spec['run_dir']).resolve() and out==(ROOT/spec['output_path']).resolve(),'Exact frozen output paths')
    own=Path(__file__).resolve().relative_to(ROOT).as_posix();hashes=spec['frozen_sources']
    need(hashes.get(own)==sha(__file__),'Own frozen source identity')
    for p,h in hashes.items():need((ROOT/p).resolve().is_relative_to(ROOT) and sha(ROOT/p)==h,'Frozen source/proof '+p)
    env=spec['environment'];need(sys.prefix==env['sys_prefix'] and sha(ROOT/env['lock_path'])==env['lock_sha256']
        and pl.thread_pool_size()<=2,'Accepted CPU environment')
    manifest=relative_proof(spec['input_manifest']);need(manifest['status']==MANIFEST_STATUS
        and manifest['funding_rate_unit']=='UNCONFIRMED' and not manifest['funding_unit_certified'],'Honest metadata/units')
    acceptance=relative_proof(spec['trade_source_acceptance'])
    need(acceptance.get('source_only',True) and not acceptance.get('funding_unit_certified',False),
         'Source-only acceptance cannot certify funding or market execution')
    smoke=relative_proof(spec['required_smoke_receipt']);need(smoke.get('test_exit_code')==0
        and smoke.get('source_bytes_unchanged') is True,'Actual synthetic test0/source unchanged before market arrays')
    smoke_task=small(STATE/'task-progress'/f"task-{smoke['binding']['task_id']}.json")
    need(smoke_task['id']==smoke['binding']['task_id'] and smoke_task['status']=='completed'
        and smoke_task['exit_code']==0,'True completed synthetic task; not a running test report')
    before=resources.status();run.mkdir();started=time.monotonic();budget=spec['budgets']
    selected=[w for w in manifest['windows'] if args.period=='BOTH' or w['id']==args.period]
    expected=len(selected)*len(strategy.MODES)*len(COSTS)*len(UNITS)
    binding=dict(task_id=os.environ['COIN_TASK_ID'],source_path=str(Path(__file__).resolve()),source_sha256=sha(__file__),
        source_hashes=hashes,protocol_path=str(args.protocol.resolve()),protocol_sha256=sha(args.protocol),
        exact_command=shlex.join([sys.executable,*sys.argv]),git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        sys_prefix=sys.prefix,selected_periods=[w['id'] for w in selected],rules=RULES)
    write(run/'RUN_BINDING.json',binding)
    event=dict.fromkeys(FIELDS);event.update(experiment_id=args.experiment_id,event_id=args.experiment_id+':START',event_type='OPERATIONAL_RESEARCH_START',
        git_commit=binding['git_commit'],data_manifest_hash=spec['input_manifest']['sha256'],protocol_hash=binding['protocol_sha256'],
        feature_set='ORIGINAL_PUBLIC_SMA50_200_DAILY_SIGNED',labels='NONE',model_family='NONE',hyperparameters=RULES,
        seed=None,thresholds='FIXED_NO_SEARCH',cost_assumptions={'costs':COSTS,'funding_units':UNITS},all_folds=binding['selected_periods'],
        success_failure='START_BEFORE_ECONOMIC_ARRAY_READ',reason_for_next_experiment='Same product and capital four-direction comparison',
        result_influenced_later_choice=False,source_hashes=hashes,exact_command=binding['exact_command'])
    result=dict(status='FAIL_CONDITIONAL_USDM_DIRECTIONAL_RESEARCH',binding=binding,run_binding_sha256=sha(run/'RUN_BINDING.json'),
        registration_start=append_event(ROOT/'reports/experiment_registry.jsonl',event),required_cases=expected,completed_cases=0,cases=[],
        case_count_scope='NOMINAL_SCENARIO_SELECTORS_CASH_CONSTANT_ARTIFACTS_SHARED',
        planned_trading_account_simulations=len(selected)*12,planned_constant_cash_baselines=len(selected),
        completed_trading_account_simulations=0,completed_constant_cash_baselines=0,
        input_windows=[],funding_rate_unit='UNCONFIRMED',unit_certified=False,native_market_certified=False,candidate='NO_QUALIFIED_CANDIDATE',
        long_term_APR='NOT_EVALUABLE',models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,resources_before=before)
    progress=support.progress_writer(expected);progress.value['detail']='独立四方向、两成本和两条件资金费单位；不是真实市场资格'
    def guard():
        need(support.owned_bytes(run)<=budget['new_owned_bytes'],'Exclusive research output budget')
        need(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=budget['peak_RSS_bytes'],'Research peak RSS budget')
        need(time.monotonic()-started<=budget['wall_seconds'],'Research wall budget')
    try:
        progress.update('真实磁盘容量扫描，总量未知',None,None,'扫描')
        result['disk']=dict(scan_started_utc=datetime.now(UTC).isoformat(),**disk.check(budget['new_owned_bytes']))
        result['disk']['scan_finished_utc']=datetime.now(UTC).isoformat()
        need(result['disk']['total_bytes']+budget['new_owned_bytes']<=32_000_000_000,'Expected32GB reservation')
        for window_spec in selected:
            window=load_window(manifest,window_spec);result['input_windows'].append(dict(id=window_spec['id'],input_proofs=window['input_proofs'],
                original_funding_events=len(window['events']),score_start_us=window['start'],score_end_exclusive_us=window['end']))
            for mode in strategy.MODES:
                # CASH is the same fixed cash state; no repeated account minute arithmetic.
                cached_cash=None;cached_cash_directory=None
                for cost in COSTS:
                    for unit in UNITS:
                        case_id=f'{window_spec["id"]}_{mode}_{cost["id"]}_{unit["id"]}'
                        directory=run/case_id
                        if mode=='CASH' and cached_cash is not None:
                            saved=json.loads(json.dumps(cached_cash));saved['summary']['cost_scenario']=cost;saved['summary']['unit_scenario']=unit
                            saved['summary']['configured_nominal_roundtrip_bps']=cost['roundtrip_bps']
                            saved['shared_constant_cash_artifact_directory']=str(cached_cash_directory)
                        else:
                            if mode=='CASH':
                                times=window['times'];size=len(times);minute=pl.DataFrame(dict(nav=np.full(size,10000.),free_cash=np.full(size,10000.),
                                    isolated_balance=np.zeros(size),gross_notional=np.zeros(size),net_signed_notional=np.zeros(size),
                                    cumulative_fees=np.zeros(size),cumulative_execution_costs=np.zeros(size),cumulative_funding=np.zeros(size),
                                    cumulative_turnover=np.zeros(size),close_us=times+MINUTE,
                                    **{s+k:np.zeros(size) for s in SYMBOLS for k in ('_quantity','_signed_marked_notional','_isolated_balance','_isolated_equity','_signed_weight')},
                                    gross_weight=np.zeros(size),net_signed_weight=np.zeros(size)))
                                targets,meta=strategy.fixed_targets(window['daily'],np.arange(window['start'],window['end'],DAY,dtype=np.int64),mode)
                                summary=USDTLinearPerpetualAccount(PerpetualConfig(half_spread_bps=D(str(cost['half_spread_bps'])),
                                    slippage_bps=D(str(cost['slippage_bps'])))).summary();summary.update(completion='COMPLETE_CONDITIONAL_ACCOUNT',mode=mode,
                                    cost_scenario=cost,unit_scenario=unit,completed_minutes=size,required_minutes=size,all_observation_max_drawdown=0.,
                                    funding_original_events=len(window['events']),funding_observed_events=len(window['events']),funding_owned_events=0,
                                    funding_account_applied_events=0,funding_deferred_after_halt_events=0,fresh_flat_no_past_mark_events=0,
                                    known_zero_cash_ownership=True,terminal_marked_notional=0.,terminal_cash_realized=True,
                                    terminal_mark_prices=dict.fromkeys(SYMBOLS,None),terminal_signed_marked_notional=dict.fromkeys(SYMBOLS,0.),
                                    maximum_actual_gross_weight=0.,maximum_actual_asset_weights=dict.fromkeys(SYMBOLS,0.),
                                    funding_rate_unit='UNCONFIRMED',unit_certified=False,publication_certified=False,
                                    minimum_actual_free_cash_all_observations_USDT=10000.,actual_caps_instantaneously_guaranteed=False,
                                    margin_risk_observation_scope='NO_POSITION_CASH_REFERENCE_NOT_NATIVE_MARGIN_CERTIFICATION')
                                funding=[dict(**r,owned=False,quantity=0.,signed_funding_USDT=0.,mark_price=None,mark_close_us=None,
                                    status='CASH_NO_POSITION_KNOWN_ZERO_OWNERSHIP') for r in window['events']]
                                case=dict(summary=summary,targets=targets,target_meta=meta,minute=minute,trades=[],funding=funding,
                                    rejections=[],breaches=[],extrema=[])
                            else:case=simulate(window,mode,cost,unit,progress,guard)
                            saved=save_case(case,directory);del case;gc.collect()
                            if mode=='CASH':
                                cached_cash=saved;cached_cash_directory=directory
                                result['completed_constant_cash_baselines']+=1
                            else:result['completed_trading_account_simulations']+=1
                        result['cases'].append(dict(id=case_id,period=window_spec['id'],mode=mode,cost_id=cost['id'],unit_id=unit['id'],**saved))
                        result['completed_cases']=len(result['cases']);guard()
                        progress.update('实际场景选择器完成',result['completed_cases'],expected,'选择器',
                            period=window_spec['id'],direction=mode,physical_trading_accounts=result['completed_trading_account_simulations'])
            del window;gc.collect()
        need(result['completed_cases']==expected and all(sha(ROOT/p)==h for p,h in hashes.items()),'Complete case selectors/source bytes unchanged')
        result['status']=STATUS
        result['completed_full_calendar_cases']=sum(c['summary']['completed_minutes']==c['summary']['required_minutes'] for c in result['cases'])
        result['incomplete_or_halted_cases']=expected-result['completed_full_calendar_cases']
    except Exception as error:result.update(error_type=type(error).__name__,reason=str(error));raise
    finally:
        result.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,owned_bytes=support.owned_bytes(run),resources_after=resources.status())
        write(out,result)
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=args.experiment_id+':RESULT',event_type='OPERATIONAL_RESEARCH_RESULT',
            success_failure=result['status'],artifact_path=str(out.relative_to(ROOT)),artifact_sha256=sha(out)))
        progress.stop.set();progress.thread.join(timeout=3)
    print(json.dumps(dict(status=result['status'],completed_cases=result['completed_cases'],output=str(out),sha256=sha(out))))

if __name__=='__main__':main()
