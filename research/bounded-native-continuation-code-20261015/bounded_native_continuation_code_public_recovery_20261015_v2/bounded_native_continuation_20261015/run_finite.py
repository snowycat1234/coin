"""Finite offline B/C runner. Requires a new exact external review and root GO.

No default launch, self-GO, resume, old baseline mutation, provider connection,
credential path, live venue or locked-source route is implemented.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import threading
import time
import traceback

HERE=Path(__file__).resolve().parent
LIMITS=dict(per_case_wall_seconds=600,CPU_threads=1,RSS_stop_bytes=2_000_000_000,
    AS_bytes=4_000_000_000,output_bytes=250_000_000,maximum_cases=2)


def utc():return datetime.now(timezone.utc).isoformat()
def sha(raw):return sha256(raw).hexdigest()
def own_bytes(path):return sum(p.stat().st_size for p in Path(path).rglob('*') if p.is_file())


def save(path,value):
    # Explicit mutable evidence export, never account/scheduler recovery.
    from integration import OWNED
    raw=(json.dumps(OWNED.export_tree(value),indent=2,allow_nan=False)+'\n').encode()
    path=Path(path)
    with path.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())


def limits():
    for which,value in ((resource.RLIMIT_AS,LIMITS['AS_bytes']),
            (resource.RLIMIT_CPU,600),(resource.RLIMIT_RSS,LIMITS['RSS_stop_bytes'])):
        resource.setrlimit(which,(value,value))
    if hasattr(os,'sched_getaffinity'):os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})


def environment():
    return dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',
        MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',POLARS_MAX_THREADS='1')


def validate_scope(args):
    import continuation_entry as entry
    prep=(Path(args.preparation)/'PREPARATION.json').read_bytes()
    go=Path(args.go).read_bytes();review=Path(args.review).read_bytes()
    parsed=json.loads(go)
    if parsed.get('permitted_modes')!=list(entry.MODES) or parsed.get('resource_limits')!=LIMITS:
        raise ValueError('EXACT_FIRST_TWO_CASE_B_C_FIXED_FINITE_SCOPE_REQUIRED')
    for variant in entry.MODES:
        admitted=entry.validate_root_go(prep,go,args.go_sha,policy_variant=variant)
        entry._validate_independent_review(prep,admitted,review,args.review_sha,go)
    return prep,go,review


def case(args):
    limits()
    import numpy as np
    import continuation_entry as entry
    import integration
    preparation,go,review=validate_scope(args)
    if args.mode not in entry.MODES:raise ValueError('FIXED_B_OR_C_MODE_REQUIRED')
    output=Path(args.case_output);output.mkdir(exist_ok=False)
    started=utc();began=time.monotonic();stopped=threading.Event()
    def watch():
        while not stopped.wait(.1):
            rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
            reason=('RSS_LIMIT' if rss>LIMITS['RSS_stop_bytes'] else
                'WALL_LIMIT' if time.monotonic()-began>600 else
                'OUTPUT_LIMIT' if own_bytes(output)>LIMITS['output_bytes'] else None)
            if reason:
                save(output/'RESOURCE_STOP.json',dict(reason=reason,UTC=utc(),RSS_bytes=rss));os._exit(137)
    threading.Thread(target=watch,daemon=True).start()
    try:
        sim,guard=entry.make_annual_case(args.source,args.preparation,go,args.go_sha,
            policy_variant=args.mode,review_raw=review,expected_review_sha256=args.review_sha)
        construction=time.monotonic()-began
        while sim.cursor<sim.end and sim.stop is None:
            sim.advance_day()
            print(json.dumps(dict(event='NATIVE_DAY_COMPLETE',policy_variant=args.mode,
                completed_minutes=sim.rows_written,stop_us=sim.stop,UTC=utc())),flush=True)
        result=integration.case_result(sim,guard)
        minute=result.pop('minute');values=minute.to_numpy();columns=minute.columns
        result['targets']=result['targets'].to_dicts()
        np.savez_compressed(output/'MINUTE.npz',values=values,columns=np.asarray(columns))
        with (output/'MINUTE.npz').open('rb') as stream:os.fsync(stream.fileno())
        save(output/'ACCOUNT_FINANCIAL_AUDIT.json',sim.account.snapshot())
        save(output/'PRIMARY_FINANCIAL_RECONCILIATION.json',result['primary_financial_reconciliation'])
        save(output/'GUARD_RECEIPTS.json',guard.receipts)
        quality=guard.causal_mark_quality_guard
        save(output/'CAUSAL_MARK_QUALITY.json',dict(identity=quality.identity,
            policy_SHA256=quality.policy_sha256,receipts=quality.receipts,
            original_interpolated_marks_execution_admitted=False))
        # Full native outputs preserve funding ownership, pending/expiry,
        # losses, conditionally forfeited collateral and paid-cost evidence.
        save(output/'NATIVE_RESULT.json',result)
        economics=result['economics']
        classification=('FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT' if economics['actual_paid_market_flat'] else
            'FULL_CALENDAR_CONDITIONAL_SETTLED_FLAT' if economics['conditional_settled_flat'] else
            'FULL_CALENDAR_RESIDUAL_OR_UNSETTLED_UNPAID' if economics['full_calendar'] else
            'NATIVE_HALT_PARTIAL_CALENDAR' if sim.account.status in integration.P.HALTS else
            'EXECUTION_INTERRUPTION_PARTIAL_CALENDAR')
        if entry.code_identity()!=json.loads(preparation)['code_identity']:
            raise ValueError('CODE_CHANGED_DURING_FINITE_CONTINUATION_CASE')
        receipt=dict(schema='FINITE_BOUNDED_NATIVE_CONTINUATION_CASE_V1',status=classification,
            policy_variant=args.mode,config=entry.CONFIG,cost=entry.COST,calendar=[entry.START,entry.END],
            root_GO_SHA256=args.go_sha,independent_review_SHA256=args.review_sha,
            preparation_SHA256=sha(preparation),source_identity=json.loads(preparation)['source_identity'],
            code_identity=entry.code_identity(),policy_identity=json.loads(preparation)['policy_identity'],
            started_UTC=started,ended_UTC=utc(),PID=os.getpid(),construction_seconds=construction,
            total_wall_seconds=time.monotonic()-began,
            max_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            CPU_seconds=resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,
            completed_minutes=sim.rows_written,required_minutes=entry.MINUTES,account_stop_us=sim.stop,
            limits=LIMITS,output_bytes=own_bytes(output),full_calendar=economics['full_calendar'],
            actual_paid_market_flat=economics['actual_paid_market_flat'],
            conditional_settled_flat=economics['conditional_settled_flat'],
            comparable_full_calendar_return=economics['comparable_full_calendar_return'],
            no_halt_reset=True,snapshot_restart_certified=False,locked_source_reads=0,
            actual_trades_or_orders=0,venue_settlement_certified=False,
            primary_financial_reconciliation_passed=result['primary_financial_reconciliation']['passed'])
        save(output/'CASE_RECEIPT.json',receipt)
        if own_bytes(output)>LIMITS['output_bytes']:raise RuntimeError('OUTPUT_LIMIT')
        save(output/'TERMINAL_CHECKPOINT.json',dict(case_receipt_SHA256=sha((output/'CASE_RECEIPT.json').read_bytes()),
            account_financial_audit_SHA256=sha((output/'ACCOUNT_FINANCIAL_AUDIT.json').read_bytes()),
            native_result_SHA256=sha((output/'NATIVE_RESULT.json').read_bytes()),
            primary_financial_reconciliation_SHA256=sha((output/'PRIMARY_FINANCIAL_RECONCILIATION.json').read_bytes()),
            all_evidence_fsynced=True,restart_permission=False))
        print(json.dumps(dict(event='CASE_TERMINAL',policy_variant=args.mode,status=classification,UTC=utc())),flush=True)
    except BaseException as error:
        if 'sim' in locals():
            try:save(output/'FAILED_ACCOUNT_FINANCIAL_AUDIT.json',sim.account.snapshot())
            except BaseException as audit_error:save(output/'FAILED_AUDIT_ERROR.json',dict(error=repr(audit_error)))
        save(output/'FAILURE.json',dict(error=repr(error),traceback=traceback.format_exc(),UTC=utc(),automatic_retry=False))
        raise
    finally:stopped.set()


def validate_saved_terminal(case_directory,*,preparation_raw,go_raw,expected_go_sha256,
                            expected_review_sha256,policy_variant):
    """Read-only saved-evidence reconciliation; creates no account or replay."""
    from decimal import Decimal as D,localcontext
    import integration
    directory=Path(case_directory);prep=json.loads(preparation_raw);go=json.loads(go_raw)
    body=(directory/'CASE_RECEIPT.json').read_bytes();receipt=json.loads(body)
    checkpoint=json.loads((directory/'TERMINAL_CHECKPOINT.json').read_bytes())
    referenced={'CASE_RECEIPT.json':'case_receipt_SHA256','ACCOUNT_FINANCIAL_AUDIT.json':'account_financial_audit_SHA256',
        'NATIVE_RESULT.json':'native_result_SHA256','PRIMARY_FINANCIAL_RECONCILIATION.json':'primary_financial_reconciliation_SHA256'}
    if (sha(go_raw)!=expected_go_sha256 or checkpoint.get('all_evidence_fsynced') is not True
            or checkpoint.get('restart_permission') is not False
            or any(sha((directory/name).read_bytes())!=checkpoint.get(key) for name,key in referenced.items())):
        raise ValueError('EXACT_SAVED_TERMINAL_ALL_REFERENCED_BYTES_REQUIRED')
    expected=dict(schema='FINITE_BOUNDED_NATIVE_CONTINUATION_CASE_V1',policy_variant=policy_variant,
        config=prep['config'],cost=prep['cost'],calendar=prep['calendar'],root_GO_SHA256=expected_go_sha256,
        independent_review_SHA256=expected_review_sha256,preparation_SHA256=sha(preparation_raw),
        source_identity=prep['source_identity'],code_identity=prep['code_identity'],policy_identity=prep['policy_identity'],
        required_minutes=(prep['calendar'][1]-prep['calendar'][0])//integration.MINUTE,limits=LIMITS,
        no_halt_reset=True,snapshot_restart_certified=False,locked_source_reads=0,actual_trades_or_orders=0,
        venue_settlement_certified=False,primary_financial_reconciliation_passed=True)
    if any(json.dumps(receipt.get(k),sort_keys=True)!=json.dumps(v,sort_keys=True) for k,v in expected.items()):
        raise ValueError('EXACT_SAVED_CASE_SCOPE_IDENTITY_REQUIRED')
    audit=json.loads((directory/'ACCOUNT_FINANCIAL_AUDIT.json').read_bytes())
    result=json.loads((directory/'NATIVE_RESULT.json').read_bytes())
    recon=json.loads((directory/'PRIMARY_FINANCIAL_RECONCILIATION.json').read_bytes())
    economics=result['economics'];summary=result['summary'];ds=summary['decimal_strings']
    if result.get('primary_financial_reconciliation')!=recon or recon.get('passed') is not True:
        raise ValueError('PRIMARY_SAVED_RECONCILIATION_BINDING_REQUIRED')
    with localcontext() as ctx:
        ctx.prec=100
        ledger=audit['financial_ledger'];cash=D(10000)+sum((D(r['free_cash_delta']) for r in ledger),D(0))
        debt=sum((D(r['unpaid_liability_delta']) for r in ledger),D(0))
        isolated={s:sum((D(r['isolated_delta'][s]) for r in ledger),D(0)) for s in integration.S}
        if (cash!=D(audit['free_cash']) or debt!=D(audit['unpaid_liability'])
                or set(audit['positions'])!=set(integration.S)
                or any(isolated[s]!=D(audit['positions'][s]['isolated_balance']) for s in integration.S)):
            raise ValueError('SAVED_PRIMARY_CASH_ISOLATED_DEBT_LEDGER_MISMATCH')
        settlements=audit['settlement_journal'];support=adjustment=D(0)
        for row in settlements:
            d=row['decimal_strings'];equity=D(d['pre_settlement_equity'])
            received=D(d['conditional_insurance_value_received']);forfeit=D(d['conditional_forfeiture_value_paid'])
            value=D(d['settlement_value_cashflow'])
            if (equity+received-forfeit!=0 or value!=received-forfeit
                    or D(d['NAV_after'])-D(d['NAV_before'])!=value
                    or D(d['free_cash_credit'])!=0):
                raise ValueError('SAVED_CONDITIONAL_SUPPORT_FORFEITURE_LEDGER_MISMATCH')
            support+=received;adjustment+=value
        if (D(economics['conditional_insurance_overshoot_absorption_USDT'])!=support
                or D(economics['conditional_NAV_adjustment_USDT'])!=adjustment
                or economics['conditional_position_settlements']!=len(settlements)
                or economics['actual_liquidation_fills']!=0):
            raise ValueError('SAVED_CONDITIONAL_MODEL_ECONOMICS_MISMATCH')
    with localcontext() as ctx:
        ctx.prec=40
        nav=D(audit['free_cash'])-D(audit['unpaid_liability'])
        for s in integration.S:
            p=audit['positions'][s];nav+=D(p['isolated_balance'])
            if D(p['quantity']):nav+=D(p['quantity'])*(D(audit['marks'][s][-1]['price'])-D(p['entry_price']))
        unrealized=sum((D(p['quantity'])*(D(audit['marks'][s][-1]['price'])-D(p['entry_price']))
            for s,p in audit['positions'].items() if D(p['quantity'])),D(0))
        totals=audit['totals'];gross_mid=D(totals['realized_PnL'])+unrealized+D(totals['execution_cost'])
        replay=(nav-D(10000))-(gross_mid-D(totals['execution_cost'])-D(totals['fees'])+D(totals['funding_cash']))
        if (recon.get('exact_frozen_native_secondary_arithmetic_replay_match') is not True
                or D(recon['native_40digit_secondary_PnL_bridge_residual'])!=replay
                or D(ds['accounting_bridge_error_USDT'])!=replay):
            raise ValueError('SAVED_EXACT_FROZEN_NATIVE_SECONDARY_ARITHMETIC_REPLAY_MISMATCH')
        if (nav!=D(ds['NAV']) or D(ds['free_cash'])!=D(audit['free_cash'])
                or D(ds['unpaid_liability'])!=D(audit['unpaid_liability'])
                or audit['totals']['fees']!=ds['fees_USDT'] or audit['totals']['funding_cash']!=ds['funding_USDT']):
            raise ValueError('SAVED_AUDIT_RESULT_BALANCE_MISMATCH')
    if (audit['status']!=summary['account_status'] or audit.get('halt_witness')!=summary.get('halt_witness')
            or set(summary['positions'])!=set(audit['positions'])):
        raise ValueError('SAVED_NATIVE_STATUS_WITNESS_POSITIONS_BINDING_MISMATCH')
    for symbol,position in audit['positions'].items():
        reported=summary['positions'][symbol]
        exact=reported.get('decimal_strings',{})
        if (any(D(exact.get(key,str(reported.get(key))))!=D(position[key])
                for key in ('quantity','entry_price','isolated_balance'))
                or reported.get('opened_us')!=position['opened_us']):
            raise ValueError('SAVED_NATIVE_EXACT_POSITION_BINDING_MISMATCH')
    complete=receipt['completed_minutes']==receipt['required_minutes'] and receipt['account_stop_us'] is None
    flat=all(D(p['quantity'])==0 for p in audit['positions'].values())
    healthy=audit['status'] not in integration.P.HALTS and D(audit['unpaid_liability'])==0
    paid=bool(complete and flat and healthy and not settlements)
    conditional=bool(complete and flat and healthy and settlements)
    if not complete:
        witness=audit.get('halt_witness');stop=receipt['account_stop_us']
        if (audit['status'] not in integration.P.HALTS or not isinstance(witness,dict) or not witness
                or type(stop) is not int or stop!=audit['clock_us'] or witness.get('event_us')!=stop
                or not prep['calendar'][0]<=stop<=prep['calendar'][1]
                or receipt['completed_minutes']!=(stop-prep['calendar'][0]-1)//integration.MINUTE):
            raise ValueError('INCOMPLETE_ACTIVE_OR_EXECUTION_INTERRUPTION_IS_NOT_ECONOMIC_HALT_PAUSE_QUEUE')
        def witness_decimal(key):
            value=D(str(witness.get('decimal_strings',{}).get(key,witness.get(key))))
            if not value.is_finite():raise ValueError('FINITE_NATIVE_HALT_WITNESS_REQUIRED')
            return value
        witness_nav,witness_debt=witness_decimal('NAV'),witness_decimal('unpaid_liability')
        if witness_nav!=nav or witness_debt!=D(audit['unpaid_liability']) or witness_debt<0:
            raise ValueError('EXACT_SAVED_NATIVE_HALT_NAV_DEBT_REQUIRED')
        with localcontext() as ctx:
            ctx.prec=40
            if 'symbol' in witness:
                symbol=witness['symbol']
                if symbol not in audit['positions']:raise ValueError('SAVED_NATIVE_HALT_SYMBOL_REQUIRED')
                position=audit['positions'][symbol];q=D(position['quantity'])
                mark=D(audit['marks'][symbol][-1]['price'])
                equity=D(position['isolated_balance'])+q*(mark-D(position['entry_price']))
                maintenance=abs(q)*mark*D('.005')
                if (q==0 or mark<=0 or witness_decimal('quantity')!=q
                        or witness_decimal('mark_price')!=mark or witness_decimal('isolated_equity')!=equity
                        or witness_decimal('maintenance_margin')!=maintenance
                        or audit['status']=='LIQUIDATION_REQUIRED_HALT' and not (0<equity<=maintenance and nav>0 and witness_debt==0)
                        or audit['status']=='BANKRUPT_HALT' and not (equity<=0 or nav<=0 or witness_debt>0)):
                    raise ValueError('EXACT_SAVED_NATIVE_ISOLATED_HALT_PREDICATE_REQUIRED')
            elif audit['status']!='BANKRUPT_HALT' or not (nav<=0 or witness_debt>0):
                raise ValueError('EXACT_SAVED_NATIVE_GLOBAL_BANKRUPTCY_PREDICATE_REQUIRED')
    classification=('FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT' if paid else
        'FULL_CALENDAR_CONDITIONAL_SETTLED_FLAT' if conditional else
        'FULL_CALENDAR_RESIDUAL_OR_UNSETTLED_UNPAID' if complete else 'NATIVE_HALT_PARTIAL_CALENDAR')
    expected_return=float(nav/D(10000)-1) if paid or conditional else None
    for record,keys in ((receipt,('full_calendar','actual_paid_market_flat','conditional_settled_flat')),
            (economics,('full_calendar','actual_paid_market_flat','paid_flat','conditional_settled_flat'))):
        if any(type(record.get(key)) is not bool for key in keys):raise ValueError('STRICT_SAVED_TERMINAL_BOOLEAN_TYPES_REQUIRED')
    if (receipt['status']!=classification or receipt['full_calendar']!=complete
            or receipt['actual_paid_market_flat']!=paid or receipt['conditional_settled_flat']!=conditional
            or economics['full_calendar']!=complete or economics['actual_paid_market_flat']!=paid
            or economics['paid_flat']!=paid or economics['conditional_settled_flat']!=conditional
            or economics['paid_net_return']!=(expected_return if paid else None)
            or economics['conditional_model_net_return']!=(expected_return if conditional else None)
            or receipt['comparable_full_calendar_return']!=expected_return
            or economics['comparable_full_calendar_return']!=expected_return
            or summary['completed_minutes']!=receipt['completed_minutes']
            or summary['stop_us']!=receipt['account_stop_us']
            or receipt['completed_minutes']<0 or receipt['completed_minutes']>receipt['required_minutes']
            or receipt['total_wall_seconds']>600 or receipt['max_RSS_bytes']>LIMITS['RSS_stop_bytes']
            or own_bytes(directory)>LIMITS['output_bytes']):
        raise ValueError('SAVED_TERMINAL_CALENDAR_PAYMENT_TAXONOMY_OR_RESOURCE_MISMATCH')
    binding=audit['historical_execution_scope']
    for key,value in dict(preparation_SHA256=sha(preparation_raw),source_identity=prep['source_identity'],
            root_GO_SHA256=expected_go_sha256,independent_review_SHA256=expected_review_sha256,
            policy_identity=prep['policy_identity'],policy_variant=policy_variant,config=prep['config'],
            generated_fixture_scope_used=False,fresh_genesis_only=True).items():
        if not isinstance(binding,dict) or binding.get(key)!=value:
            raise ValueError('SAVED_ACTUAL_EXECUTION_SCOPE_BINDING_MISMATCH')
    return receipt


def controller(args):
    import continuation_entry as entry
    preparation,go,review=validate_scope(args)
    output=Path(args.output);output.mkdir(exist_ok=False)
    for name,body in (('ROOT_GO.json',go),('INDEPENDENT_REVIEW.json',review)):
        with (output/name).open('xb') as stream:stream.write(body);stream.flush();os.fsync(stream.fileno())
    results=[];start=utc()
    for mode in entry.MODES:
        command=[sys.executable,str(HERE/'run_finite.py'),'--case','--mode',mode,
            '--source',str(Path(args.source).resolve()),'--preparation',str(Path(args.preparation).resolve()),
            '--go',str((output/'ROOT_GO.json').resolve()),'--go-sha',args.go_sha,
            '--review',str((output/'INDEPENDENT_REVIEW.json').resolve()),'--review-sha',args.review_sha,
            '--case-output',str((output/mode).resolve())]
        with (output/(mode+'.log')).open('x') as log:
            process=subprocess.Popen(command,cwd=HERE,env=environment(),stdout=log,stderr=subprocess.STDOUT,preexec_fn=limits)
            try:code=process.wait(timeout=600)
            except subprocess.TimeoutExpired:process.kill();process.wait();code=124
        results.append(dict(policy_variant=mode,PID=process.pid,exit_code=code))
        if code:
            save(output/'CONTROLLER_FAILURE.json',dict(cases=results,UTC=utc(),automatic_retry=False))
            raise RuntimeError('FINITE_CASE_FAILED_NO_AUTOMATIC_RERUN:'+mode)
        receipt=validate_saved_terminal(output/mode,preparation_raw=preparation,go_raw=go,
            expected_go_sha256=args.go_sha,expected_review_sha256=args.review_sha,policy_variant=mode)
        body=(output/mode/'CASE_RECEIPT.json').read_bytes()
        results[-1].update(receipt_SHA256=sha(body),status=receipt['status'])
    reports={mode:json.loads((output/mode/'NATIVE_RESULT.json').read_bytes())['economics'] for mode in entry.MODES}
    b,c=(reports[mode] for mode in entry.MODES)
    compare=(b['comparable_full_calendar_return'] is not None and c['comparable_full_calendar_return'] is not None)
    save(output/'B_C_COMPARISON.json',dict(comparable_completed_calendars=compare,
        C_minus_B_return_difference=c['comparable_full_calendar_return']-b['comparable_full_calendar_return'] if compare else None,
        attribution='WHOLE_BOUNDED_MARGIN_MANAGEMENT_PACKAGE_NOT_PURE_TOPUP_TRANSFER',
        conditional_settlement_assumption=entry.SETTLEMENT_MODE,by_mode=reports,
        native_venue_certified=False,annual_return_improvement_over_HALTED_PREFIX_claimed=False))
    save(output/'CONTROLLER_RECEIPT.json',dict(status='BOTH_APPROVED_CASES_TERMINAL',started_UTC=start,
        ended_UTC=utc(),cases=results,root_GO_SHA256=args.go_sha,history_scope='ONLY_FULL2024_STATIC50_MID_B_C_BASE27',
        no_other_years=True,no_parameter_search=True,publication_actions=0))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--case',action='store_true')
    for name in ('source','preparation','go','go-sha','review','review-sha'):parser.add_argument('--'+name,required=True)
    for name in ('mode','case-output','output'):parser.add_argument('--'+name)
    args=parser.parse_args();case(args) if args.case else controller(args)
