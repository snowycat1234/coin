"""Four fixed wallets using saved causal targets and the unchanged finance kernel."""
import argparse
import gc
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import time
import zipfile
from datetime import datetime, timezone

import numpy as np
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq

from restore_minutes import SYMBOLS, START, END, DAY, MINUTE, disk_budget, save, sha

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TARGET_SHA = '414b90f4804ad890ab78fbf9154647c848cca4d8b866c9dacf6aa6de02fefec2'


def saved_factory(saved, arm):
    if list(saved['symbol_order']) != list(SYMBOLS):
        raise ValueError('Exact CORE5 target coordinates')
    clocks = saved['decision_us']
    ix = np.flatnonzero((clocks >= START) & (clocks < END))
    required = np.arange(START, END, DAY, dtype=np.int64)
    if not np.array_equal(clocks[ix], required) or not saved['ready'][ix].all():
        raise ValueError('Complete causal saved target decisions')
    weights = saved[arm][ix]
    if weights.shape != (63, 5) or not np.isfinite(weights).all():
        raise ValueError('Saved target shape/finite')
    frame = pl.DataFrame([dict(available_us=int(t), symbol=s, target_weight=float(weights[i, j]))
                          for i, t in enumerate(required) for j, s in enumerate(SYMBOLS)])

    def factory(daily, decisions, mode):
        if mode != 'LONG_SHORT' or not np.array_equal(decisions, required):
            raise ValueError('One fixed window/mode')
        return frame, dict(arm=arm, target_sha256=TARGET_SHA,
                           signal_fit_in_wallet=False, BTC_hedge_fully_charged=True,
                           same_risk_algorithm_not_equal_realized_risk=True)
    return factory


def decision_prices(features):
    rows = []
    with zipfile.ZipFile(features) as z:
        manifest = json.loads(z.read('MEMBERS.json'))['files']
        for symbol in SYMBOLS:
            name = 'source_tables_not_model_inputs/daily_features/' + symbol + '.parquet'
            raw = z.read(name)
            if sha(raw) != manifest[name]['SHA256']:
                raise ValueError('Accepted daily price source')
            dtype = pq.read_schema(io.BytesIO(raw)).field('dt').type
            tab = pq.read_table(io.BytesIO(raw), columns=['dt', 'close', 'complete_kline'], filters=[
                ('dt', '>=', pa.scalar(datetime(2021, 4, 4, tzinfo=timezone.utc), type=dtype)),
                ('dt', '<', pa.scalar(datetime(2021, 6, 6, tzinfo=timezone.utc), type=dtype))])
            for r in tab.to_pylist():
                if not r['complete_kline'] or not np.isfinite(r['close']) or r['close'] <= 0:
                    raise ValueError('Observed completed decision close')
                rows.append(dict(symbol=symbol, close_us=int(r['dt'].timestamp() * 1000000) + DAY,
                                 close=float(r['close'])))
    return pl.DataFrame(rows).sort(['symbol', 'close_us'])


def asset_attribution(trades, funds, summary):
    # Price attribution is a signed inventory bridge, not spendable short proceeds.
    out = {s: dict(gross_price_USDT=0., fees_USDT=0., execution_USDT=0., funding_USDT=0.,
                   turnover_USDT=0.) for s in SYMBOLS}
    for r in trades:
        x = out[r['symbol']]
        x['gross_price_USDT'] -= r['position_delta'] * r['mid_price']
        x['fees_USDT'] += r['fee_USDT_mid']
        x['execution_USDT'] += r['execution_cost']
        x['turnover_USDT'] += abs(r['position_delta']) * r['mid_price']
    for r in funds:
        out[r['symbol']]['funding_USDT'] += r['signed_funding_USDT']
    for s, x in out.items():
        x['gross_price_USDT'] += summary['terminal_signed_marked_notional'][s]
        x['net_contribution_USDT'] = x['gross_price_USDT'] - x['fees_USDT'] - x['execution_USDT'] + x['funding_USDT']
    error = abs(sum(x['net_contribution_USDT'] for x in out.values()) - summary['net_PnL'])
    if error > 1e-7:
        raise ValueError('Asset bridge and full wallet net disagree')
    return dict(assets=out, full_wallet_bridge_error_USDT=error,
                alt_gross_price_USDT=sum(out[s]['gross_price_USDT'] for s in SYMBOLS[1:]),
                BTC_hedge_gross_price_USDT=out[SYMBOLS[0]]['gross_price_USDT'],
                extra_hedge_costs_fully_retained=True)


def paired_bootstrap(delta):
    values = np.asarray(delta, dtype=np.float64)
    if values.shape != (63, 2) or not np.isfinite(values).all():
        raise ValueError('Joint pair/unit UTC calendar')
    rng = np.random.default_rng(811084)
    draws = np.empty((1000, 2))
    for i in range(1000):
        starts = rng.integers(0, len(values), size=5)
        indices = ((starts[:, None] + np.arange(14)) % len(values)).ravel()[:len(values)]
        draws[i] = values[indices].sum(axis=0)
    return np.quantile(draws, [.025, .975], axis=0).T


