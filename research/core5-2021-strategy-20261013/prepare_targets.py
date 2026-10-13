"""Exact source/mask/golden admission and four fixed targets. No historical PnL."""
from __future__ import annotations
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'): os.environ[k]='1'
import hashlib
import json
from pathlib import Path
import resource
import time
import numpy as np
from targets_2021 import ARMS,DAY,SYMBOLS,asset_masks,build,load_cube,us,load_originals
from terminal_quotes import check as terminal_check

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
SOURCE=ROOT/'coin_2021_source_closure_20261013/prepared_2021'
CUBE_SHA={2023:'1c500e9d5b0244a1daaabc597d7cc5ae97a21a156cc42d8a44a1504b821e599f',
          2025:'88a698ceed87603a36ca2bcf4ae76d805aa90085b344bbeee47e58a8c9770add'}
SAVED_SHA={2023:('e81bf92d3599a6d3059ab462ac984ed9cc066647b1ea839d6147d2e10c40359f',
                 '2047463e7be0ea4f086de744018d65924568dbd2e37f5960e75951c32746abf7'),
           2025:('5e525cf65a5519a739d7ce2baf9c83809af44a1b9722f37fcf9891ede79bbf4e',
                 '595425c86df274c6c6105d058d478d772c75ae75cb9c6d2c3ca8c5b9b4c1d968')}

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):
    with Path(p).open('x') as f: json.dump(v,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')

def source_gate():
    if sha(SOURCE/'SOURCE_INDEX.json')!='13a0d6551deef1e5cc6865ff4487ebf3fed5dd518364e909fb25ab228838eb33':
        raise ValueError('SOURCE_STOP: source closure bytes changed')
    rpath=ROOT/'coin_2021_source_closure_review_20261013/INDEPENDENT_REVIEW.json'
    review=json.loads(rpath.read_text())
    if review['status']!='PASS_INDEPENDENT_CACHE_ONLY_SOURCE_REVIEW_WITH_EXPLICIT_LIMITS':
        raise ValueError('SOURCE_STOP: independent source review required')
    index=json.loads((SOURCE/'SOURCE_INDEX.json').read_text())
    if index['calendar_us']!=[us(2021),us(2022)] or index['days']!=365 or index['funding_events']!=5475:
        raise ValueError('SOURCE_STOP: full calendar source contract')
    for rec in index['months']:
        p=SOURCE/'months'/(rec['month']+'.npz')
        if sha(p)!=rec['source_NPZ_SHA256'] or p.stat().st_size!=rec['source_NPZ_bytes']:
            raise ValueError('SOURCE_STOP: monthly body changed')
    for name,rec in index['files'].items():
        if sha(SOURCE/name)!=rec['SHA256'] or (SOURCE/name).stat().st_size!=rec['bytes']:
            raise ValueError('SOURCE_STOP: prepared file changed')
    return dict(source_index_SHA256=sha(SOURCE/'SOURCE_INDEX.json'),
                independent_source_review_SHA256=sha(rpath))

def golden():
    reports={};functions=load_originals()
    for y in (2023,2025):
        cube=ROOT/f'coin_cs_sma_recovery_20261013/inputs/Y{y}.npz'
        if sha(cube)!=CUBE_SHA[y]: raise ValueError('Golden cube changed')
        t,p=load_cube(cube);d=np.arange(us(y),us(y+1),DAY,dtype=np.int64)
        # Exact prior accepted full-five original HOLD reconstruction. Preserve
        # contiguous full-five arithmetic; the SMA body has its own submatrix.
        hold=np.zeros((len(d),5));mask=asset_masks(t,p,d)
        if not mask.all(): raise ValueError('Golden original years require their original fullfive masks')
        for i,at in enumerate(d):
            k=int(np.searchsorted(t,at));past=p[k-30:k+1]
            r=np.diff(past,axis=0)/past[:-1]
            hold[i],_=functions.signed_risk_weights(np.full(5,.6/5),r)
        out,cov,proof=build(t,p,d,original_hold=hold,original_hold_mask=mask)
        sp=ROOT/f'coin_strong_candidates_20261013/STATIC50_Y{y}.npz'
        mp=ROOT/f'coin_strong_candidates_20261013/SMA200_Y{y}.npz'
        if (sha(sp),sha(mp))!=SAVED_SHA[y]: raise ValueError('Golden original target archive changed')
        with np.load(sp,allow_pickle=False) as s,np.load(mp,allow_pickle=False) as m:
            for arm in ('STATIC50','VOL_MATCHED'): np.testing.assert_array_equal(out[arm],s[arm])
            np.testing.assert_array_equal(proof['CS_MATCHED'],s['CS_MATCHED'])
            np.testing.assert_array_equal(cov,s['annual_covariance'])
            if (proof['CS_MATCHED'].tobytes()!=s['CS_MATCHED'].tobytes()
                    or cov.tobytes()!=s['annual_covariance'].tobytes()):
                raise ValueError('Golden CS/covariance numerical bits differ')
            np.testing.assert_array_equal(out['SMA200_10PCT'],m['SMA200_10PCT'])
            for arm,arr in [('STATIC50',s['STATIC50']),('VOL_MATCHED',s['VOL_MATCHED']),
                            ('SMA200_10PCT',m['SMA200_10PCT'])]:
                if out[arm].tobytes()!=arr.tobytes(): raise ValueError('Golden numerical bits differ')
        reports[str(y)]=dict(status='BIT_EXACT_365DAY_FROZEN_ORIGINAL_FOUR_COMPONENTS_AND_COVARIANCE',
                            static_archive_SHA256=sha(sp),sma_archive_SHA256=sha(mp),wallets=0)
    return reports

def prepare():
    start=time.monotonic();gate=source_gate();term=terminal_check();gold=golden()
    cube=ROOT/'coin_cs_sma_recovery_20261013/inputs/Y2023.npz'
    if sha(cube)!=CUBE_SHA[2023]: raise ValueError('SOURCE_STOP: prior-close cube bytes')
    t,p=load_cube(cube)
    # Do not expose later-year values to the2021 formula; only required past and
    # 2021 closes are selected. Saved NPZ outcome fields are never selected.
    scope=(t>=us(2021)-205*DAY)&(t<=us(2022));t=t[scope];p=p[scope]
    d=np.arange(us(2021),us(2022),DAY,dtype=np.int64)
    with np.load(SOURCE/'DAILY_OHLC.npz',allow_pickle=False) as a:
        if tuple(a['symbol_order'])!=SYMBOLS or not a['ready'].all():raise ValueError('SOURCE_STOP: real daily OHLC')
        ids=np.searchsorted(t,a['available_us']);np.testing.assert_array_equal(t[ids],a['available_us'])
        np.testing.assert_array_equal(p[ids],a['close'])
        if p[ids].tobytes()!=a['close'].tobytes():raise ValueError('SOURCE_STOP: real 2021 close bits')
    context=HERE/'ORIGINAL_2021_CONTEXT.npz'
    if sha(context)!='775074cc788949e5b12953f4f22d5b724b653e358b04f44b46ecb5dbc703e7cf':raise ValueError('Original2021 context changed')
    with np.load(context,allow_pickle=False) as a:
        np.testing.assert_array_equal(a['decision_us'],d)
        if tuple(a['symbol_order'])!=SYMBOLS or tuple(a['expert_names'])!=('CASH','VOL_MANAGED_HOLD','CSMOM21'):
            raise ValueError('Original2021 context order changed')
        hold=a['expert_targets'][:,1].copy();mask=a['asset_eligible'][:,1].copy();oldcs=a['expert_targets'][:,2].copy()
    out,cov,proof=build(t,p,d,original_hold=hold,original_hold_mask=mask)
    np.testing.assert_array_equal(proof['CS_ORIGINAL'],oldcs)
    if proof['CS_ORIGINAL'].tobytes()!=oldcs.tobytes():raise ValueError('TARGET_STOP: original2021 CS bits differ')
    masks=ROOT/'coin_2021_source_closure_20261013/CORE5_WARMUP_MASKS.npz'
    with np.load(masks,allow_pickle=False) as a:
        for j,s in enumerate(SYMBOLS):np.testing.assert_array_equal(mask[:,j],a[s+'_200close'])
    # Prefix recomputation uses only available prefix inputs and original saved
    # HOLD intents/masks; it tests rank restoration and all three mask phases.
    prefixes=[]
    for offset in (24,25,90,91,180,364):
        cut=d[offset];sel=t<=cut;rows=d<=cut
        alt,acov,ap=build(t[sel],p[sel],d[rows],original_hold=hold[rows],original_hold_mask=mask[rows])
        for arm in ARMS:np.testing.assert_array_equal(alt[arm],out[arm][rows])
        np.testing.assert_array_equal(acov,cov[rows])
        prefixes.append(dict(cut_us=int(cut),rows=int(rows.sum()),status='BIT_EXACT_INPUT_PREFIX_NO_FUTURE_ROWS'))
    cash=np.abs(out['STATIC50']).sum(1)==0
    if not cash[:91].all() or cash[91:].any() or not np.array_equal(mask.sum(1),np.r_[np.full(25,3),np.full(66,4),np.full(274,5)]):
        raise ValueError('TARGET_STOP: original2021 dynamic phases differ')
    dest=HERE/'targets';dest.mkdir()
    path=dest/'Y2021.npz'
    np.savez_compressed(path,decision_us=d,symbol_order=np.asarray(SYMBOLS),annual_covariance=cov,
                        HOLD_original=hold,HOLD_mask=mask,SMA_mask=proof['sma_mask'],
                        CS_original=oldcs,CS_MATCHED=proof['CS_MATCHED'],**out)
    journal=dict(match=proof['match_proof'],risk=proof['risk_proof'],rank=proof['rank_diagnostic'])
    write(dest/'TARGET_PROOF.json',journal)
    write(HERE/'TERMINAL_QUOTE_GATE.json',term)
    write(HERE/'GOLDEN_PARITY.json',gold)
    cases=[]
    for arm in ARMS:
        cases.append(dict(case_id='Y2021_'+arm,year=2021,arm=arm,calendar=[us(2021),us(2022)],symbols=list(SYMBOLS),
            source_index_local_locator=str((SOURCE/'SOURCE_INDEX.json').relative_to(ROOT)),source_index_SHA256=gate['source_index_SHA256'],
            target_archive_local_locator=str(path.relative_to(ROOT)),target_archive_SHA256=sha(path),
            target_array_SHA256=hashlib.sha256(out[arm].tobytes()).hexdigest(),target_dtype=out[arm].dtype.str,
            target_shape=list(out[arm].shape),protective_enabled=False))
    write(HERE/'CASE_BINDINGS.json',dict(status='FROZEN_FOUR_FULL2021_FINE_ORIGINAL_CASES_ZERO_HISTORY',case_count=4,cases=cases,modes=['ORIGINAL'],
        fine_profile_SHA256=sha(ROOT/'coin_quantity_resolution_20261013/FINE_PROFILE.json'),
        source_commit='560d9afbe40ffe7d961b4d3b22db9df684d21800',
        source_repository_path='research/core5-2021-fullsource-20261013/SOURCE_INDEX.json',
        target_proof_SHA256=sha(dest/'TARGET_PROOF.json'),terminal_quote_gate_SHA256=sha(HERE/'TERMINAL_QUOTE_GATE.json'),
        independent_source_review_SHA256=gate['independent_source_review_SHA256'],
        parent_GO_required=True,independent_exact_byte_review_required=True,new_historical_wallets_executed=0))
    summary=dict(status='PASS_ORIGINAL_DYNAMIC_MASK_FULL365_TARGET_ADMISSION_NO_HISTORY',days=365,asset_days=1825,
        target_archive_SHA256=sha(path),source_gate=gate,original_HOLD_context_SHA256=sha(context),
        original_CS_2021_bit_parity=True,mask_counts=mask.sum(0).tolist(),mask_phases=[dict(days=25,assets=3),dict(days=66,assets=4),dict(days=274,assets=5)],
        early_original_match_CASH_days=91,all_calendar_rows_retained=True,last_day_forced_cash=False,completed_prefix_checks=prefixes,
        arms={arm:dict(target_array_SHA256=hashlib.sha256(w.tobytes()).hexdigest(),cash_days=int((np.abs(w).sum(1)==0).sum()),
              max_asset=float(np.abs(w).max()),max_gross=float(np.abs(w).sum(1).max()),mean_gross=float(np.abs(w).sum(1).mean())) for arm,w in out.items()},
        new_fits=0,new_historical_wallets=0,old_wallet_replays=0,provider_downloads=0,Library_calls=0,retained_2026_opened=0,
        no_OOS_claim=True,elapsed_seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    write(HERE/'TARGET_PREPARATION.json',summary)
    print(json.dumps(summary,indent=2))

if __name__=='__main__': prepare()
