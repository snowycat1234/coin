"""Direct saved-leg cost/turnover diagnosis; never replay an account or market.

Pure API: diagnose_case(trades, target_meta, summary, funding=None). Root freezes --protocol
after the new synthetic case. parents contain actual/independent references
{path,sha256,required_status,task_id}, and modes: D049 LO/SO, D048 LS.
Their accepted trades.json, target_meta.json and funding.json are read sequentially.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from decimal import Decimal, localcontext
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import sys
import time
from quant import resources

ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
CONTRACT='D049_TURTLE_SAVED_LEG_TURNOVER_REASON_DIAGNOSTIC_V1'
STATUS='COMPLETE_TURTLE_SAVED_LEG_TURNOVER_REASON_DIAGNOSTIC_NOT_ALPHA_OR_APR'
REASONS=('ENTRY','ADD','EXIT','STOP','RISK_REDUCTION','TERMINAL','UNKNOWN')
COSTS=('BASE27','STRESS43');UNITS=('RAW_AS_FRACTION','RAW_AS_PERCENT')
BUDGET=dict(new_owned_bytes=50_000_000,peak_RSS_bytes=1_000_000_000,wall_seconds=120)
FIELDS=('mid_notional_USDT','fill_notional_USDT','fees_USDT','execution_cost_USDT')
CASH_TOL=1e-7


def require(condition,message):
    if not condition:raise ValueError(message)


def finite(value):
    number=float(value);require(math.isfinite(number),'Finite saved value');return number


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(65536),b''):digest.update(block)
    return digest.hexdigest()


def read_json(path,digest=None,expected_bytes=None,limit=10_000_000):
    path=Path(path)
    base=ROOT if path.is_relative_to(ROOT) else STATE
    require(path.is_relative_to(base) and path.is_file() and path.suffix=='.json'
        and path.stat().st_size<=limit,'Authorized bounded JSON only')
    for ancestor in (path,*path.parents):
        require(not ancestor.is_symlink(),'No symlink payload')
        if ancestor==base:break
    require(expected_bytes is None or path.stat().st_size==expected_bytes,'Saved artifact bytes changed')
    require(digest is None or sha(path)==digest,'Saved JSON SHA changed')
    with path.open(encoding='utf-8') as stream:return json.load(stream)


def closed(identity):
    require(isinstance(identity,str) and len(identity)==32 and all(c in '0123456789abcdef' for c in identity),'Exact task identity')
    path=STATE/'task-progress'/('task-'+identity+'.json');task=read_json(path)
    require(task['id']==identity and task['status']=='completed' and task['exit_code']==0,'Actual prerequisite closed0')
    return dict(path=str(path),sha256=sha(path),task=task)


def intent_mapping(journal):
    intents={};notifications={};duplicates=dict(notifications=0,intents=0)
    for row in journal:
        if row.get('event')=='INTENT_SUBMITTED':
            key=row['id'];identity={k:row.get(k) for k in ('symbol','side','signal_us','kind')}
            require(key not in intents or intents[key]==identity,'Conflicting INTENT_SUBMITTED identity')
            duplicates['intents']+=int(key in intents);intents[key]=identity
        elif row.get('event')=='ACTUAL_FILL_NOTIFIED':
            key=row['fill_id']
            require(key not in notifications or notifications[key]==row,'Conflicting ACTUAL_FILL_NOTIFIED identity')
            duplicates['notifications']+=int(key in notifications);notifications[key]=row
    return intents,notifications,duplicates


def aggregate(rows):
    fills={r['fill_id'] for r in rows if r['fill_id'] is not None}
    intents={r['intent_id'] for r in rows if r['intent_id'] is not None}
    totals={key:math.fsum(r[key] for r in rows) for key in FIELDS}
    small=[r for r in rows if r['small']]
    return dict(legs=len(rows),distinct_fills=len(fills),logical_intents=len(intents),**totals,
        total_cost_USDT=totals['fees_USDT']+totals['execution_cost_USDT'],
        cost_percent_full_capital=(totals['fees_USDT']+totals['execution_cost_USDT'])/100,
        small_fill_notional_lt10=dict(legs=len(small),**{k:math.fsum(r[k] for r in small)
            for k in ('fill_notional_USDT','fees_USDT','execution_cost_USDT')}))


def asset_attribution(trades,funding,summary):
    """Original same-quantity mid-cashflow gross, separately from reasons.

