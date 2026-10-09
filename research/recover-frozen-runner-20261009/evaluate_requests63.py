"""One covered prequential63 fold, using the parameterized frozen61 adapter.

Readiness/context generation is offline and never fits, infers or runs accounts.
"""
import argparse,json,os,resource,socket,zipfile
from pathlib import Path
import evaluate_requests61 as base

HERE=base.HERE
CALENDAR=dict(start=1704067200000000,end_exclusive=1709510400000000,days=63,minutes=90720,funding_events=945)
SCHEMA='SOURCE_HASHED_FROZEN_NATIVE63_REQUESTS_V1'
PUBLIC=HERE/'prequential63'
CONTRACT=PUBLIC/'ADAPTER_CONTRACT.json'


def prepare_context(state,output):
    import numpy as np,polars as pl
    base.frozen.modules(state)
    from scripts.investment import momentum_short_pool_target as momentum
    from momentum_training_context import independent
    tt=np.arange(CALENDAR['start'],CALENDAR['end_exclusive'],base.frozen.DAY,dtype=np.int64)
    bars=[]
    for symbol in base.frozen.SYMBOLS:
        p=state/'h1_validation/original/h1_market/data/normalized'/(symbol+'_daily.parquet')
        d=pl.read_parquet(p).filter((pl.col('close_us')<=int(tt[-1]))&(pl.col('available_us')<=int(tt[-1]))&pl.all_horizontal([pl.col(k).is_finite() for k in ('open','high','low','close','volume')]))
        bars.append(d.select('symbol','open_us','close_us','available_us','open','high','low','close','volume'))
    bars=pl.concat(bars);frame,_=momentum.fixed_targets(bars,tt,symbols=base.frozen.SYMBOLS)
    raw,reference,eligible,available,first=independent(bars,tt)
    actual=frame['target_weight'].to_numpy().reshape(63,5);actual_raw=frame['raw_signed_target'].to_numpy().reshape(63,5);reasons=frame['eligibility_reason'].to_numpy().reshape(63,5)
    base.frozen.require(np.array_equal(actual_raw,raw) and np.array_equal(reasons=='ELIGIBLE',eligible) and abs(actual-reference).max()<=1e-14,'Scalar causal momentum state/eligibility/covariance differs')
    base.frozen.require(eligible.all() and (available<=tt[:,None]).all(),'Actual causal200-bar warmup required; no gap substitution')
    output.mkdir(parents=True,exist_ok=False)
    short=output/'MOMENTUM_SHORT_CONTEXTS63.npz'
    np.savez_compressed(short,decision_us=tt,symbol_order=np.array(base.frozen.SYMBOLS),expert_order=np.array([base.SHORT]),expert_targets=actual[:,None],expert_raw_targets=actual_raw[:,None],expert_eligible=eligible.any(1)[:,None],expert_asset_eligible=eligible[:,None],target_available_us=tt[:,None],asset_context_available_us=available,warmup_first_close_us=first,eligibility_reason=reasons)
    c=base.contexts(state,True,CALENDAR,(short,base.frozen.sha(short)))
    original=state/'h1_validation/original/h1_market/inputs/H1_E5_INPUTS.npz'
    with np.load(original,allow_pickle=False) as z:
        ix=np.searchsorted(z['decision_us'],tt)
        extras={k:z[k][ix].copy() for k in ('market_close','market_state13','market_state13_available_us')}
    np.savez_compressed(output/'CANONICAL_CONTEXTS63.npz',decision_us=tt,symbol_order=np.array(base.frozen.SYMBOLS),expert_order=np.array(c['expert_order']),**{k:v for k,v in c.items() if k!='expert_order'},**extras)
    report=dict(status='PASS_ORIGINAL_E5_FIRST63_AND_EXISTING_CAUSAL_MOMENTUM_SHORT_RECIPE',calendar=CALENDAR,original_E5_SHA256=base.INPUT_SHA,short_recipe_SHA256=base.frozen.sha(base.frozen.REPO/'scripts/investment/momentum_short_pool_target.py'),scalar_raw_and_eligibility_exact=True,scalar_target_maximum_error=float(abs(actual-reference).max()),canonical_E5_slots_unchanged=True,short_slot=5,causal200_contiguous_completed_bars=True,maximum_context_input_us=int(available.max()),last_decision_us=int(tt[-1]),source_data_roles='CAUSAL_EVALUATION_CONTEXTS_NOT_TRAINING_LABELS',context_files={p.name:dict(bytes=p.stat().st_size,sha256=base.frozen.sha(p)) for p in sorted(output.glob('*.npz'))},fits=0,wallets_run=0,provider_downloads=0)
    (output/'CONTEXT_READY.json').write_text(json.dumps(report,indent=2)+'\n');return report


