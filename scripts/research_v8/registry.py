"""Append-only experiment receipts; unknown historical metadata stays unknown."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

FIELDS = ('experiment_id', 'git_commit', 'data_manifest_hash', 'protocol_hash',
          'feature_set', 'labels', 'model_family', 'hyperparameters', 'seed',
          'thresholds', 'cost_assumptions', 'all_folds', 'success_failure',
          'reason_for_next_experiment', 'result_influenced_later_choice')


def canonical(record):
    return json.dumps(record, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode()


def read_verified(payload: bytes):
    if payload and not payload.endswith(b'\n'):
        raise ValueError('Incomplete registry tail: preserve and investigate, do not overwrite')
    previous = None
    records = []
    for line in payload.splitlines():
        record = json.loads(line)
        digest = record.pop('record_sha256')
        if record['previous_record_sha256'] != previous:
            raise ValueError('Registry chain mismatch')
        if hashlib.sha256(canonical(record)).hexdigest() != digest:
            raise ValueError('Registry record bytes changed')
        previous = digest
        record['record_sha256'] = digest
        records.append(record)
    return records


def append_event(path: Path, event: dict):
    if set(FIELDS) - event.keys():
        raise ValueError('Missing required registry metadata')
    if event.get('event_type') == 'FORMAL_START':
        for field in FIELDS:
            if event[field] is None or event[field] == 'UNKNOWN':
                raise ValueError('Formal run metadata must be known: ' + field)
        for field, size in [('git_commit', 40), ('data_manifest_hash', 64), ('protocol_hash', 64)]:
            value = event[field]
            if len(value) != size or any(c not in '0123456789abcdef' for c in value):
                raise ValueError('Invalid frozen identity: ' + field)
        if event['model_family'] not in ('RIDGE', 'XGB_FIXED', 'FIXED_MULTISCALE_LINEAR_TREE', 'NONE'):
            raise ValueError('V8 formal depth/family research remains gated; use first layer only')
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError('Registry must be an ordinary local file')
    with path.open('a+b') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        history = read_verified(f.read())
        if any(r['event_id'] == event['event_id'] for r in history):
            raise ValueError('Event already recorded; append a new event, never replace')
        item = dict(event, created_utc=datetime.now(UTC).isoformat(),
                    previous_record_sha256=history[-1]['record_sha256'] if history else None)
        item['record_sha256'] = hashlib.sha256(canonical(item)).hexdigest()
        f.seek(0, os.SEEK_END)
        f.write(canonical(item) + b'\n')
        f.flush()
        os.fsync(f.fileno())
        return item
