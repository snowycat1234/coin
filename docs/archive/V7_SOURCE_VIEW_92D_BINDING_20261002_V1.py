import importlib.util
import json
import resource
import sys
import time
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path

root = Path('/mnt/d/codex/coin')
sys.path.insert(0, str(root / 'scripts/research_v7'))
from source_view import build_shards
from quant.research_fast.trade_flow_v2 import checksum, source_hashes

target = root / 'reports/fast_research/V7_SHARED_SOURCE_VIEW_92D_20261002_V1.json'
if target.exists():
    raise RuntimeError('Exclusive source binding')
pairs = [(root / 'reports/fast_research/V7_MONTHLY_SPOT_BTC_202509_PILOT_V1.json', root / 'reports/fast_research/V7_MONTHLY_SPOT_BTC_202509_INDEPENDENT_QA_V1.json')]
for market, symbol in [('SPOT', 'ETHUSDT'), ('PERP', 'BTCUSDT'), ('PERP', 'ETHUSDT')]:
    prefix = 'V7_MONTHLY_' + market + '_' + symbol + '_202509'
    pairs.append((root / ('reports/fast_research/' + prefix + '_V1.json'), root / ('reports/fast_research/' + prefix + '_INDEPENDENT_QA_V1.json')))
started = time.monotonic()
result = {'status': 'FAILED_SHARED_V7_SOURCE_VIEW_92D', 'created_utc': datetime.now(UTC).isoformat(), 'source_hashes': {**source_hashes(), 'scripts/research_v7/source_view.py': checksum(root / 'scripts/research_v7/source_view.py')}, 'labels_or_model_results_read': False, 'alpha_eligible': False}
try:
    shards, binding = build_shards(date(2025, 7, 1), date(2025, 10, 1), monthly_pairs=pairs)
    counts = Counter(row['source_kind'] for row in binding['selected'])
    unique = {(shard.market, shard.symbol, shard.day) for shard in shards}
    if len(shards) != 368 or len(unique) != len(shards) or sum(counts.values()) != len(shards):
        raise RuntimeError('Unexpected actual source selection')
    result.update(status='PASS_SHARED_V7_SOURCE_VIEW_92D', actual_common_days=92, actual_unique_stream_days=len(shards), actual_rows=sum(shard.rows for shard in shards), source_counts=dict(counts), binding=binding)
except Exception as error:
    result.update(error_type=type(error).__name__, reason=str(error))
    raise
finally:
    result['elapsed_seconds'] = time.monotonic() - started
    result['peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    with target.open('x') as writer:
        writer.write(json.dumps(result, indent=2, allow_nan=False) + '\n')
print(json.dumps({k: result[k] for k in ('status', 'actual_common_days', 'actual_unique_stream_days', 'source_counts', 'elapsed_seconds', 'peak_rss_bytes')}))
