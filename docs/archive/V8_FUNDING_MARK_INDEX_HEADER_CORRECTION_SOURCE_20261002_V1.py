"""Correct one acceptance synopsis using unchanged per-file independent QA metadata."""
from datetime import UTC, datetime
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path('/mnt/d/codex/coin')
sys.path.insert(0, str(ROOT))
from scripts.research_v8.registry import FIELDS, append_event


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


reports = ROOT / 'reports/fast_research'
acceptance_path = reports / 'V8_FUNDING_MARK_INDEX_SOURCE_ACCEPTANCE_20261002_V1.json'
qa_path = reports / 'V8_FUNDING_MARK_INDEX_INDEPENDENT_QA_20261002_V1.json'
protocol_path = ROOT / 'protocols/FUNDING_MARK_INDEX_SOURCE_V8_V1.json'
assert sha(acceptance_path) == '318622721ed9733d84ae66082f750e8b7d4ed960d7812c9e899c94b3cb5188aa'
assert sha(qa_path) == '2f2b13b6be120a2db7e09abc24943f33b0892e53bfcc6b474f1bf3a53055ac74'
assert sha(protocol_path) == '2b3ef722ba3276c95d4a658d63ecdae12d92ae7a4f95a88de2918a4fd775d38a'
acceptance = json.loads(acceptance_path.read_bytes())
qa = json.loads(qa_path.read_bytes())
expected_header = ['open_time', 'open', 'high', 'low', 'close', 'volume',
                   'close_time', 'quote_volume', 'count', 'taker_buy_volume',
                   'taker_buy_quote_volume', 'ignore']
checked = [row for row in qa['sources'] if row['kind'] != 'fundingRate']
accepted = [row for row in acceptance['sources'] if row['kind'] != 'fundingRate']
assert len(checked) == len(accepted) == 16
assert all(row['header'] == expected_header for row in checked)
assert all(row['observed_header'] == expected_header for row in accepted)
assert {(row['kind'], row['symbol'], row['month']) for row in checked} == {
    (row['kind'], row['symbol'], row['month']) for row in accepted}
result = {
    'status': 'ACCEPTANCE_SYNOPSIS_HEADER_CORRECTION_ONLY',
    'created_utc': datetime.now(UTC).isoformat(),
    'prior_acceptance_path': str(acceptance_path),
    'prior_acceptance_sha256': sha(acceptance_path),
    'independent_qa_path': str(qa_path),
    'independent_qa_sha256': sha(qa_path),
    'protocol_path': str(protocol_path),
    'protocol_sha256': sha(protocol_path),
    'corrected_field': 'accepted_format.price_proxy_headers',
    'incorrect_prior_synopsis': acceptance['accepted_format']['price_proxy_headers'],
    'corrected_synopsis': 'Present in all 16 actual official price-proxy CSVs; exact 12-column header independently verified and excluded from numeric rows.',
    'observed_price_proxy_header': expected_header,
    'verified_price_proxy_archive_count': 16,
    'evidence': 'Original acceptance.sources[].observed_header and independent_qa.sources[].header already record the correct actual headers.',
    'original_artifact_bytes_modified': False,
    'producer_and_auditor_qa_changed': False,
    'market_data_rows_read': False,
    'source_format_acceptance_changed': False,
    'economic_or_p1_status_changed': False,
    'fits': 0,
    'apr_claimed': False,
    'source_sha256': sha(__file__),
}
output = reports / 'V8_FUNDING_MARK_INDEX_HEADER_CORRECTION_20261002_V1.json'
with output.open('x') as stream:
    json.dump(result, stream, indent=2, allow_nan=False)
    stream.write('\n')
event = dict.fromkeys(FIELDS)
event.update(
    event_id='v8-funding-mark-index-source-format-20261002-v1:header-synopsis-correction',
    event_type='OPERATIONAL_SOURCE_ACCEPTANCE_CORRECTION',
    experiment_id='V8-FUNDING-MARK-INDEX-SOURCE-20261002-V1',
    git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    data_manifest_hash=sha(acceptance_path), protocol_hash=sha(protocol_path),
    feature_set='NONE_SOURCE_METADATA_ONLY', labels='NONE', model_family='NONE',
    hyperparameters={'qa_sha256': sha(qa_path), 'source_sha256': sha(__file__)},
    seed=None, thresholds={'verified_price_proxy_headers': 16},
    cost_assumptions='UNCHANGED_NOT_EVALUATED', all_folds='SOURCE_METADATA_ONLY',
    success_failure=result['status'],
    reason_for_next_experiment='Correct one narrative header synopsis before root module acceptance; no research queue expansion',
    result_influenced_later_choice='NO_MODEL_RESULTS', fits=0,
    output_path=str(output), output_sha256=sha(output),
)
registered = append_event(ROOT / 'reports/experiment_registry.jsonl', event)
print(json.dumps({'status': result['status'], 'output_sha256': sha(output),
                  'record_sha256': registered['record_sha256'], 'source_sha256': sha(__file__)}))
