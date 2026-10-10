"""Exact April export checks and three authorized original native63 accounts.

The frozen preparation contract/financial engine remain unchanged. This thin
entry point is bound separately by the published request-specific plans.
"""
import argparse,importlib.util,json,os,resource,shutil,socket,sys,types
from datetime import datetime,UTC
from pathlib import Path
import prepare_april63 as april
native=april.native;base=native.base;HERE=base.HERE;CAL=april.CALENDAR
PUBLIC=HERE/'april63-native';CONTRACT=april.PUBLIC/'ADAPTER_CONTRACT.json'
CONTRACT_SHA='5163c9b4e0cf7305662b715b46d0dabd4e8de35fc8ee38728aff8ff74f9c9b77'
EXPORT='b8299bc22321b9dadf707f14da83ac40a39b5491';PREFIX='research/temporal-april-transfer-20261009'
MANIFEST_SHA='99f07ef591581a51babb0b4a8b3079310f24a8bfe0e91b09103c4a68ffa82130'
READY_SHA='b3a295e1e36ca9aa0ae8e8089d27dedca0a8ed6b11105213dee533c88b22a9df'
PROOF_SHA='618380ea3d5ce8fff98a3236f8a54b5fd3ca3f1088b65191d09bb1f177f781ad'
MODEL='FRESH_GRU_FOLD20240401';LABELS={MODEL:'FRESH_GRU','STATIC50':'VOL50_CS50','CASH50':'CASH50_VOL25_CS25'}
sha=base.frozen.sha;read=base.frozen.read;require=base.frozen.require


def locations(state):
    cache=state/'april63-export'/EXPORT
    return cache,cache/PREFIX/'forward/FOLD_20240401',state/'april63-native-wrappers'


