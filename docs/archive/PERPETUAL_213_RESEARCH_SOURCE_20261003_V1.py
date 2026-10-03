"""UNRUN D043 draft: one fixed213-day independent window over accepted financial bodies.

No source download/QA, model fitting, account transport or spot/perp mixing.
The parent controller.main is privately compiled only to bind the new metadata
and dispatch the fifth fixed selector; its constant-cash branch is preserved.
"""
from __future__ import annotations
import gc
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
import polars as pl
from quant.paths import ROOT, STATE
from scripts.investment import perpetual_directional as base
from scripts.investment import public_sma_perpetual as sma
from scripts.investment import public_donchian_perpetual as donchian
from scripts.investment import perpetual_public_benchmark as benchmark
from scripts.investment import public_long_development_adapter as private

CONTRACT = 'D043_FIXED_213D_SMA_DIRECTIONS_AND_PUBLIC2H_CONDITIONAL_V1'
STATUS = 'COMPLETE_D043_FIXED213D_PUBLIC_PERPETUAL_SCREENING_NOT_NATIVE_OR_LONG_TERM_APR'
MANIFEST_STATUS = 'PASS_D043_FIXED_213D_USDM_INPUT_SOURCE_BINDING_NOT_ECONOMICS'
INPUT = 'reports/fast_research/PERPETUAL_213D_INPUT_BINDING_20261003_V1.json'
PRECEDING_FAILURE = dict(path='reports/fast_research/PERPETUAL_HISTORY_SOURCE_ACTUAL_20261003_V1.json',
    sha256='82cae26a2313417c59e6a63af8458d775851e7c1e341d51bc9e7fa9a2cf6c427',
    required_status='FAIL_D042_HISTORY_SOURCE')
PERIOD = '213D'
START = '2024-01-01T00:00:00+00:00'
END = '2024-08-01T00:00:00+00:00'
SMA_ID = 'COIN_JESSE_SMA50_200_1D_USDT_PERPETUAL_ADAPTER'
DONCHIAN_ID = donchian.STRATEGY_ID
DONCHIAN_SELECTOR = 'DONCHIAN_LONG_ONLY'
SELECTORS = (*sma.MODES, DONCHIAN_SELECTOR)
PINS = {
    'src/quant/perpetual_account.py': 'cf47ae9b889eab4506be2b22929322976a6833235eaab6459399bdec53de2261',
    'scripts/investment/perpetual_directional.py': '547a1ca2d8e4b9278f599a1972f099bfe449910e34791e5a0e16873ce67d5ef3',
    'scripts/investment/public_sma_perpetual.py': 'c90a9d383fe3365681bfdd5772c0f8a9a8977d57e423627b9159098ce25f30df',
    'scripts/investment/public_donchian_perpetual.py': '33bf4b12ab70619097aa139b844a06205b5bf00ca15594afc5abdfabd15f9cc1',
    'scripts/investment/perpetual_public_benchmark.py': '322178db8d8001833460b1ed01fc53ae2f4f86b494410c1407605de6e97db4b6',
}
RULES = dict(base.RULES, period_id=PERIOD, score_start=START, score_end_exclusive=END,
    strategy_design=[dict(strategy_id=SMA_ID, mode=mode) for mode in sma.MODES]
        + [dict(strategy_id=DONCHIAN_ID, mode='LONG_ONLY')],
    planned_selectors=20, planned_trading_account_simulations=16,
    planned_constant_cash_baselines=1, fresh_flat_each_strategy_direction=True,
    no_saved_old_financial_accounts_replayed=True,
    signal_histories='200_COMPLETED_DAILY_SMA_OR_200_COMPLETED2H_DONCHIAN',
    risk_histories='SAME30_COMPLETED_UTC_DAILY_RETURN_COVARIANCE',
    conditional_unit_scenarios_are_sensitivity_not_HPO=True,
    classification='NEW_INDEPENDENT213_SEEN_SCREENING_NOT_COMPLETE547',
    original_547D_source_failure_preserved=True, original_547D_source_completed=False)


def stamp(text):
    return int(datetime.fromisoformat(text).timestamp() * 1_000_000)


def months(first, last):
    year, month = map(int, first.split('-')); result = []
    while f'{year:04d}-{month:02d}' <= last:
        result.append(f'{year:04d}-{month:02d}')
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return result


