"""UNRUN D035: one unchanged VM account and one cost in either fixed period.

Only four cost/count AST anchors change in the pinned common runner. Dates,
source counts, original VM all-past EWMA, native finance and original Parquet
reuse/IO remain unchanged. context() reads small frozen metadata/code only.
"""
from __future__ import annotations
import argparse, json
from copy import deepcopy
from pathlib import Path
from quant.paths import ROOT, STATE
from scripts.investment import public_long_development_adapter as parent

STRATEGY = 'VOL_MANAGED_BUY_AND_HOLD'
VM_RULES = dict(VOL_MANAGED_BUY_AND_HOLD='Original .3/.3 gross reference basket, all available completed daily return prefix EWMA span7/min7 adjustFalse unbiased, same past seed and cap multiplier; original30day/min20 common risk retained',
    entry_and_capital='Original first intent and independent10k per period; no warmup cash or trades, no resets inside period',
    execution='Original minute latency/lot/previous-volume capacity and terminal marked remainder; native received-asset settlement unchanged',
    selection='Only fixed VM at36bp, no fitting/HPO/threshold change, no winner-month or account stitching')
PARENT_ADAPTER_SHA = '15ea3a089f39149d9d669fa3425fa35821c2c01b3cce1c15f751fd1723a9406f'
PROFILES = {
    'CONT122': dict(period='122D', days=122, source_scope='JUL_NOV_2025',
        source_calendar=['2025-07','2025-08','2025-09','2025-10','2025-11'], source_days=153,
        source_rows=440640, derivative_rows=440640,
        protocol='protocols/BYBIT_SPOT_2H_122D_V2.json',
        protocol_sha256='11a667b18ec6c3f779214c28fc0bcfe805319ee8b89e62097f6ee3aa52659192',
        report='reports/fast_research/BYBIT_SPOT_2H_122D_ACTUAL_20261002_V2.json',
        report_sha256='53447ac3722829cb5c4db12f5b469b100edb20c05bbb6e9c83f29bce5138bee3',
        source_receipt='reports/fast_research/V8_EXISTING_FROZEN_SPOT_MINUTE_SOURCE_REUSE_20261002_V1.json',
        source_receipt_sha256='a8b5389eced2ae4d9742d3e212e88562ca7bcc879990f3fa2b9632ebfdf1552e',
        input_dir='bybit-spot-2h-122d-actual-20261002-v2',
        input_sha256='116448ddf2f2705804aae8b4129515fcbecf5a4d3d3201b9bfd1793a684c5d38'),
    'CONT90': dict(period='90D', days=90, source_scope='OCT2025_FEB2026',
        source_calendar=['2025-10','2025-11','2025-12','2026-01','2026-02'], source_days=151,
        source_rows=434880, derivative_rows=348480,
        protocol='protocols/BYBIT_SPOT_2H_90D_V2.json',
        protocol_sha256='8505eec0f6406d7725962856455e3dfdbefda6139503f5e2d7856443383ca457',
        report='reports/fast_research/BYBIT_SPOT_2H_90D_ACTUAL_20261002_V2.json',
        report_sha256='329f9f923ed4fd8223e2e267a200c2e67036c8ce4f82a7fef0027efdd3b7960a',
        source_receipt='reports/fast_research/PUBLIC_STRATEGY_CHRONOLOGY_SOURCE_REUSE_20261002_V1.json',
        source_receipt_sha256='388d3be0611c038df2f955a88c5be822e17d6cbda5f265fdef101f6abe23d8a2',
        input_dir='bybit-spot-2h-90d-actual-20261002-v2',
        input_sha256='96adcfe79bb73f11bcdc924e83b43d51f6381c7b43977be90504f968b3bd0905'),
}

def require(ok, reason):
    if not ok: raise ValueError(reason)

def metadata(path, digest):
    path = ROOT / path
    require(path.is_file() and path.stat().st_size < 2_000_000
        and parent.native.file_sha(path) == digest, 'Exact bounded frozen metadata: ' + str(path))
    return json.loads(path.read_text())

def parent_metadata(identifier):
    require(identifier in PROFILES, 'Only CONT122 or CONT90 fixed input profile')
    profile = PROFILES[identifier]
    return metadata(profile['protocol'], profile['protocol_sha256'])

def input_reference(profile):
    return dict(report_path=profile['report'], report_sha256=profile['report_sha256'],
        path=str(STATE / profile['input_dir'] / 'shared_source_minutes.parquet'), sha256=profile['input_sha256'])

def validate(spec, inherited, identifier, profile):
    require(spec['namespace_parent_protocol'] == dict(path=profile['protocol'], sha256=profile['protocol_sha256']),
        'Exact accepted native parent metadata for this period')
    require(spec['strategy_ids'] == [STRATEGY] and spec['planned_ledgers'] == 1,
        'One original VM account and one fixed cost only')
    require(spec['folds'] == inherited['folds'] and spec['folds'][0]['id'] == identifier
        and spec['warmup_days'] == inherited['warmup_days'] == 31, 'Unchanged full period and31day warmup')
    for key in ('common_config','environment','fee_settlement','fee_profile_path',
        'fee_profile_sha256','market_type'):
        require(spec[key] == inherited[key], 'Unchanged original capital/risk/environment/fees: ' + key)
    require(spec['strategy_rules'] == VM_RULES, 'Explicit original VM rule metadata; no old public-target relabeling')
    costs = deepcopy(inherited['costs']); costs.update(spread_bps=[8], nominal_roundtrip_bps=[36])
    require(spec['costs'] == costs, 'Only existing conservative36bp scenario, all fee semantics unchanged')
    require(spec['source_receipt'] == inherited['source_receipt'] == profile['source_receipt']
        and spec['source_receipt_sha256'] == inherited['source_receipt_sha256'] == profile['source_receipt_sha256'],
        'Exact existing accepted source receipt')
    require(spec['source_scope'] == profile['source_scope']
        and spec['source_calendar'] == profile['source_calendar']
        and spec['source_days_per_symbol'] == profile['source_days'], 'Explicit existing whole source calendar')
    require(spec['reused_minute_input'] == input_reference(profile), 'Exact original four-field Parquet reuse')
    require(not any(key in spec for key in ('reused_reference_report','reused_reference_report_sha256','reused_target_inputs')),
        'No old accounts, targets or prices regenerated from normalized sources')
    require(type(spec['maximum_new_owned_bytes']) is int and 0 < spec['maximum_new_owned_bytes'] <= 150_000_000
        and type(spec['maximum_wall_seconds']) is int and 0 < spec['maximum_wall_seconds'] <= 1800,
        'Explicit root-frozen bounded output and wall budgets required')

