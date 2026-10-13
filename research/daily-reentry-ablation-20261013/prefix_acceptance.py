"""Bit-exact financial identity through the first newly allowed same-side signal."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np

MINUTE = 60_000_000

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def financial_prefix(minute, trades, funding, *, start_us, through_us):
    rows = len(minute) if through_us is None else max(0, (through_us - start_us) // MINUTE)
    return {'minute': np.asarray(minute)[:rows],
            'trades': [r for r in trades if through_us is None or r['event_us'] <= through_us],
            'funding': [r for r in funding if through_us is None or r['event_us'] <= through_us]}

def compare_prefix(new, old, *, through_us):
    if new['minute'].shape != old['minute'].shape or new['minute'].dtype != old['minute'].dtype:
        raise ValueError('Guard prefix minute shape/dtype differs')
    # Equality means all financial bits, including signed zero, not allclose.
    if new['minute'].tobytes(order='C') != old['minute'].tobytes(order='C'):
        raise ValueError('Guard prefix financial minute bits differ')
    for key in ('trades', 'funding'):
        if json.dumps(new[key], sort_keys=True, separators=(',', ':'), allow_nan=False) != \
                json.dumps(old[key], sort_keys=True, separators=(',', ':'), allow_nan=False):
            raise ValueError(f'Guard prefix {key} differ')
    return {'status': 'PASS_ALL_FINANCIAL_MINUTE_TRADE_FUNDING_PREFIX_BITS',
            'through_us_inclusive': through_us,
            'minute_rows': len(new['minute']),
            'minute_raw_SHA256': hashlib.sha256(new['minute'].tobytes(order='C')).hexdigest(),
            'trade_legs': len(new['trades']), 'funding_rows': len(new['funding']),
            'guard_wallets_rerun': 0}

def load_minute(recovery: Path):
    pointer = json.loads((recovery / 'POINTER.json').read_text())
    arrays = []
    for row in pointer['chunks']:
        path = recovery / row['path']
        if sha(path) != row['SHA256']:
            raise ValueError('Guard lossless chunk bytes changed')
        with np.load(path, allow_pickle=False) as z:
            if z.files != ['minute_chunk']:
                raise ValueError('Lossless checkpoint schema changed')
            array = z['minute_chunk'].copy()
        if list(array.shape) != [row['rows'], row['columns']] or array.dtype != np.float64:
            raise ValueError('Lossless checkpoint minute dimensions changed')
        arrays.append(array)
    if sum(map(len, arrays)) != pointer['completed_minutes']:
        raise ValueError('Lossless checkpoint completed count differs')
    return np.concatenate(arrays) if arrays else np.empty((0, 36), dtype=np.float64)

def verify_result_prefix(result, case, root: Path):
    guard_ref = case['fine_comparators']['GUARD50']
    state = root / guard_ref['state_locator']
    for name in ('account', 'pointer'):
        record = guard_ref['files'][name]
        if sha(root / record['locator']) != record['SHA256']:
            raise ValueError('Predeclared guard comparator changed')
    old = json.loads((state / 'ACCOUNT.json').read_text())
    through = result['daily_reentry_policy']['first_same_direction_signal_us']
    if through is None:
        for field in ('completed_minutes', 'stop_us', 'completion', 'account_status'):
            if result['summary'][field] != old['summary'][field]:
                raise ValueError('No-new-rule guard horizon/status identity differs: ' + field)
    else:
        if not case['calendar'][0] <= through < case['calendar'][1] or through % 86_400_000_000:
            raise ValueError('First same-direction permission is not a frozen new daily clock')
    # result minute excludes close_us (the checkpoint columns do too).
    numeric = result['minute'].drop('close_us').to_numpy()
    new_prefix = financial_prefix(numeric, result['trades'], result['funding'],
                                 start_us=case['calendar'][0], through_us=through)
    old_prefix = financial_prefix(load_minute(state / 'recovery'), old['trades'], old['funding'],
                                 start_us=case['calendar'][0], through_us=through)
    receipt = compare_prefix(new_prefix, old_prefix, through_us=through)
    receipt.update(comparator_case_id=guard_ref['case_id'],
                   comparator_pointer_SHA256=guard_ref['files']['pointer']['SHA256'],
                   no_same_direction_signal_requires_full_path_identity=through is None)
    return receipt
