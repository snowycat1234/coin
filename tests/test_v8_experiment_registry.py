"""Necessary audit invariants: history, unknown metadata and corruption rejection."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.research_v8.registry import FIELDS, append_event, read_verified


def event(name):
    e = dict.fromkeys(FIELDS)
    e.update(experiment_id=name, event_id=name, event_type='LEGACY_ARTIFACT_INVENTORY')
    return e


def test_append_preserves_exact_prefix_and_rejects_duplicate(tmp_path):
    p = tmp_path/'registry.jsonl'
    append_event(p, event('failed-run'))
    before = p.read_bytes()
    append_event(p, event('successful-run'))
    assert p.read_bytes().startswith(before)
    assert len(read_verified(p.read_bytes())) == 2
    with pytest.raises(ValueError, match='already recorded'):
        append_event(p, event('failed-run'))


def test_missing_or_unknown_metadata_cannot_start_formal_run(tmp_path):
    e = event('formal')
    e['event_type'] = 'FORMAL_START'
    with pytest.raises(ValueError, match='must be known'):
        append_event(tmp_path/'registry.jsonl', e)
    assert not (tmp_path/'registry.jsonl').exists()


def test_corruption_and_partial_write_rejected_without_repair(tmp_path):
    p = tmp_path/'registry.jsonl'
    append_event(p, event('original'))
    correct = p.read_bytes()
    corrupt = correct.replace(b'original', b'modified')
    with pytest.raises(ValueError, match='changed'):
        read_verified(corrupt)
    with pytest.raises(ValueError, match='Incomplete'):
        read_verified(correct[:-1])
    assert p.read_bytes() == correct


def test_formal_depth_family_is_rejected_before_p1(tmp_path):
    e = {key: {} for key in FIELDS}
    e.update(experiment_id='deep', event_id='deep', event_type='FORMAL_START',
             git_commit='a'*40, data_manifest_hash='b'*64, protocol_hash='c'*64,
             model_family='TCN', seed=20261001, success_failure='RUNNING',
             reason_for_next_experiment='preregistered', result_influenced_later_choice=False)
    with pytest.raises(ValueError, match='remains gated'):
        append_event(tmp_path/'registry.jsonl', e)
    assert not (tmp_path/'registry.jsonl').exists()
