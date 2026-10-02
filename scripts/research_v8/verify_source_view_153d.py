"""Explicit source-only Jul--Nov binding; reuse the unchanged shared logical view."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, date, datetime
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

from quant import disk, resources
from quant.paths import ROOT, STATE
from quant.research_fast.trade_flow_v2 import checksum, require, source_hashes

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'scripts/research_v7'))
from scripts.research_v8.registry import FIELDS, append_event, canonical, read_verified
from source_view import build_shards

PRIOR_SHA = '32a71b6018a00b2bcfca1d198661be59c0889049606c19774a5dd141d9aedf51'
VIEW_SHA = '9b5cedf83f1de618f642640740d9b8528a84a30af34968e94d20bba0a03a8ac9'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--producer-task', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to(ROOT/'reports') and not output.exists(), 'Exclusive source view report required')
    clean_path = ROOT/'reports/fast_research/V8_CLEAN_ENVIRONMENT_SMOKE_20261002_V2.json'
    clean = json.loads(clean_path.read_text())
    require(Path(sys.prefix).resolve() == Path(clean['sys_prefix']).resolve() and not any(
        'research-env-v6' in entry or '/coin/.venv/' in entry for entry in sys.path),
        'Accepted independent clean V8 runtime required')
    environment = {'python_executable': sys.executable, 'sys_prefix': sys.prefix,
                   'accepted_clean_environment_report': str(clean_path),
                   'accepted_clean_environment_sha256': checksum(clean_path),
                   'lock_sha256': checksum(ROOT/'environments/v8/uv.lock'),
                   'external_overlay_site_paths': []}
    prior_path = ROOT/'reports/fast_research/V7_SHARED_SOURCE_VIEW_123D_20261002_V1.json'
    require(checksum(prior_path) == PRIOR_SHA, 'Frozen accepted 123-day source view changed')
    require(checksum(ROOT/'scripts/research_v7/source_view.py') == VIEW_SHA, 'Shared logical-view source changed')
    prior = json.loads(prior_path.read_text())
    require(prior['status'] == 'PASS_SHARED_V7_SOURCE_VIEW_123D' and prior['actual_common_days'] == 123, 'Accepted prior source evidence required')
    producer_path = args.producer_task.resolve()
    require(producer_path.is_relative_to(STATE/'task-progress'), 'Actual producer task receipt required')
    producer = json.loads(producer_path.read_text())
    require(producer['id'] == '0124c7da7aef40b4bb4a57acd4b0bd17' and producer['pid'] == 3134 and producer['start_ticks'] == 519151 and producer['status'] == 'completed' and producer['exit_code'] == 0, 'Original November queue must really finish successfully')
    spec_path = ROOT/'reports/fast_research/V8_NOVEMBER_SOURCE_PREREGISTRATION_20261002_V1.json'
    spec = json.loads(spec_path.read_text())
    history = read_verified((ROOT/'reports/experiment_registry.jsonl').read_bytes())
    start = next(event for event in history if event['event_id'] == spec['event_id'])
    require(start['protocol_hash'] == checksum(spec_path), 'Original 40e source preregistration changed')
    pairs = [(Path(item['receipt_path']), Path(item['qa_path'])) for item in prior['binding']['monthly_proofs']]
    inputs = [{'path': str(prior_path), 'sha256': checksum(prior_path)},
              {'path': str(spec_path), 'sha256': checksum(spec_path)},
              {'path': str(producer_path), 'sha256': checksum(producer_path)},
              {'path': str(clean_path), 'sha256': checksum(clean_path)},
              {'path': str(ROOT/'environments/v8/uv.lock'), 'sha256': checksum(ROOT/'environments/v8/uv.lock')}]
    for stream in spec['streams']:
        receipt_path, qa_path = Path(stream['output']), Path(stream['qa_output'])
        acceptance = ROOT/f'reports/fast_research/V8_MONTHLY_{stream["market"].upper()}_{stream["symbol"]}_202511_SOURCE_ACCEPTANCE_V1.json'
        value = json.loads(acceptance.read_text())
        require(value['status'] == 'PASS_SOURCE_ONLY_INDEPENDENT_MONTHLY_QA' and value['checked_days'] == 30 and value['checked_rows'] == 518400, 'Real independent month QA acceptance required')
        require(value['receipt_sha256'] == checksum(receipt_path) and value['qa_sha256'] == checksum(qa_path), 'Accepted November source hashes changed')
        pairs.append((receipt_path, qa_path))
        inputs.extend({'path': str(path), 'sha256': checksum(path)} for path in (receipt_path, qa_path, acceptance))
    protocol = {'command': [sys.executable, str(Path(__file__).resolve()), '--producer-task', str(producer_path), '--output', str(output)],
                'start': '2025-07-01', 'end_exclusive': '2025-12-01', 'days': 153, 'stream_days': 612,
                'rows': 10575360, 'source_view_sha256': VIEW_SHA, 'verifier_sha256': checksum(Path(__file__)),
                'environment': environment,
                'source_scope': 'Source SHA/schema/ID and selected-prefix metadata only, no repeat row QA, labels or model outcomes.'}
    event = dict.fromkeys(FIELDS)
    event.update(event_id='v8-jul-nov-153d-source-view-20261002-v1:start', event_type='OPERATIONAL_SOURCE_ACCEPTANCE_START',
                 experiment_id='V8-JUL-NOV-153D-SOURCE-VIEW-20261002-V1',
                 git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                 data_manifest_hash=hashlib.sha256(canonical(inputs)).hexdigest(),
                 protocol_hash=hashlib.sha256(canonical(protocol)).hexdigest(),
                 feature_set='UNCHANGED_FROZEN_5S_SOURCE_TABLES_AND_SHARDSPEC', labels='NONE_SOURCE_ONLY',
                 model_family='NOT_APPLICABLE_SOURCE_ONLY', hyperparameters=protocol, seed=None,
                 thresholds={'common_days': 153, 'unique_stream_days': 612, 'rows': 10575360, 'old_prefix_rows': 492},
                 cost_assumptions='NOT_APPLICABLE_NO_ECONOMIC_EXPERIMENT', all_folds='NOT_APPLICABLE_SOURCE_ONLY',
                 success_failure='SOURCE_ACCEPTANCE_START_BEFORE_SHARED_VIEW_BUILD',
                 reason_for_next_experiment='Make accepted November data available to later V8 P1; data availability is not economic or statistical gate passage.',
                 result_influenced_later_choice='SOURCE_AVAILABILITY_ONLY_NO_MODEL_RESULTS', inputs=inputs,
                 model_fits=0, seed_meaning='NOT_APPLICABLE_SOURCE_ONLY', trial_count_eligible=False,
                 locked_consumed=False, orders_sent=0, p1_gate='NOT_READY', qualification='NO_QUALIFIED_CANDIDATE')
    registered = append_event(ROOT/'reports/experiment_registry.jsonl', event)
    result = {'status': 'FAILED_SHARED_V8_SOURCE_VIEW_153D', 'created_utc': datetime.now(UTC).isoformat(),
              'git_commit_at_start': event['git_commit'], 'registration_start': registered,
              'source_hashes': {**source_hashes(), 'scripts/research_v7/source_view.py': VIEW_SHA,
                                'scripts/research_v8/verify_source_view_153d.py': checksum(Path(__file__))},
              'prior_123d_report': inputs[0], 'actual_original_source_producer': inputs[2],
              'environment': environment,
              'original_november_source_start_commit': spec['git_commit'],
              'original_november_source_event_sha256': start['record_sha256'],
              'classification': 'SCREENING_SOURCE_SUPPORT_ONLY', 'p1_gate': 'NOT_READY',
              'qualification': 'NO_QUALIFIED_CANDIDATE', 'model_fits': 0,
              'research_labels_or_model_outcomes_read': False, 'alpha_eligible': False,
              'real_time_quality_eligible': False, 'locked_consumed': False, 'orders_sent': 0}
    started = time.monotonic()
    try:
        shards, binding = build_shards(date(2025, 7, 1), date(2025, 12, 1), monthly_pairs=pairs)
        require(len(shards) == 612 and len({(s.market, s.symbol, s.day) for s in shards}) == 612 and sum(s.rows for s in shards) == 10575360, 'Complete unique 153-day view required')
        counts = Counter(row['source_kind'] for row in binding['selected'])
        require(counts == {'original_daily': 266, 'independently_audited_monthly': 346}, 'Daily-first source selection changed')
        require(binding['selected'][:492] == prior['binding']['selected'], 'Frozen 123-day selected source prefix changed')
        october_recovery = [row for row in binding['selected'] if row['market'] == 'perp' and row['symbol'] == 'ETHUSDT' and row['day'].startswith('2025-10')]
        require(len(october_recovery) == 31 and all('/recovery_20261002_v3/' in row['manifest_path'] for row in october_recovery), 'Original partial October must not be spliced or promoted')
        november = [row for row in binding['selected'] if row['day'].startswith('2025-11')]
        require(len(november) == 120 and all(row['source_kind'] == 'independently_audited_monthly' and '/recovery_20261002_v3/' not in row['manifest_path'] for row in november), 'November publication must use actual original monthly root')
        excluded = prior['excluded_partial_october_v2']
        require(checksum(Path(excluded['path'])) == excluded['sha256'], 'Preserved original partial evidence changed')
        scan_start = time.monotonic()
        ledger = disk.check(1_000_000_000)
        ledger.update(measured_utc=datetime.now(UTC).isoformat(), elapsed_seconds=time.monotonic()-scan_start)
        result.update(status='PASS_SHARED_V8_SOURCE_VIEW_153D', actual_common_days=153,
                      actual_unique_stream_days=612, actual_rows=10575360, source_counts=dict(counts),
                      original_123d_exact_prefix_preserved=True, excluded_original_30_day_october=excluded,
                      november_source_days=30, november_unique_stream_days=120, binding=binding,
                      disk=ledger, resources=resources.status())
    except Exception as error:
        result.update(error_type=type(error).__name__, reason=str(error)[:2048])
        raise
    finally:
        result['elapsed_seconds'] = time.monotonic()-started
        result['peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        with output.open('x') as stream:
            json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
        completion = dict(event, event_id='v8-jul-nov-153d-source-view-20261002-v1:complete',
                          event_type='OPERATIONAL_SOURCE_ACCEPTANCE_COMPLETE', success_failure=result['status'],
                          output_path=str(output), output_sha256=checksum(output))
        append_event(ROOT/'reports/experiment_registry.jsonl', completion)
    print(json.dumps({key: result[key] for key in ('status', 'actual_common_days', 'actual_unique_stream_days',
        'source_counts', 'elapsed_seconds', 'peak_rss_bytes')}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
