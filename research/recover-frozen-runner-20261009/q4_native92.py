"""Frozen selected256 Q4 requests through the unchanged native minute engine.

92 daily decisions, 91 held intervals, then the original six-minute terminal
window on December31. Actual capacity/lot/cost/funding rules own every fill.
No fits, inference, synthetic inputs, reselection or completed account reruns.
"""
import argparse,fcntl,gzip,hashlib,io,json,os,resource,shutil,signal,socket,subprocess,time
from datetime import datetime,UTC
from pathlib import Path
import numpy as np
import prefix_static_native63 as reused
base=reused.base;HERE=base.HERE;REPO=base.frozen.REPO;PUBLIC=HERE/'q4-native92'
read=reused.read;sha=reused.sha;require=reused.require;record=reused.record;encoded=reused.encoded;atomic=reused.atomic;write_once=reused.write_once;arrays=reused.arrays
PRODUCER='657aeaff93889da600ad88b3603739508ba03216';DATA='152606ad56fe6d8943b27ce89c8c57e2068ee944'
PRODUCER_REL='research/temporal-selected-refit-q4-20261010';DATA_REL='research/core5-q4-2024-native-data'
MANIFEST_SHA='ff28cd141f7f40d879365e8e635da4795f2eeef2626ab664869c095e321987a3'
CONSUMER_SHA='d972444cb43320ef3f356bd90d83a2a51dcea5d3ce552784870f99b40d2dbe23'
PRODUCER_RESULT_MANIFEST_SHA='f6982f558bc5001ae742198f7f54a52d7e3f3effbc0f24d1cf50a42f15376695'
ENGINE_SHA=reused.ENGINE_SHA;START=1727740800000000;LAST=1735603200000000;END=LAST+6*base.frozen.MINUTE
REQUEST_CAL=dict(start=START,end_exclusive=1735689600000000,days=92,minutes=132480,funding_events=1380)
EXECUTION_CAL=dict(start=START,end_exclusive=END,decisions=92,full_held_days=91,terminal_minutes=6,minutes=131046,funding_events=1370)
ARMS={'SELECTED_FULL773_256':'REQUESTS.npz','FROZEN_VOL':'REQUESTS_FROZEN_VOL.npz','Static50':'REQUESTS_Static50.npz','Cash50':'REQUESTS_Cash50.npz'}


def locations(state):return state/'q4-public'/PRODUCER/PRODUCER_REL/'q4-results',state/'q4-data/Q42024',state/'q4-data/Q42024/normalized'


def terminal_contract():
    return dict(request_decisions=92,held_intervals=91,producer_paid_close_us=LAST+base.frozen.MINUTE+1,producer_paid_close_UTC='2024-12-31T00:01:00.000001Z',native_close_signal_us=LAST,native_first_eligible_close_us=LAST+base.frozen.MINUTE+1,native_last_eligible_attempt_us=LAST+5*base.frozen.MINUTE+1,native_window_end_exclusive_us=END,original_terminal_attempts=5,last_request_preserved=True,last_execution_target_zero=True,extra_full_day_exposure=False,January1_outcome_consumed=False,terminal_price_and_quantity='ACTUAL_TRADE_OPEN_PREVIOUS_QUOTE_CAPACITY_LOT_AND_FEE_RULES;NO_FORCED_FILL',minute_exact_epsilon_daily_fill_parity_claimed=False,unavoidable_difference='The daily producer assumes one complete paid close at its epsilon-time execution price. Native closure may be partial or delayed through five original attempt-minutes, and includes actual funding ownership until fills. A remaining position stops evaluation; no invented fill or extra holding day.')


def window(state):
    """Slice actual source callback; retain causal completed-day sizing prices."""
    import polars as pl
    base.frozen.modules(state);_,_,work=locations(state)
    complete=base.market(state,REQUEST_CAL,work);callback=complete['minute_blocks']
    def blocks():
        for block in callback():
            ix=block['times']<END
            if not ix.any():break
            yield dict(times=block['times'][ix],market={s:{k:v[ix] for k,v in asset.items()} for s,asset in block['market'].items()})
    daily=[]
    for s in base.frozen.SYMBOLS:
        p=state/'h1_validation/original/h1_market/data/normalized'/(s+'_daily.parquet')
        daily.append(pl.read_parquet(p).filter((pl.col('close_us')>=START)&(pl.col('close_us')<=LAST)&(pl.col('available_us')<=pl.col('close_us'))).select('symbol','close_us','close'))
    return complete|dict(end=END,events=[e for e in complete['events'] if e['event_us']<END],daily=pl.concat(daily),minute_blocks=blocks)