def inspect_export(producer):
    """April's original receipt omits a redundant terminal maximum field.

Validate that maximum from the bound outcome packet, preserving every original
export byte and the unchanged January interface/source and financial contract.
"""
    import numpy as np
    manifest=producer/'MANIFEST.json';require(sha(manifest)==MANIFEST_SHA,'Exact externally pinned April export required');m=read(manifest)
    require(m['schema']==native.PRODUCER_SCHEMA and m['status']=='COMPLETE' and m['fold']=='FOLD_20240401' and m['completed_updates']==512 and m['native_results'] is False and m['prediction_role']=='HISTORICAL_FROZEN_REPLAY_NOT_LIVE','Exact original completed April512 export required')
    for name,v in m['files'].items():p=base.member(producer,name);require(0<=v['bytes']<2**20 and p.stat().st_size==v['bytes'] and sha(p)==v['SHA256'],'Actual April export member differs: '+name)
    with np.load(producer/'REQUESTS.npz',allow_pickle=False) as z:a={k:z[k].copy() for k in z.files}
    with np.load(producer/'CURRENT_CONTEXT63.npz',allow_pickle=False) as z:c={k:z[k].copy() for k in z.files}
    require(c['expert_order'].tolist()==list(base.E5+(base.SHORT,)) and c['symbol_order'].tolist()==list(base.frozen.SYMBOLS) and np.array_equal(c['decision_us'],a['decision_us']),'Actual E6/CORE5/decision identity differs');c['expert_order']=base.E5+(base.SHORT,)
    full,_=base.validate(dict(expert_order=list(c['expert_order']),allowed_actions=list(base.COMPACT+(base.SHORT,)),uses_feedback_features=False),a,c,CAL)
    require((full[:,2:4]==0).all() and (c['expert_targets'][:,2:4]==0).all(),'Original unused producer slots differ')
    run=read(producer/'RUN.json')['specification'];fold=run['data_split_identity']['fold'];terminal=m['terminal_close'];t=read(producer/'TERMINAL.json');score=read(producer/'RESULT.json');scaler=read(producer/'SCALER.json')
    require(fold['fold_id']==m['fold'] and fold['first_forward_decision_us']==CAL['start'] and fold['forward_end_exclusive_us']==CAL['end_exclusive'] and fold['forward']==terminal,'Exact April producer calendar/terminal binding differs')
    outcome=base.clock(c['outcome_available_us'],(63,),'Actual April outcome clocks');tt=a['decision_us']
    require(np.array_equal(outcome[:-1],tt[1:]+base.frozen.MINUTE+1) and outcome[-1]==outcome[-2] and terminal['decisions']==63 and terminal['active_intervals']==62 and terminal['first_decision_us']==CAL['start'] and terminal['last_decision_us']==int(tt[-1]) and terminal['paid_terminal_close_available_us']==int(outcome.max()) and terminal['cutoff_us']==CAL['end_exclusive']+base.frozen.DAY and terminal['no_future_suffix_consumed'] and terminal['terminal_price_equals_last_active_end'],'Actual62 active outcomes and paid terminal clock differ')
    if 'latest_active_outcome_available_us' in terminal:require(terminal['latest_active_outcome_available_us']==int(outcome[:-1].max()),'Declared terminal maximum differs')
    require(c['surrogate_prices'].shape==(64,5) and np.isfinite(c['surrogate_prices']).all() and (c['surrogate_prices']>0).all() and np.array_equal(c['surrogate_prices'][-1],c['surrogate_prices'][-2]) and c['surrogate_funding_coeff'].shape==(63,5) and np.isfinite(c['surrogate_funding_coeff']).all() and (c['surrogate_funding_coeff'][-1]==0).all(),'Actual known-flat forward identity differs')
    require(c['initial_wallet_cash'].shape==() and float(c['initial_wallet_cash'])==10000 and c['initial_previous_quote_none'].shape==c['initial_quote_capacity_zero'].shape==() and c['initial_previous_quote_none'].dtype==c['initial_quote_capacity_zero'].dtype==bool and bool(c['initial_previous_quote_none']) and bool(c['initial_quote_capacity_zero']),'Actual original fresh startup differs')
    inputs=base.clock(c['expert_input_available_us'],(63,18),'Actual expert18 clocks');require(c['expert_state'].shape==(63,18) and np.isfinite(c['expert_state']).all() and (inputs.max(1)<=a['feature_available_us']).all(),'Actual current expert features/clocks differ')
    alg=run['algorithm'];require(alg['parent']==dict(fresh=True,step=0) and len(alg['parameter_birth_steps'])==13 and all(type(v) is int and v==0 for v in alg['parameter_birth_steps'].values()) and t['fresh_initialization'] and t['initial_step']==0 and t['fixed_target']==t['completed_updates']==512 and t['status']=='FRESH_FIXED512_COMPLETED' and t['failure'] is None and t['parameter_count']==13699 and t['forward_economic_scoring_used_for_training'] is False,'Actual fresh512/birth0 provenance differs')
    require(t['fold']==score['fold']==m['fold'] and t['model_identity']==score['model_identity']==m['model_identity'] and t['checkpoint_SHA256']==score['checkpoint_sha256']==m['files']['MODEL_ADAM_RNG.pt']['SHA256'] and scaler['identity']==fold['scaler_identity']==m['scaler_identity'] and scaler['provenance']==fold['scaler_provenance'] and alg['versioned_sources']==m['versioned_sources'],'Actual model/scaler/source receipt identities differ')
    fit=datetime.fromisoformat(score['actual_fit_completed_UTC']);require(fit.tzinfo is not None and fit<=datetime.now(UTC) and score['optimizer_updates_during_forward']==0 and score['terminal_frozen_before_forward_economic_score'] and score['inference_Torch_RNG_unchanged'] and score['native_wallets']==0,'Actual retrospective/frozen inference receipt differs')
    require(len(fold['training_wallets'])==5 and sum(p['decisions'] for p in fold['training_wallets'])==749 and fold['additional_embargo_days']==0 and scaler['provenance']['training_cutoff_us']==CAL['start'],'Actual strict prefix/no-embargo declaration differs')
    return dict(status='PASS_ORIGINAL_APRIL_EXPORT_INTERFACE',calendar=CAL,terminal_maximum_field='OMITTED_IN_ORIGINAL_EXPORT;VERIFIED_FROM_HASH_BOUND_OUTCOME_PACKET',paid_terminal_close_available_us=int(outcome.max()),producer_manifest_SHA256=MANIFEST_SHA,model_tensors_loaded=False)


