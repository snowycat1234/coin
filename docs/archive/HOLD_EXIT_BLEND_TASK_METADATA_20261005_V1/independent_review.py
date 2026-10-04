"""Independent Decimal reconciliation of 16 closed JSON accounts; no replay."""
import argparse
import hashlib
import json
import os
from decimal import Decimal, getcontext
from pathlib import Path

getcontext().prec = 60
TOL = Decimal('1e-7')
STEM = 'HOLD_EXIT_BLEND_20261005_V1'
BLEND_ID = 'COIN_HALF_HOLD10_HALF_EXIT10_ACTIVE_EQUAL_1D_USDM_CONFIGURED_POOL_BLEND'
HOLD_ID = 'COIN_PAST30_COVARIANCE_CONSTANT_LONG_USDM_REFERENCE'
EXIT_ID = 'COIN_JESSE_DONCHIAN20_SMA200_EXIT10_1D_USDM_CONFIGURED_POOL_VARIANT'
RISK_TOL = Decimal('1e-10')
SCENARIOS = {(cost, unit) for cost in ('BASE27', 'STRESS43')
             for unit in ('RAW_AS_FRACTION', 'RAW_AS_PERCENT')}


def need(ok, text):
    if not ok:
        raise ValueError(text)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path, digest=None):
    need(digest is None or sha(path) == digest, 'changed bound input: ' + str(path))
    return json.loads(Path(path).read_text(encoding='utf-8'))


def amount(row, key):
    value = Decimal(row.get('decimal_strings', {}).get(key, str(row[key])))
    need(value.is_finite(), 'nonfinite ' + key)
    return value


def closed(report, state):
    identity = report.get('task_id') or report['binding']['task_id']
    task = read(state / 'task-progress' / ('task-' + identity + '.json'))
    need(task['status'] == 'completed' and task['exit_code'] == 0 and task['ended_at'],
         'task is not closed0: ' + identity)
    return identity


