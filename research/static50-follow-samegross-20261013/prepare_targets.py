"""Read-only inputs, fixed target arithmetic only; source gate precedes every year."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
from same_gross_targets import ARMS, DAY, SYMBOLS, common_gross
from original_follow_adapter import original

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,body):
    with Path(path).open('x') as f: json.dump(body,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')

def run():
    gate_path=HERE/'source_audit/SOURCE_GATE.json'
    gate=json.loads(gate_path.read_text())
    if (gate['status']!='PASS_REAL_CORE5_2024_OHLC_SOURCE_GATE'
            or gate['new_historical_wallets']!=0 or gate['warmup_complete_days']<20
            or gate['evaluation_decisions']!=366
            or gate['completed_daily_close_cells_bit_matching_STATIC50']!=1985):
        raise ValueError('SOURCE_STOP: no target generation or historical wallet for any year')
    source_path=HERE/'source_audit/Y2024_REAL_OHLC.npz'
    if sha(source_path)!=gate['dataset_SHA256']:
        raise ValueError('SOURCE_STOP: actual source bytes changed')
    with np.load(source_path,allow_pickle=False) as a:
        if tuple(a['symbol_order'])!=SYMBOLS or not a['ready'].all():
            raise ValueError('SOURCE_STOP: exact complete real CORE5 source required')
        core=original()
        d=np.arange(1704067200000000,1735689600000000,DAY,dtype=np.int64)
        out,proof=core.targets(a['available_us'],a['high'],a['low'],a['close'],a['ready'],a['risk_t'],a['risk_p'],d)
        if any('UNKNOWN_SOURCE' in row['reasons'] for row in proof):
            raise ValueError('SOURCE_STOP: unknown actual event candles')
        f2024=out['FOLLOW']
    fine=json.loads((ROOT/'coin_quantity_resolution_20261013/CASE_BINDINGS.json').read_text())
    saved=json.loads((HERE/'inputs/READINESS.json').read_text())
    target_dir=HERE/'targets'; target_dir.mkdir()
    cases=[]; reports={}
    for year in (2023,2024,2025):
        base=next(c for c in fine['cases'] if c['year']==year and c['arm']=='STATIC50')
        sp=ROOT/base['target_archive_local_locator']
        if sha(sp)!=base['target_archive_SHA256']: raise ValueError('Frozen S archive changed')
        with np.load(sp,allow_pickle=False) as a:
            clocks=a['decision_us'].copy(); s=a['STATIC50'].copy(); names=a['symbol_order'].copy()
        if hashlib.sha256(s.tobytes()).hexdigest()!=base['target_array_SHA256']:
            raise ValueError('Frozen S array changed')
        if year==2024:
            f=f2024; fd=d
            f_identity={'kind':'GENERATED_ONCE_ORIGINAL_UNCHANGED_FORMULA_FROM_REAL_2024_OHLC',
                        'source_gate_SHA256':sha(gate_path),'real_source_SHA256':sha(source_path),
                        'reference_manifest_SHA256':sha(HERE/'ORIGINAL_REFERENCE.json')}
        else:
            fp=HERE/f'inputs/Y{year}.npz'
            rec=saved['original_members'][fp.name]
            if sha(fp)!=rec['SHA256'] or fp.stat().st_size!=rec['bytes']:
                raise ValueError('Saved FOLLOW original member changed')
            with np.load(fp,allow_pickle=False) as a:
                fd=a['decision_us'].copy(); f=a['FOLLOW'].copy()
                if tuple(a['symbol_order'])!=SYMBOLS or not np.array_equal(f,-a['FADE']):
                    raise ValueError('Saved FOLLOW original order/direction changed')
            f_identity={'kind':'REUSED_SAVED_FOLLOW_NO_REGENERATION',
                        'public_commit':'80086cfaf7123b87496704bbe136aecebe5f3472',
                        'original_target_artifact':saved['target_artifact'],
                        'archive_SHA256':sha(fp),'array_SHA256':hashlib.sha256(f.tobytes()).hexdigest(),
                        'local_locator':str(fp.relative_to(ROOT))}
        r=common_gross(clocks,names,s,fd,SYMBOLS,f)
        target_path=target_dir/f'Y{year}.npz'
        np.savez_compressed(target_path,decision_us=clocks,symbol_order=names,**r)
        with np.load(target_path,allow_pickle=False) as a:
            for k,v in r.items(): np.testing.assert_array_equal(a[k],v)
        # Bind reusable original S accounts without re-execution or alteration.
        comparator=ROOT/f'coin_quantity_resolution_20261013/state_20261013/Y{year}_STATIC50_FINE_ORIGINAL'
        files={}
        for name in ('BINDING.json','ACCOUNT.json','RESULT.json','MINUTE_NUMERIC.json','recovery/POINTER.json'):
            p=comparator/name; files[name]={'local_locator':str(p.relative_to(ROOT)),'SHA256':sha(p)}
        old_binding=json.loads((comparator/'BINDING.json').read_text())
        if (old_binding['source_index_SHA256']!=base['source_index_SHA256']
                or old_binding['target_array_SHA256']!=base['target_array_SHA256']
                or old_binding['fine_profile_SHA256']!=fine['fine_profile_SHA256']):
            raise ValueError('Original fine S comparator identity mismatch')
        for arm in ARMS:
            cases.append({'case_id':f'Y{year}_{arm}','year':year,'arm':arm,
                          'calendar':base['calendar'],'symbols':base['symbols'],
                          'source_index_local_locator':base['source_index_local_locator'],
                          'source_index_SHA256':base['source_index_SHA256'],
                          'target_archive_local_locator':str(target_path.relative_to(ROOT)),
                          'target_archive_SHA256':sha(target_path),
                          'target_array_SHA256':hashlib.sha256(r[arm].tobytes()).hexdigest(),
                          'target_dtype':r[arm].dtype.str,'target_shape':list(r[arm].shape),
                          'original_STATIC50':{k:base[k] for k in ('target_archive_local_locator','target_archive_SHA256','target_array_SHA256')},
                          'FOLLOW':f_identity,'reused_original_STATIC50_fine_comparator':files,
                          'protective_enabled':False})
        reports[str(year)]={'days':len(clocks),'target_archive_SHA256':sha(target_path),
                           'S_array_SHA256':base['target_array_SHA256'],'F_array_SHA256':hashlib.sha256(f.tobytes()).hexdigest(),
                           'common_gross_mean':float(r['common_gross'].mean()),
                           'common_gross_max':float(r['common_gross'].max()),
                           'cash_days':int((r['common_gross']==0.).sum()),
                           'static_downscaled_days':int((r['static_factor']<1.).sum()),
                           'pool_downscaled_days':int((r['pool_factor']<1.).sum()),
                           'gross_equality_max_abs_error':float(np.max(np.abs(np.abs(r[ARMS[0]]).sum(1)-np.abs(r[ARMS[1]]).sum(1)))),
                           'performance_evaluation':'NOT_RUN'}
    write(HERE/'Y2024_FOLLOW_PROOF.json',{'formula':'ORIGINAL_EXACT_BYTES_UNCHANGED','days':366,
          'real_OHLC_source_SHA256':sha(source_path),'source_gate_SHA256':sha(gate_path),'risk':proof})
    write(HERE/'CASE_BINDINGS.json',{'status':'FROZEN_SIX_FINE_CASES_PRE_GO_ZERO_HISTORY',
          'case_count':6,'modes':['ORIGINAL'],'cases':cases,'parent_GO_required':True,
          'fine_profile_SHA256':fine['fine_profile_SHA256'],'coarse_profile_SHA256':fine['coarse_profile_SHA256'],
          'source_gate_SHA256':sha(gate_path),'source_dataset_SHA256':sha(source_path),
          'original_fine_bindings_SHA256':sha(ROOT/'coin_quantity_resolution_20261013/CASE_BINDINGS.json'),
          'wallets_to_rerun':0,'new_historical_wallets_executed':0})
    write(HERE/'TARGET_PREPARATION.json',{'status':'PASS_FIXED_ALL_THREE_YEAR_TARGETS_NO_HISTORY',
          'years':reports,'source_gate_passed_before_any_year':True,'new_fits':0,
          'new_historical_wallets':0,'original_wallet_reruns':0,'provider_downloads':0,
          'ratio_searches':0,'RNG':0,'targets_only_no_PnL':True})

if __name__=='__main__': run()