def common_changes(node, changes):
    if node.name == 'comparison_plan':
        return parent.native._replace(node, changes, 'D035_ONE_COST_PLANNED_COUNT',
            'planned = len(windows) * len(strategies) * 3', 'planned = len(windows) * len(strategies)')
    if node.name == 'period_aggregate':
        return parent.literal(node, changes, 'D035_SPREAD8_ONLY_AGGREGATE', '(2,4,8)', '(8,)', 1)
    if node.name == 'research':
        node = parent.literal(node, changes, 'D035_SPREAD8_ONLY_ACTUAL_LOOP', '(2,4,8)', '(8,)', 1)
        return parent.native._replace(node, changes, 'D035_ONE_COST_FOLD_COMPLETION_COUNT',
            'fold_record["status"] = "COMPLETE_PROXY_COMPARISON" if len(fold_record["results"]) == len(strategies) * 3 else "PARTIAL_INPUT_COVERAGE"',
            'fold_record["status"] = "COMPLETE_PROXY_COMPARISON" if len(fold_record["results"]) == len(strategies) else "PARTIAL_INPUT_COVERAGE"')
    if node.name == 'main':
        return parent.native._replace(node, changes, 'D035_METADATA_DERIVATION_ONLY',
            'progress = Progress()', 'report["period_namespace_derivation"] = PERIOD_DERIVATION\nprogress = Progress()')
    return node

def context(spec):
    require(len(spec['folds']) == 1 and spec['folds'][0]['id'] in PROFILES, 'One separate fixed-period protocol')
    identifier = spec['folds'][0]['id']; profile = PROFILES[identifier]
    inherited = parent_metadata(identifier); validate(spec, inherited, identifier, profile)
    require(parent.native.file_sha(ROOT / 'scripts/investment/public_long_development_adapter.py') == PARENT_ADAPTER_SHA,
        'Pinned mature AST namespace utility')
    for path, digest in parent.PINS.items():
        require(parent.native.file_sha(ROOT / path) == digest, 'Pinned unchanged original module: ' + path)
    report = metadata(profile['report'], profile['report_sha256'])
    reference = input_reference(profile)
    require(report['status'] == 'COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING'
        and report['source_bytes_unchanged'] and report['all_planned_ledgers_complete']
        and report['source_receipt_sha256'] == profile['source_receipt_sha256']
        and report['minute_source']['path'] == reference['path']
        and report['minute_source']['sha256'] == reference['sha256']
        and report['minute_source']['rows'] == profile['derivative_rows']
        and report['minute_source']['invalid_minutes'] == 0, 'Exact accepted derivative metadata, no arrays reread')
    changes = []
    derivation = dict(classification='D035_FIXED_ORIGINAL_VM_TWO_SEPARATE_SEEN_DEVELOPMENT_PERIODS_NOT_UNSEEN',
        period=profile['period'], accounts=1, strategy_ids=[STRATEGY], fixed_spread_bps=[8],
        nominal_roundtrip_bps=[36], parent_protocol=deepcopy(spec['namespace_parent_protocol']),
        reused_minute_input=reference, source_rows=profile['source_rows'], derivative_rows=profile['derivative_rows'],
        days=profile['days'], warmup_days=31, functions=changes,
        original_date_source_counts_targets_native_finance_and_IO_unchanged=True,
        EWMA_scope='ALL_AVAILABLE_COMPLETED_DAILY_GROSS_REFERENCE_RETURNS_SPAN7_MIN7_NOT_LAST7_ONLY',
        same_risk_rules_not_equal_realized_risk=True, old_accounts_replayed=False,
        original_modules_or_globals_mutated=False, source_acceptance_or_market_IO_performed_by_context=False,
        long_term_APR_or_native_execution_qualification=False)
    # Source validators need the same private planned=1 globals. Their ASTs
    # themselves are unchanged; ten-file receipt counts and date guards stay.
    environment = parent.namespace(parent.old,
        ('comparison_plan','period_aggregate','verify_source_calendar','verify_sources','research','main'),
        dict(STRATEGIES=(STRATEGY,), PERIOD_DERIVATION=derivation), changes, common_changes)
    source = metadata(profile['source_receipt'], profile['source_receipt_sha256'])
    environment['verify_source_calendar'](spec, source)
    environment['__file__'] = str(Path(__file__).resolve())
    return environment

def main():
    parser = argparse.ArgumentParser(add_help=False); parser.add_argument('--protocol', type=Path, required=True)
    args, _ = parser.parse_known_args(); path = args.protocol.resolve()
    require(path.is_relative_to(ROOT / 'protocols') and path.is_file() and path.stat().st_size < 2_000_000,
        'Exclusive new frozen ROOT D035 protocol required before execution')
    context(json.loads(path.read_text()))['main']()

if __name__ == '__main__': main()