def actual_prefix(state,cache,producer):
    """Reconcile consumed episode identities using original numeric identity ABI.

Only the NumPy window readers are imported. Identity dictionaries below follow
the hash-bound Episode/ExpandedEpisode/ExpertEpisode schemas; they are not a
financial engine or a model. Original normalizer reconstruction is comparison
with the frozen export, never a new producer fit or an inference input.
"""
    import numpy as np
    run=read(producer/'RUN.json');spec=run['specification'];fold=spec['data_split_identity']['fold']
    sources={**spec['sources'],**spec['algorithm']['versioned_sources']}
    for name,h in sources.items():require(sha(cache/name)==h,'Bound original producer source differs: '+name)
    require(sha(cache/PREFIX/'READY.json')==READY_SHA,'Original fresh prefit receipt differs')
    initial=read(cache/PREFIX/'READY.json')['folds']['FOLD_20240401']
    require(initial['binding']==run and initial['empty_Adam'] and initial['optimizer_updates']==0 and initial['parameter_count']==13699 and initial['model_identity']==spec['initial_model_identity'],'Original empty-Adam birth0 receipt differs')
    proof_path=state/'april-prefix-proof/46a4d0abf8f935795cd7c4d9931040dde4985cb6'/PREFIX/'KNOWN_FLAT_PREFIX_PROOF.json'
    require(sha(proof_path)==PROOF_SHA,'Original published known-flat prefix proof differs');proof=read(proof_path)
    require(proof['native_contract_SHA256']==CONTRACT_SHA and proof['frozen_prefit_prefix_proof']==fold['training_wallets'][-1] and proof['prefix_identity']==spec['data_split_identity']['train'][-1] and proof['raw_March31_outcome_consumed'] is False,'Actual consumed RUN prefix identity differs from prefit proof')
    for name,(relative,h) in april.TRAIN_FILES.items():require(sha(state/relative)==h,'Actual retained prefix bytes differ: '+name)
    package='_april_native_numeric_reader';module=types.ModuleType(package);module.__path__=[str(cache/'modules/temporal_two_expert')];sys.modules[package]=module
    for name in ('inputs','feature_windows'):
        full=package+'.'+name;s=importlib.util.spec_from_file_location(full,Path(module.__path__[0])/(name+'.py'));m=importlib.util.module_from_spec(s);sys.modules[full]=m;s.loader.exec_module(m)
    reader=sys.modules[package+'.inputs'];features=sys.modules[package+'.feature_windows'].load_feature_inputs(state/april.TRAIN_FILES['features.npz'][0],state/april.TRAIN_FILES['feature_manifest.json'][0]);ad=reader.array_digest;digest=reader.digest
    with np.load(state/april.TRAIN_FILES['economic.npz'][0],allow_pickle=False) as z:e={k:z[k].copy() for k in ('decision_us','episode_id','expert_targets','expert_eligible','target_available_us','past_returns30','start_execution_us','end_execution_us','start_price','end_price','funding_per_unit')}
    with np.load(state/april.TRAIN_FILES['short.npz'][0],allow_pickle=False) as z:short={k:z[k].copy() for k in ('decision_us','expert_targets','expert_eligible','target_available_us','asset_context_available_us')}
    require(np.array_equal(e['decision_us'],short['decision_us']),'Actual training expert dates differ')
    batches=[];decisions=[];labels=[];experts=[];identities=[]
    for i,p in enumerate(fold['training_wallets']):
        ix=np.flatnonzero((e['episode_id']==i)&(e['decision_us']<CAL['start']));tt=e['decision_us'][ix];n=len(tt)
        require(n==p['decisions'] and np.array_equal(tt,np.arange(p['first_decision_us'],p['last_decision_us']+base.frozen.DAY,base.frozen.DAY,dtype=np.int64)) and np.array_equal(e['start_execution_us'][ix],tt+base.frozen.MINUTE+1),'Actual natural prefix dates/execution clocks differ')
        # No raw final-row outcome price or funding is selected for consumption.
        active=ix[:-1];terminal=ix[-1:];prices=np.concatenate((e['start_price'][ix],e['start_price'][terminal]));funding=np.concatenate((e['funding_per_unit'][active],np.zeros((1,5))));outcome=np.r_[e['end_execution_us'][active],e['start_execution_us'][terminal]]
        require(np.array_equal(e['end_price'][active],e['start_price'][ix[1:]]) and np.array_equal(outcome[:-1],tt[1:]+base.frozen.MINUTE+1) and outcome[-1]==p['paid_terminal_close_available_us']==p['latest_active_outcome_available_us'] and (outcome<CAL['start']).all(),'Actual paid prefix labels/prices cross fold start')
        targets=np.zeros((n,5,5));masks=np.zeros((n,5),bool);clocks=np.tile(tt[:,None],(1,5))
        targets[:,[0,1,4]]=e['expert_targets'][ix];masks[:,[0,1,4]]=e['expert_eligible'][ix];clocks[:,[0,1,4]]=e['target_available_us'][ix]
        window=features.windows(tt);contexts=[dict(decision=int(t),available=int(t),expert_targets=ad(targets[j]),eligible=ad(masks[j]),past_returns30=ad(e['past_returns30'][ix[j]]),market13=ad(np.zeros(13)),target_available_us=ad(clocks[j])) for j,t in enumerate(tt)]
        original=digest(dict(wallet_id=p['wallet_id'],windows=window.identity,contexts=contexts,prices=ad(prices),funding=ad(funding),labels=ad(outcome),start=int(tt[0]),end=int(tt[-1])+base.frozen.DAY,cutoff=CAL['start'],role='TRAIN',producer=april.TRAIN_FILES['economic.npz'][1]))
        targets=np.concatenate((targets,short['expert_targets'][ix]),1);masks=np.concatenate((masks,short['expert_eligible'][ix]),1);clocks=np.concatenate((clocks,short['target_available_us'][ix]),1)
        expanded=digest(dict(original=original,short_payload=april.TRAIN_FILES['short.npz'][1],canonical_order=base.E5+(base.SHORT,),private_coordinates=(0,1,2,4,5),targets=ad(targets),eligible=ad(masks),target_clocks=ad(clocks)))
        signed=np.where(masks[:,[1,4,5],None],targets[:,[1,4,5]],0.);expert_state=np.concatenate((signed.reshape(n,15)/.3,masks[:,[1,4,5]].astype(float)),1);expert_clocks=np.concatenate((np.repeat(clocks[:,[1,4,5]],5,1),clocks[:,[1,4,5]]),1)
        identity=digest(dict(original=expanded,layout=(base.E5[1],base.E5[4],base.SHORT),symbols=base.frozen.SYMBOLS,target_scale=.3,state=ad(expert_state),clocks=ad(expert_clocks)))
        require(identity==p['identity']==spec['data_split_identity']['train'][i],'Independent actual consumed prefix episode identity differs')
        require((expert_clocks<=tt[:,None]).all() and (short['asset_context_available_us'][ix]<=tt[:,None]).all(),'Actual consumed prefix expert inputs are future')
        if i==4:require(ad(prices[-1])==proof['terminal_price_SHA256'] and ad(funding[-1])==proof['terminal_funding_SHA256'] and int(e['end_execution_us'][ix[-1]])==proof['raw_March31_outcome_available_us'],'Known-flat observed terminal identity or excluded raw label differs')
        batches.append(window);decisions.append(tt);labels.append(outcome);experts.append(np.maximum(clocks.max(1),short['asset_context_available_us'][ix].max(1)));identities.append(identity)
    # Read-only reconstruction verifies frozen normalizer values and provenance.
    scaler=reader.fit_standardizer(batches,training_cutoff_us=CAL['start'])
    require(scaler.identity==proof['scaler_identity']==fold['scaler_identity'] and scaler.provenance==fold['scaler_provenance'],'Actual frozen normalizer identity/provenance differs')
    with np.load(producer/'SCALER.npz',allow_pickle=False) as z:require(all(np.array_equal(z[k],getattr(scaler,k)) for k in ('mean','scale','count')),'Actual frozen normalizer values differ')
    clock_packet=dict(sample_decision_us=np.concatenate(decisions),feature_available_us=np.concatenate([np.where(w.valid,w.available_us,0).max((1,2,3)) for w in batches]),expert_input_available_us=np.concatenate(experts),label_available_us=np.concatenate(labels),scaler_input_available_us=np.unique(np.concatenate([w.completed_us.ravel() for w in batches])))
    require(len(clock_packet['sample_decision_us'])==749 and len(clock_packet['scaler_input_available_us'])==878 and (clock_packet['feature_available_us']<=clock_packet['sample_decision_us']).all() and all((v<CAL['start']).all() for v in clock_packet.values()),'Actual consumed prefix sample/scaler clocks cross April1')
    return dict(status='PASS_INDEPENDENT_ACTUAL_CONSUMED_PREFIX_EPISODE_IDENTITIES_CLOCKS_NORMALIZER_AND_READY',training_samples=749,scaler_rows=878,active_intervals=744,known_flat_paid_closes=5,episode_identities=identities,maximum_training_label_available_us=int(clock_packet['label_available_us'].max()),maximum_scaler_input_available_us=int(clock_packet['scaler_input_available_us'].max()),raw_March31_outcome_consumed=False,prefix_identity=proof['prefix_identity'],known_flat_proof_SHA256=PROOF_SHA,scaler_identity=scaler.identity,scaler_values_bit_identical=True,initial_model_identity=initial['model_identity'],initial_optimizer_updates=0,parameter_count=13699,optimizer_history_replayed=False,model_tensors_loaded=False,model_fits=0),clock_packet


