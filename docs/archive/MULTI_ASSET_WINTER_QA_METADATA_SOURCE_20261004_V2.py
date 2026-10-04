"""Bind the completed winter source to the metadata-corrected independent QA."""
from datetime import UTC, datetime
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
HEAD = '1f40239706162eb92daa8a1e2fa0abb9b59299ed'
SOURCE = 'reports/fast_research/MULTI_ASSET_WINTER_MARKET_SOURCE_20261004_V1.json'
SOURCE_SHA = 'c288226323a65d1da041a62d1f204417f88a1d50c0cc1648fda19c2dfd68a17e'
SOURCE_PROTOCOL = 'protocols/MULTI_ASSET_WINTER_MARKET_SOURCE_20261004_V1.json'
SOURCE_PROTOCOL_SHA = '0764b3678d66944230eca555962ce3b891e8e2ad9887bb00ed50bc18aac9733e'
SOURCE_TASK = 'b0aaad827c564304a52b2826d81caa6c'
SOURCE_TASK_ARCHIVE = 'docs/archive/MULTI_ASSET_WINTER_SOURCE_ACTUAL_TASK_20261004_V1.json'
SOURCE_TASK_SHA = 'dbc41baf7ee61facb7ef810c819202edfad874e0fd66e6b6d01d7895a24f3cbf'
SOURCE_RB_SHA = '725cbf19f164d40e7f52920e3b1987db1d676acc02903b6ea1eb22754ceb6eb8'
ARCHIVE = 'docs/archive/MULTI_ASSET_WINTER_QA_METADATA_SOURCE_20261004_V2.py'
QA = 'scripts/investment/multi_asset_source_acceptance.py'
QA_SHA = '9479b0862d13c53ef66bc2852c0e939ef523bfc49f5fd410b69cecea47cfe35a'
FAILED_SOURCE = 'docs/archive/MULTI_ASSET_WINTER_SOURCE_ACCEPTANCE_FAILED_SOURCE_20261004_V1.py'
FAILED_REPORT = 'reports/fast_research/MULTI_ASSET_WINTER_SOURCE_ACCEPTANCE_20261004_V1.json'
FAILED_TASK = 'docs/archive/MULTI_ASSET_WINTER_SOURCE_ACCEPTANCE_FAILED_TASK_20261004_V1.json'
EXTRA_PINS = {
    QA: QA_SHA,
    'docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py':
        '278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a',
    'scripts/research_v8/audit_funding_price_source.py':
        'edf2b7e8f7f74e392c422a126ae11d3755f915d11984b50014aa44df54dcd79c',
    'scripts/investment/audit_perpetual_trade_source.py':
        '7770342534d216b121d42da3c541874bb7c175fcd3b10c9939337417760e8e92',
    SOURCE: SOURCE_SHA, SOURCE_PROTOCOL: SOURCE_PROTOCOL_SHA,
    SOURCE_TASK_ARCHIVE: SOURCE_TASK_SHA,
    FAILED_SOURCE: '7e661f95ee97e533e6788541b115f2e699171ad4d70813a4d4212424cdb8cc7e',
    FAILED_REPORT: '771959930353bcc39b97007a0bd100c51d45058f1613f9dfb17cb8b1fe4a3344',
    FAILED_TASK: '3f60df7a40c9e96c12cb56c19b9560fd708a696ab96d030439fb2ab775e9657d',
    'protocols/MULTI_ASSET_WINTER_SOURCE_ACCEPTANCE_20261004_V1.json':
        'f038ee6930843c3199976b1254d74d38e850b396496f1e0b730e57a30a69e437',
    'docs/archive/MULTI_ASSET_WINTER_QA_METADATA_SOURCE_20261004_V1.py':
        'fdec9c84d73c2a8d57fd94a5776174cd92a441796ba3d9c5d9ba2338146d41b0',
    'reports/fast_research/MULTI_ASSET_WINTER_QA_METADATA_20261004_V1.json':
        '66f90a350d982d72ddec04b4a40473540203d3d8962c8bc7204756fc557173d2',
    'reports/fast_research/MULTI_ASSET_WINTER_SOURCE_ACCEPTANCE_STARTUP_FAILURE_20261004_V1.json':
        '447714e0419fe507644556fb1ae8a5176ed7e7a898c67c462a932d73e0f36def',
    'docs/archive/MULTI_ASSET_WINTER_SOURCE_ACCEPTANCE_STARTUP_FAILURE_TASK_20261004_V1.json':
        'e79133bef7c4a45edf31ce00ebdae3003af997ca0bb5a81244184c0942880b09',
}


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path, digest, limit=2_000_000):
    path = Path(path)
    need(not path.is_symlink() and path.is_file() and 0 < path.stat().st_size <= limit,
         'Small ordinary metadata '+str(path))
    need(sha(path) == digest, 'Exact metadata identity '+str(path))
    return json.loads(path.read_bytes())


