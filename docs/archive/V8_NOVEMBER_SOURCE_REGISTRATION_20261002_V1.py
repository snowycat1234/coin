"""Seal exact metadata-only source commands before append-only operational start."""
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from quant.paths import ROOT, STATE
from quant.research_fast.dataset import file_sha

sys.path.insert(0, str(ROOT))
from scripts.research_v8.registry import FIELDS, append_event, canonical, read_verified

def proof(path, purpose):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': file_sha(path), 'bytes': path.stat().st_size, 'purpose': purpose}

def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)

metadata_path = ROOT/'reports/fast_research/V8_P1_FOUR_FOLD_SOURCE_OPTIONS_20261002_V1.json'
view_path = ROOT/'reports/fast_research/V7_SHARED_SOURCE_VIEW_123D_20261002_V1.json'
assert file_sha(view_path) == '32a71b6018a00b2bcfca1d198661be59c0889049606c19774a5dd141d9aedf51'
assert file_sha(metadata_path) == '15ea64b8ae33d751b48948f97c91bc78445772b3b15181d4d0db03b228fe915d'
metadata = json.loads(metadata_path.read_text())
global_proofs = [proof(view_path, 'accepted_123_day_source_view_only'), proof(metadata_path, 'official_November_HEAD_CHECKSUM_metadata_only')]
spec_path = ROOT/'reports/fast_research/V8_NOVEMBER_SOURCE_PREREGISTRATION_20261002_V1.json'
run_dir = STATE/'v8-november-source-20261002-v1'
assert not spec_path.exists() and not run_dir.exists()
queue = ROOT/'.cache/v8_november_sources_20261002_v1.sh'
sources = ['scripts/research_v7/fetch_monthly.py', 'scripts/research_v7/fetch_monthly_v2.py',
           'scripts/research_v7/fetch_monthly_recovery_v3.py', 'scripts/research_v7/audit_monthly.py',
           'scripts/research_v7/source_view.py', 'scripts/research_v7/oracle_flow_ceiling.py',
           'scripts/research_v8/fetch_monthly_from_recovery.py', 'scripts/research_v8/registry.py',
           '.cache/v8_november_sources_20261002_v1.sh', '.cache/v8_november_source_guard_v1.py',
           '.cache/v8_register_november_sources_v1.py', 'scripts/with_task_progress.sh', 'scripts/bounded.sh',
           'scripts/env.sh', 'scripts/task_progress_run.py']
