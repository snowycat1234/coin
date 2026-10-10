"""Four source-frozen prefix-static choices; original native engine, durable daily recovery.

No fitting, inference, provider access, choice changes, or completed-wallet reruns.
Checkpoint transport only separates numeric minute chunks from the original
engine's JSON snapshot; restoration uses its unchanged validated from_snapshot.
"""
import argparse,gzip,hashlib,json,os,resource,shutil,signal,socket,subprocess,time
from datetime import datetime,UTC
from pathlib import Path
import evaluate_requests63 as native
from package_prequential63 import write_once
base=native.base;HERE=base.HERE;REPO=base.frozen.REPO;PUBLIC=HERE/'prefix-static63'
read=base.frozen.read;sha=base.frozen.sha;require=base.frozen.require
EXPORT='57a90f59bb702eab8fe74803e7de765b350cab93'
CHOICE='49c0ff4b88286ccb7131af99e88838b4015dc5be'
SOURCE_REL='research/temporal-prefix-static-baseline-20261010'
SELECTION_SHA='c836e76c6f200688569275be55d724bf8ab3659c9dcf41f00d7cce98d64e5ba9'
FINANCIAL=HERE/'april63/ADAPTER_CONTRACT.json'
FINANCIAL_SHA='5163c9b4e0cf7305662b715b46d0dabd4e8de35fc8ee38728aff8ff74f9c9b77'
ENGINE_SHA='318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585'
FOLDS={
 'FOLD_20230703':('fe7ebc74ff3630902e0044629685427d29e6304507baae16d40ae4deca690016','prequential2023/FOLD_20230703',5,371),
 'FOLD_20231002':('f69d4e082dd74c2813fb53be4a93993dc46e578d2abb5dbc61184db031c1856e','prequential2023/FOLD_20231002',1,462),
 'FOLD_20240101':('c7c9e56007df82700c5019a39c3bd7462c9db8f3f166daeef19f8bf59ace941a','prequential63',1,553),
 'FOLD_20240401':('e45637155a0b46a4a101357926cc1cab397e4c9c0452c1a735e8a65b4996e599','april63',1,644)}
SCHEMA='SOURCE_HASHED_PREFIX_STATIC_NATIVE63_ADAPTER_V1'


def encoded(value):return (json.dumps(value,indent=2,allow_nan=False)+'\n').encode()
def record(path):return dict(bytes=path.stat().st_size,sha256=sha(path))
def arrays(path):
    import numpy as np
    with np.load(path,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}