def canonical_contexts(state,extended=True):
    contract=base.frozen.read(CONTRACT);record=contract['context_files']['MOMENTUM_SHORT_CONTEXTS63.npz']
    return base.contexts(state,extended,CALENDAR,(PUBLIC/'MOMENTUM_SHORT_CONTEXTS63.npz',record['sha256']))


def prefix_provenance(path,m,a,c):
    import numpy as np
    require=base.frozen.require;contract=base.frozen.read(CONTRACT)
    require(m['calendar']==CALENDAR and m['adapter_contract_sha256']==base.frozen.sha(CONTRACT),'Explicit published63 calendar/contract binding differs')
    require(m['policy_role'] in ('LEARNED_FROZEN','FIXED_CONTROL'),'Explicit learned/fixed role required')
    if m['policy_role']=='FIXED_CONTROL':
        require(m['arm_id'] in ('STATIC50','CASH50') and m['actual_fit_completed_UTC'] is None and m['maximum_training_label_available_us']==m['maximum_scaler_input_available_us']==0,'Fixed controls must not invent fits')
        require(m['training_plan_file'] in m['files'] and m['files'][m['training_plan_file']]['sha256']==m['training_plan_sha256'],'Bound fixed-control export plan required')
        plan=base.frozen.read(base.member(path.parent,m['training_plan_file']))
        require(plan['policy_role']=='FIXED_CONTROL' and plan['fits']==0 and plan['calendar']==CALENDAR and plan['control']==m['arm_id'],'Fixed-control export plan differs')
        full,_=base.validate(m,a,c,CALENDAR);require(np.array_equal(full,base.fixed_control_requests(m['arm_id'],CALENDAR,len(c['expert_order'])==6)),'Fixed reference request coefficients differ')
        return dict(status='PASS_EXPLICIT_FROZEN_FIXED_CONTROL_NO_FIT',fits=0)
    required=('model_file','scaler_file','training_plan_file','initial_state_file','initialization_file','training_clock_file','context_file')
    require(all(m[k] in m['files'] for k in required),'Actual hashed model/scaler/initialization/training/context members required')
    training_data=m['training_data_files']
    require(isinstance(training_data,list) and training_data and len(set(training_data))==len(training_data) and all(n in m['files'] and n not in (m['context_file'],m['request_file'],m['training_clock_file']) for n in training_data),'Actual training dataset source members must be hash-bound separately from evaluation inputs and clock proof')
    require(m['allowed_actions']==list(base.COMPACT+(base.SHORT,)),'This fold freezes the existing four admitted learned actions')
    for field,sha_field in (('model_file','model_sha256'),('scaler_file','scaler_sha256'),('training_plan_file','training_plan_sha256'),('initial_state_file','initial_state_sha256')):
        require(m['files'][m[field]]['sha256']==base.digest(m[sha_field]),'Bound '+field+' identity differs')
    init=base.frozen.read(base.member(path.parent,m['initialization_file']))
    require(init['kind']=='FRESH_RANDOM_NO_WARM_START' and type(init['seed']) is int and init['parent_checkpoint_sha256'] is None and init['optimizer_updates']==0 and init['initial_state_sha256']==m['initial_state_sha256'],'Fresh initial model/optimizer provenance required')
    plan=base.frozen.read(base.member(path.parent,m['training_plan_file']))
    require(plan['prefix_only'] is True and plan['warm_start'] is False and plan['fold_start_us']==CALENDAR['start'],'Prefix-only declared producer schedule differs')
    clocks=base.member(path.parent,m['training_clock_file'])
    require(clocks.stat().st_size<2**20,'Training clock proof size limit')
    with zipfile.ZipFile(clocks) as z:require(sum(f.file_size for f in z.infolist())<=8*2**20,'Training clock proof decompression limit')
    with np.load(clocks,allow_pickle=False) as z:clock_arrays={k:z[k].copy() for k in z.files}
    require(set(clock_arrays)=={'sample_decision_us','feature_available_us','expert_input_available_us','label_available_us','scaler_input_available_us'},'Complete per-sample training and scaler clocks required')
    decision=clock_arrays['sample_decision_us'];require(decision.ndim==1 and len(decision)>0,'Actual prefix training samples required')
    decision=base.clock(decision,decision.shape,'training decisions')
    for key in ('feature_available_us','expert_input_available_us','label_available_us'):
        values=base.clock(clock_arrays[key],decision.shape,key)
        require((values>decision).all() if key=='label_available_us' else (values<=decision).all(),'Training feature/label clock ordering differs')
        require((values<CALENDAR['start']).all(),'Training values cross fold start')
    scaler=clock_arrays['scaler_input_available_us'];require(scaler.ndim==1 and len(scaler)>0,'Actual scaler prefix samples required');scaler=base.clock(scaler,scaler.shape,'scaler clocks')
    require((decision<CALENDAR['start']).all() and (scaler<CALENDAR['start']).all(),'Training/scaler are not strict prefixes')
    require(int(clock_arrays['label_available_us'].max())==m['maximum_training_label_available_us'] and int(scaler.max())==m['maximum_scaler_input_available_us'] and m['training_cutoff_us']==CALENDAR['start'],'Declared prefix maxima/cutoff differ from hashed sample clocks')
    require(m['files'][m['context_file']]['sha256']==contract['context_files']['CANONICAL_CONTEXTS63.npz']['sha256'],'Producer evaluation context differs from published canonical packet')
    with np.load(base.member(path.parent,m['context_file']),allow_pickle=False) as z:
        for key in ('expert_targets','expert_eligible','target_available_us','past_returns30'):
            expected=c[key] if key=='past_returns30' else c[key][:,:5] if len(c['expert_order'])==5 else c[key]
            actual=z[key] if key=='past_returns30' else z[key][:,:len(c['expert_order'])]
            require(np.array_equal(actual,expected),'Canonical source context value differs: '+key)
        require(np.array_equal(z['decision_us'],a['decision_us']) and np.all(z['market_state13_available_us']<=a['feature_available_us']),'Canonical context/feature clocks differ')
    require(np.all(c['target_available_us'].max(1)<=a['feature_available_us']),'Current expert inputs are later than reported feature availability')
    return dict(status='PASS_HASH_BOUND_FRESH_INITIALIZATION_STRICT_PREFIX_SAMPLE_CLOCKS_AND_CANONICAL_CONTEXT',initial_state_SHA256=m['initial_state_sha256'],training_samples=len(decision),scaler_samples=len(scaler),context_SHA256=contract['context_files']['CANONICAL_CONTEXTS63.npz']['sha256'],optimizer_updates_at_initialization=0,model_tensors_loaded=False,producer_training_history_scope='DECLARED_SCHEDULE_AND_HASHED_SOURCES_CLOCKS_NOT_INDEPENDENT_OPTIMIZER_REPLAY',fits=0)


