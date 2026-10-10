"""One frozen expanded-history Q4 account, reusing the unchanged native92 kernel.

Only request/authorization binding differs. The original window, mapper,
financial engine, daily checkpoint/restore and independent auditors are reused.
No training, inference, provider data, risk-policy change or comparator rerun.
"""
import argparse,concurrent.futures,fcntl,gzip,hashlib,json,os,re,resource,shutil,signal,socket,subprocess,sys,time,urllib.request,zipfile
from datetime import datetime,UTC
from pathlib import Path
import numpy as np
import q4_native92 as q4
import finalize_q4_native92 as audit92
from package_q4_native92 import months
import native_margin_risk_summary as margin
HERE=q4.HERE;REPO=q4.REPO;PUBLIC=HERE/'expanded-q4-native92'
ARM='EXPANDED1137_FIXED907_FRESH256'
PRODUCER='0e5f41c255f315dccdd922de9a4ce762a1f40771'
PRODUCER_REL='research/temporal-expanded-refit-q4-20261010'
COMPARATORS='eb89009c2a4dfcb2666a6d9419cc56c7067e1b94'
HANDOFF_SHA='606fec3accf5f9195ae808569eca634af08b105ff1b1b938a79f91dabb7c91a1'
RESULT_MANIFEST_SHA='8ee9e228630a80b5324f4f8bedd327525054fe6c98504ed9881222922174049f'
AUTHORIZATION='USER_AUTHORIZED_EXACTLY_ONE_EXPANDED1137_FROZEN_Q4_NATIVE92_WALLET'
read=q4.read;sha=q4.sha;record=q4.record;encoded=q4.encoded;write_once=q4.write_once;atomic=q4.atomic;need=q4.require;arrays=q4.arrays
MEMBERS={'MANIFEST.json':'q4-results/native-handoff/MANIFEST.json','REQUESTS.npz':'q4-results/native-handoff/REQUESTS.npz','EXPANDED_PATH.npz':'q4-results/EXPANDED_PATH.npz','RESULT.json':'q4-results/RESULT.json','RESULT_MANIFEST.json':'q4-results/MANIFEST.json','INPUT_BINDING.json':'q4-results/INPUT_BINDING.json','INPUT_RECEIPT.json':'q4-results/INPUT_RECEIPT.json','VERIFICATION.json':'q4-results/VERIFICATION.json','PROTOCOL.json':'PROTOCOL.json','RUN.json':'frozen/RUN.json','TERMINAL.json':'frozen/TERMINAL.json','SCALER.json':'frozen/SCALER.json','SCALER.npz':'frozen/SCALER.npz','INITIAL.json':'prefit-safe/INITIAL.json','FROZEN_PUBLIC_READBACK.json':'FROZEN_PUBLIC_READBACK.json'}


def original_comparators(verify_git=False):
    result={}
    for arm in q4.ARMS:
        folder=q4.PUBLIC/'results'/arm;files={}
        for name in ('RESULT.json','summary.json','INDEPENDENT_AUDIT.json','RECOVERY_AUDIT.json','PUBLIC_READBACK.json'):
            p=folder/name
            if verify_git:
                raw=subprocess.check_output(['git','show',COMPARATORS+':'+p.relative_to(REPO).as_posix()],cwd=REPO);need(raw==p.read_bytes(),'Preserved comparator differs: '+arm+'/'+name)
            files[name]=record(p)
        r=read(folder/'RESULT.json');need(r['engine_SHA256']==q4.ENGINE_SHA and r['execution_calendar']==q4.EXECUTION_CAL and r['full_original_snapshot_recovery']['account_snapshot_exact'],'Comparator contract differs')
        result[arm]=dict(commit=COMPARATORS,files=files,result=r,rerun=False)
    return result


def request_gate(m,a,path,c,source,mapper):
    need(m['symbol_order']==list(q4.base.frozen.SYMBOLS) and m['expert_order']==list(q4.base.E5+(q4.base.SHORT,)),'Exact CORE5/E6 handoff order required')
    full,report=q4.base.validate(dict(expert_order=m['expert_order'],allowed_actions=list(q4.base.COMPACT+(q4.base.SHORT,)),uses_feedback_features=False),a,c,q4.REQUEST_CAL)
    need(np.array_equal(a['decision_us'],path['decision_us']) and np.array_equal(full,path['request']),'All92 original expanded requests required')
    need(np.array_equal(a['feature_available_us'],source['input_available_us'].max(1)) and np.array_equal(a['request_available_us'],a['decision_us']),'Exact source feature/request clocks required')
    need(np.array_equal(a['action_eligible'],source['expert_eligible']) and not a['action_eligible'][:,2:4].any(),'Exact original mask/excluded E5 slots required')
    fractions,budgets=q4.base.mapped(full,c,mapper.mapper,q4.REQUEST_CAL)
    need(np.array_equal(fractions,path['targets']) and np.array_equal(budgets,path['budget']),'Original mapper/source target and budget parity required')
    need(not fractions[-1].any() and np.array_equal(full[-1],path['request'][-1]),'Preserve terminal request and original zero execution target')
    return fractions,budgets,report|dict(status='PASS_EXPANDED92_SOURCE_REQUEST_CLOCK_MASK_SLOT_AND_BIT_EXACT_MAPPING',arm=ARM,request_sha256=sha(PUBLIC/'producer/REQUESTS.npz'),handoff_manifest_sha256=HANDOFF_SHA,fractions_f64_sha256=hashlib.sha256(fractions.tobytes()).hexdigest(),budgets_f64_sha256=hashlib.sha256(budgets.tobytes()).hexdigest(),terminal_request_preserved=True,terminal_execution_target_zero=True,fits=0,model_inference=0,wallets_run=0)


