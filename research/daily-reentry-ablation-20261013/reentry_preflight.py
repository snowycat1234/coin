"""Read-only source, exact targets, and already-completed comparator identity."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from reentry_freeze import verify, sha

REVIEWED = verify()
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FINE = ROOT / 'coin_quantity_resolution_20261013'
EXPECTED = {(2024, 'STATIC50'), (2025, 'STATIC50'), (2025, 'COMBINED')}

def bindings():
    if verify()['freeze_manifest_SHA256'] != REVIEWED['freeze_manifest_SHA256']:
        raise ValueError('Prepared module changed after import')
    document = json.loads((HERE / 'CASE_BINDINGS.json').read_text())
    if (document['new_wallets'] != 3 or document['comparator_wallets_to_rerun'] != 0
            or document['mode'] != 'FRESH_DAILY_REENTRY'
            or {(c['year'], c['arm']) for c in document['cases']} != EXPECTED
            or len(document['cases']) != 3):
        raise ValueError('Exactly three predeclared ablation cases required')
    old = json.loads((FINE / 'CASE_BINDINGS.json').read_text())
    index = {c['case_id']: c for c in old['cases']}
    if document['fine_profile_SHA256'] != sha(FINE / 'FINE_PROFILE.json'):
        raise ValueError('Reused fine profile differs')
    for case in document['cases']:
        original = index[case['case_id']]
        for key in original:
            if case[key] != original[key]:
                raise ValueError(f'Frozen fine case field differs: {case["case_id"]}, {key}')
        for mode in ('ORIGINAL', 'GUARD50'):
            comparator = case['fine_comparators'][mode]
            for record in comparator['files'].values():
                if sha(ROOT / record['locator']) != record['SHA256']:
                    raise ValueError(f'Completed fine comparator changed: {case["case_id"]}, {mode}')
            state = ROOT / comparator['state_locator']
            binding = json.loads((state / 'BINDING.json').read_text())
            pointer = json.loads((state / 'recovery/POINTER.json').read_text())
            result = json.loads((state / 'RESULT.json').read_text())
            receipt = json.loads((ROOT / comparator['files']['cold_receipt']['locator']).read_text())
            if (pointer['binding'] != binding or pointer['state_hash'] != result['genuine_state_hash']
                    or receipt['status'] != 'PASS_COLD_RESTORE_ZERO_ADVANCE'
                    or receipt['financial_advances'] != 0
                    or receipt['state_hash'] != pointer['state_hash']
                    or receipt['pointer_SHA256'] != comparator['files']['pointer']['SHA256']
                    or receipt['result_SHA256'] != comparator['files']['result']['SHA256']
                    or binding['target_array_SHA256'] != case['target_array_SHA256']
                    or binding['source_index_SHA256'] != case['source_index_SHA256']
                    or binding['fine_profile_SHA256'] != document['fine_profile_SHA256']):
                raise ValueError('Completed comparator journal/checkpoint identity differs')
    return document

def check(*, full_source=True, full_comparators=True):
    import numpy as np
    document = bindings()
    for case in document['cases']:
        if (sha(ROOT / case['source_index_local_locator']) != case['source_index_SHA256']
                or sha(ROOT / case['target_archive_local_locator']) != case['target_archive_SHA256']):
            raise ValueError('Frozen target/source bytes differ')
        with np.load(ROOT / case['target_archive_local_locator'], allow_pickle=False) as z:
            array = z[case['arm']]
            if (hashlib.sha256(array.tobytes(order='C')).hexdigest() != case['target_array_SHA256']
                    or array.dtype.str != case['target_dtype'] or list(array.shape) != case['target_shape']
                    or not np.array_equal(z['decision_us'], np.arange(*case['calendar'], 86_400_000_000))
                    or tuple(z['symbol_order']) != tuple(case['symbols'])):
                raise ValueError('Frozen daily matrix differs')
        if full_comparators:
            for row in case['fine_comparators'].values():
                recovery = ROOT / row['state_locator'] / 'recovery'
                pointer = json.loads((recovery / 'POINTER.json').read_text())
                if sha(recovery / pointer['snapshot_path']) != pointer['snapshot_SHA256']:
                    raise ValueError('Completed comparator snapshot changed')
                for chunk in pointer['chunks']:
                    if sha(recovery / chunk['path']) != chunk['SHA256']:
                        raise ValueError('Completed comparator minute bits changed')
    if full_source:
        # This pre-existing gate checks frozen market-month/target bytes and
        # constructs no wallet. Import its unique module name, preserve its
        # original freeze_bootstrap dependency, and never edit old files.
        sys.path.insert(0, str(FINE))
        spec = importlib.util.spec_from_file_location('old_fine_readonly_preflight', FINE / 'preflight.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.check(full_source=True)
    return {'status': 'PASS_PREPARED_READONLY_NO_NEW_HISTORY', 'new_wallets': 3,
            'comparator_wallets_to_rerun': 0, 'new_historical_wallets_executed': 0,
            'full_source_checked': full_source, 'full_comparator_bytes_checked': full_comparators,
            'independent_review_and_parent_GO_required': True}