def metadata_view(manifest):
    """Pure JSON role normalization before the unchanged financial reader."""
    base.need(manifest['status'] == MANIFEST_STATUS
        and manifest['funding_rate_unit'] == 'UNCONFIRMED'
        and manifest['funding_unit_certified'] is False
        and manifest['locked_consumed'] is False, 'Accepted213 source-only metadata, no unit claim')
    base.need(len(manifest['windows']) == 1 and len(manifest['source_files']) == 72,
        'Exact72 accepted213 source bindings; no wider failed547 universe')
    original = manifest['windows'][0]
    base.need((original['id'], original['start'], original['end_exclusive'], original['days'],
        original['minutes_per_symbol']) == (PERIOD, START, END, 213, 306720), 'Fixed complete213 window')
    layout = {
        'trade_1m': ('trade:1m:', 'USD_M_PERPETUAL_TRADE_KLINES', '2024-01', '2024-07'),
        'mark_1m': ('markPriceKlines:', 'USD_M_PERPETUAL_markPriceKlines', '2024-01', '2024-07'),
        'funding': ('fundingRate:', 'USD_M_PERPETUAL_fundingRate', '2024-01', '2024-07'),
        'trade_1d_warmup': ('trade:1d:', 'USD_M_PERPETUAL_TRADE_KLINES', '2023-06', '2023-12'),
        'trade_1d_score': ('trade:1d:', 'USD_M_PERPETUAL_TRADE_KLINES', '2024-01', '2024-07'),
        'signal_warmup_2h': ('trade:2h:', 'USD_M_PERPETUAL_TRADE_KLINES', '2023-12', '2023-12'),
    }
    files = manifest['source_files']; symbols = {}; all_ids = []
    for symbol in base.SYMBOLS:
        roles = original['source_ids'][symbol]
        base.need(set(roles) == set(layout), 'Exact six source roles, no index or Spot substitution')
        for role, (prefix, product, first, last) in layout.items():
            expected = [prefix + symbol + ':' + month for month in months(first, last)]
            base.need(roles[role] == expected, 'Exact symbol/product/month order ' + symbol + ' ' + role)
            for identity in expected:
                item = files[identity]
                base.need(item['symbol'] == symbol and item['month'] == identity[-7:]
                    and item['product'] == product and type(item['rows']) is int and item['rows'] > 0,
                    'Exact accepted metadata row, no inherited missing event count')
            all_ids.extend(expected)
        counts = {role: sum(files[key]['rows'] for key in identities) for role, identities in roles.items()}
        base.need(counts['trade_1m'] == counts['mark_1m'] == 306720
            and counts['trade_1d_warmup'] == 214 and counts['trade_1d_score'] == 213
            and counts['signal_warmup_2h'] == 372, 'Full scoring and genuine200-bar warmup counts')
        symbols[symbol] = dict(source_ids=roles, rows_inherited_from_receipts={'funding': counts['funding']})
    base.need(len(all_ids) == len(set(all_ids)) == 72 and set(all_ids) == set(files),
        'Every explicit source used exactly in one metadata role; no wider IO universe')
    return dict(manifest, windows=[dict(original, symbols=symbols)])


def relative_proof(ref):
    value = base.relative_proof(ref)
    return metadata_view(value) if ref['path'] == INPUT else value


def signal_history(manifest, window):
    """Monthly accepted pairs -> original complete120-minute2h aggregator."""
    columns = ['symbol', 'interval', 'open_us', 'close_us', 'available_us',
               'open', 'high', 'low', 'close', 'volume']
    roles = window['symbols']; warm = [roles[s]['source_ids']['signal_warmup_2h'][0] for s in base.SYMBOLS]
    frame, proofs = base.source_frame(manifest, warm); frames = [frame.select(columns)]
    for index in range(7):
        identities = [roles[s]['source_ids']['trade_1m'][index] for s in base.SYMBOLS]
        minute, pairs = base.source_frame(manifest, identities); proofs.extend(pairs)
        frames.append(benchmark.closed_two_hours(minute.select([key for key in columns if key != 'interval'])))
        del minute; gc.collect()
    bars = pl.concat(frames).sort(['symbol', 'open_us'])
    base.need(bars.height == 2 * (372 + 213 * 12), 'December warmup and every scored2h bar retained')
    return bars, proofs


