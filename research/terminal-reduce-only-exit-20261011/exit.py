"""Financial-anchor recovery for a bounded new-namespace reduce-only exit.

Historical scheduler/fill-request maps are absent and remain UNKNOWN. This is
not a manufactured original snapshot or a replay of the original account.
"""
import argparse
from copy import deepcopy
from decimal import localcontext,ROUND_DOWN
import io
import json
from pathlib import Path
import sys
import time
import zipfile

import numpy as np
import pyarrow.parquet as pq

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'research/composite-mark-replay-20261011'))
import replay as source_api
from composite_bars import composite_bars
from quant.perpetual_account import D,ZERO,HALTS,Position,USDTLinearPerpetualAccount
from quant.execution_contract import ExecutionContractV2
from scripts.investment.bybit_cost_inputs import account_for_cost,execution_components
from scripts.investment.perpetual_directional import COSTS

git=source_api.git;digest=source_api.digest;save=source_api.save
MINUTE=60_000_000; START=1664841600000000; DEADLINE=START+60*MINUTE
OLD='research/composite-mark-replay-20261011/result/'
ARTIFACT='1eddf0b99885926867d650720c8c8b0d58453fa6'
NAMESPACE='FINITE_EXIT_EXTENSION_20221004'


def require(value,message):
    if not bool(value):raise ValueError(message)


