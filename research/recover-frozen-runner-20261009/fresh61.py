"""Validate and execute exactly one public fresh512 path over unchanged native61."""
import argparse,hashlib,importlib.util,json,os,resource,socket,sys,types
from pathlib import Path
import evaluate_requests61 as base
from prepare_short_expansion61 import expert_input_check
from prequential63_producer import TRAIN_FILES
HERE=base.HERE;PUBLIC=HERE/'fresh-initialization-native61';ARM='EXP_FRESH_DATE_512'
EXPORT='442c7a127187ae23c5d0a12a1324a4c4cc07e431';EVIDENCE='5870eddb2f60c15bab60e3a7285b2ca0d8395916';MANIFEST_SHA='ef4ca59643431cf08eb210e28c85d643154af073eee850d2f32106317abf66bb'
ORIGINAL_CONTRACT_SHA='9e29ad31a3c795e531e556c2da2f04dfa30d2d71e8df74111731360fc4ca07b2';WARM_COMMIT='d3d57332ca45b7a4443108db21f46abad0e1ac99'
sha=base.frozen.sha;read=base.frozen.read;require=base.frozen.require


def locations(state):return state/'temporal-fresh-init-exports'/EXPORT/ARM,state/'temporal-fresh-init-evidence'/EVIDENCE


def initialization(m,run,terminal,ready,comparison):
    spec=run['specification'];alg=spec['algorithm'];protocol=alg['protocol']
    require(m['arm_id']==ARM and m['initial_step']==0 and m['completed_initialization_updates']==m['cumulative_base_Adam_step']==m['new_head_Adam_step']==512,'One real fresh512 arm/age required')
    require(alg['parent']==dict(fresh=True,step=0) and len(alg['parameter_birth_steps'])==13 and set(alg['parameter_birth_steps'].values())=={0} and alg['mixing']==0 and alg['objective_version']==2,'Fresh births0/date objective v2 required')
    require(protocol['fixed_updates']==512 and protocol['seed']==20261009 and protocol['training_decisions']==778 and protocol['natural_wallet_lengths']==[54,88,62,144,430],'Exact source fixed512 recipe required')
    require(ready['binding']==run and ready['empty_Adam'] is True and ready['optimizer_updates']==0 and ready['initial_model_identity']==spec['initial_model_identity']==terminal['diagnostics'][0]['model_identity'],'Original bound fresh empty-Adam receipt differs')
    require(terminal['status']==m['terminal_training_status']=='FRESH_FIXED512_COMPLETED' and terminal['failure'] is None and terminal['fresh_initialization'] is True and terminal['initial_step']==0 and terminal['completed_updates']==terminal['fixed_target']==512 and terminal['parameters']==13699,'Original fixed512 terminal receipt differs')
    require(terminal['checkpoint_SHA256']==m['model_sha256'] and terminal['model_identity']==m['model_identity'] and terminal['development_scoring_used_for_training'] is False,'Frozen terminal model identity/role differs')
    require([d['snapshot_step'] for d in terminal['diagnostics']]==[0,128,256,512] and all(d['optimizer_updates']==0 and d['optimizer_state_accesses']==0 and d['RNG_unchanged'] for d in terminal['diagnostics']),'Train-only diagnostics changed fit history')
    for key in ('architecture_equal_except_initialization_metadata','training_features_targets_clocks_prices_funding_masks_identities_equal','same_supplied_weights_train_requests_bitwise_equal','fresh_Adam_empty','existing_sources_unchanged'):require(comparison[key] is True,'Original matched comparability receipt differs: '+key)
    require(comparison['training_decisions']==778 and comparison['unique_training_scaler_rows']==907 and comparison['fresh_parameters']==13699 and comparison['natural_wallet_lengths']==protocol['natural_wallet_lengths'] and comparison['data_identity']==spec['data_split_identity'],'Actual matched data/scaler receipt differs')
    require(comparison['warm_terminal_base_Adam_age']==1292 and comparison['warm_new_heads_Adam_age']==comparison['fresh_terminal_all_Adam_age_target']==512,'Declared unequal lifetime exposure differs')
    return dict(status='PASS_SOURCE_BOUND_FRESH_EMPTY_ADAM_BIRTH0_FIXED512_MATCHED_DATA_RECEIPTS',training_decisions=778,scaler_rows=907,parameters=13699,fresh_all_Adam_age=512,warm_base_Adam_age=1292,warm_heads_Adam_age=512,initial_model_identity=ready['initial_model_identity'],initial_parameters_identity=ready['initial_parameter_identity'],initial_all_RNG_identity=ready['initial_all_RNG_identity'],optimizer_history_replayed=False,model_tensors_loaded=False,equal_lifetime_exposure=False)