def contexts():
    a=arrays(PUBLIC/'producer/CURRENT_EXPERT_INPUTS92.npz');return {k:a[k] for k in ('expert_targets','expert_eligible','target_available_us','past_returns30')}|dict(expert_order=base.E5+(base.SHORT,))


def check(state,arm):
    manifest=read(PUBLIC/'producer/MANIFEST.json');a=arrays(PUBLIC/'producer'/ARMS[arm]);c=contexts();source=arrays(PUBLIC/'producer/CURRENT_EXPERT_INPUTS92.npz');paired=arrays(PUBLIC/'producer/PAIRED_PATHS.npz')
    full,report=base.validate(dict(expert_order=manifest['expert_order'],allowed_actions=list(base.COMPACT+(base.SHORT,)),uses_feedback_features=False),a,c,REQUEST_CAL)
    require(np.array_equal(full,paired[arm+'_requests']) and np.array_equal(a['feature_available_us'],source['input_available_us'].max(1)) and np.array_equal(a['request_available_us'],a['decision_us']),'Original frozen request/source feature clocks differ')
    require(np.array_equal(a['action_eligible'],source['expert_eligible']) and not a['action_eligible'][:,2:4].any(),'Original mask/excluded E5 slots differ')
    mapper=base.frozen.modules(state);fractions,budgets=base.mapped(full,c,mapper.mapper,REQUEST_CAL)
    require(np.array_equal(fractions,paired[arm+'_targets']) and np.array_equal(budgets,paired[arm+'_budget']),'Original native mapper and source budget/target parity required')
    if arm!='SELECTED_FULL773_256':
        expected=np.zeros((92,6))
        if arm=='FROZEN_VOL':expected[:,1]=1
        elif arm=='Static50':expected[:,[1,4]]=.5
        else:expected[:,0]=.5;expected[:,[1,4]]=.25
        require(np.array_equal(full,expected),'Frozen control changed')
    require(not fractions[-1].any() and np.array_equal(full[-1],paired[arm+'_requests'][-1]),'Preserve terminal request; original execution target zero required')
    return fractions,budgets,report|dict(status='PASS_FROZEN92_REQUEST_CLOCK_MASK_SLOT_AND_BIT_EXACT_MAPPING',arm=arm,request_sha256=sha(PUBLIC/'producer'/ARMS[arm]),handoff_manifest_sha256=MANIFEST_SHA,fractions_f64_sha256=hashlib.sha256(fractions.tobytes()).hexdigest(),budgets_f64_sha256=hashlib.sha256(budgets.tobytes()).hexdigest(),terminal_request_preserved=True,terminal_execution_target_zero=True,fits=0,model_inference=0,wallets_run=0)


def source_check(state):
    contract=read(PUBLIC/'ADAPTER_CONTRACT.json');require(contract['engine_sha256']==ENGINE_SHA and contract['request_calendar']==REQUEST_CAL and contract['execution_calendar']==EXECUTION_CAL and contract['terminal']==terminal_contract(),'Frozen exact calendars/terminal/engine required')
    for n,h in contract['source_sha256'].items():require(sha(REPO/n)==h,'Original financial or thin adapter source differs: '+n)
    for section in ('market_artifacts','daily_sizing_sources','official_archive_sources','state_source_dependencies'):
        for entry in contract[section]:require(record(base.member(state,entry['path']))=={k:entry[k] for k in ('bytes','sha256')},'Retained actual input byte identity differs: '+entry['path'])
    manifest=read(PUBLIC/'producer/MANIFEST.json');require(sha(PUBLIC/'producer/MANIFEST.json')==MANIFEST_SHA,'Original handoff manifest differs')
    for n,v in manifest['files'].items():
        p=PUBLIC/'producer'/n
        if p.exists():require(p.stat().st_size==v['bytes'] and sha(p)==v['SHA256'],'Preserved original producer member differs: '+n)
    result_manifest=read(PUBLIC/'producer/RESULT_MANIFEST.json');require(sha(PUBLIC/'producer/RESULT_MANIFEST.json')==PRODUCER_RESULT_MANIFEST_SHA,'Original once-score manifest differs')
    for n in ('PAIRED_PATHS.npz','RESULT.json','CURRENT_CONTEXT.npz','INPUT_RECEIPT.json'):
        require(record(PUBLIC/'producer'/n)==dict(bytes=result_manifest['files'][n]['bytes'],sha256=result_manifest['files'][n]['SHA256']),'Original once-score member differs: '+n)
    require(record(PUBLIC/'producer/VERIFICATION.json')==dict(bytes=463,sha256='6d1d983f125ee4bf30a47b0f7cb14414b4a12d1977d54aea8d7ab87b6537461f'),'Pinned producer verification differs')
    return dict(status='PASS_ORIGINAL_FINANCIAL_SOURCE_AND_BOUND_RETAINED_ACTUAL_INPUT_BYTES',engine_sha256=ENGINE_SHA,provider_downloads=0)