def options(state):
    contract=read(CONTRACT);return dict(calendar=CAL,contract_path=CONTRACT,short_context=(CONTRACT.parent/'MOMENTUM_SHORT_CONTEXTS63.npz',contract['context_files']['MOMENTUM_SHORT_CONTEXTS63.npz']['sha256']),request_schema=native.SCHEMA,provenance_check=lambda p,m,a,c:provenance(state,p,m,a,c))


def provenance(state,path,m,a,c):
    import numpy as np
    cache,producer,wrapper=locations(state);require(path.parent==wrapper and m['calendar']==CAL and m['adapter_contract_sha256']==CONTRACT_SHA and sha(CONTRACT)==CONTRACT_SHA,'Exact April wrapper/calendar/unchanged contract required')
    receipt=inspect_export(producer);require(receipt['calendar']==CAL,'Actual frozen April producer calendar differs')
    original=read(producer/'MANIFEST.json')
    for name,v in original['files'].items():require((producer/name).stat().st_size==v['bytes'] and sha(producer/name)==v['SHA256'],'Actual frozen producer member differs')
    label=LABELS[m['arm_id']];full,_=base.validate(m,a,c,CAL)
    with np.load(producer/'PAIRED_PATHS.npz',allow_pickle=False) as z:
        require(np.array_equal(z['decision_us'],a['decision_us']) and np.array_equal(z[label+'_requests'],full),'Actual exported paired request bytes differ')
        fractions,budgets=base.mapped(full,c,base.frozen.modules(state).mapper,CAL)
        require(np.array_equal(z[label+'_targets'],fractions) and np.array_equal(z[label+'_budget'],budgets),'Original producer/native63 mapped targets/budgets differ')
    with np.load(producer/'CURRENT_CONTEXT63.npz',allow_pickle=False) as z:
        for key in ('expert_targets','expert_eligible','target_available_us'):require(np.array_equal(z[key][:,[0,1,4,5]],c[key][:,[0,1,4,5]]),'Actual current admitted contexts differ: '+key)
        require(np.array_equal(z['past_returns30'],c['past_returns30']),'Actual current covariance differs')
        selected=[1,4,5];state18=np.concatenate((np.where(c['expert_eligible'][:,selected,None],c['expert_targets'][:,selected],0.).reshape(63,15)/.3,c['expert_eligible'][:,selected].astype(float)),1);clock18=np.concatenate((np.repeat(c['target_available_us'][:,selected],5,1),c['target_available_us'][:,selected]),1)
        require(np.array_equal(z['expert_state'],state18) and np.array_equal(z['expert_input_available_us'],clock18),'Current18 expert features/masks/clocks differ')
    if m['policy_role']=='FIXED_CONTROL':
        require(m['arm_id'] in ('STATIC50','CASH50') and np.array_equal(full,base.fixed_control_requests(m['arm_id'],CAL)) and m['actual_fit_completed_UTC'] is None,'Actual fixed control differs')
        return dict(status='PASS_ACTUAL_EXPORTED_FIXED_CONTROL_CURRENT_CONTEXT_AND_BIT_IDENTICAL_MAPPER_NO_FIT',model_fits=0)
    proof,clocks=actual_prefix(state,cache,producer)
    require(proof==read(wrapper/'PREFIX_PROOF.json') and m['maximum_training_label_available_us']==proof['maximum_training_label_available_us'] and m['maximum_scaler_input_available_us']==proof['maximum_scaler_input_available_us'],'Actual independently derived consumed-prefix receipt differs')
    with np.load(wrapper/'TRAINING_CLOCKS.npz',allow_pickle=False) as z:require(set(z.files)==set(clocks) and all(np.array_equal(z[k],v) for k,v in clocks.items()),'Actual consumed-prefix per-sample clocks differ')
    return dict(proof,current_expert_inputs_and_producer_mapper='BIT_IDENTICAL',completed_updates=512)


