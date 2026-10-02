"""Frozen independent RSI2 six-ledger checker; official kernel/rawhook, no engine replay."""
from pathlib import Path
from datetime import UTC,date,datetime
import hashlib,json,os,sys,resource,traceback,math,ast,importlib.util
from types import SimpleNamespace
import xml.etree.ElementTree as ET
import numpy as np
import polars as pl
ROOT=Path('/mnt/d/codex/coin');STATE=Path(__file__).parent.resolve()
MIN=60_000_000;HOUR=60*MIN;DAY=24*HOUR;SYMS=('BTCUSDT','ETHUSDT')
STRATEGY='COIN_JESSE_RSI2_1H_SPOT_ADAPTER'
REUSE='docs/archive/PUBLIC_DONCHIAN_HYBRID_NATIVE_SIX_LEDGER_CHECKER_20261002_V1.py'
REUSE_SHA='d79bc8a156987786e190e606d27a1656dc059137e739cbc919780e7b12e77135'
FINANCIAL_SHA='4b6e0514898676ea2fc1a75881917b2cb480e5f2f0501621008e13617924d04f'
OUT=ROOT/'reports/fast_research/PUBLIC_RSI2_NATIVE_SIX_LEDGER_INDEPENDENT_AUDIT_20261002_V1.json'
CASES={
 '122':('PUBLIC_RSI2_BYBIT_122D_ACTUAL_20261002_V1.json','PUBLIC_RSI2_BYBIT_122D_V1.json',None,'CONT122','2025-08-01','2025-12-01'),
 '90':('PUBLIC_RSI2_BYBIT_90D_ACTUAL_20261002_V1.json','PUBLIC_RSI2_BYBIT_90D_V1.json',None,'CONT90','2025-12-01','2026-03-01')}
PINS={
 'scripts/investment/public_rsi2_adapter.py':'9963316a9dab481c9c0de179772680800d2d7cf65cfaadaede9b15d470c2c722',
 'scripts/investment/public_rsi2_indicator.py':'417b9044ff1b2cb32326d4648d1239ebc2b7f872bf7da123901b0fe1bf0a2315',
 'scripts/investment/public_donchian_hybrid.py':'80e4b24319becacefb0d6c9551473e3d4214cf3167ae45f5ac8ff7f559c27d68',
 'scripts/investment/compare_simple_strategies.py':'3dfa0e3176791980de51e5bc990b1998f93eb24c02bdc1261a074eab92fb52f1',
 'scripts/investment/bybit_spot_adapter.py':'8c8852bf70813ada5720c210f50c9038a5ecaadee1b4f38b77a71aa9e8b038ca',
 'scripts/research_v8/public_donchian_adapter.py':'169d7ba6ebde24be5ce4730c5e741ed281a0155e4cadc22f1bb2bedccb4093c2',
 'tests/test_public_rsi2_native_integration.py':'2c14c528874a9979fce20c1a1074f1e8b477fd772d168fa49cf273ffa02bdc45',
 'tests/test_investment_bybit_pipeline.py':'412d0638a48673fc1d0209a9e70cbbcf50d6b2d1252f0f813ff7465c0f90418c'}
CONTROL_AUDIT='reports/fast_research/BYBIT_SPOT_NATIVE_FEE_SIX_LEDGER_COMPOSITE_AUDIT_20261002_V1.json'
CONTROL_AUDIT_SHA='70fc1568e51019d2c13abb42eb7fd844a58f9c39e77f0ff27278f1b5f7d94c6f'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def need(ok,msg):
    if not bool(ok):raise ValueError(msg)
def close(a,b,atol=1e-6):return np.allclose(a,b,rtol=0,atol=atol,equal_nan=False)
def json_scalar(x):
    if isinstance(x,np.generic):return x.item()
    raise TypeError(type(x).__name__)