source_hashes = {name: file_sha(ROOT/name) for name in sources}
assert source_hashes['scripts/research_v7/fetch_monthly.py'] == '935917cd8a6215ded1b35e3e0a30a51a9d9c5b997f83a032fa37add9bd42b978'
assert source_hashes['scripts/research_v7/fetch_monthly_v2.py'] == 'a0dc0e120b1de90f35a1bb17f6dd8a4bebe42bb381f076f5f1a96450a3a6614c'
assert source_hashes['scripts/research_v7/audit_monthly.py'] == 'b1bd9c560f2d0f36ded98cf8a40e3edccf8e0e1fb00ab15ff0efc475134a50f7'
assert source_hashes['scripts/research_v7/source_view.py'] == '9b5cedf83f1de618f642640740d9b8528a84a30af34968e94d20bba0a03a8ac9'
python = '/home/xflops/coin-state/research-env-v6/bin/python'
env = ['OMP_NUM_THREADS=1', 'OPENBLAS_NUM_THREADS=1', 'MKL_NUM_THREADS=1', 'POLARS_MAX_THREADS=1', 'ARROW_NUM_THREADS=1', 'CUDA_VISIBLE_DEVICES=-1']
streams = []
for item in metadata['official_november_metadata']:
    market, symbol = item['market'], item['symbol']
    stem = f'V7_MONTHLY_{market.upper()}_{symbol}_202510'
    receipt = ROOT/f'reports/fast_research/{stem}_V2.json'
    qa_path = ROOT/f'reports/fast_research/{stem}_INDEPENDENT_QA_V2.json'
    fetch = 'scripts/research_v7/fetch_monthly_v2.py'
    if (market, symbol) == ('perp', 'ETHUSDT'):
        receipt = ROOT/f'reports/fast_research/{stem}_RECOVERY_V3.json'
        qa_path = ROOT/f'reports/fast_research/{stem}_RECOVERY_INDEPENDENT_QA_V3.json'
        fetch = 'scripts/research_v8/fetch_monthly_from_recovery.py'
    prior, qa = json.loads(receipt.read_text()), json.loads(qa_path.read_text())
    assert prior['status'] == 'OFFICIAL_MONTHLY_V7_COMPLETE_PENDING_INDEPENDENT_QA'
    assert prior['completed_days'] == prior['required_days'] == qa['checked_days'] == 31
    assert qa['status'] == 'PASS_MONTHLY_V7_INDEPENDENT_SOURCE_QA' and qa['receipt_sha256'] == file_sha(receipt)
    assert qa['auditor_sha256'] == source_hashes['scripts/research_v7/audit_monthly.py']
    for name, sha in prior['source_hashes'].items():
        assert file_sha(ROOT/name) == sha, name
        source_hashes[name] = sha
    boundary = prior['daily'][-1]
    manifest = Path(boundary['path'])
    assert file_sha(manifest) == boundary['sha256']
    value = json.loads(manifest.read_text())
    feature = Path(value['feature_path'])
    assert value['date'] == '2025-10-31' and file_sha(feature) == value['feature_sha256'] == boundary['parquet_sha256']
    original_partial = None
    if (market, symbol) == ('perp', 'ETHUSDT'):
        expected = ROOT/'data/research_fast/trade_flow_5s_v2_monthly_v7/recovery_20261002_v3/perp/ETHUSDT/2025-10-31.manifest.json'
        assert manifest == expected
        assert not (ROOT/'data/research_fast/trade_flow_5s_v2_monthly_v7/perp/ETHUSDT/2025-10-31.manifest.json').exists()
        original_partial = proof(ROOT/f'reports/fast_research/{stem}_V2.json', 'preserved_original_30_day_partial_excluded_from_inputs')
    output = f'reports/fast_research/V8_MONTHLY_{market.upper()}_{symbol}_202511_V1.json'
    qa_output = f'reports/fast_research/V8_MONTHLY_{market.upper()}_{symbol}_202511_INDEPENDENT_QA_V1.json'
    directory = f'/home/xflops/coin-state/v8-monthly-{market}-{symbol.lower()}-202511-v1'
    assert not Path(directory).exists() and not (ROOT/output).exists() and not (ROOT/qa_output).exists()
    input_proofs = [proof(receipt, 'prior_full_month_receipt'), proof(qa_path, 'prior_independent_QA'),
                    proof(manifest, 'actual_prior_month_end_boundary'), proof(feature, 'actual_prior_boundary_Parquet')]
    if original_partial:
        input_proofs.append(original_partial)
    relative_receipt, relative_qa = str(receipt.relative_to(ROOT)), str(qa_path.relative_to(ROOT))
    commands = [
        ['bash', 'scripts/with_task_progress.sh', '--title', f'V8 November容量与登记核对 {market} {symbol}', '--', python, '.cache/v8_november_source_guard_v1.py', '--spec', str(spec_path.relative_to(ROOT)), '--market', market, '--symbol', symbol, '--mode', 'capacity'],
        ['bash', 'scripts/with_task_progress.sh', '--title', f'V8 官方月档 {market} {symbol} 2025-11', '--', 'env', 'COIN_TASK_PROGRESS=0', *env, python, fetch, '--market', market, '--symbol', symbol, '--month', '2025-11', '--prior-receipt', relative_receipt, '--prior-qa', relative_qa, '--run-dir', directory, '--output', output],
        ['bash', 'scripts/with_task_progress.sh', '--title', f'V8 November实际CHECKSUM绑定 {market} {symbol}', '--', python, '.cache/v8_november_source_guard_v1.py', '--spec', str(spec_path.relative_to(ROOT)), '--market', market, '--symbol', symbol, '--mode', 'receipt'],
        ['bash', 'scripts/with_task_progress.sh', '--title', f'V8 月档逐行QA {market} {symbol} 2025-11', '--', 'env', *env, python, 'scripts/research_v7/audit_monthly.py', '--receipt', output, '--output', qa_output],
        ['bash', 'scripts/with_task_progress.sh', '--title', f'V8 November独立QA接受核对 {market} {symbol}', '--', python, '.cache/v8_november_source_guard_v1.py', '--spec', str(spec_path.relative_to(ROOT)), '--market', market, '--symbol', symbol, '--mode', 'accepted']]
    streams.append({'market': market, 'symbol': symbol, 'month': '2025-11', 'url': item['url'],
                    'zip_bytes': item['zip_bytes'], 'official_checksum_sha256': item['checksum_text'].split()[0].lower(),
                    'input_proofs': input_proofs, 'prior_boundary_manifest': proof(manifest, 'actual_prior_boundary'),
                    'prior_boundary_ids': {'last_l': value['conversion']['last_l'], 'last_a': value['conversion']['last_a']},
                    'fetch_script': fetch, 'run_dir': directory, 'output': str(ROOT/output), 'qa_output': str(ROOT/qa_output),
                    'required_days': 30, 'required_5s_rows': 518400, 'new_parquet_hashes_before_execution': 'UNKNOWN_NOT_YET_CREATED',
                    'commands': commands})

