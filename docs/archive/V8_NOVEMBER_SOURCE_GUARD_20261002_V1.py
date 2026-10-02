"""Task-specific metadata binding and the existing physical disk guard."""
import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from quant import disk, resources
from quant.paths import ROOT
from quant.research_fast.dataset import file_sha

sys.path.insert(0, str(ROOT))
from scripts.research_v8.registry import read_verified

p = argparse.ArgumentParser()
p.add_argument('--spec', type=Path, required=True)
p.add_argument('--market', required=True)
p.add_argument('--symbol', required=True)
p.add_argument('--mode', choices=('capacity', 'receipt', 'accepted'), required=True)
args = p.parse_args()
spec = json.loads(args.spec.read_text())
history = read_verified((ROOT/'reports/experiment_registry.jsonl').read_bytes())
events = [event for event in history if event['event_id'] == spec['event_id']]
assert len(events) == 1 and events[0]['event_type'] == 'OPERATIONAL_SOURCE_START'
assert events[0]['protocol_hash'] == file_sha(args.spec)
assert events[0]['data_manifest_hash'] == spec['data_manifest_hash']
for name, expected in spec['source_hashes'].items():
    assert file_sha(ROOT/name) == expected, name
for entry in spec['global_input_proofs']:
    assert file_sha(Path(entry['path'])) == entry['sha256'], entry['path']
stream = next(item for item in spec['streams'] if (item['market'], item['symbol']) == (args.market, args.symbol))
for entry in stream['input_proofs']:
    assert file_sha(Path(entry['path'])) == entry['sha256'], entry['path']
result = {'status': 'SOURCE_ONLY_CHECK_RUNNING_UNACCEPTED', 'created_utc': datetime.now(UTC).isoformat(),
          'mode': args.mode, 'market': args.market, 'symbol': args.symbol,
          'event_id': spec['event_id'], 'registered_event_sha256': events[0]['record_sha256'],
          'spec_sha256': file_sha(args.spec), 'source_guard_sha256': file_sha(Path(__file__)),
          'source_only': True, 'models_fit': 0, 'labels_read': False, 'model_outcomes_read': False,
          'p1_gate': 'NOT_READY', 'qualification': 'NO_QUALIFIED_CANDIDATE',
          'locked_consumed': False, 'orders_sent': 0}
suffix = {'capacity': 'CAPACITY', 'receipt': 'CHECKSUM_BINDING', 'accepted': 'SOURCE_ACCEPTANCE'}[args.mode]
output = ROOT/f'reports/fast_research/V8_MONTHLY_{args.market.upper()}_{args.symbol}_202511_{suffix}_V1.json'
assert not output.exists()
try:
    if args.mode == 'capacity':
        assert not Path(stream['run_dir']).exists() and not Path(stream['output']).exists()
        started = time.monotonic()
        ledger = disk.check(spec['resource_budget']['required_preflight_reserve_bytes'])
        ledger.update(measured_utc=datetime.now(UTC).isoformat(), elapsed_seconds=time.monotonic()-started)
        expected = ledger['total_bytes'] + ledger['reserved_bytes']
        stress = expected + spec['resource_budget']['additional_stress_reserve_bytes']
        assert expected <= 32_000_000_000 and stress < 36_000_000_000
        result.update(status='PASS_REGISTERED_SOURCE_CAPACITY_AND_INPUT_BINDINGS', disk=ledger,
                      expected_total_with_reserve_bytes=expected, stress_total_with_reserve_bytes=stress)
    else:
        receipt = json.loads(Path(stream['output']).read_text())
        assert receipt['status'] == 'OFFICIAL_MONTHLY_V7_COMPLETE_PENDING_INDEPENDENT_QA'
        assert receipt['completed_days'] == receipt['required_days'] == 30
        assert receipt['zip_sha256'] == stream['official_checksum_sha256']
        assert receipt['zip_bytes'] == stream['zip_bytes'] and receipt['checksum_status'] == 'PASS'
        assert receipt['store'] == spec['november_publication_root']
        assert receipt['prior_boundary']['path'] == stream['prior_boundary_manifest']['path']
        assert receipt['prior_boundary']['sha256'] == stream['prior_boundary_manifest']['sha256']
        if args.mode == 'accepted':
            qa = json.loads(Path(stream['qa_output']).read_text())
            assert qa['status'] == 'PASS_MONTHLY_V7_INDEPENDENT_SOURCE_QA'
            assert qa['receipt_sha256'] == file_sha(Path(stream['output']))
            assert qa['checked_days'] == 30 and qa['checked_rows'] == 30*17280
            result.update(status='PASS_SOURCE_ONLY_INDEPENDENT_MONTHLY_QA',
                          qa_path=stream['qa_output'], qa_sha256=file_sha(Path(stream['qa_output'])),
                          checked_days=30, checked_rows=qa['checked_rows'])
        else:
            result['status'] = 'PASS_ACTUAL_MONTH_CHECKSUM_AND_BOUNDARY_MATCH_PREREGISTRATION'
        result.update(receipt_path=stream['output'], receipt_sha256=file_sha(Path(stream['output'])),
                      completed_days=30)
except Exception as error:
    result.update(status='FAILED_REGISTERED_SOURCE_CHECK_UNACCEPTED', error_type=type(error).__name__, reason=str(error))
    raise
finally:
    result['resources'] = resources.status()
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
print(json.dumps({key: result[key] for key in ('status', 'mode', 'market', 'symbol')}, ensure_ascii=False), flush=True)
