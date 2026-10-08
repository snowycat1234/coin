"""Explicit candidate masks and a frozen causal RANK checkpoint schedule."""
from __future__ import annotations
import hashlib
import json
import numpy as np
from scripts.investment.perpetual_directional import need


def candidate_mask(value):
    mask = np.asarray(value)
    need(mask.shape == (6,) and np.all((mask == 0) | (mask == 1)),
         'Explicit six-candidate availability mask')
    mask = mask.astype(bool)
    need(mask.any(), 'Every state needs at least one available candidate')
    return mask


def digest(value, name):
    need(isinstance(value, str) and len(value) == 64
         and all(c in '0123456789abcdef' for c in value), 'Exact SHA256 identity: ' + name)
    return value


class CheckpointSchedule:
    """A declared gap means no usable RANK model, never a fabricated checkpoint.

    available_us is when the fitted artifact was available. training_label_end_us
    is the latest mature label used by that artifact, not its sample start date.
    Future entries may be declared but never resolve before their interval.
    """

    FIELDS = {'start_us', 'end_us', 'available_us', 'training_label_end_us', 'checkpoint_sha256'}

    def __init__(self, entries):
        items = []
        for entry in entries:
            need(set(entry) == self.FIELDS, 'Explicit checkpoint schedule fields')
            for key in self.FIELDS - {'checkpoint_sha256'}:
                need(type(entry[key]) is int, 'Integer microsecond checkpoint clock: ' + key)
            digest(entry['checkpoint_sha256'], 'checkpoint_sha256')
            need(0 <= entry['training_label_end_us'] <= entry['available_us'] <= entry['start_us']
                 < entry['end_us'], 'Checkpoint training labels and publication must precede use')
            items.append(dict(entry))
        items.sort(key=lambda x: x['start_us'])
        need(all(a['end_us'] <= b['start_us'] for a, b in zip(items, items[1:])),
             'Checkpoint schedule intervals must not overlap')
        self._json = json.dumps(items, sort_keys=True, separators=(',', ':'))
        self.sha256 = hashlib.sha256(self._json.encode()).hexdigest()

    @property
    def entries(self):
        return json.loads(self._json)

    def at(self, decision_us):
        return next((x['checkpoint_sha256'] for x in self.entries
                     if x['start_us'] <= decision_us < x['end_us']), None)

    def validate_binding(self, binding, decision_us, mask):
        mask = candidate_mask(mask)
        need(binding.get('rank_checkpoint_schedule_sha256') == self.sha256,
             'Exact causal checkpoint schedule binding')
        expected = self.at(decision_us)
        current = binding.get('rank_checkpoint_sha256')
        if mask[5]:
            need(expected is not None and current == expected,
                 'Available RANK requires the causally scheduled checkpoint')
        else:
            need(current is None or (expected is not None and current == expected),
                 'Unavailable RANK cannot carry a future or foreign checkpoint')


def scheduled_identity(binding):
    """Fixed non-RANK identity plus the entire schedule; current RANK may change."""
    return {key: binding.get(key) for key in (
        'expert_order', 'mapper_sha256', 'expert_identity_sha256',
        'rank_checkpoint_schedule_sha256',
    )}


def label_mask(row):
    if 'e6_available' not in row:
        need(np.asarray(row['e6_valid']).shape == (6,) and all(row['e6_valid']),
             'Partial labels require an explicit availability mask')
        return candidate_mask([True] * 6)
    mask = candidate_mask(row['e6_available'])
    valid = np.asarray(row['e6_valid'])
    need(valid.shape == (6,) and np.all((valid == 0) | (valid == 1))
         and np.array_equal(valid.astype(bool), mask),
         'All available candidates must have complete native labels')
    return mask


def masked_rewards(row, mask):
    raw = row['e6_rewards_USDT']
    need(len(raw) == 6, 'Six reward slots including explicit missing slots')
    y = np.asarray([np.nan if x is None else float(x) for x in raw])
    need(np.isfinite(y[mask]).all() and np.isnan(y[~mask]).all(),
         'Available rewards finite; unavailable rewards null or NaN, never zero')
    return y
