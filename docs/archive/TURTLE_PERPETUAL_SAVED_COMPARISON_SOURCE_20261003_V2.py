"""UNRUN D047 four-condition saved-summary comparison; no payload replay.

Turtle vs accepted SMA LONG_SHORT, HOLD and CASH on the same seen303 days.
Whole-period differences are unavailable for a halted/new prefix. Different
strategy state, holdings and realized risk prevent a pure short causal claim.
"""
import argparse
from datetime import UTC, datetime
import hashlib
import importlib.util
import os
from pathlib import Path
import shlex
import sys

from quant import resources

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
GUARD = 'docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA = '278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
ARCHIVE = 'docs/archive/TURTLE_PERPETUAL_SAVED_COMPARISON_SOURCE_20261003_V2.py'
PROTOCOL = 'protocols/TURTLE_PERPETUAL_RESEARCH_20261003_V1.json'
ACTUAL = 'reports/fast_research/TURTLE_PERPETUAL_RESEARCH_ACTUAL_20261003_V2.json'
AUDIT = 'reports/fast_research/TURTLE_PERPETUAL_FINANCIAL_INDEPENDENT_20261003_V1.json'
OUT = 'reports/fast_research/TURTLE_PERPETUAL_SAVED_COMPARISON_20261003_V2.json'
STATUS = 'COMPLETE_D047_FOUR_CONDITION_SAVED_TURTLE_SMA_HOLD_CASH_COMPARISON_NOT_NATIVE_OR_LONG_TERM_APR'
ACTUAL_STATUS = 'COMPLETE_D047_FIXED303D_TURTLE4H_CONDITIONAL_ACCOUNTS_NOT_NATIVE_OR_LONG_TERM_APR'
AUDIT_STATUS = 'PASS_D047_TURTLE_RECORDED_PERPETUAL_ACCOUNTING_NOT_COMPLETE_STRATEGY_NATIVE_OR_LONG_TERM_APR'
LS_ROOT = 'reports/fast_research/PERPETUAL_RISK_REDUCTION_ROOT_ACCEPTANCE_20261003_V1.json'
LS_ROOT_SHA = 'feb63187abafc1ae3b8a52c5a9404cd74aff6354abf0404812cc2242e276858c'
OLD_ROOT = 'reports/fast_research/PERPETUAL_303_RESEARCH_ROOT_ACCEPTANCE_20261003_V1.json'
OLD_ROOT_SHA = '841a525d41162bbcbaedb14b0be0c3696bcf3356cfdb76542a864662797c4f58'
OLD_ACTUAL = 'reports/fast_research/PERPETUAL_303_RESEARCH_ACTUAL_20261003_V1.json'
LS_ROOT_STATUS = 'PASS_ROOT_D046_FOUR_CORRECTNESS_CONTROLS_AND_TWENTY_SAVED_SELECTORS_NOT_NATIVE_OR_LONG_TERM_APR'
OLD_ROOT_STATUS = 'PASS_ROOT_D045_TWENTY_FIXED303D_CONDITIONAL_ACCOUNTS_NOT_NATIVE_OR_LONG_TERM_APR'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def view(case):
    s = case['summary']
    complete = s['completion'] == 'COMPLETE_CONDITIONAL_ACCOUNT' and s['completed_minutes'] == s['required_minutes'] == 436320
    if 'stop_us' not in s and not (case['mode'] == 'CASH' and complete and s.get('known_zero_cash_ownership') is True):
        raise ValueError('Missing stop_us is allowed only for the accepted complete constant CASH control')
    stop_us = s['stop_us'] if 'stop_us' in s else None
    return dict(id=case['id'], strategy_id=case['strategy_id'], mode=case['mode'],
        complete_calendar=complete, completion=s['completion'], summary_scope='FULL_SEEN303D' if complete else 'ACTUAL_PREFIX_NOT_303D_RETURN',
        completed_minutes=s['completed_minutes'], required_minutes=s['required_minutes'], stop_us=stop_us,
        configured_nominal_roundtrip_bps=s['configured_nominal_roundtrip_bps'], cost_scenario=s['cost_scenario'],
        unit_scenario=s['unit_scenario'], capital_USDT=10000, NAV=s['NAV'], net_PnL=s['net_PnL'],
        gross_PnL_same_quantities=s['gross_PnL_same_quantities'], funding_USDT=s['funding_USDT'],
        fees_USDT=s['fees_USDT'], execution_cost_USDT=s['execution_cost_USDT'],
        spread_cost_USDT=s['spread_cost_USDT'], slippage_cost_USDT=s['slippage_cost_USDT'],
        trade_legs=s['trade_legs'], gross_fill_turnover_USDT=s['gross_fill_turnover_USDT'],
        normalized_total_turnover=s.get('normalized_total_turnover'),
        net_return_on_full_initial_capital_percent=s.get('net_return_on_full_initial_capital_percent'),
        long_short_marked_contribution=s['long_short_marked_contribution'],
        daily_metrics_descriptive=s['daily_metrics'], minute_max_drawdown=s['minute_max_drawdown'],
        all_observation_max_drawdown=s['all_observation_max_drawdown'],
        realized_exposure=s.get('realized_exposure'), daily_net_gain_concentration=s.get('daily_net_gain_concentration'),
        metrics_NOT_EVALUABLE_reason=s.get('metrics_NOT_EVALUABLE_reason'),
        months=s['months'], terminal_marked_notional=s['terminal_marked_notional'],
        terminal_signed_marked_notional=s['terminal_signed_marked_notional'], terminal_cash_realized=s['terminal_cash_realized'],
        positions=s['positions'], isolated_balance=s['isolated_balance'], free_cash=s['free_cash'],
        minimum_actual_free_cash_all_observations_USDT=s['minimum_actual_free_cash_all_observations_USDT'],
        actual_caps_instantaneously_guaranteed=s['actual_caps_instantaneously_guaranteed'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, default=STATE / 'd047-turtle-saved-comparison-20261003-v2')
    args = parser.parse_args()
    assert os.environ.get('COIN_TASK_ID') and sys.prefix == str(STATE / 'v8-clean-env-20261002-v2')
    assert sha(ROOT / GUARD) == GUARD_SHA and sha(__file__) == sha(ROOT / ARCHIVE)
    module_spec = importlib.util.spec_from_file_location('d047_saved_comparison_guards', ROOT / GUARD)
    g = importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(g)
    before = resources.status(); g.bounded(before)
    hashes = {ARCHIVE: sha(__file__), GUARD: GUARD_SHA}; tasks = {}

    def small(name, digest=None):
        value, actual_sha = g.small(g.project(name), digest)
        hashes[name] = actual_sha
        return value

    spec = small(PROTOCOL); actual = small(ACTUAL); audit = small(AUDIT)
    g.check(spec['contract_id'] == 'D047_FIXED303D_TURTLE4H_CALLBACK_CONDITIONAL_V1'
        and spec['period_ids'] == ['303D'] and actual['status'] == ACTUAL_STATUS
        and actual['binding']['protocol_sha256'] == hashes[PROTOCOL]
        and actual['binding']['source_hashes'] == spec['frozen_sources'], 'Exact current Turtle recipe/period')
    g.check(audit['status'] == AUDIT_STATUS and audit['actual_report_sha256'] == hashes[ACTUAL]
        and audit['protocol_sha256'] == hashes[PROTOCOL] and audit['completed_cases_verified'] == audit['financial_case_calls'] == 4
        and audit['binding']['actual_reports'] == {str(ROOT / ACTUAL): hashes[ACTUAL]}, 'Current real four-case financial proof')
    for role, report in (('MARKET', actual), ('FINANCE', audit)):
        tasks[role] = g.closed(report['binding']['task_id'])
    g.check(tasks['FINANCE']['task']['started_at'] >= tasks['MARKET']['task']['ended_at'], 'Financial check started after market completed')
    root_ls = small(LS_ROOT, LS_ROOT_SHA); root_old = small(OLD_ROOT, OLD_ROOT_SHA)
    g.check(root_ls['status'] == LS_ROOT_STATUS and root_old['status'] == OLD_ROOT_STATUS, 'Only accepted original control receipts')
    tasks['D046_ROOT'] = g.closed(root_ls['binding']['task_id']); tasks['D045_ROOT'] = g.closed(root_old['binding']['task_id'])
    ref = root_ls['new_LS_source']; old_ls = small(ref['path'], ref['sha256'])
    g.check(old_ls['status'] == ref['required_status'] and old_ls['binding']['task_id'] == ref['task_id'], 'Original corrected complete LS, not old failed prefixes')
    old = small(OLD_ACTUAL, root_old['verified_actual_reports'][OLD_ACTUAL])
    g.check(old['status'] == 'COMPLETE_D045_FIXED303D_PERPETUAL_SCREENING_NOT_NATIVE_OR_LONG_TERM_APR', 'Original HOLD/CASH saved producer')
    tasks['D046_MARKET'] = g.closed(old_ls['binding']['task_id']); tasks['D045_MARKET'] = g.closed(old['binding']['task_id'])
    w = actual['input_windows'][0]
    original = [r for r in w['input_proofs'] if r.get('role') != 'OFFICIAL_4H_WARMUP_ONLY']
    for controls in (old_ls, old):
        past = controls['input_windows'][0]
        g.check(w['id'] == past['id'] == '303D' and original == past['input_proofs']
            and all(w[k] == past[k] for k in ('score_start_us', 'score_end_exclusive_us', 'original_funding_events')),
            'Exact common score-source bytes/calendar/funding metadata; new signal warmup is separate')
    g.check(actual['completed_cases'] == actual['required_cases'] == len(actual['cases']) == 4, 'All four new fixed selectors retained')
    proofs = {r['id']: r for r in audit['cases']}; groups = []
    g.check(len(proofs) == 4 and set(proofs) == {r['id'] for r in actual['cases']}, 'Exactly the audited four selectors')

    def one(report, selector, cost, unit):
        rows = [r for r in report['cases'] if r.get('selector_mode', r['mode']) == selector
                and r['period'] == '303D' and r['cost_id'] == cost and r['unit_id'] == unit]
        g.check(len(rows) == 1, 'Unique saved matching selector: ' + selector)
        return rows[0]

    for cost in ('BASE27', 'STRESS43'):
        for unit in ('RAW_AS_FRACTION', 'RAW_AS_PERCENT'):
            new = one(actual, 'LONG_SHORT', cost, unit)
            proof = proofs[new['id']]
            g.check(proof['complete_calendar_verified'] == view(new)['complete_calendar']
                and proof['completed_minutes_verified'] == new['summary']['completed_minutes'], 'Exact new full/prefix flag and recorded count')
            for field in ('NAV', 'net_PnL', 'gross_PnL_same_quantities', 'fees_USDT', 'execution_cost_USDT', 'funding_USDT'):
                g.near(new['summary'][field], proof['summary'][field], 1e-7)
            choices = dict(TURTLE_LONG_SHORT=view(new), SMA_LONG_SHORT=view(one(old_ls, 'LONG_SHORT', cost, unit)),
                           HOLD_LONG_ONLY=view(one(old, 'HOLD_LONG_ONLY', cost, unit)), CASH=view(one(old, 'CASH', cost, unit)))
            for v in choices.values():
                g.check(v['cost_scenario'] == new['summary']['cost_scenario'] and v['unit_scenario'] == new['summary']['unit_scenario'], 'Matched original cost/unit, no selected interpretation')
                if v['complete_calendar']:
                    g.check(v['daily_metrics_descriptive']['days'] == 303 and v['daily_metrics_descriptive']['initial_nav'] == 10000., 'Original full capital and all303 days')
            current = choices['TURTLE_LONG_SHORT']; deltas = {}
            for label in ('SMA_LONG_SHORT', 'HOLD_LONG_ONLY', 'CASH'):
                prior = choices[label]; full = current['complete_calendar'] and prior['complete_calendar']
                deltas[label] = dict(scope='FULL303D_SAVED_RESULT_DIFFERENCES_UNMATCHED_REALIZED_RISK' if full else 'NOT_EVALUABLE_PREFIX_VS_FULL_PERIOD',
                    net_PnL_delta_USDT=current['net_PnL'] - prior['net_PnL'] if full else None,
                    gross_PnL_delta_USDT=current['gross_PnL_same_quantities'] - prior['gross_PnL_same_quantities'] if full else None,
                    funding_delta_USDT=current['funding_USDT'] - prior['funding_USDT'] if full else None,
                    fee_delta_USDT=current['fees_USDT'] - prior['fees_USDT'] if full else None,
                    execution_cost_delta_USDT=current['execution_cost_USDT'] - prior['execution_cost_USDT'] if full else None,
                    actual_annual_volatility_delta=current['daily_metrics_descriptive']['annual_volatility'] - prior['daily_metrics_descriptive']['annual_volatility'] if full else None,
                    minute_MDD_delta=current['minute_max_drawdown'] - prior['minute_max_drawdown'] if full else None,
                    all_observation_MDD_delta=current['all_observation_max_drawdown'] - prior['all_observation_max_drawdown'] if full else None)
            groups.append(dict(period='303D', cost_id=cost, unit_id=unit, selectors=choices, paired_deltas=deltas))
    g.check(args.run_dir.parent == STATE and not args.run_dir.exists() and not (ROOT / OUT).exists(), 'Exclusive new saved-summary operation')
    args.run_dir.mkdir()
    binding = dict(task_id=os.environ['COIN_TASK_ID'], source_path=str(Path(__file__).resolve()),
        source_sha256=sha(__file__), source_hashes=hashes, exact_command=shlex.join([sys.executable, *sys.argv]),
        actual_report_sha256=hashes[ACTUAL], financial_report_sha256=hashes[AUDIT])
    g.write(args.run_dir / 'RUN_BINDING.json', binding)
    g.write(ROOT / OUT, dict(status=STATUS, created_utc=datetime.now(UTC).isoformat(), binding=binding,
        run_dir=str(args.run_dir), run_binding_sha256=sha(args.run_dir / 'RUN_BINDING.json'),
        closed_prerequisite_tasks=tasks, source_hashes=hashes, groups=groups, cost_unit_groups=4,
        newly_compared_accounts=4, saved_control_references=12,
        new_full_calendar_accounts=sum(r['selectors']['TURTLE_LONG_SHORT']['complete_calendar'] for r in groups),
        new_prefix_accounts=sum(not r['selectors']['TURTLE_LONG_SHORT']['complete_calendar'] for r in groups),
        prefix_full_period_comparisons='NOT_EVALUABLE', old_arrays_or_accounts_or_QA_replayed=False,
        financial_metrics_recalculated=False, copied_saved_months_not_month_selection=True,
        market_or_Parquet_IO=False, no_registry_event_requested_main_and_finance_cover_this_saved_comparison=True,
        candidate='NO_QUALIFIED_CANDIDATE', long_term_APR='NOT_EVALUABLE', funding_rate_unit='UNCONFIRMED',
        unit_certified=False, native_market_certified=False,
        product_quantity_and_minimum_notional_filter_scope='FROZEN_PROXY_NOT_NATIVE_BYBIT_FILTER_CERTIFICATION',
        complete_strategy_state_independently_rebuilt=False,
        seen_development_screening=True, realized_risk_equalized=False, pure_short_causal_effect_identified=False,
        NAV_or_months_stitched=False, models_fit=0, orders_sent=0, GPU=0, locked_consumed=False,
        economic_action='SAVED_SEEN_SCREENING_ONLY_NO_INVESTMENT_ADOPTION', resources_before=before,
        resources_after=resources.status(), own_completion='LIVE_CALLER_ROOT_MUST_VERIFY_ACTUAL_CLOSED0'))
    print(OUT + ' SHA256 ' + sha(ROOT / OUT))


if __name__ == '__main__':
    main()