def prepare(state):
    import numpy as np
    require(sha(CONTRACT)==CONTRACT_SHA,'Keep original preparation contract unchanged');cache,producer,wrapper=locations(state);require(not wrapper.exists(),'Fresh April wrapper directory required');wrapper.mkdir(parents=True)
    interface=inspect_export(producer);require(interface['calendar']==CAL,'Exact authorized April export required')
    proof,clocks=actual_prefix(state,cache,producer);np.savez_compressed(wrapper/'TRAINING_CLOCKS.npz',**clocks);(wrapper/'PREFIX_PROOF.json').write_text(json.dumps(proof,indent=2)+'\n')
    shutil.copytree(producer,wrapper/'producer');run=read(producer/'RUN.json');spec=run['specification'];sources={**spec['sources'],**spec['algorithm']['versioned_sources']}
    for n in sources:p=wrapper/'source'/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(cache/n,p)
    shutil.copyfile(cache/PREFIX/'READY.json',wrapper/'READY.json');shutil.copyfile(CONTRACT.parent/'CANONICAL_CONTEXTS63.npz',wrapper/'CANONICAL_CONTEXTS63.npz')
    with np.load(producer/'REQUESTS.npz',allow_pickle=False) as z:a={k:z[k].copy() for k in z.files}
    with np.load(producer/'PAIRED_PATHS.npz',allow_pickle=False) as z:
        for arm,label in list(LABELS.items())[1:]:
            current={k:v.copy() for k,v in a.items()};current['desired_expert_budget']=z[label+'_requests'].copy();np.savez_compressed(wrapper/(arm+'_REQUESTS.npz'),**current)
            (wrapper/(arm+'_PLAN.json')).write_text(json.dumps(dict(policy_role='FIXED_CONTROL',fits=0,calendar=CAL,control=arm),indent=2)+'\n')
    files={p.relative_to(wrapper).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(wrapper.rglob('*')) if p.is_file()};PUBLIC.mkdir(exist_ok=False);records={}
    native.readiness(state,calendar=CAL,contract_path=CONTRACT)
    for arm in LABELS:
        control=arm!=MODEL;planfile=arm+'_PLAN.json' if control else 'producer/RUN.json';requestfile=arm+'_REQUESTS.npz' if control else 'producer/REQUESTS.npz'
        m=dict(schema=native.SCHEMA,arm_id=arm,policy_role='FIXED_CONTROL' if control else 'LEARNED_FROZEN',objective_version=2,prediction_role='HISTORICAL_FROZEN_REPLAY_NOT_LIVE_PREDICTIONS',source_files=['source/'+n for n in sources],files=files,request_file=requestfile,producer_commit=read(producer/'MANIFEST.json')['producer_commit'],expert_order=list(base.E5+(base.SHORT,)),allowed_actions=list(base.COMPACT+(base.SHORT,)),uses_feedback_features=False,calendar=CAL,adapter_contract_sha256=CONTRACT_SHA,training_cutoff_us=CAL['start'],maximum_training_label_available_us=0 if control else proof['maximum_training_label_available_us'],maximum_scaler_input_available_us=0 if control else proof['maximum_scaler_input_available_us'],actual_fit_completed_UTC=None if control else read(producer/'RESULT.json')['actual_fit_completed_UTC'],actual_export_completed_UTC=datetime.now(UTC).isoformat(),training_plan_file=planfile,training_plan_sha256=files[planfile]['sha256'],model_sha256=None if control else files['producer/MODEL_ADAM_RNG.pt']['sha256'],scaler_sha256=None if control else files['producer/SCALER.npz']['sha256'])
        path=wrapper/('MANIFEST_'+arm+'.json');path.write_text(json.dumps(m,indent=2)+'\n');h=sha(path)
        _,_,_,gate=base.check(state,path,h,**options(state));require(not (state/'native-calendar-request-ledger'/h).exists() and not (state/'april63-native'/arm).exists(),'Never rerun a reserved/completed April wallet')
        plan=dict(schema='THREE_ACTUAL_FROZEN_APRIL63_NATIVE_EVALUATION_V1',authorization='USER_AUTHORIZED_REAL_FROZEN63_NATIVE_EVALUATION',arm_id=arm,calendar=CAL,request_manifest_sha256=h,adapter_contract_sha256=CONTRACT_SHA,engine_sha256=read(CONTRACT)['engine_sha256'],financial_contract=read(CONTRACT)['financial_contract'],resource_limits=read(CONTRACT)['limits'],mapping_preflight=gate,export_commit=EXPORT,producer_manifest_SHA256=MANIFEST_SHA,original_prefix_proof_SHA256=PROOF_SHA,entrypoint_source_SHA256={'research/recover-frozen-runner-20261009/april_native63.py':sha(Path(__file__))},fresh_capital_USDT=10000,paid_terminal_flat_required=True,source_plan_scope='THREE_SEPARATE_FRESH_ACCOUNTS_MODEL_THEN_STATIC50_THEN_CASH50;PUBLISH_FIRST_FINISHED',model_fits=0,model_inference=0,provider_downloads=0,completed_wallet_reruns=0)
        (PUBLIC/(arm+'.json')).write_text(json.dumps(plan,indent=2)+'\n');records[arm]=dict(manifest_sha256=h,request_sha256=gate['request_payload_sha256'],mapping_preflight=gate)
    report=dict(status='PASS_THREE_ACTUAL_EXPORTED_APRIL63_REQUESTS_CONSUMED_PREFIX_CONTEXTS_AND_MAPPER',unchanged_contract_SHA256=CONTRACT_SHA,export_commit=EXPORT,producer_manifest_SHA256=MANIFEST_SHA,prefix_proof=proof,arms=records,model_fits=0,model_inference=0,wallets_run=0,provider_downloads=0)
    (PUBLIC/'PRECHECK.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status=report['status'],arms={a:v['manifest_sha256'] for a,v in records.items()},prefix=proof)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('prepare','check','run'));p.add_argument('--state',type=Path,required=True);p.add_argument('--arm',choices=tuple(LABELS));p.add_argument('--plan-commit');p.add_argument('--plan-sha256');a=p.parse_args()
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','POLARS_MAX_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6000000000,6000000000));resource.setrlimit(resource.RLIMIT_CPU,(600,600))
    def blocked(*args,**kwargs):raise RuntimeError('Offline April native execution forbids network')
    socket.create_connection=blocked;socket.socket.connect=blocked
    if a.command=='prepare':prepare(a.state)
    else:
        require(a.arm is not None,'Explicit authorized April arm required');planpath=PUBLIC/(a.arm+'.json');plan=read(planpath);_,_,wrapper=locations(a.state);manifest=wrapper/('MANIFEST_'+a.arm+'.json')
        for name,h in plan['entrypoint_source_SHA256'].items():require(sha(base.frozen.REPO/name)==h,'Published April entry point differs')
        require(plan['authorization']=='USER_AUTHORIZED_REAL_FROZEN63_NATIVE_EVALUATION' and plan['calendar']==CAL and plan['adapter_contract_sha256']==CONTRACT_SHA,'Exact three-wallet April authorization required')
        if a.command=='check':print(json.dumps(base.check(a.state,manifest,plan['request_manifest_sha256'],**options(a.state))[3]),flush=True)
        else:
            require(a.plan_commit and a.plan_sha256,'Externally pinned published request-specific plan required');base.run(a.state,manifest,plan['request_manifest_sha256'],a.state/'april63-native'/a.arm,planpath,a.plan_sha256,a.plan_commit,**options(a.state))
