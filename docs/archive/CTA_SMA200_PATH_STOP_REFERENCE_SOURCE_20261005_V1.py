"""D095 bounded read-only final review; no simulator, fitting or wallet replay.

The earlier actual stdin mechanism source was not retained. Its result and task
ID are preserved byte-for-byte. This source independently checks its saved
Decimal inputs and common target matrices, then final summary/period bridges.
Run through scripts/with_task_progress.sh -> bounded.sh in WSL.
"""
from pathlib import Path
from decimal import Decimal, localcontext
import hashlib
import json
import os
from datetime import datetime, timezone
import polars as pl

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
REFDIR = STATE / 'd095-independent-mechanism-20261005-v1'
OUT = ROOT / 'reports/CTA_SMA200_303D_INDEPENDENT_REVIEW_20261005_V1.json'

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

sources = []
def read(path, expected=None):
    path = Path(path)
    sha = digest(path)
    if expected is not None:
        assert sha == expected, str(path)
    sources.append({'path': str(path), 'sha256': sha, 'bytes': path.stat().st_size})
    return json.loads(path.read_text())

def near(a, b, eps=1e-8):
    assert abs(a - b) < eps, (a, b)
    return a - b

accepted_path = ROOT / 'reports/CTA_SMA200_303D_ACCEPTED_20261005_V1.json'
a = read(accepted_path)
baseline = read(ROOT / a['baseline']['path'], a['baseline']['sha256'])
assert a['new_accounts'] == 12 and a['reused_controls'] == 8
assert a['new_complete_accounts'] == 4 and a['stopped_accounts'] == 8
assert a['complete_accounts'] == 12  # Four new plus eight reused controls.
assert a['actual_days'] == 303 and a['initial_capital_per_counterfactual_USDT'] == 10000
assert a['qualified_investment'] == 'NONE/CASH' and a['long_term_APR'] == 'NOT_EVALUABLE'
reference = read(REFDIR / 'SMA_PATH_STOP_REFERENCE.json',
                 '4678d40a5b51b617706b667a68ae27305760f1f0b784c26f88d5308d9bfa854f')
default_scope = read(REFDIR / 'SOURCE_DEFAULT_SCOPE.json',
                     'afcbf4544ec77b056e5c037aa26899d2497f80135f7bc0230f94ba1e3d901348')
copy = ROOT / 'reports/CTA_SMA200_PATH_STOP_REFERENCE_20261005_V1.json'
if copy.exists():
    assert copy.read_bytes() == (REFDIR / 'SMA_PATH_STOP_REFERENCE.json').read_bytes()
else:
    copy.write_bytes((REFDIR / 'SMA_PATH_STOP_REFERENCE.json').read_bytes())

# Actual prior matrices: all columns, all 1220 common ordered rows, no fitting.
targets = [x for x in reference['sources'] if x.get('kind') == 'targets.parquet']
frames = []
for src in targets:
    assert digest(src['path']) == src['sha256']
    frames.append(pl.read_parquet(src['path']))
old = frames[0]
new = frames[1].filter((pl.col('available_us') >= 1740787200000000) &
                       (pl.col('available_us') < 1751328000000000))
assert old.height == new.height == 1220 and old.equals(new)
with localcontext() as ctx:
    ctx.prec = 50
    o = reference['old_WIF_at_old_stop']; n = reference['new_WIF_at_old_stop']
    D = Decimal
    old_eq = D(o['collateral']) + D(o['q']) * (D(o['mark']) - D(o['entry']))
    old_mmr = D('.005') * abs(D(o['q'])) * D(o['mark'])
    new_eq = D(n['collateral']) + D(n['q']) * (D(n['mark_from_signednotional_over_q']) -
                                               D(n['independent_entry_from_prior_WIF_fills']))
    new_mmr = D('.005') * abs(D(n['q'])) * D(n['mark_from_signednotional_over_q'])
    assert old_eq < old_mmr and new_eq > new_mmr
    assert abs(new_eq - D(n['recorded_equity'])) < D('1e-10')
assert reference['new_case_scope']['account_status'] == 'LIQUIDATION_REQUIRED_HALT'
delay = reference['new_case_scope']['stop_us'] - reference['old_case_scope']['stop_us']
assert delay == 262 * 60 * 1000000

