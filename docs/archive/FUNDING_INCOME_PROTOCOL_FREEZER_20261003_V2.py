"""Freeze one explicit certified-sample or unverified-assumption diagnostic.

Metadata/code hashes only. No funding Parquet, price arrays, source QA, tests,
statistical coupon calculation or registry append is performed by this helper.
"""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
OUT = ROOT / 'protocols/FUNDING_INCOME_DIAGNOSTIC_122D_20261003_V1.json'
ACCEPTANCE = 'reports/fast_research/V8_FUNDING_MARK_INDEX_SOURCE_ACCEPTANCE_20261002_V1.json'
ACCEPTANCE_SHA = '318622721ed9733d84ae66082f750e8b7d4ed960d7812c9e899c94b3cb5188aa'
RUNNER = 'scripts/investment/funding_income_diagnostic.py'
RUNNER_SHA = '78c776bfbc3405876a93422b2b3a6e5798d041673c31f2307c6bf7ce49d1f492'
TEST = 'tests/test_funding_income_diagnostic.py'
TEST_SHA = 'ec827b6757c3ed665d38c2ac8c92718ccd67077d7cf1d99f1494e57489ad9559'
SELF_ARCHIVE = 'docs/archive/FUNDING_INCOME_PROTOCOL_FREEZER_20261003_V2.py'
PROBE_STATUS = 'PASS_OFFICIAL_FUNDING_DOCUMENTARY_SEMANTICS_AND_SAMPLED_API_PARITY'
ASSUMPTION_BASIS = 'EXPLICIT_UNVERIFIED_FRACTION_ASSUMPTION_AFTER_HTTP451'
FAILED_PROBE_STATUS = 'FAIL_OFFICIAL_FUNDING_API_PARITY_UNCONFIRMED'
FAILED_PROBE_SHA = '54febc06b7815e521715c8d70c3e930929a489c7e2a84d1ddae9507a03e4da4d'


