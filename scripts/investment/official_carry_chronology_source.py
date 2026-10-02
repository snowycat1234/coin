"""Fixed 18 official archives via accepted download/format functions only.

Prepared without network or arrays. Metadata starts unknown; source acceptance
remains separate and requires a genuinely independent task.
"""
from __future__ import annotations
import argparse, ast, json, os, resource, shlex, subprocess, sys, time
from datetime import UTC, datetime
from pathlib import Path
import httpx
from quant import disk, resources
from quant.paths import ROOT, STATE
from scripts.research_v8 import funding_price_source_v2 as producer
from scripts.research_v8.registry import FIELDS, append_event

MONTHS = ['2025-12', '2026-01', '2026-02']
SYMBOLS = ['BTCUSDT', 'ETHUSDT']
KINDS = ['fundingRate', 'indexPriceKlines', 'markPriceKlines']
LIMIT = 200_000_000
PROVIDER = 'scripts/research_v8/funding_price_source_v2.py'
AUDITOR = 'scripts/research_v8/audit_funding_price_source.py'
META = 'docs/archive/V8_OFFICIAL_INPUT_METADATA_SOURCE_20261002_V1.py'
COMPONENT = 'reports/fast_research/V8_OFFICIAL_DOWNLOAD_COMPONENT_20261002_V2.json'
OLD_PROTOCOL = 'protocols/FUNDING_MARK_INDEX_SOURCE_V8_V1.json'
PINS = {PROVIDER:'2f39c9803051373654094ee990474b3ebe9b241ef85fa9eb586b9bde92bb4cdb',
    AUDITOR:'edf2b7e8f7f74e392c422a126ae11d3755f915d11984b50014aa44df54dcd79c',
    META:'d2e419dcbc05c3a1f71ee147a2ec5307ee49918106a206bc72cb3d19ea15aa5c',
    COMPONENT:'8a2ae22bd5bbf60763df352abb50d380763ba1fe19ac6545cc398f8d45d3ce96',
    OLD_PROTOCOL:'2b3ef722ba3276c95d4a658d63ecdae12d92ae7a4f95a88de2918a4fd775d38a'}
MANIFEST_SHA = '6f08e6cc8828c1f4247bcc03c90ea17699a43df91bf4c30f76e4389a08b6b34c'


def small_json(path, root, expected=None):
    original = Path(path)
    path = original.resolve()
    producer.require(path.is_relative_to(root.resolve()) and path.is_file() and not original.is_symlink()
                     and path.stat().st_size <= 2_000_000, 'Explicit small ordinary proof/manifest')
    producer.require(expected is None or producer.sha(path) == expected, 'Frozen small proof changed')
    return json.loads(path.read_bytes())


def metadata_inspector(client):
    """Reuse only three exact pinned functions; never run the old 224-object main."""
    source = ROOT / META
    producer.require(producer.sha(source) == PINS[META], 'Pinned metadata helper changed')
    tree = ast.parse(source.read_bytes())
    names = {'sha', 'access', 'inspect'}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    producer.require({node.name for node in nodes} == names and len(nodes) == 3, 'Exact metadata function set')
    namespace = dict(client=client, datetime=datetime, UTC=UTC, hashlib=__import__('hashlib'))
    exec(compile(ast.Module(body=nodes,type_ignores=[]), str(source)+':THREE_FUNCTIONS_ONLY', 'exec'), namespace)
    return namespace['inspect']