def prepare(state):
    import polars as pl
    producer,data,work=locations(state);handoff=producer/'native-handoff';m=read(handoff/'MANIFEST.json');require(sha(handoff/'MANIFEST.json')==MANIFEST_SHA and m['schema']=='SOURCE_BOUND_SELECTED256_Q4_NATIVE92_REQUESTS_V1' and m['decisions']==92 and m['active_intervals']==91 and m['terminal_execution_us']==LAST+base.frozen.MINUTE+1 and m['economic_source_commit']==DATA,'Exact external selected256 handoff required')
    for n,v in m['files'].items():
        if n.endswith('.pt'):continue
        require(record(handoff/n)==dict(bytes=v['bytes'],sha256=v['SHA256']),'Original producer member differs: '+n)
    for n,h in m['source_files'].items():require(sha(handoff/'source'/n)==h,'Original producer source differs: '+n)
    protocol=read(handoff/'PROTOCOL.json');run=read(handoff/'RUN.json')['specification'];terminal=read(handoff/'TERMINAL.json');scaler=read(handoff/'SCALER.json');initial=read(producer.parent/'frozen/FULL773_LOW_LR3E4_DATE_256/INITIAL.json');score=read(producer/'RESULT.json')
    require(protocol['parameters']==m['parameters']==terminal['parameters']==13699 and protocol['active_training_dates']==773 and protocol['training_decisions']==778 and protocol['updates']==m['training_updates']==terminal['completed_updates']==terminal['fixed_target']==256,'Frozen selected refit size/update receipt differs')
    require(run['algorithm']['parent']==dict(fresh=True,step=0) and len(run['algorithm']['parameter_birth_steps'])==13 and all(v==0 for v in run['algorithm']['parameter_birth_steps'].values()) and initial['step']==terminal['initial_step']==0 and terminal['status']=='FIXED256_COMPLETE' and terminal['failure'] is None and terminal['reserve_reads']==0,'Declared fresh refit and freeze-before-Q4 receipt differs')
    require(all(v==256 for v in terminal['optimizer_parameter_ages'].values()) and terminal['checkpoint_SHA256']==score['checkpoint_SHA256']==m['checkpoint_SHA256'] and terminal['model_identity']==score['model_identity']==m['model_identity'] and scaler['identity']==m['scaler_identity'] and scaler['provenance']['real_row_count']==907 and scaler['provenance']['training_cutoff_us']<START,'Frozen model/scaler identities and source clocks differ')
    require(score['native_wallets']==score['optimizer_updates']==score['scaler_updates']==0 and score['reserve_model_scores']==1 and score['model_Adam_all_RNG_unchanged'] and score['no_Q4_checkpoint_selection'],'Only the already completed frozen once-score required')
    names=['MANIFEST.json','PROTOCOL.json','RUN.json','TERMINAL.json','SCALER.json','SCALER.npz','latest.json','CURRENT_EXPERT_INPUTS92.npz',*ARMS.values()]
    for n in names:write_once(PUBLIC/'producer'/n,(handoff/n).read_bytes())
    for n in ('PAIRED_PATHS.npz','RESULT.json','CURRENT_CONTEXT.npz','INPUT_RECEIPT.json','VERIFICATION.json'):write_once(PUBLIC/'producer'/n,(producer/n).read_bytes())
    require(sha(producer/'MANIFEST.json')==PRODUCER_RESULT_MANIFEST_SHA,'Original once-score source manifest differs');write_once(PUBLIC/'producer/RESULT_MANIFEST.json',(producer/'MANIFEST.json').read_bytes())
    write_once(PUBLIC/'producer/INITIAL.json',encoded(initial))
    consumer=state/'q4-public'/DATA/DATA_REL/'CONSUMER_INDEX.json';require(sha(consumer)==CONSUMER_SHA,'Frozen public input consumer differs');write_once(PUBLIC/'CONSUMER_INDEX.json',consumer.read_bytes())
    local=read(data/'LOCAL_NORMALIZED_VALIDATION.json');published=read(data/'VALIDATION.json');require(local['coverage']==published['coverage'] and local['monthly_and_daily_source_receipts']==published['monthly_and_daily_source_receipts'] and local['supplement_checks']==published['supplement_checks'],'Exact original source values/normalizer/supplement receipt parity required')
    require(published['native_minute_grid_complete'] and all(v['zero_quote_volume_minutes']==89 for v in published['coverage'].values()),'Complete actual grid with original zeros required')
    financial=read(reused.FINANCIAL);require(sha(reused.FINANCIAL)==reused.FINANCIAL_SHA,'Original financial reference differs');sources=dict(financial['source_sha256'])
    for n in ('prefix_static_native63.py','q4_native92.py','verify_q4_native92.py'):sources[(HERE/n).relative_to(REPO).as_posix()]=sha(HERE/n)
    artifacts=[]
    for v in published['derived_artifacts']:
        p=data/v['path'];artifacts.append(dict(path=p.relative_to(state).as_posix(),**record(p),published_sha256=v['SHA256'],published_parquet_bytes_identical=sha(p)==v['SHA256'],role=v['role']))
    raw=read(data/'RAW_MANIFEST.json');rawsources=[dict(path=(data/v['relative_raw_path']).relative_to(state).as_posix(),bytes=v['size'],sha256=v['SHA256']) for v in raw['records']]
    daily=[dict(path=(state/'h1_validation/original/h1_market/data/normalized'/(s+'_daily.parquet')).relative_to(state).as_posix(),**record(state/'h1_validation/original/h1_market/data/normalized'/(s+'_daily.parquet'))) for s in base.frozen.SYMBOLS]
    old_dependencies=read(HERE/'NATIVE61_PLAN.json')['public_input'];dependencies=[]
    for name,key in [('h1_validation/original/source_increment/modules/native_action/e5_inputs.py','original_mapper_sha256'),('e5-bear-original/source_increment/modules/native_action/e5_teacher.py','original_mapper_teacher_sha256')]:
        require(sha(state/name)==old_dependencies[key],'Original retained mapper source differs');dependencies.append(dict(path=name,**record(state/name)))
    contract=dict(schema='Q4_NATIVE92_CALENDAR_AND_TERMINAL_ADAPTER_V1',engine_sha256=ENGINE_SHA,financial_reference=dict(path=reused.FINANCIAL.relative_to(REPO).as_posix(),sha256=reused.FINANCIAL_SHA),financial_contract=financial['financial_contract'],cost=financial['cost'],limits=financial['limits'],request_calendar=REQUEST_CAL,execution_calendar=EXECUTION_CAL,terminal=terminal_contract(),source_sha256=sources,market_work_relative=work.relative_to(state).as_posix(),market_artifacts=artifacts,daily_sizing_sources=daily,official_archive_sources=rawsources,normalization_source_SHA256=published['normalization_source_SHA256'],source_producer_commit=PRODUCER,source_data_commit=DATA,consumer_SHA256=CONSUMER_SHA,parquet_encoding_scope='Original published economic/funding bytes retained. Native minute Parquets have different container bytes but exact frozen-normalizer source values and identical original source/quote/clock/supplement receipts.',daily_sizing_price='UNCHANGED_ORIGINAL_ENGINE_COMPLETED_DAILY_CLOSE;ACTUAL_00:01_OPENS_ARE_EXECUTION_ONLY',historical_publication_and_account_rules_certified=False)
    contract['state_source_dependencies']=dependencies
    write_once(PUBLIC/'ADAPTER_CONTRACT.json',encoded(contract));base.frozen.modules(state);c=contexts();tt=np.arange(START,REQUEST_CAL['end_exclusive'],base.frozen.DAY,dtype=np.int64);checkdates=np.arange(1711929600000000,REQUEST_CAL['end_exclusive'],base.frozen.DAY,dtype=np.int64);bars=[];matrix=[];clock=None
    for j,s in enumerate(base.frozen.SYMBOLS):
        d=pl.read_parquet(state/'h1_validation/original/h1_market/data/normalized'/(s+'_daily.parquet')).filter((pl.col('close_us')<=LAST)&(pl.col('available_us')<=LAST)).sort('close_us');times=d['close_us'].to_numpy();values=d['close'].to_numpy();ix=np.searchsorted(times,tt)
        require(np.array_equal(times[ix],tt) and np.array_equal(np.stack([np.diff(values[i-30:i+1])/values[i-30:i] for i in ix]),c['past_returns30'][:,:,j]),'Actual completed daily covariance source differs')
        if clock is not None:require(np.array_equal(times,clock),'Identical asset daily source calendar required')
        clock=times;matrix.append(values);bars.append(d.filter(pl.col('complete_kline')).select('symbol','open_us','close_us','available_us','open','high','low','close','volume'))
    from scripts.investment import vol_managed_perpetual_target as vol,momentum_short_pool_target as short
    from scripts.research.public_cross_section_momentum import public_targets
    bars=pl.concat(bars);ix=np.searchsorted(checkdates,tt);vf,_=vol.fixed_targets(bars,checkdates,symbols=base.frozen.SYMBOLS);sf,_=short.fixed_targets(bars,checkdates,symbols=base.frozen.SYMBOLS);cs,diag=public_targets(np.column_stack(matrix),clock,checkdates,base.frozen.SYMBOLS,base.frozen.SYMBOLS)
    for slot,a in [(1,vf['target_weight'].to_numpy().reshape(len(checkdates),5)[ix]),(4,cs[ix]),(5,sf['target_weight'].to_numpy().reshape(len(checkdates),5)[ix])]:require(np.array_equal(a,c['expert_targets'][:,slot]),'Original expert target recipe parity differs')
    require(diag['weekly_anchor_us']==1704067200000000,'Original Jan1 weekly rank anchor required')
    source_check(state);win=window(state);n=0;zeros=dict.fromkeys(base.frozen.SYMBOLS,0)
    for block in win['minute_blocks']():
        require(np.array_equal(block['times'],np.arange(START+n*base.frozen.MINUTE,START+(n+len(block['times']))*base.frozen.MINUTE,base.frozen.MINUTE)) and set(block['market'])==set(base.frozen.SYMBOLS),'Complete actual scored minute grid required')
        for s,a in block['market'].items():require(all(np.isfinite(v).all() for v in a.values()) and (a['open']>0).all() and (a['mark']>0).all() and (a['quote_volume']>=0).all(),'Real finite prices/quote capacity required');zeros[s]+=int((a['quote_volume']==0).sum())
        n+=len(block['times'])
    require(n==131046 and len(win['events'])==1370,'Exact91 held days plus six terminal minutes/funding1370 required')
    gates={}
    for arm in ARMS:
        fractions,budgets,gate=check(state,arm);gates[arm]=gate
        plan=dict(authorization='USER_AUTHORIZED_EXACTLY_FOUR_FROZEN_Q4_NATIVE92_WALLETS',arm=arm,producer_commit=PRODUCER,data_commit=DATA,request_calendar=REQUEST_CAL,execution_calendar=EXECUTION_CAL,adapter_contract_sha256=sha(PUBLIC/'ADAPTER_CONTRACT.json'),engine_sha256=ENGINE_SHA,mapping_preflight=gate,terminal=terminal_contract(),resource_limits=financial['limits'],account_start='FRESH10000;PREVIOUS_QUOTE_NONE;INITIAL_CAPACITY_ZERO;NO_CARRIED_POSITION',controls='NO_EXISTING_NATIVE_Q4_CONTROL_HAS_THIS_EXACT_PARTIAL_TERMINAL_CONTRACT;FOUR_NEW_ACCOUNTS',resume='ORIGINAL_ENGINE_SOURCE_BOUND_DAILY_CHECKPOINT_INCLUDING_FINAL_PARTIAL_DAY',stop='ANY_SOURCE_OR_GRID_OR_FINANCIAL_OR_FLAT_OR_AUDIT_FAILURE;NO_TUNING_OR_RESELECTION_OR_FORCED_FILLS',model_fits=0,model_inference=0,provider_downloads=0,new_wallets=1)
        write_once(PUBLIC/(arm+'.json'),encoded(plan))
    ready=dict(status='PASS_FROZEN_Q4_NATIVE92_REQUESTS_SOURCE_RECIPE_MAPPING_AND_PARTIAL_TERMINAL_READY',producer_commit=PRODUCER,data_commit=DATA,handoff_manifest_sha256=MANIFEST_SHA,producer_sources_verified=len(m['source_files']),model_identity=m['model_identity'],checkpoint_sha256=m['checkpoint_SHA256'],protocol_identity=m['protocol_identity'],scaler_identity=m['scaler_identity'],provenance_scope='HASH_BOUND_ALREADY_COMPLETED_SELECTED_FRESH256_AND_ONCE_Q4_RECEIPTS;NO_TENSORS_LOADED_OR_OPTIMIZER_REPLAY',actual_daily_covariance_and_expert_recipe_bit_exact=True,source_request_target_budget_bit_exact=True,scored_minutes=n,scored_funding_events=1370,source_full_minutes=132480,source_capacity_zeros_per_asset=89,scored_capacity_zeros=zeros,terminal=terminal_contract(),gates=gates,fits=0,model_inference=0,wallets_run=0,provider_downloads=0)
    write_once(PUBLIC/'PRECHECK.json',encoded(ready));return {k:v for k,v in ready.items() if k not in ('gates','terminal')}