def check(state):
    source=arrays(q4.PUBLIC/'producer/CURRENT_EXPERT_INPUTS92.npz')
    return request_gate(read(PUBLIC/'producer/MANIFEST.json'),arrays(PUBLIC/'producer/REQUESTS.npz'),arrays(PUBLIC/'producer/EXPANDED_PATH.npz'),q4.contexts(),source,q4.base.frozen.modules(state))


def source_check(state):
    q4.source_check(state);c=read(PUBLIC/'ADAPTER_CONTRACT.json')
    need(c['original_native92_contract_SHA256']==sha(q4.PUBLIC/'ADAPTER_CONTRACT.json') and c['execution_calendar']==q4.EXECUTION_CAL and c['terminal']==q4.terminal_contract(),'Unchanged original Q4 contract required')
    for name,h in c['source_SHA256'].items():need(sha(REPO/name)==h,'Frozen adapter or original source differs: '+name)
    for name,r in c['producer_files'].items():need(record(PUBLIC/'producer'/name)==r,'Exact expanded producer member differs: '+name)
    need(sha(PUBLIC/'producer/MANIFEST.json')==HANDOFF_SHA and sha(PUBLIC/'producer/RESULT_MANIFEST.json')==RESULT_MANIFEST_SHA,'Exact public expanded handoff required')
    m=read(PUBLIC/'producer/MANIFEST.json');need(m['current_context_SHA256']==sha(q4.PUBLIC/'producer/CURRENT_CONTEXT.npz') and m['economic_source']['source_commit']==q4.DATA and m['economic_source']['consumer_SHA256']==q4.CONSUMER_SHA,'Same cached original Q4 context/data required')
    for name in ('SCALER.json','SCALER.npz'):need((PUBLIC/'producer'/name).read_bytes()==(q4.PUBLIC/'producer'/name).read_bytes(),'Original907-row scaler changed')
    need(sha(PUBLIC/'COMPARATORS.json')==c['comparator_manifest_SHA256'] and read(PUBLIC/'COMPARATORS.json')==original_comparators(),'Original four saved comparator bindings differ')
    return c


