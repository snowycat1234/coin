"""Read-only original-source prefix proof and minimal frozen63 native wrappers."""
import importlib.util,json,shutil,sys,types
from datetime import datetime,UTC
from pathlib import Path
import evaluate_requests63 as native
base=native.base
PRODUCER_MANIFEST_SHA='62ec3efa0d02c964ffcc59fb16f679740b9854556f1aefa3aeefd5737836b14f'
READY_SHA='57a72ada0eb4f586fc89a717640618f06012cf096c683bb5d5d427a754a40900'
SOURCE_COMMIT='c49cbe28f3f8265987c1e7fe2141d87ce220f339'
TRAIN_FILES={
 'features.npz':('temporal-feature-transfer/original/features/CORE5_PRE_MAY2024.npz','f164dc8986727e12446f4a807aed72382e8fd665ad7eda9ba14590811ebc680c'),
 'feature_manifest.json':('temporal-feature-transfer/original/FEATURE_MANIFEST.json','9ecbc55c21a5eab2b400604bbd7347a6e9b1261f31b4e749364ee292031da464'),
 'economic.npz':('temporal-train-context/PRE_MAY_TWO_EXPERT_ECONOMIC_CONTEXTS.npz','66c5fdb2317689ed1d084c3f8eeb6e1781fa04ccc15e6243784a03a3555e7676'),
 'short.npz':('momentum-expert-contexts/TRAIN778_MOMENTUM_SHORT_CONTEXTS.npz','64accfc82f78034af0da48561ef7e2fabfc8712760066860194e3d2bce9e382d')}


