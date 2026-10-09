"""Validate two published frozen E6 request bundles and write bounded plans.

Reads numeric contexts and producer source constants; never imports models or
producer execution code. No fits, accounts or provider access.
"""
import argparse, ast, importlib.util, json, os, resource, socket, sys
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


def prepare(state,bundles,output):
    assert sha(HERE/'EVALUATE_REQUESTS61_ADAPTER.json')==CONTRACT_SHA
    assert sha(bundles/'INDEX.json')==INDEX_SHA
    index=read(bundles/'INDEX.json');assert tuple(index['arms'])==ARMS and index['canonical_E5_slots_preserved'] and index['appended_short_slot']==5
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
    output.mkdir(exist_ok=False);records={};prior=[]
    for i,name in enumerate(ARMS):
        entry=index['arms'][name];bundle=bundles/entry['manifest'];manifest=read(bundle)
        assert entry['requests_sha256']==REQUESTS[i] and manifest['native_adapter_contract_sha256']==CONTRACT_SHA
        assert manifest['files'][manifest['request_file']]['sha256']==REQUESTS[i]
        source=bundle.parent/'source/modules/temporal_short_expansion/adapter.py';assert sha(source)==SOURCE_SHA
        constants={node.targets[0].id:ast.literal_eval(node.value) for node in ast.parse(source.read_text()).body if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id in ('SOURCE_COMMIT','PAYLOADS','ACTIVE_COORDINATES')}
        assert constants==dict(SOURCE_COMMIT='1291857d53360e4e06a4dd50540c130886deffbf',PAYLOADS=PAYLOADS,ACTIVE_COORDINATES=(0,1,2,4,5))
        run=read(bundle.parent/'RUN.json');split=run['specification']['data_split_identity'];terminal=read(bundle.parent/'TERMINAL.json')
        assert split['source_commit']==constants['SOURCE_COMMIT'] and split['short_payloads']==PAYLOADS
        assert manifest['parent_checkpoint_sha256']==terminal['parent_checkpoint_SHA256']=='24152f6854a4826696fe74e948c56f744cbaf651d9d36dc01f78e3651374086f'
        assert terminal['status']==manifest['terminal_training_status']=='CAPPED_NOT_CONVERGED' and terminal['failure'] is None
        assert terminal['completed_stage_updates']==manifest['completed_expansion_updates']==entry['completed_expansion_updates']
        m,fractions,budgets,gate=adapter.check(state,bundle,entry['manifest_sha256'])
        _,arrays=adapter.load_bundle(bundle,entry['manifest_sha256'])
        assert m['expert_order']==list(canonical['expert_order']) and not np.any(arrays['desired_expert_budget'][:,2:4])
        producer_targets,producer_records=prototype.mapped_path(arrays['desired_expert_budget'][:,coordinates],private_contexts)
        producer_budget=np.zeros((61,6));producer_budget[:,coordinates]=np.stack([r['budget'] for r in producer_records])
        target_error=float(abs(producer_targets-fractions).max());budget_error=float(abs(producer_budget-budgets).max())
        assert target_error<1e-14 and budget_error<1e-14, 'Source-bound producer private ABI differs from native canonical E6 mapping'
        gate['producer_mapper_parity']=dict(status='PASS_SOURCE_BOUND_ORIGINAL_PRIVATE5_VERSUS_CANONICAL_E6_MAPPING',prototype_SHA256=prototype_sha,maximum_target_error=target_error,maximum_budget_error=budget_error,targets_bit_identical=bool(np.array_equal(producer_targets,fractions)),budgets_bit_identical=bool(np.array_equal(producer_budget,budgets)),exported_mapper_parity_fields='PRESENT' if 'mapper_target_fractions' in arrays else 'NOT_EXPORTED_RAW_REQUESTS_ONLY',models_loaded=0,wallets_run=0)
        assert not (state/'native61-request-ledger'/entry['manifest_sha256']).exists(), 'Request wallet identity already reserved; never rerun'
        assert not (state/'temporal-short-native61'/name).exists(), 'Output already exists; preserve completed or failed prefix'
        prior.append((m['parent_checkpoint_sha256'],m['scaler_sha256'],m['training_plan_sha256'],split))
        plan=dict(schema='ONE_AUTHORIZED_FROZEN_SHORT_EXPANSION_NATIVE61_EVALUATION_V1',arm_id=name,request_manifest_sha256=entry['manifest_sha256'],adapter_contract_sha256=CONTRACT_SHA,
            public_export=dict(commit=COMMIT,path='research/temporal-short-expansion-20261009/native61-requests/'+entry['manifest'],request_sha256=REQUESTS[i],model_sha256=m['model_sha256'],index_sha256=INDEX_SHA),
            mapping_preflight=gate,canonical_E5_preserved=True,short_slot=5,short_target_provenance=dict(source_commit=constants['SOURCE_COMMIT'],source_SHA256=SOURCE_SHA,payloads=PAYLOADS,canonical_targets_masks_clocks_exact=True),
            training_status=terminal['status'],completed_expansion_updates=m['completed_expansion_updates'],cumulative_base_Adam_step=m['cumulative_base_Adam_step'],new_head_Adam_step=m['new_head_Adam_step'],actual_fit_completed_UTC=m['actual_fit_completed_UTC'],
            parent_checkpoint_sha256=m['parent_checkpoint_sha256'],fresh_capital_USDT=10000,calendar='2024May1-July1exclusive61days',engine_sha256=adapter.frozen.read(HERE/'EVALUATE_REQUESTS61_ADAPTER.json')['engine_sha256'],financial_contract=adapter.frozen.read(HERE/'EVALUATE_REQUESTS61_ADAPTER.json')['financial_contract'],resource_limits=adapter.frozen.read(HERE/'EVALUATE_REQUESTS61_ADAPTER.json')['limits'],
            sequencing='CONTROL_FIRST_REPORT_AND_PRESERVE_FIRST_FINISHED_RESULT_THEN_MOMENTUM_SHORT',primary_comparison='SHORT_VERSUS_THIS_MATCHED_CONTINUED_CONTROL; UNEQUAL_COMPLETED_UPDATES_AND_REALIZED_RISK_REMAIN',controls='REUSE_COMPLETED_STATIC50_CASH50_AND_PARENT_GRU_WITH_CASH_JOURNALS_WITHOUT_RERUN',
            development_role='ALREADY_SEEN_MAY_JUNE_NOT_OOS',approval='USER_AUTHORIZED_TWO_REQUEST_WALLETS_NOW',fits=0,model_inference=0,provider_downloads=0,completed_wallet_reruns=0,recipes_added=0,paid_terminal_flat=True)
        (output/(name+'.json')).write_text(json.dumps(plan,indent=2)+'\n');records[name]=dict(manifest_sha256=entry['manifest_sha256'],request_sha256=REQUESTS[i],mapping=gate,allowed_actions=m['allowed_actions'])
    assert prior[0]==prior[1], 'Matched source parent, scaler, training plan and dataset required'
    report=dict(status='PASS_TWO_ACTUAL_FROZEN_E6_EXPORTS_CANONICAL_SLOT5_TARGET_MASK_CLOCK_AND_CORRECTED_MAPPER_PARITY',public_export_commit=COMMIT,index_sha256=INDEX_SHA,adapter_contract_sha256=CONTRACT_SHA,original_E5_unchanged=True,short_slot=5,source_producer_adapter_SHA256=SOURCE_SHA,source_payloads=PAYLOADS,arms=records,matched_parent_scaler_training_plan_and_dataset=True,new_wallets=0,fits=0,models_loaded=0,provider_downloads=0)
    (output/'READINESS.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--bundles',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(2000000000,2000000000));resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    def blocked(*args,**kwargs):raise RuntimeError('Offline request preflight forbids network')
    socket.create_connection=blocked;socket.socket.connect=blocked
    prepare(a.state,a.bundles,a.output)