def write(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def main():
    need(os.environ.get('COIN_TASK_ID') and sys.prefix == str(STATE/'v8-clean-env-20261002-v2'),
         'Actual bounded clean metadata task')
    need(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == HEAD,
         'Exact D055 accepted HEAD before D056 QA preparation')
    source = read(ROOT/SOURCE, SOURCE_SHA, 4_000_000)
    producer = read(ROOT/SOURCE_PROTOCOL, SOURCE_PROTOCOL_SHA)
    task_path = STATE/'task-progress'/('task-'+SOURCE_TASK+'.json')
    task = read(task_path, SOURCE_TASK_SHA)
    need(read(ROOT/SOURCE_TASK_ARCHIVE, SOURCE_TASK_SHA) == task and task['id'] == SOURCE_TASK
         and task['status'] == 'completed' and type(task['exit_code']) is int and task['exit_code'] == 0
         and all(type(task[k]) in (int, float) and math.isfinite(task[k]) for k in ('started_at', 'ended_at'))
         and task['ended_at'] >= task['started_at'], 'Actual closed0 source task and exact archived bytes')
    source_run = STATE/'d056-multiasset-winter-source-20261004-v1'
    rb = read(source_run/'RUN_BINDING.json', SOURCE_RB_SHA)
    need(source['run_dir'] == str(source_run) and source['run_binding_sha256'] == SOURCE_RB_SHA
         and source['binding'] == rb and rb['task_id'] == SOURCE_TASK
         and Path(rb['protocol_path']).resolve() == (ROOT/SOURCE_PROTOCOL).resolve()
         and rb['protocol_sha256'] == SOURCE_PROTOCOL_SHA and rb['git_commit'] == HEAD
         and rb['source_hashes'] == producer['source_hashes'], 'Source report/protocol/RUN_BINDING/task agree')
    need(source['status'] == 'COMPLETE_D056_FIXED_POOL_WINTER_SOURCE_FORMAT_PENDING_ACCEPTANCE'
         and source['actual_exit_code'] == 0 and source['source_bytes_unchanged'] is True
         and source['source_only'] is True and source['model_fits'] == source['orders_sent'] == source['GPU'] == 0
         and source['locked_consumed'] is False and source['funding_unit_certified'] is False
         and source['native_Bybit_certified'] is False and producer['ready_for_execution'] is True
         and producer['capacity_registered'] is True, 'Completed source-only gate; no QA or unit certification yet')
    need((source['start_us'], source['end_us'], source['days']) ==
         (1733011200000000, 1740787200000000, 90)
         and source['score_months'] == producer['score_months'] == ['2024-12', '2025-01', '2025-02']
         and source['new_market_files'] == producer['new_market_files'] == 72
         and source['reused_market_files'] == producer['reused_market_files'] == 18
         and len(source['market_records']) == source['completed_source_files'] == 90
         and len(source['daily_records']) == 70 and len(source['warmup_minute_records']) == 30
         and len(source['control_daily_records']) == 14, 'Exact quarter and prospective 72new/18old/100warm scope')
    pins = dict(producer['source_hashes'])
    need(pins['scripts/investment/multi_asset_data.py'] == rb['source_sha256'] ==
         'dccf64472a8ec27cc34e03a3c8a8fba91231aac00df6c1dd97fb644fc8ec3e9c'
         and pins['scripts/investment/multi_asset_official_transport.ps1'] ==
         '8e2c38a2f67558d9bc11f2d71ec71805aed060bb235e9265f9bda602a874a7be', 'Actually consumed production source identities')
    warm_ref = producer['warmup_manifest']
    need(warm_ref == source['warmup_manifest'] and warm_ref['sha256'] ==
         '847d8a6e561d782ae641d492697ee03fd7b3ba2eda65298e5d0f02cb0c7b1e50', 'Original D055 warm composite identity')
    warm = read(warm_ref['path'], warm_ref['sha256'])
    need(warm['status'] == warm_ref['required_status'] == 'PASS_D055_CONTINUOUS_91D_ACCEPTED_SOURCE_BINDING_NOT_ECONOMICS'
         and warm['monthly_acceptances'] == producer['warmup_source_acceptances'] == source['warmup_source_acceptances']
         and warm['daily_records'] == source['daily_records'] and warm['control_daily_records'] == source['control_daily_records']
         and [r for r in warm['market_records'] if r['kind'] == 'klines'] == source['warmup_minute_records']
         and warm['pool_receipt'] == producer['pool_receipt'] == source['pool_receipt'], 'Unchanged source descriptors and fixed July pool')
    for ref in warm['monthly_acceptances']:
        path = (ROOT/Path(ref['path'])).resolve()
        cap = read(path, ref['sha256'])
        need(cap['status'] == ref['required_status'] and cap['actual_exit_code'] == 0 and cap['source_only'] is True,
             'Original actually accepted warm capability')
        identity = cap['binding']['task_id']; p = STATE/'task-progress'/('task-'+identity+'.json')
        t = read(p, sha(p))
        need(t['id'] == identity and t['status'] == 'completed' and type(t['exit_code']) is int and t['exit_code'] == 0,
             'Warm source capability truly closed0')
        pins[path.relative_to(ROOT).as_posix()] = ref['sha256']
    pins.update(EXTRA_PINS); pins[ARCHIVE] = sha(__file__)
    for name, digest in pins.items():
        path = ROOT/name
        need(name != 'state/dataset_lock.json' and not Path(name).is_absolute() and '..' not in Path(name).parts
             and not path.is_symlink() and sha(path) == digest, 'Current exact public source '+name)
    need(sha(ROOT/'state/dataset_lock.json') == '29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d',
         'Private policy hash only; excluded from public source map')
    failed = read(ROOT/FAILED_REPORT, EXTRA_PINS[FAILED_REPORT])
    failed_task = read(ROOT/FAILED_TASK, EXTRA_PINS[FAILED_TASK])
    need(failed['status'] == 'FAIL_D056_FIXED_POOL_WINTER_SOURCE_ACCEPTANCE'
         and failed['actual_exit_code'] == 1 and failed['sources'] == [] and failed['reason'] == "'status'"
         and failed['error_type'] == 'KeyError' and failed['binding']['checker_sha256'] == EXTRA_PINS[FAILED_SOURCE]
         and failed['binding']['task_id'] == failed_task['id'] == 'faae23f4c0404115a864b1a087b25902'
         and failed_task['status'] == 'failed' and type(failed_task['exit_code']) is int and failed_task['exit_code'] == 1,
         'Preserved actual metadata failure, without a fabricated passed prefix')
    failed_rb = read(Path(failed['run_dir'])/'RUN_BINDING.json', failed['run_binding_sha256'])
    need(failed_rb == failed['binding'], 'Preserved failed task actual RUN_BINDING')
    run = STATE/'d056-multiasset-winter-source-acceptance-20261004-v2'
    protocol_path = ROOT/'protocols/MULTI_ASSET_WINTER_SOURCE_ACCEPTANCE_20261004_V2.json'
    output = 'reports/fast_research/MULTI_ASSET_WINTER_SOURCE_ACCEPTANCE_20261004_V2.json'
    metadata = ROOT/'reports/fast_research/MULTI_ASSET_WINTER_QA_METADATA_20261004_V2.json'
    need(not run.exists() and not protocol_path.exists() and not (ROOT/output).exists() and not metadata.exists(),
         'Single new prospective QA identity; no existing outputs overwritten')
    spec = dict(contract_id='D056_FIXED_POOL_WINTER_SOURCE_FORMAT_ACCEPTANCE_V1',
        experiment_id='d056-winter-source-independent-20261004-v2', ready_to_execute=True,
        source_month='2024-12_2025-02', score_months=source['score_months'], days=90,
        start_us=source['start_us'], end_us=source['end_us'], frozen_sources=pins,
        market_receipt=dict(path=SOURCE, sha256=SOURCE_SHA, required_status=source['status']),
        pool_receipt=producer['pool_receipt'], prior_manifest=warm_ref,
        prior_acceptances=warm['monthly_acceptances'], reuse_manifest=producer['reuse_manifest'],
        run_dir=str(run), output_path=output, manifest_path=str(run/'INPUT_MANIFEST.json'),
        budgets=dict(new_owned_bytes=5_000_000, peak_RSS_bytes=1_000_000_000, wall_seconds=1200),
        source_only=True, new_source_QA_files=72, old_market_metadata_reuses=18,
        prior_warmup_daily_files=70, prior_warmup_minute_files=30,
        old_warmup_rows_CRC_QA_repeated=False, funding_rate_unit='UNCONFIRMED',
        funding_unit_certified=False, native_Bybit_certified=False, publication_time_certified=False,
        source_actual_task=dict(path=SOURCE_TASK_ARCHIVE, sha256=SOURCE_TASK_SHA, task_id=SOURCE_TASK),
        source_run_binding=dict(path=str(source_run/'RUN_BINDING.json'), sha256=SOURCE_RB_SHA),
        source_host=dict(session=49285, chunk='699414', exit_code=0),
        child_environment=dict(producer['child_environment']),
        preserved_metadata_failure=dict(report=dict(path=FAILED_REPORT, sha256=EXTRA_PINS[FAILED_REPORT]),
            task=dict(path=FAILED_TASK, sha256=EXTRA_PINS[FAILED_TASK], task_id=failed_task['id'], exit_code=1),
            source=dict(path=FAILED_SOURCE, sha256=EXTRA_PINS[FAILED_SOURCE]),
            run_binding=dict(path=str(Path(failed['run_dir'])/'RUN_BINDING.json'), sha256=failed['run_binding_sha256']),
            host=dict(session=91357, chunk='65fd1e', exit_code=1), sources_completed=0),
        repair_scope='OLD_ROW_STATUS_NULL_RETAINED_AND_ORIGINAL_QA_SCOPE_METADATA_ONLY_NO_PARSER_TOLERANCE_OR_UNIT_CHANGE',
        historical_failure_pins_scope='ALREADY_CONSUMED_PRODUCER_DEPENDENCIES_ONLY_NOT_D056_FAILURE_ROLES',
        metadata_source=dict(path=ARCHIVE, sha256=sha(__file__)), created_utc=datetime.now(UTC).isoformat())
    need(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == HEAD
         and all(sha(ROOT/p) == h for p, h in pins.items()), 'HEAD and public bytes unchanged at protocol freeze')
    write(protocol_path, spec)
    result = dict(status='READY_D056_WINTER_QA_PROTOCOL_SOURCE_CLOSED0_QA_NOT_RUN',
        task_id=os.environ['COIN_TASK_ID'], own_completion='LIVE_CALLER_NOT_SELF_CERTIFIED',
        protocol=dict(path=str(protocol_path.relative_to(ROOT)), sha256=sha(protocol_path)),
        frozen_sources=pins, source_actual_task=spec['source_actual_task'], source_run_binding=spec['source_run_binding'],
        source_host=spec['source_host'], new_source_QA_files=72, old_market_metadata_reuses=18, old_warm_sources=100,
        preserved_metadata_failure=spec['preserved_metadata_failure'], repair_scope=spec['repair_scope'],
        payloads_read=0, QA_calls=0, financial_calls=0, market_accounts=0, models_fit=0,
        locked_consumed=False, source_acceptance_granted=False, metadata_source=spec['metadata_source'])
    write(metadata, result)
    print(json.dumps(dict(status=result['status'], protocol=str(protocol_path), sha256=sha(protocol_path))))


if __name__ == '__main__':
    main()
