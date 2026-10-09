"""Prepare April's existing 63-day inputs; no fitting, inference or wallets."""
import argparse,importlib.util,json,os,resource,socket,sys,types
from pathlib import Path
import evaluate_requests63 as native
from prequential63_producer import TRAIN_FILES
base=native.base;HERE=base.HERE
CALENDAR=dict(start=1711929600000000,end_exclusive=1717372800000000,days=63,minutes=90720,funding_events=945)
FOLD='FOLD_20240401';PUBLIC=HERE/'april63'
READERS_RELATIVE='temporal-fresh-init-exports/442c7a127187ae23c5d0a12a1324a4c4cc07e431/EXP_FRESH_DATE_512/source/modules/temporal_two_expert'
READERS_SHA={'inputs.py':'e9b175aadede32539eefc25cc64c4d98964e7e2b166278f972c41f1dedcffcf5','feature_windows.py':'6132b39410112462edc865e45d933c0a3b7e528a181681b5900cc525e4166d63'}
sha=base.frozen.sha;read=base.frozen.read;require=base.frozen.require


def prefix_availability(state):
    """Count causal windows and raw mature labels, without fitting a scaler."""
    import numpy as np
    for name,(relative,h) in TRAIN_FILES.items():require(sha(state/relative)==h,'Exact retained prefix source differs: '+name)
    readers=state/READERS_RELATIVE
    for name,h in READERS_SHA.items():require(sha(readers/name)==h,'Exact NumPy-only prefix reader differs: '+name)
    package='_april63_feature_reader';module=types.ModuleType(package);module.__path__=[str(readers)];sys.modules[package]=module
    for name in ('inputs','feature_windows'):
        full=package+'.'+name;spec=importlib.util.spec_from_file_location(full,readers/(name+'.py'));m=importlib.util.module_from_spec(spec);sys.modules[full]=m;spec.loader.exec_module(m)
    features=sys.modules[package+'.feature_windows'].load_feature_inputs(state/TRAIN_FILES['features.npz'][0],state/TRAIN_FILES['feature_manifest.json'][0])
    with np.load(state/TRAIN_FILES['economic.npz'][0],allow_pickle=False) as z:e={k:z[k].copy() for k in ('decision_us','episode_id','symbol_order','target_available_us','start_execution_us','end_execution_us')}
    with np.load(state/TRAIN_FILES['short.npz'][0],allow_pickle=False) as z:s={k:z[k].copy() for k in ('decision_us','target_available_us','asset_context_available_us')}
    require(e['symbol_order'].tolist()==list(base.frozen.SYMBOLS) and np.array_equal(e['decision_us'],s['decision_us']),'Actual prefix dates/CORE5 identity differ')
    ix=np.flatnonzero(e['decision_us']<CALENDAR['start']);tt=e['decision_us'][ix];labels=e['end_execution_us'][ix]
    require(np.array_equal(e['start_execution_us'][ix],tt+base.frozen.MINUTE+1) and np.array_equal(labels,tt+base.frozen.DAY+base.frozen.MINUTE+1),'Actual prefix raw outcome clocks differ')
    expert=np.maximum(e['target_available_us'][ix].max(1),np.maximum(s['target_available_us'][ix].max(1),s['asset_context_available_us'][ix].max(1)))
    windows=features.windows(tt);feature=np.where(windows.valid,windows.available_us,0).max((1,2,3));rows=np.unique(windows.completed_us)
    require((feature<=tt).all() and (expert<=tt).all() and (rows<CALENDAR['start']).all(),'Retained prefix feature/expert windows cross their decisions or fold start')
    crossing=labels>=CALENDAR['start']
    return dict(status='PASS_CAUSAL_PREFIX_INPUT_AVAILABILITY_ONLY_NOT_FROZEN_TRAINING_PROVENANCE',training_cutoff_us=CALENDAR['start'],precutoff_decisions=len(tt),natural_prefix_lengths=[int(((e['episode_id'][ix])==i).sum()) for i in range(5)],raw_labels_mature_strictly_before_cutoff=int((~crossing).sum()),raw_labels_crossing_cutoff=int(crossing.sum()),crossing_sample_decision_us=tt[crossing].tolist(),crossing_raw_label_available_us=labels[crossing].tolist(),last_precutoff_decision_us=int(tt[-1]),prospective_unique_feature_rows=len(rows),maximum_feature_available_us=int(feature.max()),maximum_expert_input_available_us=int(expert.max()),maximum_feature_row_available_us=int(rows.max()),known_flat_terminal_proof='PENDING_ACTUAL_FROZEN_PRODUCER_RECEIPT;NO_RAW_LABEL_BACKDATING',last_decision_plus_one_minute_plus_one_us=int(tt[-1])+base.frozen.MINUTE+1,terminal_clock_is_conditional_not_an_observed_label=True,training_sources={n:dict(state_relative_path=p,sha256=h) for n,(p,h) in TRAIN_FILES.items()},NumPy_only_readers_SHA256=READERS_SHA,scaler_values='NOT_FIT_OR_RECONSTRUCTED;AWAIT_ACTUAL_EXPORT',fits=0,model_inference=0,wallets_run=0,provider_downloads=0)