def atomic(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.pending')
    with tmp.open('wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)
    fd=os.open(path.parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)


def old_paths(state,fold):
    if fold in ('FOLD_20230703','FOLD_20231002'):return state/'prequential2023-wrappers'/fold/'producer'
    if fold=='FOLD_20240101':return state/'prequential63-native-wrappers/producer'
    return state/'april63-export/b8299bc22321b9dadf707f14da83ac40a39b5491/research/temporal-april-transfer-20261009/forward/FOLD_20240401'


def contexts(contract_path):
    c=read(contract_path);p=contract_path.parent/'CANONICAL_CONTEXTS63.npz'
    require(record(p)==c['context_files'][p.name],'Original canonical context bytes differ')
    z=arrays(p);require(z['expert_order'].tolist()==list(base.E5+(base.SHORT,)) and z['symbol_order'].tolist()==list(base.frozen.SYMBOLS),'CORE5/E6 context identity differs')
    require(z['decision_us'].tolist()==list(range(c['calendar']['start'],c['calendar']['end_exclusive'],base.frozen.DAY)),'Context calendar differs')
    return {k:z[k] for k in ('expert_targets','expert_eligible','target_available_us','past_returns30')}|dict(expert_order=base.E5+(base.SHORT,))


def validate_choice(selection,fold,calendar):
    require(hashlib.sha256(encoded(selection)).hexdigest()==SELECTION_SHA,'Exact committed selection bytes required')
    without={k:v for k,v in selection.items() if k!='selection_identity'}
    identity=hashlib.sha256(json.dumps(without,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    require(identity==selection['selection_identity'] and selection['fits']==selection['forward_outcomes_read']==0,'Frozen prefix identity/zero-fit receipt differs')
    date=fold[5:9]+'-'+fold[9:11]+'-'+fold[11:13];choice=next(v for v in selection['folds'] if v['fold']==date)
    _,_,slot,count=FOLDS[fold]
    require(choice['E6_slot']==slot and choice['first_forward_decision_us']==calendar['start'] and choice['mature_labels']==count==sum(choice['labels_by_original_wallet'].values()),'Original choice/count/calendar differs')
    require(choice['latest_label_available_us']==calendar['start']-base.frozen.DAY+base.frozen.MINUTE+1<calendar['start'],'Strict mature prefix clock differs')
    candidates=selection['protocol']['candidates'];winner=max(range(len(candidates)),key=lambda i:choice['prefix_means'][candidates[i]])
    require(candidates==[base.E5[1],base.E5[4],base.SHORT] and candidates[winner]==choice['selected_expert']==(base.E5+(base.SHORT,))[slot],'Recorded fixed-order prefix argmax differs')
    return choice


def request_parity(a,c,choice,producer,paired,surrogate,calendar):
    import numpy as np
    m=dict(expert_order=list(base.E5+(base.SHORT,)),allowed_actions=list(base.COMPACT+(base.SHORT,)),uses_feedback_features=False)
    full,_=base.validate(m,a,c,calendar);slot=choice['E6_slot'];expected=np.zeros((63,6));expected[:,slot]=1
    require(set(a)=={'decision_us','symbol_order','expert_order','desired_expert_budget','action_eligible','feature_available_us','request_available_us'},'Original seven request arrays required')
    require(np.array_equal(full,expected) and np.array_equal(full,paired[choice['selected_control']+'_requests']),'All63 original one-hot requests, including terminal, required')
    for key in ('expert_targets','expert_eligible','target_available_us'):
        require(np.array_equal(producer[key][:,[0,1,4,5]],c[key][:,[0,1,4,5]]),'Admitted source context differs: '+key)
    require(np.array_equal(producer['past_returns30'],c['past_returns30']),'Original covariance source differs')
    clocks=base.clock(producer['expert_input_available_us'],(63,18),'original18 input clocks')
    require(np.array_equal(a['feature_available_us'],np.maximum(choice['latest_label_available_us'],clocks.max(1))) and np.array_equal(a['request_available_us'],a['decision_us']),'Original feature/request clocks differ')
    require(np.array_equal(a['action_eligible'],producer['expert_eligible']) and not a['action_eligible'][:,2:4].any(),'Source masks/unused E5 slots differ')
    require(np.array_equal(surrogate['decision_us'],a['decision_us']) and np.array_equal(surrogate['targets'],paired[choice['selected_control']+'_targets']) and np.array_equal(surrogate['mapped_expert_budget'],paired[choice['selected_control']+'_budget']) and np.array_equal(surrogate['nav'],paired[choice['selected_control']+'_nav']),'Original surrogate selected-control receipt differs')
    return full


def grid(state,contract_path):
    import numpy as np
    contract=read(contract_path);cal=contract['calendar'];work=base.member(state,contract['market_work_relative'])
    report=base.source_market_check(state,cal,contract_path,work);base.frozen.modules(state);window=base.market(state,cal,work);n=0
    for block in window['minute_blocks']():
        require(np.array_equal(block['times'],np.arange(cal['start']+n*base.frozen.MINUTE,cal['start']+(n+len(block['times']))*base.frozen.MINUTE,base.frozen.MINUTE)) and set(block['market'])==set(base.frozen.SYMBOLS),'Actual full synchronous trade/mark grid required')
        require(all(all(np.isfinite(v).all() for v in asset.values()) and (asset['quote_volume']>=0).all() and (asset['mark']>0).all() and (asset['open']>0).all() for asset in block['market'].values()),'Actual finite prices/quote volume required');n+=len(block['times'])
    require(n==90720 and len(window['events'])==945,'Exact63 tape/funding coverage differs')
    for symbol in base.frozen.SYMBOLS:
        events=[e for e in window['events'] if e['symbol']==symbol];tt=np.array([e['event_us'] for e in events],np.int64)
        require(len(events)==189 and np.array_equal((tt//1000000+1)//28800,np.arange(cal['start']//1000000//28800,cal['end_exclusive']//1000000//28800)) and all(e['reported_interval_hours']==8 and np.isfinite(e['raw_rate']) for e in events),'Actual189 signed funding slots/asset required; raw timestamps preserved')
    return report|dict(status='PASS_EXACT_RETAINED_TRADE_MARK_QUOTE_FUNDING63_GRID',provider_downloads=0,wallets_run=0)


def prepare(state):
    import numpy as np
    require(sha(FINANCIAL)==FINANCIAL_SHA,'Original declared financial contract differs');financial=read(FINANCIAL)
    require(financial['engine_sha256']==ENGINE_SHA,'Exact original guard-OFF engine required')
    source=state/'prefix-static-export'/EXPORT;selection_path=source/SOURCE_REL/'FROZEN_SELECTIONS.json'
    require(sha(selection_path)==SELECTION_SHA and selection_path.read_bytes()==(state/'prefix-static-choice-proof'/CHOICE/'FROZEN_SELECTIONS.json').read_bytes(),'Full pre-evaluation commit choice bytes required')
    write_once(PUBLIC/'FROZEN_SELECTIONS.json',selection_path.read_bytes());selection=read(selection_path);reports={}
    for fold,(manifest_sha,old_relative,slot,count) in FOLDS.items():
        folder=PUBLIC/fold;original=source/SOURCE_REL/fold;manifest=read(original/'MANIFEST.json');old_path=HERE/old_relative/'ADAPTER_CONTRACT.json';old=read(old_path);cal=old['calendar']
        require(sha(original/'MANIFEST.json')==manifest_sha and manifest['native_contract_SHA256']==FINANCIAL_SHA and manifest['model_parameters']==manifest['optimizer_updates']==0 and manifest['no_forward_selection'] is True and manifest['selection_SHA256']==SELECTION_SHA and manifest['selection_identity']==selection['selection_identity'] and manifest['producer_commit']==CHOICE[:7] and manifest['private_mapper_coordinates']==[0,1,2,4,5],'Original export/source/contract identity differs')
        require(old['financial_contract']==financial['financial_contract'] and old['cost']==financial['cost'] and old['engine_sha256']==ENGINE_SHA,'Existing fold financial semantics differ')
        for name,h in manifest['versioned_sources'].items():require(sha(source/name)==h,'Versioned published producer source differs: '+name)
        for name,r in manifest['files'].items():
            p=original/name;require(p.stat().st_size==r['bytes'] and sha(p)==r['SHA256'],'Exact original export member differs: '+name);write_once(folder/'export'/name,p.read_bytes())
        write_once(folder/'export/MANIFEST.json',(original/'MANIFEST.json').read_bytes())
        for name in ('baseline.py','evaluate.py'):write_once(folder/'source'/name,(source/'modules/temporal_prefix_static_baseline'/name).read_bytes())
        context=old_path.parent/'CANONICAL_CONTEXTS63.npz';write_once(folder/context.name,context.read_bytes())
        contract={k:financial[k] for k in ('engine_sha256','financial_contract','cost','limits','retained_preflight_sha256','fresh_start','original_E5_order','permitted_extension','dependency_recipe')}
        contract.update(schema='PREFIX_STATIC63_FINANCIAL_AND_EXPLICIT_CALENDAR_BINDING_V1',fold=fold,calendar=cal,declared_export_financial_reference=dict(path=FINANCIAL.relative_to(REPO).as_posix(),sha256=FINANCIAL_SHA,scope='FINANCIAL_SEMANTICS;APRIL_CALENDAR_NOT_USED_FOR_OTHER_FOLDS'),existing_fold_reference=dict(path=old_path.relative_to(REPO).as_posix(),sha256=sha(old_path)),market_work_relative=old.get('market_work_relative','h1_validation/original/h1_market'),market_artifacts=old.get('market_artifacts',read(state/'h1_validation/original/h1_market/reports/DATASET_MANIFEST.json')['artifacts']),context_files={context.name:record(context)},source_sha256=dict(financial['source_sha256']),historical_publication_and_exchange_account_rules_certified=False)
        for name in ('prefix_static_native63.py','durable_native_checkpoint.py'):contract['source_sha256'][str((HERE/name).relative_to(REPO))]=sha(HERE/name)
        write_once(folder/'ADAPTER_CONTRACT.json',encoded(contract));choice=validate_choice(selection,fold,cal);c=contexts(folder/'ADAPTER_CONTRACT.json')
        producer=old_paths(state,fold)
        for name,h in manifest['input_source_files'].items():require(sha(producer/Path(name).name)==h,'Retained original producer input differs: '+name)
        a=arrays(folder/'export/REQUESTS.npz');s=arrays(folder/'export/SURROGATE_PATH.npz');full=request_parity(a,c,choice,arrays(producer/'CURRENT_CONTEXT63.npz'),arrays(producer/'PAIRED_PATHS.npz'),s,cal)
        mapper=base.frozen.modules(state);fractions,budgets=base.mapped(full,c,mapper.mapper,cal)
        require(np.array_equal(fractions,s['targets']) and np.array_equal(budgets,s['mapped_expert_budget']),'Native mapper and original surrogate target/budget parity differ')
        np.testing.assert_allclose(budgets[:20,slot],np.arange(1,21)/20,rtol=0,atol=1e-14);np.testing.assert_allclose(budgets[20:,slot],1,rtol=0,atol=1e-14)
        planfile=folder/'FIXED_PREFIX_CHOICE.json';write_once(planfile,encoded(dict(policy_role='FIXED_CONTROL',choice=choice,choice_commit=CHOICE,export_commit=EXPORT,fits=0,model_parameters=0,no_forward_selection=True,calendar=cal)))
        files={p.relative_to(folder).as_posix():record(p) for p in sorted(folder.rglob('*')) if p.is_file()}
        wrapper=dict(schema=SCHEMA,arm_id='PREFIX_STATIC_'+fold,objective_version=2,prediction_role='HISTORICAL_FROZEN_REPLAY_NOT_LIVE_PREDICTIONS',policy_role='FIXED_CONTROL',model_sha256=None,scaler_sha256=None,training_plan_file=planfile.name,training_plan_sha256=sha(planfile),producer_commit=EXPORT,training_cutoff_us=cal['start'],maximum_training_label_available_us=choice['latest_label_available_us'],maximum_scaler_input_available_us=0,actual_fit_completed_UTC=None,actual_export_completed_UTC=datetime.now(UTC).isoformat(),source_files=['source/baseline.py','source/evaluate.py'],request_file='export/REQUESTS.npz',expert_order=list(base.E5+(base.SHORT,)),allowed_actions=list(base.COMPACT+(base.SHORT,)),uses_feedback_features=False,files=files,calendar=cal,adapter_contract_sha256=sha(folder/'ADAPTER_CONTRACT.json'))
        write_once(folder/'NATIVE_MANIFEST.json',encoded(wrapper));ready=grid(state,folder/'ADAPTER_CONTRACT.json')
        m,f,b,gate=check(state,fold);require(np.array_equal(f,fractions) and np.array_equal(b,budgets),'Bound native gate differs')
        report=dict(status='PASS_SOURCE_FROZEN_PREFIX_STATIC_NATIVE63_READY',fold=fold,choice=choice,export_commit=EXPORT,choice_commit=CHOICE,original_manifest_sha256=manifest_sha,selection_sha256=SELECTION_SHA,producer_sources_verified=len(manifest['versioned_sources']),retained_input_sources_verified=len(manifest['input_source_files']),selection_scope='COMMITTED_PREFIX_ONLY_SELECTION_RECEIPT;RECORDED_MEANS_AND_MATURITY_VERIFIED;LABEL_MEANS_NOT_RECOMPUTED',mapping=gate,grid=ready,terminal_request_onehot_unchanged=True,terminal_execution_target_zero=True,source_surrogate_result=read(folder/'export/RESULT.json')['net_PnL'],wallets_run=0,fits=0,model_inference=0,provider_downloads=0)
        write_once(folder/'PRECHECK.json',encoded(report))
        plan=dict(authorization='USER_AUTHORIZED_EXACTLY_FOUR_PREFIX_STATIC_NATIVE63_WALLETS',fold=fold,arm_id=m['arm_id'],calendar=cal,choice_commit=CHOICE,export_commit=EXPORT,request_manifest_sha256=sha(folder/'NATIVE_MANIFEST.json'),request_payload_sha256=gate['request_payload_sha256'],adapter_contract_sha256=sha(folder/'ADAPTER_CONTRACT.json'),engine_sha256=ENGINE_SHA,mapping_preflight=gate,resource_limits=contract['limits'],resume='BOUND_ORIGINAL_ENGINE_DAILY_SNAPSHOT;NO_COMPLETED_WALLET_RERUN',terminal_request='ORIGINAL_ONEHOT_UNCHANGED;ORIGINAL_ENGINE_FINAL_DAY_TARGET_ZERO_PAID_CLOSE',controls='REUSE_TWELVE_COMPLETED_FRESH_GRU_STATIC50_CASH50_ACCOUNTS',stop='IDENTITY_OR_AUDIT_OR_CAP_OR_TERMINAL_FAILURE;NO_RESELECTION;NO_REPAIR_BY_TUNING',new_wallets=1,fits=0,model_inference=0,provider_downloads=0)
        write_once(folder/'EXECUTION_PLAN.json',encoded(plan));reports[fold]=report
    write_once(PUBLIC/'READINESS.json',encoded(dict(status='PASS_ALL_FOUR_SOURCE_FROZEN_BASELINE_REQUESTS',folds=reports,new_wallets=0,completed_wallet_reruns=0)))
    return {fold:dict(status=r['status'],selected_expert=r['choice']['selected_expert'],target_parity_exact=True,plan_sha256=sha(PUBLIC/fold/'EXECUTION_PLAN.json')) for fold,r in reports.items()}


def check(state,fold):
    folder=PUBLIC/fold;contract_path=folder/'ADAPTER_CONTRACT.json';contract=read(contract_path);cal=contract['calendar'];m,a=base.load_bundle(folder/'NATIVE_MANIFEST.json',sha(folder/'NATIVE_MANIFEST.json'),cal,SCHEMA)
    require(m['adapter_contract_sha256']==sha(contract_path),'Explicit calendar/financial binding differs');c=contexts(contract_path);choice=validate_choice(read(PUBLIC/'FROZEN_SELECTIONS.json'),fold,cal)
    producer=old_paths(state,fold);s=arrays(folder/'export/SURROGATE_PATH.npz');full=request_parity(a,c,choice,arrays(producer/'CURRENT_CONTEXT63.npz'),arrays(producer/'PAIRED_PATHS.npz'),s,cal)
    mapper=base.frozen.modules(state);fractions,budgets=base.mapped(full,c,mapper.mapper,cal)
    import numpy as np
    require(np.array_equal(fractions,s['targets']) and np.array_equal(budgets,s['mapped_expert_budget']),'Exact native/surrogate mapping required')
    gate=dict(status='PASS_SOURCE_BOUND_ORIGINAL_REQUEST_MASK_CLOCK_SLOT_AND_TARGET_BUDGET_PARITY',manifest_sha256=sha(folder/'NATIVE_MANIFEST.json'),request_payload_sha256=sha(folder/'export/REQUESTS.npz'),fractions_f64_sha256=hashlib.sha256(fractions.tobytes()).hexdigest(),budgets_f64_sha256=hashlib.sha256(budgets.tobytes()).hexdigest(),arm_id=m['arm_id'],fits=0,wallets_run=0)
    return m,fractions,budgets,gate


def run(state,fold,commit):
    import numpy as np
    import durable_native_checkpoint as durable
    folder=PUBLIC/fold;planpath=folder/'EXECUTION_PLAN.json';plan=read(planpath);contract_path=folder/'ADAPTER_CONTRACT.json';contract=read(contract_path);cal=contract['calendar'];work=base.member(state,contract['market_work_relative'])
    require(len(commit)==40 and subprocess.check_output(['git','show',commit+':'+planpath.relative_to(REPO).as_posix()],cwd=REPO)==planpath.read_bytes(),'Public request-specific plan required')
    require(plan['authorization']=='USER_AUTHORIZED_EXACTLY_FOUR_PREFIX_STATIC_NATIVE63_WALLETS' and plan['request_manifest_sha256']==sha(folder/'NATIVE_MANIFEST.json') and plan['adapter_contract_sha256']==sha(contract_path),'Exact authorized baseline request binding required')
    base.source_market_check(state,cal,contract_path,work);m,fractions,budgets,gate=check(state,fold);require(gate==plan['mapping_preflight'],'Precommitted mapper identity differs')
    from scripts.investment import perpetual_directional as old
    output=state/'prefix-static63-native'/fold;ledger=state/'prefix-static-native-ledger'/gate['manifest_sha256'];binding=dict(fold=fold,plan_commit=commit,plan_sha256=sha(planpath),request_manifest_sha256=gate['manifest_sha256'],request_payload_sha256=gate['request_payload_sha256'],adapter_contract_sha256=sha(contract_path),engine_sha256=ENGINE_SHA)
    if output.exists():
        require(ledger.exists() and read(output/'BINDING.json')==binding and read(ledger)['binding']==binding,'Only the reserved original account can resume')
        require(read(ledger)['status'] in ('RUNNING','INTERRUPTED_RESUMABLE','COMPLETE_CONDITIONAL_ACCOUNT'),'Audited or financially failed account cannot rerun')
        sim,pointer=durable.restore(output/'recovery',binding,base.market(state,cal,work));started=read(output/'STARTED.json');elapsed_prior=pointer['elapsed_seconds'];completed=pointer['completed_days'];print(json.dumps(dict(status='RESUMED_ORIGINAL_DURABLE_ACCOUNT',fold=fold,completed_days=completed)),flush=True)
    else:
        ledger.parent.mkdir(parents=True,exist_ok=True)
        with ledger.open('x') as f:f.write(json.dumps(dict(status='RUNNING',binding=binding))+'\n');f.flush();os.fsync(f.fileno())
        output.mkdir(parents=True,exist_ok=False);write_once(output/'BINDING.json',encoded(binding));sim=base.simulator(state,contract,cal,work);sim.budget=[1.]+[0.]*5
        started=dict(policy=m['arm_id'],request_manifest_sha256=gate['manifest_sha256'],request_payload_sha256=gate['request_payload_sha256'],plan_commit=commit,started_UTC=datetime.now(UTC).isoformat(),limits=contract['limits'],export_provenance=m)
        write_once(output/'STARTED.json',encoded(started));write_once(output/'REQUEST_GATE.json',encoded(gate));elapsed_prior=0.;completed=0;durable.save(output/'recovery',sim,binding,0.)
    status='RUNNING';error=None;start=time.monotonic()
    def interrupt(*args):raise KeyboardInterrupt('External interruption: resume durable original account')
    def timeout(*args):raise TimeoutError('600-second cumulative native baseline account cap')
    signal.signal(signal.SIGTERM,interrupt);signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,max(.001,600-elapsed_prior))
    try:
        for i in range(completed,63):
            require(shutil.disk_usage(output).free>=15*2**30,'15GiB reserve required');sim.budget=budgets[i].tolist()
            require(sim.advance_day(dict(zip(base.frozen.SYMBOLS,fractions[i],strict=True)))['completed'],'Incomplete financial account must stop')
            durable.save(output/'recovery',sim,binding,elapsed_prior+time.monotonic()-start)
            if (i+1)%10==0 or i==62:print(json.dumps(dict(fold=fold,completed_days=i+1,total_days=63,NAV=float(sim.account.nav()))),flush=True)
        require(sim.rows_written==90720 and all(p.quantity==0 for p in sim.account.positions.values()) and not fractions[-1].any(),'Full63 original paid terminal flat required');status='COMPLETE_CONDITIONAL_ACCOUNT'
    except KeyboardInterrupt as ex:status='INTERRUPTED_RESUMABLE';error=dict(type=type(ex).__name__,message=str(ex));raise
    except BaseException as ex:status='FAILED_STOP_PREFIX_RETAINED';error=dict(type=type(ex).__name__,message=str(ex));raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        receipt=started|dict(status=status,error=error,finished_UTC=datetime.now(UTC).isoformat(),elapsed_seconds=elapsed_prior+time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,completed_minutes=sim.rows_written,original_engine_sha256=ENGINE_SHA,resumed_from_days=completed,audit='PENDING_INDEPENDENT_POST_RUN_RECONCILIATION')
        atomic(output/'EXECUTION.json',encoded(receipt));atomic(ledger,encoded(dict(status=status,binding=binding)))
    if (output/'account/summary.json').exists():
        saved=dict(summary=read(output/'account/summary.json'))
    else:
        temporary=output/('account_save_'+str(time.time_ns()))
        saved=old.save_case(sim.result(),temporary);write_once(temporary/'summary.json',encoded(saved['summary']))
        require(not (output/'account').exists(),'Partial account publication must remain separately preserved')
        os.replace(temporary,output/'account')
    from pyarrow.parquet import read_table
    actual=read_table(output/'account/targets.parquet')['target_weight'].to_numpy().reshape(63,5);require(np.array_equal(actual,fractions),'Saved mapped daily targets differ')
    audit=base.audit(output,state,cal,work);audit.update(mapped_request_targets_exact=True,terminal_request_onehot_preserved=True,terminal_execution_forced_zero=True)
    require(audit['actual_input_check']['funding_events']==945 and audit['terminal_paid_flat'],'Independent actual-input financial audit required')
    restored,pointer=durable.restore(output/'recovery',binding,base.market(state,cal,work));require(restored.state_hash()==sim.state_hash() and restored.account.snapshot()==sim.account.snapshot() and np.array_equal(np.concatenate(restored.minute_chunks),np.concatenate(sim.minute_chunks)),'Final full account and numeric journal recovery differs')
    write_once(output/'INDEPENDENT_AUDIT.json',encoded(audit));write_once(output/'RECOVERY_AUDIT.json',encoded(dict(status='PASS_ORIGINAL_ENGINE_FINAL_SNAPSHOT_RESTORE',state_hash=sim.state_hash(),completed_minutes=sim.rows_written,account_snapshot_exact=True,minute_journal_bit_exact=True,paid_flat=True,checkpoint_pointer_sha256=sha(output/'recovery/CHECKPOINT.json'),wallet_advanced_after_restore=False)))
    atomic(ledger,encoded(dict(status='COMPLETE_AND_AUDITED',binding=binding)));print(json.dumps(dict(status='COMPLETE_AND_AUDITED',fold=fold,net_PnL=saved['summary']['net_PnL'],checkpoint_days=pointer['completed_days'])),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('prepare','check','run'));p.add_argument('--state',type=Path,required=True);p.add_argument('--fold',choices=tuple(FOLDS));p.add_argument('--plan-commit');a=p.parse_args()
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','POLARS_MAX_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6000000000,6000000000));resource.setrlimit(resource.RLIMIT_CPU,(600,600))
    def blocked(*args,**kwargs):raise RuntimeError('Offline baseline native runner forbids network')
    socket.create_connection=blocked;socket.socket.connect=blocked
    if a.command=='prepare':print(json.dumps(prepare(a.state)),flush=True)
    elif a.command=='check':print(json.dumps(check(a.state,a.fold)[3]),flush=True)
    else:
        require(a.fold is not None and a.plan_commit is not None,'Explicit frozen fold and published plan commit required')
        import fcntl
        locks=a.state/'prefix-static63-locks';locks.mkdir(exist_ok=True)
        with (locks/a.fold).open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);run(a.state,a.fold,a.plan_commit)


if __name__=='__main__':main()
