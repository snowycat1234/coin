"""Prepared metadata-only root acceptance; no account/source/test replay.

Only completed JSON, closed task records, small frozen source hashes and the four
new output Parquet byte hashes per policy are read. Output rows are never opened.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys
from datetime import UTC, datetime
from pathlib import Path
from quant import resources
ROOT = Path('/mnt/d/codex/coin'); STATE = Path('/home/xflops/coin-state')
PROTOCOL = 'protocols/CONDITIONAL_CARRY_90D_FIXED_PERIOD_20261003_V1.json'
TINY = 'reports/fast_research/CARRY_90D_PERIOD_TINY_20261003_V1.json'
ACTUALS = {p:'reports/fast_research/CARRY_90D_'+p+'_ACTUAL_20261003_V1.json' for p in ('ALL_FLAT', 'PAIR_TRIM')}
AUDIT = 'reports/fast_research/CARRY_90D_TWO_POLICY_DECIMAL_INDEPENDENT_AUDIT_20261003_V3.json'
OUT = ROOT/'reports/fast_research/CARRY_90D_TWO_POLICY_ROOT_ACCEPTANCE_20261003_V1.json'
MONTHS = ['2025-12', '2026-01', '2026-02']; VIEW_SHA = 'd167109731945e06aea2134f1eb495ab5647f68b70fc288ab2d23a03c7a1ee29'

def check(ok, text):
    if not ok: raise ValueError(text)

def small(path, expected=None, parse=True):
    original = Path(path); value = original.resolve()
    check((value.is_relative_to(ROOT) or value.is_relative_to(STATE)) and not original.is_symlink()
          and value.is_file() and value.stat().st_size <= 2_000_000
          and value.suffix in {'.json', '.py', '.sh', '.ps1', '.lock', '.toml'}, 'Only ordinary small metadata/code')
    data = value.read_bytes(); digest = hashlib.sha256(data).hexdigest()
    check(expected is None or digest == expected, 'Changed small proof: '+str(value))
    return (json.loads(data) if parse else None), digest

def closed(report):
    identity = report['binding']['task_id']
    check(re.fullmatch('[0-9a-f]{32}', identity) is not None, 'Exact task id')
    path = STATE/'task-progress'/('task-'+identity+'.json'); value, digest = small(path)
    check(value['id'] == identity and value['status'] == 'completed' and value['exit_code'] == 0, 'Actual closed exit0 required')
    return dict(path=str(path), sha256=digest, task=value)

def output_hash(row, work):
    original = Path(row['path']); path = original.resolve()
    check(not original.is_symlink() and path.is_relative_to(work) and path.is_file()
          and path.suffix == '.parquet' and path.stat().st_size == row['bytes'] <= 50_000_000, 'New output byte metadata only')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1_048_576), b''): digest.update(block)
    check(digest.hexdigest() == row['sha256'], 'Saved new output byte hash changed')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('tiny-host', 'flat-host', 'trim-host', 'audit-host'): parser.add_argument('--'+name, required=True)
    parser.add_argument('--audit-source', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=OUT); args = parser.parse_args()
    check(os.environ.get('COIN_TASK_ID') and Path(sys.prefix).resolve() == STATE/'v8-clean-env-20261002-v2', 'Existing clean bounded/progress runtime')
    own_resources = resources.status(); out = args.output.resolve()
    check(out.is_relative_to(ROOT/'reports/fast_research') and not out.exists(), 'Exclusive root metadata receipt')
    spec, protocol_sha = small(ROOT/PROTOCOL); tiny, tiny_sha = small(ROOT/TINY); audit, audit_sha = small(ROOT/AUDIT)
    check(spec['contract_id'] == 'CONDITIONAL_CARRY_90D_FIXED_PERIOD_V1' and spec['period_start'] == '2025-12-01'
          and spec['period_end_exclusive'] == '2026-03-01' and spec['source_calendar'] == MONTHS
          and spec['expected_price_files'] == 18 and spec['expected_funding_files'] == 6
          and spec['expected_minutes_per_asset'] == 129600 and spec['expected_funding_events'] == 540, 'Fixed accepted90d input counts')
    view, _ = small(ROOT/spec['source_view_path'], VIEW_SHA)
    check(spec['source_view_sha256'] == VIEW_SHA and view['funding_event_total'] == 540
          and view['funding_counts_by_symbol'] == spec['expected_funding_events_by_symbol']
          and view['source_calendar'] == MONTHS and not view['economic_gate_passed'] and not view['funding_unit_certified'], 'Source acceptance is format-only')
    hashes = dict(spec['frozen_sources']); hashes[PROTOCOL] = protocol_sha
    check(tiny['binding']['source_hashes'] == hashes and tiny['binding']['protocol_sha256'] == protocol_sha, 'Same frozen newperiod tiny binding')
    for name, digest in hashes.items():
        check(not Path(name).is_absolute() and (ROOT/name).resolve().is_relative_to(ROOT), 'ROOT-relative source map only')
        small(ROOT/name, digest, parse=False)
    check(tiny['status'] == 'PASS_CARRY_90D_PERIOD_SOURCE_ENDPOINT_SYNTHETIC_ONLY' and tiny['test_exit_code'] == 0
          and tiny['junit_counts'] == dict(tests=1, errors=0, failures=0, skipped=0)
          and not tiny['price_arrays_read'] and not tiny['funding_arrays_read'], 'One new source/period/endpoint case, no old financial replay')
    check(audit['status'] == 'PASS_CARRY_90D_TWO_POLICY_DECIMAL_CONDITIONAL_ACCOUNTING_NOT_NATIVE_OR_LONG_TERM_APR'
          and audit['completed_cases_verified'] == 2 and audit['verified_source_hashes'] == hashes, 'Independent twoaccount Decimal proof')
    _, checker_sha = small(args.audit_source, audit['binding']['checker_sha256'], parse=False)
    check(checker_sha == audit['independent_source_sha256'], 'Executed independent checker bytes')
    audit_cases = {c['policy']:c for c in audit['cases']}
    check(len(audit['cases']) == 2 and set(audit_cases) == set(ACTUALS), 'Exactly two fixed policies')
    actuals = {}; tasks = {'tiny':closed(tiny), 'audit':closed(audit)}; proofs = {}; outputs = {}; input_map = None
    for policy, name in ACTUALS.items():
        report, digest = small(ROOT/name); case = audit_cases[policy]; summary = report['summary']
        check(report['status'] == 'COMPLETE_CARRY_90D_DEVELOPMENT_EXTRAPOLATION_CONDITIONAL_NOT_LONG_TERM_APR'
              and report['policy'] == policy and report['source_view_sha256'] == VIEW_SHA
              and report['binding']['protocol_sha256'] == protocol_sha and report['binding']['source_hashes'] == hashes
              and report['binding']['rules'] == spec['policies'][policy] and report['accepted_smoke_sha256'] == tiny_sha, 'Exact commonprotocol/source and fixed policy')
        check(case['actual_report_sha256'] == digest and Path(case['actual_report_path']).resolve() == (ROOT/name).resolve()
              and case['completed_source_files_verified'] == 24 and case['completed_minutes_verified'] == 129600
              and case['completed_original_funding_events_verified'] == 540 and case['completed_days_verified'] == 90
              and case['completed_months_verified'] == 3 and case['maximum_cash_error_USDT'] <= 1e-7
              and case['maximum_ratio_error'] <= 1e-10, 'Actual newaccount independently verified within fixed tolerances')
        check(summary['rows'] == 129600 and summary['all_source_events'] == 540
              and summary['owned_funding_events'] == case['owned_events'] and summary['excluded_funding_events'] == case['excluded_events']
              and summary['owned_funding_events'] + summary['excluded_funding_events'] == 540
              and summary['fills'] == case['completed_fills_verified']
              and [m['month'] for m in summary['months']] == MONTHS, 'Actual unknown fills/ownership and continuous3months now resolved')
        check(summary['capital_net_APR'] == report['capital_net_APR'] == 'NOT_EVALUABLE'
              and summary['candidate_status'] == report['candidate_status'] == 'NO_QUALIFIED_CANDIDATE'
              and not report['unseen_qualification'] and not report['funding_unit_certified']
              and not report['native_Bybit_prices_or_filters'] and not report['real_liquidation_MMR_or_ADL_modeled']
              and not report['locked_consumed'] and not report['old_QA_or_green_tests_repeated']
              and report['source_bytes_unchanged'] and report['models_fit'] == report['orders_sent'] == report['GPU'] == 0, 'No native/unit/APR/investment promotion')
        check(report['resources']['ram_limit_bytes'] <= 5_000_000_000 and report['resources']['swap_bytes'] == 0
              and not report['resources']['gpu_used'] and report['disk']['status'] == 'OK', 'Recorded shared5GB/swap0/GPU0')
        inputs = {(r['kind'],r['symbol'],r['month']):(r['parquet_path'],r['parquet_sha256'],r['rows']) for r in report['input_bindings']}
        expected = {(r['kind'],r['symbol'],r['month']):(r['parquet_path'],r['parquet_sha256'],r['rows']) for r in view['sources']}
        check(len(report['input_bindings']) == len(inputs) == 24 and inputs == expected
              and (input_map is None or inputs == input_map), 'Same24 already accepted input bindings; no source bytes re-read')
        input_map = inputs; work = Path(report['run_dir']).resolve()
        check(work.is_relative_to(STATE) and len(report['output_bindings']) == 4, 'Four new output files in isolated STATE')
        output_map = {r['kind']:r for r in report['output_bindings']}
        check(set(output_map) == {'minute_nav','daily_nav','funding_ledger','fill_ledger'}
              and output_map['minute_nav']['rows'] == 129600 and output_map['daily_nav']['rows'] == 90
              and output_map['funding_ledger']['rows'] == 540 and output_map['fill_ledger']['rows'] == summary['fills'], 'New output metadata counts')
        for row in report['output_bindings']: output_hash(row, work)
        tasks[policy] = closed(report)
        check(tasks[policy]['task']['started_at'] >= tasks['tiny']['task']['ended_at'], 'New actual after the onecase accepted')
        actuals[policy] = report; outputs[policy] = report['output_bindings']; proofs[name] = digest
    check(len({v['task']['id'] for v in tasks.values()}) == 4
          and tasks['audit']['task']['started_at'] >= max(tasks[p]['task']['ended_at'] for p in ACTUALS), 'Independent closed task after both actual exits')
    check(sum(v['owned_bytes'] for v in actuals.values()) <= spec['combined_output_budget_bytes'] == 50_000_000, 'Combined new output budget')
    flat, trim = (actuals[p]['summary'] for p in ('ALL_FLAT','PAIR_TRIM'))
    check(abs(audit['paired_net_PnL_delta_USDT']-(trim['net_PnL_USDT']-flat['net_PnL_USDT'])) <= 1e-7, 'Paired savedsummary delta only, no market recomputation')
    metrics = ('net_PnL_USDT','gross_cost_addback_PnL_USDT','fees_USDT','assumed_spread_USDT','assumed_slippage_USDT',
               'signed_conditional_funding_USDT','turnover','fills','owned_funding_events','minute_max_drawdown','all_observation_max_drawdown','maximum_total_gross')
    value = dict(status='PASS_ROOT_CARRY_90D_TWO_POLICY_CONDITIONAL_ACCOUNT_MATH_NOT_NATIVE_OR_LONG_TERM_APR',
        created_utc=datetime.now(UTC).isoformat(), git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        root_task_id=os.environ['COIN_TASK_ID'], root_helper=dict(path=str(Path(__file__).resolve()),sha256=small(__file__,parse=False)[1]),
        source_hashes=hashes, small_reports={TINY:tiny_sha,AUDIT:audit_sha,**proofs}, actual_task_copies=tasks,
        actual_host_results=dict(tiny=args.tiny_host,ALL_FLAT=args.flat_host,PAIR_TRIM=args.trim_host,audit=args.audit_host),
        independent_checker=dict(path=str(args.audit_source.resolve()),sha256=checker_sha), source_view_sha256=VIEW_SHA,
        financial_summaries={p:r['summary'] for p,r in actuals.items()}, independent_cases=audit['cases'],
        paired_summary_deltas={k:trim[k]-flat[k] for k in metrics}, monthly_paired_deltas=audit['monthly_paired_deltas'],
        common_C0_cost_caps_only=True, same_caps_not_equal_realized_risk=True, periods_122d_and90d_not_spliced=True,
        output_bindings=outputs, output_bytes_SHA_reverified=True, output_rows_or_CRC_replayed=False,
        source_data_QA_or_account_math_or_old_tests_replayed=False, data_retained_in_STATE_not_Git=True,
        funding_unit_certified=False, native_account_certified=False, capital_net_APR='NOT_EVALUABLE', candidate_status='NO_QUALIFIED_CANDIDATE',
        unseen_qualification=False, root_resources=own_resources, models_fit=0, orders_sent=0,GPU=0,locked_consumed=False)
    with out.open('x',encoding='utf-8') as stream: json.dump(value,stream,indent=2,ensure_ascii=False,allow_nan=False); stream.write('\n')
    print(json.dumps(dict(status=value['status'],output=str(out),sha256=small(out)[1])))

if __name__ == '__main__': main()