def prefix(state,bundle,m):
    import numpy as np
    for name,(relative,h) in TRAIN_FILES.items():require(sha(state/relative)==h,'Actual retained training bytes differ: '+name)
    package='_fresh61_actual_prefix';module=types.ModuleType(package);module.__path__=[str(bundle/'source/modules/temporal_two_expert')];sys.modules[package]=module
    for name in ('inputs','feature_windows'):
        full=package+'.'+name;s=importlib.util.spec_from_file_location(full,Path(module.__path__[0])/(name+'.py'));mod=importlib.util.module_from_spec(s);sys.modules[full]=mod;s.loader.exec_module(mod)
    inputs=sys.modules[package+'.inputs'];features=sys.modules[package+'.feature_windows'].load_feature_inputs(state/TRAIN_FILES['features.npz'][0],state/TRAIN_FILES['feature_manifest.json'][0])
    with np.load(state/TRAIN_FILES['economic.npz'][0],allow_pickle=False) as z:e={k:z[k].copy() for k in ('decision_us','episode_id','target_available_us','start_execution_us','end_execution_us')}
    with np.load(state/TRAIN_FILES['short.npz'][0],allow_pickle=False) as z:s={k:z[k].copy() for k in ('decision_us','target_available_us','asset_context_available_us')}
    tt=e['decision_us'];require(len(tt)==778 and np.array_equal(s['decision_us'],tt) and np.array_equal(e['start_execution_us'],tt+base.frozen.MINUTE+1) and np.array_equal(e['end_execution_us'],tt+base.frozen.DAY+base.frozen.MINUTE+1),'Actual778 training decisions/outcome clocks differ')
    batches=[features.windows(tt[e['episode_id']==i]) for i in range(5)];require([len(b.decision_us) for b in batches]==[54,88,62,144,430],'Actual natural-wallet sample lengths differ')
    scaler=inputs.fit_standardizer(batches,training_cutoff_us=m['training_cutoff_us']);run=read(bundle/'RUN.json')['specification']
    require(scaler.identity==run['data_split_identity']['scaler'],'Independent source scaler identity differs')
    with np.load(bundle/'SCALER.npz',allow_pickle=False) as z:require(all(np.array_equal(z[k],getattr(scaler,k)) for k in ('mean','scale','count')),'Independent actual scaler values/counts differ')
    clocks=np.unique(np.concatenate([b.completed_us.ravel() for b in batches]));feature=np.concatenate([np.where(b.valid,b.available_us,0).max((1,2,3)) for b in batches]);expert=np.maximum(e['target_available_us'].max(1),np.maximum(s['target_available_us'].max(1),s['asset_context_available_us'].max(1)))
    require(len(clocks)==907 and (tt<m['training_cutoff_us']).all() and (feature<=tt).all() and (expert<=tt).all() and int(e['end_execution_us'].max())==m['maximum_training_label_available_us']<m['training_cutoff_us'] and int(clocks.max())==m['maximum_scaler_input_available_us']<m['training_cutoff_us'] and int(expert.max())==m['maximum_training_expert_input_available_us'],'Actual strict prefix label/scaler/expert clocks differ')
    return dict(status='PASS_INDEPENDENT_ACTUAL778_PREFIX_AND907_SCALER_VALUES_CLOCKS',scaler_identity=scaler.identity,maximum_training_label_available_us=int(e['end_execution_us'].max()),maximum_scaler_input_available_us=int(clocks.max()),maximum_training_expert_input_available_us=int(expert.max()),retained_training_SHA256={n:h for n,(_,h) in TRAIN_FILES.items()},scaler_values_bit_identical=True,model_tensors_loaded=False)