def prefix(root):
    import numpy as np
    require=base.frozen.require;p=root/'producer';run=base.frozen.read(p/'RUN.json');spec=run['specification'];fold=spec['data_split_identity']['fold']
    require(base.frozen.sha(p/'MANIFEST.json')==PRODUCER_MANIFEST_SHA and base.frozen.sha(root/'READY.json')==READY_SHA,'Exact authorized public January and initialization receipts required')
    ready=base.frozen.read(root/'READY.json');initial=ready['folds']['FOLD_20240101']
    require(initial['binding']==run and initial['empty_Adam'] is True and initial['optimizer_updates']==0 and initial['parameter_count']==13699 and initial['model_identity']==spec['initial_model_identity'],'Actual source-bound fresh empty-Adam initial receipt differs')
    for field in ('raw_parameter_identity','initial_Torch_RNG_identity'):base.digest(initial[field])
    sources={**spec['sources'],**spec['algorithm']['versioned_sources']}
    for name,sha in sources.items():require(base.frozen.sha(base.member(root/'source',name))==sha,'Published producer source differs: '+name)
    for name,(_,sha) in TRAIN_FILES.items():require(base.frozen.sha(root/'training'/name)==sha,'Actual retained training source differs: '+name)
    require(spec['data_split_identity']['economic_SHA256']==TRAIN_FILES['economic.npz'][1],'Published training economics identity differs')
    # Import only the two exact, NumPy-only source readers; no model/optimizer code.
    package='_native63_published_prefix';module=types.ModuleType(package);module.__path__=[str(root/'source/modules/temporal_two_expert')];sys.modules[package]=module
    for name in ('inputs','feature_windows'):
        full=package+'.'+name;s=importlib.util.spec_from_file_location(full,Path(module.__path__[0])/(name+'.py'));m=importlib.util.module_from_spec(s);sys.modules[full]=m;s.loader.exec_module(m)
    inputs=sys.modules[package+'.inputs'];features=sys.modules[package+'.feature_windows'].load_feature_inputs(root/'training/features.npz',root/'training/feature_manifest.json')
    with np.load(root/'training/economic.npz',allow_pickle=False) as z:e={k:z[k].copy() for k in ('decision_us','episode_id','symbol_order','target_available_us','start_execution_us','end_execution_us')}
    with np.load(root/'training/short.npz',allow_pickle=False) as z:short={k:z[k].copy() for k in ('decision_us','target_available_us','asset_context_available_us')}
    require(e['symbol_order'].tolist()==list(base.frozen.SYMBOLS) and np.array_equal(short['decision_us'],e['decision_us']),'Actual ordered training expert/feature dates differ')
    decisions=[];labels=[];expert=[];batches=[]
    for i,proof in enumerate(fold['training_wallets']):
        ix=np.flatnonzero((e['episode_id']==i)&(e['decision_us']<native.CALENDAR['start']));tt=e['decision_us'][ix]
        require(len(tt)==proof['decisions'] and np.array_equal(tt,np.arange(proof['first_decision_us'],proof['last_decision_us']+base.frozen.DAY,base.frozen.DAY,dtype=np.int64)),'Actual selected natural-wallet prefix differs')
        require(np.array_equal(e['start_execution_us'][ix],tt+base.frozen.MINUTE+1) and np.array_equal(e['end_execution_us'][ix],tt+base.frozen.DAY+base.frozen.MINUTE+1),'Actual training execution/outcome clocks differ')
        outcome=e['end_execution_us'][ix].copy();outcome[-1]=proof['paid_terminal_close_available_us']
        require(int(outcome.max())==proof['latest_active_outcome_available_us'] and (outcome<native.CALENDAR['start']).all(),'Actual paid prefix labels cross January start')
        clocks=np.maximum(e['target_available_us'][ix].max(1),np.maximum(short['target_available_us'][ix].max(1),short['asset_context_available_us'][ix].max(1)))
        require((clocks<=tt).all(),'Actual prefix expert inputs cross their decisions')
        decisions.append(tt);labels.append(outcome);expert.append(clocks);batches.append(features.windows(tt))
    scaler=inputs.fit_standardizer(batches,training_cutoff_us=native.CALENDAR['start'])
    require(scaler.identity==fold['scaler_identity'] and scaler.provenance==fold['scaler_provenance'],'Read-only original-source scaler reconstruction differs')
    with np.load(p/'SCALER.npz',allow_pickle=False) as z:
        require(all(np.array_equal(z[k],getattr(scaler,k)) for k in ('mean','scale','count')),'Published scaler values/counts differ')
    decision=np.concatenate(decisions);feature=np.concatenate([np.where(w.valid,w.available_us,0).max((1,2,3)) for w in batches]);scaler_clocks=np.unique(np.concatenate([w.completed_us.ravel() for w in batches]))
    clocks=dict(sample_decision_us=decision,feature_available_us=feature,expert_input_available_us=np.concatenate(expert),label_available_us=np.concatenate(labels),scaler_input_available_us=scaler_clocks)
    require(len(decision)==658 and len(scaler_clocks)==787 and (feature<=decision).all() and all((v<native.CALENDAR['start']).all() for v in clocks.values()),'Actual independent658/787 prefix clocks differ')
    report=dict(status='PASS_ORIGINAL_SOURCE_INDEPENDENT_ACTUAL_PREFIX_CLOCKS_SCALER_AND_FRESH_READY_RECEIPT',training_samples=658,scaler_rows=787,maximum_training_label_available_us=int(clocks['label_available_us'].max()),maximum_scaler_input_available_us=int(scaler_clocks.max()),scaler_identity=scaler.identity,scaler_values_bit_identical=True,training_window_identities=scaler.provenance['training_window_identities'],initial_model_identity=initial['model_identity'],raw_initial_parameter_identity=initial['raw_parameter_identity'],initial_Torch_RNG_identity=initial['initial_Torch_RNG_identity'],empty_Adam=True,initial_optimizer_updates=0,initialization_evidence='ORIGINAL_PUBLIC_READY_SEMANTIC_IDENTITIES_NOT_INVENTED_INITIAL_SNAPSHOT',proof_scope='INDEPENDENT_SOURCE_DATA_SELECTION_CLOCKS_SCALER;DECLARED_FRESH_PARAMETER_RECEIPT;NO_OPTIMIZER_REPLAY',models_fit=0,model_tensors_loaded=False)
    return report,clocks


