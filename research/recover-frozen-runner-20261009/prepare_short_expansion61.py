"""Validate two published frozen E6 request bundles and write bounded plans.

Reads numeric contexts and producer source constants; never imports models or
producer execution code. No fits, accounts or provider access.
"""
import argparse, ast, hashlib, importlib.util, json, os, resource, socket, sys
from pathlib import Path
import numpy as np
import evaluate_requests61 as adapter

HERE=Path(__file__).resolve().parent
COMMIT='7059e955306a5285316b58f7d38a26f917cdb116'
INDEX_SHA='21f3a947463eba1e725dc2a9c17da61a453e4d06a4d2204ee84a03ae8693f36b'
CONTRACT_SHA='9e29ad31a3c795e531e556c2da2f04dfa30d2d71e8df74111731360fc4ca07b2'
SOURCE_SHA='a29dfa919b144f69ad50e3ef59a62d74aa966ebed28c57aa6b7eb89f5bcd1a1d'
ARMS=('EXP_GRU64_CASH_CONTROL','EXP_GRU64_CASH_MOM30_SHORT')
REQUESTS=('2c61c428f2f08e34ac79195b3c0b2557d683c5d752926dc629ab66ffed7f922e','7514bb2d9b0f92995bdf2f5b00b7ad2a191894996a1ab187608a8375bce4ec43')
PAYLOADS={'TRAIN778_MOMENTUM_SHORT_CONTEXTS.npz':'64accfc82f78034af0da48561ef7e2fabfc8712760066860194e3d2bce9e382d','DEV61_MOMENTUM_SHORT_CONTEXTS.npz':adapter.SHORT_SHA}
sha=adapter.frozen.sha
read=adapter.frozen.read


def expert_input_check(bundle,m,arrays,canonical,index,entry,state):
    assert sha(state/'v2-proxy-sources/H1_VALIDATE.npz')==index.get('original_recovered_H1_context_SHA256','c13de3125698f1fc350d1435453cbb6e33b7d5873537d7f859c1570344f081bc')=='c13de3125698f1fc350d1435453cbb6e33b7d5873537d7f859c1570344f081bc'
    p=adapter.member(bundle.parent,m['current_expert_input_file']);assert sha(p)==entry['current_expert_inputs_SHA256']=='129d7f188005f65684052cbfa5dc58017c8995453fe85081f9379241a6adf6be'
    with np.load(p,allow_pickle=False) as z:a={k:z[k].copy() for k in z.files}
    assert set(a)=={'decision_us','symbol_order','input_expert_order','expert_state','input_available_us','signed_targets','expert_eligible','target_available_us','target_unit'}
    indices=[1,4,5];targets=canonical['expert_targets'][:,indices];mask=canonical['expert_eligible'][:,indices];clocks=canonical['target_available_us'][:,indices]
    assert np.array_equal(a['decision_us'],arrays['decision_us']) and a['symbol_order'].tolist()==list(adapter.frozen.SYMBOLS)
    assert a['input_expert_order'].tolist()==[canonical['expert_order'][i] for i in indices] and float(a['target_unit'])==.3
    for key,expected in [('signed_targets',targets),('expert_eligible',mask),('target_available_us',clocks)]:assert np.array_equal(a[key],expected)
    expected=np.concatenate((np.where(mask[:,:,None],targets,0).reshape(61,15)/.3,mask.astype(float)),axis=1)
    available=np.concatenate((np.repeat(clocks,5,axis=1),clocks),axis=1)
    assert a['expert_state'].dtype==np.float64 and np.array_equal(a['expert_state'],expected)
    assert a['input_available_us'].dtype==np.int64 and np.array_equal(a['input_available_us'],available)
    assert np.all(available<=arrays['decision_us'][:,None]) and np.all(available.max(1)<=arrays['feature_available_us'])
    assert m['maximum_training_expert_input_available_us']<=m['training_cutoff_us'] and m['input_enabled']==entry['input_enabled']
    assert m['current_expert_input']['canonical_indices']==indices and m['current_expert_input']['width']==18 and m['current_expert_input']['target_scale']==.3
    assert index.get('parameter_count_per_arm',13699)==13699
    for name,h in [('inputs.py','13a5e7cf84918004f19423ac7b25ea49f69387ba0b72cfceb0f882a286e82f7d'),('model.py','ca3ca013896ce3aed057af98bde055cf9799afc9ca1a462fa347cb2fc5e49344')]:assert sha(bundle.parent/'source/modules/temporal_expert_input'/name)==h
    return dict(status='PASS_EXACT_CURRENT_CANONICAL_TARGET_ELIGIBILITY_INPUT_AND_SAVED_SOURCE_CLOCKS',packet_SHA256=sha(p),input_enabled=m['input_enabled'],width=18,canonical_indices=indices,masked_before_fixed_point3_scaling=True,flat_and_ineligible_distinct=True,target_mask_clock_state_bytes_exact=True,available_not_after_decision_or_feature_clock=True,source_declared_parameters_each=13699,parameter_tensors_loaded=False)


