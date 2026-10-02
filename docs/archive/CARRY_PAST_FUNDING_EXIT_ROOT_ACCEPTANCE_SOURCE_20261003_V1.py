"""D032 metadata-only acceptance: saved JSON/tasks/code and new output byte SHA.

Never opens Parquet rows, price sources, old NAV, or replays account/test/QA math.
Economic adoption may fail while this narrowly scoped engineering module passes.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, re, subprocess, sys
from datetime import UTC, datetime
from pathlib import Path
from quant import resources
ROOT = Path('/mnt/d/codex/coin'); STATE = Path('/home/xflops/coin-state')
MASTER = 'protocols/CARRY_PAST_FUNDING_EXIT_D032_20261003_V1.json'
TINY = 'reports/fast_research/CARRY_PAST_FUNDING_EXIT_TINY_20261003_V1.json'
AUDIT = 'reports/fast_research/CARRY_PAST_FUNDING_EXIT_TWO_PERIOD_DECIMAL_AUDIT_20261003_V1.json'
COMPARISON = 'reports/fast_research/CARRY_PAST_FUNDING_EXIT_ECONOMIC_COMPARISON_20261003_V1.json'
ARCHIVE = 'docs/archive/CARRY_PAST_FUNDING_EXIT_ROOT_ACCEPTANCE_SOURCE_20261003_V1.py'
OUT = ROOT/'reports/fast_research/CARRY_PAST_FUNDING_EXIT_ROOT_ACCEPTANCE_20261003_V1.json'
PERIODS = {'122D':(175680,122,732,32), '90D':(129600,90,540,24)}
ACTUALS = {p:'reports/fast_research/CARRY_PAST_FUNDING_EXIT_'+p+'_ACTUAL_20261003_V1.json' for p in PERIODS}
ACTUAL_STATUS = 'COMPLETE_D032_PAST_FUNDING_EXIT_CONDITIONAL_SCREENING_NOT_LONG_TERM_APR'
AUDIT_STATUS = 'PASS_D032_TWO_PERIOD_DECIMAL_CONDITIONAL_ACCOUNTING_NOT_NATIVE_OR_LONG_TERM_APR'
COMPARE_STATUS = 'COMPLETE_D032_SAVED_SUMMARY_CONDITIONAL_ATTRIBUTION_NOT_NATIVE_OR_LONG_TERM_APR'
MONEY = ('initial_capital_USDT','final_nav_USDT','net_PnL_USDT','gross_cost_addback_PnL_USDT',
         'fees_USDT','assumed_spread_USDT','assumed_slippage_USDT','signed_conditional_funding_USDT')

def check(ok, reason):
    if not ok: raise ValueError(reason)

def small(path, expected=None, parse=True):
    original = Path(path); path = original.resolve()
    check((path.is_relative_to(ROOT) or path.is_relative_to(STATE)) and not original.is_symlink()
          and path.is_file() and path.stat().st_size <= 2_000_000
          and path.suffix in {'.json','.py','.sh','.ps1','.lock','.toml','.md'}, 'Ordinary small metadata/code only')
    data = path.read_bytes(); digest = hashlib.sha256(data).hexdigest()
    check(expected is None or digest == expected, 'Frozen small proof changed: '+str(path))
    return (json.loads(data) if parse else None), digest

def closed(report):
    identity = report['binding']['task_id']; check(re.fullmatch('[0-9a-f]{32}', identity) is not None, 'Exact task id')
    path = STATE/'task-progress'/('task-'+identity+'.json'); task, digest = small(path)
    check(task['id'] == identity and task['status'] == 'completed' and task['exit_code'] == 0, 'Real closed exit0 required')
    return dict(path=str(path), sha256=digest, task=task)

def timestamp(value):
    check(type(value) in (int,float) and math.isfinite(value), 'Actual finite Unix task time required')
    return datetime.fromtimestamp(value, UTC)

def near(a, b, tolerance):
    check(math.isfinite(a) and math.isfinite(b) and abs(a-b) <= tolerance, 'Saved audit/producer numeric disagreement')

def bounded(record):
    check(record['ram_limit_bytes'] <= 5_000_000_000 and record['swap_bytes'] == 0
          and not record['gpu_used'], 'Recorded shared5GB/swap0/noGPU')

def output_hash(row, work):
    original = Path(row['path']); path = original.resolve()
    check(not original.is_symlink() and path.is_relative_to(work) and path.is_file() and path.suffix == '.parquet'
          and path.stat().st_size == row['bytes'] <= 25_000_000, 'New output byte metadata only')
    with path.open('rb') as stream: digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    check(digest == row['sha256'], 'New output byte SHA changed')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('tiny-host','period122-host','period90-host','audit-host','comparison-host'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--output', type=Path, default=OUT); args = parser.parse_args()
    check(os.environ.get('COIN_TASK_ID') and Path(sys.prefix).resolve() == STATE/'v8-clean-env-20261002-v2', 'Existing clean bounded/progress runtime')
    own_resources = resources.status(); bounded(own_resources); out = args.output.resolve()
    check(out.is_relative_to(ROOT/'reports/fast_research') and not out.exists(), 'Exclusive root receipt')
    _, own_sha = small(__file__, parse=False); small(ROOT/ARCHIVE, own_sha, parse=False)
    spec, protocol_sha = small(ROOT/MASTER); tiny, tiny_sha = small(ROOT/TINY)
    audit, audit_sha = small(ROOT/AUDIT); comparison, comparison_sha = small(ROOT/COMPARISON)
    check(spec['contract_id'] == 'CARRY_PAST_FUNDING_EXIT_D032_V1' and len(spec['frozen_sources']) == 78
          and spec['actual_accounts'] == 2 and spec['configurations'] == 1 and not spec['hyperparameter_search'], 'Fixed master78-source two-period single gate')
    hashes = dict(spec['frozen_sources']); hashes[MASTER] = protocol_sha
    for name, digest in hashes.items():
        check(not Path(name).is_absolute() and (ROOT/name).resolve().is_relative_to(ROOT), 'ROOT-relative source map')
        small(ROOT/name, digest, parse=False)
    check(tiny['status'] == 'PASS_D032_PAST_FUNDING_EXIT_SYNTHETIC_NOT_MARKET_OR_AVAILABILITY_PROOF'
          and tiny['test_exit_code'] == 0 and tiny['junit_counts'] == dict(tests=1,errors=0,failures=0,skipped=0)
          and tiny['binding']['protocol_sha256'] == protocol_sha and tiny['binding']['source_hashes'] == hashes
          and not tiny['price_arrays_read'] and not tiny['funding_arrays_read'], 'Exactly one new synthetic case, same frozen source')
    check(audit['status'] == AUDIT_STATUS and audit['completed_cases_verified'] == 2
          and audit['verified_source_hashes'] == hashes, 'Actual independent two-period Decimal proof')
    _, checker_sha = small(audit['independent_source'], audit['binding']['checker_sha256'], parse=False)
    check(checker_sha == audit['independent_source_sha256'], 'Actual independent checker byte binding')
    check(comparison['status'] == COMPARE_STATUS and comparison['gate_rules'] == spec['gate_rules']
          and comparison['adoption_criteria'] == spec['adoption_criteria'], 'Actual comparison same pre-results scientific rules')
    compare_binding, compare_binding_sha = small(comparison['binding']['comparison_binding_path'], comparison['binding']['comparison_binding_sha256'])
    small(comparison['helper_path'], comparison['helper_sha256'], parse=False)
    check(compare_binding['master_protocol_sha256'] == protocol_sha and compare_binding['audit_sha256'] == audit_sha
          and compare_binding['helper_sha256'] == comparison['helper_sha256'] == comparison['binding']['source_sha256'], 'Actual comparison exact master/audit/helper')
    check(type(comparison['economic_adoption_criteria_passed']) is bool and comparison['economic_adoption_scope'] == 'CONDITIONAL_RESEARCH_ONLY_NOT_INVESTMENT_QUALIFICATION'
          and comparison['research_action'] == ('CONTINUE_FIXED_GATE_RESEARCH' if comparison['economic_adoption_criteria_passed'] else 'PAUSE_FIXED_GATE_RECIPE_PRESERVE_CAPABILITY'), 'Save actual economic action, no fabricated adoption')
    audit_cases = {c['period']:c for c in audit['cases']}; compare_cases = {c['period']:c for c in comparison['cases']}
    check(len(audit['cases']) == len(comparison['cases']) == 2 and set(audit_cases) == set(compare_cases) == set(PERIODS), 'Exactly the two whole periods')
    tasks = {'tiny':closed(tiny),'audit':closed(audit),'comparison':closed(comparison)}
    proofs = {MASTER:protocol_sha,TINY:tiny_sha,AUDIT:audit_sha,COMPARISON:comparison_sha}; actuals = {}; outputs = {}
    for period, name in ACTUALS.items():
        report, digest = small(ROOT/name); case = audit_cases[period]; cc = compare_cases[period]
        summary = report['summary']; meta = spec['period_metadata'][period]; minutes, days, events, files = PERIODS[period]
        check(report['status'] == ACTUAL_STATUS and report['period_id'] == period and report['gate_rules'] == spec['gate_rules']
              and report['binding']['rules'] == spec['rules'] and report['binding']['protocol_sha256'] == protocol_sha
              and report['binding']['source_hashes'] == hashes and report['accepted_smoke_sha256'] == tiny_sha, 'New actual exact frozen master/smoke/rules')
        check(report['parent_contract_path'] == spec['period_contracts'][period]['path'] and report['parent_contract_sha256'] == spec['period_contracts'][period]['sha256']
              and report['parent_source_options_sha256'] == meta['source_options_sha256'] and report['period_calendar'] == meta['source_calendar']
              and report['period_start'] == meta['period_start'] and report['period_end_exclusive'] == meta['period_end_exclusive'], 'Only selected accepted period and endpoints')
        check(case['actual_report_sha256'] == cc['new_actual_sha256'] == digest and Path(case['actual_report_path']).resolve() == Path(cc['new_actual_path']).resolve() == (ROOT/name).resolve(), 'Audit/comparison actual identity')
        for key, expected in [('completed_source_files_verified',files),('completed_minutes_verified',minutes),('completed_original_funding_events_verified',events),('completed_days_verified',days),('completed_months_verified',len(meta['source_calendar']))]:
            check(case[key] == expected, 'Independent complete count '+key)
        check(case['maximum_cash_error_USDT'] <= 1e-7 and case['maximum_ratio_error'] <= 1e-10, 'Existing fixed independent accounting tolerances')
        near(float(case['terminal_bridge_error_USDT']), 0., 1e-7)
        check(summary['rows'] == minutes and summary['all_source_events'] == events and summary['daily_metrics']['days'] == days
              and summary['owned_funding_events'] == case['owned_events'] and summary['excluded_funding_events'] == case['excluded_events']
              and summary['owned_funding_events']+summary['excluded_funding_events'] == events and summary['fills'] == case['completed_fills_verified'], 'Full original calendar/events and actual fills')
        check([m['month'] for m in summary['months']] == [m['month'] for m in case['months']] == meta['source_calendar'], 'All full-period months retained')
        for key in MONEY: near(summary[key], case['financial_summary'][key], 1e-7)
        for key in ('minute_max_drawdown','all_observation_max_drawdown'): near(summary[key], case[key], 1e-10)
        for key, value in cc['new_summary'].items(): near(summary[key], value, 1e-10 if key in ('all_observation_max_drawdown','minute_max_drawdown','maximum_total_gross','turnover') else 1e-7)
        check(summary['exit_reason'] == case['exit_reason'] and summary['exit_us'] == case['exit_us'] and summary['stop_signal_us'] == case['stop_signal_us'], 'Actual/audit exit metadata')
        check(report['capital_net_APR'] == summary['capital_net_APR'] == 'NOT_EVALUABLE' and report['candidate_status'] == summary['candidate_status'] == 'NO_QUALIFIED_CANDIDATE'
              and not any(report[k] for k in ('unseen_qualification','funding_unit_certified','native_Bybit_prices_or_filters','real_liquidation_MMR_or_ADL_modeled','publication_assumption_certified','locked_consumed','old_QA_or_green_tests_repeated'))
              and report['models_fit'] == report['orders_sent'] == report['GPU'] == 0 and report['source_bytes_unchanged'], 'No qualification/unit/availability/native/longAPR promotion')
        bounded(report['resources']); check(report['disk']['status'] == 'OK' and report['disk']['total_bytes']+report['disk']['reserved_bytes'] <= 40_000_000_000, 'Recorded actual disk scan and shared runtime')
        check(len(report['input_bindings']) == len({(r['kind'],r['symbol'],r['month']) for r in report['input_bindings']}) == files, 'Unique selected input metadata, no source reread')
        work = Path(report['run_dir']).resolve(); rows = {r['kind']:r for r in report['output_bindings']}
        check(work.is_relative_to(STATE) and len(report['output_bindings']) == 4 and set(rows) == {'minute_nav','daily_nav','funding_ledger','fill_ledger'}
              and report['output_bindings'] == case['output_bindings'], 'Four exact independently bound new outputs')
        for kind, count in [('minute_nav',minutes),('daily_nav',days),('funding_ledger',events),('fill_ledger',summary['fills'])]:
            check(rows[kind]['rows'] == count, 'New output saved row metadata'); output_hash(rows[kind], work)
        tasks[period] = closed(report); check(case['actual_task']['id'] == tasks[period]['task']['id'], 'Same independently closed actual task')
        check(timestamp(tasks[period]['task']['started_at']) >= timestamp(tasks['tiny']['task']['ended_at']), 'New actual after closed synthetic0')
        actuals[period] = report; outputs[period] = report['output_bindings']; proofs[name] = digest
    check(len({r['task']['id'] for r in tasks.values()}) == 5 and timestamp(tasks['audit']['task']['started_at']) >= max(timestamp(tasks[p]['task']['ended_at']) for p in PERIODS)
          and timestamp(tasks['comparison']['task']['started_at']) >= timestamp(tasks['audit']['task']['ended_at']), 'All five real independent tasks closed in order')
    check(sum(r['owned_bytes'] for r in actuals.values()) <= spec['combined_output_budget_bytes'] == 50_000_000, 'Combined new STATE budget')
    bounded(tiny['resources']); bounded(comparison['resources'])
    check(comparison['capital_net_APR'] == audit['capital_net_APR'] == 'NOT_EVALUABLE' and comparison['candidate_status'] == audit['candidate_status'] == 'NO_QUALIFIED_CANDIDATE'
          and not comparison['funding_unit_certified'] and not comparison['signal_availability_certified'] and not audit['funding_unit_certified']
          and not audit['historical_signal_availability_certified'], 'Metadata acceptance cannot certify units/native investment')
    check(comparison['numerical_adoption_paused'] or not audit['economic_adoption_paused_due_to_rounding'], 'Any independent numeric pause propagated')
    value = dict(status='PASS_ROOT_D032_TWO_PERIOD_CONDITIONAL_ACCOUNT_AND_COMPARISON_NOT_NATIVE_OR_LONG_TERM_APR', created_utc=datetime.now(UTC).isoformat(),
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(), binding=dict(task_id=os.environ['COIN_TASK_ID'],helper_sha256=own_sha),
        root_task_id=os.environ['COIN_TASK_ID'],root_helper=dict(path=str(Path(__file__).resolve()),sha256=own_sha,archive=ARCHIVE), source_hashes=hashes, small_reports=proofs,
        comparison_binding=dict(path=comparison['binding']['comparison_binding_path'],sha256=compare_binding_sha), actual_task_copies=tasks,
        actual_host_results=dict(tiny=args.tiny_host,period122=args.period122_host,period90=args.period90_host,audit=args.audit_host,comparison=args.comparison_host),
        independent_checker=dict(path=audit['independent_source'],sha256=checker_sha), financial_summaries={p:r['summary'] for p,r in actuals.items()},
        independent_cases=audit['cases'],comparison_cases=comparison['cases'],economic_action=comparison['research_action'],economic_adoption_criteria_passed=comparison['economic_adoption_criteria_passed'],
        economic_adoption_scope=comparison['economic_adoption_scope'],numerical_adoption_paused=comparison['numerical_adoption_paused'],engineering_scope_pass_not_economic_adoption=True,
        output_bindings=outputs,output_bytes_SHA_reverified=True,output_rows_or_CRC_replayed=False,source_QA_or_account_math_or_old_tests_replayed=False,
        same_caps_not_equal_realized_risk=True,periods_not_spliced=True,data_retained_in_STATE_not_Git=True,funding_unit_certified=False,signal_availability_certified=False,
        native_account_certified=False,capital_net_APR='NOT_EVALUABLE',candidate_status='NO_QUALIFIED_CANDIDATE',unseen_qualification=False,
        recorded_actual_resources={p:dict(resources=r['resources'],disk=r['disk'],elapsed_seconds=r['elapsed_seconds'],peak_RSS_bytes=r['peak_RSS_bytes']) for p,r in actuals.items()},
        independent_audit_elapsed_seconds=audit['elapsed_seconds'],independent_audit_peak_RSS_bytes=audit['peak_RSS_bytes'],root_resources=own_resources,models_fit=0,orders_sent=0,GPU=0,locked_consumed=False)
    with out.open('x',encoding='utf-8') as stream: json.dump(value,stream,indent=2,ensure_ascii=False,allow_nan=False); stream.write('\n')
    print(json.dumps(dict(status=value['status'],output=str(out),sha256=small(out)[1])))

if __name__ == '__main__': main()
