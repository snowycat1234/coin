"""Append precise completed V8 operation/audit receipts without fabricating trials."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path('/mnt/d/codex/coin')
sys.path.insert(0, str(ROOT))
from scripts.research_v8.registry import FIELDS, append_event, read_verified

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('reports', nargs='+')
args = p.parse_args()
ledger = ROOT/'reports/experiment_registry.jsonl'
previous = read_verified(ledger.read_bytes())
known = {x['event_id'] for x in previous}
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
for name in args.reports:
    path = (ROOT/name).resolve()
    assert path.is_relative_to((ROOT/'reports').resolve()) and path.is_file()
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    event_id = 'v8-operation-result:' + str(path.relative_to(ROOT)) + ':' + digest
    if event_id in known:
        continue
    e = dict.fromkeys(FIELDS)
    e.update(event_type='OPERATIONAL_RESULT', event_id=event_id,
        experiment_id='v8-operation:' + path.stem,
        git_commit=head, git_commit_scope='HEAD when receipt registered; dirty source hashes separately bound',
        data_manifest_hash=digest, data_manifest_scope='operation output receipt; not a market data manifest',
        protocol_hash=hashlib.sha256((ROOT/'protocols/LABEL_CONTRACT_V8.json').read_bytes()).hexdigest(),
        feature_set='NO_NEW_MARKET_FEATURES', labels='NO_NEW_MARKET_LABELS',
        model_family='NONE', hyperparameters={}, seed=value.get('seed'),
        thresholds='NO_MARKET_THRESHOLD_TEST', cost_assumptions='NOT_EVALUATED',
        all_folds=[], success_failure=value.get('status') or value.get('implementation_status') or 'UNKNOWN',
        reason_for_next_experiment='Resolve V8 contract, source and causality prerequisites before any market fit',
        result_influenced_later_choice=path.name.startswith('V8_LABEL_ADVERSARIAL_AUDIT'),
        artifact_path=str(path.relative_to(ROOT)), artifact_sha256=digest,
        exact_command_receipt='existing task progress and named report; unavailable fields remain null',
        model_research_trial_count=0, locked_consumed=False,
        source_hashes=value.get('source_hashes') or value.get('audited_sources_sha256') or {})
    append_event(ledger, e)
    print(json.dumps({'registered': e['experiment_id'], 'status': e['success_failure']}), flush=True)