def daily_context_check(state,contract_path):
    """Reuse the tested daily price/covariance and VOL/CS recipe checks."""
    import numpy as np,polars as pl
    c=native.canonical_contexts(state,calendar=CALENDAR,contract_path=contract_path)
    with np.load(contract_path.parent/'CANONICAL_CONTEXTS63.npz',allow_pickle=False) as z:
        packet={k:z[k].copy() for k in z.files}
    tt=packet['decision_us'];require(np.array_equal(tt,np.arange(CALENDAR['start'],CALENDAR['end_exclusive'],base.frozen.DAY,dtype=np.int64)),'Exact April63 daily grid required')
    require(packet['symbol_order'].tolist()==list(base.frozen.SYMBOLS) and packet['expert_order'].tolist()==list(c['expert_order']) and all(np.array_equal(packet[k],v) for k,v in c.items() if k!='expert_order'),'Full canonical E5+SHORT packet differs')
    require((packet['market_state13_available_us']<=tt).all() and np.isfinite(packet['market_state13']).all(),'Original current market input clocks/values differ')
    bars=[];matrix=[];available=None
    for j,symbol in enumerate(base.frozen.SYMBOLS):
        d=pl.read_parquet(state/'h1_validation/original/h1_market/data/normalized'/(symbol+'_daily.parquet')).filter((pl.col('close_us')<=int(tt[-1]))&(pl.col('available_us')<=int(tt[-1]))).sort('close_us')
        times=d['available_us'].to_numpy();prices=d['close'].to_numpy();ix=np.searchsorted(times,tt)
        require(np.array_equal(times[ix],tt) and np.array_equal(d['close_us'].to_numpy()[ix],tt) and np.array_equal(prices[ix],packet['market_close'][:,j]),'Actual completed daily prices differ')
        require(all(np.all(np.diff(times[i-30:i+1])==base.frozen.DAY) for i in ix) and np.array_equal(np.stack([np.diff(prices[i-30:i+1])/prices[i-30:i] for i in ix]),c['past_returns30'][:,:,j]),'Actual contiguous causal30 returns differ')
        if available is None:available=times
        require(np.array_equal(times,available),'Actual daily calendars differ');matrix.append(prices)
        bars.append(d.filter(pl.col('complete_kline')&pl.all_horizontal([pl.col(k).is_finite() for k in ('open','high','low','close','volume')])).select('symbol','open_us','close_us','available_us','open','high','low','close','volume'))
    from scripts.investment import vol_managed_perpetual_target as vol
    from scripts.research.public_cross_section_momentum import public_targets,ANCHOR_US
    targets,_=vol.fixed_targets(pl.concat(bars),tt,symbols=base.frozen.SYMBOLS);cs,_=public_targets(np.column_stack(matrix),available,tt,base.frozen.SYMBOLS,base.frozen.SYMBOLS)
    require(np.array_equal(targets['target_weight'].to_numpy().reshape(63,5),c['expert_targets'][:,1]) and np.array_equal(cs,c['expert_targets'][:,4]) and ANCHOR_US==1704067200000000,'Original VOL/CS recipe/weekly anchor differs')
    return dict(status='PASS_ACTUAL_DAILY_CLOSE_PAST30_COVARIANCE_VOL_CS_AND_FULL_CANONICAL_CONTEXT',decisions=63,first_decision_us=int(tt[0]),last_decision_us=int(tt[-1]),actual_daily_prices_and_returns_bit_identical=True,VOL_CS_targets_bit_identical=True,weekly_rank_anchor_us=ANCHOR_US,original_E5_slots_unchanged=True,SHORT_slot=5,current_context_role='CAUSAL_EVALUATION_INPUTS_NOT_TRAINING_LABELS')


