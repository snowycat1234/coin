"""Root verification of preserved window/source/venue modules without model outputs."""
import csv
import hashlib
import io
import json
import statistics
import sys
import urllib.request
import zipfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path('/mnt/d/codex/coin')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8-sig'))


venue_name = 'reports/fast_research/V7_SPOT_USDM_ECONOMIC_MAPPING_20261002_V1.json'
venue = read(venue_name)
metadata = read('reports/fast_research/V7_VENUE_METADATA_AVAILABILITY_20261002_V1.json')
for name, expected in venue['input_hashes'].items():
    assert sha(ROOT/name) == expected, name
stats = []
for original in venue['funding_archives']:
    p = Path(metadata['run_dir'])/(original['symbol']+'-fundingRate-2025-07.zip')
    checksum = p.with_name(p.name+'.CHECKSUM')
    assert sha(p) == checksum.read_text().split()[0] == original['zip_sha256']
    assert sha(checksum) == original['checksum_sha256']
    with zipfile.ZipFile(p) as z:
        assert z.testzip() is None
        rows = list(csv.DictReader(io.TextIOWrapper(z.open(z.namelist()[0]))))
    rates = [Decimal(r['last_funding_rate'])*10000 for r in rows]
    assert len(rows) == original['rows'] == 93
    assert sum(r > 0 for r in rates) == original['positive_events']
    assert sum(r < 0 for r in rates) == original['negative_events']
    for field, actual in [('rate_bps_min', min(rates)), ('rate_bps_max', max(rates)),
                         ('rate_bps_mean', sum(rates)/Decimal(len(rates))),
                         ('rate_bps_median', statistics.median(rates))]:
        assert float(actual) == original[field], field
    assert all(int(r['funding_interval_hours']) == 8 for r in rows)
    stats.append({'symbol': original['symbol'], 'events': len(rows),
                  'mean_bps': original['rate_bps_mean'], 'official_checksum_verified': True})
for probe in venue['small_daily_price_checksum_probe']:
    assert sha(Path(probe['saved_path'])) == probe['sha256']
    assert Path(probe['saved_path']).stat().st_size == probe['bytes']
    assert probe['http_status'] == 404
assert venue['models_fit'] == venue['orders_sent'] == 0
assert not venue['unseen_or_locked_labels_read']
window_name = 'reports/fast_research/V7_TASK_WINDOW_KEEPALIVE_ACCEPTANCE_20261002_V1.json'
window = read(window_name)
for name, expected in {**window['source_hashes'], **window['verified_prior_files']}.items():
    assert sha(ROOT/name) == expected, name
with urllib.request.urlopen('http://127.0.0.1:8765/api/status', timeout=8) as f:
    live = json.load(f)
assert live['errors'] == []
assert live['resources']['ram_limit_bytes'] <= 5_000_000_000
assert live['resources']['swap_bytes'] == 0
assert not live['resources']['gpu_used']
source_name = 'reports/fast_research/V7_SHARED_SOURCE_VIEW_123D_20261002_V1.json'
source = read(source_name)
assert source['status'] == 'PASS_SHARED_V7_SOURCE_VIEW_123D'
assert source['actual_common_days'] == 123 and source['actual_unique_stream_days'] == 492
assert source['actual_rows'] == 8_501_760
assert source['original_92d_exact_prefix_preserved']
assert not source['labels_or_model_results_read']
for name, expected in source['source_hashes'].items():
    assert sha(ROOT/name) == expected, name
producer = source['recovery_actual_producer']
assert sha(Path(producer['path'])) == producer['sha256']
assert producer['exit_code'] == 0
assert json.loads(Path(producer['path']).read_text())['exit_code'] == 0
old = source['excluded_partial_october_v2']
assert sha(Path(old['path'])) == old['sha256'] and not old['accepted']
receipt = {'status': 'ROOT_PASS_COMPLETED_WINDOW_SOURCE_AND_VENUE_MODULES_ONLY',
    'created_utc': datetime.now(UTC).isoformat(),
    'candidate': 'NONE', 'candidate_status': 'NO_QUALIFIED_CANDIDATE',
    'classification': 'SCREENING_OR_OPERATIONAL',
    'verified_prior_files': {name: sha(ROOT/name) for name in [venue_name, window_name, source_name]},
    'funding_independent_recalculation': stats,
    'source_acceptance': {'days': 123, 'unique_shards': 492, 'rows': 8_501_760,
                          'prior_prefix_equal': True, 'producer_actual_exit_zero': True},
    'current_window_generated_at': live['generated_at'],
    'current_window_errors': live['errors'], 'resources': live['resources'],
    'models_fit': 0, 'locked_consumed': False, 'orders_sent': 0,
    'P1_gate_passed': False,
    'limits': 'Prior source/auditor evidence accepted; not a new 492-file QA rerun or strategy evaluation.'}
dest = ROOT/'reports/fast_research/V8_ROOT_PRIOR_COMPLETED_MODULES_20261002_V1.json'
with dest.open('x') as f:
    json.dump(receipt, f, ensure_ascii=False, indent=2)
print(json.dumps({'status': receipt['status'], 'report': str(dest)}, ensure_ascii=False), flush=True)
