"""Static source/calendar review: no market rows, labels, model results or fits."""
import ast
import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

root = Path('/mnt/d/codex/coin')
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

protocol_path = root/'protocols/NONOVERLAP_MECHANISM_V8_V1.json'
script_path = root/'scripts/research_v8/nonoverlap_mechanism.py'
spec = json.loads(protocol_path.read_text())
code = script_path.read_text()
ast.parse(code)
source_path = root/spec['source_receipt']
source_sha = sha(source_path)
assert source_sha == spec['source_receipt_sha256'] == 'dd931ce79f7f78e7e2c070f553077ffeca4ed73d7c0c0a1c744e4288d68f05cf'
assert sha(root/'scripts/research_v7/source_view.py') == spec['source_view_sha256'] == '9b5cedf83f1de618f642640740d9b8528a84a30af34968e94d20bba0a03a8ac9'
gates_path = root/spec['fold_contract']
assert sha(gates_path) == spec['fold_contract_sha256']
gates = json.loads(gates_path.read_text())
source = json.loads(source_path.read_text())
assert source['status'] == 'PASS_SHARED_V8_SOURCE_VIEW_153D' and source['actual_common_days'] == 153
assert [fold['id'] for fold in gates['folds']] == spec['all_fold_ids']
assert spec['locked_holdout_allowed'] is False and spec['P1_pass_allowed_from_this_diagnostic'] is False
streams = (('spot', 'BTCUSDT'), ('spot', 'ETHUSDT'), ('perp', 'BTCUSDT'), ('perp', 'ETHUSDT'))
selected = source['binding']['selected']
keys = {(row['market'], row['symbol'], date.fromisoformat(row['day'])) for row in selected}
assert len(keys) == len(selected) == 612
start, locked = date(2025, 7, 1), date(2026, 3, 1)
micro = 1_000_000
day_us = 86400 * micro
def stamp(value):
    return int(datetime.combine(date.fromisoformat(value), datetime.min.time(), UTC).timestamp())*micro

folds = []
all_days = set()
lag = gates['maximum_nominal_label_lag_seconds']*micro
embargo = gates['embargo_seconds']*micro
for fold in gates['folds']:
    train, validation, test, end = (stamp(fold[key]) for key in ('train_start', 'validation_start', 'test_start', 'test_end_exclusive'))
    assert stamp(str(start)) <= train < validation < test < end < stamp(str(locked))
    cutoff = validation - embargo - lag - 1
    wanted = set()
    for lower, upper in ((train, cutoff), (test, end)):
        cursor = lower//day_us*day_us
        while cursor < upper:
            first = datetime.fromtimestamp((max(lower,cursor)-256*5*micro)//micro, UTC).date()
            last = datetime.fromtimestamp((min(upper,cursor+day_us)+lag-1)//micro, UTC).date()
            while first <= last:
                wanted.add(first)
                first += timedelta(days=1)
            cursor += day_us
    assert all(start <= day < date(2025,12,1) < locked for day in wanted)
    assert {(market,symbol,day) for market,symbol in streams for day in wanted}.issubset(keys)
    all_days.update(wanted)
    folds.append({'fold': fold['id'], 'wanted_source_days': len(wanted),
                  'first_source_day': str(min(wanted)), 'last_source_day_inclusive': str(max(wanted)),
                  'explicit_source_days': sorted(map(str,wanted)), 'all_four_streams_available': True,
                  'calendar_is_sparse_between_train_and_oos': True,
                  'validation_content_not_read_by_this_review': True})
report = {'status': 'PASS_STATIC_SOURCE_CALENDAR_REUSE_REVIEW', 'created_utc': datetime.now(UTC).isoformat(),
          'review_scope': 'Source selection, accepted source byte binding, declared source calendar and locked read boundaries only.',
          'source_calendar_correctness_blocker': False,
          'prior_source_receipt_pin_finding': 'Resolved by root before any market diagnostic: protocol SHA pins and pre-read require guards are present.',
          'source_chain': ['Frozen 153-day receipt binding.selected', 'Original ShardSpec.from_manifest for daily / from_conversion for monthly', 'Original FastSequenceDataset(mode=smoke)'],
          'source_framework_reimplementation_required': False,
          'actual_market_row_or_parquet_content_read': False, 'market_labels_read': False,
          'model_outcomes_read': False, 'market_diagnostic_executed': False, 'market_models_fit': 0,
          'p1_gate': 'NOT_READY', 'qualification': 'NO_QUALIFIED_CANDIDATE',
          'independent_label_v5_acceptance': 'OUTSIDE_THIS_SOURCE_REVIEW_SCOPE_REQUIRED_BEFORE_RUN',
          'source_receipt_sha256': source_sha, 'protocol_sha256': sha(protocol_path),
          'mechanism_script_sha256': sha(script_path), 'fold_contract_sha256': sha(gates_path),
          'original_dataset_source_sha256': sha(root/'src/quant/research_fast/dataset.py'),
          'source_view_sha256': spec['source_view_sha256'],
          'source_calendar_days_union': len(all_days), 'source_calendar_stream_days': len(all_days)*4,
          'folds': folds, 'locked_boundary': str(locked), 'locked_consumed': False, 'orders_sent': 0,
          'original_reader_guards': ['Dates validated before opening Parquet', 'Unique stream-day declaration',
              'Actual Parquet SHA and bounded row-group metadata', 'Synchronized exact 5s joint grid without interpolation',
              'joint_rows rejects any requested interval crossing locked boundary'],
          'reviewer_source_sha256': sha(Path(__file__))}
output = root/'reports/fast_research/V8_NONOVERLAP_SOURCE_STATIC_REVIEW_20261002_V1.json'
with output.open('x') as stream:
    json.dump(report, stream, indent=2, ensure_ascii=False, allow_nan=False)
    stream.write('\n')
print(json.dumps({'status': report['status'], 'source_calendar_days_union': len(all_days),
                  'source_calendar_stream_days': len(all_days)*4,
                  'report_sha256': sha(output), 'mechanism_script_sha256': report['mechanism_script_sha256']}), flush=True)
