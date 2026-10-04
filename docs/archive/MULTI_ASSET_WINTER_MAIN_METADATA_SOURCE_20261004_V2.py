"""Metadata only: bind closed winter QA and freeze the three unchanged HOLD recipes."""
import argparse
import copy
from datetime import UTC, datetime
import hashlib
import json
import math
import os
from pathlib import Path
import sys

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
SUFFIX = '_20261004_V1.json'
RECIPES = ('TWO_CONTROL', 'TEN_EQUAL', 'TEN_INVERSE')
PARENTS = (
    'd8428231f6e30e7337cafa69daa669f3d1c52df99197e7020ca93e0479d4619c',
    '25fdf0ab7ae6fe1cfd1a01f13800b3360146748d4bfc23395c6c6485428384c9',
    '1b0d09eea4d807ddb09cc6163806900fb0232976b4db0896a99136cbf6937e57',
)
UPDATED = {
    'scripts/investment/multi_asset_data.py': 'dccf64472a8ec27cc34e03a3c8a8fba91231aac00df6c1dd97fb644fc8ec3e9c',
    'scripts/investment/multi_asset_portfolio.py': '47a1a456e715f6884ddf9164a2d4cce272ea1c94a6388888d4e56b38deaf8c49',
}
CHECKER = '0d77b4b0bbb6bbb970d5ea6d101efd24ab863e00fb0c3cf37547e39248388bc1'
COMPARER = '04ee429f9e33dbcbfbb1210d9556edfd2aeb526878855931c010c708bc4fd68a'
QA_PATH = ROOT/'reports/fast_research/MULTI_ASSET_WINTER_SOURCE_ACCEPTANCE_20261004_V2.json'
QA_RUN = STATE/'d056-multiasset-winter-source-acceptance-20261004-v2'
QA_STATUS = 'PASS_D056_FIXED_POOL_WINTER_SOURCE_FORMAT_ONLY'
MANIFEST_STATUS = 'PASS_D056_SELECTED_PORTFOLIO_WINTER_SOURCE_BINDING_NOT_ECONOMICS'
BOUNDS = (1733011200000000, 1740787200000000)
MONTHS = ['2024-12', '2025-01', '2025-02']


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path, digest=None):
    path = Path(path)
    need(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= 2_000_000,
         'Small ordinary metadata: '+str(path))
    if digest is not None:
        need(sha(path) == digest, 'Exact metadata SHA: '+str(path))
    return json.loads(path.read_bytes())


