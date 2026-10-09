"""Two declared2023 frozen63 folds over the existing native request runner."""
import argparse,json,os,resource,socket,zipfile
from pathlib import Path
import evaluate_requests63 as original
import prequential63_producer as producer
from recover_prequential2023 import PUBLIC_DATA
base=original.base
FOLDS={'FOLD_20230703':dict(start=1688342400000000,end_exclusive=1693785600000000,days=63,minutes=90720,funding_events=945),'FOLD_20231002':dict(start=1696204800000000,end_exclusive=1701648000000000,days=63,minutes=90720,funding_events=945)}


def prepare_context(state,fold,public):
    import numpy as np,polars as pl
    require=base.frozen.require;cal=FOLDS[fold];tt=np.arange(cal['start'],cal['end_exclusive'],base.frozen.DAY,dtype=np.int64)
    for name,(relative,sha) in producer.TRAIN_FILES.items():require(base.frozen.sha(state/relative)==sha,'Exact existing original training context source required')
    with np.load(state/producer.TRAIN_FILES['economic.npz'][0],allow_pickle=False) as z:
        ix=np.searchsorted(z['decision_us'],tt);require(np.array_equal(z['decision_us'][ix],tt) and z['symbol_order'].tolist()==list(base.frozen.SYMBOLS) and z['expert_order'].tolist()==list(base.COMPACT),'Exact original cash/vol/cs63 evaluation slice required')
        c=dict(expert_targets=np.zeros((63,6,5)),expert_eligible=np.zeros((63,6),bool),target_available_us=np.tile(tt[:,None],(1,6)),past_returns30=z['past_returns30'][ix].copy());close=z['completed_decision_daily_close'][ix].copy()
        for key in ('expert_targets','expert_eligible','target_available_us'):c[key][:,[0,1,4]]=z[key][ix]
    with np.load(state/producer.TRAIN_FILES['short.npz'][0],allow_pickle=False) as z:
        require(np.array_equal(z['decision_us'][ix],tt) and (z['asset_context_available_us'][ix]<=tt[:,None]).all(),'Exact causal existing short63 evaluation slice required')
        for key in ('expert_targets','expert_eligible','target_available_us'):c[key][:,5:6]=z[key][ix]
    bars=[];matrix=[];available=None
    for j,symbol in enumerate(base.frozen.SYMBOLS):
        d=pl.read_parquet(state/'h1_validation/original/h1_market/data/normalized'/(symbol+'_daily.parquet')).filter((pl.col('close_us')<=int(tt[-1]))&(pl.col('available_us')<=int(tt[-1]))).sort('close_us');times=d['close_us'].to_numpy();values=d['close'].to_numpy();idx=np.searchsorted(times,tt)
        require(np.array_equal(times[idx],tt) and np.array_equal(values[idx],close[:,j]),'Actual completed daily prices differ from frozen source')
        real=np.stack([np.diff(values[i-30:i+1])/values[i-30:i] for i in idx]);require(np.array_equal(real,c['past_returns30'][:,:,j]),'Actual30 contiguous daily returns differ from frozen covariance input')
        if available is None:available=times
        require(np.array_equal(times,available),'Actual daily calendars differ');matrix.append(values)
        bars.append(d.filter(pl.col('complete_kline')&pl.all_horizontal([pl.col(k).is_finite() for k in ('open','high','low','close','volume')])).select('symbol','open_us','close_us','available_us','open','high','low','close','volume'))
    bars=pl.concat(bars);base.frozen.modules(state)
    from scripts.investment import vol_managed_perpetual_target as vol,momentum_short_pool_target as short
    from scripts.research.public_cross_section_momentum import public_targets
    vol_frame,_=vol.fixed_targets(bars,tt,symbols=base.frozen.SYMBOLS);vol_targets=vol_frame['target_weight'].to_numpy().reshape(63,5);cs,_=public_targets(np.column_stack(matrix),available,tt,base.frozen.SYMBOLS,base.frozen.SYMBOLS);short_frame,_=short.fixed_targets(bars,tt,symbols=base.frozen.SYMBOLS)
    require(np.array_equal(vol_targets,c['expert_targets'][:,1]) and np.array_equal(cs,c['expert_targets'][:,4]) and np.array_equal(short_frame['target_weight'].to_numpy().reshape(63,5),c['expert_targets'][:,5]),'Actual daily original VOL/CS/SHORT recipe targets differ')
    public.mkdir(parents=True,exist_ok=True);np.savez_compressed(public/'CANONICAL_CONTEXTS63.npz',decision_us=tt,symbol_order=np.array(base.frozen.SYMBOLS),expert_order=np.array(base.E5+(base.SHORT,)),**c,market_close=close)
    report=dict(status='PASS_ORIGINAL_ADMITTED_TARGETS_MASKS_CLOCKS_AND_ACTUAL_DAILY_PRICE_COVARIANCE_RECIPE_VALUES',fold=fold,calendar=cal,training_E3_SHA256=producer.TRAIN_FILES['economic.npz'][1],short_SHA256=producer.TRAIN_FILES['short.npz'][1],original_E5_slots=[0,1,4],appended_short_slot=5,unused_SMA_Don_slots='EXCLUDED_BY_PUBLISHED_POOL;ZERO_TARGETS_AND_FALSE_MASKS;NOT_INFERRED_MARKET_INELIGIBILITY',actual_daily_close_and_past30_returns_bit_identical=True,actual_source_VOL_CS_SHORT_target_recipes_bit_identical=True,weekly_rank_anchor='ORIGINAL2024JAN1_UNCHANGED',canonical_context_SHA256=base.frozen.sha(public/'CANONICAL_CONTEXTS63.npz'),fits=0,wallets=0,provider_downloads=0)
    (public/'CONTEXT_READY.json').write_text(json.dumps(report,indent=2)+'\n');return report