class Progress:
    def __init__(self, name):
        self.name = name
        self.last = 0.

    def update(self, stage, count, total, unit, **kwargs):
        now = time.monotonic()
        if now - self.last >= 20 or count == 1:
            print(self.name, stage, count, '/', total, unit, flush=True)
            self.last = now


def run(state, features, source_commit):
    os.environ['QUANT_ROOT'] = str(ROOT)
    os.environ['QUANT_STATE'] = str(state)
    from scripts.investment import perpetual_directional as engine
    from modules.transformer_v3.isolated_audit import verify
    from quant.bybit_isolated_account import BybitIsolatedAccount
    git = lambda *args: subprocess.check_output(['git', *args], cwd=ROOT).decode().strip()
    if git('rev-parse', 'HEAD') != source_commit or git('status', '--porcelain'):
        raise ValueError('Clean exact published economics source required')
    binding = json.loads((HERE / 'SOURCE_BINDING.json').read_bytes())
    for name, digest in binding['financial_source_sha256'].items():
        if sha((ROOT / name).read_bytes()) != digest:
            raise ValueError('Unchanged financial/source binding: ' + name)
    if sha(features.read_bytes()) != 'bdbcdc488fc4245c1fb6b433df1fc4bf806a120433db71e180816119cebbcc30':
        raise ValueError('Feature archive binding')
    target_path = HERE / 'diagnostic/SAVED_TARGETS.npz'
    if sha(target_path.read_bytes()) != TARGET_SHA:
        raise ValueError('Original saved targets only; no refit')
    diagnostic = json.loads((HERE / 'diagnostic/DIAGNOSTIC_RESULT.json').read_bytes())
    if diagnostic['status'] != 'ALLOCATION_GATE_PASS' or not all(diagnostic['gates'].values()):
        raise ValueError('Allocation gates before economics')
    source = state / 'minute-source'
    recovery = json.loads((source / 'RECOVERY.json').read_bytes())
    if recovery['status'] != 'PASS_REAL_GIT_WINDOW_RESTORATION' or recovery['window'] != [START, END]:
        raise ValueError('Frozen real recovered window only')
    derived_binding = json.loads((source / 'DERIVED_BINDING.json').read_bytes())
    if sha((source / 'RECOVERY.json').read_bytes()) != derived_binding['recovery_sha256']:
        raise ValueError('Original data recovery receipt binding')
    for name, digest in derived_binding['derived_file_sha256'].items():
        if sha((source / name).read_bytes()) != digest:
            raise ValueError('Restored execution bytes changed')
    saved = np.load(target_path, allow_pickle=False)
    tape = np.load(source / 'WINDOW_MARKET.npz', allow_pickle=False)
    required = np.arange(START, END, MINUTE, dtype=np.int64)
    if not np.array_equal(tape['times'], required):
        raise ValueError('Complete 90720 real execution minutes')
    market = {s: {k: tape[s + '_' + k] for k in ('open', 'close', 'quote_volume', 'mark')} for s in SYMBOLS}
    window = dict(symbols=SYMBOLS, start=START, end=END, market=market,
                  daily=decision_prices(features), events=json.loads((source / 'FUNDING_EVENTS.json').read_bytes()))
    output = state / 'economics'
    output.mkdir()
    started = time.monotonic()
    save(output / 'STARTED.json', dict(source_commit=source_commit, protocol_sha256=sha((HERE / 'PROTOCOL.json').read_bytes()),
                                      target_sha256=TARGET_SHA, source_recovery_sha256=sha((source / 'RECOVERY.json').read_bytes()),
                                      attempt=1, additional_fits=0, wallet_limit=4, window=[START, END]))

    def guard():
        disk_budget(state)
        if time.monotonic() - started > 1200:
            raise RuntimeError('Frozen economic wall budget')

    results = []
    daily_delta = {}
    for unit in engine.UNITS:
        for arm in ('raw', 'residual'):
            name = arm + '_' + unit['id']
            print('START wallet', len(results) + 1, '/4', name, flush=True)
            case = engine.simulate(window, 'LONG_SHORT', engine.COSTS[0], unit,
                                   progress=Progress(name), guard=guard, target_factory=saved_factory(saved, arm),
                                   account_factory=BybitIsolatedAccount, persist_cash_close=True)
            directory = output / name
            written = engine.save_case(case, directory)
            summary = written['summary']
            save(directory / 'summary.json', summary)
            audit = verify(directory, SYMBOLS, unit['scale'])
            save(directory / 'INDEPENDENT_AUDIT.json', audit)
            attribution = asset_attribution(case['trades'], case['funding'], summary)
            save(directory / 'ASSET_ATTRIBUTION.json', attribution)
            record = dict(id=name, arm=arm, scale=unit['scale'], summary=summary, audit=audit,
                          attribution=attribution, additional_fits=0)
            results.append(record)
            save(output / ('CASE_' + str(len(results)) + '.json'), record)
            daily = pl.read_parquet(directory / 'daily_nav.parquet')
            if daily.height == 63:
                daily_delta[name] = np.diff(np.r_[10000., daily['nav'].to_numpy()])
            print('COMPLETE wallet', len(results), '/4', name, summary['completion'],
                  'net_USDT', summary['net_PnL'], 'cash', summary['terminal_cash_realized'], flush=True)
            del case
            gc.collect()
            guard()
    return finish(output, results, daily_delta, source_commit, started)