Only the saved terminal signed mark closes the gross bridge. This does not
reconstruct an account, charge new fees, predict or allocate gross to exits.
"""
    symbols={'BTCUSDT','ETHUSDT'}|{r['symbol'] for r in trades}
    if funding is not None:symbols|={r['symbol'] for r in funding}
    marks=summary.get('terminal_signed_marked_notional',{})
    rows=[]
    for symbol in sorted(symbols):
        legs=[r for r in trades if r['symbol']==symbol]
        mid_cashflow=-math.fsum(finite(r['position_delta'])*finite(r['mid_price']) for r in legs)
        terminal=finite(marks[symbol]) if symbol in marks else None
        events=[r for r in funding if r['symbol']==symbol] if funding is not None else None
        complete_funding=events is not None and all('signed_funding_USDT' in r for r in events)
        paid=math.fsum(finite(r['signed_funding_USDT']) for r in events) if complete_funding else None
        fee=math.fsum(finite(r['fee_USDT_mid']) for r in legs)
        execution=math.fsum(finite(r['execution_cost']) for r in legs)
        gross=mid_cashflow+terminal if terminal is not None else None
        net=gross-fee-execution+paid if gross is not None and paid is not None else None
        rows.append(dict(symbol=symbol,recorded_mid_cashflow_USDT=mid_cashflow,
            terminal_signed_marked_notional_USDT=terminal,price_PnL_gross_USDT=gross,
            signed_funding_USDT=paid,funding_events=len(events) if events is not None else None,
            fees_USDT=fee,execution_cost_USDT=execution,net_contribution_USDT=net,
            net_contribution_percent_full_10000=net/100 if net is not None else None,
            scope='SAVED_MID_CASHFLOW_PLUS_TERMINAL_MARK_CONDITIONAL_FUNDING' if net is not None else 'UNKNOWN_MISSING_TERMINAL_OR_FUNDING'))
    checked={}
    for field,target in (('price_PnL_gross_USDT','gross_PnL_same_quantities'),('signed_funding_USDT','funding_USDT'),('net_contribution_USDT','net_PnL')):
        if target in summary and all(r[field] is not None for r in rows):
            error=abs(math.fsum(r[field] for r in rows)-finite(summary[target]))
            require(error<=CASH_TOL,'Saved asset bridge mismatch: '+target);checked[target]=error
    return dict(assets=rows,summary_bridge_errors_USDT=checked,funding_event_count=len(funding) if funding is not None else None,
        gross_formula='MINUS_SUM_POSITION_DELTA_TIMES_MID_PLUS_SAVED_TERMINAL_SIGNED_MARK',
        asset_returns_do_not_use_separate_asset_capital=True,gross_attributed_to_reason=False,
        funding_unit_certified=False,new_account_or_weighted_entry_model=False)


def diagnose_case(trades,target_meta,summary,funding=None):
    """Classify costs by explicit intent and owned direction, never exit PnL.

