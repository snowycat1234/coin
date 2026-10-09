"""Add separate causal short context; never edit the original VOL/CS payload."""
import argparse,hashlib,json,os
from pathlib import Path
import resource,socket,sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import native61 as frozen
import short_regimes


def build(state,output):
    import numpy as np
    import polars as pl
    frozen.modules(state);short_regimes.source_check()
    from scripts.investment import donchian_short_daily_pool_target as short
    original_payload=HERE/'temporal-economics/PRE_MAY_TWO_EXPERT_ECONOMIC_CONTEXTS.npz'
    old_hash=frozen.sha(original_payload)
    frozen.require(old_hash=='66c5fdb2317689ed1d084c3f8eeb6e1781fa04ccc15e6243784a03a3555e7676','Frozen778 context identity differs')
    with np.load(original_payload,allow_pickle=False) as z:
        train=z['decision_us'].copy();episode=z['episode_id'].copy();original_past=z['past_returns30'].copy()
    frozen.require(len(train)==778 and (train<frozen.START).all(),'Exact778 pre-May dates required')
    output.mkdir(parents=True,exist_ok=False)
    source=state/'temporal-feature-transfer/original/source_tables_not_model_inputs/daily_features'
    hashes={};parts=[]
    for s in frozen.SYMBOLS:
        p=source/(s+'.parquet');hashes['training_daily/'+p.name]=frozen.sha(p)
        d=pl.read_parquet(p).filter(pl.col('complete_kline')&pl.all_horizontal([pl.col(k).is_finite() for k in ('open','high','low','close','volume')]))
        d=d.with_columns(pl.lit(s).alias('symbol'),pl.col('dt').dt.epoch('us').alias('open_us'))
        d=d.with_columns((pl.col('open_us')+frozen.DAY).alias('close_us'),(pl.col('open_us')+frozen.DAY).alias('available_us'))
        parts.append(d.select('symbol','open_us','close_us','available_us','open','high','low','close','volume'))
    training_bars=pl.concat(parts)
    # Advance signal state on every daily decision, including days lacking
    # mature outcomes. Outcome/episode boundaries never reset virtual signals.
    full=np.arange(int(train[0]),frozen.START,frozen.DAY,dtype=np.int64)
    frame,_=short.fixed_targets(training_bars,full,symbols=frozen.SYMBOLS)
    selected=frame.filter(pl.col('available_us').is_in(train.tolist()))
    manifests=[]
    for name,tt,own,bars,ids in [('TRAIN778',train,selected,training_bars,episode)]:
        manifests.append(save(output,name,tt,own,bars,ids))
        # Validate the new source path against original covariance contexts;
        # no original targets, identities, masks or economic labels change.
        matrix=[]
        for t in tt:
            cols=[]
            for s in frozen.SYMBOLS:
                d=bars.filter((pl.col('symbol')==s)&(pl.col('close_us')<=t)&(pl.col('available_us')<=t)).sort('close_us').tail(31)
                frozen.require(d.height==31 and np.all(np.diff(d['close_us'].to_numpy())==frozen.DAY),'Missing original30-return context')
                c=d['close'].to_numpy();cols.append(np.diff(c)/c[:-1])
            matrix.append(np.column_stack(cols))
        frozen.require(np.array_equal(np.asarray(matrix),original_past),'Training daily context differs from frozen VOL/CS source')
    root=state/'h1_validation/original/h1_market';parts=[]
    for s in frozen.SYMBOLS:
        p=root/'data/normalized'/(s+'_daily.parquet');hashes['development_daily/'+p.name]=frozen.sha(p)
        d=pl.read_parquet(p).filter(pl.col('complete_kline')&pl.all_horizontal([pl.col(k).is_finite() for k in ('open','high','low','close','volume')]))
        parts.append(d.select('symbol','open_us','close_us','available_us','open','high','low','close','volume'))
    bars=pl.concat(parts);dev=np.arange(frozen.START,frozen.END,frozen.DAY,dtype=np.int64)
    frame,_=short.fixed_targets(bars,dev,symbols=frozen.SYMBOLS)
    manifests.append(save(output,'DEV61',dev,frame,bars,np.zeros(61,np.int64)))
    frozen.require(frozen.sha(original_payload)==old_hash,'Original VOL/CS contexts changed')
    report=dict(schema='SEPARATE_FROZEN_SHORT_EXPERT_CONTEXT_V1',status='PASS_TARGET_ELIGIBILITY_AVAILABILITY_ONLY_NO_POOL_OR_FITS',
        original_three_slot_payload_sha256=old_hash,original_payload_unchanged=True,original_expert_order=['CASH','VOL_MANAGED_HOLD','CSMOM21'],
        new_expert_name='DONCHIAN20_EXIT10_SHORT_ONLY',frozen_recipe_sha256=frozen.sha(frozen.REPO/'scripts/investment/donchian_short_daily_pool_target.py'),
        source_sha256=hashes,contexts=manifests,
        training_state='FRESH_FLAT_AT_FIRST_FROZEN_TRAINING_DATE; ADVANCE_EVERY_CALENDAR_DAY_TO_MAY1; RESET_ONLY_BY_FROZEN_MISSING_OR_EXIT_RULES',
        development_state='FRESH_FLAT_MAY1; ALL61_DECISIONS_CONTINUOUS; MATCHES_FROZEN_NATIVE61_SIGNAL_STATE',
        expert_targets='CAUSAL_UNRAMPED_EXPERT_TARGETS; EXECUTION_RAMP_AND_LAST_DAY_CLOSURE_APPLY_SEPARATELY',
        original_covariance_source_parity='EXACT_ON_ALL778_DATES',publication_clock='HISTORICAL_COMPLETED_DAILY_CLOSE_PROXY_UNCERTIFIED',
        future_labels_included=False,models_fit=0,scalers_fit=0,wallets_run=0,provider_downloads=0,pool_expansion=False)
    (output/'SHORT_CONTEXT_READY.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


def save(output,name,tt,frame,bars,ids):
    import numpy as np
    import polars as pl
    frozen.require(frame.height==len(tt)*5,'Exact selected target rows required')
    weights=frame['target_weight'].to_numpy().reshape(-1,5);raw=frame['raw_signed_target'].to_numpy().reshape(-1,5)
    reasons=frame['eligibility_reason'].to_numpy().reshape(-1,5);eligible=reasons=='ELIGIBLE'
    first=np.zeros((len(tt),5),np.int64);available=np.zeros_like(first)
    for j,s in enumerate(frozen.SYMBOLS):
        d=bars.filter(pl.col('symbol')==s).sort('close_us');clocks=d['close_us'].to_numpy();a=d['available_us'].to_numpy()
        for i,t in enumerate(tt):
            if eligible[i,j]:
                k=int(np.searchsorted(clocks,t));frozen.require(k>=199 and clocks[k]==t and (a[k-199:k+1]<=t).all(),'Unverified causal200 context')
                first[i,j]=clocks[k-199];available[i,j]=int(a[k-199:k+1].max())
    p=output/(name+'_SHORT_CONTEXTS.npz')
    np.savez_compressed(p,decision_us=tt,episode_id=ids,symbol_order=np.array(frozen.SYMBOLS),expert_order=np.array(['DONCHIAN20_EXIT10_SHORT_ONLY']),
        expert_targets=weights[:,None],expert_raw_targets=raw[:,None],expert_eligible=eligible.any(1)[:,None],expert_asset_eligible=eligible[:,None],
        target_available_us=tt[:,None],asset_context_available_us=available,warmup_first_close_us=first,eligibility_reason=reasons)
    return dict(path=p.name,bytes=p.stat().st_size,sha256=frozen.sha(p),dates=len(tt),eligible_asset_dates=int(eligible.sum()),
        availability_i64_sha256=hashlib.sha256(available.tobytes()).hexdigest(),decision_i64_sha256=hashlib.sha256(tt.tobytes()).hexdigest(),
        target_f64_sha256=hashlib.sha256(weights.tobytes()).hexdigest(),raw_f64_sha256=hashlib.sha256(raw.tobytes()).hexdigest())


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','POLARS_MAX_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6000000000,6000000000))
    def blocked(*a,**kw):raise RuntimeError('Offline context generation forbids network')
    socket.create_connection=blocked;socket.socket.connect=blocked
    build(a.state,a.output)