def frame_sha(frame):return hashlib.sha256(json.dumps(frame.to_dicts(),sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def stamp(text):return int(datetime.combine(date.fromisoformat(text),datetime.min.time(),UTC).timestamp())*1_000_000
def task_for(binding):
    p=Path('/home/xflops/coin-state/task-progress')/('task-'+binding['task_id']+'.json')
    t=read(p);need(t['id']==binding['task_id'] and t['status']=='completed' and t['exit_code']==0 and t['pid']>0 and t['start_ticks']>0,'Actual completed0 task binding')
    return {'path':str(p),'sha256':sha(p),'task':t}
def monthly_intervals(start,end):
    cursor=datetime.fromtimestamp(start/1_000_000,UTC);rows=[]
    while int(cursor.timestamp())*1_000_000<end:
        after=datetime(cursor.year+(cursor.month==12),cursor.month%12+1,1,tzinfo=UTC)
        lower=max(start,int(cursor.timestamp())*1_000_000);upper=min(end,int(after.timestamp())*1_000_000)
        rows.append((cursor.strftime('%Y-%m'),lower,upper));cursor=after
    return rows
def shared(d):
    return {k:v for k,v in d.items() if k.startswith(('src/','scripts/','tests/','environments/','third_party/')) or k in ('protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json','protocols/BYBIT_SPOT_RECEIVED_ASSET_ADAPTER_V1.json')}
def kernel_context():
    """Load the pinned official wheel directly, without either target adapter."""
    vendor=ROOT/'third_party/jesse_example_rsi2'
    install_path=ROOT/'reports/fast_research/RSI2_OFFICIAL_KERNEL_DEPENDENCY_INSTALL_20261002_V3.json'
    semantic_path=ROOT/'reports/fast_research/RSI2_OFFICIAL_KERNEL_SEMANTICS_20261002_V1.json'
    need(sha(install_path)=='8758bd7d9c951f0e652ac200e295d6ba2ff163b02980cfde97e69daed48ef27c','Actual official install receipt pin')
    need(sha(semantic_path)=='3be76ff10b74642f1eca7625d2d7a14911fae5eb5527071d442e485c9a9b9469','Actual official semantic receipt pin')
    installed=read(install_path);semantic=read(semantic_path)
    need(installed['status']=='PASS_OFFICIAL_FIXED_RSI_CODE_WHEEL_INSTALL_NOT_YET_SEMANTIC_ACCEPTANCE' and installed['installer_exit_code']==0 and installed['base_environment_unmodified'],'Official install readiness')
    need(semantic['status']=='PASS_OFFICIAL_RSI_KERNEL_SYNTHETIC_SEMANTICS' and semantic['passed']==6 and semantic['failed']==0 and all(c['status']=='PASS' for c in semantic['cases']) and not semantic['market_inputs_read'] and not semantic['locked_consumed'],'Official six fixed synthetic semantics')
    need({p:sha(ROOT/p) for p in semantic['binding']['source_sha256']}==semantic['binding']['source_sha256'],'Semantic source pins unchanged')
    install_task=task_for(installed['binding']);semantic_task=task_for(semantic['binding'])
    binding_path=vendor/'INSTALLED_KERNEL_BINDING_20261002_V1.json'
    need(sha(binding_path)=='4035a57485f63bc7e4470f91b7fdea950e3b99a07638e959d32013b705f23b2a','Installed kernel binding pin')
    b=read(binding_path);target=Path(b['target'])
    need(b==installed['installed_binding'] and b['package_version']=='1.3.0' and target==Path('/home/xflops/coin-state/rsi2-kernel-jesse-rust-1.3.0-cp312-v1') and b['wheel_sha256']=='65c0e9edd3af5397642ca417da2ef7c23f311d6fa2bf6a2d46c729f656528cee' and b['sdist_sha256']=='9609ec6b74aeccaf2889f8bdc5551cdc0fe0d093e0c657f8b1629f7dbc1600e1','Official exact wheel/sdist version')
    need(all(sha(target/p)==v['sha256'] and (target/p).stat().st_size==v['bytes'] for p,v in b['installed_files'].items()),'All actual installed artifact bytes')
    need(b['original_sources']['rsi_kernel_original.rs']['sdist_member']=='jesse_rust-1.3.0/src/oscillators.rs' and sha(vendor/'rsi_kernel_original.rs')=='25a07d9c665a30bd2c56606b07b9d83fd59b67c8b1771bf0ccae2c3f0ca6b208','Exact official RSI recurrence member')
    need('jesse_rust' not in sys.modules and 'jesse_rust.jesse_rust' not in sys.modules,'Independent direct official import; no preloaded adapter module')
    module_spec=importlib.util.spec_from_file_location('jesse_rust',target/'jesse_rust/__init__.py',submodule_search_locations=[str(target/'jesse_rust')])
    package=importlib.util.module_from_spec(module_spec);sys.modules['jesse_rust']=package;module_spec.loader.exec_module(package)
    extension=sys.modules['jesse_rust.jesse_rust'];need(Path(extension.__file__).resolve()==(target/b['extension_relative_path']).resolve() and sha(extension.__file__)=='4ca1bc482f53650842817901ce8a1199d302db93242949fdaeffcb9384c8b2eb','Actual mature extension identity')
    class Context:
        def __init__(self):self.vars={}
    def official_scalar(candles,period=2):
        source=np.asarray(candles[-240:,2],dtype=np.float64)
        need(len(source)==240 and np.isfinite(source).all(),'Raw hook consumes exactly 240 closed finite prices')
        return np.float64(package.rsi_last(source,int(period)))
    namespace={'Strategy':Context,'utils':None,'ta':SimpleNamespace(sma=lambda c,p:np.mean(c[-p:,2]),rsi=official_scalar)}
    nodes=[n for n in ast.parse((vendor/'rsi2_original.py').read_text()).body if isinstance(n,ast.ClassDef) and n.name=='RSI2']
    need(len(nodes)==1 and sha(vendor/'rsi2_original.py')=='fd463da53b6ac78138a0886268f654973daa569dd2094c6aa96796a8a5015f70','One exact public RSI2 class')
    exec(compile(ast.Module(nodes,type_ignores=[]),str(vendor/'rsi2_original.py'),'exec'),namespace)
    return package,namespace['RSI2'],{'install_receipt_sha256':sha(install_path),'semantic_receipt_sha256':sha(semantic_path),'install_actual_task':install_task,'semantic_actual_task':semantic_task,'installed_binding_sha256':sha(binding_path),'extension_sha256':sha(extension.__file__),'official_raw_hook_AST_sha256':hashlib.sha256(ast.dump(nodes[0],include_attributes=False).encode()).hexdigest(),'package_version':'1.3.0','scalar_window':240,'seed':'First two price changes arithmetic mean then Wilder recurrence per official Rust; flat avg_loss==0 gives100.','custom_RSI_recurrence_implemented':False}

def verify_rsi2_target(fm,intent,receipt,calendar,kernel,Rules):
    """Raw original hook and official scalar kernel; no fixed_targets call."""
    need(receipt['strategy_id']==STRATEGY and receipt['paired_comparison_allowed'] and not receipt['warmup_failed'],'RSI2 paired target ready')
    need(receipt['timeframe_minutes']==60 and receipt['rsi_period']==2 and receipt['entry_rsi_threshold']==10 and receipt['entry_trend_sma_period']==200 and receipt['exit_sma_period']==5 and receipt['official_scalar_candle_window']==receipt['continuous_availability_guard_bars']==240,'Fixed RSI2 recipe and complete initialization window')
    need(receipt['signal_hooks_reused_unmodified'] and receipt['long_only'] and not receipt['native_Jesse_engine_replicated'] and not receipt['upstream_balance_sizing_called'] and receipt['model_fits']==0,'Public long-only hook port scope')
    need(receipt['same_stamp_priority']=='HELD_EXIT_FIRST_NO_REENTRY' and receipt['entry_eligibility_restores']=='NEXT_NEW_CLOSED_1H_BAR_NO_EXTRA_COOLDOWN' and receipt['missing_policy']=='WHOLE_PAIRED_FOLD_NOT_EVALUABLE_NO_EXECUTION' and receipt['rsi_initialization']=='OFFICIAL_SCALAR_KERNEL_ON_EACH_CLOSED_240_BAR_WINDOW','Fixed RSI2 priority/missing/scalar semantics')
    need(receipt['calendar_sha256']==hashlib.sha256(calendar.tobytes()).hexdigest() and receipt['decision_count']==len(calendar) and intent.height==len(calendar)*2,'RSI2 complete minute decision calendar')
    need(receipt['raw_strategy_sha256']=='fd463da53b6ac78138a0886268f654973daa569dd2094c6aa96796a8a5015f70','Target original hook identity')
    for p,d in receipt['source_hashes'].items():need(sha(ROOT/p)==d,'Target source hash')
    need(all(receipt['source_hashes'].get(p)==d for p,d in PINS.items() if p in ('scripts/investment/public_rsi2_adapter.py','scripts/investment/public_rsi2_indicator.py','scripts/research_v8/public_donchian_adapter.py','scripts/investment/public_donchian_hybrid.py')),'Target source identity')
    lower=int(fm['open_us'].min());end=int(fm['close_us'].max());entries=exits=events=0
    need(lower%DAY==0 and calendar[0]%DAY==0 and end%DAY==0,'UTC aligned signal input')
    for symbol in SYMS:
        one=intent.filter(pl.col('symbol')==symbol).sort('decision_us')
        need(one.height==len(calendar) and np.array_equal(one['decision_us'].to_numpy(),calendar),'One intent per symbol per minute')
        rows=fm.filter(pl.col('symbol')==symbol).sort('open_us');need(rows.height%60==0,'Complete hourly source')
        closes=rows['close'].to_numpy().reshape(-1,60)[:,-1]
        high=rows['high'].to_numpy().reshape(-1,60).max(axis=1);low=rows['low'].to_numpy().reshape(-1,60).min(axis=1)
        available=rows['available_us'].to_numpy().reshape(-1,60).max(axis=1);stamps=lower+np.arange(1,len(closes)+1,dtype=np.int64)*HOUR
        need(np.array_equal(available,stamps),'Closed candle availability exclusive UTC hour')
        candles=np.zeros((len(closes),6));candles[:,0]=stamps//1000;candles[:,2]=closes;candles[:,3]=high;candles[:,4]=low
        expected_weights=np.zeros(len(calendar));expected_reasons=np.full(len(calendar),'RSI2_FLAT',dtype=object);held=False;rules=Rules()
        need(rules.vars=={'fast_sma_period':5,'slow_sma_period':200,'rsi_period':2,'rsi_ob_threshold':90,'rsi_os_threshold':10},'Original fixed hook parameters')
        for k,decision in enumerate(calendar):
            idx=int((decision-lower)//HOUR-1)
            need(idx>=239 and stamps[idx]==decision//HOUR*HOUR and np.all(available[idx-239:idx+1]<=decision) and np.all(np.diff(stamps[idx-239:idx+1])==HOUR),'All 240 actually consumed bars contiguous and available')
            exited=entered=False
            if decision%HOUR==0:
                window=candles[idx-239:idx+1];source=np.asarray(window[:,2],dtype=np.float64)
                rsi_value=float(kernel.rsi_last(source,2));need(math.isfinite(rsi_value) and 0<=rsi_value<=100,'Official initialized RSI2 value')
                rules.candles=window;rules.price=float(closes[idx]);rules.is_long=held;rules.is_short=False
                direct_exit=held and rules.price>source[-5:].mean();direct_entry=rules.price>source[-200:].mean() and rsi_value<=10
                liquidation=[];rules.liquidate=lambda:liquidation.append(True);rules.update_position()
                need(bool(liquidation)==direct_exit and bool(rules.should_long())==direct_entry,'Original raw hook differs from independent official-kernel/mean expression')
                if direct_exit:held=False;exited=True;exits+=1
                if not held and not exited and direct_entry:held=True;entered=True;entries+=1
                events+=1
            expected_weights[k]=.3 if held else 0.
            expected_reasons[k]='RSI2_PUBLIC_1H_EXIT_NO_SAME_STAMP_REENTRY' if exited else ('RSI2_PUBLIC_1H_ENTRY' if entered else ('RSI2_LONG' if held else 'RSI2_FLAT'))
        expected_weights[-1]=0.;expected_reasons[-1]='COMMON_TERMINAL_EXIT_INTENT_NEEDS_FEASIBLE_FILL'
        need(np.array_equal(one['target_weight'].to_numpy(),expected_weights),'Saved RSI2 minute intents differ from official scalar kernel/raw hook')
        need(np.array_equal(one['reason'].to_numpy(),expected_reasons),'Saved RSI2 event/reason chronology differs')
    return {'independent_saved_input_rule_arithmetic':True,'raw_original_hooks_compiled_without_body_changes':True,'direct_official_rsi_last_calls':True,'fixed_targets_called':False,'full_calendar_minutes':len(calendar),'closed1h_events_across_symbols':events,'entries_across_symbols':entries,'closed1h_exit_events_across_symbols':exits,'strict_causal_initialization_bars':240,'kernel_seed_and_flat_branch_reused':True,'full_prefix_scalar_substituted':False,'source_end_close_is_valuation_only_not_future_signal':True,'max_signal_decision_us':int(calendar[-1])}
def check_period(case,audit,kernel,Rules):
    label=case['period'];name,protocol,protocol_sha,fold_id,start_text,end_text=CASES[label]
    expected_sha=case['report_sha256'];session=case['actual_host_session_id'];days=int(label);protocol_sha=case['protocol_sha256']
    actual_path=ROOT/'reports/fast_research'/name;need(sha(actual_path)==expected_sha,'Frozen actual report SHA')
    r=read(actual_path);binding=read(Path(r['run_dir'])/'RUN_BINDING.json');actual_task=task_for(binding)
    need(binding['task_id']==case['actual_task_id'],'Explicit actual task selector')
    spec=read(ROOT/'protocols'/protocol);hashes=binding['source_hashes']
    need(sha(ROOT/'protocols'/protocol)==protocol_sha==binding['protocol_sha256'],'Protocol prebound before market result')
    need(binding==r['binding'] and sha(Path(r['run_dir'])/'RUN_BINDING.json')==r['run_binding_sha256'],'Actual RUN_BINDING')
    need(r['status']=='COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING' and r['source_bytes_unchanged'] and r['completed_ledgers']==3 and r['all_planned_ledgers_complete'],'Complete actual three accounts')
    need(binding['fits']==r['market_models_fit']==0 and not r['locked_consumed'] and r['orders_sent']==0 and r['candidate_status']=='NO_QUALIFIED_CANDIDATE','Scope exceeds historical screening')
    need(binding['planned_ledgers']==spec['planned_ledgers']==3 and binding['all_folds']==spec['folds'] and binding['strategies']==spec['strategy_ids']==[STRATEGY],'Fixed three RSI2 recipes')
    need(spec['folds']==[{'id':fold_id,'period_start':start_text,'period_end_exclusive':end_text}] and len(r['folds'])==1 and spec['warmup_days']==31 and not spec.get('reused_target_inputs'),'Explicit new RSI2 period; no old target reuse')
    need({p:sha(ROOT/p) for p in hashes}==hashes and all(sha(Path(r['run_dir'])/'source-snapshot'/p)==d for p,d in hashes.items()) and all(hashes.get(p)==d for p,d in spec['frozen_sources'].items()) and all(hashes.get(p)==d for p,d in PINS.items()),'Current/snapshot frozen source bindings')
    tiny_path=ROOT/spec['required_smoke_receipt'];tiny=read(tiny_path);tb=read(Path(tiny['run_dir'])/'RUN_BINDING.json')
    need(tb==tiny['binding'] and sha(Path(tiny['run_dir'])/'RUN_BINDING.json')==tiny['run_binding_sha256'] and sha(tiny_path)==r['accepted_smoke_sha256'],'Actual new integration receipt binding')
    need(tiny['status']=='PASS_SIMPLE_COMPARISON_SYNTHETIC_NOT_MARKET_RESULT' and shared(tb['source_hashes'])==shared(hashes) and tiny['registration_start']['hyperparameters']==spec['common_config'] and tiny['registration_start']['cost_assumptions']==spec['costs'] and tiny['registration_start']['thresholds']==spec['strategy_rules'] and spec['smoke_test_path']=='tests/test_public_rsi2_native_integration.py','Exact new target/native code and economics smoke')
    x=ET.parse(Path(tiny['run_dir'])/'junit.xml').getroot();counts={k:sum(int(s.get(k,0)) for s in x.iter('testsuite')) for k in ('tests','failures','errors','skipped')}
    need(counts=={'tests':1,'failures':0,'errors':0,'skipped':0} and sha(Path(tiny['run_dir'])/'junit.xml')==tiny['junit_sha256'],'One actual new integration case; old greens not rerun')
    deriv=r['fee_derivation']
    need(deriv['derived_AST_SHA256']=='39ffd9142be81285b3a6b460c73b1c7799c7621a1c34a2f1faa845d290608b73' and sha(deriv['derived_source_path'])==deriv['derived_source_file_sha256']=='a33c4f392c033d44224be5f64a42456b529e973d9af0925c8a454043f2762a8f' and sha(deriv['receipt_path'])==deriv['receipt_sha256'],'Frozen sixteen-change native fee implementation')
    need(r['fee_settlement']==spec['fee_settlement']=='BYBIT_SPOT_RECEIVED_ASSET_V1' and r['fee_profile_sha256']==spec['fee_profile_sha256']=='d6c1e2f5b25dabf4d088edfbccbc35d7154684287ff477c2fc16a14ee5f96b3f','Fixed global Spot Non-VIP received-asset profile')
    source_path=Path(r['minute_source']['path']);need(source_path==Path(r['run_dir'])/'shared_source_minutes.parquet' and sha(source_path)==r['minute_source']['sha256'],'Actual derivative Parquet file SHA')
    minutes=pl.read_parquet(source_path)
    need(minutes.height==r['minute_source']['rows']==2*(days+31)*1440 and r['minute_source']['invalid_minutes']==0 and set(minutes['symbol'].unique().to_list())==set(SYMS),'Complete paired source row count')
    need(minutes['minute_valid'].null_count()==0 and minutes['minute_valid'].all() and minutes['valid_day'].null_count()==0 and minutes['valid_day'].all() and minutes['missing_reason'].null_count()==minutes.height,'No missing/unknown source admitted')
    need(all(minutes[p].null_count()==0 and minutes.schema[p]==pl.Int64 for p in ('open_us','close_us','available_us')) and np.array_equal(minutes['close_us'].to_numpy(),minutes['open_us'].to_numpy()+MIN) and np.array_equal(minutes['available_us'].to_numpy(),minutes['close_us'].to_numpy()),'Complete past-only minute availability')
    reference=spec['reused_minute_input'];parent=read(ROOT/reference['report_path']);old_source=Path(reference['path'])
    need(sha(ROOT/reference['report_path'])==reference['report_sha256'] and parent['status']=='COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING' and parent['source_bytes_unchanged'] and parent['all_planned_ledgers_complete'] and sha(old_source)==reference['sha256']==parent['minute_source']['sha256'] and parent['source_receipt_sha256']==spec['source_receipt_sha256'],'Accepted saved input provenance')
    original=pl.read_parquet(old_source);need(original.equals(minutes) and original.schema==minutes.schema,'Exact old derivative source values and schema');del original
    audit['period_bindings'].append({'label':label,'report_path':str(actual_path),'report_sha256':expected_sha,'actual_host_session_id':session,'actual_task':actual_task,'actual_smoke_task':task_for(tb),'smoke_path':str(tiny_path),'smoke_sha256':sha(tiny_path),'fresh_synthetic_cases':counts,'verified_source_hashes':hashes,'original_derivative_parquet_sha256':reference['sha256'],'current_derivative_parquet_sha256':sha(source_path),'logical_original_values_and_schema_preserved':True,'protocol_sha256':protocol_sha,'source_receipt_sha256':spec['source_receipt_sha256'],'derivation_AST_sha256':deriv['derived_AST_SHA256'],'derivation_source_sha256':deriv['derived_source_file_sha256']})
    seen=set()
    for fold in r['folds']:
        fc=next(f for f in spec['folds'] if f['id']==fold['fold']);start,end=stamp(fc['period_start']),stamp(fc['period_end_exclusive'])
        need(fold['start_us']==start and fold['end_us']==end and fold['status']=='COMPLETE_PROXY_COMPARISON' and len(fold['results'])==3,'Fold/calendar scope')
        fm=minutes.filter(pl.col('open_us').is_between(start-31*DAY,end,closed='left'));input_path=Path(fold['minute_input_path'])
        need(input_path==Path(r['run_dir'])/(fold['fold']+'-minute-input.arrow') and sha(input_path)==fold['minute_input_sha256'] and fold['minute_input_format']=='IMMUTABLE_ARROW_IPC_FILE_READ_BEFORE_SIGNALS_AND_EXECUTION','Exact runtime physical Arrow file binding')
        actual_fm=pl.read_ipc(input_path,memory_map=False)
        need(fm.equals(minutes) and actual_fm.equals(fm) and actual_fm.schema==fm.schema and fm.height==2*(days+31)*1440,'Same complete physical IPC/Parquet input values/schema');fm=actual_fm
        audit['runtime_inputs'].append({'fold':fold['fold'],'arrow_path':str(input_path),'arrow_sha256':sha(input_path),'parquet_sha256':sha(source_path),'logical_values_and_schema_equal':True,'physical_file_hash_checked':True,'IPC_reserialization_performed':False})
        per={}
        for symbol in SYMS:
            m=fm.filter(pl.col('symbol')==symbol);need(np.array_equal(m['open_us'].to_numpy(),np.arange(start-31*DAY,end,MIN,dtype=np.int64)),'Complete warmup/evaluation UTC minute grid')
            per[symbol]=m.filter(pl.col('open_us')>=start)
        close_times=per[SYMS[0]]['close_us'].to_numpy();calendar=np.arange(start,end,MIN,dtype=np.int64);target_bound={}
        d=Path(r['run_dir'])/(fold['fold']+'-'+STRATEGY);targets=pl.read_parquet(d/'targets.parquet');intent=pl.read_parquet(d/'intent_calendar.parquet');target_receipt=read(d/'target_receipt.json')
        need(target_receipt['targets_sha256']==frame_sha(targets),'Causal target logical value digest')
        target_math=verify_rsi2_target(fm,intent,target_receipt,calendar,kernel,Rules)
        reconstructed_rows=[]
        for symbol in SYMS:
            one=intent.filter(pl.col('symbol')==symbol).sort('decision_us');times=one['decision_us'].to_numpy();w=one['target_weight'].to_numpy()
            need(np.array_equal(one['available_us'].to_numpy(),times) and np.array_equal(one['comparison_order_eligible_us'].to_numpy(),times+MIN) and np.array_equal(one['preserved_v8_intent_earliest_order_us'].to_numpy(),times+5_000_000),'Intent availability and distinct preserved order metadata')
            need(np.isfinite(w).all() and np.all((w==0)|(w==.3)) and w[-1]==0,'Fixed long-only hybrid intent sizing')
            changed=np.r_[True,np.diff(w)!=0];reconstructed_rows.extend({'available_us':int(t),'symbol':symbol,'target_weight':float(v)} for t,v in zip(times[changed],w[changed]))
        reconstructed=pl.DataFrame(reconstructed_rows).sort(['available_us','symbol']);need(targets.sort(['available_us','symbol']).equals(reconstructed),'Compressed execution targets differ from full causal intent calendar')
        target_bound[STRATEGY]={'target_sha256':sha(d/'targets.parquet'),'intent_sha256':sha(d/'intent_calendar.parquet'),'receipt_sha256':sha(d/'target_receipt.json')}
        audit['target_causality'].append({'fold':fold['fold'],**target_math,**target_bound[STRATEGY]})
        for item in fold["results"]:
            strategy,spread=item["strategy"],item["spread_bps"]
            key=(fold["fold"],strategy,spread)
            need(key not in seen and strategy in spec["strategy_ids"] and spread in (2,4,8),"Missing/duplicate recipe")
            seen.add(key)
            d=Path(item["directory"])
            need(d==Path(r["run_dir"])/(fold["fold"]+"-"+strategy)/("spread"+str(spread)),"Explicit ledger path")
            need(set(item["artifacts"])=={"daily_nav.parquet","trades.parquet","orders.parquet","round_trips.parquet","minute_nav_inventory.parquet","config_and_summary.json"},"Complete ledger artifacts")
            for name,b in item["artifacts"].items():
                need(sha(d/name)==b["sha256"] and (d/name).stat().st_size==b["bytes"],"Ledger artifact changed")
            book=read(d/"config_and_summary.json")
            cfg=book["config"]
            summary=book["summary"]
            published=item["summary"]
            expected_cfg={"initial_cash":10000.,"fee_bps":10.,"half_spread_bps":spread/2,"slippage_bps":4.,
                "fee_multiplier":1.,"slippage_multiplier":1.,"latency_minutes":1,"start_us":start,"end_us":end,
                "max_weight":.3,"max_gross":.6,"target_annual_vol":.1,"vol_window_days":30,"min_vol_days":20,
                "participation_rate":.001,"max_order_wait_minutes":5,"liquidate_at_end":True,"min_notional":10.,
                "lot_step_by_symbol":{"BTCUSDT":.00001,"ETHUSDT":.0001}}
            need(cfg==expected_cfg,"Actual parameters changed")
            need(all(published[k]==v for k,v in summary.items()),"Published base summary differs")
            fills=pl.read_parquet(d/"trades.parquet").sort("execution_us",maintain_order=True)
            inventory=pl.read_parquet(d/"minute_nav_inventory.parquet")
            daily=pl.read_parquet(d/"daily_nav.parquet")
            orders=pl.read_parquet(d/"orders.parquet")
            need(np.array_equal(inventory["close_us"].to_numpy(),close_times) and inventory.height==days*1440,"Full minute inventory")
            t=fills["execution_us"].to_numpy()
            sign=np.where(fills["side"].to_numpy()=="buy",1.,-1.)
            need(fills["side"].is_in(["buy","sell"]).all() and fills["symbol"].is_in(SYMS).all(),"Illegal fill identity")
            q=fills["quantity"].to_numpy()
            mid=fills["mid_price"].to_numpy()
            fill_price=fills["fill_price"].to_numpy()
            notionals=fills["notional"].to_numpy()
            buy=sign>0
            expected_fee_units=np.where(buy,q*.001,notionals*.001)
            fees=np.where(buy,expected_fee_units*mid,expected_fee_units)
            position_delta=np.where(buy,q-q*.001,-q)
            cash_delta=np.where(buy,-notionals,notionals-notionals*.001)
            need(close(fills["gross_quantity"].to_numpy(),q,1e-12)
                and np.array_equal(fills["fee_asset"].to_numpy(),np.where(buy,np.char.replace(fills["symbol"].to_numpy().astype(str),"USDT",""),"USDT"))
                and close(fills["fee_amount"].to_numpy(),expected_fee_units,1e-10)
                and close(fills["fee_USDT_mid"].to_numpy(),fees,1e-8)
                and close(fills["position_delta"].to_numpy(),position_delta,1e-12)
                and close(fills["cash_delta"].to_numpy(),cash_delta,1e-8),"Native asset settlement formula")
            extra=q*np.abs(fill_price-mid)
            need(np.isfinite(q).all() and np.all(q>0) and close(notionals,q*fill_price)
                and close(fills["fee"].to_numpy(),fees) and close(fills["execution_cost"].to_numpy(),extra),"Actual fill costs")
            need(close(fill_price,mid*(1+sign*(spread/2+4)/10000)),"Cost scenario fill proxy")
            if len(t):
                sig=fills["signal_us"].to_numpy()
                eligible=((sig+MIN-1)//MIN+1)*MIN+1
                need(np.all(t>=eligible)&np.all(t%MIN==1)&np.all(t<end),"Future/period fill")
                cash_steps=10000.+np.cumsum(cash_delta)
                need(close(cash_steps,fills["cash_after"].to_numpy(),1e-7),"Sequential cash identity")
            else:
                cash_steps=np.empty(0)
            counts=np.searchsorted(t,close_times,side="right")
            def acc(v): return np.r_[0.,np.cumsum(v)][counts]
            cash=10000.+acc(cash_delta)
            gross_cash=10000.-acc(position_delta*mid)
            nav=cash.copy()
            gross_nav=gross_cash.copy()
            quantities={}
            symbol_values=[]
            fill_nav=10000.+np.cumsum(cash_delta)
            fill_after_positions=[]
            for symbol in SYMS:
                mask=fills["symbol"].to_numpy()==symbol
                qty=acc(position_delta*mask)
                values=qty*per[symbol]["close"].to_numpy()
                quantities[symbol]=qty
                symbol_values.append(values)
                nav+=values
                gross_nav+=values
                need(np.all(qty>=-1e-9) and close(qty,inventory[symbol+"_quantity"].to_numpy(),1e-8)
                    and close(values,inventory[symbol+"_marked_notional"].to_numpy()),"Quantity/mark identity")
                need(abs(qty[-1]-summary["open_positions"][symbol])<1e-8,"Terminal quantity omitted")
                if len(t):
                    index=(t-1-start)//MIN
                    opens=per[symbol]["open"].to_numpy()
                    prequotes=fm.filter(pl.col("symbol")==symbol)["quote_volume"].to_numpy()
                    fill_nav+=np.cumsum(position_delta*mask)*opens[index]
                    own=np.flatnonzero(mask)
                    need(close(mid[mask],opens[index[mask]],1e-8),"Fill not actual minute-open proxy")
                    capacities=prequotes[index[mask]+31*1440-1]*.001
                    need(close(capacities,fills["capacity"].to_numpy()[mask])
                        and np.all(notionals[mask]<=capacities+1e-7)
                        and np.all(notionals[mask]>=10-1e-7),"Zero/future capacity or minnotional")
                    need(np.all(np.abs(q[mask]/cfg["lot_step_by_symbol"][symbol]-np.round(q[mask]/cfg["lot_step_by_symbol"][symbol]))<1e-5),"Lot filter")
                    need(np.array_equal(fills["capacity_open_us"].to_numpy()[mask],t[mask]//MIN*MIN-MIN),"Capacity minute identity")
            need(close(nav,inventory["nav"].to_numpy()) and close(cash,inventory["cash"].to_numpy())
                and close(gross_nav,inventory["gross_marked_nav_same_quantities"].to_numpy())
                and close(gross_nav-acc(fees+extra),nav) and np.all(cash>=-1e-7),"Minute NAV cash/gross-cost identity")
            need(close(acc(fees),inventory["cumulative_fee"].to_numpy()) and close(acc(extra),inventory["cumulative_execution_cost"].to_numpy()),"Minute cost accumulation")
            need(close(fill_nav,fills["nav_after"].to_numpy()),"Per-fill NAV at both symbol open marks")
            daily_mask=close_times%DAY==0
            dn=nav[daily_mask]
            dr=dn/np.r_[10000.,dn[:-1]]-1
            need(len(dn)==days and close(dn,daily["nav"].to_numpy()) and close(dr,daily["return"].to_numpy()),"UTC daily NAV/returns")
            fee_day=np.bincount((t//DAY-start//DAY).astype(int),weights=fees,minlength=days)
            cost_day=np.bincount((t//DAY-start//DAY).astype(int),weights=extra,minlength=days)
            notional_day=np.bincount((t//DAY-start//DAY).astype(int),weights=notionals,minlength=days)
            need(close(fee_day,daily["fees"].to_numpy()) and close(cost_day,daily["execution_costs"].to_numpy())
                and close(notional_day/np.r_[10000.,dn[:-1]],daily["turnover"].to_numpy()),"Daily fees/cost/turnover")
            normalized_turnover=float((notional_day/np.r_[10000.,dn[:-1]]).sum())
            need(close(summary["turnover"],normalized_turnover,1e-10),"Total daily-normalized turnover")
            net=nav[-1]-10000.
            gross=net+fees.sum()+extra.sum()
            mdd=float(-np.min(np.r_[10000.,nav]/np.maximum.accumulate(np.r_[10000.,nav])-1))
            dmdd=float(-np.min(np.r_[10000.,dn]/np.maximum.accumulate(np.r_[10000.,dn])-1))
            vol=float(np.std(dr,ddof=1)*np.sqrt(365))
            gw=np.sum(symbol_values,axis=0)/nav
            weights={s:symbol_values[i]/nav for i,s in enumerate(SYMS)}
            positive=np.maximum(dn-np.r_[10000.,dn[:-1]]+fee_day+cost_day,0)
            concentration=float(positive.max()/positive.sum()) if positive.sum() else None
            need(abs(nav[-1]-summary["final_nav"])<1e-6 and abs(net-published["net_cash_PnL"])<1e-6
                and abs(gross-published["gross_cash_PnL_same_quantities"])<1e-6
                and abs(mdd-published["max_observed_minute_MDD"])<1e-12
                and abs(dmdd-summary["max_drawdown"])<1e-12
                and abs(vol-summary["annual_volatility"])<1e-12
                and abs(gw.max()-published["max_minute_marked_gross_weight"])<1e-12,"Published PnL/risk differs")
            need((concentration is None and published["top1_day_positive_gross_PnL_share"] is None) or (concentration is not None and published["top1_day_positive_gross_PnL_share"] is not None and abs(concentration-published["top1_day_positive_gross_PnL_share"])<=1e-10),"Positive gross day concentration")
            need(np.all(fills.filter(pl.col("side")=="buy")["asset_weight_after"].to_numpy()<=.3+1e-9)
                and np.all(fills.filter(pl.col("side")=="buy")["gross_weight_after"].to_numpy()<=.6+1e-9),"New buy exceeds actual postcost caps")
            need(published["candidate_qualification_allowed"] is False and published["real_BBO"] is False
                and published["capacity_proven"] is False and published["net_long_term_CAGR_proven"] is False,"Proxy scope overstated")
            annual=float((nav[-1]/10000.)**(365/days)-1)
            need(summary["days"]==days and abs(summary["total_return"]-net/10000.)<1e-12
                and abs(summary["annual_return"]-annual)<1e-12 and published["period_days"]==days
                and close(published["period_net_return"],net/10000.,1e-12)
                and close(published["period_descriptive_net_CAGR"],annual,1e-12)
                and published["annualized_return_is_descriptive_only"] is True, "122day descriptive return fields")
            month_rows=[]
            previous_nav=10000.
            previous_gross_nav=10000.
            for month,lower,upper in monthly_intervals(start,end):
                day_indices=np.flatnonzero((close_times[daily_mask]>lower)&(close_times[daily_mask]<=upper))
                indices=np.flatnonzero((close_times>lower)&(close_times<=upper))
                fill_indices=(t>=lower)&(t<upper)
                last=int(indices[-1])
                mn=float(nav[last])
                mg=float(gross_nav[last])
                mf=float(fees[fill_indices].sum())
                mc=float(extra[fill_indices].sum())
                mp=float(mn-previous_nav)
                gp=float(mg-previous_gross_nav)
                need(close(gp-mp,mf+mc), "Monthly ongoing positions gross-cost identity")
                mv=float(np.std(dr[day_indices],ddof=1)*np.sqrt(365))
                mnav=np.r_[previous_nav,nav[indices]]
                mmdd=float(-np.min(mnav/np.maximum.accumulate(mnav)-1))
                end_quantities={s:float(quantities[s][last]) for s in SYMS}
                month_rows.append({"month":month,"days":int(len(day_indices)),"start_NAV":float(previous_nav),
                    "end_NAV":mn,"marked_net_return":float(mn/previous_nav-1),"net_PnL":mp,
                    "gross_PnL_same_quantities":gp,"fee":mf,"execution_cost":mc,
                    "trade_count":int(np.sum(fill_indices)),"turnover_notional_USDT":float(notionals[fill_indices].sum()),
                    "normalized_daily_turnover":float((notional_day/np.r_[10000.,dn[:-1]])[day_indices].sum()),"within_month_minute_MDD":mmdd,
                    "descriptive_daily_annual_vol":mv,"month_end_quantities":end_quantities,
                    "month_end_marked_notional":float(sum(v[last] for v in symbol_values)),
                    "cash_reset":False,"monthly_liquidation_assumed":False})
                previous_nav,previous_gross_nav=mn,mg
            need([m["days"] for m in month_rows]==[int((b-a)//DAY) for _,a,b in monthly_intervals(start,end)] and close(sum(m["net_PnL"] for m in month_rows),net)
                and close(sum(m["fee"] for m in month_rows),fees.sum()) and close(sum(m["execution_cost"] for m in month_rows),extra.sum()), "Month totals do not close")
            positive_months=np.maximum([m["gross_PnL_same_quantities"] for m in month_rows],0.)
            positive_net_months=np.maximum([m["net_PnL"] for m in month_rows],0.)
            entry={"fold":fold["fold"],"strategy":strategy,"spread_bps":spread,
                "net_return":float(net/10000.),"net_PnL":float(net),"gross_PnL_same_quantities":float(gross),
                "fees":float(fees.sum()),"execution_costs":float(extra.sum()),"trade_count":fills.height,
                "turnover_notional_USDT":float(notionals.sum()),"normalized_daily_turnover":normalized_turnover,
                "minute_MDD":mdd,"daily_MDD":dmdd,"period_days":days,"descriptive_net_CAGR":annual,
                "months":month_rows,"net_positive_months":int(np.sum([m["net_PnL"]>0 for m in month_rows])),
                "top1_positive_gross_month_share":float(positive_months.max()/positive_months.sum()) if positive_months.sum() else None,
                "top1_positive_net_month_share":float(positive_net_months.max()/positive_net_months.sum()) if positive_net_months.sum() else None,"descriptive_period_daily_annual_vol":vol,
                "max_minute_gross_weight":float(gw.max()),
                "max_minute_BTC_weight":float(weights["BTCUSDT"].max()),"max_minute_ETH_weight":float(weights["ETHUSDT"].max()),
                "passive_drift_symbol_cap_excess_minutes":int(np.sum((weights["BTCUSDT"]>.3+1e-9)|(weights["ETHUSDT"]>.3+1e-9))),
                "passive_drift_gross_cap_excess_minutes":int(np.sum(gw>.6+1e-9)),
                "day_concentration_absolute_difference":abs(concentration-published["top1_day_positive_gross_PnL_share"]) if concentration is not None else None,"day_concentration_absolute_tolerance":1e-10,"top1_positive_gross_day_share":concentration,
                "terminal_marked_notional":float(sum(v[-1] for v in symbol_values)),
                "cash_min":float(cash.min()),"target_bindings":target_bound[strategy],
                "ledger_artifact_hashes":{n:b["sha256"] for n,b in item["artifacts"].items()}}
            rt=pl.read_parquet(d/"round_trips.parquet")
            held=dict.fromkeys(SYMS,0.);cycles=dict.fromkeys(SYMS,None);expected_cycles=[]
            check_cash=10000.
            for rowindex,row in enumerate(fills.iter_rows(named=True)):
                s=row["symbol"];g=row["quantity"];F=row["fill_price"];M=row["mid_price"];w=row["target_weight"]
                i=(row["execution_us"]-1-start)//MIN
                marks={z:float(per[z]["open"][i]) for z in SYMS}
                before=check_cash+sum(held[z]*marks[z] for z in SYMS)
                desired=w*before-held[s]*M
                is_buy=row["side"]=="buy"
                need((desired>0)==is_buy and 0<=w<=.3,"Fill side/target weight")
                loss=F-.999*M if is_buy else M-F+F*.001
                target=abs(desired)/(.999*M+w*loss if is_buy else M-w*loss)
                upper=min(target,row["capacity"]/F)
                if is_buy:
                    gross_before=sum(held[z]*marks[z] for z in SYMS)
                    upper=min(upper,check_cash/F,
                        max(0.,(.3*before-held[s]*M)/(.999*M+.3*loss)),
                        max(0.,(.6*before-gross_before)/(.999*M+.6*loss)))
                    for z in SYMS:
                        if z!=s:upper=min(upper,max(0.,(before-held[z]*marks[z]/.3)/loss))
                else:upper=min(upper,held[s])
                step=cfg["lot_step_by_symbol"][s]
                expected_g=math.floor(upper/step+1e-9)*step
                if not is_buy and expected_g>held[s]:expected_g=max(0.,expected_g-step)
                need(abs(g-expected_g)<1e-12,"Native target/cash/net-base/capacity/cap sizing")
                check_cash+=row["cash_delta"]
                if row["side"]=="buy" and held[s]<=1e-12:
                    cycles[s]={"entry_us":row["execution_us"],"cost":0.,"proceeds":0.,"fees":0.}
                if row["side"]=="sell":
                    need(g<=held[s]+1e-12,"Sold unavailable net base")
                held[s]+=row["position_delta"]
                after=check_cash+sum(held[z]*marks[z] for z in SYMS)
                if is_buy:
                    need(max(held[z]*marks[z]/after for z in SYMS)<=.3+1e-9
                        and sum(held[z]*marks[z] for z in SYMS)/after<=.6+1e-9,"All-symbol postcost buy cap")
                need(held[s]>=-1e-12,"Negative net inventory")
                cyc=cycles[s];need(cyc is not None,"Sell without purchased inventory")
                cyc["fees"]+=row["fee"]
                if row["side"]=="buy":cyc["cost"]+=g*F
                else:cyc["proceeds"]+=g*F-g*F*.001
                if row["side"]=="sell" and held[s]==0:
                    expected_cycles.append({"symbol":s,"entry_us":cyc["entry_us"],
                        "exit_us":row["execution_us"],"pnl":cyc["proceeds"]-cyc["cost"],"fees":cyc["fees"]})
            need(rt.height==len(expected_cycles)==summary["round_trip_count"],"Closed cycle count")
            for observed,expected in zip(rt.iter_rows(named=True),expected_cycles):
                need(all(observed[k]==expected[k] for k in ("symbol","entry_us","exit_us"))
                    and close(observed["pnl"],expected["pnl"]) and close(observed["fees"],expected["fees"]),
                    "Cycle cost double fee or incorrect proceeds")
            need(orders["quantity"].sum()==fills["quantity"].sum()
                or close(orders["quantity"].sum(),fills["quantity"].sum(),1e-10),"Order/trade gross quantity")
            need(orders.filter(pl.col("filled_notional")==0)["quantity"].sum()==0,"Fee or quantity on unfilled order")
            entry.update(native_asset_fee_verified=True,closed_cycle_count_verified=rt.height,
                fee_settlement_version=summary["fee_settlement_version"],
                positive_terminal_dust_preserved=any(0<held[s]<cfg["lot_step_by_symbol"][s] for s in SYMS))
            audit["ledgers"].append(entry)

    need(len(seen)==3 and seen=={(f["id"],s,b) for f in spec["folds"] for s in spec["strategy_ids"] for b in (2,4,8)},"Missing fixed cost account")
    for spread in (2,4,8):
        one=next(z for z in audit['ledgers'] if z['fold']==fold_id and z['spread_bps']==spread)
        published=next(z for z in r['aggregate'] if z['spread_bps']==spread)
        need(published['complete_periods']==1 and published['period_lengths_days']==[days] and close(published['period_net_return'],one['net_return'],1e-12) and close(published['fees_USDT_across_period_accounts'],one['fees']) and close(published['execution_cost_USDT_across_period_accounts'],one['execution_costs']) and close(published['max_observed_minute_MDD'],one['minute_MDD'],1e-12),'Aggregate versus independent ledger')
    control=spec['paired_control_reference'];control_path=ROOT/control['report_path'];old=read(control_path)
    control_spec_path=ROOT/control['protocol_path'];control_spec=read(control_spec_path)
    need(sha(control_path)==control['report_sha256'] and sha(control_spec_path)==control['protocol_sha256'] and old['status']=='COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING' and old['completed_ledgers']==3 and old['all_planned_ledgers_complete'],'Saved native2h control complete report binding')
    need(control['strategy_id']=='COIN_JESSE_DONCHIAN_2H_SPOT_ADAPTER' and set(control['same_fields'])=={'common_config','costs','folds','warmup_days','reused_minute_input','fee_settlement','fee_profile_sha256'} and all(spec[k]==control_spec[k] for k in control['same_fields']),'Control differs in capital/cost/risk/calendar/source/fee assumptions')
    need(old['fee_derivation']['derived_AST_SHA256']==deriv['derived_AST_SHA256'] and old['fee_profile_sha256']==r['fee_profile_sha256'],'Old/new fee math differs')
    prior_audit=audit['control_audit_metadata'];prior_period=next(z for z in prior_audit['period_bindings'] if z['label']==label)
    need(prior_period['report_sha256']==sha(control_path) and prior_period['protocol_sha256']==control['protocol_sha256'] and prior_period['original_derivative_parquet_sha256']==reference['sha256'],'Accepted old financial audit is exact paired control')
    for spread in (2,4,8):
        current=next(z for z in audit['ledgers'] if z['fold']==fold_id and z['spread_bps']==spread)
        prior=next(z for z in prior_audit['ledgers'] if z['period_days']==days and z['strategy']==control['strategy_id'] and z['spread_bps']==spread)
        ps=next(z['summary'] for f in old['folds'] for z in f['results'] if z['spread_bps']==spread)
        need(close(prior['net_PnL'],ps['net_cash_PnL']) and close(prior['gross_PnL_same_quantities'],ps['gross_cash_PnL_same_quantities']) and close(prior['minute_MDD'],ps['max_observed_minute_MDD'],1e-12) and close(prior['fees'],ps['fees']) and close(prior['execution_costs'],ps['execution_costs']),'Saved control summary and accepted audit differ')
        gross_pnl=current['gross_PnL_same_quantities'];total_cost=current['fees']+current['execution_costs']
        current['gross_to_net_retention']=current['net_PnL']/gross_pnl if gross_pnl!=0 else None
        current['cost_to_gross_PnL_ratio']=total_cost/gross_pnl if gross_pnl!=0 else None
        current['cost_to_gross_ratios_are_signed_descriptive_not_profitability_qualification']=True
        current['round_trip_zero_explanation']='Positive net-base sublot dust remains in inventory; exact-zero inventory closes a cycle. No dust writeoff, no inferred profitable/lossless closed trades.' if current['closed_cycle_count_verified']==0 and current['terminal_marked_notional']>0 else 'Exact-zero inventory cycle semantics; terminal positive inventory stays marked.'
        comparisons=[]
        need([m['month'] for m in current['months']]==[m['month'] for m in prior['months']],'Paired monthly calendar')
        for cm,pm in zip(current['months'],prior['months']):
            comparisons.append({'month':cm['month'],'hybrid_net_PnL':cm['net_PnL'],'control_net_PnL':pm['net_PnL'],'delta_net_PnL':cm['net_PnL']-pm['net_PnL'],'hybrid_gross_PnL':cm['gross_PnL_same_quantities'],'control_gross_PnL':pm['gross_PnL_same_quantities'],'delta_gross_PnL':cm['gross_PnL_same_quantities']-pm['gross_PnL_same_quantities'],'hybrid_total_cost':cm['fee']+cm['execution_cost'],'control_total_cost':pm['fee']+pm['execution_cost'],'hybrid_turnover_notional_USDT':cm['turnover_notional_USDT'],'control_turnover_notional_USDT':pm['turnover_notional_USDT'],'hybrid_descriptive_annual_vol':cm['descriptive_daily_annual_vol'],'control_descriptive_annual_vol':pm['descriptive_daily_annual_vol'],'accounts_reset_or_monthly_liquidated':False})
        current['paired_native_2h_control']={'report_path':str(control_path),'report_sha256':sha(control_path),'accepted_audit_path':CONTROL_AUDIT,'accepted_audit_sha256':CONTROL_AUDIT_SHA,'old_ledger_arrays_read':False,'same_capital_cost_risk_mechanism_source_period_and_fee_math':True,'identical_realized_risk_claimed':False,'control_net_PnL':prior['net_PnL'],'control_gross_PnL':prior['gross_PnL_same_quantities'],'control_fees':prior['fees'],'control_execution_costs':prior['execution_costs'],'control_turnover_notional_USDT':prior['turnover_notional_USDT'],'control_minute_MDD':prior['minute_MDD'],'control_descriptive_daily_annual_vol':prior['descriptive_period_daily_annual_vol'],'control_terminal_marked_notional':prior['terminal_marked_notional'],'delta_net_PnL':current['net_PnL']-prior['net_PnL'],'delta_gross_PnL':gross_pnl-prior['gross_PnL_same_quantities'],'delta_total_cost':total_cost-prior['fees']-prior['execution_costs'],'delta_turnover_notional_USDT':current['turnover_notional_USDT']-prior['turnover_notional_USDT'],'delta_minute_MDD':current['minute_MDD']-prior['minute_MDD'],'delta_descriptive_daily_annual_vol':current['descriptive_period_daily_annual_vol']-prior['descriptive_period_daily_annual_vol'],'months':comparisons,'different_strategy_and_entry_rule_not_isolated_indicator_effect':True}
    need({p:sha(ROOT/p) for p in hashes}==hashes and sha(actual_path)==expected_sha,'Frozen actual bytes changed')

def dependency_receipts():
    rows=[]
    old4=ROOT/'reports/fast_research/BYBIT_SPOT_COMMON_PIPELINE_TINY_20261002_V2.json';o=read(old4)
    need(sha(old4)=='5538567a796646e7e1420119a4704044c499d8bce47ceb1931f490244e1cecb7' and o['status']=='PASS_SIMPLE_COMPARISON_SYNTHETIC_NOT_MARKET_RESULT','Original native four PASS evidence')
    need(o['binding']['source_hashes']['scripts/investment/compare_simple_strategies.py']=='bff0fe43a4a46406668a8a7bbe1d298397437a31d6ec623480abff2b2006131e' and o['binding']['source_hashes']['scripts/investment/bybit_spot_adapter.py']==PINS['scripts/investment/bybit_spot_adapter.py'],'Old native4 code reuse')
    p=Path(o['run_dir'])/'junit.xml';x=ET.parse(p).getroot();counts={k:sum(int(s.get(k,0)) for s in x.iter('testsuite')) for k in ('tests','failures','errors','skipped')}
    need(sha(p)==o['junit_sha256'] and counts=={'tests':4,'failures':0,'errors':0,'skipped':0},'Old native4 actual JUnit')
    rows.append({'path':str(old4),'sha256':sha(old4),'counts':counts,'actual_task':task_for(o['binding']),'suite_rerun':False})
    old7=ROOT/'reports/fast_research/PUBLIC_DONCHIAN_HYBRID_TARGET_TINY_20261002_V1.json';o=read(old7)
    need(sha(old7)=='32086aa3f4d1e331da1dc4f3e1f242b433500690a65e53d98f08b6eeb534a808' and o['status']=='PASS_PUBLIC_DONCHIAN_HYBRID_TARGET_SYNTHETIC_NOT_MARKET_RESULT' and o['source_bytes_unchanged'] and all(sha(ROOT/p)==d for p,d in o['source_hashes'].items()),'Original hybrid7 code evidence')
    p=Path(o['junit_path']);x=ET.parse(p).getroot();counts={k:sum(int(s.get(k,0)) for s in x.iter('testsuite')) for k in ('tests','failures','errors','skipped')}
    task=read(o['task_path']);need(sha(p)==o['junit_sha256'] and counts==o['junit_counts']=={'tests':7,'failures':0,'errors':0,'skipped':0} and task==o['actual_task'] and sha(o['task_path'])==o['task_sha256'] and task['status']=='completed' and task['exit_code']==0,'Old hybrid7 actual JUnit/task')
    rows.append({'path':str(old7),'sha256':sha(old7),'counts':counts,'actual_task':task,'suite_rerun':False})
    return rows

def main():
    need(os.environ.get('COIN_TASK_ID') and len(sys.argv)==2 and not OUT.exists() and not (STATE/'RUN_BINDING.json').exists(),'Exclusive single new audit run')
    need(str(Path(sys.prefix))=='/home/xflops/coin-state/v8-clean-env-20261002-v2' and pl.thread_pool_size()<=2,'Clean bounded audit environment')
    manifest_path=Path(sys.argv[1]).resolve();need(manifest_path==STATE/'ACTUAL_BINDING.json','Own prebound manifest only')
    manifest=read(manifest_path);cases=manifest['cases']
    need(len(cases)==2 and [c['period'] for c in cases]==['122','90'] and all(set(c)=={'period','report_sha256','protocol_sha256','actual_host_session_id','actual_task_id'} and len(c['report_sha256'])==64 and len(c['protocol_sha256'])==64 and c['actual_host_session_id']>0 and c['actual_task_id'] for c in cases),'Two explicit new 3+3 selectors; no old account reuse')
    need(sha(ROOT/REUSE)==REUSE_SHA and sha(STATE/'reused_checker.py')==REUSE_SHA,'Reused native financial checker byte pin')
    reused=(STATE/'reused_checker.py').read_bytes();code=Path(__file__).read_bytes()
    anchor=b'        for item in fold["results"]:';after=b'    need(len(seen)==3'
    original_financial=reused[reused.index(anchor):reused.index(after,reused.index(anchor))]
    actual_financial=code[code.index(anchor):code.index(after,code.index(anchor))]
    need(original_financial==actual_financial and hashlib.sha256(actual_financial).hexdigest()==FINANCIAL_SHA,'Whole native financial block byte-identical reuse')
    previous_path=ROOT/'docs/archive/COMPARE_SIMPLE_STRATEGIES_PRE_RSI2_20261002_V1.py'
    need(sha(previous_path)=='bff0fe43a4a46406668a8a7bbe1d298397437a31d6ec623480abff2b2006131e','Frozen common engine pre-RSI2 archive')
    before=previous_path.read_text(encoding='utf-8-sig');current=(ROOT/'scripts/investment/compare_simple_strategies.py').read_text(encoding='utf-8-sig')
    allowed=before.replace('"COIN_JESSE_DONCHIAN_2H_ENTRY_1H_EXIT_SPOT_ADAPTER")','"COIN_JESSE_DONCHIAN_2H_ENTRY_1H_EXIT_SPOT_ADAPTER", "COIN_JESSE_RSI2_1H_SPOT_ADAPTER")',1).replace('            elif strategy in (public_strategy.STRATEGY_ID, public_strategy.STRATEGY_2H_ID):','            elif strategy == "COIN_JESSE_RSI2_1H_SPOT_ADAPTER":\n                from scripts.investment import public_rsi2_adapter\n                plan = public_rsi2_adapter.fixed_targets(fold_minutes, calendar)\n            elif strategy in (public_strategy.STRATEGY_ID, public_strategy.STRATEGY_2H_ID):',1)
    need(allowed==current and sha(ROOT/'scripts/investment/compare_simple_strategies.py')==PINS['scripts/investment/compare_simple_strategies.py'],'Only strategyID and three lazy-dispatch lines changed in shared runner')
    need(sha(ROOT/CONTROL_AUDIT)==CONTROL_AUDIT_SHA,'Accepted original six native controls')
    controls=read(ROOT/CONTROL_AUDIT);need(controls['status']=='PASS_COMPOSITE_NATIVE_RECEIVED_ASSET_FEE_PROXY_LEDGER_ACCOUNTING_NOT_SINGLE_FRESH_SIX_SUITE' and controls['completed_ledgers_verified']==6,'Old composite control accepted scope')
    binding={'task_id':os.environ['COIN_TASK_ID'],'exact_command':' '.join(sys.argv),'python':sys.executable,'sys_prefix':sys.prefix,'checker_sha256':sha(__file__),'reused_checker':REUSE,'reused_checker_sha256':REUSE_SHA,'financial_block_sha256':FINANCIAL_SHA,'financial_block_bytes_identical':True,'actual_reports':{CASES[c['period']][0]:c['report_sha256'] for c in cases},'actual_manifest_path':str(manifest_path),'actual_manifest_sha256':sha(manifest_path),'explicit_financial_selectors':[{'period_days':int(c['period']),'fold':CASES[c['period']][3],'strategy':STRATEGY,'spread_bps':[2,4,8],'planned_new_ledgers':3} for c in cases],'environment_lock_sha256':sha(ROOT/'environments/v8/uv.lock'),'data_scope':'SIX_NEW_RSI2_LEDGER_READS_CONT122_3_AND_CONT90_3; OLD_NATIVE_CONTROLS_SUMMARIES_ONLY'}
    (STATE/'RUN_BINDING.json').write_text(json.dumps(binding,indent=2,allow_nan=False))
    audit={'version':'PUBLIC_RSI2_NATIVE_SIX_LEDGER_INDEPENDENT_AUDIT_20261002_V1','status':'FAIL_RSI2_NATIVE_SIX_LEDGER_AUDIT','binding':binding,'independent_task_id':os.environ['COIN_TASK_ID'],'independent_source':str(Path(__file__)),'independent_source_sha256':sha(__file__),'run_binding_sha256':sha(STATE/'RUN_BINDING.json'),'period_bindings':[],'runtime_inputs':[],'target_causality':[],'ledgers':[],'control_audit_metadata':controls,'candidate_status':'NO_QUALIFIED_CANDIDATE','registry_appended_by_auditor':False,'original_market_source_files_read':False,'old_control_ledger_arrays_read':False,'models_fit':0,'orders_sent':0,'locked_consumed':False,'fixed_targets_called':False}
    try:
        audit['reused_synthetic_receipts']=dependency_receipts()
        kernel,Rules,kernel_identity=kernel_context();audit['official_kernel_metadata']=kernel_identity
        for case in cases:check_period(case,audit,kernel,Rules)
        need(len(audit['ledgers'])==6 and {(z['fold'],z['strategy'],z['spread_bps']) for z in audit['ledgers']}=={(f,STRATEGY,b) for f in ('CONT122','CONT90') for b in (2,4,8)},'Exactly all six new RSI2 financial blocks')
        del audit['control_audit_metadata']
        audit.update(status='PASS_RSI2_NATIVE_RECEIVED_ASSET_FEE_PROXY_LEDGER_ACCOUNTING_AND_CAUSAL_SCOPE',completed_ledgers_verified=6,economic_qualification='NOT_PROVEN_SCREENING_ONLY',limits=['Previously seen historical Binance minute proxy; fixed 2026 Bybit global non-VIP Spot received-asset fee counterfactual.','No native Bybit BBO/queue/filters/fee-tier qualification, no long-term APR/CAGR or candidate claim.','Common intent-event risk mechanism and caps do not imply identical realized risk or continuous hard caps; passive drift measured.','RSI2 is a fixed long-only1h port of the public long/short hook under COIN sizing and fees; not native Jesse sizing/engine replica.','Same actual net-inventory gross shadow, signed retention descriptive; no independently optimized fee-free account.','Positive dust remains marked; exact-zero cycle closure may be absent and is not a win-rate result.','Old native4/shared hourly-stream evidence and official6kernel semantic groups reused; exactly one new RSI2 integration case accepted, not one fresh combined suite.','Old native six controls read from saved report/audit summaries only, no old account replay.'])
    except Exception as error:
        audit.pop('control_audit_metadata',None)
        audit.update(error_type=type(error).__name__,error=str(error),traceback=traceback.format_exc(),completed_ledgers_before_failure=len(audit['ledgers']));raise
    finally:
        audit.update(created_utc=datetime.now(UTC).isoformat(),peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        with OUT.open('x') as stream:json.dump(audit,stream,indent=2,allow_nan=False,default=json_scalar)
        print(json.dumps({'status':audit['status'],'report':str(OUT),'sha256':sha(OUT),'completed_ledgers':len(audit['ledgers'])}))
if __name__=='__main__':main()