def context(spec):
    """Metadata/AST only; original source bytes and shared globals stay fixed."""
    base.need(spec['contract_id'] == CONTRACT and spec['rules'] == RULES
        and spec['period_ids'] == [PERIOD] and spec['cost_scenarios'] == base.COSTS
        and spec['unit_scenarios'] == base.UNITS and spec['input_manifest']['path'] == INPUT,
        'One predeclared213 independent period, twenty fixed cost/unit selectors')
    base.need(spec['preceding_failed_source'] == PRECEDING_FAILURE, 'Original547 failure cannot be hidden')
    prior = base.relative_proof(spec['preceding_failed_source'])
    base.need(prior['completed_files'] == 83 and prior['required_files'] == 148
        and prior['source_acceptance_granted'] is False, 'Original83/148 remains failed, not a complete547 window')
    for name, digest in PINS.items():
        base.need(base.sha(ROOT / name) == digest and spec['frozen_sources'][name] == digest,
            'Preserved financial/target source ' + name)
    derivation = []
    globals2h = private.namespace(donchian, ['_contexts', 'fixed_targets'], dict(
        SOURCE_BEGIN_US=stamp('2023-12-01T00:00:00+00:00'),
        DAILY_BEGIN_US=stamp('2023-06-01T00:00:00+00:00'), SCORE_BEGIN_US=stamp(START)), derivation)
    target2h = SimpleNamespace(fixed_targets=globals2h['fixed_targets'])
    simulate2h = benchmark.adapted_simulate(derivation, target2h)

    def load_window(manifest, window):
        actual = base.load_window(manifest, window)
        actual['signal_bars'], signal_proofs = signal_history(manifest, window)
        actual['input_proofs'] += [dict(proof, role='SIGNAL_ONLY_NOT_EXECUTION_OR_RISK') for proof in signal_proofs]
        return actual

    def dispatch(window, mode, cost, unit, progress=None, guard=None):
        if mode == DONCHIAN_SELECTOR:
            return simulate2h(window, 'LONG_ONLY', cost, unit, progress, guard)
        return base.simulate(window, mode, cost, unit, progress, guard)

    def transform(node, changes):
        node = private.literal(node, changes, 'ONE_FIXED_PERIOD_CLI',
            "['122D','90D','BOTH']", "['213D','BOTH']", 1)
        node = private.literal(node, changes, 'ONE_FIXED_PERIOD_METADATA',
            "['122D','90D']", "['213D']", 1)
        node = private.literal(node, changes, 'SIXTEEN_PHYSICAL_TRADING_ACCOUNTS',
            'len(selected)*12', 'len(selected)*16', 1)
        node = private.native._replace(node, changes, 'RECORD_PRIVATE_METADATA_AND_SIGNAL_DERIVATION',
            "write(run/'RUN_BINDING.json',binding)",
            "binding['private_history_derivation'] = PRIVATE_DERIVATION\nwrite(run/'RUN_BINDING.json',binding)")
        old = "result['cases'].append(dict(id=case_id,period=window_spec['id'],mode=mode,cost_id=cost['id'],unit_id=unit['id'],**saved))"
        new = "saved['summary']['strategy_id'] = DONCHIAN_ID if mode == DONCHIAN_SELECTOR else SMA_ID\nresult['cases'].append(dict(id=case_id,period=window_spec['id'],mode='LONG_ONLY' if mode == DONCHIAN_SELECTOR else mode,strategy_id=saved['summary']['strategy_id'],selector_mode=mode,cost_id=cost['id'],unit_id=unit['id'],**saved))"
        node = private.native._replace(node, changes, 'CANONICAL_DIRECTION_AND_EXPLICIT_STRATEGY_ID', old, new)
        node = private.literal(node, changes, 'HONEST_FIVE_SELECTOR_FEATURE_METADATA',
            "'ORIGINAL_PUBLIC_SMA50_200_DAILY_SIGNED'", "'ORIGINAL_SMA_DAILY_AND_DONCHIAN2H_FIXED213'", 1)
        return private.literal(node, changes, 'PREDECLARED_LONGER_WINDOW_REASON',
            "'Same product and capital four-direction comparison'",
            "'Predeclared complete213 independent account; original547 source failure preserved'", 1)

    strategy = SimpleNamespace(MODES=SELECTORS, fixed_targets=sma.fixed_targets)
    environment = private.namespace(base, ['main'], dict(__file__=__file__, CONTRACT=CONTRACT,
        STATUS=STATUS, MANIFEST_STATUS=MANIFEST_STATUS, RULES=RULES, strategy=strategy,
        relative_proof=relative_proof, load_window=load_window, simulate=dispatch,
        PRIVATE_DERIVATION=derivation, SMA_ID=SMA_ID, DONCHIAN_ID=DONCHIAN_ID,
        DONCHIAN_SELECTOR=DONCHIAN_SELECTOR), derivation, transform)
    return dict(main=environment['main'], simulate=dispatch, load_window=load_window,
        target2h=globals2h['fixed_targets'], derivation=derivation)


def main():
    # The unchanged parent.main parses identical CLI arguments and does all
    # environment, pinned-source, accepted-smoke, registry and resource checks.
    import argparse
    p = argparse.ArgumentParser(add_help=False); p.add_argument('--protocol', type=Path, required=True)
    arguments, _ = p.parse_known_args()
    context(base.small(arguments.protocol))['main']()


if __name__ == '__main__':
    main()
