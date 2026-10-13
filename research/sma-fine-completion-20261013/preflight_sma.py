"""Three fixed original-SMA source/target admission; no wallet construction."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from freeze_sma import verify
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
REVIEWED=verify()
BINDINGS_SHA256=REVIEWED['files_SHA256']['CASE_BINDINGS.json']
DAY=86_400_000_000
EXPECTED={(2023,'SMA200_10PCT'),(2024,'SMA200_10PCT'),(2025,'SMA200_10PCT')}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bindings():
    verify();b=json.loads((HERE/'CASE_BINDINGS.json').read_text())
    if (sha(HERE/'CASE_BINDINGS.json')!=BINDINGS_SHA256 or b['case_count']!=3 or b['modes']!=['ORIGINAL']
            or b['new_historical_wallets_executed']!=0 or len(b['cases'])!=3
            or {(c['year'],c['arm']) for c in b['cases']}!=EXPECTED):
        raise ValueError('Fixed three-case original SMA plan changed')
    return b

def require_publication():
    p=HERE/'PUBLICATION_RECEIPT.json'
    if not p.is_file():raise RuntimeError('Exact code/targets remote publication required before GO')
    r=json.loads(p.read_text())
    if (r.get('status')!='PASS_EXACT_PRE_GO_REMOTE_PUBLICATION' or r.get('remote_verified') is not True
            or r.get('freeze_manifest_SHA256')!=sha(HERE/'FROZEN_CODE.json')
            or r.get('case_bindings_SHA256')!=sha(HERE/'CASE_BINDINGS.json')
            or r.get('publication_base_commit')!=bindings()['publication_base_commit']
            or r.get('review_receipt_SHA256')!=sha(HERE/'REVIEW_RECEIPT.json')):
        raise RuntimeError('Exact code/targets remote publication required before GO')
    return dict(publication_receipt_SHA256=sha(p))

def validate_terminal(times,available,opens,marks,volume,end):
    import numpy as np
    M=60_000_000
    if (not np.array_equal(times,np.arange(end-6*M,end,M,dtype=np.int64))
            or not np.array_equal(available,times+M)):
        raise ValueError('Actual final six frozen quote clocks required')
    for a in (opens,marks):
        if a.shape!=(6,) or not np.isfinite(a).all() or (a<=0).any():
            raise ValueError('Actual positive final prices required')
    if volume.shape!=(6,) or not np.isfinite(volume).all() or (volume<0).any():
        raise ValueError('Actual final prior quote-volume required')
    return {'signal_us':end-6*M,'attempt_us':[int(t+1) for t in times[1:]],'attempt_count':5,
            'prior_capacity_available_us':[int(t) for t in available[:-1]],
            'all_attempts_before_end':bool((times[1:]+1<end).all())}

def check():
    import numpy as np
    b=bindings();oldfine=ROOT/'coin_quantity_resolution_20261013'
    if (sha(oldfine/'FINE_PROFILE.json')!=b['fine_profile_SHA256']
            or sha(oldfine/'CASE_BINDINGS.json')!=b['old_fine_plan_SHA256']
            or sha(oldfine/'state_20261013/RUN_BINDING.json')!=b['old_fine_run_binding_SHA256']):
        raise ValueError('Reviewed fine profile/control plan changed')
    mpath=ROOT/'coin_margin_protective_policy_20261013/RUN_MANIFEST.json'
    if sha(mpath)!=b['guard_manifest_SHA256']:raise ValueError('Original SMA target registry changed')
    indexed={c['case_id']:c for c in json.loads(mpath.read_text())['cases']}
    term=json.loads((HERE/'TERMINAL_QUOTE_GATE.json').read_text())
    if (sha(HERE/'TERMINAL_QUOTE_GATE.json')!=b['terminal_quote_gate_SHA256']
            or term['status']!='PASS_ACTUAL_FIVE_TERMINAL_QUOTES_NO_FILL_PROMISE'):
        raise ValueError('Terminal quote admission changed')
    total_months=0
    for c in b['cases']:
        old=indexed[c['case_id']]
        for k in ('source_index_local_locator','source_index_SHA256','target_archive_local_locator',
                  'target_archive_SHA256','target_array_SHA256','target_dtype','target_shape','calendar','symbols'):
            if c[k]!=old[k]:raise ValueError('Original source/target registry changed: '+k)
        if c['protective_enabled'] is not False:raise ValueError('Guard disabled')
        src=ROOT/c['source_index_local_locator'];archive=ROOT/c['target_archive_local_locator']
        if sha(src)!=c['source_index_SHA256'] or sha(archive)!=c['target_archive_SHA256']:
            raise ValueError('Frozen source/target archive changed')
        idx=json.loads(src.read_text())
        if idx['calendar']!=c['calendar'] or idx['symbol_order']!=c['symbols']:raise ValueError('Source calendar/order')
        for row in idx['months']:
            p=src.parent/'months'/f"{row['month']}.npz"
            if p.stat().st_size!=row['source_NPZ_bytes'] or sha(p)!=row['source_NPZ_SHA256']:raise ValueError('Month bits')
            total_months+=1
        for name in ('DAILY.json','EVENTS.json'):
            p=src.parent/name
            if p.stat().st_size!=idx['files'][name]['bytes'] or sha(p)!=idx['files'][name]['SHA256']:raise ValueError('Metadata bits')
        with np.load(archive,allow_pickle=False) as a:
            w=a[c['arm']]
            if (w.dtype.str!=c['target_dtype'] or list(w.shape)!=c['target_shape']
                or hashlib.sha256(w.tobytes()).hexdigest()!=c['target_array_SHA256']):raise ValueError('Target bits')
            np.testing.assert_array_equal(a['decision_us'],np.arange(*c['calendar'],DAY,dtype=np.int64))
            if tuple(a['symbol_order'])!=tuple(c['symbols']):raise ValueError('Target order')
            if not np.isfinite(w).all() or np.abs(w).max()>.3+1e-12 or np.abs(w).sum(axis=1).max()>.6+1e-12:raise ValueError('Target caps')
            if c['year'] in (2023,2025):
                p=ROOT/c['standalone_original_target_local_locator']
                if sha(p)!=c['standalone_original_target_SHA256']:raise ValueError('Standalone archive changed')
                with np.load(p,allow_pickle=False) as s:
                    if s[c['arm']].tobytes()!=w.tobytes():raise ValueError('Original standalone SMA numerical bits changed')
        for control in c['existing_fine_controls'].values():
            p=ROOT/control['state_local_locator']
            for name,h in control['files_SHA256'].items():
                if sha(p/name)!=h:raise ValueError('Existing fine control changed')
            cb=json.loads((p/'BINDING.json').read_text())
            if cb['source_index_SHA256']!=c['source_index_SHA256'] or cb['fine_profile_SHA256']!=b['fine_profile_SHA256']:
                raise ValueError('Read-only control source/profile differs')
    return {'status':'PASS_THREE_FINE_ORIGINAL_SMA_ZERO_HISTORY','source_months_verified':total_months,
        'planned_new_wallets':3,'historical_wallets_started':0,'old_wallets_rerun':0,'new_fits':0,
        'retained_2026_opened':0,'provider_downloads':0,'protective_enabled':False,
        'parent_GO_required':True,'publication_required_before_launch':True}