def prepare(state,cache,output):
    import numpy as np
    require=base.frozen.require;require(not output.exists(),'Fresh wrapper directory required');output.mkdir(parents=True)
    source=cache/'research/temporal-prequential-transfer-20261009';shutil.copytree(source/'forward/FOLD_20240101',output/'producer');shutil.copyfile(source/'READY.json',output/'READY.json')
    require(base.frozen.sha(output/'producer/MANIFEST.json')==PRODUCER_MANIFEST_SHA,'Actual authorized January manifest differs')
    run=base.frozen.read(output/'producer/RUN.json');spec=run['specification'];sources={**spec['sources'],**spec['algorithm']['versioned_sources']}
    for name,sha in sources.items():
        p=base.member(output/'source',name);p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(base.member(cache,name),p);require(base.frozen.sha(p)==sha,'Actual source byte identity differs')
    for name,(relative,sha) in TRAIN_FILES.items():
        p=output/'training'/name;p.parent.mkdir(exist_ok=True);shutil.copyfile(state/relative,p);require(base.frozen.sha(p)==sha,'Retained training input bytes differ')
    proof,clocks=prefix(output);np.savez_compressed(output/'TRAINING_CLOCKS.npz',**clocks);(output/'PREFIX_PROOF.json').write_text(json.dumps(proof,indent=2)+'\n');shutil.copyfile(native.PUBLIC/'CANONICAL_CONTEXTS63.npz',output/'CANONICAL_CONTEXTS63.npz')
    original=base.frozen.read(output/'producer/MANIFEST.json');score=base.frozen.read(output/'producer/RESULT.json');requests={}
    with np.load(output/'producer/REQUESTS.npz',allow_pickle=False) as z:actual={k:z[k].copy() for k in z.files}
    with np.load(output/'producer/PAIRED_PATHS.npz',allow_pickle=False) as z:
        require(np.array_equal(z['decision_us'],actual['decision_us']) and np.array_equal(z['FRESH_GRU_requests'],actual['desired_expert_budget']),'Actual paired frozen learned path differs')
        for arm,label in [('STATIC50','VOL50_CS50'),('CASH50','CASH50_VOL25_CS25')]:
            expected=base.fixed_control_requests(arm,native.CALENDAR);require(np.array_equal(z[label+'_requests'],expected),'Published fixed control requests differ')
            a={k:v.copy() for k,v in actual.items()};a['desired_expert_budget']=z[label+'_requests'].copy();name=arm+'_REQUESTS.npz';np.savez_compressed(output/name,**a);requests[arm]=name
            (output/(arm+'_PLAN.json')).write_text(json.dumps(dict(policy_role='FIXED_CONTROL',fits=0,calendar=native.CALENDAR,control=arm),indent=2)+'\n')
        require(np.array_equal(z['CASH_requests'],np.tile([1.,0,0,0,0,0],(63,1))),'Published analytic CASH path differs')
    files={p.relative_to(output).as_posix():dict(bytes=p.stat().st_size,sha256=base.frozen.sha(p)) for p in sorted(output.rglob('*')) if p.is_file()}
    source_commit=base.frozen.read(cache/'PRODUCER_SOURCE_COMMIT.json')['sha'];require(source_commit==SOURCE_COMMIT,'Verified full original producer source commit differs')
    for arm in ('FRESH_GRU_FOLD20240101','STATIC50','CASH50'):
        control=arm!='FRESH_GRU_FOLD20240101';plan=arm+'_PLAN.json' if control else 'producer/RUN.json';m=dict(schema=native.SCHEMA,arm_id=arm,policy_role='FIXED_CONTROL' if control else 'LEARNED_FROZEN',objective_version=2,prediction_role='HISTORICAL_FROZEN_REPLAY_NOT_LIVE_PREDICTIONS',source_files=['source/'+n for n in sources],files=files,request_file=requests[arm] if control else 'producer/REQUESTS.npz',producer_commit=source_commit,expert_order=list(base.E5+(base.SHORT,)),allowed_actions=list(base.COMPACT+(base.SHORT,)),uses_feedback_features=False,calendar=native.CALENDAR,adapter_contract_sha256=base.frozen.sha(native.CONTRACT),training_cutoff_us=native.CALENDAR['start'],maximum_training_label_available_us=0 if control else proof['maximum_training_label_available_us'],maximum_scaler_input_available_us=0 if control else proof['maximum_scaler_input_available_us'],actual_fit_completed_UTC=None if control else score['actual_fit_completed_UTC'],actual_export_completed_UTC=score['actual_fit_completed_UTC'],training_plan_file=plan,training_plan_sha256=files[plan]['sha256'],model_sha256=None if control else original['files']['MODEL_ADAM_RNG.pt']['SHA256'],scaler_sha256=None if control else original['files']['SCALER.npz']['SHA256'])
        if not control:m.update(prefix_evidence_mode='PUBLISHED_FRESH_RECEIPT_AND_INDEPENDENT_SOURCE_CLOCKS',producer_manifest_file='producer/MANIFEST.json',producer_ready_file='READY.json',producer_prefix_proof_file='PREFIX_PROOF.json',model_file='producer/MODEL_ADAM_RNG.pt',scaler_file='producer/SCALER.npz',training_clock_file='TRAINING_CLOCKS.npz',training_data_files=['training/'+n for n in TRAIN_FILES],context_file='CANONICAL_CONTEXTS63.npz')
        m['actual_export_completed_UTC']=datetime.now(UTC).isoformat()
        path=output/('MANIFEST_'+arm+'.json');path.write_text(json.dumps(m,indent=2)+'\n')
    return proof