def financial_anchor(body,marks):
    """Only restore fields explicitly saved or source-derived; no historical IDs invented."""
    summary=body['summary'];symbols=tuple(summary['symbols'])
    cost=summary['cost_scenario'];account=account_for_cost(cost,symbols)
    require(type(account) is USDTLinearPerpetualAccount,'Default factory must be unchanged')
    require(account.contract_metadata()==summary['contract'],'Exact saved contract/profile/cost identity')
    require(summary['account_status']=='ACTIVE' and not summary['halt_witness'] and not summary['pending_orders_at_stop'],
            'Only explicit active no-pending anchor is supported')
    exact=summary['decimal_strings']
    for field in ('free_cash','unpaid_liability'):setattr(account,field,D(exact[field]))
    for field,key in [('fees','fees_USDT'),('execution_cost','execution_cost_USDT'),('funding_cash','funding_USDT'),
                      ('realized_PnL','realized_PnL'),('gross_fill_turnover','gross_fill_turnover_USDT')]:
        setattr(account,field,D(exact[key]))
    for s in symbols:
        row=summary['positions'][s];v=row['decimal_strings']
        account.positions[s]=Position(D(v['quantity']),D(v['entry_price']),D(v['isolated_balance']),row['opened_us'])
        require(len(marks[s])==2,'Actual lasttwo completed source marks required')
        for mark,expected in zip(marks[s],(summary['clock_us']-MINUTE,summary['clock_us'])):
            require(set(mark)=={'price','close_us','available_us'} and D(mark['price'])>0
                    and mark['close_us']==mark['available_us']==expected,
                    'Exact positive ordered lasttwo completion clocks required')
        account.marks[s]=deepcopy(marks[s])
    account.clock_us=summary['clock_us'];account.status=summary['account_status']
    account.trades=deepcopy(body['trades']);account.last_fill_us=max(r['event_us'] for r in account.trades)
    account.funding=[]
    funding_fields=('symbol','event_id','event_us','rate_available_us','rate_fraction','mark_price','mark_close_us',
                    'owned','quantity','signed_funding_USDT','account_status','unit_and_publication_scope','decimal_strings')
    for row in body['funding']:
        if row.get('status')=='NO_POSITION_NO_PAST_MARK':continue
        require(all(k in row for k in funding_fields),'Applied funding receipt must be complete')
        receipt={k:deepcopy(row[k]) for k in funding_fields};account.funding.append(receipt)
        key=f"{row['symbol']}:{row['event_us']}"
        account.funding_events[key]=dict(identity=dict(event_id=row['event_id'],rate=row['assumed_fraction_decimal'],
            rate_available_us=row['rate_available_us']),receipt=deepcopy(receipt))
        account.funding_ids[row['event_id']]=key
    # Historical fill_requests are UNKNOWN. Empty here means ONLY the new exit
    # namespace, never that the historical request set was empty. General
    # from_snapshot is intentionally unsupported until those maps are recovered.
    require(not account.fill_requests,'Fresh namespace required')
    with localcontext() as ctx:
        ctx.prec=40
        rate=D(str(ExecutionContractV2.execution_rate(float(account.config.half_spread_bps),float(account.config.slippage_bps))))
        for row in account.trades:account._validate_snapshot_trade(row,rate)
        for s in symbols:
            quantity=sum((D(r['decimal_strings']['position_delta']) for r in account.trades if r['symbol']==s),ZERO)
            require(quantity==account.positions[s].quantity,'Exact saved journal/inventory bridge')
        totals=dict(fees=sum((D(r['decimal_strings']['fee_amount']) for r in account.trades),ZERO),
            execution_cost=sum((D(r['decimal_strings']['execution_cost']) for r in account.trades),ZERO),
            realized_PnL=sum((D(r['decimal_strings']['realized_PnL']) for r in account.trades),ZERO),
            funding_cash=sum((D(r['decimal_strings']['signed_funding_USDT']) for r in account.funding),ZERO),
            gross_fill_turnover=sum((D(r['decimal_strings']['quantity'])*D(r['decimal_strings']['fill_price']) for r in account.trades),ZERO))
        for k,v in totals.items():require(abs(getattr(account,k)-v)<=D('1e-25'),'Exact saved journal/cost total bridge '+k)
        account._risk('FINANCIAL_ANCHOR_RESTORE')
        actual=account.summary()
        # Every original base-account field, including nested Decimal strings,
        # must match the saved summary, rather than a rounded NAV tolerance.
        for k,v in actual.items():require(v==summary[k],'Saved financial state differs: '+k)
    return account,dict(status='PASS_EXACT_SAVED_FINANCIAL_ANCHOR_AND_JOURNAL_BRIDGES',
        historical_fill_requests='UNKNOWN_NOT_RESTORED',full_scheduler_snapshot='UNKNOWN_NOT_RESTORED',
        general_original_snapshot_restore='NOT_SUPPORTED',supported_resume='ONLY_FRESH_NAMESPACE_REDUCE_ONLY_EXTENSION',
        original_market_minutes_replayed=0,old_state_fabricated=False,original_account_class=type(account).__name__)


def diagnose(body):
    summary=body['summary'];terminal=[r for r in body['rejections'] if r.get('kind')=='TERMINAL' and r.get('reason')=='FIVE_ATTEMPTS_EXPIRED']
    require(len(terminal)==1 and terminal[0]['symbol']=='DOGEUSDT','Exact saved terminal expiration witness')
    order=terminal[0]['order_id'];partial=[r for r in body['rejections'] if r.get('order_id')==order and r.get('status')=='PARTIAL']
    require(len(partial)==5 and all(r['reason'] is None for r in partial),'Five successful capacity partials, no minnotional/reduce-only rejection')
    return dict(status='CAUSE_FIVE_ATTEMPT_LIMIT_AFTER_FIVE_CAPACITY_PARTIAL_FILLS',
        expired_order_id=order,partial_receipts=partial,expired_receipt=terminal[0],
        terminal_quantity_exact=summary['positions']['DOGEUSDT']['decimal_strings']['quantity'],
        terminal_notional_USDT=summary['terminal_marked_notional'],
        original_last_attempt_us=terminal[0]['event_us'],original_end_us=summary['clock_us'],
        source_boundary_not_cause='Lastattempt at23:59:00.000001, source continues beyondOct4; expiration removedorder beforeend',
        quantity_step_not_cause='Remaining quantity10945.60840428 aligned1e-8, far above10USDT minimum',
        reduce_only_not_cause='Allfive recordedCLOSE legs reducepositiveDOGE; noflip/newOPEN',
        implementation_error_found=False,old_protocol_status='STOP_DEFAULT_ACCOUNT_PAID_FLAT_GATE')


