"""D037 private daily signal dispatch over pinned minute/native account loops.

Only metadata and ASTs are touched by context(). Approved daily files are read
inside research(), after the original source/smoke/budget registration guards.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import polars as pl
from quant.paths import ROOT, STATE
from scripts.investment import public_long_development_adapter as parent
from scripts.investment import public_donchian_daily as daily

STRATEGY = daily.STRATEGY_ID
PROFILES = {
 'CONT547': dict(protocol='protocols/PUBLIC_LONG_547D_FIXED_THREE_ACCOUNTS_20261003_V1.json',
    protocol_sha256='5366363196157c1629e2e00a00301956e61b2c295b476520359bc0bd55ac746d',
    report='reports/fast_research/PUBLIC_LONG_547D_ACTUAL_20261003_V1.json',
    report_sha256='c70e3011f74ddbbbf250316bb2cad9a02d2bd6945b266a1a96a1083b9fcbc6e8',
    scope=parent.SCOPE,months=list(parent.MONTHS),days=578,files=38,derivative_rows=1664640),
 'CONT122': dict(protocol='protocols/BYBIT_SPOT_2H_122D_V2.json',
    protocol_sha256='11a667b18ec6c3f779214c28fc0bcfe805319ee8b89e62097f6ee3aa52659192',
    report='reports/fast_research/BYBIT_SPOT_2H_122D_ACTUAL_20261002_V2.json',
    report_sha256='53447ac3722829cb5c4db12f5b469b100edb20c05bbb6e9c83f29bce5138bee3',
    scope='JUL_NOV_2025',months=[f'2025-{m:02d}' for m in range(7,12)],days=153,files=10,derivative_rows=440640),
 'CONT90': dict(protocol='protocols/BYBIT_SPOT_2H_90D_V2.json',
    protocol_sha256='8505eec0f6406d7725962856455e3dfdbefda6139503f5e2d7856443383ca457',
    report='reports/fast_research/BYBIT_SPOT_2H_90D_ACTUAL_20261002_V2.json',
    report_sha256='329f9f923ed4fd8223e2e267a200c2e67036c8ce4f82a7fef0027efdd3b7960a',
    scope='OCT2025_FEB2026',months=['2025-10','2025-11','2025-12','2026-01','2026-02'],days=151,files=10,derivative_rows=348480),
}
DAILY_MONTHS = tuple(f'{year}-{month:02d}' for year in range(2023,2027) for month in range(1,13)
    if '2023-06' <= f'{year}-{month:02d}' <= '2026-02')
DAILY_STATUS = 'PASS_D037_OFFICIAL_SPOT_DAILY_SOURCE_FORMAT_AND_CALENDAR_ONLY'
DAILY_DIR = STATE / 'd037-official-spot-daily-source-20261003-v1'
UTILITY_SHA = '15ea3a089f39149d9d669fa3425fa35821c2c01b3cce1c15f751fd1723a9406f'
require, file_sha = parent.old.require, parent.native.file_sha


def metadata(path, sha256):
    result = parent.old.read_json(ROOT / path)
    require(file_sha(ROOT / path) == sha256, 'Exact small prior proof/protocol identity required')
    return result


def input_reference(profile):
    proof = metadata(profile['report'],profile['report_sha256'])
    require(proof['status'] == 'COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING'
        and proof['source_bytes_unchanged'] and proof['all_planned_ledgers_complete']
        and proof['minute_source']['rows'] == profile['derivative_rows']
        and proof['minute_source']['invalid_minutes'] == 0, 'Completed accepted parent derivative metadata')
    return dict(report_path=profile['report'],report_sha256=profile['report_sha256'],
        path=proof['minute_source']['path'],sha256=proof['minute_source']['sha256'])


def daily_metadata(spec):
    reference = spec['daily_source_receipt']
    require(set(reference) == {'path','sha256','required_status'}
        and reference['required_status'] == DAILY_STATUS, 'Fixed source-only daily receipt binding')
    proof = metadata(reference['path'],reference['sha256'])
    require(proof['status'] == DAILY_STATUS, 'Daily source must have completed format/calendar acceptance')
    source_spec = proof['binding']['spec']
    require(source_spec['source_scope'] == 'JUN2023_FEB2026'
        and tuple(source_spec['source_calendar']) == DAILY_MONTHS
        and source_spec['days_per_symbol'] == 1004, 'Explicit66-file daily scope and1004 UTC days')
    records = proof['sources']
    require(len(records) == 66 and len({(r['symbol'],r['month']) for r in records}) == 66
        and {(r['symbol'],r['month']) for r in records} ==
        {(symbol,month) for symbol in parent.old.SYMBOLS for month in DAILY_MONTHS},
        'Exact daily symbol-month universe before any market IO')
    for record in records:
        expected = DAILY_DIR / (record['symbol']+'-'+record['month']) / 'source.parquet'
        require(Path(record['normalized_path']).resolve() == expected.resolve(), 'Exact authorized native STATE1d path')
        first = date.fromisoformat(record['month']+'-01')
        end = date(first.year+first.month//12,first.month%12+1,1)
        require(type(record['rows']) is int and record['rows'] == (end-first).days
            and len(record['normalized_sha256']) == 64
            and all(c in '0123456789abcdef' for c in record['normalized_sha256']), 'Exact monthly day count/hash metadata')
    return proof


def load_daily(spec):
    """Market IO only in research; fixed period plus200 daily bars, no latest."""
    proof = daily_metadata(spec)
    fold = spec['folds'][0]
    start = date.fromisoformat(fold['period_start'])-timedelta(days=200)
    end = date.fromisoformat(fold['period_end_exclusive'])
    selected = [row for row in proof['sources'] if start.strftime('%Y-%m') <= row['month'] < end.strftime('%Y-%m')]
    frames, bindings = [], []
    for row in sorted(selected,key=lambda row:(row['month'],row['symbol'])):
        path = Path(row['normalized_path']).resolve()
        require(file_sha(path) == row['normalized_sha256'], 'Accepted daily bytes changed')
        frame = pl.read_parquet(path)
        require(frame.height == row['rows'] and frame['symbol'].eq(row['symbol']).all()
            and frame['interval'].eq('1d').all(), 'Accepted daily row/schema binding changed')
        frames.append(frame)
        bindings.append({key:row[key] for key in ('symbol','month','normalized_path','normalized_sha256','rows')})
    require(frames, 'Complete fixed daily warmup/scoring source required')
    frame = pl.concat(frames).sort(['symbol','open_us'])
    frame = frame.filter(pl.col('open_us').is_between(parent.old.day_us(start),parent.old.day_us(end),closed='left'))
    view = daily.daily_view(frame)
    expected = list(range(parent.old.day_us(start),parent.old.day_us(end),daily.DAY_US))
    require(view['daily_valid'].all() and all(view.filter(pl.col('symbol') == symbol)['open_us'].to_list() == expected
        for symbol in parent.old.SYMBOLS), 'Whole complete daily calendar and200-bar past warmup, no drop/fill')
    return frame, dict(source_receipt=spec['daily_source_receipt'],selected_sources=bindings,
        rows=frame.height,warmup_start=start.isoformat(),period_end_exclusive=end.isoformat(),
        complete_UTC_daily_calendar=True,publication_availability_certified=False,
        daily_prices_used_for_execution_or_risk=False)


def _changes(source_count):
    def change(node, changes):
        if node.name == 'comparison_plan':
            return parent.native._replace(node,changes,'D037_ONE_COST_COUNT',
                'planned = len(windows) * len(strategies) * 3','planned = len(windows) * len(strategies)')
        if node.name == 'period_aggregate':
            return parent.literal(node,changes,'D037_SPREAD8_AGGREGATE','(2,4,8)','(8,)',1)
        if node.name == 'verify_source_calendar' and source_count != 10:
            return parent.literal(node,changes,'D037_ACCEPTED_SOURCE_FILE_COUNT','10',str(source_count),2)
        if node.name in ('verify_sources','research'):
            node = parent.native._replace(node,changes,'D037_PRIVATE_NATIVE_DATE_ROUTE',
                'from scripts.investment import bybit_spot_adapter','bybit_spot_adapter = PERIOD_NATIVE')
        if node.name == 'research':
            if source_count != 10:
                node = parent.literal(node,changes,'D037_SOURCE_FILE_PROGRESS','10',str(source_count),3)
            node = parent.literal(node,changes,'D037_SPREAD8_ACCOUNT','(2,4,8)','(8,)',1)
            node = parent.native._replace(node,changes,'D037_READ_DAILY_SIGNAL_SOURCE_AFTER_EXISTING_GUARDS',
                'daily_reference = reference_daily_returns(fold_minutes)',
                'daily_reference = reference_daily_returns(fold_minutes)\ndaily_bars, daily_binding = load_daily(spec)\nfold_record["daily_signal_source"] = daily_binding')
            node = parent.native._replace(node,changes,'D037_ORIGINAL_HOOK_DAILY_TARGET_DISPATCH',
                'plan = bulk_fixed_targets.fixed_targets(strategy, closes, calendar, daily_returns=daily_reference if strategy == "VOL_MANAGED_BUY_AND_HOLD" else None)',
                'require(strategy == PERIOD_DAILY.STRATEGY_ID, "Only fixed daily strategy dispatch")\nplan = PERIOD_DAILY.fixed_targets(daily_bars, calendar)\nplan.receipt["daily_source_input_binding"] = daily_binding')
            return parent.native._replace(node,changes,'D037_ONE_COST_COMPLETION',
                'fold_record["status"] = "COMPLETE_PROXY_COMPARISON" if len(fold_record["results"]) == len(strategies) * 3 else "PARTIAL_INPUT_COVERAGE"',
                'fold_record["status"] = "COMPLETE_PROXY_COMPARISON" if len(fold_record["results"]) == len(strategies) else "PARTIAL_INPUT_COVERAGE"')
        if node.name == 'main':
            return parent.native._replace(node,changes,'D037_PRIVATE_NAMESPACE_RECEIPT',
                'progress = Progress()','report["period_namespace_derivation"] = PERIOD_DERIVATION\nprogress = Progress()')
        return node
    return change


def native_namespace(lower, end, receipt):
    """Same pinned received-asset entry, isolated date globals for each period."""
    return SimpleNamespace(**parent.namespace(parent.native,('run_backtest',),
        dict(BEGIN_US=parent.old.day_us(lower),END_US=parent.old.day_us(end)),receipt))

def context(spec):
    """Only accepted small metadata + exactAST; no market hash/array read."""
    require(file_sha(ROOT/'scripts/investment/public_long_development_adapter.py') == UTILITY_SHA, 'Pinned namespace utility')
    for path,digest in parent.PINS.items(): require(file_sha(ROOT/path) == digest, 'Pinned original module changed: '+path)
    require(len(spec['folds']) == 1 and spec['folds'][0]['id'] in PROFILES, 'One fixed existing scoring window')
    profile = PROFILES[spec['folds'][0]['id']]
    inherited = metadata(profile['protocol'],profile['protocol_sha256'])
    require(spec['namespace_parent_protocol'] == {'path':profile['protocol'],'sha256':profile['protocol_sha256']}, 'Exact original parent protocol')
    require(spec['folds'] == inherited['folds'] and spec['strategy_ids'] == [STRATEGY] and spec['planned_ledgers'] == 1,
        'Fixed original period, one daily strategy and36bp account')
    costs = deepcopy(inherited['costs']); costs.update(spread_bps=[8],nominal_roundtrip_bps=[36])
    require(spec['costs'] == costs and spec['strategy_rules'] == daily.RULES, 'Only timeframe changes; fixed native36bp costs and rules')
    for key in ('common_config','environment','fee_settlement','fee_profile_path','fee_profile_sha256','market_type',
            'source_receipt','source_receipt_sha256'):
        require(spec[key] == inherited[key], 'Original parent capital/risk/environment/fee/minute source: '+key)
    require(spec['source_scope'] == profile['scope'] and spec['source_calendar'] == profile['months']
        and spec['source_days_per_symbol'] == profile['days'] and spec['reused_minute_input'] == input_reference(profile),
        'Same exact minute source and accepted derivative, no sourceQA replay')
    require(not any(key in spec for key in ('reused_reference_report','reused_target_inputs')), 'No old accounts or targets replayed')
    require(type(spec['maximum_new_owned_bytes']) is int and 0 < spec['maximum_new_owned_bytes'] <= 400_000_000
        and type(spec['maximum_wall_seconds']) is int and 0 < spec['maximum_wall_seconds'] <= 1800,
        'Root-frozen output/wall budget before IO')
    daily_metadata(spec)
    fold = spec['folds'][0]
    lower = date.fromisoformat(fold['period_start'])-timedelta(days=31)
    end = date.fromisoformat(fold['period_end_exclusive'])
    receipt = []
    private_time = SimpleNamespace(**parent.namespace(parent.timeguard,('_integer_array','_timestamps','_stamp','_minute_decisions'),
        dict(BEGIN=parent.old.day_us(lower),END=parent.old.day_us(end)),receipt))
    private_v2 = SimpleNamespace(**parent.namespace(parent.v2,('calendar_array','_integer_timestamp_columns'),dict(_time=private_time),receipt))
    private_native = native_namespace(lower,end,receipt)
    source_status = parent.SOURCE_STATUS if profile['files'] == 38 else parent.old.SOURCE_SCOPES[profile['scope']][2]
    derived = dict(classification='D037_THREE_SEPARATE_SEEN_DAILY_PUBLIC_SCREENING_NOT_UNSEEN',
        period=fold['id'],accounts=1,timeframe_minutes=1440,warmup_daily_bars=200,risk_warmup_minutes_days=31,
        native_financial_kernel_AST_unchanged=True,original_public_hooks_unchanged=True,
        original_modules_or_globals_mutated=False,new_engine_or_account_loop_written=False,
        context_market_arrays_or_market_bytes_read=False,parent_protocol=spec['namespace_parent_protocol'],
        reused_minute_input=spec['reused_minute_input'],daily_source_receipt=spec['daily_source_receipt'],functions=receipt)
    environment = parent.namespace(parent.old,('source_scope','allowed_source_path','minute_view','signal_close_view',
        'comparison_plan','period_aggregate','verify_source_calendar','verify_sources','research','main'),
        dict(START=lower,LOCKED=end,SOURCE_SCOPES={profile['scope']:(tuple(profile['months']),profile['days'],source_status)},
        STRATEGIES=(STRATEGY,),benchmarks=private_v2,PERIOD_NATIVE=private_native,PERIOD_DAILY=daily,
        load_daily=load_daily,PERIOD_DERIVATION=derived),receipt,_changes(profile['files']))
    environment['verify_source_calendar'](spec,metadata(spec['source_receipt'],spec['source_receipt_sha256']))
    environment['__file__'] = str(Path(__file__).resolve())
    return environment


def protocol_template(identifier,daily_receipt_path,daily_receipt_sha256,smoke_receipt):
    """Small metadata proposal; ROOT caller freezes final source/test/budgets."""
    require(identifier in PROFILES, 'Only three preregistered seen scoring windows')
    profile = PROFILES[identifier]
    spec = deepcopy(metadata(profile['protocol'],profile['protocol_sha256']))
    for key in ('reused_reference_report','reused_reference_report_sha256','reused_target_inputs'):
        spec.pop(key,None)
    spec.update(strategy_ids=[STRATEGY],planned_ledgers=1,primary_reference=STRATEGY,
        strategy_rules=deepcopy(daily.RULES),namespace_parent_protocol={'path':profile['protocol'],'sha256':profile['protocol_sha256']},
        source_scope=profile['scope'],source_calendar=profile['months'],source_days_per_symbol=profile['days'],
        reused_minute_input=input_reference(profile),daily_source_receipt={'path':daily_receipt_path,
            'sha256':daily_receipt_sha256,'required_status':DAILY_STATUS},required_smoke_receipt=smoke_receipt,
        smoke_test_path='tests/test_public_donchian_daily.py',smoke_pytest_expression='test_daily_public_native_route',
        classification='SEEN_DEVELOPMENT_SCREENING_NOT_UNSEEN_OR_LONG_TERM_APR')
    spec['costs'].update(spread_bps=[8],nominal_roundtrip_bps=[36])
    # The ROOT freezer must replace inherited source pins with one shared current
    # union across all three children, bind the new daily source proof, and set
    # owned/wall budgets before execution. No inherited old target is accepted.
    spec['limitations'] = list(spec['limitations']) + [
        'Official daily close availability is an exclusive-close proxy; no actual publication certification.',
        'Daily signal data never supplies execution prices or minute risk; existing native-fee minute proxy account is reused.',
        'Three accounts begin fresh-flat and are not stitched into a common CAGR or an unseen validation.']
    return spec


def main():
    parser = argparse.ArgumentParser(add_help=False); parser.add_argument('--protocol',type=Path,required=True)
    args,_ = parser.parse_known_args()
    path = args.protocol.resolve()
    require(path.is_relative_to(ROOT/'protocols') and path.is_file() and path.stat().st_size < 2_000_000,
        'Exclusive frozen new ROOT protocol before execution')
    context(parent.old.read_json(path))['main']()

if __name__ == '__main__': main()