def prepare(state,output=PUBLIC):
    context=native.prepare_context(state,output,CALENDAR)
    old=read(HERE/'EVALUATE_REQUESTS61_ADAPTER.json');previous=read(native.CONTRACT)
    contract={k:previous[k] for k in ('schema','request_schema','engine_sha256','financial_contract','cost','limits','retained_preflight_sha256','original_E5_order','compact_model_E5_indices','permitted_extension','fresh_start','learned_admitted_actions','historical_publication_and_exchange_account_rules_certified','short_hypothesis_previously_selected_after_seen_June2024')}
    require(contract['financial_contract']==old['financial_contract'] and contract['cost']==old['cost'] and sha(base.frozen.REPO/'scripts/investment/resumable_perpetual.py')==contract['engine_sha256'],'Exact original guard-OFF financial contract/engine required')
    contract.update(fold=FOLD,calendar=CALENDAR,calendar_UTC='2024-04-01_to_2024-06-03_exclusive',source_sha256={n:sha(base.frozen.REPO/n) for n in previous['source_sha256']},context_files=context['context_files'],original_financial_contract_SHA256=sha(HERE/'EVALUATE_REQUESTS61_ADAPTER.json'),dependency_recipe=dict(path='research/recover-frozen-runner-20261009/requirements-native61.txt',sha256=sha(HERE/'requirements-native61.txt')),market_source=dict(state_relative_root='h1_validation/original/h1_market',published_identity=read(HERE/'NATIVE61_PLAN.json')['public_input']),prefix_cutoff_us=CALENDAR['start'],fresh_initialization='REQUIRED_ACTUAL_SOURCE_BOUND_FRESH_EMPTY_ADAM_BIRTH0_FIXED512_RECEIPTS_NOT_YET_PROVIDED',terminal=dict(active_intervals=62,last_decision_us=CALENDAR['end_exclusive']-base.frozen.DAY,final_day_target_zero=True,persist_cash_close=True,paid_flat_closure_required=True,actual_fill_clocks='NOT_RUN;DO_NOT_FORCE_SURROGATE_CLOCK',market_available_through_exclusive_us=CALENDAR['end_exclusive']),current_requests='NOT_YET_PROVIDED',current_wallet_authorization='PREPARATION_ONLY;NO_WALLET_OR_STATIC_FALLBACK',run_requires='ACTUAL_FROZEN_MODEL_AND_CONTROL_EXPORTS;EXTERNAL_HASH_BINDINGS;CURRENT_CONTEXT_AND_TARGET_BUDGET_PARITY;STRICT_PREFIX_CLOCK_AND_KNOWN_FLAT_TERMINAL_PROOF;REQUEST_SPECIFIC_AUTHORIZED_PUBLISHED_PLAN',producer_interface=dict(schema=native.PRODUCER_SCHEMA,decisions=63,active_intervals=62,admitted_context_indices=[0,1,4,5],unused_SMA_Don_source_slots='PRESERVE_FULL_CANONICAL_SOURCE;PRODUCER_UNUSED_ZERO_SLOTS_COMPARE_ADMITTED_ACTIONS',raw_terminal_request='PRESERVE_UNCHANGED;ORIGINAL_FINAL_DAY_EXECUTION_TARGET_ZERO'),fits=0,model_inference=0,wallets_run=0,provider_downloads=0)
    for name in ('prepare_april63.py',):contract['source_sha256'][(HERE/name).relative_to(base.frozen.REPO).as_posix()]=sha(HERE/name)
    path=output/'ADAPTER_CONTRACT.json';path.write_text(json.dumps(contract,indent=2)+'\n')
    prefix=prefix_availability(state);(output/'PREFIX_AVAILABILITY.json').write_text(json.dumps(prefix,indent=2)+'\n')
    report=native.readiness(state,calendar=CALENDAR,contract_path=path);report.update(fold=FOLD,adapter_contract_sha256=sha(path),daily_context_check=daily_context_check(state,path),prefix_availability=prefix,terminal_execution='NOT_RUN;ORIGINAL_PAID_CLOSURE_SOURCE_FLAGS_AND_FULL_FINAL_DAY_TAPE_BOUND',missing_dependencies=['Actual frozen April model/control requests and externally pinned source/config/model/scaler/initialization receipts','Actual prefix clock/known-flat terminal proof; raw March31 next-day label crosses April1','Producer current-context and target/budget parity; request-specific authorized execution plan'],model_inference=0,completed_wallet_reruns=0)
    (output/'READINESS.json').write_text(json.dumps(report,indent=2)+'\n');return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--output',type=Path,default=PUBLIC);a=p.parse_args()
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','POLARS_MAX_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6000000000,6000000000));resource.setrlimit(resource.RLIMIT_CPU,(600,600))
    require(__import__('shutil').disk_usage(a.state).free>=16106127360,'Preserve15GiB disk reserve')
    def blocked(*args,**kwargs):raise RuntimeError('Offline April preparation forbids network')
    socket.create_connection=blocked;socket.socket.connect=blocked
    print(json.dumps(prepare(a.state,a.output)),flush=True)