input_manifest = {'global_input_proofs': global_proofs, 'stream_prior_proofs': [{k: s[k] for k in ('market', 'symbol', 'input_proofs', 'prior_boundary_ids')} for s in streams],
                  'official_month_metadata': metadata['official_november_metadata']}
data_manifest_hash = hashlib.sha256(canonical(input_manifest)).hexdigest()
git_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
assert git_commit == '40e77fc3bec0257e2a173ca08f12efa02928d839'
event_id = 'v8-november-four-stream-source-20261002-v1:operational-source-start'
spec = {'status': 'SOURCE_ONLY_METADATA_SEALED_BEFORE_START', 'created_utc': datetime.now(UTC).isoformat(),
        'event_id': event_id, 'git_commit': git_commit, 'git_commit_meaning': 'Current parent commit; uncommitted source bytes separately pinned by source_hashes.',
        'data_manifest_hash': data_manifest_hash, 'input_manifest': input_manifest, 'global_input_proofs': global_proofs,
        'source_hashes': source_hashes, 'queue_script': str(queue), 'queue_script_sha256': file_sha(queue),
        'queue_run_dir': str(run_dir), 'queue_log': str(run_dir/'queue.log'),
        'queue_start_command': ['bash', 'scripts/with_task_progress.sh', '--title', 'V8 November四流官方来源串行 · 无模型', '--', 'bash', str(queue.relative_to(ROOT))],
        'interpreter': python, 'streams': streams, 'raw_concurrency': 1,
        'november_publication_root': str(ROOT/'data/research_fast/trade_flow_5s_v2_monthly_v7'),
        'reuse': 'Unchanged V1/V2/converter/auditor; only ETH prior lookup private-module adapter to accepted recovery subtree.',
        'source_only_scope': 'Official ZIP conversion and source QA; no research labels, model metrics, fit, economic experiment, holdout or orders.',
        'QA_data_reads': 'Frozen original raw/5s row values are read only for converter and original source-QA correctness.',
        'known_zip_download_bytes_total': 3201489577, 'largest_single_zip_bytes': 1110070854,
        'required_stream_days': 120, 'required_rows': 2073600, 'minimal_P1_missing_stream_days': 88,
        'resource_budget': {'shared_ram_limit_bytes': 4999999488, 'project_swap_bytes': 0, 'gpu_used': False,
                            'original_largest_month_reserve_bytes': 3970141708,
                            'additional_working_reserve_bytes': 1000000000,
                            'required_preflight_reserve_bytes': 4970141708,
                            'additional_stress_reserve_bytes': 1000000000,
                            'expected_max_total_bytes': 32000000000, 'stress_max_total_bytes': 36000000000,
                            'hard_max_total_bytes': 40000000000,
                            'disk_measurement_before_execution': 'UNKNOWN_WILL_MEASURE_BEFORE_EACH_STREAM'},
        'reason_for_next_experiment': 'Supply the fourth separated November month for V8 P1 causal OOF source coverage; no source acceptance proves regime independence or alpha.',
        'model_fits': 0, 'research_label_reads': False, 'model_outcome_reads': False,
        'locked_consumed': False, 'orders_sent': 0, 'seed': None, 'seed_meaning': 'NOT_APPLICABLE_SOURCE_ONLY',
        'p1_gate': 'NOT_READY', 'qualification': 'NO_QUALIFIED_CANDIDATE', 'classification': 'SOURCE_ENGINEERING_SCREENING_SUPPORT'}