def contexts(contract_path):
    import numpy as np
    contract=base.frozen.read(contract_path);path=contract_path.parent/'CANONICAL_CONTEXTS63.npz';base.frozen.require(base.frozen.sha(path)==contract['canonical_context_SHA256'],'Bound original admitted context differs')
    with np.load(path,allow_pickle=False) as z:c={k:z[k].copy() for k in ('expert_targets','expert_eligible','target_available_us','past_returns30')};order=z['expert_order'].tolist()
    base.frozen.require(order==list(base.E5+(base.SHORT,)),'Original E5 slot names and short append required');c['expert_order']=tuple(order);return c


def provenance(path,m,a,c,contract_path):
    import numpy as np
    require=base.frozen.require;contract=base.frozen.read(contract_path);cal=contract['calendar'];fold=contract['fold']
    require(m['calendar']==cal and m['adapter_contract_sha256']==base.frozen.sha(contract_path),'Explicit new fold contract binding required')
    if m['policy_role']=='FIXED_CONTROL':
        require(m['arm_id'] in ('STATIC50','CASH50') and m['actual_fit_completed_UTC'] is None and m['maximum_training_label_available_us']==m['maximum_scaler_input_available_us']==0,'Fixed rules cannot invent fits')
        plan=base.frozen.read(base.member(path.parent,m['training_plan_file']));require(plan==dict(policy_role='FIXED_CONTROL',fits=0,calendar=cal,control=m['arm_id']) and m['files'][m['training_plan_file']]['sha256']==m['training_plan_sha256'],'Exact bound fixed control plan required');full,_=base.validate(m,a,c,cal);require(np.array_equal(full,base.fixed_control_requests(m['arm_id'],cal)),'Exact source fixed coefficients required');return dict(status='PASS_FIXED_CONTROL_NO_FIT',fits=0)
    require(m['policy_role']=='LEARNED_FROZEN' and m['prefix_evidence_mode']=='PUBLISHED_FRESH_RECEIPT_AND_INDEPENDENT_SOURCE_CLOCKS' and m['producer_commit']==producer.SOURCE_COMMIT and m['allowed_actions']==list(base.COMPACT+(base.SHORT,)),'Exact frozen learned pool/source/prefix role required')
    report,clocks=producer.prefix(path.parent,cal,fold);require(report==base.frozen.read(base.member(path.parent,m['producer_prefix_proof_file'])),'Independent actual prefix receipt differs')
    with np.load(base.member(path.parent,m['training_clock_file']),allow_pickle=False) as z:require(set(z.files)==set(clocks) and all(np.array_equal(z[k],v) for k,v in clocks.items()),'Actual strict prefix sample/scaler clocks differ')
    require(m['maximum_training_label_available_us']==report['maximum_training_label_available_us'] and m['maximum_scaler_input_available_us']==report['maximum_scaler_input_available_us'] and m['training_cutoff_us']==cal['start'],'Actual strict prefix maxima/cutoff differ')
    p=base.member(path.parent,m['producer_manifest_file']);receipt=original.producer_interface(p,m['files'][m['producer_manifest_file']]['sha256']);require(receipt['calendar']==cal,'Actual producer decision/outcome/terminal calendar differs');source=base.frozen.read(p)
    for field,member in [('request_file','REQUESTS.npz'),('model_file','MODEL_ADAM_RNG.pt'),('scaler_file','SCALER.npz')]:require(m['files'][m[field]]['sha256']==source['files'][member]['SHA256'],'Original producer byte identity differs: '+member)
    require(m['files'][m['context_file']]['sha256']==contract['canonical_context_SHA256'],'Actual source context packet binding differs')
    with np.load(p.parent/'CURRENT_CONTEXT63.npz',allow_pickle=False) as z:
        for key in ('expert_targets','expert_eligible','target_available_us'):require(np.array_equal(z[key],c[key]),'Actual full published admitted E6 context differs: '+key)
        require(np.array_equal(z['past_returns30'],c['past_returns30']),'Actual covariance input differs')
    return dict(report,context_SHA256=contract['canonical_context_SHA256'],fits=0)