def provenance(state,path,m,a,c):
    import numpy as np
    bundle,evidence=locations(state);require(path.parent==bundle and sha(path)==MANIFEST_SHA and m['producer_commit']=='34c73c2d28947d7847a11a8c9f15ba24bccdd860' and m['native_adapter_contract_sha256']==ORIGINAL_CONTRACT_SHA,'Original public export/source/contract identity differs')
    contract=read(PUBLIC/'ADAPTER_CONTRACT.json')
    for name,v in contract['public_evidence_files'].items():require((evidence/name).stat().st_size==v['bytes'] and sha(evidence/name)==v['SHA256'],'Original published evidence differs: '+name)
    run=read(bundle/'RUN.json');terminal=read(bundle/'TERMINAL.json');ready=read(evidence/'READY.json');comparison=read(evidence/'COMPARABILITY.json');birth=initialization(m,run,terminal,ready,comparison)
    warm=state/'temporal-weighting512-exports'/WARM_COMMIT/'EXP_GRU64_WEIGHT_DATE'
    for name,h in comparison['comparator_files_SHA256'].items():require(sha(warm/name)==h,'Retained exact warm comparator bytes differ: '+name)
    require(run['specification']['data_split_identity']==read(warm/'RUN.json')['specification']['data_split_identity'] and (bundle/'SCALER.npz').read_bytes()==(warm/'SCALER.npz').read_bytes(),'Actual warm/fresh split or scaler differs')
    spec=run['specification'];sources={**spec['sources'],**spec['algorithm']['versioned_sources']}
    for name,h in sources.items():require(sha(bundle/'source'/name)==h,'Bound full producer source differs: '+name)
    current=expert_input_check(path,m,a,c,{},dict(current_expert_inputs_SHA256=m['files'][m['current_expert_input_file']]['sha256'],input_enabled=True),state)
    actual_prefix=prefix(state,bundle,m);full,_=base.validate(m,a,c);f,b=base.mapped(full,c,base.frozen.modules(state).mapper)
    with np.load(evidence/'SEEN61_PATH.npz',allow_pickle=False) as z:
        require(np.array_equal(z['decision_us'],a['decision_us']) and np.array_equal(z['requests'],full) and np.max(abs(z['targets']-f))<1e-14 and np.max(abs(z['mapped_budget']-b))<1e-14,'Original source proxy/native E6 target/budget parity differs')
    return dict(initialization=birth,actual_prefix=actual_prefix,current_expert_input=current,producer_mapper_parity='PASS_ORIGINAL_FROZEN_RAW_REQUESTS_PRIVATE5_TO_CANONICAL_E6_TARGETS_BUDGETS_WITHIN1E14',fits=0,model_inference=0)


def check(state):
    bundle,_=locations(state);return base.check(state,bundle/'MANIFEST.json',MANIFEST_SHA,contract_path=PUBLIC/'ADAPTER_CONTRACT.json',provenance_check=lambda p,m,a,c:provenance(state,p,m,a,c))