run_dir.mkdir()
write(spec_path, spec)
registry = ROOT/'reports/experiment_registry.jsonl'
prior_registry = registry.read_bytes()
read_verified(prior_registry)
event = dict.fromkeys(FIELDS)
event.update(event_type='OPERATIONAL_SOURCE_START', event_id=event_id,
             experiment_id='V8-NOVEMBER-FOUR-STREAM-SOURCE-20261002-V1', git_commit=git_commit,
             data_manifest_hash=data_manifest_hash, protocol_hash=file_sha(spec_path),
             feature_set='FROZEN_TRADE_FLOW_5S_V2_SOURCE_TABLES_ONLY', labels='NONE_SOURCE_ONLY',
             model_family='NOT_APPLICABLE_SOURCE_ONLY', hyperparameters={'month': '2025-11', 'raw_concurrency': 1, 'commands': [s['commands'] for s in streams]},
             seed=None, thresholds=spec['resource_budget'], cost_assumptions='NOT_APPLICABLE_NO_ECONOMIC_OR_MODEL_EXPERIMENT',
             all_folds='NOT_APPLICABLE_SOURCE_ONLY; intended fourth P1 month November, future qualification UNKNOWN',
             success_failure='OPERATIONAL_START_REGISTERED_BEFORE_ANY_DOWNLOAD',
             reason_for_next_experiment=spec['reason_for_next_experiment'], result_influenced_later_choice='SOURCE_AVAILABILITY_ONLY_NO_MODEL_RESULTS',
             source_spec_path=str(spec_path), exact_queue_start_command=spec['queue_start_command'],
             sources=source_hashes, models_fit=0, labels_read=False, model_outcomes_read=False,
             qualification='NO_QUALIFIED_CANDIDATE', p1_gate='NOT_READY', trial_count_eligible=False,
             unknown_future_values='actual new ZIP outcome, Parquet hashes, source acceptance, elapsed and peak RAM not yet known')
registered = append_event(registry, event)
current_registry = registry.read_bytes()
assert current_registry.startswith(prior_registry)
write(ROOT/'reports/fast_research/V8_NOVEMBER_SOURCE_OPERATIONAL_START_20261002_V1.json', {
    'status': 'SOURCE_ONLY_OPERATIONAL_START_APPENDED_BEFORE_DOWNLOAD', 'registered_event': registered,
    'spec_path': str(spec_path), 'spec_sha256': file_sha(spec_path), 'old_registry_prefix_sha256': hashlib.sha256(prior_registry).hexdigest(),
    'old_registry_prefix_bytes': len(prior_registry), 'registry_prefix_preserved': True,
    'models_fit': 0, 'source_downloads_started': 0, 'locked_consumed': False, 'orders_sent': 0})
print(json.dumps({'status': 'SOURCE_ONLY_OPERATIONAL_START_APPENDED_BEFORE_DOWNLOAD', 'event_id': event_id,
                  'event_sha256': registered['record_sha256'], 'spec_sha256': file_sha(spec_path),
                  'git_commit': git_commit, 'streams': len(streams)}, ensure_ascii=False), flush=True)