def write(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qa-sha256', required=True)
    parser.add_argument('--qa-task-id', required=True)
    parser.add_argument('--qa-host-session', type=int, required=True)
    parser.add_argument('--qa-host-chunk', required=True)
    args = parser.parse_args()
    need(os.environ.get('COIN_TASK_ID') and sys.prefix == str(STATE/'v8-clean-env-20261002-v2'),
         'Actual bounded clean metadata task')
    qa = read(QA_PATH, args.qa_sha256)
    need(qa['status'] == QA_STATUS and qa['actual_exit_code'] == 0 and qa['source_only'] is True
         and qa['binding']['task_id'] == args.qa_task_id and qa['run_dir'] == str(QA_RUN)
         and qa['binding']['checker_sha256'] == sha(ROOT/'scripts/investment/multi_asset_source_acceptance.py')
         and qa['funding_unit_certified'] is False and qa['native_Bybit_certified'] is False
         and qa['publication_time_certified'] is False and qa['locked_consumed'] is False,
         'Actual completed format-only QA identity; no financial or native certification')
    task_path = STATE/'task-progress'/('task-'+args.qa_task_id+'.json')
    task = read(task_path)
    need(task['id'] == args.qa_task_id and task['status'] == 'completed' and type(task['exit_code']) is int
         and task['exit_code'] == 0 and all(type(task[k]) in (int, float) and math.isfinite(task[k])
         for k in ('started_at', 'ended_at')) and task['ended_at'] >= task['started_at'],
         'QA must truly be closed0 before main protocols')
    rb_path = QA_RUN/'RUN_BINDING.json'
    need(read(rb_path, qa['run_binding_sha256']) == qa['binding'], 'Actual QA RUN_BINDING')
    qa_protocol = Path(qa['binding']['protocol_path']).resolve()
    need(qa_protocol == ROOT/'protocols/MULTI_ASSET_WINTER_SOURCE_ACCEPTANCE_20261004_V2.json',
         'Fixed winter QA protocol')
    qa_spec = read(qa_protocol, qa['binding']['protocol_sha256'])
    need(qa['binding']['source_hashes'] == qa_spec['frozen_sources'], 'QA consumed the frozen source map')
    for name, digest in qa_spec['frozen_sources'].items():
        need(not Path(name).is_absolute() and '..' not in Path(name).parts and name != 'state/dataset_lock.json'
             and sha(ROOT/name) == digest, 'Consumed QA public source unchanged: '+name)
    manifest_path = QA_RUN/'INPUT_MANIFEST.json'
    manifest_digest = sha(manifest_path)
    manifest = read(manifest_path, manifest_digest)
    ref = manifest['source_acceptance']
    need(manifest['status'] == MANIFEST_STATUS and Path(ref['path']).resolve() == QA_PATH
         and ref['sha256'] == args.qa_sha256 and ref['required_status'] == QA_STATUS
         and manifest['source_only'] is True and manifest['checksummed_source_format_verified'] is True
         and (manifest['start_us'], manifest['end_us']) == BOUNDS
         and manifest['days'] == qa['days'] == 90 and manifest['score_months'] == qa['score_months'] == MONTHS
         and (qa['start_us'], qa['end_us']) == BOUNDS
         and qa['completed_files'] == len(qa['sources']) == len(qa['normalized_source_hashes']) == 90
         and qa['newly_verified_files'] == 72 and qa['reused_accepted_files'] == 18
         and len(manifest['market_records']) == 90 and len(manifest['daily_records']) == 70
         and len(manifest['warmup_minute_records']) == 30 and len(manifest['control_daily_records']) == 14
         and len(manifest['normalized_source_hashes']) == 190,
         'Exact accepted winter90/72new/18old/100warm metadata scope')
    score_pins = {r['normalized_path']: r['normalized_sha256'] for r in manifest['market_records']}
    need(len(score_pins) == 90 and score_pins == qa['normalized_source_hashes']
         and all(manifest['normalized_source_hashes'].get(p) == h for p, h in score_pins.items())
         and manifest['warmup_manifest'] == qa['warmup_manifest']
         and manifest['warmup_source_acceptances'] == qa['warmup_source_acceptances'],
         'Manifest score and historical warm capability identities; no payload reread')
    need(sha(ROOT/'scripts/investment/multi_asset_financial_audit.py') == CHECKER
         and sha(ROOT/'scripts/investment/compare_multi_asset_portfolios.py') == COMPARER,
         'Current independent/comparison sources pinned before new accounts')
    outputs = {r: ROOT/('protocols/MULTI_ASSET_WINTER_'+r+SUFFIX) for r in RECIPES}
    report_path = ROOT/('reports/fast_research/MULTI_ASSET_WINTER_INPUT_BINDING'+SUFFIX)
    need(not report_path.exists() and all(not p.exists() for p in outputs.values()), 'Exclusive new outputs')
    prepared = {}
    for recipe, digest in zip(RECIPES, PARENTS):
        parent_path = ROOT/('protocols/MULTI_ASSET_CONTINUOUS_91D_'+recipe+SUFFIX)
        parent = read(parent_path, digest)
        need((ROOT/Path(parent['pool_receipt']['path'])).resolve() == (ROOT/Path(manifest['pool_receipt']['path'])).resolve() and parent['pool_receipt']['sha256'] == manifest['pool_receipt']['sha256'] and parent['initial_capital_USDT'] == 10000,
             'Same July pool and full capital')
        need(parent['pools'][1]['symbols'] == manifest['selected_symbols'], 'Same ordered ten-member identity')
        pins = {name: UPDATED.get(name, old) for name, old in parent['source_hashes'].items()}
        need(len(pins) == 14 and set(UPDATED).issubset(pins), 'Original finite14 source dependencies')
        for name, expected in pins.items():
            need(name != 'state/dataset_lock.json' and sha(ROOT/name) == expected, 'Current unchanged source: '+name)
        spec = copy.deepcopy(parent)
        spec.update(experiment_id='D056-WINTER-90D-'+recipe+'-20261004',
            start='2024-12-01T00:00:00+00:00', end_exclusive='2025-03-01T00:00:00+00:00', period_days=90,
            account_path='CONTINUOUS_SHARED_ACCOUNT_DEC_FEB_90D',
            data_role='SEEN_DEVELOPMENT_CONTINUOUS_NEXT_QUARTER_MANIFEST',
            data_role_note='One fresh full10k wallet for the complete winter quarter; no month reset or NAV stitching.',
            warmup='Accepted Feb-Aug70 daily and Sep-Nov30 minute sources reduced causally; no repeated source QA.',
            data_manifest=dict(path=str(manifest_path), sha256=manifest_digest), source_hashes=pins,
            source_acceptances=[ref, *manifest['warmup_source_acceptances']],
            independent_reference_pre_market_sha256=CHECKER, economic_comparer_pre_market_sha256=COMPARER,
            budget=dict(owned_bytes=100_000_000 if recipe == 'TWO_CONTROL' else 250_000_000,
                        wall_seconds=1800, peak_RSS_bytes=3_000_000_000),
            question='Do unchanged July-pool HOLD allocations retain money/risk quality in the complete next winter quarter?',
            created_utc=datetime.now(UTC).isoformat())
        prepared[recipe] = spec
    # All three parents and source bytes pass before the first exclusive protocol write.
    protocols = {}
    for recipe, spec in prepared.items():
        write(outputs[recipe], spec)
        protocols[recipe] = dict(path=outputs[recipe].relative_to(ROOT).as_posix(), sha256=sha(outputs[recipe]),
            run_dir=str(STATE/('d056-winter-'+recipe.lower().replace('_', '-')+'-20261004-v1')),
            output_path='reports/fast_research/MULTI_ASSET_WINTER_'+recipe+SUFFIX,
            pool_id='TWO_ASSET' if recipe == 'TWO_CONTROL' else 'LIQUIDITY_TEN')
    result = dict(status='BOUND_ACCEPTED_WINTER90_SOURCE_FOR_THREE_UNCHANGED_HOLD_RECIPES_NOT_MARKET_RESULTS',
        task_id=os.environ['COIN_TASK_ID'], own_completion='LIVE_CALLER_NOT_SELF_CERTIFIED',
        metadata_source_sha256=sha(__file__), qa=dict(path=QA_PATH.relative_to(ROOT).as_posix(), sha256=args.qa_sha256),
        qa_closed_task=dict(path=str(task_path), sha256=sha(task_path), task=task),
        qa_host=dict(session=args.qa_host_session, chunk=args.qa_host_chunk, exit_code=0),
        qa_run_binding=dict(path=str(rb_path), sha256=sha(rb_path)),
        manifest=dict(path=str(manifest_path), sha256=manifest_digest), protocols=protocols,
        new_downloads=0, new_source_QA=0, financial_calls=0, new_market_accounts=0, models_fit=0,
        funding_unit_certified=False, native_Bybit_certified=False, locked_consumed=False)
    write(report_path, result)
    print(json.dumps(dict(status=result['status'], report_path=str(report_path), report_sha256=sha(report_path),
                         protocols=protocols)))


if __name__ == '__main__':
    main()