def readiness(state,contract_path):
    import numpy as np,polars as pl
    contract=base.frozen.read(contract_path);cal=contract['calendar'];fold=contract['fold'];require=base.frozen.require;require(cal==FOLDS[fold],'Declared63 calendar only; no fallback')
    work=base.member(state,contract['market_work_relative']);report=base.source_market_check(state,cal,contract_path,work);base.frozen.modules(state);window=base.market(state,cal,work);n=0
    for block in window['minute_blocks']():
        require(np.array_equal(block['times'],np.arange(cal['start']+n*base.frozen.MINUTE,cal['start']+(n+len(block['times']))*base.frozen.MINUTE,base.frozen.MINUTE)) and set(block['market'])==set(base.frozen.SYMBOLS),'Actual full synchronous trade/mark/quote grid required')
        require(all(all(np.isfinite(v).all() for v in asset.values()) and (asset['quote_volume']>=0).all() and (asset['mark']>0).all() for asset in block['market'].values()),'Actual finite native values required');n+=len(block['times'])
    require(n==90720 and len(window['events'])==945,'Actual63 minutes or funding count differs')
    for symbol in base.frozen.SYMBOLS:
        events=[v for v in window['events'] if v['symbol']==symbol];tt=np.array([v['event_us'] for v in events],np.int64);rate=np.array([v['raw_rate'] for v in events]);slots=(tt//1000000+1)//28800
        require(len(events)==189 and np.array_equal(slots,np.arange(cal['start']//1000000//28800,cal['end_exclusive']//1000000//28800)) and np.isfinite(rate).all() and all(v['reported_interval_hours']==8 for v in events),'Actual signed funding189 slots/asset required; preserve raw jitter')
    contexts(contract_path);report.update(status='PASS_PUBLIC_ACTUAL63_TRADE_MARK_QUOTE_REUSED_DAILY_FUNDING_AND_SOURCE_CONTEXT',fold=fold,calendar=cal,actual_first_capacity=0,external_previous_quote_supplied=False,funding945_actual=True,provider_downloads=0,wallets_run=0);return report


def options(state,contract_path):
    contract=base.frozen.read(contract_path);return dict(calendar=contract['calendar'],contract_path=contract_path,request_schema=original.SCHEMA,provenance_check=lambda p,m,a,c:provenance(p,m,a,c,contract_path),context_override=lambda *a:contexts(contract_path),market_work=base.member(state,contract['market_work_relative']))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('context','readiness','check','run'));p.add_argument('--state',type=Path,required=True);p.add_argument('--fold',choices=tuple(FOLDS),required=True);p.add_argument('--contract',type=Path);p.add_argument('--manifest',type=Path);p.add_argument('--manifest-sha256');p.add_argument('--contract-sha256');p.add_argument('--output',type=Path);p.add_argument('--execution-plan',type=Path);p.add_argument('--execution-plan-sha256');p.add_argument('--plan-commit');a=p.parse_args()
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','POLARS_MAX_THREADS'):os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6000000000,6000000000));resource.setrlimit(resource.RLIMIT_CPU,(600,600))
    def blocked(*a,**kw):raise RuntimeError('Offline frozen transfer63 forbids network')
    socket.create_connection=blocked;socket.socket.connect=blocked
    if a.command=='context':print(json.dumps(prepare_context(a.state,a.fold,a.output)),flush=True);return
    base.frozen.require(a.contract is not None,'Explicit fold contract required; no calendar fallback');report=readiness(a.state,a.contract)
    if a.command=='readiness':print(json.dumps(report),flush=True);return
    base.frozen.require(a.manifest is not None and a.manifest_sha256 is not None and a.contract_sha256 is not None and base.frozen.sha(a.contract)==base.digest(a.contract_sha256),'Actual source-hashed requests and external fold contract SHA required')
    if a.command=='check':print(json.dumps(base.check(a.state,a.manifest,a.manifest_sha256,**options(a.state,a.contract))[3]),flush=True)
    else:
        base.frozen.require(all(v is not None for v in (a.output,a.execution_plan,a.execution_plan_sha256,a.plan_commit)),'Published request-specific plan/fresh output required');plan=base.frozen.read(a.execution_plan);base.frozen.require(plan['authorization']=='USER_AUTHORIZED_REAL_FROZEN63_NATIVE_EVALUATION' and plan['calendar']==FOLDS[a.fold],'Exact authorized fold required');base.run(a.state,a.manifest,a.manifest_sha256,a.output,a.execution_plan,a.execution_plan_sha256,a.plan_commit,**options(a.state,a.contract))


if __name__=='__main__':main()