def prepare(state):
    require(sha(HERE/'EVALUATE_REQUESTS61_ADAPTER.json')==ORIGINAL_CONTRACT_SHA,'Original frozen61 contract changed');PUBLIC.mkdir(exist_ok=True);contract=read(HERE/'EVALUATE_REQUESTS61_ADAPTER.json')
    for name in contract['source_sha256']:contract['source_sha256'][name]=sha(base.frozen.REPO/name)
    for name in ('fresh61.py','prepare_short_expansion61.py'):contract['source_sha256'][(HERE/name).relative_to(base.frozen.REPO).as_posix()]=sha(HERE/name)
    bundle,evidence=locations(state);recovery=read(evidence/'RECOVERED_PUBLIC_BYTES.json');contract.update(original_financial_contract_SHA256=ORIGINAL_CONTRACT_SHA,original_warm_reproduction_commit='85fa946b4be3d9b3b2b7ffad2ee058f8b33e9014',public_evidence_commit=EVIDENCE,public_evidence_files={v['path']:dict(bytes=v['bytes'],SHA256=v['SHA256']) for v in recovery['files']},current_requests='ONE_REAL_FRESH512_FROZEN_PATH',authorization='ONE_FRESH10000_MAY_JUNE61_NATIVE_ACCOUNT_ONLY_REUSE_WARM_JOURNALS_NO_RERUN')
    path=PUBLIC/'ADAPTER_CONTRACT.json';require(not path.exists(),'New immutable current-source contract required');path.write_text(json.dumps(contract,indent=2)+'\n');m,f,b,gate=check(state)
    require(not (state/'native61-request-ledger'/MANIFEST_SHA).exists() and not (state/'temporal-fresh-init-native61'/ARM).exists(),'Fresh request/output identity already reserved; never rerun')
    warm=state/'temporal-weighting512-native61/EXP_GRU64_WEIGHT_DATE';summary=read(warm/'account/summary.json');audit=read(warm/'INDEPENDENT_AUDIT.json');require(audit['status'].startswith('PASS_') and summary['terminal_cash_realized'] and summary['completed_minutes']==87840,'Retained warm native comparator incomplete')
    plan=dict(schema='ONE_AUTHORIZED_FRESH_INITIALIZATION_NATIVE61_V1',authorization='USER_AUTHORIZED_ONE_FRESH_NATIVE61_ACCOUNT',arm_id=ARM,request_manifest_sha256=MANIFEST_SHA,adapter_contract_sha256=sha(path),original_financial_contract_SHA256=ORIGINAL_CONTRACT_SHA,engine_sha256=contract['engine_sha256'],financial_contract=contract['financial_contract'],limits=contract['limits'],fresh_start=dict(capital_USDT=10000,previous_quote=None,initial_positions=0,initial_capacity=0),calendar=dict(start=base.frozen.START,end_exclusive=base.frozen.END,days=61,minutes=87840,funding_events=915),public_export=dict(commit=EXPORT,path='research/temporal-fresh-initialization-20261009/native61-requests/'+ARM+'/MANIFEST.json',manifest_SHA256=MANIFEST_SHA,request_SHA256=m['files'][m['request_file']]['sha256'],model_SHA256=m['model_sha256'],scaler_SHA256=m['scaler_sha256'],evidence_commit=EVIDENCE),mapping_preflight=gate,reused_warm_native=dict(public_commit='85fa946b4be3d9b3b2b7ffad2ee058f8b33e9014',relative_path='temporal-weighting512-native61-results/EXP_GRU64_WEIGHT_DATE',summary_SHA256=sha(warm/'account/summary.json'),audit_SHA256=sha(warm/'INDEPENDENT_AUDIT.json'),execution_SHA256=sha(warm/'EXECUTION.json'),net_PnL_USDT=summary['net_PnL'],reruns=0),data_role='SEEN_INITIALIZATION_REGIME_ABLATION_NOT_OOS_OR_EQUAL_LIFETIME_EXPOSURE',fits=0,model_inference=0,provider_downloads=0,completed_wallet_reruns=0,stop='ANY_SOURCE_CLOCK_MAPPING_MARK_CAPACITY_ACCOUNT_FAILURE;600CPU_AND_WALL_SECONDS;6GB_AS;15GiB_RESERVE')
    (PUBLIC/(ARM+'.json')).write_text(json.dumps(plan,indent=2)+'\n');(PUBLIC/'READINESS.json').write_text(json.dumps(gate,indent=2)+'\n');(PUBLIC/'MANIFEST.json').write_bytes((bundle/'MANIFEST.json').read_bytes());print(json.dumps(dict(status='PASS_EXACT_FRESH512_E6_PREFIX_AND_NATIVE_MAPPING_READY_FOR_PUBLIC_PLAN',manifest_SHA256=MANIFEST_SHA,contract_SHA256=sha(path),warm_native_PnL=summary['net_PnL'],wallets_run=0)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('prepare','check','run'));p.add_argument('--state',type=Path,required=True);p.add_argument('--plan-commit');p.add_argument('--plan-sha256');p.add_argument('--contract-sha256');a=p.parse_args()
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','POLARS_MAX_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6000000000,6000000000));resource.setrlimit(resource.RLIMIT_CPU,(600,600))
    def blocked(*a,**kw):raise RuntimeError('Offline native61 forbids provider/network calls')
    socket.create_connection=blocked;socket.socket.connect=blocked
    if a.command=='prepare':prepare(a.state)
    elif a.command=='check':print(json.dumps(check(a.state)[3]),flush=True)
    else:
        path=PUBLIC/'ADAPTER_CONTRACT.json';plan=PUBLIC/(ARM+'.json');require(a.plan_commit and a.plan_sha256 and a.contract_sha256 and sha(path)==a.contract_sha256 and read(plan)['authorization']=='USER_AUTHORIZED_ONE_FRESH_NATIVE61_ACCOUNT','Actual published one-account plan and external contract SHA required');bundle,_=locations(a.state)
        base.run(a.state,bundle/'MANIFEST.json',MANIFEST_SHA,a.state/'temporal-fresh-init-native61'/ARM,plan,a.plan_sha256,a.plan_commit,contract_path=path,provenance_check=lambda p,m,arrays,c:provenance(a.state,p,m,arrays,c))