def prepare(state):
    q4.source_check(state);root=state/'q4-expanded-public'/PRODUCER;producer=root/PRODUCER_REL;m=read(producer/'q4-results/native-handoff/MANIFEST.json')
    need(sha(producer/'q4-results/native-handoff/MANIFEST.json')==HANDOFF_SHA and m['schema']=='SOURCE_BOUND_EXPANDED1137_FIXED907_FRESH256_Q4_NATIVE92_V1' and m['decisions']==92 and m['active_intervals']==91 and m['terminal_execution_us']==q4.LAST+q4.base.frozen.MINUTE+1,'Exact expanded native92 handoff required')
    for n,h in m['source_files'].items():need(sha(root/'source'/n)==h,'Published expanded producer source differs: '+n)
    for name,path in MEMBERS.items():write_once(PUBLIC/'producer'/name,(producer/path).read_bytes())
    p=PUBLIC/'producer';rm=read(p/'RESULT_MANIFEST.json');need(sha(p/'RESULT_MANIFEST.json')==RESULT_MANIFEST_SHA,'Original expanded result manifest differs')
    for name,v in m['files'].items():need(record(p/name)==dict(bytes=v['bytes'],sha256=v['SHA256']),'Original handoff payload differs')
    for name in ('EXPANDED_PATH.npz','RESULT.json','INPUT_BINDING.json','INPUT_RECEIPT.json'):need(record(p/name)==dict(bytes=rm['files'][name]['bytes'],sha256=rm['files'][name]['SHA256']),'Original frozen once-score member differs')
    need(rm['source_files']==m['source_files'],'Original expanded source sets differ')
    protocol=read(p/'PROTOCOL.json');terminal=read(p/'TERMINAL.json');run=read(p/'RUN.json');initial=read(p/'INITIAL.json');score=read(p/'RESULT.json');scaler=read(p/'SCALER.json');binding=read(p/'INPUT_BINDING.json');verification=read(p/'VERIFICATION.json')
    need(protocol==m['protocol'] and protocol['parameters']==terminal['parameters']==13699 and protocol['active_training_intervals']==1137 and protocol['training_decisions']==1143 and protocol['updates']==terminal['completed_updates']==terminal['fixed_target']==256,'Frozen expanded size/update receipt differs')
    spec=run['specification'];oldspec=read(q4.PUBLIC/'producer/RUN.json')['specification'];need(spec['model_contract']==oldspec['model_contract'] and spec['optimizer']==oldspec['optimizer'] and spec['optimizer']['lr']==.0003,'Same architecture/optimizer/lr required')
    need(spec['algorithm']['parent']==dict(fresh=True,step=0) and len(spec['algorithm']['parameter_birth_steps'])==13 and all(v==0 for v in spec['algorithm']['parameter_birth_steps'].values()) and initial['step']==0 and initial['run_id']==run['run_id']==m['run_id'] and terminal['status']=='FIXED256_COMPLETE' and terminal['failure'] is None and terminal['Q4_scores']==0,'Fresh completed freeze-before-Q4 receipts required')
    need(all(v==256 for v in terminal['optimizer_parameter_ages'].values()) and terminal['checkpoint_SHA256']==score['checkpoint_SHA256']==m['checkpoint_SHA256']==binding['checkpoint_SHA256'] and terminal['model_identity']==score['model_identity']==m['model_identity'],'Frozen expanded model identity differs')
    need(scaler['identity']==m['scaler_identity']==terminal['scaler_identity'] and scaler['provenance']['real_row_count']==terminal['scaler_rows']==907 and scaler['provenance']['training_cutoff_us']<q4.START and not terminal['normalization_refitted'] and not score['normalization_refitted'],'Unchanged causal907-row scaler required')
    need(score['model_Adam_all_RNG_unchanged'] and score['new_model_scores']==1 and score['new_native_wallets']==0 and score['old_model_and_three_controls_reused'] and score['no_checkpoint_selection'] and verification['native_requests']==92 and verification['model_inferences']==verification['optimizer_updates']==verification['wallet_rollouts']==0,'Only saved frozen requests/once-score receipts may be used')
    write_once(PUBLIC/'COMPARATORS.json',encoded(original_comparators(verify_git=True)));original=read(q4.PUBLIC/'ADAPTER_CONTRACT.json');sources=dict(original['source_sha256'])
    for n in ('expanded_q4_native92.py','finalize_q4_native92.py','package_q4_native92.py','native_margin_risk_summary.py','requirements-native61.txt','requirements.txt'):sources[(HERE/n).relative_to(REPO).as_posix()]=sha(HERE/n)
    contract=dict(schema='ONE_EXPANDED1137_ORIGINAL_NATIVE92_BINDING_V1',producer_commit=PRODUCER,data_commit=q4.DATA,original_native92_contract_path=(q4.PUBLIC/'ADAPTER_CONTRACT.json').relative_to(REPO).as_posix(),original_native92_contract_SHA256=sha(q4.PUBLIC/'ADAPTER_CONTRACT.json'),execution_calendar=q4.EXECUTION_CAL,request_calendar=q4.REQUEST_CAL,terminal=q4.terminal_contract(),financial_contract=original['financial_contract'],cost=original['cost'],limits=original['limits'],source_SHA256=sources,producer_files={n:record(p/n) for n in MEMBERS},producer_source_files_verified=len(m['source_files']),producer_source_verification_commit=PRODUCER,producer_sources=m['source_files'],scaler_bytes_identical=True,model_tensors_loaded=False,comparator_commit=COMPARATORS,comparator_manifest_SHA256=sha(PUBLIC/'COMPARATORS.json'),feature_source_scope='Original unchanged context and source-bound handoff clocks; native execution consumes requests only, never model feature tensors or weights')
    write_once(PUBLIC/'ADAPTER_CONTRACT.json',encoded(contract));source_check(state);fractions,budgets,gate=check(state);win=q4.window(state);n=0
    for block in win['minute_blocks']():
        need(np.array_equal(block['times'],np.arange(q4.START+n*q4.base.frozen.MINUTE,q4.START+(n+len(block['times']))*q4.base.frozen.MINUTE,q4.base.frozen.MINUTE)),'Same complete cached native grid required');n+=len(block['times'])
    need(n==131046 and len(win['events'])==1370,'Same131046-minute/1370-funding domain required')
    plan=dict(authorization=AUTHORIZATION,arm=ARM,new_wallets=1,producer_commit=PRODUCER,data_commit=q4.DATA,adapter_contract_sha256=sha(PUBLIC/'ADAPTER_CONTRACT.json'),engine_sha256=q4.ENGINE_SHA,mapping_preflight=gate,execution_calendar=q4.EXECUTION_CAL,terminal=q4.terminal_contract(),resource_limits=original['limits'],comparator_commit=COMPARATORS,controls='REUSE_ALL_FOUR_ORIGINAL_COMPLETED_NATIVE_Q4_ACCOUNTS_WITHOUT_RERUN',account_start='FRESH10000;PREVIOUS_QUOTE_NONE;INITIAL_CAPACITY_ZERO;NO_CARRIED_POSITION',resume='UNCHANGED_NATIVE92_SAVE_CHECKPOINT_AND_RESTORE;COMPLETED_ACCOUNT_MUST_NOT_ADVANCE',stop='ANY_IDENTITY_GRID_FINANCIAL_TERMINAL_OR_AUDIT_FAILURE;NO_TUNING_OR_FORCED_FILL',classification=m['classification'],fits=0,model_inference=0,provider_downloads=0,policy_changes=0)
    write_once(PUBLIC/'EXECUTION_PLAN.json',encoded(plan));ready=dict(status='PASS_ONE_EXPANDED1137_NATIVE92_READY',producer_commit=PRODUCER,engine_SHA256=q4.ENGINE_SHA,handoff_SHA256=HANDOFF_SHA,request_SHA256=gate['request_sha256'],producer_sources_verified=len(m['source_files']),model_identity=m['model_identity'],checkpoint_SHA256=m['checkpoint_SHA256'],scaler_identity=m['scaler_identity'],scaler_bytes_identical=True,original_native92_methods_reused=['window','contexts','base.validate','base.mapped','save_checkpoint','restore','finalize_q4_native92.verify'],mapped_targets_and_budgets_bit_exact=True,calendar=q4.EXECUTION_CAL,terminal=q4.terminal_contract(),gate=gate,new_wallets=0,fits=0,model_inference=0,provider_downloads=0,blockers=[])
    write_once(PUBLIC/'PRECHECK.json',encoded(ready));print(json.dumps({k:v for k,v in ready.items() if k not in ('gate','terminal','calendar')}),flush=True)


