"""No-wallet preparation and 2025 no-op evidence from genuine old journals."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
SHADOW=ROOT/'coin_causal_headroom_shadow_20261013'
CORE_SHA='2ab4158bf610c0075bc901b4ba0a649eed5b993251090bf54bbaa5332f1dfb39'
sys.path.insert(0,str(SHADOW))
from headroom_buffer import features, assess, MINUTE
from scan_shadow import load_source, numeric_chunks, sha, read, SYMBOLS
from feature_tape import FIELDS, REASONS, array_sha, FeatureTape

def write_new(p,obj):
    with Path(p).open('x') as f:
        json.dump(obj,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')

def build_one(desc):
    source,derived,counts=load_source(desc)
    arrays={'close_us':source['times']+MINUTE}
    for s in SYMBOLS:
        feature=features(source['times'],source[s+'_mark'],source[s+'_open'],derived[s])
        arrays[s+'_mark']=source[s+'_mark']
        for k in ('ready','a_down','a_up','g_down','g_up'):
            arrays[s+'_'+k]=feature[k]
        codes=np.zeros(len(source['times']),dtype=np.uint8)
        for code,reason in enumerate(REASONS):codes[feature['reason']==reason]=code
        arrays[s+'_reason_code']=codes
    folder=HERE/'features';folder.mkdir(exist_ok=True)
    path=folder/f"Y{desc['year']}.npz"
    if path.exists():raise FileExistsError('Never overwrite prior feature archive')
    np.savez_compressed(path,**arrays)
    bindings={k:{'dtype':a.dtype.str,'shape':list(a.shape),'SHA256':array_sha(a)} for k,a in arrays.items()}
    digest=hashlib.sha256(json.dumps(bindings,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    manifest={'year':desc['year'],'symbols':list(SYMBOLS),'calendar':desc['case']['calendar'],
        'core_SHA256':CORE_SHA,'source_index_SHA256':desc['case']['source_index_SHA256'],
        'source_months':desc['source_months'],'archive_SHA256':sha(path),'archive_bytes':path.stat().st_size,
        'array_binding_SHA256':digest,'arrays':bindings,'derived_original_cells':int(sum(d.sum() for d in derived.values())),
        'prepared_wallets':0,'new_source_requests':0,'status':'SOURCE_ONLY_CAUSAL_FEATURE_TAPE_READY'}
    write_new(folder/f"Y{desc['year']}.json",manifest)
    FeatureTape.load(path,manifest)
    return manifest,arrays

def prove_2025(desc,manifest,arrays):
    state=ROOT/desc['state'];pointer=read(state/'recovery/POINTER.json');old=read(state/'RESULT.json')
    account=read(state/'ACCOUNT.json');binding=read(state/'BINDING.json')
    n=pointer['completed_minutes']
    if n!=525600 or old['completed_minutes']!=n or old['account_status']!='ACTIVE' or old['paid_flat'] is not False:
        raise ValueError('Complete original5open2025 unpaid fine path required')
    if binding['mode']!='ORIGINAL' or binding['persist_cash_close'] or binding['final_day_target_zero']:
        raise ValueError('Original financial path settings differ')
    if pointer['binding']!=binding or old['genuine_state_hash']!=pointer['state_hash']:
        raise ValueError('Genuine original checkpoint binding differs')
    stats={s:{'invested_ready_minutes':0,'invested_not_ready_minutes':0,'trigger_minutes':0,
              'minimum_ready_buffered_headroom_USDT':None} for s in SYMBOLS}
    chunks=[]
    for offset,a in numeric_chunks(desc):
        chunks.append(pointer['chunks'][len(chunks)])
        rows=len(a)
        # The lossless checkpoint stores 36 numeric fields, with the exact
        # close clock reconstructed by the original scheduler's start+offset.
        np.testing.assert_array_equal(arrays['close_us'][offset:offset+rows],
            binding['calendar'][0]+(np.arange(offset,offset+rows,dtype=np.int64)+1)*MINUTE)
        for j,s in enumerate(SYMBOLS):
            q=a[:,9+j];E=a[:,24+j];P=arrays[s+'_mark'][offset:offset+rows]
            np.testing.assert_allclose(a[:,14+j],q*P,rtol=2e-15,atol=1e-10)
            f={k:arrays[s+'_'+k][offset:offset+rows] for k in ('a_down','a_up','g_down','g_up')}
            ready=arrays[s+'_ready'][offset:offset+rows];invested=q!=0
            stress=assess(q,E,P,**f);flag=ready&stress['trigger']
            row=stats[s];row['trigger_minutes']+=int(flag.sum())
            row['invested_ready_minutes']+=int((invested&ready).sum())
            row['invested_not_ready_minutes']+=int((invested&~ready).sum())
            if np.any(invested&ready):
                minimum=float(np.min(stress['buffered_headroom'][invested&ready]))
                row['minimum_ready_buffered_headroom_USDT']=min(minimum,row['minimum_ready_buffered_headroom_USDT']) if row['minimum_ready_buffered_headroom_USDT'] is not None else minimum
    if any(row['trigger_minutes'] for row in stats.values()):
        raise ValueError('2025 path not a strict no-op; report to parent, never start extra wallet')
    targets=account['targets'];archive=ROOT/desc['case']['target_archive_local_locator']
    with np.load(archive,allow_pickle=False) as z:
        np.testing.assert_array_equal(np.array([r['target_weight'] for r in targets]).reshape(-1,5),z['STATIC50'])
        np.testing.assert_array_equal(np.array([targets[i*5]['available_us'] for i in range(365)],dtype=np.int64),z['decision_us'])
    out={'status':'INFERRED_NO_OP_REUSED_ORIGINAL_FINANCIAL_PATH','candidate_wallets_executed':0,
        'original_case_id':old['case_id'],'original_genuine_state_hash':pointer['state_hash'],
        'original_file_SHA256':{name:sha(state/name) for name in ('ACCOUNT.json','RESULT.json','BINDING.json','MINUTE_NUMERIC.json','recovery/POINTER.json')},
        'original_daily_chunks':chunks,'all_525600_minute_close_inputs_verified':True,
        'feature_archive_SHA256':manifest['archive_SHA256'],'feature_array_binding_SHA256':manifest['array_binding_SHA256'],
        'symbols':stats,'same_clock_hook_argument':
        'Native marks are updated before funding_through(close,True). All earlier same-clock funding callbacks skip while another event remains. The final event callback and subsequent explicit close callback see the exact q/E stored in that completed close row; duplicate false evaluations have no financial side effects. Funding callbacks using a stale mark skip because close_us != stamp. Halt/zero-position cases cannot schedule protection.',
        'induction_argument':
        'Initial fresh base financial state, targets, source, costs, funding and account class are identical. Until the first true trigger, locks/events are empty and inherited schedule/attempt/advance_day are base-identical. At every eligible original-path hook, READY predicate is false or NOT_READY takes no protection action. Thus no first differing financial transition exists, by chronological prefix induction. Metadata and coverage differ; snapshot bytes and candidate genuine hashes are not claimed equal.',
        'old_5open_terminal_preserved':True,'full_calendar':old['full_calendar'],'paid_flat':False,
        'paid_cash_PnL_USDT':None,'marked_PnL_USDT':old['marked_PnL_USDT'],
        'terminal_residual_quantity':old['terminal_residual_quantity'],
        'terminal_residual_gross_notional_USDT':old['terminal_residual_gross_notional_USDT'],
        'new_candidate_genuine_state_hash':None,'economic_path_equivalence_inferred_not_new_execution':True}
    write_new(HERE/'Y2025_NO_OP_PROOF.json',out)
    return out

def main():
    if sha(SHADOW/'headroom_buffer.py')!=CORE_SHA:raise ValueError('Reviewed stress core changed')
    inputs=read(SHADOW/'INPUTS.json')
    for p,h in inputs['files_SHA256'].items():
        if sha(ROOT/p)!=h:raise ValueError('Original shadow input changed: '+p)
    results={}
    for desc in inputs['cases']:
        started=time.monotonic();manifest,arrays=build_one(desc)
        results[str(desc['year'])]={'manifest_SHA256':sha(HERE/'features'/f"Y{desc['year']}.json"),
                                  'archive_SHA256':manifest['archive_SHA256'],
                                  'array_binding_SHA256':manifest['array_binding_SHA256'],
                                  'archive_bytes':manifest['archive_bytes'],'elapsed_seconds':time.monotonic()-started}
        if desc['year']==2025:prove_2025(desc,manifest,arrays)
        print('FEATURES_PREPARED',desc['year'],results[str(desc['year'])],flush=True)
    write_new(HERE/'FEATURE_PREPARATION.json',{'status':'PASS_SOURCE_ONLY_PREPARATION_ZERO_HISTORY','years':results,
        'historical_wallets_started':0,'new_fits':0,'new_source_requests':0})

if __name__=='__main__':main()