def save_checkpoint(root,sim,binding,elapsed):
    root.mkdir(parents=True,exist_ok=True);old=read(root/'CHECKPOINT.json') if (root/'CHECKPOINT.json').exists() else None;count=len(sim.minute_chunks)
    expected=min(count*1440,EXECUTION_CAL['minutes']);require(sim.stop is None and sim.rows_written==expected and ((count<=EXECUTION_CAL['full_held_days'] and sim.cursor==START+count*base.frozen.DAY) or (count==EXECUTION_CAL['decisions'] and sim.cursor==END)),'Complete original decision boundary required')
    require((old is None and count==0) or (old['binding']==binding and old['completed_decisions']+1==count),'Monotone bound same-account checkpoint required');chunks=[] if old is None else old['minute_chunks'].copy()
    if count:
        buffer=io.BytesIO();np.save(buffer,sim.minute_chunks[-1],allow_pickle=False);name=f'minute/DECISION_{count:03d}.npy';raw=buffer.getvalue();atomic(root/name,raw);chunks.append(dict(path=name,**record(root/name)))
    snap=sim.snapshot();snap.pop('minute_chunks');name=f'state/DECISION_{count:03d}.json.gz';atomic(root/name,gzip.compress(encoded(snap),compresslevel=1,mtime=0))
    pointer=dict(schema='Q4_ORIGINAL_NATIVE92_RECOVERY_V1',binding=binding,completed_decisions=count,completed_minutes=sim.rows_written,elapsed_seconds=elapsed,state_hash=sim.state_hash(),snapshot=dict(path=name,**record(root/name)),minute_chunks=chunks);atomic(root/'CHECKPOINT.json',encoded(pointer));return pointer