def account(state):return state/'expanded-q4-native92'/ARM
def ledger(state,gate):return state/'expanded-q4-native92-ledger'/gate['request_sha256']
def finish(state):
    import polars as pl
    source_check(state);fractions,budgets,gate=check(state);root=account(state);binding=read(root/'BINDING.json');plan=read(PUBLIC/'EXECUTION_PLAN.json');e=read(root/'EXECUTION.json')
    need(e['status']=='COMPLETE_CONDITIONAL_ACCOUNT' and binding['plan_sha256']==sha(PUBLIC/'EXECUTION_PLAN.json') and plan['mapping_preflight']==gate and read(root/'REQUEST_GATE.json')==gate,'Only the exact completed bound account may finish')
    audit=audit92.verify(root,state);write_once(root/'INDEPENDENT_AUDIT.json',encoded(audit));sim,pointer=q4.restore(root/'recovery',binding,q4.window(state));minute=pl.read_parquet(root/'account/minute_nav_inventory.parquet');summary=read(root/'account/summary.json')
    need(pointer['completed_decisions']==92 and np.array_equal(minute.drop('close_us').to_numpy(),np.concatenate(sim.minute_chunks)) and np.array_equal(pl.read_parquet(root/'account/targets.parquet')['target_weight'].to_numpy().reshape(92,5),fractions),'Exact original numeric snapshot and target journal required')
    need(sim.account.trades==read(root/'account/trades.json') and sim.funding_journal==read(root/'account/funding.json') and abs(float(sim.account.nav())-summary['NAV'])<1e-8 and all(p.quantity==0 for p in sim.account.positions.values()),'Original full journal restoration and paid final flat required')
    recovery=dict(status='PASS_ORIGINAL92_PARTIAL_TERMINAL_FULL_SNAPSHOT_RECOVERY',state_hash=sim.state_hash(),completed_decisions=92,completed_minutes=131046,account_snapshot_exact=True,minute_journal_bit_exact=True,wallet_advanced_after_restore=False,terminal_paid_flat=True);write_once(root/'RECOVERY_AUDIT.json',encoded(recovery));atomic(ledger(state,gate),encoded(dict(status='COMPLETE_AND_AUDITED',binding=binding)))
    print(json.dumps(dict(status='COMPLETE_AND_AUDITED_NO_REPLAY',arm=ARM,net_PnL=summary['net_PnL'],minute_max_drawdown=summary['minute_max_drawdown'],terminal=audit['terminal'])),flush=True)


