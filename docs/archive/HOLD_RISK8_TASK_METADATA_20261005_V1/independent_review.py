"""Read closed D071 JSON evidence; independent Decimal bridges, no replay/imports."""
import argparse
import hashlib
import json
import os
from decimal import Decimal, getcontext
from pathlib import Path

getcontext().prec = 60
TOL = Decimal('1e-7')
STEM = 'HOLD_RISK8_20261005_V1'


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path, digest=None):
    need(digest is None or sha(path) == digest, 'changed bound JSON: ' + str(path))
    return json.loads(Path(path).read_text(encoding='utf-8'))


def number(row, field):
    value = Decimal(row.get('decimal_strings', {}).get(field, str(row[field])))
    need(value.is_finite(), 'nonfinite amount: ' + field)
    return value


def close(a, state):
    identity = a.get('task_id') or a['binding']['task_id']
    task = read(state / 'task-progress' / ('task-' + identity + '.json'))
    need(task['status'] == 'completed' and task['exit_code'] == 0 and task['ended_at'],
         'evidence task not actually closed0: ' + identity)
    return identity


def account(case, expected_budget):
    summary = case['summary']
    names = case['symbols']
    need(names == ['BTCUSDT', 'ETHUSDT'] and case['pool'] == 'TWO_ASSET', 'two-asset identity')
    need(summary['completed_minutes'] == summary['required_minutes'] == 436320, 'calendar minutes')
    need(summary['daily_metrics']['days'] == 303, 'actual daily count')
    need(summary['daily_metrics']['initial_nav'] == 10000, 'complete initial capital')
    need(summary['terminal_cash_realized'] is True and summary['terminal_not_forced_free_fill'] is True,
         'actual cash close, not a forced free fill')
    need(summary['account_status'] == 'ACTIVE' and not summary['pending_orders_at_stop'], 'not halted/pending')
    need(summary['unit_certified'] is False and summary['publication_certified'] is False, 'unconfirmed funding')
    paths = {}
    hashes = {}
    for key in ('trades.json', 'funding.json', 'target_meta.json'):
        item = case['artifacts'][key]
        paths[key] = Path(item['path'])
        hashes[key] = sha(paths[key])
        need(hashes[key] == item['sha256'], 'changed account input ' + key)
    meta = read(paths['target_meta.json'])
    need(meta['rules']['annual_volatility_target'] == expected_budget, 'actual target budget')
    need(meta['rules']['absolute_target_per_asset'] == .3 and meta['rules']['gross_target_cap'] == .6,
         'unchanged risk caps')
    need(meta['symbols'] == names and all(r['covariance_symbol_order'] == names for r in meta['risk']),
         'ordered covariance identity')
    totals = dict.fromkeys(('realized', 'fees', 'execution', 'funding', 'unrealized'), Decimal(0))
    for row in read(paths['trades.json']):
        need(row['symbol'] in names, 'trade symbol outside account')
        totals['realized'] += number(row, 'realized_PnL')
        totals['fees'] += number(row, 'fee_USDT_mid')
        totals['execution'] += number(row, 'execution_cost')
    for row in read(paths['funding.json']):
        need(row['symbol'] in names, 'funding symbol outside account')
        totals['funding'] += number(row, 'signed_funding_USDT')
    for symbol in names:
        position = summary['positions'][symbol]
        quantity = number(position, 'quantity')
        entry = number(position, 'entry_price')
        mark = Decimal(str(summary['terminal_mark_prices'][symbol]))
        totals['unrealized'] += quantity * (mark - entry)
        need(quantity == 0 and number(position, 'isolated_balance') == 0, 'terminal quantity/margin')
    need(number(summary, 'isolated_balance') == number(summary, 'unpaid_liability') == 0,
         'terminal margin/liability')
    gross = totals['realized'] + totals['unrealized'] + totals['execution']
    net = gross - totals['fees'] - totals['execution'] + totals['funding']
    need(abs(net - number(summary, 'net_PnL')) <= TOL, 'independent cash-flow net')
    need(abs(gross - number(summary, 'gross_PnL_same_quantities')) <= TOL, 'independent gross')
    need(abs(net - (number(summary, 'NAV') - Decimal(10000))) <= TOL, 'complete-capital NAV')
    for field, total in (('fees_USDT', totals['fees']), ('execution_cost_USDT', totals['execution']),
                         ('funding_USDT', totals['funding']), ('unrealized_PnL', totals['unrealized'])):
        need(abs(number(summary, field) - total) <= TOL, 'saved summary component: ' + field)
    return dict(case_id=case['id'], annual_budget=expected_budget, input_hashes=hashes,
                net=net, gross=gross, fees=totals['fees'], execution=totals['execution'],
                funding=totals['funding'], unrealized=totals['unrealized'],
                actual_vol=summary['daily_metrics']['annual_volatility'],
                minute_MDD=summary['minute_max_drawdown'], turnover=summary['normalized_total_turnover'],
                days=303, full_capital=10000, terminal_cash=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('/mnt/d/codex/coin'))
    parser.add_argument('--state', type=Path, default=Path('/home/xflops/coin-state'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    need(args.output.resolve().is_relative_to(args.state.resolve()), 'output must remain in STATE')
    need(not args.output.exists(), 'new independent output only')
    root, state = args.root, args.state
    protocol_path = root / 'protocols' / (STEM + '.json')
    p = read(protocol_path)
    a_path = root / 'reports/fast_research' / (STEM + '.json')
    f_path = root / 'reports/fast_research' / (STEM + '_FINANCIAL.json')
    diag_path = root / 'reports/fast_research' / (STEM + '_DIAGNOSTIC.json')
    a, f, diag = read(a_path), read(f_path), read(diag_path)
    control = p['saved_control']
    old = read(root / control['actual_path'], control['actual_sha256'])
    oldf = read(root / control['financial_path'], control['financial_sha256'])
    oldp = read(root / control['protocol_path'], control['protocol_sha256'])
    roles = {k: close(v, state) for k, v in (('market8', a), ('finance8', f),
        ('market10', old), ('finance10', oldf), ('diagnostic', diag))}
    need(diag['actual_report_sha256'] == sha(a_path) and diag['financial_report_sha256'] == sha(f_path)
         and diag['protocol_sha256'] == sha(protocol_path), 'diagnostic report binding')
    need(a['binding']['protocol_sha256'] == sha(protocol_path), 'producer protocol binding')
    need(a['complete_calendar_cases'] == old['complete_calendar_cases'] == f['financial_case_calls']
         == oldf['financial_case_calls'] == 4, 'four fully closed accounts in each role')
    need(f['status'].startswith('PASS_CONFIGURED_N_') and oldf['status'].startswith('PASS_CONFIGURED_N_'),
         'independent full financial checks')
    for key in ('start', 'end_exclusive', 'period_days', 'data_manifest', 'initial_capital_USDT',
                'account_path', 'signal', 'allocation', 'strategy'):
        need(p[key] == oldp[key], 'changed paired factor ' + key)
    need(p['strategy_rules']['annual_volatility_target'] == .08, 'single fixed new budget')
    # D064's source-bound protocol predates strategy_rules. Its actual saved,
    # hash-bound target metadata is checked for .10 separately in account().
    if 'strategy_rules' in oldp:
        need(oldp['strategy_rules']['annual_volatility_target'] == .10, 'legacy protocol budget if present')
    for name, digest in p['source_hashes'].items():
        need(sha(root / name) == digest, 'current frozen source changed: ' + name)
    rows, pairs = [], []
    for case in a['cases']:
        old_case = next(c for c in old['cases'] if c['id'] == case['id'])
        x, y = account(old_case, .10), account(case, .08)
        for policy, row in (('HOLD10', x), ('HOLD8', y)):
            d = next(r for r in diag['rows'] if r['policy'] == policy and r['case_id'] == case['id'])
            for source, field in (('net', 'net_USDT'), ('gross', 'gross_USDT'), ('fees', 'fees_USDT'),
                                  ('execution', 'execution_USDT'), ('funding', 'funding_USDT')):
                need(abs(row[source] - Decimal(str(d[field]))) <= TOL, 'diagnostic money mismatch')
            rows.append(dict(policy=policy, **row))
        differences = {key: y[key] - x[key] for key in ('net', 'gross', 'fees', 'execution', 'funding')}
        need(abs(differences['net'] - (differences['gross'] - differences['fees'] -
             differences['execution'] + differences['funding'])) <= TOL, 'paired independent bridge')
        paired = next(r for r in diag['paired_cases'] if r['cost'] == case['cost_id']
                      and r['funding_unit'] == case['unit_id'])
        for component, reported in (('net', 'net_increment_USDT'), ('gross', 'gross_increment_USDT'),
                                    ('funding', 'funding_increment_USDT')):
            need(abs(differences[component] - Decimal(str(paired[reported]))) <= TOL,
                 'reported paired component mismatch: ' + component)
        need(abs(differences['fees'] + differences['execution'] -
             Decimal(str(paired['cost_increment_USDT']))) <= TOL, 'reported paired total cost')
        pairs.append(dict(case_id=case['id'], **differences))
    need(len(diag['ten_asset_EXIT10_descriptive_reference']) == 4 and
         diag['independent_market_evidence'] is False and diag['posthoc_scaling'] is False,
         'separate descriptive reference/no independent alpha or posthoc NAV scaling')
    result = dict(status='PASS_INDEPENDENT_DECIMAL_JSON_BRIDGES_NOT_MARKET_REPLAY',
        task_id=os.environ.get('COIN_TASK_ID'), helper_sha256=sha(__file__),
        protocol_sha256=sha(protocol_path), diagnostic_sha256=sha(diag_path), closed_roles=roles,
        legacy_protocol_has_strategy_rules='strategy_rules' in oldp,
        legacy_budget_evidence='Actual hash-bound saved target_meta.rules annual_volatility_target=.10; legacy protocol has no strategy_rules field',
        rows=rows, paired_differences=pairs, saved_source_resolution_scope=
        'Saved control protocol/report SHA checked; accepted Git bytes resolved by closed root diagnostic, not fetched by this helper',
        candidate='NONE', investment='CASH', long_term_APR='NOT_EVALUABLE',
        market_replays=0, model_fits=0, independent_JSON_amount_reconciliation=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, default=lambda v: str(v), allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(status=result['status'], output=str(args.output), sha256=sha(args.output))))


if __name__ == '__main__':
    main()
