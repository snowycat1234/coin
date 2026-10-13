"""Selected-executor read-only input gate; never constructs a simulator."""
import hashlib,json
from pathlib import Path
from freeze_candidate import verify,sha
HERE=Path(__file__).resolve().parent
def bindings():
    plan=json.loads((HERE/'CASE_BINDINGS.json').read_text())
    if [c['year'] for c in plan['cases']]!=[2021,2023,2024] or plan['modes']!=['HEADROOM'] or plan['case_count']!=3:
        raise ValueError('Exactly three fixed candidate wallets required')
    return plan
def require_publication():
    p=HERE/'PUBLICATION_RECEIPT.json';r=json.loads(p.read_text())
    if r.get('status')!='PASS_EXACT_PRE_GO_REMOTE_PUBLICATION' or r.get('remote_verified') is not True or r.get('freeze_manifest_SHA256')!=sha(HERE/'FROZEN_CODE.json') or r.get('review_receipt_SHA256')!=sha(HERE/'REVIEW_RECEIPT.json'):
        raise RuntimeError('Exact remote preregistration required before GO')
    return {'publication_receipt_SHA256':sha(p)}
def paths(case,workspace,source_root=None,target_archive=None,feature_archive=None):
    workspace=Path(workspace)
    return (Path(source_root) if source_root else workspace/Path(case['source_index_local_locator']).parent,
            Path(target_archive) if target_archive else workspace/case['target_archive_local_locator'],
            Path(feature_archive) if feature_archive else HERE/'features'/f"Y{case['year']}.npz")
def check(workspace=None,years=(2021,2023,2024),source_root=None,target_archive=None,feature_archive=None):
    import numpy as np
    from feature_tape import FeatureTape
    workspace=HERE.parent if workspace is None else Path(workspace);verify(workspace)
    selected=[c for c in bindings()['cases'] if c['year'] in years]
    if not selected or len(set(years))!=len(years) or set(years)!={c['year'] for c in selected}:
        raise ValueError('Selected years outside fixed candidate plan')
    if len(selected)!=1 and any(x is not None for x in (source_root,target_archive,feature_archive)):
        raise ValueError('Explicit source/target/feature paths select exactly one year')
    receipts=[]
    for c in selected:
        if c['year']==2021:
            cube=workspace/c['initial_daily_sizing_cube_locator']
            if sha(cube)!=c['initial_daily_sizing_cube_SHA256']:
                raise ValueError('Original2021 completed initial sizing close binding changed')
        source,target,feature=paths(c,workspace,source_root,target_archive,feature_archive)
        if sha(source/'SOURCE_INDEX.json')!=c['source_index_SHA256'] or sha(target)!=c['target_archive_SHA256']:
            raise ValueError('Original source/target bytes changed')
        index=json.loads((source/'SOURCE_INDEX.json').read_text())
        for rec in index['months']:
            p=source/'months'/(rec['month']+'.npz')
            if sha(p)!=rec['source_NPZ_SHA256'] or p.stat().st_size!=rec['source_NPZ_bytes']:raise ValueError('Original month changed')
        for name,rec in index['files'].items():
            p=source/name
            if sha(p)!=rec['SHA256'] or p.stat().st_size!=rec['bytes']:raise ValueError('Original metadata changed')
        with np.load(target,allow_pickle=False) as z:
            w=z[c['arm']]
            if w.dtype.str!=c['target_dtype'] or list(w.shape)!=c['target_shape'] or hashlib.sha256(w.tobytes()).hexdigest()!=c['target_array_SHA256']:
                raise ValueError('Frozen target array changed')
            np.testing.assert_array_equal(z['decision_us'],np.arange(*c['calendar'],86_400_000_000,dtype=np.int64))
            if not np.isfinite(w).all() or np.abs(w).max()>.3+1e-12 or np.abs(w).sum(axis=1).max()>.6+1e-12:raise ValueError('Target caps changed')
            if tuple(z['symbol_order'])!=tuple(c['symbols']):raise ValueError('Target symbol order changed')
        m=json.loads((HERE/'features'/f"Y{c['year']}.json").read_text());tape=FeatureTape.load(feature,m)
        if tape.binding['source_index_SHA256']!=c['source_index_SHA256']:raise ValueError('Feature/source identity differs')
        receipts.append({'year':c['year'],'source_root':str(source.resolve()),'target_archive':str(target.resolve()),
                         'feature_archive':str(feature.resolve()),'feature_binding':tape.binding})
    return {'status':'PASS_FIXED_CANDIDATE_INPUTS_ZERO_HISTORY','wallets_started':0,'new_fits':0,'new_source_requests':0,'selected_cases':receipts}
