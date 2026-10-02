"""Unexecuted D032 two-period audit entry; source/task schema awaits frozen actuals.
Reuses accepted source readers and independent pair finance. Never calls any
production gate_witness/simulate_account or replays an accepted control account.
"""
import hashlib, importlib.util, json, os, resource, sys, time
from pathlib import Path
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
WORK=STATE/'test-d032-past-funding-exit-independent-audit-20261003-v1'
OUT=ROOT/'reports/fast_research/CARRY_PAST_FUNDING_EXIT_TWO_PERIOD_DECIMAL_AUDIT_20261003_V1.json'
CALENDARS={
 '122D':dict(start=1754006400000000,end=1764547200000000,minutes=175680,events=732,days=122,
     months=['2025-08','2025-09','2025-10','2025-11'],files=32),
 '90D':dict(start=1764547200000000,end=1772323200000000,minutes=129600,events=540,days=90,
     months=['2025-12','2026-01','2026-02'],files=24)}

def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):digest.update(block)
    return digest.hexdigest()
def load(path):return json.loads(Path(path).read_bytes())
def need(ok,message):
    if not ok:raise AssertionError(message)
def new_json(path,value):
    with Path(path).open('x',encoding='utf-8') as stream:json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False)
def imported(label,path,digest):
    need(sha(path)==digest,'Exact accepted source changed before import:'+str(path))
    spec=importlib.util.spec_from_file_location(label,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def main():
    began=time.monotonic();bound=load(WORK/'ACTUAL_BINDING.json')
    need(sys.prefix==str(STATE/'v8-clean-env-20261002-v2') and os.environ.get('COIN_TASK_ID')
         and sha(__file__)==bound['checker_sha256'] and not OUT.exists(),'Unique closed0 bounded audit/code binding')
    report=dict(status='FAIL_D032_TWO_PERIOD_DECIMAL_INDEPENDENT_AUDIT',
        binding=dict(task_id=os.environ['COIN_TASK_ID'],checker_sha256=sha(__file__),ACTUAL_BINDING_sha256=sha(WORK/'ACTUAL_BINDING.json')),
        independent_source=str(Path(__file__)),independent_source_sha256=sha(__file__),cases=[],completed_cases_verified=0,
        cash_absolute_tolerance_USDT='1e-7',ratio_absolute_tolerance='1e-10',
        financial_scope='CONDITIONAL_UNVERIFIED_RAW_FRACTIONS_CLOSE_PROXY_ACCOUNTING_NOT_NATIVE_OR_LONG_TERM_APR',
        old_control_financial_replayed=False,raw_ZIP_or_CRC_read=False,old_QA_or_green_tests_repeated=False,
        production_gate_or_simulate_called=False,actual_HTTP_requests=0,models_fit=0,orders_sent=0,
        funding_unit_certified=False,historical_signal_availability_certified=False,
        capital_net_APR='NOT_EVALUABLE',candidate_status='NO_QUALIFIED_CANDIDATE')
    try:
        for path,digest in bound['small_inputs'].items():need(sha(path)==digest,'Bound small metadata/code changed:'+path)
        spec=load(ROOT/bound['protocol_path'])
        need(spec['contract_id']=='CARRY_PAST_FUNDING_EXIT_D032_V1' and set(spec['period_contracts'])==set(CALENDARS),
             'One fixed gate over both accepted complete calendars')
        core=imported('d032_core',bound['core_path'],bound['core_sha256'])
        pair=imported('d032_accepted_pair_finance',bound['pair_audit_path'],bound['pair_audit_sha256'])
        delta=imported('d032_accepted_pair_delta',bound['pair_delta_path'],bound['pair_delta_sha256'])
        reader=imported('d032_accepted_price_reader',bound['price_reader_path'],bound['price_reader_sha256'])
        old90=imported('d032_accepted_90d_input_reader',bound['accepted_90d_audit_path'],bound['accepted_90d_audit_sha256'])
        rb=imported('d032_accepted_source_path_adapter',bound['accepted_90d_blocks_path'],bound['accepted_90d_blocks_sha256'])
        gate=imported('d032_independent_gate_delta',WORK/'gate_delta.py',bound['gate_delta_sha256'])
        need(core.USDT_TOL==core.D('1e-7') and core.RATIO_TOL==core.D('1e-10'),'Accepted cash/ratio tolerance')
        rules=spec['gate_rules']
        need(rules['minimum_hold_us']==8*gate.DAY and rules['observed_window']=='[D-8DAY,D-1DAY)'
             and rules['decision_observation_offset_us']==1 and rules['window_start_strictly_after_entry'] is True
             and rules['threshold_signed_owned_cash_USDT']==0. and rules['condition']=='SUM_LE_ZERO'
             and rules['decision_arithmetic']=='MATH_FSUM_OF_ACTUAL_CREDITED_FLOAT64_LEDGER_CASH_EXACT_LE_ZERO_NO_BAND'
             and rules['input']=='ACTUALLY_OWNED_SIGNED_FUNDING_CASH_ACCOUNT_SUM_BOTH_SYMBOLS'
             and rules['publication_assumption']=='UNCERTIFIED_ONE_UTC_DAY_LAG'
             and rules['no_reentry'] is rules['no_extra_capital'] is rules['no_HPO'] is True,'No lookahead/rate sum/zero band/reentry')
        expected_hashes=dict(spec['frozen_sources']);expected_hashes[bound['protocol_path']]=sha(ROOT/bound['protocol_path'])
        for path,digest in expected_hashes.items():need(sha(ROOT/path)==digest,'Frozen master dependency changed:'+path)
        report['verified_source_hashes']=expected_hashes
        smoke=load(ROOT/spec['required_smoke_receipt']);report['smoke_actual_task']=reader.task(smoke['binding']['task_id'])
        need(smoke['status']=='PASS_D032_PAST_FUNDING_EXIT_SYNTHETIC_NOT_MARKET_OR_AVAILABILITY_PROOF'
             and smoke['test_exit_code']==0 and smoke['junit_counts']==dict(tests=1,errors=0,failures=0,skipped=0)
             and smoke['source_bytes_unchanged'] is True and smoke['price_arrays_read'] is False
             and smoke['funding_arrays_read'] is False and smoke['binding']['source_hashes']==expected_hashes,
             'One new closed same-source synthetic gate case')
        need([c['period'] for c in bound['actuals']]==['122D','90D'],'Two explicit complete-period selectors')
        selected=[]
        for case in bound['actuals']:
            period=case['period'];calendar=CALENDARS[period];parent_pin=spec['period_contracts'][period]
            need(sha(ROOT/parent_pin['path'])==parent_pin['sha256']==spec['frozen_sources'][parent_pin['path']],
                 'Exact accepted parent contract')
            parent=load(ROOT/parent_pin['path'])
            parent_rules=parent['rules'] if period=='122D' else parent['policies']['PAIR_TRIM']
            need(spec['rules']==dict(parent_rules,past_funding_exit=rules) and parent['source_calendar']==calendar['months']
                 and parent['expected_minutes_per_asset']==calendar['minutes'] and parent['expected_funding_events']==calendar['events'],
                 'Old money/caps/fees unchanged; exact observed source counts')
            path=ROOT/case['actual_report_path'];need(sha(path)==case['actual_report_sha256'],'Exact new actual report')
            actual=load(path);task=reader.task(case['actual_task_id'])
            need(actual['status']=='COMPLETE_D032_PAST_FUNDING_EXIT_CONDITIONAL_SCREENING_NOT_LONG_TERM_APR'
                 and actual['binding']['task_id']==task['id'] and actual['period_id']==period
                 and actual['source_bytes_unchanged'] is True and actual['gate_rules']==rules
                 and actual['publication_assumption_certified'] is False and actual['period_calendar']==calendar['months']
                 and actual['period_start']==parent['period_start'] and actual['period_end_exclusive']==parent['period_end_exclusive']
                 and actual['parent_contract_path']==parent_pin['path'] and actual['parent_contract_sha256']==parent_pin['sha256']
                 and actual['parent_source_options_sha256']==parent['source_options_sha256'],
                 'Each new actual complete, immutable, exact selected-parent calendar and conditional')
            need(actual['binding']==load(Path(actual['run_dir'])/'RUN_BINDING.json')
                 and actual['binding']['protocol_sha256']==sha(ROOT/bound['protocol_path'])
                 and actual['binding']['rules']==spec['rules'] and actual['binding']['source_hashes']==expected_hashes
                 and actual['accepted_smoke_sha256']==sha(ROOT/spec['required_smoke_receipt']),
                 'Exact actual source/fee/gate/run/smoke binding')
            unit=actual['unit_interpretation']
            need(unit['raw_rate_unit']=='UNCONFIRMED' and unit['assumed_funding_rate_unit']=='FRACTION'
                 and unit['conditional_fraction_assumption'] is True and unit['full_732_event_unit_certified'] is False
                 and unit['sampled_API_unit_certified'] is False,'Do not certify fraction units')
            fundspec=load(ROOT/parent['funding_contract_path']);probe=load(ROOT/fundspec['unit_probe']['path'])
            unit_task_path=STATE/'task-progress'/('task-'+probe['binding']['task_id']+'.json');unit_task=load(unit_task_path)
            need(unit_task['id']==probe['binding']['task_id'] and unit_task['status']=='failed' and unit_task['exit_code']==1
                 and probe['unit_evidence']['matched_records']==0,'Actual failed1/zero-match unit evidence remains')
            receipt=actual['gate_derivation']
            need(receipt['period']==period and receipt['parent_contract_path']==parent_pin['path']
                 and receipt['parent_contract_sha256']==parent_pin['sha256'] and receipt['event_loop_reordered'] is False
                 and receipt['legacy_globals_mutated'] is False and receipt['original_financial_sources_unchanged'] is True
                 and receipt['base_sha256']==parent['base_account_sha256']
                 and receipt['pair_trim_sha256']==parent['frozen_sources']['scripts/investment/conditional_carry_reduce_adapter.py']
                 and receipt['derived_simulate_AST_sha256']==spec['pre_array_metadata_compile'][period]['simulate_AST_sha256']
                 and receipt['derived_main_AST_sha256']==spec['pre_array_metadata_compile'][period]['main_AST_sha256']
                 and len(receipt['new_gate_changes'])==3 and all(r['matches']==1 for r in receipt['new_gate_changes']),
                 'Frozen exact gate-only derivation over accepted account')
            selected.append((case,parent,actual,task,unit_task_path,unit_task))
        # Deliberately compile both financial spans before any original source or output arrays.
        compiled={period:gate.financial(core,pair,delta,calendar) for period,calendar in CALENDARS.items()}
        new_json(WORK/'RUN_BINDING.json',dict(task_id=os.environ['COIN_TASK_ID'],checker_sha256=sha(__file__),
            gate_delta_sha256=sha(WORK/'gate_delta.py'),ACTUAL_BINDING_sha256=sha(WORK/'ACTUAL_BINDING.json'),
            actuals=bound['actuals'],source_hashes=bound['small_inputs'],exact_command=' '.join(sys.argv),
            sys_prefix=sys.prefix,precompiled_before_arrays=True))
        import pyarrow.parquet as pq
        for case,parent,actual,task,unit_task_path,unit_task in selected:
            period=case['period'];calendar=CALENDARS[period];core.MAX_USDT_ERROR=core.MAX_RATIO_ERROR=core.ZERO
            (WORK/'progress.json').write_text(json.dumps(dict(phase='独立金融核验 '+period,
                completed=report['completed_cases_verified'],total=2,unit='完整账户',pid=os.getpid(),task_id=os.environ['COIN_TASK_ID']),ensure_ascii=False))
            if period=='122D':prices,events,inputs=core.original_inputs(parent,actual,reader);path_proof='ORIGINAL_ACCEPTED_READER_UNCHANGED'
            else:
                view,owner=old90.metadata_source_view(parent);new_reader,path_proof=rb.reader_for_new_owner(reader,owner)
                prices,events,inputs=old90.original_inputs(view,new_reader,core)
            need(len(inputs)==calendar['files'] and len(events)==calendar['events'],'Whole accepted source universe')
            sortkey=lambda r:(r['kind'],r['symbol'],r['month'])
            need(sorted(actual['input_bindings'],key=sortkey)==sorted(inputs,key=sortkey),
                 'Both actual input maps directly equal independently selected accepted sources')
            frames={}
            need(len(actual['output_bindings'])==4 and {r['kind'] for r in actual['output_bindings']}==
                 {'minute_nav','fill_ledger','funding_ledger','daily_nav'},'Four immutable output artifacts')
            for row in actual['output_bindings']:
                path=Path(row['path']);need(path.parent==Path(actual['run_dir']) and path.resolve()==path
                    and not path.is_symlink() and sha(path)==row['sha256'],'Exact physical output SHA/path')
                file=pq.ParquetFile(path);need(file.metadata.num_rows==row['rows'],'Physical output row count');frames[row['kind']]=file
            fills=frames['fill_ledger'].read(use_threads=False).to_pylist()
            fundrows=frames['funding_ledger'].read(use_threads=False).to_pylist();daily=frames['daily_nav'].read(use_threads=False).to_pylist()
            need(len(fundrows)==calendar['events'] and len(daily)==calendar['days'] and
                 [(r['symbol'],r['event_us'],r['raw_rate']) for r in fundrows]==[(r['symbol'],r['event_us'],r['rate']) for r in events],
                 'Every original included/excluded event, rate/order and day')
            checked=dict(completed_minutes_verified=0);verify,financial_proof=compiled[period]
            result=verify(actual,actual['summary'],prices,events,frames,fills,fundrows,daily,checked)
            def plain(value):
                if isinstance(value,core.D):return float(value)
                if isinstance(value,dict):return {k:plain(v) for k,v in value.items()}
                if isinstance(value,list):return [plain(v) for v in value]
                return value
            tracker=result['tracker'];wallet=result['wallet'];obs=result['obs']
            report['cases'].append(dict(period=period,actual_report_path=case['actual_report_path'],actual_report_sha256=sha(ROOT/case['actual_report_path']),
                actual_task=task,unit_failed_task={k:unit_task[k] for k in ('id','status','exit_code','pid','start_ticks')},
                completed_source_files_verified=len(inputs),completed_minutes_verified=checked['completed_minutes_verified'],
                completed_original_funding_events_verified=result['event_cursor'],completed_fills_verified=result['fill_cursor'],
                completed_days_verified=len(daily),completed_months_verified=len(result['months']),
                completed_pair_reductions_verified=len(result['reductions']),owned_events=result['owned'],
                excluded_events=calendar['events']-result['owned'],financial_summary=plain(result['financial']),months=result['months'],
                independent_pair_reductions=plain(result['reductions']),first_risk_signal=plain(result['breaches'][0]) if result['breaches'] else None,
                stop_signal_us=result['stop_signal'],exit_us=result['exit_time'],exit_reason=result['exit_reason'],
                independent_gate_checks=tracker.checks,gate_numeric_witnesses=tracker.numeric,
                rounding_sensitive_trigger_count=sum(r['rounding_sensitive_trigger'] for r in tracker.numeric),
                terminal_bridge_error_USDT=str(result['bridge']-wallet.cash),maximum_cash_error_USDT=float(core.MAX_USDT_ERROR),
                maximum_ratio_error=float(core.MAX_RATIO_ERROR),minute_max_drawdown=float(result['minute_dd']),
                all_observation_max_drawdown=float(obs.max_dd),independent_financial_derivation=financial_proof,
                accepted_reader_path_derivation=path_proof,output_bindings=actual['output_bindings']))
            report['completed_cases_verified']+=1
            for row in inputs:need(sha(row['parquet_path'])==row['parquet_sha256'],'Original source changed during new account audit')
            for row in actual['output_bindings']:need(sha(row['path'])==row['sha256'],'New output changed during audit')
            need(time.monotonic()-began<=600 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=512000000,'Independent wall/RAM budget')
        for path,digest in bound['small_inputs'].items():need(sha(path)==digest,'Small source changed during audit:'+path)
        report.update(status='PASS_D032_TWO_PERIOD_DECIMAL_CONDITIONAL_ACCOUNTING_NOT_NATIVE_OR_LONG_TERM_APR',
            rounding_sensitive_trigger_count=sum(c['rounding_sensitive_trigger_count'] for c in report['cases']),
            economic_adoption_paused_due_to_rounding=any(c['rounding_sensitive_trigger_count'] for c in report['cases']),
            limitations=['Uncertified raw fractions, actual venue funding ownership/mark/publication; named lag is a hypothesis',
                'Same seen122/90 close-proxy source and costs; no native execution/MMR/ADL/financing or long-term APR',
                'Exact primary Float64 fsum predicate retained; independent Decimal sign disagreement is exposed, not corrected with EPS',
                'No saved-control coupon attribution or economic adoption judgment inside this independent wallet audit'])
    except Exception as error:report.update(error_type=type(error).__name__,reason=str(error));raise
    finally:
        report.update(elapsed_seconds=time.monotonic()-began,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        new_json(OUT,report)
    print(json.dumps(dict(status=report['status'],output=str(OUT),sha256=sha(OUT))))
if __name__=='__main__':main()