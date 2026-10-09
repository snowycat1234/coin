"""Bind existing public 2023 bytes and frozen paths; no fits or wallets."""
import argparse,importlib.metadata,json,os,resource,shutil,socket
from pathlib import Path
import evaluate_transfer63 as transfer
import prequential63_producer as producer
base=transfer.base;HERE=transfer.original.HERE


def prepare(state,cache,fold):
    import numpy as np
    require=base.frozen.require;public=HERE/'prequential2023'/fold;cal=transfer.FOLDS[fold]
    context=base.frozen.read(public/'CONTEXT_READY.json');data=base.frozen.read(state/'prequential2023-data'/transfer.PUBLIC_DATA[fold]['folder']/'NORMALIZED_RECOVERY.json')
    contract=base.frozen.read(HERE/'prequential63/ADAPTER_CONTRACT.json')
    for name in list(contract['source_sha256']):contract['source_sha256'][name]=base.frozen.sha(base.frozen.REPO/name)
    for name in ('evaluate_transfer63.py','recover_prequential2023.py','prepare_transfer63.py'):
        relative=(HERE/name).relative_to(base.frozen.REPO).as_posix();contract['source_sha256'][relative]=base.frozen.sha(HERE/name)
    contract.update(fold=fold,calendar=cal,calendar_UTC=fold+'_63_days_end_exclusive',canonical_context_SHA256=context['canonical_context_SHA256'],market_work_relative='prequential2023-data/'+transfer.PUBLIC_DATA[fold]['folder']+'/h1_market',market_artifacts=data['artifacts'],public_input_recovery=data,normalization_dependencies={n:importlib.metadata.version(n) for n in ('numpy','pandas','pyarrow','polars')},context_files={'CANONICAL_CONTEXTS63.npz':dict(bytes=(public/'CANONICAL_CONTEXTS63.npz').stat().st_size,sha256=context['canonical_context_SHA256'])},current_requests='REAL_FROZEN2023_SOURCE_CONTEXT_PREFIX_AND_MAPPING_VERIFIED',legacy_January_reproduction=dict(commit='ffd105da80b6c65b3cd707a0a2c8f4430d9d726c',contract_SHA256='34454d9e185c9a5cafed5dbed35d8673582e2bd460b8c9af5e2826b8d9d66e81',new_helper_source_requires_new_contract=True))
    contract['prefix_provenance']['training_cutoff_us']=cal['start'];contract['prefix_provenance'].pop('published_January_mode',None)
    contract['producer_interface'].update(native_end_exclusive_us=cal['end_exclusive'],auxiliary_surrogate_maturity_fence_us=cal['end_exclusive']+base.frozen.DAY,paid_surrogate_terminal_clock_us=cal['end_exclusive']-base.frozen.DAY+base.frozen.MINUTE+1)
    contract['fixture_acceptance']=dict(existing_61_and_63_fixtures=102,new_wallets_before_publication=0)
    path=public/'ADAPTER_CONTRACT.json';require(not path.exists(),'New immutable fold contract required');path.write_text(json.dumps(contract,indent=2)+'\n')
    wrapper=state/'prequential2023-wrappers'/fold;proof=producer.prepare(state,cache,wrapper,cal,fold,path,public/'CANONICAL_CONTEXTS63.npz')
    readiness=transfer.readiness(state,path);gates={};plans=public/'plans';plans.mkdir()
    arms=('FRESH_GRU_'+fold.replace('_',''),'STATIC50','CASH50');labels=('FRESH_GRU','VOL50_CS50','CASH50_VOL25_CS25')
    with np.load(wrapper/'producer/PAIRED_PATHS.npz',allow_pickle=False) as z:
        for arm,label in zip(arms,labels):
            manifest=wrapper/('MANIFEST_'+arm+'.json');m,f,b,gate=base.check(state,manifest,base.frozen.sha(manifest),**transfer.options(state,path))
            require(np.array_equal(z[label+'_budget'],b) and np.array_equal(z[label+'_targets'],f),'Original paired63 mapped budgets/targets differ: '+arm)
            gate.update(producer_mapper_parity='BIT_IDENTICAL_ALL63_BUDGETS_AND_TARGETS_WITH_PUBLISHED_PAIRED_PATHS',producer_pair_SHA256=base.frozen.sha(wrapper/'producer/PAIRED_PATHS.npz'),producer_policy=label);gates[arm]=gate;shutil.copyfile(manifest,plans/manifest.name)
            plan=dict(schema='PUBLISHED_PREQUENTIAL63_NATIVE_EXECUTION_PLAN_V1',authorization='USER_AUTHORIZED_REAL_FROZEN63_NATIVE_EVALUATION',arm_id=arm,producer_policy=label,request_manifest_sha256=base.frozen.sha(manifest),adapter_contract_sha256=base.frozen.sha(path),engine_sha256=contract['engine_sha256'],calendar=cal,fresh_capital_USDT=10000,fresh_start=contract['fresh_start'],limits=contract['limits'],original_financial_contract=contract['financial_contract'],public_export=dict(commit='38b86686e40a50c14f0499bd370e4a6bb3d0c339',path='research/temporal-prequential-transfer-20261009/forward/'+fold+'/MANIFEST.json',manifest_SHA256=producer.PRODUCER_MANIFESTS[fold]),mapping_preflight=gate,order='MODEL_FIRST_THEN_TWO_FIXED_CONTROLS_SEQUENTIAL',fits=0,model_inference=0,provider_downloads=0,completed_wallet_reruns=0,account_stitching=False,stop='ANY_SOURCE_CLOCK_CONTEXT_MAPPING_CAPACITY_ACCOUNT_FAILURE;600CPU_AND_WALL_SECONDS;6GB_AS;15GiB_RESERVE')
            (plans/(arm+'.json')).write_text(json.dumps(plan,indent=2)+'\n')
    cash=dict(status='ANALYTIC_NATIVE_CASH_ZERO_NO_WALLET',calendar=cal,capital_USDT=10000,net_PnL_USDT=0,fees_USDT=0,execution_cost_USDT=0,funding_USDT=0,drawdown=0,gross=0,net_exposure=0,proof='All63 CASH requests map to zero targets; fresh unheld positions, funding, fills and paid closure remain zero.',source_contract_SHA256=base.frozen.sha(path),engine_SHA256=contract['engine_sha256'],wallets_run=0)
    (plans/'CASH_ANALYTIC.json').write_text(json.dumps(cash,indent=2)+'\n')
    (plans/'PRECHECK.json').write_text(json.dumps(dict(status='PASS_ACTUAL_NATIVE63_INPUT_PREFIX_AND_MAPPER_PARITY_NO_WALLET',readiness=readiness,prefix_proof=proof,mapping=gates,analytic_cash=cash,fits=0,model_inference=0,wallets_run=0,provider_downloads=0),indent=2)+'\n')
    (public/'README.md').write_text('Frozen '+fold+' native evaluation. Three separate fresh10k accounts, original zero-external-quote startup, exact guard-OFF engine and full costs, paid terminal closure. No fit, inference, provider download or completed-wallet rerun. The original requests, model and scaler remain bound to public commit38b86686; real actual daily/funding contexts are reused. Original public raw bytes are exact. Derived Parquet hashes differ from the unpublished worker containers; every canonical value and published quote-volume hash passes. Original provider retrieval timestamps were not supplied, so remain UNKNOWN. Historical publication/account rules remain uncertified. This is project-seen history with unequal realized risk, not pristine unseen evidence.\n\nUse requirements-native61.txt plus the normalization versions in ADAPTER_CONTRACT.json. Recover via recover_prequential2023.py, create context via evaluate_transfer63.py context, bind via prepare_transfer63.py, and execute evaluate_transfer63.py run with the published request/contract/plan SHAs and public plan commit. State-relative market, wrapper and result locations preserve portable provenance; no private inventories or credentials are published.\n')
    print(json.dumps(dict(status='PASS_READY_FOR_PUBLIC_PLAN_PRESERVATION',fold=fold,arms=arms,contract_SHA256=base.frozen.sha(path),prefix_samples=proof['training_samples'],scaler_rows=proof['scaler_rows'],wallets_run=0)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--cache',type=Path,required=True);p.add_argument('--fold',choices=tuple(transfer.FOLDS),required=True);a=p.parse_args()
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','POLARS_MAX_THREADS'):os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6000000000,6000000000));resource.setrlimit(resource.RLIMIT_CPU,(600,600))
    def blocked(*a,**kw):raise RuntimeError('Offline frozen binding forbids network')
    socket.create_connection=blocked;socket.socket.connect=blocked;prepare(a.state,a.cache,a.fold)