def extend(account,rows,events,previous_quote,signal,deadline):
    """Finite retry adapter calls existing fill/funding/mark kernel without factory changes."""
    require(signal==account.clock_us and deadline>signal,'Resume at explicit saved financial clock')
    require(all(signal<=r['event_us']<deadline and f"{r['symbol']}:{r['event_us']}" not in account.funding_events for r in events),
            'Only actual new future funding events including uncharged exact boundary')
    require(not account.fill_requests,'Historical request dedup not used; new namespace starts here')
    old_trades=len(account.trades);old_funding=len(account.funding);before=account.summary();attempts=[];trace=[]
    event_cursor=0;initially_owned=[s for s in account.symbols if account.positions[s].quantity]
    status='STOP_EXIT_DEADLINE_WITH_RESIDUAL';stop_us=deadline;max_gross=before['gross_notional'];min_nav=before['NAV'];peak=before['NAV'];mdd=0.
    previous=deepcopy(previous_quote);observations=[]
    def observe(event,cause):
        nonlocal max_gross,min_nav,peak,mdd
        v=account.summary();peak=max(peak,v['NAV']);min_nav=min(min_nav,v['NAV'])
        mdd=max(mdd,1-v['NAV']/peak);max_gross=max(max_gross,v['gross_notional'])
        observations.append(dict(event_us=event,cause=cause,NAV=v['NAV'],gross_notional=v['gross_notional'],account_status=account.status))
    def funding_through(limit,inclusive):
        nonlocal event_cursor
        while event_cursor<len(events):
            raw=events[event_cursor];e=raw['event_us']
            if e>limit or not inclusive and e==limit:break
            require(e>=signal,'Never replay historical funding')
            observe(e,'BEFORE_FUNDING')
            account.apply_funding(raw['symbol'],f"{raw['symbol']}:{e}",e,D(str(raw['raw_rate'])),e)
            observe(e,'AFTER_FUNDING')
            event_cursor+=1
            if account.status in HALTS:break
    for t,row in rows:
        require(signal<=t<deadline and t%MINUTE==0,'Exact actual continuation minute')
        absent=[s for s in initially_owned if account.positions[s].quantity and
                (s not in row or not np.isfinite([row[s]['open'],row[s]['mark']]).all())]
        if absent:status='STOP_MISSING_HELD_EXECUTION_OR_MARK';stop_us=t;break
        funding_through(t+1,True)
        if account.status in HALTS:status='STOP_ACCOUNT_HALT';stop_us=account.clock_us;break
        if t+1>=ExecutionContractV2().earliest_execution_us(signal)+1:
            for s in initially_owned:
                quantity=account.positions[s].quantity
                if not quantity:continue
                capacity=D(str(previous[s]))*D('.001')/D(str(row[s]['open']))
                fill_id=f'{NAMESPACE}:{s}:{t}'
                require(fill_id.startswith(NAMESPACE+':'),'Only new namespace allowed')
                receipt=account.execute_fill(s,'SELL' if quantity>0 else 'BUY',abs(quantity),t+1,signal,fill_id,
                    execution_mid_price=D(str(row[s]['open'])),quote_available_us=t,
                    available_quantity=capacity,reduce_only=True)
                attempts.append(dict(symbol=s,event_us=t+1,previous_quote_volume_exact=str(D(str(previous[s]))),
                    capacity_quantity_exact=str(capacity),quantity_before_exact=str(quantity),receipt=receipt))
                observe(t+1,'AFTER_REDUCE_ONLY_FILL')
                require(account.positions[s].quantity*quantity>=0 and abs(account.positions[s].quantity)<=abs(quantity),'Exit must notflip/upsize')
                if account.status in HALTS:break
        if account.status in HALTS:status='STOP_ACCOUNT_HALT';stop_us=account.clock_us;break
        funding_through(t+MINUTE,False)
        if account.status in HALTS:status='STOP_ACCOUNT_HALT';stop_us=account.clock_us;break
        account.update_marks(t+MINUTE,{s:dict(price=D(str(v['mark'])),close_us=t+MINUTE,available_us=t+MINUTE) for s,v in row.items()})
        observe(t+MINUTE,'MINUTE_MARK')
        if account.status in HALTS:status='STOP_ACCOUNT_HALT';stop_us=account.clock_us;break
        funding_through(t+MINUTE,True)
        summary=account.summary();trace.append(dict(close_us=t+MINUTE,NAV=summary['NAV'],free_cash=summary['free_cash'],
            gross_notional=summary['gross_notional'],positions=deepcopy(summary['positions']),account_status=account.status,
            cumulative_fees=summary['fees_USDT'],cumulative_execution_costs=summary['execution_cost_USDT'],cumulative_funding=summary['funding_USDT']))
        previous={s:v['quote_volume'] for s,v in row.items()}
        if account.status in HALTS:status='STOP_ACCOUNT_HALT';stop_us=account.clock_us;break
        if all(p.quantity==0 for p in account.positions.values()):
            status='PASS_FINITE_EXTENSION_EXACT_PAID_FLAT';stop_us=t+MINUTE;break
    final=account.summary();oldexact=before['decimal_strings'];newexact=final['decimal_strings']
    diff=lambda k:float(D(newexact[k])-D(oldexact[k]))
    spread,slip=execution_components(diff('execution_cost_USDT'),COSTS[0])
    return dict(status=status,start_us=signal,stop_us=stop_us,maximum_end_us=deadline,minutes_observed=len(trace),
        exact_paid_flat=all(p.quantity==0 for p in account.positions.values()),attempts=attempts,minute_trace=trace,observations=observations,
        new_trades=account.trades[old_trades:],new_funding=account.funding[old_funding:],events_applied=event_cursor,
        before=before,after=final,exit_increment_USDT=diff('NAV'),fees_paid_USDT=diff('fees_USDT'),
        execution_loss_paid_USDT=diff('execution_cost_USDT'),halfspread_component_USDT=spread,slippage_component_USDT=slip,
        funding_cash_USDT=diff('funding_USDT'),minimum_extension_NAV=min_nav,maximum_extension_marked_notional=max_gross,
        extension_available_event_drawdown=mdd,realized_PnL_increment_USDT=diff('realized_PnL'),
        old_three_day_status='STOP_DEFAULT_ACCOUNT_PAID_FLAT_GATE_UNCHANGED',
        historical_fill_requests='UNKNOWN_UNMODIFIED_NEW_NAMESPACE_ONLY',financial_scope='CONDITIONAL_EXIT_NOT_NEW_STRATEGY_PROFIT_OR_NATIVE_CERTIFICATION')