Duplicate notifications affect only mapping. CLOSE+OPEN sharing one fill_id
remain separate financial legs. Repeated (fill_id,leg) is an input error.
Missing/identity-mismatched evidence preserves all money under UNKNOWN.
"""
    require(isinstance(trades,list) and isinstance(target_meta.get('journal'),list),'Saved journal schema')
    intents,notifications,duplicates=intent_mapping(target_meta['journal'])
    grouped=defaultdict(list);rows=[];seen=set();unknown=[]
    for index,trade in enumerate(trades):
        fill=trade.get('fill_id');leg=trade.get('leg');symbol=trade['symbol']
        require(leg in ('OPEN','CLOSE'),'Known financial leg')
        identity=(fill,leg) if fill is not None else ('MISSING_FILL_ID_ROW_'+str(index),leg)
        require(identity not in seen,'Duplicate financial leg');seen.add(identity)
        quantity=finite(trade['quantity']);mid=finite(trade['mid_price']);price=finite(trade['fill_price'])
        fee=finite(trade['fee_USDT_mid']);cost=finite(trade['execution_cost'])
        require(quantity>0 and mid>0 and price>0 and fee>=0 and cost>=0,'Positive quantity/price and nonnegative costs')
        owner=finite(trade['quantity_before'] if leg=='CLOSE' else trade['position_delta'])
        direction='LONG' if owner>0 else 'SHORT' if owner<0 else 'UNKNOWN'
        notice=notifications.get(fill);intent_id=notice.get('intent_id') if notice else None
        intent=intents.get(intent_id);reason='UNKNOWN';why='MISSING_NOTIFICATION_OR_INTENT'
        if intent is not None:
            matched=all(intent.get(k) is not None and intent[k]==trade.get(k) for k in ('symbol','side','signal_us'))
            if matched and intent['kind'] in REASONS[:-1]:reason=intent['kind'];why=None
            else:why='IDENTITY_MISMATCH_OR_UNKNOWN_KIND'
        exact=trade.get('decimal_strings',{})
        with localcontext() as context:
            context.prec=80
            fill_notional=Decimal(str(exact.get('quantity',trade['quantity'])))*Decimal(str(exact.get('fill_price',trade['fill_price'])))
        row=dict(fill_id=fill,intent_id=intent_id if reason!='UNKNOWN' else None,
            mid_notional_USDT=quantity*mid,fill_notional_USDT=float(fill_notional),fees_USDT=fee,
            execution_cost_USDT=cost,small=fill_notional<Decimal('10'))
        grouped[direction,symbol,reason].append(row);rows.append(row)
        if reason=='UNKNOWN' and len(unknown)<20:unknown.append(dict(row=index,fill_id=fill,intent_id=intent_id,symbol=symbol,leg=leg,reason=why))
    totals=aggregate(rows)
    expected={'fill_notional_USDT':summary['gross_fill_turnover_USDT'],
        'fees_USDT':summary['fees_USDT'],'execution_cost_USDT':summary['execution_cost_USDT']}
    differences={k:abs(totals[k]-finite(value)) for k,value in expected.items()}
    require(totals['legs']==summary['trade_legs'] and max(differences.values(),default=0)<=CASH_TOL,'Saved totals do not reconcile')
    if summary.get('normalized_total_turnover') is not None:
        require(abs(totals['fill_notional_USDT']/10000-finite(summary['normalized_total_turnover']))<=1e-10,'Saved turnover definition mismatch')
    groups=[dict(direction=d,symbol=s,reason=r,**aggregate(values)) for (d,s,r),values in sorted(grouped.items())]
    reason_totals=[dict(reason=reason,**aggregate([row for (d,s,r),values in grouped.items() if r==reason for row in values]))
        for reason in REASONS]
    unknown_legs=sum(g['legs'] for g in groups if g['reason']=='UNKNOWN')
    return dict(groups=groups,reason_totals=reason_totals,totals=totals,
        asset_price_and_funding_attribution=asset_attribution(trades,funding,summary),
        mapping=dict(mapped_legs=len(rows)-unknown_legs,UNKNOWN_legs=unknown_legs,
            duplicate_notifications=duplicates['notifications'],duplicate_intent_submissions=duplicates['intents'],
            notified_distinct_fills=len(notifications),submitted_distinct_intents=len(intents),unknown_witnesses=unknown),
        reconciliation=dict(saved_summary_trade_legs=summary['trade_legs'],
            maximum_absolute_summary_difference_USDT=max(differences.values(),default=0),PASS=True),
        initial_capital_USDT=10000,execution_cost_includes_spread_and_slippage=True,
        size_lt10_is_additional_tag_not_a_reason=True,reason_tables_are_alternative_views_not_additive=True,
        realized_exit_PnL_attributed_to_reason=False)


def write_new(path,value):
    payload=(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()
    require(len(payload)<=5_000_000,'Small diagnostic output')
    with Path(path).open('xb') as stream:stream.write(payload)
    return hashlib.sha256(payload).hexdigest(),len(payload)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('protocol','output','run-dir'):parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();began=time.monotonic();spec=read_json(args.protocol);proto_sha=sha(args.protocol)
    require(spec['contract_id']==CONTRACT and spec['budgets']==BUDGET and spec['ready_to_execute'] is True
        and os.environ.get('COIN_TASK_ID') and sys.prefix==str(STATE/'v8-clean-env-20261002-v2'),'Frozen bounded clean caller')
    require(args.protocol.parent==ROOT/'protocols' and args.run_dir==Path(spec['run_dir'])
        and args.run_dir.parent==STATE and not args.run_dir.exists()
        and args.output==(ROOT/spec['output_path']).resolve() and args.output.parent==ROOT/'reports/fast_research'
        and not args.output.exists(),'Exclusive metadata output')
    own=Path(__file__).relative_to(ROOT).as_posix();sources=dict(spec['frozen_sources'])
    require(sources.get(own)==sha(__file__) and 'state/dataset_lock.json' not in sources,'Exact diagnostic source; private lock never parsed')
    for name,digest in sources.items():
        path=ROOT/name;require(path.is_relative_to(ROOT) and '..' not in Path(name).parts and path.is_file()
            and sha(path)==digest,'Frozen small source changed')
    for name,digest in spec.get('local_non_git_hash_guard',{}).items():
        require(name=='state/dataset_lock.json' and sha(ROOT/name)==digest,'Private hash-only guard')
    smoke=spec['required_smoke_receipt'];test=read_json(ROOT/smoke['path'],smoke['sha256'])
    require(test['status']==smoke['required_status'] and test['binding']['task_id']==smoke['task_id']
        and test['test_exit_code']==0 and test['source_bytes_unchanged']
        and test['junit_counts']==dict(tests=1,failures=0,errors=0,skipped=0),'One genuine new synthetic case')
    closed(test['binding']['task_id'])
    before=resources.status();require(before['ram_limit_bytes']<=5_000_000_000 and before['swap_bytes']==0 and not before['gpu_used'],'Shared limits')
    selected=[];tasks={};input_sources={};window=None
    for parent in spec['parents']:
        actual_ref,audit_ref=parent['actual'],parent['independent'];reports=[]
        for role,ref in (('MARKET',actual_ref),('FINANCE',audit_ref)):
            path=ROOT/ref['path'];report=read_json(path,ref['sha256']);tasks[parent['id']+':'+role]=closed(ref['task_id'])
            require(report['status']==ref['required_status'] and report['binding']['task_id']==ref['task_id'],'Accepted report/task')
            reports.append(report);sources[ref['path']]=ref['sha256']
        actual,audit=reports
        require(audit['actual_report_sha256']==actual_ref['sha256'] and actual['funding_rate_unit']=='UNCONFIRMED'
            and not actual['unit_certified'] and not actual['native_market_certified'],'Accepted conditional finance only')
        if window is None:window=actual['input_windows']
        require(actual['input_windows']==window,'Same full303 source window')
        proofs={c['id']:c for c in audit['cases']}
        for case in actual['cases']:
            if case['mode'] not in parent['modes']:continue
            proof=proofs[case['id']]
            require(case['period']=='303D' and proof['complete_calendar_verified']
                and case['summary']['completed_minutes']==case['summary']['required_minutes']==436320,'Complete accepted303-day case')
            require(case['summary']['terminal_cash_realized'] and all(p['quantity']==0 for p in case['summary']['positions'].values())
                and case['summary']['terminal_marked_notional']==0,'Accepted flat terminal; no free liquidation added')
            artifacts={name:case['artifacts'][name] for name in ('trades.json','target_meta.json','funding.json')}
            selected.append((case,proof,artifacts))
    expected={(c,u,m) for c in COSTS for u in UNITS for m in ('LONG_ONLY','SHORT_ONLY','LONG_SHORT')}
    require(len(selected)==12 and {(c['cost_id'],c['unit_id'],c['mode']) for c,p,a in selected}==expected,'Exactly twelve declared Turtle cases')
    args.run_dir.mkdir();binding=dict(task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),protocol_sha256=proto_sha,
        source_hashes=dict(sources),command=[sys.executable,*sys.argv])
    rb_sha,_=write_new(args.run_dir/'RUN_BINDING.json',binding);results=[]
    for number,(case,proof,artifacts) in enumerate(selected,1):
        payloads={}
        for name,ref in artifacts.items():
            path=Path(ref['path']);require(path.parent.name==case['id'] and path.name==name and path.is_relative_to(STATE),'Exact saved case artifact')
            payloads[name]=read_json(path,ref['sha256'],ref['bytes']);input_sources[str(path)]=ref
        diagnostic=diagnose_case(payloads['trades.json'],payloads['target_meta.json'],case['summary'],payloads['funding.json'])
        require(diagnostic['totals']['legs']==proof['completed_fills_verified'],'Independent saved fill count')
        require(diagnostic['asset_price_and_funding_attribution']['funding_event_count']==case['summary']['funding_observed_events']
            and all(r['net_contribution_USDT'] is not None for r in diagnostic['asset_price_and_funding_attribution']['assets']),
            'Every recorded asset funding event and terminal bridge is present')
        context={k:case['summary'].get(k) for k in ('net_PnL','gross_PnL_same_quantities','funding_USDT','fees_USDT',
            'execution_cost_USDT','spread_cost_USDT','slippage_cost_USDT','daily_metrics','realized_exposure',
            'all_observation_max_drawdown','minute_max_drawdown','maximum_actual_gross_weight','maximum_actual_asset_weights',
            'long_short_marked_contribution','daily_net_gain_concentration','months','terminal_marked_notional')}
        results.append(dict(id=case['id'],mode=case['mode'],cost_id=case['cost_id'],unit_id=case['unit_id'],
            accepted_financial_context=context,**diagnostic));del payloads
        print(json.dumps(dict(completed_cases=number,total_cases=12,last_case=case['id'])),flush=True)
        require(time.monotonic()-began<=120 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=1_000_000_000,'Diagnostic resource budget')
    after=resources.status();require(after['ram_limit_bytes']<=5_000_000_000 and after['swap_bytes']==0 and not after['gpu_used'],'Shared limits remain')
    result=dict(status=STATUS,binding=binding,run_dir=str(args.run_dir),run_binding_sha256=rb_sha,cases=results,
        completed_cases=12,completed_saved_JSON_files=36,input_artifact_proofs=input_sources,closed_prerequisite_tasks=tasks,
        same303_window=True,separate_full_initial_capital_each_USDT=10000,no_accounts_added_or_NAV_joined=True,
        aggregate_fee_denominator='EACH_SEPARATE_FULL_10000_NOT_SUM_OF_CASES',
        cost_scope='FEE_PLUS_EXECUTION_COST_ONCE_EXECUTION_ALREADY_INCLUDES_SPREAD_AND_SLIPPAGE',
        market_source_QA_or_account_replay=False,new_strategy_or_parameter_search=False,models_fit=0,orders_sent=0,GPU=0,
        candidate='NO_QUALIFIED_CANDIDATE',investment='CASH_NONE',long_term_APR='NOT_EVALUABLE',
        funding_unit_certified=False,native_market_certified=False,common_caps_equal_realized_risk=False,
        resources_before=before,resources_after=after,elapsed_seconds=time.monotonic()-began,
        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    digest,size=write_new(args.output,result)
    require(size+(args.run_dir/'RUN_BINDING.json').stat().st_size<=50_000_000,'Exclusive new metadata budget');print(digest)


if __name__=='__main__':main()