cases = {}; finance = []; tasks = []
for item in a['inputs']:
    producer = read(ROOT / item['path'], item['sha256'])
    task_id = producer['binding']['task_id']
    t = read(STATE / 'task-progress' / ('task-' + task_id + '.json'), item['task_sha256'])
    assert t['exit_code'] == 0 and t['status'] == 'completed'
    tasks.append({'task_id': task_id, 'exit_code': t['exit_code']})
    proto_path = ROOT / ('protocols/CTA_SMA200_303D_' + producer['protocol']['cost_ids'][0] + '_20261005_V1.json')
    read(proto_path, producer['binding']['protocol_sha256'])
    assert producer['legacy_control_targets_status'] == 'PASS_SAME_CASH_AND_HOLD_ALL303D_ORDERED_TARGETS'
    assert producer['legacy_signal_golden']['status'].startswith('PASS_')
    for c in producer['cases']:
        proof = c['independent']; s = c['summary']
        assert proof['status'].startswith('PASS_')
        assert proof['minutes'] == s['completed_minutes']
        assert proof['maximum_NAV_error_USDT'] < 1e-7
        assert proof['maximum_wallet_error_USDT'] < 1e-7
        cases[c['id']] = c
        finance.append({'id': c['id'], 'status': proof['status'], 'minutes': proof['minutes'],
                        'NAV_error_USDT': proof['maximum_NAV_error_USDT'],
                        'wallet_error_USDT': proof['maximum_wallet_error_USDT'],
                        'scope': 'REUSED_SAVED_PRODUCER_INDEPENDENT_FINANCE_NOT_RERUN'})

rows = {x['id']: x for x in a['rows']}
baserows = {x['id']: x for x in baseline['rows']}
for row in a['rows']:
    if row['strategy'] in ('CASH', 'HOLD'):
        assert {k: v for k, v in row.items() if k != 'reuse_scope'} == {
            k: v for k, v in baserows[row['id']].items() if k != 'reuse_scope'}
        assert row['reuse_scope'].startswith('REUSED')
stops = []; pairs = []; periods = []
for row in a['rows']:
    if row['strategy'] != 'SMA200_SIGNED':
        continue
    c = cases[row['id']]; s = c['summary']
    near(row['gross_USDT'] + row['funding_USDT'] - row['fees_USDT'] - row['execution_USDT'],
         row['net_USDT'] if row['complete'] else row['stopped_prefix_net_USDT'])
    if not row['complete']:
        assert row['net_USDT'] is None and row['vol'] is None and row['DD'] is None
        assert row['completion'].startswith('NOT_EVALUABLE') and not row['paid_flat']
        assert s['account_status'].endswith('_HALT') and s['NAV'] > 0
        assert row['completed_minutes'] < 436320 and row['residual'] > 0
        stops.append({k: row[k] for k in ['id','completed_minutes','completion','stop_us',
                    'stopped_prefix_net_USDT','residual','halt_witness']})
        continue
    assert row['mode'] == 'LONG_ONLY' and row['completed_minutes'] == 436320
    assert row['paid_flat'] and row['residual'] == 0 and row['SHORT'] == 0
    p = next(x for x in a['paired_recipe'] if x['mode'] == row['mode'] and
             x['cost'] == row['cost'] and x['unit'] == row['unit'])
    base = baserows[p['reference_id']]
    hold = next(x for x in a['rows'] if x['strategy'] == 'HOLD' and
                x['cost'] == row['cost'] and x['unit'] == row['unit'])
    delta = {key: row[key] - base[key] for key in
             ['gross_USDT','funding_USDT','fees_USDT','execution_USDT','net_USDT','vol','DD']}
    near(delta['gross_USDT'] + delta['funding_USDT'] - delta['fees_USDT'] - delta['execution_USDT'], delta['net_USDT'])
    near(delta['net_USDT'], p['net_delta'])
    assert delta['net_USDT'] < 0 and delta['vol'] > 0 and delta['DD'] > 0
    pairs.append({'id': row['id'], 'SMA_net': row['net_USDT'], 'Donchian_net': base['net_USDT'],
                  'HOLD_net': hold['net_USDT'], 'delta_vs_Donchian': delta,
                  'SMA_vol': row['vol'], 'SMA_DD': row['DD'], 'SMA_risk': row['risk'],
                  'paid_flat': row['paid_flat']})
    daily = c['artifacts']['daily_nav.parquet']
    assert digest(daily['path']) == daily['sha256']
    frame = pl.read_parquet(daily['path'])
    assert frame.height == 303
    near(sum(x['net_USDT'] for x in row['periods']), row['net_USDT'])
    near(sum(x['LONG'] + x['SHORT'] + x.get('CASH', 0) for x in c['independent']['daily_direction_contributions']), row['net_USDT'])
    periods.append({'id': row['id'], 'periods': row['periods'], 'daily_artifact': daily,
                    'scope': '303_SAVED_ROWS_AND_DIRECTION_TOTAL_AND_THREE_PERIOD_SUM_NO_NEW_WALLET_REPLAY'})