def restore(root,binding,win):
    from scripts.investment.resumable_perpetual import NativeDailySimulator
    from quant.bybit_isolated_account import BybitIsolatedAccount
    pointer=read(root/'CHECKPOINT.json');count=pointer['completed_decisions'];require(pointer['schema']=='Q4_ORIGINAL_NATIVE92_RECOVERY_V1' and pointer['binding']==binding and len(pointer['minute_chunks'])==count and 0<=count<=EXECUTION_CAL['decisions'] and pointer['completed_minutes']==min(count*1440,EXECUTION_CAL['minutes']),'Exact source/plan/request partial-calendar recovery binding required')
    entry=pointer['snapshot'];p=base.member(root,entry['path']);require(record(p)=={k:entry[k] for k in ('bytes','sha256')},'Financial snapshot bytes differ');snapshot=json.loads(gzip.decompress(p.read_bytes()));chunks=[]
    for i,e in enumerate(pointer['minute_chunks'],1):
        require(e['path']==f'minute/DECISION_{i:03d}.npy','Exact ordered recovery chunks required');p=base.member(root,e['path']);require(record(p)=={k:e[k] for k in ('bytes','sha256')},'Minute snapshot bytes differ');a=np.load(p,allow_pickle=False);require(a.dtype==np.float64 and a.shape==((1440 if i<=EXECUTION_CAL['full_held_days'] else EXECUTION_CAL['terminal_minutes']),36) and np.isfinite(a).all(),'Original numeric minute shape differs');chunks.append(a)
    require(snapshot['state']['rows_written']==pointer['completed_minutes'] and snapshot['state']['cursor']==START+pointer['completed_minutes']*base.frozen.MINUTE and snapshot['persist_cash_close'] and snapshot['final_day_target_zero'],'Original partial terminal scheduler recovery differs');snapshot['minute_chunks']=[a.tolist() for a in chunks]
    sim=NativeDailySimulator.from_snapshot(snapshot,win,account_class=BybitIsolatedAccount);require(sim.state_hash()==pointer['state_hash'] and sim.account.snapshot()==snapshot['account'] and all(np.array_equal(a,b) for a,b in zip(sim.minute_chunks,chunks,strict=True)),'Original account/journal/scheduler state restoration differs');return sim,pointer