def readiness(state):
    import numpy as np
    base.frozen.modules(state)
    contract=base.frozen.read(CONTRACT);old=base.frozen.read(HERE/'EVALUATE_REQUESTS61_ADAPTER.json')
    base.frozen.require(contract['calendar']==CALENDAR and contract['financial_contract']==old['financial_contract'] and contract['cost']==old['cost'],'Original financial contract and explicit covered fold required')
    report=base.source_market_check(state,CALENDAR,CONTRACT);window=base.market(state,CALENDAR);minutes=0
    for block in window['minute_blocks']():
        tt=block['times'];base.frozen.require(np.array_equal(tt,np.arange(CALENDAR['start']+minutes*base.frozen.MINUTE,CALENDAR['start']+(minutes+len(tt))*base.frozen.MINUTE,base.frozen.MINUTE)) and set(block['market'])==set(base.frozen.SYMBOLS),'Complete actual synchronous63 grid required')
        for value in block['market'].values():
            base.frozen.require(all(np.isfinite(v).all() for v in value.values()) and (value['quote_volume']>=0).all() and (value['mark']>0).all() and (value['open']>0).all(),'Actual finite prices/quote volumes required')
        minutes+=len(tt)
    base.frozen.require(minutes==90720 and len(window['events'])==945,'Exact63 trade/mark/funding coverage differs')
    canonical_contexts(state)
    report.update(status='PASS_ACTUAL63_TAPE_GRID_SOURCE_HASHES_AND_CANONICAL_CONTEXT_NO_WALLET',calendar=CALENDAR,fresh_start=dict(previous_quote=None,initial_capacity=0,prior_external_minute_supplied=False,initial_position=0),requests='NOT_YET_PROVIDED',wallets_run=0,fits=0,provider_downloads=0)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('readiness','check','run','context'));p.add_argument('--state',type=Path,required=True);p.add_argument('--manifest',type=Path);p.add_argument('--manifest-sha256');p.add_argument('--contract-sha256');p.add_argument('--output',type=Path);p.add_argument('--execution-plan',type=Path);p.add_argument('--execution-plan-sha256');p.add_argument('--plan-commit');args=p.parse_args()
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','POLARS_MAX_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6000000000,6000000000));resource.setrlimit(resource.RLIMIT_CPU,(600,600))
    def blocked(*a,**kw):raise RuntimeError('Offline native63 forbids network')
    socket.create_connection=blocked;socket.socket.connect=blocked
    if args.command=='context':base.frozen.require(args.output is not None,'Fresh output required');print(json.dumps(prepare_context(args.state,args.output)),flush=True);return
    if args.command=='readiness':print(json.dumps(readiness(args.state)),flush=True);return
    base.frozen.require(args.manifest is not None and args.manifest_sha256 is not None and args.contract_sha256 is not None and base.frozen.sha(CONTRACT)==base.digest(args.contract_sha256),'Real requests and external published contract SHA required')
    readiness(args.state)
    contract=base.frozen.read(CONTRACT);short=(PUBLIC/'MOMENTUM_SHORT_CONTEXTS63.npz',contract['context_files']['MOMENTUM_SHORT_CONTEXTS63.npz']['sha256'])
    options=dict(calendar=CALENDAR,contract_path=CONTRACT,short_context=short,request_schema=SCHEMA,provenance_check=prefix_provenance)
    if args.command=='check':print(json.dumps(base.check(args.state,args.manifest,args.manifest_sha256,**options)[3]),flush=True)
    else:
        base.frozen.require(all(v is not None for v in (args.output,args.execution_plan,args.execution_plan_sha256,args.plan_commit)),'Published request-specific authorized plan required')
        plan=base.frozen.read(args.execution_plan);base.frozen.require(plan['authorization']=='USER_AUTHORIZED_REAL_FROZEN63_NATIVE_EVALUATION' and plan['calendar']==CALENDAR,'Actual request-specific63 authorization/calendar required')
        base.run(args.state,args.manifest,args.manifest_sha256,args.output,args.execution_plan,args.execution_plan_sha256,args.plan_commit,**options)


if __name__=='__main__':main()