def prepare(state,bundles,output,profile='short-expansion'):
    commit,index_sha,arms,requests,member_root,state_root,updates=COMMIT,INDEX_SHA,ARMS,REQUESTS,'research/temporal-short-expansion-20261009/native61-requests','temporal-short-native61','completed_expansion_updates'
    if profile=='expert-input':
        commit='bd0d1d4b9b50fb8547f75f28c166bc445a09e073';index_sha='99f0b094cfbfe0de9d1e7007565f6290d245d63312853a11bf36a16f258780c7';arms=('EXP_GRU64_EXPERT_INPUT_CONTROL','EXP_GRU64_EXPERT_INPUT_ACTIVE');requests=('9180bf41fb4b137163ffdfc3c549ca61d13f4372d6bcb62e53243b7adaf820af','79bb6a38fb180e53422c4fd33f937abd7f08dac56c5a58a11a87e947aa1ce688');member_root='research/temporal-expert-input-20261009/native61-requests';state_root='temporal-expert-input-native61';updates='completed_input_ablation_updates'
    if profile=='weighting512':
        commit='d3d57332ca45b7a4443108db21f46abad0e1ac99';index_sha='da69245bf93928fa880bbf2ee9a3532acb54cf364199bc58579cb125c36306be';arms=('EXP_GRU64_WEIGHT_DATE','EXP_GRU64_WEIGHT_MIXED');requests=('7508a06345c92f72c5a415985d9ed847ad83846b44f1fae232436d28ddd51181','7b1335872a03092bedcd2baef549aa17f5327cf2e32ca86cd80d75d4f52e4207');member_root='research/temporal-episode-weighting-v2-20261009/native61-requests';state_root='temporal-weighting512-native61';updates='completed_weighting_updates'
    assert sha(HERE/'EVALUATE_REQUESTS61_ADAPTER.json')==CONTRACT_SHA
    assert sha(bundles/'INDEX.json')==index_sha
    index=read(bundles/'INDEX.json');entries=index['bundles'] if profile=='weighting512' else index['arms'];assert set(entries)==set(arms)
    if profile=='short-expansion':assert index['canonical_E5_slots_preserved'] and index['appended_short_slot']==5
    elif profile=='expert-input':assert index['public_old_slots_preserved'] and index['canonical_expert_order']==list(adapter.E5+(adapter.SHORT,)) and index['native_adapter_contract_SHA256']==CONTRACT_SHA
    else:assert index['original_E5_slots_preserved'] and index['native_adapter_contract_SHA256']==CONTRACT_SHA
    for name,value in PAYLOADS.items():assert sha(HERE/'short-candidate-contexts'/name)==value
    before=adapter.contexts(state,False);canonical=adapter.contexts(state,True)
    for key in ('expert_targets','expert_eligible','target_available_us'):assert np.array_equal(before[key],canonical[key][:,:5])
    assert np.array_equal(before['past_returns30'],canonical['past_returns30'])
    with np.load(HERE/'short-candidate-contexts/DEV61_MOMENTUM_SHORT_CONTEXTS.npz',allow_pickle=False) as z:
        for key in ('expert_targets','expert_eligible','target_available_us'):assert np.array_equal(canonical[key][:,5:],z[key])
        assert np.all(z['expert_targets']<=0) and z['expert_asset_eligible'].dtype==bool and z['expert_asset_eligible'].shape==(61,1,5)
        assert not np.any(z['expert_targets'][~z['expert_asset_eligible']])
        assert np.all(z['asset_context_available_us']<=z['decision_us'][:,None])
    assert canonical['expert_order']==adapter.E5+(adapter.SHORT,)
    prototype_path=state/'v2-proxy-sources/prototype.py';prototype_sha='46a0ca0b76bf29d50133bdd85b5730f4fd029f05378ce2ef086752b869a8fcab'
    assert sha(prototype_path)==prototype_sha
    spec=importlib.util.spec_from_file_location('_short_expansion_bound_original_mapper',prototype_path);prototype=importlib.util.module_from_spec(spec);sys.modules[spec.name]=prototype;spec.loader.exec_module(prototype)
    coordinates=[0,1,2,4,5];private_contexts=[]
    for i,t in enumerate(range(adapter.frozen.START,adapter.frozen.END,adapter.frozen.DAY)):
        mask=canonical['expert_eligible'][i,coordinates].copy();mask[2]=False
        private_contexts.append(prototype.Context(int(t),int(t),canonical['expert_targets'][i,coordinates].copy(),mask,canonical['past_returns30'][i],np.zeros(13),canonical['target_available_us'][i,coordinates].copy()))
    output.mkdir(exist_ok=False);records={};prior=[];common_specs=[]
    for i,name in enumerate(arms):
        original_entry=entries[name]
        if profile=='short-expansion':entry=original_entry
        elif profile=='expert-input':entry=dict(original_entry,requests_sha256=original_entry['request_SHA256'],manifest_sha256=original_entry['manifest_SHA256'],completed_expansion_updates=original_entry['completed_updates'])
        else:entry=dict(original_entry,requests_sha256=original_entry['requests_SHA256'],manifest_sha256=original_entry['manifest_SHA256'],completed_expansion_updates=original_entry['completed_new_updates'],current_expert_inputs_SHA256=original_entry['current_expert_input_SHA256'])
        bundle=bundles/entry['manifest'];manifest=read(bundle)
        assert entry['requests_sha256']==requests[i] and manifest['native_adapter_contract_sha256']==CONTRACT_SHA
        assert manifest['files'][manifest['request_file']]['sha256']==requests[i]
        source=bundle.parent/'source/modules/temporal_short_expansion/adapter.py';assert sha(source)==SOURCE_SHA
        constants={node.targets[0].id:ast.literal_eval(node.value) for node in ast.parse(source.read_text()).body if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id in ('SOURCE_COMMIT','PAYLOADS','ACTIVE_COORDINATES')}
        assert constants==dict(SOURCE_COMMIT='1291857d53360e4e06a4dd50540c130886deffbf',PAYLOADS=PAYLOADS,ACTIVE_COORDINATES=(0,1,2,4,5))
        run=read(bundle.parent/'RUN.json');split=run['specification']['data_split_identity'];terminal=read(bundle.parent/'TERMINAL.json');short_split=split if profile=='short-expansion' else split['original_short_dataset']
        assert short_split['source_commit']==constants['SOURCE_COMMIT'] and short_split['short_payloads']==PAYLOADS
        initial='0f51bd3316f6e1100de518e8283ef3afb1c1148007bbb4d5fa7e3d1375acaddb' if profile=='weighting512' else '24152f6854a4826696fe74e948c56f744cbaf651d9d36dc01f78e3651374086f'
        status='FIXED_512_UPDATES_COMPLETED' if profile=='weighting512' else 'CAPPED_NOT_CONVERGED'
        assert manifest['parent_checkpoint_sha256']==terminal['parent_checkpoint_SHA256']==initial
        assert terminal['status']==manifest['terminal_training_status']==status and terminal['failure'] is None
        assert terminal['completed_stage_updates']==manifest[updates]==entry['completed_expansion_updates']
        m,fractions,budgets,gate=adapter.check(state,bundle,entry['manifest_sha256'])
        _,arrays=adapter.load_bundle(bundle,entry['manifest_sha256'])
        assert m['expert_order']==list(canonical['expert_order']) and not np.any(arrays['desired_expert_budget'][:,2:4])
        if profile!='short-expansion':gate['current_expert_input_check']=expert_input_check(bundle,m,arrays,canonical,index,entry,state)
        if profile=='weighting512':
            common=json.loads(json.dumps(run['specification']));algorithm=common['algorithm'];protocol=algorithm['protocol'];diagnostics=terminal['diagnostics']
            assert algorithm['arm']==name.removeprefix('EXP_') and algorithm['mixing']==i*.5 and algorithm['initial_snapshot_SHA256']==index['initial_snapshot_SHA256']==initial
            assert m[updates]==m['new_head_Adam_step']==terminal['fixed_update_target']==512 and m['cumulative_base_Adam_step']==1292 and m['input_enabled']
            assert protocol['expert_input_enabled_both'] and protocol['weighting_experiment_updates']==512 and protocol['initial_snapshot_SHA256']==initial and 'both13699parameters' in protocol['architecture']
            assert protocol['arm_mixing']=={'GRU64_WEIGHT_DATE':0.,'GRU64_WEIGHT_MIXED':.5} and protocol['sole_comparison']=='date_coefficients_n/778_vs_0.5*n/778+0.5/5;identical_expanded_pool_and_expert_inputs'
            assert diagnostics[0]['snapshot_step']==0 and diagnostics[0]['model_identity']==common['initial_model_identity']=='2dd1898b9f7e05cd9a7a8418bf7b1c8609c7f50b79c03110e68590e9630522ad'
            lengths=np.array([e['dates'] for e in diagnostics[0]['episodes']]);assert np.array_equal(lengths,[54,88,62,144,430])
            coefficients=(1-i*.5)*lengths/778+i*.5/5
            assert np.max(abs(coefficients-[e['coefficient'] for e in diagnostics[0]['episodes']]))<1e-15
            algorithm.pop('arm');algorithm.pop('mixing');common_specs.append(common)
            gate['matched_weighting512_contract']=dict(status='PASS_BYTE_BOUND_COMMON_INITIALIZATION_EXACT512_AND_ONLY_ARM_MIXING_SPEC_DIFFERENCES',initial_snapshot_SHA256=initial,initial_model_identity=common['initial_model_identity'],common_training_spec_SHA256=hashlib.sha256(json.dumps(common,sort_keys=True,separators=(',',':')).encode()).hexdigest(),completed_updates_each=512,cumulative_base_Adam_step_each=1292,new_parameter_Adam_step_each=512,source_declared_parameters_each=13699,episode_lengths=lengths.tolist(),episode_coefficients=coefficients.tolist(),mixing=i*.5,training_spec_differences_allowed=['algorithm.arm','algorithm.mixing'],trained_model_tensors_loaded=False,convergence_claim=False)
        producer_targets,producer_records=prototype.mapped_path(arrays['desired_expert_budget'][:,coordinates],private_contexts)
        producer_budget=np.zeros((61,6));producer_budget[:,coordinates]=np.stack([r['budget'] for r in producer_records])
        target_error=float(abs(producer_targets-fractions).max());budget_error=float(abs(producer_budget-budgets).max())
        assert target_error<1e-14 and budget_error<1e-14, 'Source-bound producer private ABI differs from native canonical E6 mapping'
        gate['producer_mapper_parity']=dict(status='PASS_SOURCE_BOUND_ORIGINAL_PRIVATE5_VERSUS_CANONICAL_E6_MAPPING',prototype_SHA256=prototype_sha,maximum_target_error=target_error,maximum_budget_error=budget_error,targets_bit_identical=bool(np.array_equal(producer_targets,fractions)),budgets_bit_identical=bool(np.array_equal(producer_budget,budgets)),exported_mapper_parity_fields='PRESENT' if 'mapper_target_fractions' in arrays else 'NOT_EXPORTED_RAW_REQUESTS_ONLY',models_loaded=0,wallets_run=0)
        assert not (state/'native61-request-ledger'/entry['manifest_sha256']).exists(), 'Request wallet identity already reserved; never rerun'
        assert not (state/state_root/name).exists(), 'Output already exists; preserve completed or failed prefix'
        prior.append((m['parent_checkpoint_sha256'],m['scaler_sha256'],m['training_plan_sha256'],split))
        plan=dict(schema='ONE_AUTHORIZED_FROZEN_SHORT_EXPANSION_NATIVE61_EVALUATION_V1',arm_id=name,request_manifest_sha256=entry['manifest_sha256'],adapter_contract_sha256=CONTRACT_SHA,
            public_export=dict(commit=commit,path=member_root+'/'+entry['manifest'],request_sha256=requests[i],model_sha256=m['model_sha256'],index_sha256=index_sha),
            mapping_preflight=gate,canonical_E5_preserved=True,short_slot=5,short_target_provenance=dict(source_commit=constants['SOURCE_COMMIT'],source_SHA256=SOURCE_SHA,payloads=PAYLOADS,canonical_targets_masks_clocks_exact=True),
            training_status=terminal['status'],**{updates:m[updates]},cumulative_base_Adam_step=m['cumulative_base_Adam_step'],new_head_Adam_step=m['new_head_Adam_step'],actual_fit_completed_UTC=m['actual_fit_completed_UTC'],
            parent_checkpoint_sha256=m['parent_checkpoint_sha256'],fresh_capital_USDT=10000,calendar='2024May1-July1exclusive61days',engine_sha256=adapter.frozen.read(HERE/'EVALUATE_REQUESTS61_ADAPTER.json')['engine_sha256'],financial_contract=adapter.frozen.read(HERE/'EVALUATE_REQUESTS61_ADAPTER.json')['financial_contract'],resource_limits=adapter.frozen.read(HERE/'EVALUATE_REQUESTS61_ADAPTER.json')['limits'],
            sequencing='CONTROL_FIRST_REPORT_AND_PRESERVE_FIRST_FINISHED_RESULT_THEN_ACTIVE_ARM',primary_comparison='ACTIVE_VERSUS_THIS_MATCHED_CONTROL; UNEQUAL_COMPLETED_UPDATES_AND_REALIZED_RISK_REMAIN',controls='REUSE_COMPLETED_STATIC50_CASH50_AND_PARENT_GRU_WITH_CASH_JOURNALS_WITHOUT_RERUN',
            development_role='ALREADY_SEEN_MAY_JUNE_NOT_OOS',approval='USER_AUTHORIZED_TWO_REQUEST_WALLETS_NOW',fits=0,model_inference=0,provider_downloads=0,completed_wallet_reruns=0,recipes_added=0,paid_terminal_flat=True)
        if profile!='short-expansion':plan.update(schema='ONE_AUTHORIZED_FROZEN_EXPERT_INPUT_NATIVE61_EVALUATION_V1',input_enabled=m['input_enabled'],current_expert_input_check=gate['current_expert_input_check'],source_declared_parameters_each=13699)
        if profile=='weighting512':plan.update(schema='ONE_AUTHORIZED_MATCHED512_WEIGHTING_NATIVE61_EVALUATION_V1',matched_weighting512_contract=gate['matched_weighting512_contract'],sequencing='DATE_WEIGHTED_FIRST_REPORT_AND_PRESERVE_THEN_HALF_EPISODE_MIXED',primary_comparison='HALF_DATE_HALF_EQUAL_EPISODE_MINUS_DATE_WEIGHTED; EXACT512_COMMON_INITIALIZATION; UNEQUAL_REALIZED_RISK_REMAINS')
        (output/(name+'.json')).write_text(json.dumps(plan,indent=2)+'\n');records[name]=dict(manifest_sha256=entry['manifest_sha256'],request_sha256=requests[i],mapping=gate,allowed_actions=m['allowed_actions'])
    assert prior[0]==prior[1], 'Matched source parent, scaler, training plan and dataset required'
    if profile=='weighting512':assert common_specs[0]==common_specs[1], 'Only weighting coefficient and arm identity may differ'
    report=dict(status='PASS_TWO_ACTUAL_FROZEN_E6_EXPORTS_CANONICAL_SLOT5_TARGET_MASK_CLOCK_AND_CORRECTED_MAPPER_PARITY',profile=profile,public_export_commit=commit,index_sha256=index_sha,adapter_contract_sha256=CONTRACT_SHA,original_E5_unchanged=True,short_slot=5,source_producer_adapter_SHA256=SOURCE_SHA,source_payloads=PAYLOADS,arms=records,matched_parent_scaler_training_plan_and_dataset=True,new_wallets=0,fits=0,models_loaded=0,provider_downloads=0)
    (output/'READINESS.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--bundles',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--profile',choices=('short-expansion','expert-input','weighting512'),default='short-expansion');a=p.parse_args()
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(2000000000,2000000000));resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    def blocked(*args,**kwargs):raise RuntimeError('Offline request preflight forbids network')
    socket.create_connection=blocked;socket.socket.connect=blocked
    prepare(a.state,a.bundles,a.output,a.profile)