def run(state,arm,commit):
    source_check(state);fractions,budgets,gate=check(state,arm);planpath=PUBLIC/(arm+'.json');plan=read(planpath);require(len(commit)==40 and subprocess.check_output(['git','show',commit+':'+planpath.relative_to(REPO).as_posix()],cwd=REPO)==planpath.read_bytes(),'Published frozen Q4 execution plan required')
    require(plan['authorization']=='USER_AUTHORIZED_EXACTLY_FOUR_FROZEN_Q4_NATIVE92_WALLETS' and plan['mapping_preflight']==gate and plan['adapter_contract_sha256']==sha(PUBLIC/'ADAPTER_CONTRACT.json'),'Exact authorized request/mapping/adapter binding required')
    from scripts.investment import perpetual_directional as old
    from scripts.investment.resumable_perpetual import NativeDailySimulator
    from quant.bybit_isolated_account import BybitIsolatedAccount
    contract=read(PUBLIC/'ADAPTER_CONTRACT.json');output=state/'q4-native92'/arm;ledger=state/'q4-native92-ledger'/gate['request_sha256'];binding=dict(arm=arm,plan_commit=commit,plan_sha256=sha(planpath),adapter_contract_sha256=sha(PUBLIC/'ADAPTER_CONTRACT.json'),request_sha256=gate['request_sha256'],engine_sha256=ENGINE_SHA,execution_calendar=EXECUTION_CAL)
    if output.exists():
        require(read(output/'BINDING.json')==binding and read(ledger)['binding']==binding and read(ledger)['status'] in ('RUNNING','INTERRUPTED_RESUMABLE','COMPLETE_CONDITIONAL_ACCOUNT'),'Only reserved uncompleted original account can resume')
        sim,pointer=restore(output/'recovery',binding,window(state));started=read(output/'STARTED.json');prior=pointer['elapsed_seconds'];count=pointer['completed_decisions'];print(json.dumps(dict(status='RESUMED_EXACT_ORIGINAL_ACCOUNT',arm=arm,completed_decisions=count)),flush=True)
    else:
        ledger.parent.mkdir(parents=True,exist_ok=True)
        with ledger.open('x') as f:f.write(json.dumps(dict(status='RUNNING',binding=binding))+'\n');f.flush();os.fsync(f.fileno())
        output.mkdir(parents=True,exist_ok=False);write_once(output/'BINDING.json',encoded(binding));sim=NativeDailySimulator(window(state),'LONG_SHORT',old.COSTS[0],dict(id='RAW_AS_FRACTION',scale=1.),account_factory=BybitIsolatedAccount,persist_cash_close=True,final_day_target_zero=True)
        require(float(sim.account.nav())==10000 and sim.previous_quote is None and all(p.quantity==0 for p in sim.account.positions.values()) and old.COSTS[0]==contract['cost'],'Original fresh cash/start/cost required');sim.budget=[1.]+[0.]*5;prior=0.;count=0
        started=dict(arm=arm,started_UTC=datetime.now(UTC).isoformat(),plan_commit=commit,limits=contract['limits'],request_sha256=gate['request_sha256'],producer_commit=PRODUCER,data_commit=DATA);write_once(output/'STARTED.json',encoded(started));write_once(output/'REQUEST_GATE.json',encoded(gate));save_checkpoint(output/'recovery',sim,binding,0.)
    status='RUNNING';error=None;start=time.monotonic()
    def interrupted(*args):raise KeyboardInterrupt('Resume original durable account')
    def expired(*args):raise TimeoutError('600-second cumulative native Q4 cap')
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,max(.001,600-prior))
    try:
        for i in range(count,92):
            require(shutil.disk_usage(output).free>=15*2**30,'15GiB reserve required');sim.budget=budgets[i].tolist();require(sim.advance_day(dict(zip(base.frozen.SYMBOLS,fractions[i],strict=True)))['completed'],'Financial failure must stop');save_checkpoint(output/'recovery',sim,binding,prior+time.monotonic()-start)
            if (i+1)%10==0 or i==91:print(json.dumps(dict(arm=arm,completed_decisions=i+1,total_decisions=92,NAV=float(sim.account.nav()))),flush=True)
        require(sim.rows_written==131046 and all(p.quantity==0 for p in sim.account.positions.values()),'Original five-attempt terminal must achieve paid flat; no additional day or forced fill');status='COMPLETE_CONDITIONAL_ACCOUNT'
    except KeyboardInterrupt as ex:status='INTERRUPTED_RESUMABLE';error=dict(type=type(ex).__name__,message=str(ex));raise
    except BaseException as ex:
        status='FAILED_STOP_PREFIX_RETAINED';error=dict(type=type(ex).__name__,message=str(ex));atomic(output/'FAILED_ORIGINAL_SNAPSHOT.json.gz',gzip.compress(encoded(sim.snapshot()),compresslevel=1,mtime=0));raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);receipt=started|dict(status=status,error=error,finished_UTC=datetime.now(UTC).isoformat(),elapsed_seconds=prior+time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,completed_minutes=sim.rows_written,original_engine_sha256=ENGINE_SHA,execution_calendar=EXECUTION_CAL,terminal=terminal_contract());atomic(output/'EXECUTION.json',encoded(receipt));atomic(ledger,encoded(dict(status=status,binding=binding)))
    if not (output/'account/summary.json').exists():
        temp=output/('account_save_'+str(time.time_ns()));saved=old.save_case(sim.result(),temp);write_once(temp/'summary.json',encoded(saved['summary']));require(not (output/'account').exists(),'Preserve any partial publication separately');os.replace(temp,output/'account')
    from pyarrow.parquet import read_table
    require(np.array_equal(read_table(output/'account/targets.parquet')['target_weight'].to_numpy().reshape(92,5),fractions),'Original saved targets differ from source mapped requests')
    from verify_q4_native92 import verify
    audit=verify(output,state);write_once(output/'INDEPENDENT_AUDIT.json',encoded(audit));recovered,pointer=restore(output/'recovery',binding,window(state));require(recovered.state_hash()==sim.state_hash() and recovered.account.snapshot()==sim.account.snapshot() and np.array_equal(np.concatenate(recovered.minute_chunks),np.concatenate(sim.minute_chunks)),'Full original final account recovery differs')
    write_once(output/'RECOVERY_AUDIT.json',encoded(dict(status='PASS_ORIGINAL92_PARTIAL_TERMINAL_FULL_SNAPSHOT_RECOVERY',state_hash=sim.state_hash(),completed_decisions=92,completed_minutes=131046,account_snapshot_exact=True,minute_journal_bit_exact=True,wallet_advanced_after_restore=False,terminal_paid_flat=True)));atomic(ledger,encoded(dict(status='COMPLETE_AND_AUDITED',binding=binding)));print(json.dumps(dict(status='COMPLETE_AND_AUDITED',arm=arm,net_PnL=read(output/'account/summary.json')['net_PnL'],terminal=audit['terminal'])),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('prepare','check','run'));p.add_argument('--state',type=Path,required=True);p.add_argument('--arm',choices=tuple(ARMS));p.add_argument('--plan-commit');a=p.parse_args()
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','POLARS_MAX_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6000000000,6000000000));resource.setrlimit(resource.RLIMIT_CPU,(600,600))
    def offline(*args,**kwargs):raise RuntimeError('Frozen Q4 native runner forbids network')
    socket.create_connection=offline;socket.socket.connect=offline
    if a.command=='prepare':print(json.dumps(prepare(a.state)),flush=True)
    elif a.command=='check':source_check(a.state);print(json.dumps(check(a.state,a.arm)[2]),flush=True)
    else:
        require(a.arm is not None and a.plan_commit is not None,'Explicit frozen arm and public plan commit required');locks=a.state/'q4-native92-locks';locks.mkdir(exist_ok=True)
        with (locks/a.arm).open('a') as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);run(a.state,a.arm,a.plan_commit)
