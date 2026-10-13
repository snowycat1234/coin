"""Four-case source/target freeze admission only; does not construct wallets."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from freeze_2021 import verify
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
REVIEWED=verify()
BINDINGS_SHA256=REVIEWED['files_SHA256']['CASE_BINDINGS.json']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def bindings():
    verify();b=json.loads((HERE/'CASE_BINDINGS.json').read_text())
    if (sha(HERE/'CASE_BINDINGS.json')!=BINDINGS_SHA256 or b['case_count']!=4 or b['modes']!=['ORIGINAL']
            or b['new_historical_wallets_executed']!=0):raise ValueError('Fixed four-case full2021 plan changed')
    return b

def require_publication():
    p=HERE/'PUBLICATION_RECEIPT.json'
    if not p.is_file():
        raise RuntimeError('Exact frozen code and targets must be published and remotely verified before GO')
    r=json.loads(p.read_text())
    if (r.get('status')!='PASS_EXACT_PRE_GO_REMOTE_PUBLICATION' or r.get('remote_verified') is not True
            or r.get('freeze_manifest_SHA256')!=sha(HERE/'FROZEN_CODE.json')
            or r.get('case_bindings_SHA256')!=sha(HERE/'CASE_BINDINGS.json')
            or r.get('source_commit')!=bindings()['source_commit']):
        raise RuntimeError('Exact frozen code and targets must be published and remotely verified before GO')
    return dict(publication_receipt_SHA256=sha(p))

def check():
    import numpy as np
    from prepare_targets import source_gate
    from targets_2021 import ARMS,DAY,SYMBOLS,us
    source_gate();b=bindings()
    if {(c['year'],c['arm']) for c in b['cases']}!={(2021,a) for a in ARMS}:raise ValueError('Four fixed arm/year cases changed')
    for name,key in [('TERMINAL_QUOTE_GATE.json','terminal_quote_gate_SHA256'),('targets/TARGET_PROOF.json','target_proof_SHA256')]:
        if sha(HERE/name)!=b[key]:raise ValueError('Target/terminal admission changed')
    term=json.loads((HERE/'TERMINAL_QUOTE_GATE.json').read_text())
    if term['status']!='PASS_ACTUAL_FIVE_TERMINAL_QUOTES_NO_FILL_PROMISE' or term['terminal_paid_flat_assumed'] is not False:
        raise ValueError('Actual terminal quotes required without paid-flat promise')
    for c in b['cases']:
        if c['protective_enabled'] is not False or c['calendar']!=[us(2021),us(2022)]:raise ValueError('Full year/protective disabled required')
        for locator,key in [('source_index_local_locator','source_index_SHA256'),('target_archive_local_locator','target_archive_SHA256')]:
            if sha(ROOT/c[locator])!=c[key]:raise ValueError('Frozen source/target changed')
        with np.load(ROOT/c['target_archive_local_locator'],allow_pickle=False) as a:
            np.testing.assert_array_equal(a['decision_us'],np.arange(us(2021),us(2022),DAY,dtype=np.int64))
            if tuple(a['symbol_order'])!=SYMBOLS:raise ValueError('CORE5 order changed')
            w=a[c['arm']]
            if (w.dtype.str!=c['target_dtype'] or list(w.shape)!=c['target_shape']
                    or hashlib.sha256(w.tobytes()).hexdigest()!=c['target_array_SHA256']):raise ValueError('Target numerical bits changed')
            np.testing.assert_array_equal(a['EXACTHALF'],.5*a['STATIC50']+.5*a['SMA200_10PCT'])
            if not (a['STATIC50'][:91]==0).all() or not (a['VOL_MATCHED'][:91]==0).all():raise ValueError('Original early match cash must remain')
    return dict(status='PASS_FOUR_FULL2021_FINE_CASES_ZERO_HISTORY',planned_new_wallets=4,historical_wallets_started=0,
                old_wallets_rerun=0,retained_2026_opened=0,protective_enabled=False,parent_GO_required=True,
                independent_exact_byte_review_required=True,publication_required_before_launch=True)