def need(ok, message):
    if not bool(ok):
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def small(path, expected=None):
    path = Path(path)
    path = path if path.is_absolute() else ROOT / path
    need(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(ROOT.resolve())
        and path.stat().st_size < 2_000_000, 'Explicit ordinary project metadata required')
    need(expected is None or sha(path) == expected, 'Frozen metadata changed: ' + str(path))
    return path, json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--unit-probe', type=Path, required=True)
    parser.add_argument('--unit-probe-sha256', required=True)
    parser.add_argument('--unit-probe-host-session', type=int, required=True)
    parser.add_argument('--unit-basis', choices=['SAMPLED_API_PARITY',ASSUMPTION_BASIS], required=True)
    args = parser.parse_args()
    need(not OUT.exists(), 'Never overwrite a frozen protocol')
    need(args.unit_probe_host_session > 0, 'Real root-observed probe completion session required')
    probe_path, probe = small(args.unit_probe,args.unit_probe_sha256)
    evidence = probe['unit_evidence']
    conditional = args.unit_basis == ASSUMPTION_BASIS
    if conditional:
        need(args.unit_probe_sha256 == FAILED_PROBE_SHA and sha(probe_path) == FAILED_PROBE_SHA
            and probe['status'] == FAILED_PROBE_STATUS and probe['funding_rate_unit'] == 'UNCONFIRMED'
            and probe['bp_multiplier'] is None and evidence['matched_records'] == 0
            and evidence['qualification'] == 'NOT_YET_ESTABLISHED' and evidence['sample_parity_status'] == 'UNCONFIRMED'
            and probe['comparisons'] == [] and probe['actual_operation_exit_code'] == 1
            and len(probe['requests']) == 1 and probe['requests'][0]['http_status'] == 451
            and probe['requests'][0]['url'] == 'https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&startTime=1754006400000&endTime=1754064001000&limit=3',
            'Explicit conditional mode requires the exact actual HTTP451 fail, never a silent fallback')
    else:
        need(probe['status'] == PROBE_STATUS and probe['funding_rate_unit'] == 'FRACTION'
            and probe['bp_multiplier'] == 10000, 'No sampled parity protocol before actual unit PASS')
        need(evidence['qualification'] == 'DOCUMENTARY_CONVENTION_AND_SIX_SAMPLED_ARCHIVE_API_PARITY'
            and evidence['matched_records'] == 6, 'The limited six-record bridge must be explicit')
    identity = probe['binding']['task_id']
    need(len(identity) == 32 and all(char in '0123456789abcdef' for char in identity), 'Actual probe task ID')
    task_path = STATE / 'task-progress' / ('task-' + identity + '.json')
    task = json.loads(task_path.read_text())
    probe_exit = 1 if conditional else 0
    need(task['id'] == identity and task['status'] == ('failed' if conditional else 'completed')
         and task['exit_code'] == probe_exit, 'Actual unit probe exit must remain truthful')
    acceptance_path, acceptance = small(ACCEPTANCE,ACCEPTANCE_SHA)
    need(acceptance['status'] == 'PASS_NEW_OFFICIAL_INPUT_SOURCE_FORMAT_ONLY_INDEPENDENT_QA', 'Existing source acceptance required')
    qa_path, qa = small(acceptance['independent_qa_path'],acceptance['independent_qa_sha256'])
    producer_path,_ = small(acceptance['producer_path'],acceptance['producer_sha256'])
    old_protocol_path,_ = small(acceptance['protocol_path'],acceptance['protocol_sha256'])
    need(qa['status'] == 'PASS_OFFICIAL_CARRY_INPUT_FORMAT_ONLY_INDEPENDENT_QA', 'Existing QA PASS, no rerun')
    records = [row for row in acceptance['sources'] if row['kind'] == 'fundingRate']
    symbols, months = ['BTCUSDT','ETHUSDT'],['2025-08','2025-09','2025-10','2025-11']
    need(len(records) == 8 and {(row['symbol'],row['month']) for row in records} ==
        {(symbol,month) for symbol in symbols for month in months} and sum(row['rows'] for row in records) == 732,
        'Bind all accepted funding metadata; no row/month selection')
    profile_path,profile = small('protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json')
    need(profile['public_base_rates']['ordinary_crypto_spot']['taker_bps_per_side'] == 10 and
        profile['public_base_rates']['ordinary_perpetual_and_futures']['taker_bps_per_side'] == 5.5,
        'Existing ordinary Bybit cost profile, no rate substitution')
    clean_path,clean = small('reports/fast_research/V8_CLEAN_ENVIRONMENT_SMOKE_20261002_V2.json')
    need(clean['status'] == 'PASS_CLEAN_COMPLETE_CPU_LOCK_AND_SYNTHETIC_ARTIFACT_REPRODUCTION'
        and Path(sys.prefix).resolve() == Path(clean['sys_prefix']).resolve(), 'Accepted clean WSL environment required')
    need(sha(ROOT/RUNNER) == RUNNER_SHA and sha(ROOT/TEST) == TEST_SHA, 'Prepared new code/test bytes changed')
    need(sha(ROOT/'docs/archive/FUNDING_INCOME_DIAGNOSTIC_PRE_CONDITIONAL_20261003_V1.py') == '8fa34487110c310218d93dcf8259b85fcfcf9436cb9d2fc65ee578226836a410'
        and sha(ROOT/'docs/archive/FUNDING_INCOME_TEST_PRE_CONDITIONAL_20261003_V1.py') == 'ad1f5116ecd699d50fefa266d40d727f27461681d2820df08419f4b4836daca8',
        'Original prepared, unexecuted code/test archives must remain exact')
    need(sha(ROOT/SELF_ARCHIVE) == sha(__file__), 'Exact pure helper archive required')
    names = [RUNNER,TEST,SELF_ARCHIVE,
        'docs/archive/FUNDING_INCOME_DIAGNOSTIC_PRE_CONDITIONAL_20261003_V1.py',
        'docs/archive/FUNDING_INCOME_TEST_PRE_CONDITIONAL_20261003_V1.py',
        'scripts/research_v7/oracle_flow_ceiling.py','scripts/research_v8/registry.py',
        'src/quant/resources.py','src/quant/disk.py','src/quant/paths.py',
        'environments/v8/pyproject.toml','environments/v8/uv.lock',
        'protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json',
        'reports/fast_research/V8_CLEAN_ENVIRONMENT_SMOKE_20261002_V2.json',ACCEPTANCE,
        str(qa_path.relative_to(ROOT)),str(producer_path.relative_to(ROOT)),str(old_protocol_path.relative_to(ROOT)),
        str(probe_path.relative_to(ROOT))]
    names += list(probe['binding']['source_hashes']) + [probe['binding']['protocol_path']]
    hashes = {}
    for name in names:
        path = ROOT/name
        need(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(ROOT.resolve())
            and path.stat().st_size < 2_000_000, 'Small frozen source only')
        hashes[name] = sha(path)
    for name,digest in probe['binding']['source_hashes'].items():
        need(hashes[name] == digest, 'Preserved probe source binding differs')
    # The protocol and future smoke/result receipts are intentionally not in
    # frozen_sources: main adds the same protocol digest in both operating modes.
    smoke = 'reports/fast_research/FUNDING_INCOME_DIAGNOSTIC_TINY_20261003_V1.json'
    actual = 'reports/fast_research/FUNDING_INCOME_DIAGNOSTIC_122D_ACTUAL_20261003_V1.json'
    need(str(OUT.relative_to(ROOT)) not in hashes and smoke not in hashes and actual not in hashes,
         'No self-reference or future receipt identity')
    spec = dict(contract_id='FUNDING_INCOME_DIAGNOSTIC_V1',
        created_before_new_income_read_utc=datetime.now(UTC).isoformat(),
        git_commit_at_freeze=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        classification='CONDITIONAL_RAW_FRACTION_MATH_UNCERTIFIED_UNIT_NOT_CAPITAL_RETURN' if conditional else 'REALIZED_RATE_COUPON_AND_HYPOTHETICAL_COST_HURDLE_DIAGNOSTIC_NOT_CAPITAL_RETURN',
        research_question='Under the explicit unverified fraction assumption, does the fixed fullperiod raw rate sum leave hypothetical two-leg cost headroom?' if conditional else 'Does fixed fullperiod signed funding coupon leave headroom over ordinary two-leg open/close costs?',
        period_start='2025-08-01',period_end_exclusive='2025-12-01',symbols=symbols,source_calendar=months,
        source_acceptance_path=ACCEPTANCE,source_acceptance_sha256=ACCEPTANCE_SHA,
        funding_rate_unit='UNCONFIRMED' if conditional else 'FRACTION',
        assumed_funding_rate_unit='FRACTION' if conditional else None,bp_multiplier=10000,
        conditional_fraction_assumption=conditional,
        research_decision='D024_EXPLICIT_CONDITIONAL_RAW_FRACTION_MATH_AFTER_HTTP451' if conditional else 'D023_SAMPLED_UNIT_PARITY',
        unit_investment_gate_pass=False,
        raw_signed_rate_sum_also_reported_without_unit_certification=True,
        unit_probe=dict(path=str(probe_path.relative_to(ROOT)),sha256=sha(probe_path),basis=args.unit_basis,
            required_status=FAILED_PROBE_STATUS if conditional else PROBE_STATUS,limited_evidence=evidence,
            actual_task_path=str(task_path),actual_task_sha256=sha(task_path),actual_task_id=identity,
            actual_host_session=args.unit_probe_host_session,actual_exit=probe_exit),
        full_event_unit_certification=False,publication_or_exact_account_charge_certification=False,
        reported_ms_are_available_signal=False,
        fee_reference_profile_path=str(profile_path.relative_to(ROOT)),fee_reference_profile_sha256=sha(profile_path),
        costs=dict(spot_fee_bps_per_side=10,perp_taker_fee_bps_per_side=5.5,
            assumed_slippage_bps_per_side=4,assumed_each_leg_roundtrip_spread_bps=[2,4,8]),
        fee_data_mapping='BINANCE_FUNDING_HISTORY_WITH_BYBIT_CURRENT_NONVIP_FEE_HYPOTHESES_NOT_OWN_VENUE_PROFIT',
        expected_cost_hurdles_bp=[31,51,55,63],fee_hurdle_units='PER_ONE_MATCHED_SINGLE_LEG_NOMINAL_TWO_LEG_COMPLETE_ROUNDTRIP',
        cost_occurrence='ONE_OPEN_AND_CLOSE_FOR_FULL122D;_NO_MONTHLY_REPEATED_FEES',
        perp_spread_slippage_verified=False,
        signed_coupon_definition='SUM_RAW_FRACTION_RATE*10000_PER_FIXED_EVENT_NOMINAL_FOR_HYPOTHETICAL_SHORT_PERP',
        negative_definition='STRICT_RATE_LESS_THAN_ZERO;_ZERO_AND_POSITIVE_RESET_RUN',
        coupon_drawdown_definition='MAX_RUNNING_COUPON_PEAK_MINUS_PREFIX_COUPON_IN_BP_INCLUDING_INITIAL_ZERO_NOT_NAV_MDD',
        monthly_definition='ALL_FOUR_UTC_MONTHS_DESCRIPTIVE_SUMS_NO_POSITIVE_SELECTION_OR_REPEATED_FEES',
        per_symbol_only=True,combined_BTC_ETH_account_return=False,
        expected_input_files=8,expected_funding_events=732,expected_per_symbol_events=366,
        accepted_input_metadata=[{key:row[key] for key in ('symbol','month','receipt_path','receipt_sha256',
            'parquet_path','parquet_sha256','rows')} for row in records],
        frozen_sources=hashes,required_smoke_receipt=smoke,planned_actual_output=actual,
        maximum_new_owned_bytes=10_000_000,maximum_wall_seconds=600,
        environment=dict(sys_prefix=clean['sys_prefix'],lock_sha256=hashes['environments/v8/uv.lock'],
            shared_ram_limit_bytes=5_000_000_000,swap=0,GPU=0),
        metadata_freezer_path=SELF_ARCHIVE,metadata_freezer_sha256=sha(__file__),
        market_arrays_read_by_freezer=False,source_QA_or_tests_repeated_by_freezer=False,
        models_fit=0,orders_sent=0,locked_consumed=False,GPU=0,
        capital_net_APR='NOT_EVALUABLE',candidate_status='NO_QUALIFIED_CANDIDATE',
        unknowns=['Price/quantity/fee-asset changes and actual funding cash','Spot/perp execution and basis PnL',
            'Capital/collateral denominator and margin/liquidation/ADL','Financing/borrow/transfer/dust',
            'Venue/account/history-specific fees and executable spread/slippage'])
    for name,digest in hashes.items():
        need(sha(ROOT/name) == digest,'Frozen source changed before publication')
    with OUT.open('x') as writer:
        json.dump(spec,writer,indent=2,ensure_ascii=False,allow_nan=False);writer.write('\n')
    print(json.dumps(dict(protocol=str(OUT),sha256=sha(OUT),frozen_sources=len(hashes),
        source_metadata_files=8,actual_funding_events_read=0,tests_run=0,registry_appends=0)))


if __name__ == '__main__':
    main()