def execute(state,commit):
    from scripts.investment import perpetual_directional as old
    from scripts.investment.resumable_perpetual import NativeDailySimulator
    from quant.bybit_isolated_account import BybitIsolatedAccount
    contract=source_check(state);fractions,budgets,gate=check(state);planpath=PUBLIC/'EXECUTION_PLAN.json';plan=read(planpath)
    need(len(commit)==40 and subprocess.check_output(['git','show',commit+':'+planpath.relative_to(REPO).as_posix()],cwd=REPO)==planpath.read_bytes() and plan['authorization']==AUTHORIZATION and plan['new_wallets']==1 and plan['mapping_preflight']==gate and plan['adapter_contract_sha256']==sha(PUBLIC/'ADAPTER_CONTRACT.json'),'Published exact one-account plan required')
    root=account(state);book=ledger(state,gate);binding=dict(arm=ARM,producer_commit=PRODUCER,plan_commit=commit,plan_sha256=sha(planpath),adapter_contract_sha256=sha(PUBLIC/'ADAPTER_CONTRACT.json'),request_sha256=gate['request_sha256'],engine_sha256=q4.ENGINE_SHA,execution_calendar=q4.EXECUTION_CAL)
    if root.exists():
        need(read(root/'BINDING.json')==binding and read(book)['binding']==binding and read(book)['status'] in ('RUNNING','INTERRUPTED_RESUMABLE'),'Only exact uncompleted reserved account may resume')
        sim,pointer=q4.restore(root/'recovery',binding,q4.window(state));prior=pointer['elapsed_seconds'];count=pointer['completed_decisions'];started=read(root/'STARTED.json');print(json.dumps(dict(status='RESUMED_EXACT_ORIGINAL_ACCOUNT',completed_decisions=count)),flush=True)
    else:
        need(not (state/'q4-native92-ledger'/gate['request_sha256']).exists(),'Request already reserved in original account ledger')
        book.parent.mkdir(parents=True,exist_ok=True)
        with book.open('x') as f:f.write(json.dumps(dict(status='RUNNING',binding=binding))+'\n');f.flush();os.fsync(f.fileno())
        root.mkdir(parents=True,exist_ok=False);write_once(root/'BINDING.json',encoded(binding));sim=NativeDailySimulator(q4.window(state),'LONG_SHORT',old.COSTS[0],dict(id='RAW_AS_FRACTION',scale=1.),account_factory=BybitIsolatedAccount,persist_cash_close=True,final_day_target_zero=True)
        need(float(sim.account.nav())==10000 and sim.previous_quote is None and all(p.quantity==0 for p in sim.account.positions.values()) and old.COSTS[0]==contract['cost'],'Original fresh cash/start/cost required');sim.budget=[1.]+[0.]*5;prior=0.;count=0
        started=dict(arm=ARM,started_UTC=datetime.now(UTC).isoformat(),plan_commit=commit,limits=contract['limits'],request_sha256=gate['request_sha256'],producer_commit=PRODUCER,data_commit=q4.DATA);write_once(root/'STARTED.json',encoded(started));write_once(root/'REQUEST_GATE.json',encoded(gate));q4.save_checkpoint(root/'recovery',sim,binding,0.)
    status='RUNNING';error=None;start=time.monotonic()
    def interrupted(*args):raise KeyboardInterrupt('Resume original durable account')
    def expired(*args):raise TimeoutError('600-second cumulative native Q4 cap')
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,max(.001,600-prior))
    try:
        for i in range(count,92):
            need(shutil.disk_usage(root).free>=15*2**30,'15GiB reserve required');sim.budget=budgets[i].tolist();need(sim.advance_day(dict(zip(q4.base.frozen.SYMBOLS,fractions[i],strict=True)))['completed'],'Financial failure must stop');q4.save_checkpoint(root/'recovery',sim,binding,prior+time.monotonic()-start)
            if (i+1)%10==0 or i==91:print(json.dumps(dict(arm=ARM,completed_decisions=i+1,total_decisions=92,NAV=float(sim.account.nav()))),flush=True)
        need(sim.rows_written==131046 and all(p.quantity==0 for p in sim.account.positions.values()),'Original five-attempt terminal must achieve paid flat; no extra day or forced fill');status='COMPLETE_CONDITIONAL_ACCOUNT'
    except KeyboardInterrupt as ex:status='INTERRUPTED_RESUMABLE';error=dict(type=type(ex).__name__,message=str(ex));raise
    except BaseException as ex:status='FAILED_STOP_PREFIX_RETAINED';error=dict(type=type(ex).__name__,message=str(ex));atomic(root/'FAILED_ORIGINAL_SNAPSHOT.json.gz',gzip.compress(encoded(sim.snapshot()),compresslevel=1,mtime=0));raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);atomic(root/'EXECUTION.json',encoded(started|dict(status=status,error=error,finished_UTC=datetime.now(UTC).isoformat(),elapsed_seconds=prior+time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,completed_minutes=sim.rows_written,original_engine_sha256=q4.ENGINE_SHA,execution_calendar=q4.EXECUTION_CAL,terminal=q4.terminal_contract())));atomic(book,encoded(dict(status=status,binding=binding)))
    temp=root/('account_save_'+str(time.time_ns()));saved=old.save_case(sim.result(),temp);write_once(temp/'summary.json',encoded(saved['summary']));need(not (root/'account').exists(),'Preserve any existing account publication');os.replace(temp,root/'account');finish(state)