def finish(output, results, daily_delta, source_commit, started):
    indexed = {(r['arm'], r['scale']): r for r in results}
    pairs = []
    complete = all(r['summary']['completed_minutes'] == r['summary']['required_minutes'] and
                   r['summary']['terminal_cash_realized'] and r['audit']['status'].startswith('PASS') for r in results)
    if complete:
        delta = np.column_stack([daily_delta['residual_' + name] - daily_delta['raw_' + name]
                                 for name in ('RAW_AS_FRACTION', 'RAW_AS_PERCENT')])
        intervals = paired_bootstrap(delta)
    else:
        intervals = [None, None]
    for k, scale in enumerate((1., .01)):
        raw = indexed['raw', scale]
        residual = indexed['residual', scale]
        a, b = raw['summary'], residual['summary']
        va = a['daily_metrics']['annual_volatility'] if a['daily_metrics'] else None
        vb = b['daily_metrics']['annual_volatility'] if b['daily_metrics'] else None
        pairs.append(dict(scale=scale, raw_net_USDT=a['net_PnL'], residual_net_USDT=b['net_PnL'],
                          paired_net_increment_USDT=b['net_PnL'] - a['net_PnL'],
                          paired_alt_gross_price_increment_USDT=residual['attribution']['alt_gross_price_USDT'] - raw['attribution']['alt_gross_price_USDT'],
                          paired_BTC_hedge_gross_price_increment_USDT=residual['attribution']['BTC_hedge_gross_price_USDT'] - raw['attribution']['BTC_hedge_gross_price_USDT'],
                          paired_fee_increment_USDT=b['fees_USDT'] - a['fees_USDT'],
                          paired_execution_increment_USDT=b['execution_cost_USDT'] - a['execution_cost_USDT'],
                          paired_funding_increment_USDT=b['funding_USDT'] - a['funding_USDT'],
                          raw_annual_realized_vol=va, residual_annual_realized_vol=vb,
                          residual_over_raw_vol_ratio=vb / va if va and vb is not None else None,
                          conditional_14day_joint_bootstrap_net_increment_95_USDT=None if intervals[k] is None else intervals[k].tolist()))
    gates = dict(all4_complete_charged_cash_independently_audited=complete,
                 no_liquidation=all(r['summary'].get('liquidation_count', len(r['summary'].get('liquidations', []))) == 0 for r in results),
                 residual_net_positive_both=all(p['residual_net_USDT'] > 0 for p in pairs),
                 paired_net_increment_positive_both=all(p['paired_net_increment_USDT'] > 0 for p in pairs),
                 paired_bootstrap_lower_positive_both=complete and all(p['conditional_14day_joint_bootstrap_net_increment_95_USDT'][0] > 0 for p in pairs),
                 alt_gross_price_increment_positive_both=all(p['paired_alt_gross_price_increment_USDT'] > 0 for p in pairs),
                 actual_vol_and_MDD_within12percent=complete and all(r['summary']['daily_metrics']['annual_volatility'] <= .12 and r['summary']['minute_max_drawdown'] <= .12 for r in results),
                 residual_raw_vol_ratio_at_most1_10=complete and all(p['residual_over_raw_vol_ratio'] is not None and p['residual_over_raw_vol_ratio'] <= 1.10 for p in pairs))
    result = dict(status='PASS_FROZEN_ECONOMIC_GATES' if all(gates.values()) else 'STOP_THIS_84_21_RECIPE',
                  source_commit=source_commit, target_sha256=TARGET_SHA, attempt=1, additional_fits=0,
                  actual_wallets=len(results), window=[START, END], pairs=pairs, gates=gates,
                  elapsed_seconds=time.monotonic() - started,
                  bootstrap_seed=811084, bootstrap_replicates=1000,
                  interpretation='Conditional reused training history, crossvenue/unit/mark/MMR assumptions; not native, unseen OOS or riskmatched alpha',
                  development_reads=0, parameter_search=False)
    save(output / 'RESULT.json', result)
    print(json.dumps(result, indent=2), flush=True)
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--state', type=Path, required=True)
    p.add_argument('--features', type=Path, required=True)
    p.add_argument('--source-commit', required=True)
    a = p.parse_args()
    if not a.state.resolve().is_relative_to(Path('/workspace')):
        raise ValueError('Task STATE only')
    run(a.state.resolve(), a.features.resolve(), a.source_commit)


if __name__ == '__main__':
    main()