for p in a['paired_recipe']:
    if p['mode'] != 'LONG_ONLY':
        assert not p['full_pair'] and p['net_delta'] is None

report = {'status': 'PASS_LIMITED_INDEPENDENT_FINAL_SMA303D_IDENTITY_BRIDGES_AND_HALT_SCOPE',
          'accepted_sha256': digest(accepted_path), 'created_utc': datetime.now(timezone.utc).isoformat(),
          'review_task_id': os.environ['COIN_TASK_ID'], 'reference_source': str(Path(__file__)),
          'reference_source_sha256': digest(__file__), 'sources': sources,
          'producer_tasks': tasks, 'new_accounts': 12, 'new_complete': 4, 'new_halted': 8,
          'reused_controls': 8, 'finance_proofs': finance, 'four_complete_LO_bridges': pairs,
          'four_LO_periods': periods, 'eight_HALTs': stops,
          'original_path_stop_proof': {'path': str(copy), 'sha256': digest(copy),
             'actual_original_task_id': reference['review_task_id'], 'original_stdin_source': 'NOT_RETAINED',
             'common_ordered_targets': 1220, 'old_equity': str(old_eq), 'old_MMR': str(old_mmr),
             'new_equity_at_old_stop': str(new_eq), 'new_MMR_at_old_stop': str(new_mmr),
             'both_cases_halt': True, 'stop_delay_minutes': 262,
             'March1_new_NAV': 10203.610893934867, 'March1_new_WIF_quantity': -169.11066554},
          'source_default_scope_review': default_scope,
          'conclusion': 'PAUSE_THIS_SMA200_RECIPE_PROMOTION; NONE/CASH. Four LO paths underperform same-mode Donchian with greater actual vol/DD; eight short-capable paths halt. No full-window short-alpha conclusion.',
          'limitations': ['SEEN_DEVELOPMENT_BINANCE_PRICE_FUNDING_BYBIT_COST_PROXY_NOT_NATIVE',
             'FUNDING_UNIT_UNKNOWN_TWO_SCENARIOS_NOT_CERTIFICATION',
             'HALTS_ARE_CONDITIONAL_ISOLATED_RULE_STOPS_NOT_NATIVE_LIQUIDATION_FILLS_OR_PORTFOLIO_BANKRUPTCY',
             'SOURCE_BYTES_DIFFER_OPTIONAL_DEFAULT_STATIC_REVIEW_AND_SYNTHETIC_GOLDEN_NOT_WHOLEHISTORY_CAUSAL_ISOLATION',
             'SAME122D_FORECAST_BUT_DIFFERENT_START_INVENTORY_ENTRY_AND_NAV_DESCRIPTIVE_NOT_RESCUE',
             'PERIOD_SUM_CHECK_IS_NOT_REPEAT_MINUTE_ACCOUNTANT',
             'COLLECTOR_CONTINUITY_NOT_REVIEWED_NO_HEALTH_CLAIM'],
          'new_accounts_run_by_reviewer': 0, 'new_fits': 0, 'new_downloads': 0,
          'full_finance_replays': 'NOT_RUN_REUSED_12_EXISTING_PROOFS', 'locked_body_read': False}
assert not OUT.exists(), 'Do not overwrite evidence'
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
print(json.dumps({'path': str(OUT), 'sha256': digest(OUT), 'bytes': OUT.stat().st_size,
                  'status': report['status'], 'accepted_sha256': report['accepted_sha256'],
                  'task_id': report['review_task_id']}))