def report(state):
    source_check(state);root=account(state);s=read(root/'account/summary.json');a=read(root/'INDEPENDENT_AUDIT.json');e=read(root/'EXECUTION.json');recovery=read(root/'RECOVERY_AUDIT.json');fractions,budgets,gate=check(state)
    need(s['completion']==e['status']=='COMPLETE_CONDITIONAL_ACCOUNT' and s['terminal_cash_realized'] and recovery['account_snapshot_exact'] and recovery['minute_journal_bit_exact'],'Completed audited paid-flat result required')
    need(abs(s['net_PnL']-(s['gross_PnL_same_quantities']+s['funding_USDT']-s['fees_USDT']-s['execution_cost_USDT']))<1e-8,'Original net/cost/funding bridge differs')
    risk=margin.summarize(root/'account',ARM);write_once(PUBLIC/'HEADROOM.json',margin.encode(risk));m=read(PUBLIC/'producer/MANIFEST.json');desired=arrays(PUBLIC/'producer/REQUESTS.npz')['desired_expert_budget']
    result=dict(status='COMPLETE_ONE_EXPANDED_NATIVE92_AND_INDEPENDENTLY_AUDITED',arm=ARM,producer_commit=PRODUCER,data_commit=q4.DATA,engine_SHA256=q4.ENGINE_SHA,source_plan_commit=e['plan_commit'],request_SHA256=gate['request_sha256'],adapter_contract_SHA256=sha(PUBLIC/'ADAPTER_CONTRACT.json'),model_identity=m['model_identity'],checkpoint_identity=m['checkpoint_SHA256'],scaler_identity=m['scaler_identity'],execution_calendar=q4.EXECUTION_CAL,fresh_capital_USDT=10000,net_PnL_USDT=s['net_PnL'],price_PnL_USDT=s['gross_PnL_same_quantities'],funding_USDT=s['funding_USDT'],fees_USDT=s['fees_USDT'],execution_cost_USDT=s['execution_cost_USDT'],spread_USDT=s['spread_cost_USDT'],slippage_USDT=s['slippage_cost_USDT'],minute_max_drawdown=s['minute_max_drawdown'],realized_exposure=s['realized_exposure'],maximum_actual_gross_weight=s['maximum_actual_gross_weight'],maximum_actual_asset_weights=s['maximum_actual_asset_weights'],risk_reduction_signal_count=s['risk_reduction_signal_count'],liquidation_count=s['liquidation_count'],trade_legs=s['trade_legs'],normalized_total_turnover=s['normalized_total_turnover'],expert_order=m['expert_order'],expert_weights=dict(request_mean_all92=desired.mean(0).tolist(),applied_budget_mean_all92=budgets.mean(0).tolist(),request_mean_held91=desired[:91].mean(0).tolist(),applied_budget_mean_held91=budgets[:91].mean(0).tolist(),terminal_request=desired[-1].tolist(),terminal_applied_budget=budgets[-1].tolist()),terminal=a['terminal'],full_minute_window_months=months(root),original_monthly_table_scope=s['monthly_table_scope'],maximum_NAV_error_USDT=a['maximum_NAV_error_USDT'],actual_input_audit=a['actual_input_check'],elapsed_seconds=e['elapsed_seconds'],peak_RSS_bytes=e['peak_RSS_bytes'],full_original_snapshot_recovery=recovery,headroom_result_SHA256=sha(PUBLIC/'HEADROOM.json'),new_wallets=1,completed_wallet_reruns=0,fits=0,model_inference=0,provider_downloads=0,policy_changes=0)
    for name in ('INDEPENDENT_AUDIT.json','REQUEST_GATE.json','RECOVERY_AUDIT.json'):write_once(PUBLIC/name,(root/name).read_bytes())
    write_once(PUBLIC/'summary.json',(root/'account/summary.json').read_bytes());write_once(PUBLIC/'RESULT.json',encoded(result));comparators=read(PUBLIC/'COMPARATORS.json')
    comparison=dict(status='PASS_ONE_CONTROLLED_EXPANDED_HISTORY_NATIVE_Q4_COMPARISON',new_account=result,reused_comparator_commit=COMPARATORS,reused_accounts={k:v['result'] for k,v in comparators.items()},expanded_minus_original={k:{f:result[f]-v['result'][f] for f in ('net_PnL_USDT','price_PnL_USDT','funding_USDT','fees_USDT','execution_cost_USDT','minute_max_drawdown')} for k,v in comparators.items()},classification='SEEN_HISTORICAL_DEVELOPMENT_CONTROLLED_ADDED_DATA_COMPARISON',same_tape_and_financial_contract=True,realized_risk_equalized=False,independent_accounts_stitched=False,pristine_OOS=False,more_history_always_helps_claimed=False,daily_result_used_as_native_result=False,promotion=False,APR_claimed=False,new_wallets=1,comparator_wallet_reruns=0,fits=0,provider_downloads=0)
    write_once(PUBLIC/'COMPARISON.json',encoded(comparison));print(json.dumps(dict(status=result['status'],net_PnL_USDT=s['net_PnL'],minute_max_drawdown=s['minute_max_drawdown'],liquidations=s['liquidation_count'],old_model_delta=comparison['expanded_minus_original']['SELECTED_FULL773_256']['net_PnL_USDT'])),flush=True)