def validate(protocol, manifest):
    producer.require(protocol['contract_id'] == 'OFFICIAL_CARRY_CHRONOLOGY_SOURCE_V1'
        and protocol['period_start'] == '2025-12-01' and protocol['period_end_exclusive'] == '2026-03-01'
        and protocol['months'] == MONTHS and protocol['symbols'] == SYMBOLS and protocol['kinds'] == KINDS
        and protocol['expected_archives'] == 18 and protocol['maximum_new_owned_bytes'] == LIMIT
        and 0 < protocol['maximum_wall_seconds'] <= 1200, 'Fixed90day source-only budget/scope')
    producer.require(protocol['funding_events_expected'] is None and protocol['announced_zip_bytes_expected'] is None
        and protocol['funding_rate_unit_certified'] is False and protocol['economic_scope'] == 'NOT_EVALUATED',
        'No invented funding count, archive size or unit/economics certification')
    producer.require(protocol['runner_sha256'] == producer.sha(__file__)
        and protocol['manifest_sha256'] == MANIFEST_SHA, 'Frozen actual runner/static manifest')
    old = small_json(ROOT / OLD_PROTOCOL, ROOT, PINS[OLD_PROTOCOL])
    producer.require(protocol['funding_header'] == old['funding_header'] and protocol['price_header'] == old['price_header']
        and protocol['funding_nominal_interval_tolerance_ms'] == old['funding_nominal_interval_tolerance_ms'],
        'Reuse accepted headers and actual interval tolerance without retesting old formats')
    producer.require(manifest['contract_id'] == 'OFFICIAL_CARRY_CHRONOLOGY_18_URLS_V1'
        and manifest['months'] == MONTHS and manifest['symbols'] == SYMBOLS and manifest['kinds'] == KINDS
        and manifest['required_archives'] == 18 and manifest['maximum_new_owned_bytes'] == LIMIT
        and manifest['period_start'] == '2025-12-01' and manifest['period_end_exclusive'] == '2026-03-01'
        and manifest['compressed_bytes'] is None and manifest['funding_event_count'] is None,
        'Original static unknown manifest, not a substituted accepted source')
    entries = manifest['entries']
    producer.require(len(entries) == 18 and {(e['kind'],e['symbol'],e['month']) for e in entries} ==
        {(k,s,m) for k in KINDS for s in SYMBOLS for m in MONTHS}, 'Exactly18 unique official month archives')
    for entry in entries:
        suffix = f"{entry['symbol']}-{entry['kind']}-{entry['month']}.zip" if entry['kind'] == 'fundingRate' else f"1m/{entry['symbol']}-1m-{entry['month']}.zip"
        url = f"https://data.binance.vision/data/futures/um/monthly/{entry['kind']}/{entry['symbol']}/{suffix}"
        producer.require(entry['market'] == 'futures/um' and entry['partition'] == 'monthly'
            and entry['url'] == url and entry['checksum_url'] == url+'.CHECKSUM'
            and entry['metadata_object_available'] is None and entry['announced_zip_bytes'] is None
            and entry['announced_zip_sha256'] is None and entry['actual_source_rows'] is None,
            'Known authorized URL only; metadata and rows start unknown')
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('protocol','manifest','run-dir','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--experiment-id',required=True)
    args = parser.parse_args()
    run, output, protocol_path = args.run_dir.resolve(), args.output.resolve(), args.protocol.resolve()
    producer.require(run.is_relative_to(STATE.resolve()) and not run.exists()
        and output.is_relative_to((ROOT/'reports/fast_research').resolve()) and not output.exists()
        and os.environ.get('COIN_TASK_ID'), 'Exclusive D-hosted STATE/report and actual progress/bounded task')
    resources.status()
    producer.require(Path(sys.prefix).resolve() == STATE/'v8-clean-env-20261002-v2', 'Accepted shared CPU environment')
    protocol = small_json(protocol_path, ROOT)
    manifest_root = ROOT if args.manifest.resolve().is_relative_to(ROOT.resolve()) else STATE
    manifest = small_json(args.manifest, manifest_root, MANIFEST_SHA)
    entries = validate(protocol, manifest)
    for path, expected in PINS.items():
        producer.require(producer.sha(ROOT/path) == expected, 'Pinned existing component/protocol changed: '+path)
    hashes = {path:producer.sha(ROOT/path) for path in protocol['frozen_sources']}
    producer.require(hashes == protocol['frozen_sources'] and all(hashes.get(k) == v for k,v in PINS.items())
        and 'environments/v8/uv.lock' in hashes, 'Explicit unchanged sources/environment before network')
    component = small_json(ROOT/COMPONENT, ROOT, PINS[COMPONENT])
    producer.require(component['status'] == 'PINNED_OFFICIAL_DOWNLOAD_COMPONENT_STAGED_NO_MARKET_DATA'
        and component['commit'] == manifest['upstream_commit'] == 'f446ce3812bd4e5521f21faecd4ae3c6460e49fc',
        'Unmodified already staged official software, no new downloader dependency')
    run.mkdir()
    binding = dict(command=shlex.join([sys.executable,str(Path(__file__).resolve()),*sys.argv[1:]]),
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        protocol_path=str(protocol_path),protocol_sha256=producer.sha(protocol_path),manifest_path=str(args.manifest.resolve()),
        manifest_sha256=MANIFEST_SHA,source_path=str(Path(__file__).resolve()),source_sha256=producer.sha(__file__),
        source_hashes=hashes,task_id=os.environ['COIN_TASK_ID'],sys_prefix=sys.prefix,official_files=component['files'],
        scope='FIXED18_NEW_ARCHIVES_DEC2025_FEB2026_SOURCE_ONLY_NO_ECONOMICS')
    producer.write_new(run/'RUN_BINDING.json',binding)
    event = dict.fromkeys(FIELDS)
    event.update(experiment_id=args.experiment_id,event_id=args.experiment_id+':START',event_type='OPERATIONAL_SOURCE_START',
        git_commit=binding['git_commit'],data_manifest_hash=MANIFEST_SHA,protocol_hash=binding['protocol_sha256'],
        feature_set='NONE_SOURCE_ONLY',labels='NONE',model_family='NONE',hyperparameters=protocol,seed=None,
        thresholds={'archives':18,'owned_bytes':LIMIT},cost_assumptions='NOT_EVALUATED_UNCHANGED',all_folds='2025DEC_2026JAN_FEB_BTC_ETH',
        success_failure='START_BEFORE_NETWORK_ARRAYS',reason_for_next_experiment='Supply fixed90day unchanged carry chronology control',
        result_influenced_later_choice=False,source_hashes=hashes,exact_command=binding['command'],
        run_binding_sha256=producer.sha(run/'RUN_BINDING.json'))
    start = append_event(ROOT/'reports/experiment_registry.jsonl',event)
    result = dict(status='FAIL_NEW_OFFICIAL_CHRONOLOGY_SOURCE_UNACCEPTED',binding=binding,registration_start=start,
        required_files=18,metadata_completed_files=0,completed_files=0,sources=[],metadata=[],
        model_fits=0,orders_sent=0,GPU=0,locked_consumed=False,economic_eligibility=False,source_only=True,
        funding_unit_certified=False,carry_NAV_or_APR_computed=False,old_QA_or_green_tests_repeated=False,
        independent_audit_task_executed=False,archive_downloads_attempted=0,complete_archives=0,
        new_source_rows_read=False,declared_uncompressed_csv_bytes=0,actual_funding_events=None)
    progress = producer.progress_writer(18)
    started = time.monotonic()
    client = None
    try:
        progress.update('实际磁盘扫描，总量未知',None,None,'扫描')
        scan_started = datetime.now(UTC).isoformat()
        result['disk'] = dict(**disk.check(LIMIT),scan_started_utc=scan_started,measured_utc=datetime.now(UTC).isoformat())
        producer.require(result['disk']['total_bytes']+LIMIT <= 32_000_000_000, 'Expected32GB capacity guard')
        upstream = producer.official_module(component)
        client = httpx.Client(timeout=httpx.Timeout(12,connect=10),follow_redirects=False,
            headers={'User-Agent':'coin-fixed-chronology-source/1.0'})
        inspect = metadata_inspector(client)
        resolved = []
        for entry in entries:
            progress.update('官方HEAD/CHECKSUM，仅元数据',len(resolved),18,'文件',当前档案=entry['url'])
            checked = inspect(entry)
            name = f"{entry['kind']}-{entry['symbol']}-{entry['month']}"
            producer.write_new(run/('metadata-'+name+'.json'),checked)
            result['metadata'].append(dict(path=str(run/('metadata-'+name+'.json')),
                sha256=producer.sha(run/('metadata-'+name+'.json')),url=entry['url']))
            producer.require(checked['metadata_object_available'] and isinstance(checked['announced_zip_bytes'],int)
                and 0 < checked['announced_zip_bytes'] <= 2_000_000,
                'Missing/restricted/unknown/oversized official archive; stop, no alternate host or retry')
            resolved.append(checked);result['metadata_completed_files']=len(resolved)
            producer.require(time.monotonic()-started <= protocol['maximum_wall_seconds'], 'Source wall budget exceeded')
        result['announced_compressed_zip_bytes']=sum(e['announced_zip_bytes'] for e in resolved)
        producer.write_new(run/'RESOLVED_METADATA.json',dict(entries=resolved,archive_bodies_downloaded=False))
        result['resolved_metadata_sha256']=producer.sha(run/'RESOLVED_METADATA.json')
        converted = []
        for entry in resolved:
            name = f"{entry['kind']}-{entry['symbol']}-{entry['month']}"
            job=run/name;job.mkdir()
            receipt=dict(status='FAILED_ARCHIVE_SOURCE_UNACCEPTED',entry=entry,component_sha256=PINS[COMPONENT])
            try:
                progress.update('官方下载/转换',result['completed_files'],18,'文件',当前档案=name)
                result['archive_downloads_attempted']+=1
                archive,check,declared=producer.download_archive(entry,job,upstream)
                result['complete_archives']+=1;result['declared_uncompressed_csv_bytes']+=declared
                producer.require(result['declared_uncompressed_csv_bytes'] <= LIMIT and producer.owned_bytes(run) <= LIMIT,
                                 'New declared CSV/owned budget exceeds200MB; preserve partial sources')
                parquet=job/'source.parquet';result['new_source_rows_read']=True
                # Bound the sole new output before streaming conversion; reserve receipts/logs.
                remaining = LIMIT - producer.owned_bytes(run) - 5_000_000
                producer.require(remaining >= declared + 2_000_000, 'Conservative current CSV/output capacity')
                prior_limit = resource.getrlimit(resource.RLIMIT_FSIZE)
                prior_handler = producer.signal.signal(producer.signal.SIGXFSZ,
                    lambda _signal, _frame: (_ for _ in ()).throw(RuntimeError('New Parquet file bound exceeded; partial retained')))
                try:
                    resource.setrlimit(resource.RLIMIT_FSIZE, (remaining, prior_limit[1]))
                    stats=producer.convert_source(archive,entry,protocol,parquet)
                finally:
                    resource.setrlimit(resource.RLIMIT_FSIZE, prior_limit)
                    producer.signal.signal(producer.signal.SIGXFSZ, prior_handler)
                receipt.update(zip_path=str(archive),zip_sha256=producer.sha(archive),checksum_path=str(check),
                    checksum_sha256=producer.sha(check),zip_crc='PASS_FULL_READ',uncompressed_csv_bytes=declared,
                    stats=stats,parquet_path=str(parquet),parquet_sha256=producer.sha(parquet),parquet_bytes=parquet.stat().st_size,
                    status='SOURCE_FORMAT_QA_COMPLETE_PENDING_INDEPENDENT_QA')
                converted.append(dict(kind=entry['kind'],symbol=entry['symbol'],month=entry['month'],stats=stats))
                producer.require(producer.owned_bytes(run) <= LIMIT, 'New raw/Parquet footprint exceeds200MB')
            except Exception as error:
                receipt.update(error_type=type(error).__name__,reason=str(error));raise
            finally:
                producer.write_new(job/'receipt.json',receipt)
            result['sources'].append(dict(path=str(job/'receipt.json'),sha256=producer.sha(job/'receipt.json'),
                kind=entry['kind'],symbol=entry['symbol'],month=entry['month'],status=receipt['status']))
            result['completed_files']=len(result['sources'])
            progress.update('真实新来源格式已核验',result['completed_files'],18,'文件',新增字节=producer.owned_bytes(run))
            producer.require(time.monotonic()-started <= protocol['maximum_wall_seconds'], 'Source wall budget exceeded')
        result.update(status='OFFICIAL_CARRY_INPUT_FORMAT_QA_COMPLETE_PENDING_INDEPENDENT_QA',
            actual_funding_events=sum(q['stats']['rows'] for q in converted if q['kind']=='fundingRate'),
            actual_price_rows=sum(q['stats']['rows'] for q in converted if q['kind']!='fundingRate'),
            source_file_universe_unique=len({(q['kind'],q['symbol'],q['month']) for q in converted}),
            cross_month_reported_funding_intervals='PENDING_INDEPENDENT_QA_NO_ASSUMED8H',source_acceptance_granted=False)
        producer.require(hashes=={p:producer.sha(ROOT/p) for p in hashes} and producer.sha(__file__)==protocol['runner_sha256'],
                         'Frozen existing sources/new runner changed during task')
    except Exception as error:
        result.update(status='FAIL_NEW_OFFICIAL_CHRONOLOGY_SOURCE_UNACCEPTED',error_type=type(error).__name__,reason=str(error));raise
    finally:
        if client is not None:client.close()
        result.update(elapsed_seconds=time.monotonic()-started,created_utc=datetime.now(UTC).isoformat(),
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,resources=resources.status(),
            owned_bytes=producer.owned_bytes(run))
        if result['owned_bytes']+len(json.dumps(result,ensure_ascii=False).encode()) > LIMIT:
            result.update(status='FAIL_NEW_OFFICIAL_CHRONOLOGY_SOURCE_UNACCEPTED',reason='Final200MB owned+report budget exceeded')
        producer.write_new(output,result)
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=args.experiment_id+':RESULT',
            event_type='OPERATIONAL_SOURCE_RESULT',success_failure=result['status'],artifact_path=str(output.relative_to(ROOT)),
            artifact_sha256=producer.sha(output)))
        progress.stop.set();progress.thread.join(timeout=3)
    producer.require(result['status']=='OFFICIAL_CARRY_INPUT_FORMAT_QA_COMPLETE_PENDING_INDEPENDENT_QA', 'Failure preserved')
    print(json.dumps(dict(status=result['status'],completed_files=result['completed_files'],output=str(output),sha256=producer.sha(output))))


if __name__=='__main__':main()