def actual_sources(state,body):
    source_api.configure(state,'REUSE_OCTNOV2022');inv,_,_,_=source_api.inventories()
    protocol=json.loads((ROOT/'research/composite-mark-replay-20261011/PROTOCOL.json').read_bytes())
    tp,tc=source_api.phase(protocol['trade_source'],source_api.TRADE,'OCTNOV2022_REUSE')
    mp,mc=source_api.phase(protocol['mark_source'],source_api.MARK,'REUSE_OCTNOV2022')
    tr=source_api.TradeReader(inv,state,local=False);mr=source_api.MarkReader(inv,state,local=False)
    from modules.collector_research.pipeline.normalize import month_limits
    left,right=month_limits(2022,10);frames={};marks={};records=[]
    for s in source_api.SYMBOLS:
        def row(proof):return next(r['source'] for r in proof['sources'] if r['source']['month']=='2022-10' and r['source']['symbol']==s)
        def companions(family):return [r for r in inv['reusable_price_archives'] if r['frequency']=='daily' and r['month']=='2022-10' and r['family']==family and r['symbol']==s]
        tb,tf=composite_bars(tr,row(tp),left,right,companions('klines'));mb,mf=composite_bars(mr,row(mp),left,right,companions('markPriceKlines'))
        require(np.array_equal(tf.timestamp_ms,mf.timestamp_ms),'Independent fulltrade/mark sourcegrid')
        frames[s]=dict(trade=tf,mark=mf)
        old=mf[(mf.timestamp_ms*1000>=START-2*MINUTE)&(mf.timestamp_ms*1000<START)]
        marks[s]=[dict(price=D(str(r.close)),close_us=int(r.timestamp_ms)*1000+MINUTE,available_us=int(r.timestamp_ms)*1000+MINUTE) for r in old.itertuples()]
        records.append(dict(symbol=s,trade_manifest=tb.provenance['manifest_json'],mark_manifest=mb.provenance['manifest_json']))
    # A read-only source witness verifies why every recorded terminal leg was
    # partial. It does not replay a historical account or infer a new quote.
    terminal_order=next(r['order_id'] for r in body['rejections'] if r.get('kind')=='TERMINAL' and r.get('reason')=='FIVE_ATTEMPTS_EXPIRED')
    capacity_witnesses=[]
    for r in body['rejections']:
        if r.get('order_id')!=terminal_order or r.get('status')!='PARTIAL':continue
        s=r['symbol'];t=r['event_us']-1;f=frames[s]['trade'];i=int(np.searchsorted(f.timestamp_ms.to_numpy(),t//1000))
        require(int(f.timestamp_ms.iloc[i])*1000==t and int(f.timestamp_ms.iloc[i-1])*1000==t-MINUTE,'Actual completed capacity source clock')
        with localcontext() as ctx:
            ctx.prec=28 # original scheduler capacity arithmetic, not kernel40
            cap=D(str(float(f.quote_volume.iloc[i-1])))*D('.001')/D(str(float(f.open.iloc[i])))
        with localcontext() as ctx:
            ctx.prec=40;step=D(body['summary']['contract']['instrument_profiles'][s]['quantity_step'])
            requested=D(r['decimal_strings']['requested_quantity'])
            floored=(min(requested,cap)/step).to_integral_value(rounding=ROUND_DOWN)*step
        require(floored==D(r['decimal_strings']['executed_quantity']) and requested>cap,'Recorded fill equals real capacity floor')
        capacity_witnesses.append(dict(symbol=s,event_us=r['event_us'],previous_quote_available_us=t,
            previous_quote_volume=str(float(f.quote_volume.iloc[i-1])),execution_open=str(float(f.open.iloc[i])),
            capacity_quantity_exact=str(cap),floored_quantity_exact=str(floored),saved_executed_quantity_exact=r['decimal_strings']['executed_quantity']))
    require(len(capacity_witnesses)==5,'All five original partials explained by actual source capacity')
    tr.close();mr.close();events=[];funding_members=[]
    import importlib.util
    spec=importlib.util.spec_from_file_location('funding_source',ROOT/'research/short-funding-residual-20261011/experiment.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    raw=m.source_archive(ROOT,state)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        members=json.loads(z.read('MEMBERS.json'))['files']
        for s in source_api.SYMBOLS:
            name=f'source_tables_not_model_inputs/economics/{s}_funding_events.parquet';b=z.read(name)
            require(digest(b)==members[name]['SHA256'],'Independent funding source identity')
            f=pq.read_table(io.BytesIO(b),columns=['calc_time_ms','last_funding_rate','funding_interval_hours'],
                filters=[('calc_time_ms','>=',START//1000),('calc_time_ms','<',DEADLINE//1000)]).to_pandas()
            for r in f.itertuples(index=False):events.append(dict(symbol=s,event_us=int(r.calc_time_ms)*1000,raw_rate=float(r.last_funding_rate),reported_interval_hours=float(r.funding_interval_hours)))
            funding_members.append(dict(symbol=s,member=name,member_SHA256=digest(b),events=len(f)))
    events.sort(key=lambda r:(r['event_us'],r['symbol']))
    rows=[];previous={}
    for s,source in frames.items():previous[s]=float(source['trade'].loc[source['trade'].timestamp_ms*1000==START-MINUTE,'quote_volume'].iloc[0])
    for t in range(START,DEADLINE,MINUTE):
        market={}
        for s,source in frames.items():
            i=int(np.searchsorted(source['trade'].timestamp_ms.to_numpy(),t//1000));r=source['trade'].iloc[i];mr=source['mark'].iloc[i]
            require(int(r.timestamp_ms)*1000==t and int(mr.timestamp_ms)*1000==t,'Actual minute present')
            market[s]=dict(open=float(r.open),close=float(r.close),quote_volume=float(r.quote_volume),mark=float(mr.close))
        rows.append((t,market))
    return rows,events,previous,marks,dict(trade=tc,mark=mc,composites=records,funding_source=m.SOURCE_COMMIT,
        funding_archive_SHA256=m.ARCHIVE_SHA,funding_members=funding_members,terminal_capacity_witnesses=capacity_witnesses,provider_downloads=0)


def run(state,source,expected=None):
    require(not state.exists() and state.resolve().is_relative_to(Path('/workspace')),'Fresh STATE')
    require(not git('status','--porcelain'),'Clean published source')
    if expected is None:require(git('rev-parse','HEAD').decode().strip()==source,'Exact remotelypublished source')
    for line in (HERE/'SOURCE_SHA256.txt').read_text().splitlines():
        sha,name=line.split(maxsplit=1);require(digest((ROOT/name).read_bytes())==sha,'SourceSHA '+name)
    state.mkdir();started=time.monotonic();raw=git('show',ARTIFACT+':'+OLD+'ACCOUNT.json');body=json.loads(raw)
    report=diagnose(body);rows,events,previous,marks,proof=actual_sources(state,body)
    account,recovery=financial_anchor(body,marks)
    extension=extend(account,rows,events,previous,START,DEADLINE)
    observed=dict(source_commit=source,anchor_artifact=ARTIFACT,anchor_SHA256=digest(raw),diagnosis=report,recovery=recovery,
        source_proof=proof,extension=extension,models_fit=0,original_wallet_replays=0,new_exit_extensions=1,
        original_selector_four_failed_gates_unchanged=True,full_general_scheduler_restore=False)
    if expected:
        saved=json.loads(git('show',expected+':research/terminal-reduce-only-exit-20261011/result/RESULT.json'))
        require(saved==observed,'Exactpublic exit/financialanchor restore')
        save(state/'PUBLIC_RESTORE.json',dict(status='PASS_EXACT_PUBLIC_FINANCIAL_ANCHOR_EXIT_RESTORE',artifact_commit=expected,
            original_wallet_replays=0,new_strategy_trials=0,models_fit=0,elapsed_seconds=time.monotonic()-started))
    save(state/'RESULT.json',observed);save(state/'TIMING.json',dict(total_seconds=time.monotonic()-started))
    require(time.monotonic()-started<600,'Frozen600s budget')
    print(json.dumps(dict(status=extension['status'],minutes=extension['minutes_observed'],fees=extension['fees_paid_USDT'],
        execution_loss=extension['execution_loss_paid_USDT'],funding=extension['funding_cash_USDT'],
        remaining_notional=extension['after']['gross_notional'],original_wallet_replays=0),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True);p.add_argument('--expected-commit')
    a=p.parse_args();run(a.state,a.source_commit,a.expected_commit)