def package(state):
    report(state);original=account(state);result=read(PUBLIC/'RESULT.json');root=state/'portable-expanded-q4-native92'/ARM;root.mkdir(parents=True,exist_ok=False)
    for p in sorted(original.rglob('*')):
        if p.is_file() and 'recovery' not in p.relative_to(original).parts:
            target=root/'accounts'/ARM/p.relative_to(original);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    pointer=read(original/'recovery/CHECKPOINT.json')
    for name in ['CHECKPOINT.json',pointer['snapshot']['path'],*[v['path'] for v in pointer['minute_chunks']]]:
        target=root/'accounts'/ARM/'recovery'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(original/'recovery'/name,target)
    repo=root/'repo';helper=repo/HERE.relative_to(REPO);helper.mkdir(parents=True,exist_ok=True)
    names=('expanded_q4_native92.py','q4_native92.py','verify_q4_native92.py','finalize_q4_native92.py','package_q4_native92.py','native_margin_risk_summary.py','prefix_static_native63.py','evaluate_requests63.py','evaluate_requests61.py','native61.py','package_prequential63.py','requirements.txt','requirements-native61.txt','EVALUATE_REQUESTS61_ADAPTER.json','NATIVE61_PLAN.json')
    for name in names:shutil.copyfile(HERE/name,helper/name)
    for name,h in read(PUBLIC/'ADAPTER_CONTRACT.json')['source_SHA256'].items():
        p=REPO/name;need(sha(p)==h,'Frozen source differs');target=repo/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    for name in ('modules/transformer_v3/isolated_audit.py','scripts/investment/audit_shared_direction.py'):
        target=helper/'verification_helpers'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE/'verification_helpers'/name,target)
    original_public=helper/'q4-native92';original_public.mkdir();shutil.copyfile(q4.PUBLIC/'ADAPTER_CONTRACT.json',original_public/'ADAPTER_CONTRACT.json');shutil.copytree(q4.PUBLIC/'producer',original_public/'producer')
    for arm in q4.ARMS:
        target=original_public/'results'/arm;target.mkdir(parents=True)
        for name in read(PUBLIC/'COMPARATORS.json')[arm]['files']:shutil.copyfile(q4.PUBLIC/'results'/arm/name,target/name)
    target=repo/q4.reused.FINANCIAL.relative_to(REPO);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(q4.reused.FINANCIAL,target)
    shutil.copytree(PUBLIC,helper/'expanded-q4-native92',ignore=shutil.ignore_patterns('transport','ARTIFACT.json','RESULT_MEMBER_HASHES.json','PUBLIC_READBACK.json','COMPLETION.json'))
    write_once(root/'RESULT.json',encoded(result));write_once(root/'RECOVERY_MANIFEST.json',encoded(dict(schema='ONE_EXPANDED_NATIVE92_PORTABLE_ORIGINAL_ACCOUNT_V1',arm=ARM,required_repository='snowycat1234/coin',plan_commit=result['source_plan_commit'],account='accounts/'+ARM,checkpoint='accounts/'+ARM+'/recovery/CHECKPOINT.json',dependency_recipe='repo/'+HERE.relative_to(REPO).as_posix()+'/requirements-native61.txt',retained_market_contract='repo/'+(q4.PUBLIC/'ADAPTER_CONTRACT.json').relative_to(REPO).as_posix(),market_inputs='EXISTING_CACHED_BOUND_STATE_OR_PINNED_PUBLIC_ARTIFACTS;NO_PROVIDER_DOWNLOADS',restore='UNCHANGED_Q4_NATIVE92_RESTORE;COMPLETED_ACCOUNT_MUST_NOT_ADVANCE',completed_minutes=131046,original_engine_SHA256=q4.ENGINE_SHA,private_runtime_inventory_included=False)))
    members=[]
    for p in sorted(root.rglob('*')):
        if not p.is_file():continue
        raw=p.read_bytes();need('__pycache__' not in p.parts and p.suffix!='.pt','No cache/model tensors in archive')
        if p.suffix in ('.json','.md','.py','.txt'):need(not re.search(rb'/(?:workspace|home/xflops|mnt/d)/|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN [A-Z ]*PRIVATE KEY',raw),'Private paths/credentials prohibited')
        members.append(dict(path=p.relative_to(root).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    manifest=dict(schema='ONE_EXPANDED_NATIVE92_ORIGINAL_ACCOUNT_MEMBER_HASHES_V1',files=members,original_account_journals_edited=False,raw_market_or_model_weights_duplicated=False,private_runtime_inventories_included=False);raw=encoded(manifest);write_once(root/'RESULT_MEMBER_HASHES.json',raw);write_once(PUBLIC/'RESULT_MEMBER_HASHES.json',raw)
    archive=state/'coin_expanded_q4_native92_20261010.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(root.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(root).as_posix())
    with zipfile.ZipFile(archive) as z:need(z.testzip() is None,'ZIP CRC differs')
    data=archive.read_bytes();parts=[]
    for i,start in enumerate(range(0,len(data),768*1024)):
        raw=data[start:start+768*1024];name=archive.name+f'.bytepart{i:03d}';write_once(PUBLIC/'transport'/name,raw);parts.append(dict(path='transport/'+name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    artifact=dict(schema='ONE_EXPANDED_NATIVE92_ORDERED_PUBLIC_ACCOUNT_PARTS_V1',filename=archive.name,bytes=len(data),sha256=sha(archive),part_max_bytes=768*1024,parts=parts,member_manifest_sha256=sha(root/'RESULT_MEMBER_HASHES.json'),original_journals_byte_identical=True,raw_market_and_weights_duplicated=False);write_once(PUBLIC/'ARTIFACT.json',encoded(artifact));print(json.dumps(dict(status='PASS_ONE_ORIGINAL_EXPANDED_Q4_ACCOUNT_PACKAGE',bytes=len(data),sha256=artifact['sha256'],parts=len(parts),members=len(members))),flush=True)


def public_readback(state,commit):
    need(len(commit)==40 and set(commit)<=set('0123456789abcdef'),'Exact public artifact commit required');prefix=PUBLIC.relative_to(REPO).as_posix();root=state/'public-expanded-q4-native92-readback'/commit;root.mkdir(parents=True,exist_ok=True);digest=lambda raw:hashlib.sha256(raw).hexdigest()
    def fetch(name,limit=786433):
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
        if not p.exists():p.write_bytes(urllib.request.urlopen('https://raw.githubusercontent.com/snowycat1234/coin/'+commit+'/'+prefix+'/'+name,timeout=30).read(limit))
        return p.read_bytes()
    artifact=json.loads(fetch('ARTIFACT.json'));raw_manifest=fetch('RESULT_MEMBER_HASHES.json');manifest=json.loads(raw_manifest);need(digest(raw_manifest)==artifact['member_manifest_sha256'],'Public member manifest differs')
    def part(v):
        raw=fetch(v['path'],v['bytes']+1);need(len(raw)==v['bytes'] and digest(raw)==v['sha256'],'Public archive part differs');return raw
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:chunks=list(ex.map(part,artifact['parts']))
    raw=b''.join(chunks);need(len(raw)==artifact['bytes'] and digest(raw)==artifact['sha256'],'Public archive differs');archive=root/artifact['filename'];archive.write_bytes(raw);extracted=root/'extracted';extracted.mkdir(exist_ok=True);count=0
    with zipfile.ZipFile(archive) as z:
        need(z.testzip() is None and set(z.namelist())=={v['path'] for v in manifest['files']}|{'RESULT_MEMBER_HASHES.json'} and z.read('RESULT_MEMBER_HASHES.json')==raw_manifest,'Public archive domain/CRC differs')
        for v in manifest['files']:
            data=z.read(v['path']);need(len(data)==v['bytes'] and digest(data)==v['sha256'],'Public member differs');p=extracted/v['path'];need(p.resolve().is_relative_to(extracted.resolve()),'Unsafe archive path');p.parent.mkdir(parents=True,exist_ok=True)
            if p.exists():need(p.read_bytes()==data,'Existing recovered member differs')
            else:p.write_bytes(data)
            if v['path'].startswith('accounts/'+ARM+'/'):
                source=account(state)/v['path'][len('accounts/'+ARM+'/'):];need(record(source)==dict(bytes=v['bytes'],sha256=v['sha256']),'Original account changed');count+=1
            if v['path'].startswith('repo/'):need(subprocess.check_output(['git','show',commit+':'+v['path'][5:]],cwd=REPO)==data,'Published repository source differs')
    result=json.loads(fetch('RESULT.json'));need(result==read(extracted/'RESULT.json'),'Public result differs');source_commit=result['source_plan_commit'];source_repo=state/'public-expanded-q4-native92-source'/source_commit;source_repo.mkdir(parents=True,exist_ok=True)
    for name in subprocess.check_output(['git','ls-tree','-r','--name-only',source_commit,'--','src','scripts','modules'],cwd=REPO).decode().splitlines():
        if not name.endswith('.py'):continue
        data=subprocess.check_output(['git','show',source_commit+':'+name],cwd=REPO)
        for p in (source_repo/name,extracted/'repo'/name):
            p.parent.mkdir(parents=True,exist_ok=True)
            if p.exists():need(p.read_bytes()==data,'Transitive original source differs')
            else:p.write_bytes(data)
    code="""import json,os,resource,socket
from pathlib import Path
import expanded_q4_native92 as ex
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6000000000,6000000000))
def offline(*a,**k):raise RuntimeError('Public recovered financial audit forbids network')
socket.create_connection=offline;socket.socket.connect=offline
state=Path(STATE);root=Path(ACCOUNT)
ex.source_check(state);audit=ex.audit92.verify(root,state)
sim,pointer=ex.q4.restore(root/'recovery',ex.read(root/'BINDING.json'),ex.q4.window(state));summary=ex.read(root/'account/summary.json')
assert pointer['completed_decisions']==92 and sim.rows_written==131046 and all(p.quantity==0 for p in sim.account.positions.values()) and abs(float(sim.account.nav())-summary['NAV'])<1e-8
assert sim.account.trades==ex.read(root/'account/trades.json') and sim.funding_journal==ex.read(root/'account/funding.json')
risk=ex.margin.summarize(root/'account',ex.ARM);assert ex.margin.encode(risk)==(ex.PUBLIC/'HEADROOM.json').read_bytes()
print(json.dumps(dict(audit=audit,state_hash=sim.state_hash(),NAV=float(sim.account.nav()),journal_exact=True,headroom_exact=True)))
""".replace('STATE',repr(str(state))).replace('ACCOUNT',repr(str(extracted/'accounts'/ARM)))
    env=os.environ.copy();env.update(PYTHONPATH=os.pathsep.join(map(str,(state/'deps',source_repo/'src',source_repo))),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',POLARS_MAX_THREADS='1');portable=json.loads(subprocess.check_output([sys.executable,'-c',code],cwd=extracted/'repo'/HERE.relative_to(REPO),env=env))
    receipt=dict(status='PASS_PUBLIC_EXPANDED_ORIGINAL_JOURNALS_FULL_STATE_AND_HEADROOM_RESTORE',arm=ARM,artifact_commit=commit,archive_SHA256=artifact['sha256'],archive_bytes=artifact['bytes'],parts=len(chunks),members=len(manifest['files']),original_account_files_byte_identical=count,engine_SHA256=q4.ENGINE_SHA,final_checkpoint_state_hash=portable['state_hash'],completed_minutes=131046,terminal_paid_flat=True,account_journal_exact=portable['journal_exact'],headroom_result_exact=portable['headroom_exact'],restored_account_NAV=portable['NAV'],portable_actual_input_audit=portable['audit'],transitive_public_repository_source_commit=source_commit,wallet_advanced_after_restore=False,wallets_run=0,completed_wallet_reruns=0,fits=0,provider_downloads=0)
    write_once(PUBLIC/'PUBLIC_READBACK.json',encoded(receipt));print(json.dumps({k:v for k,v in receipt.items() if k!='portable_actual_input_audit'}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('prepare','check','run','finish','report','package','readback'));p.add_argument('--state',type=Path,required=True);p.add_argument('--commit');a=p.parse_args()
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6000000000,6000000000));resource.setrlimit(resource.RLIMIT_CPU,(600,600))
    if a.command!='readback':
        def offline(*args,**kwargs):raise RuntimeError('Expanded Q4 native execution forbids network')
        socket.create_connection=offline;socket.socket.connect=offline
    if a.command=='prepare':prepare(a.state)
    elif a.command=='check':source_check(a.state);print(json.dumps(check(a.state)[2]),flush=True)
    elif a.command in ('run','finish'):
        locks=a.state/'expanded-q4-native92-locks';locks.mkdir(exist_ok=True)
        with (locks/ARM).open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            if a.command=='run':need(a.commit is not None,'Published one-account plan commit required');execute(a.state,a.commit)
            else:finish(a.state)
    elif a.command=='report':report(a.state)
    elif a.command=='package':package(a.state)
    else:need(a.commit is not None,'Published archive commit required');public_readback(a.state,a.commit)