def reconcile(case, policy, names, budget):
    s = case['summary']
    need(case['symbols'] == names and case['pool'] == 'TWO_ASSET' and s['symbols'] == names,
         'strict ordered role identity: ' + policy)
    need(s['completed_minutes'] == s['required_minutes'] == 436320 and
         s['daily_metrics']['days'] == 303 and s['daily_metrics']['initial_nav'] == 10000,
         'complete full-capital 303day calendar')
    need(s['terminal_cash_realized'] is True and s['terminal_not_forced_free_fill'] is True and
         not s['pending_orders_at_stop'] and s['account_status'] == 'ACTIVE', 'closed real cash account')
    need(s['unit_certified'] is False and s['publication_certified'] is False, 'conditional units remain unknown')
    inputs = {}
    for name in ('trades.json', 'funding.json', 'target_meta.json'):
        entry = case['artifacts'][name]
        need(sha(entry['path']) == entry['sha256'], 'changed actual account artifact')
        inputs[name] = dict(path=entry['path'], sha256=entry['sha256'])
    meta = read(inputs['target_meta.json']['path'])
    rules = meta['rules']
    need(meta['symbols'] == names and rules['annual_volatility_target'] == budget,
         'actual target meta role budget')
    need(rules['absolute_target_per_asset'] == .3 and rules['gross_target_cap'] == .6 and
         rules['past_covariance_daily_returns'] == 30, 'caps and past30 unchanged')
    need(len(meta['risk']) == 303 and all(r['covariance_symbol_order'] == names and
         r['covariance_observations'] == 30 and r['past_only'] is True for r in meta['risk']),
         'actual covariance order/past availability')
    if policy == 'BLEND_TWO':
        need(meta['strategy_id'] == BLEND_ID and meta['allocation'] == 'HALF_HOLD_HALF_ACTIVE_EQUAL_EXIT10',
             'fixed actual blend identity')
        required = dict(hold_weight=.5, donchian_weight=.5, hold_strategy_id=HOLD_ID,
            donchian_strategy_id=EXIT_ID, hold_allocation='EQUAL', donchian_allocation='ACTIVE_EQUAL',
            exit_period=10, reentry_period=20,
            blend_stage='AFTER_COMPONENT_RISK_SCALING_NO_EXTRA_RESCALE', separate_component_capital=False,
            blend_weights_fitted=False, component_NAVs_averaged=False,
            component_signal_states_independent_of_executed_blended_position=True)
        need(all(rules.get(k) == value for k, value in required.items()), 'actual fixed component rules')
        need(meta['components']['HOLD']['strategy_id'] == HOLD_ID and
             meta['components']['EXIT10']['strategy_id'] == EXIT_ID, 'actual component identity')
        for risk in meta['risk']:
            h, d = risk['component_HOLD_target'], risk['component_EXIT10_target']
            need(len(h) == len(d) == len(names), 'ordered component target lists')
            combined = [Decimal('.5') * Decimal(str(x)) + Decimal('.5') * Decimal(str(y))
                        for x, y in zip(h, d)]
            need(all(Decimal(0) <= x <= Decimal('.3') + RISK_TOL for x in combined), 'convex asset cap')
            gross = sum(combined)
            need(gross <= Decimal('.6') + RISK_TOL and
                 abs(gross - Decimal(str(risk['gross_target_weight']))) <= RISK_TOL,
                 'target meta fixed halves/gross cap')
    elif policy.startswith('EXIT10'):
        need(rules['exit_period'] == 10 and rules.get('reentry_period', 20) == 20 and
             rules['allocation'] == 'ACTIVE_EQUAL', 'fixed10/20 active timing recipe')
    else:
        need(rules['direction_is_constant'] is True and
             rules['raw_allocation'] == 'EQUAL_SHARE_OF_0.6_GROSS_TO_CONFIGURED_ELIGIBLE_MEMBERS',
             'same constant HOLD equal recipe')
    sums = dict.fromkeys(('realized', 'fees', 'execution', 'funding', 'unrealized'), Decimal(0))
    for row in read(inputs['trades.json']['path']):
        need(row['symbol'] in names, 'unknown traded asset')
        sums['realized'] += amount(row, 'realized_PnL')
        sums['fees'] += amount(row, 'fee_USDT_mid')
        sums['execution'] += amount(row, 'execution_cost')
    for row in read(inputs['funding.json']['path']):
        need(row['symbol'] in names, 'unknown funded asset')
        sums['funding'] += amount(row, 'signed_funding_USDT')
    for symbol in names:
        position = s['positions'][symbol]
        quantity, entry = amount(position, 'quantity'), amount(position, 'entry_price')
        mark = Decimal(str(s['terminal_mark_prices'][symbol]))
        sums['unrealized'] += quantity * (mark - entry)
        need(quantity == 0 and amount(position, 'isolated_balance') == 0, 'every asset liquidated')
    need(amount(s, 'isolated_balance') == amount(s, 'unpaid_liability') == 0, 'no terminal margin/liability')
    sums['gross'] = sums['realized'] + sums['unrealized'] + sums['execution']
    sums['net'] = sums['gross'] - sums['fees'] - sums['execution'] + sums['funding']
    for own, field in (('gross', 'gross_PnL_same_quantities'), ('net', 'net_PnL'),
                       ('fees', 'fees_USDT'), ('execution', 'execution_cost_USDT'),
                       ('funding', 'funding_USDT'), ('unrealized', 'unrealized_PnL')):
        need(abs(sums[own] - amount(s, field)) <= TOL, 'independent JSON bridge: ' + field)
    need(abs(sums['net'] - (amount(s, 'NAV') - Decimal(10000))) <= TOL, 'NAV full-capital bridge')
    return dict(policy=policy, case_id=case['id'], cost=case['cost_id'], funding_unit=case['unit_id'],
        symbols=names, annual_budget=budget, days=303, full_capital=10000, terminal_cash=True,
        **sums, actual_vol=s['daily_metrics']['annual_volatility'], minute_MDD=s['minute_max_drawdown'],
        turnover=s['normalized_total_turnover'], input_hashes=inputs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('/mnt/d/codex/coin'))
    parser.add_argument('--state', type=Path, default=Path('/home/xflops/coin-state'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    need(args.output.resolve().is_relative_to(args.state.resolve()) and not args.output.exists(),
         'new STATE-only output required')
    root, state = args.root, args.state
    pp = root / 'protocols' / (STEM + '.json')
    p = read(pp)
    ap = root / 'reports/fast_research' / (STEM + '.json')
    fp = root / 'reports/fast_research' / (STEM + '_FINANCIAL.json')
    dp = root / 'reports/fast_research' / (STEM + '_DIAGNOSTIC.json')
    a, f, diag = read(ap), read(fp), read(dp)
    need(a['binding']['protocol_sha256'] == sha(pp) == diag['protocol_sha256'] and
         sha(ap) == diag['actual_report_sha256'] and sha(fp) == diag['financial_report_sha256'],
         'current actual/financial/diagnostic bindings')
    reports = {'BLEND_TWO': a}
    roles = {'BLEND_TWO_market': closed(a, state), 'BLEND_TWO_financial': closed(f, state),
             'diagnostic': closed(diag, state)}
    need(a['complete_calendar_cases'] == f['financial_case_calls'] == 4 and
         f['status'].startswith('PASS_CONFIGURED_N_'), 'current four actual/financial cases')
    legacy_missing_rules = []
    need(p['strategy'] == BLEND_ID and p['strategy_rules']['hold_weight'] == .5 and
         p['strategy_rules']['donchian_weight'] == .5, 'protocol fixed half/half recipe')
    need(f['independent_blend_targets_verified'] is True, 'actual full blend reference verified')
    need(set(p['saved_comparisons']) == {'HOLD10_TWO', 'HOLD8_TWO', 'EXIT10_TWO'}, 'all three saved controls')
    for policy, binding in p['saved_comparisons'].items():
        old = read(root / binding['actual_path'], binding['actual_sha256'])
        oldf = read(root / binding['financial_path'], binding['financial_sha256'])
        oldp = read(root / binding['protocol_path'], binding['protocol_sha256'])
        need(old['complete_calendar_cases'] == oldf['financial_case_calls'] == 4 and
             oldf['status'].startswith('PASS_CONFIGURED_N_'), 'all saved cases passed')
        roles[policy + '_market'], roles[policy + '_financial'] = closed(old, state), closed(oldf, state)
        for key in ('start', 'end_exclusive', 'period_days', 'data_manifest', 'source_acceptances',
                    'pool_receipt', 'initial_capital_USDT', 'account_path', 'data_role'):
            need(p[key] == oldp[key], 'changed common comparison factor ' + key)
        if 'strategy_rules' not in oldp:
            legacy_missing_rules.append(policy)
        reports[policy] = old
    for name, digest in p['source_hashes'].items():
        need(sha(root / name) == digest, 'current frozen source mismatch')
    rows, mapped = [], {}
    for policy, report in reports.items():
        need(len(report['cases']) == 4 and {(c['cost_id'], c['unit_id']) for c in report['cases']} == SCENARIOS,
             'complete unique four conditions')
        for case in report['cases']:
            row = reconcile(case, policy, ['BTCUSDT', 'ETHUSDT'],
                            .08 if policy == 'HOLD8_TWO' else .10)
            d = next(r for r in diag['rows'] if r['policy'] == policy and r['cost'] == row['cost'] and
                     r['funding_unit'] == row['funding_unit'])
            for key in ('net', 'gross', 'fees', 'execution', 'funding'):
                need(abs(row[key] - Decimal(str(d[key + '_USDT']))) <= TOL, 'diagnostic money mismatch')
            rows.append(row)
            mapped[policy, row['cost'], row['funding_unit']] = row
    need(len(diag['paired_cases']) == 12, 'all twelve reported contrasts')
    paired, domination = [], []
    for cost, unit in sorted(SCENARIOS):
        new = mapped['BLEND_TWO', cost, unit]
        for policy in ('HOLD10_TWO', 'HOLD8_TWO', 'EXIT10_TWO'):
            old = mapped[policy, cost, unit]
            delta = {key: new[key] - old[key] for key in ('net', 'gross', 'fees', 'execution', 'funding')}
            need(abs(delta['net'] - (delta['gross'] - delta['fees'] - delta['execution'] + delta['funding']))
                 <= TOL, 'independent paired money bridge')
            d = next(r for r in diag['paired_cases'] if r['reference'] == policy and r['cost'] == cost
                     and r['funding_unit'] == unit)
            for key in delta:
                need(abs(delta[key] - Decimal(str(d['differences'][key + '_USDT']))) <= TOL,
                     'reported paired difference mismatch')
            need(d['actual_risk_matched'] is False and d['same_pool'] is True and
                 d['same_component_risk_budget'] == (policy != 'HOLD8_TWO'), 'honest blend attribution')
            risk_delta = dict(actual_daily_annualized_volatility=Decimal(str(new['actual_vol'])) - Decimal(str(old['actual_vol'])),
                              minute_MDD=Decimal(str(new['minute_MDD'])) - Decimal(str(old['minute_MDD'])),
                              turnover_full_capital=Decimal(str(new['turnover'])) - Decimal(str(old['turnover'])))
            for key, value in risk_delta.items():
                need(abs(value - Decimal(str(d['differences'][key]))) <= RISK_TOL, 'saved risk difference')
            dominates = (old['net'] >= new['net'] - TOL and
                Decimal(str(old['actual_vol'])) <= Decimal(str(new['actual_vol'])) + RISK_TOL and
                Decimal(str(old['minute_MDD'])) <= Decimal(str(new['minute_MDD'])) + RISK_TOL and
                (delta['net'] < -TOL or risk_delta['actual_daily_annualized_volatility'] > RISK_TOL or
                 risk_delta['minute_MDD'] > RISK_TOL))
            need(d['reference_dominates_in_net_vol_and_MDD'] == dominates, 'predeclared domination arithmetic')
            domination.append(dominates)
            paired.append(dict(reference=policy, cost=cost, funding_unit=unit, differences=delta,
                risk_differences=risk_delta, reference_dominates_in_net_vol_and_MDD=dominates))
        average = (mapped['HOLD10_TWO', cost, unit]['net'] + mapped['EXIT10_TWO', cost, unit]['net']) / 2
        difference = new['net'] - average
        diagnostic_new = next(r for r in diag['rows'] if r['policy'] == 'BLEND_TWO' and
                              r['cost'] == cost and r['funding_unit'] == unit)
        need(abs(difference - Decimal(str(diagnostic_new['net_minus_arithmetic_average_of_component_account_net_USDT'])))
             <= TOL, 'actual blend vs arithmetic independent-wallet net')
        new['net_minus_independent_component_net_average'] = difference
    need(diag['all_scenarios_undominated_by_existing_same_pool_controls'] == (not any(domination)),
         'same predeclared retain criterion, not an added gate')
    need(diag['actual_targets_equal_fixed_half_saved_component_targets'] is True and
         diag['independent_market_evidence'] is False and diag['posthoc_scaling'] is False,
         'diagnostic limited causal claims')
    result = dict(status='PASS_16_CLOSED_JSON_ACCOUNTS_12_INDEPENDENT_DECIMAL_PAIRS_NOT_MARKET_REPLAY',
        task_id=os.environ.get('COIN_TASK_ID'), helper_sha256=sha(__file__), protocol_sha256=sha(pp),
        diagnostic_sha256=sha(dp), closed_roles=roles, rows=rows, paired_differences=paired,
        legacy_protocols_without_strategy_rules=legacy_missing_rules,
        legacy_budget_scope='Actual hash-bound target_meta rules checked per role; no invented legacy protocol field',
        independent_parquet_signal_or_risk_recalculation=False,
        signal_covariance_evidence='Exact half component targets, past covariance and future causal boundary verified by closed full financial/root diagnostic and synthetic test; helper checks JSON meta only, not parquet',
        all_scenarios_undominated_by_existing_same_pool_controls=not any(domination),
        criterion_scope='Exactly protocol net/actual-vol/minute-MDD dominance with declared tolerances; no additional adoption gate',
        old_source_resolution='Accepted Git bytes resolved by closed root diagnostic; helper checks saved protocol/report identities only',
        market_replays=0, model_fits=0, candidate='NONE', investment='CASH', long_term_APR='NOT_EVALUABLE')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False, default=str)
        stream.write('\n')
    print(json.dumps(dict(status=result['status'], output=str(args.output), sha256=sha(args.output))))


if __name__ == '__main__':
    main()
