"""Separate frozen momentum30 short targets, with scalar causal verification."""
import argparse, hashlib, json, os
from pathlib import Path
import resource, socket, sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import native61 as frozen
import momentum_short_challenge as recipe

ORIGINAL_SHA='66c5fdb2317689ed1d084c3f8eeb6e1781fa04ccc15e6243784a03a3555e7676'
EXPERT='MOMENTUM30_SHORT_ONLY'


def source_bars(state):
    import polars as pl
    proof=frozen.read(HERE/'short-contexts/SHORT_CONTEXT_READY.json'); member=frozen.read(state/'temporal-feature-transfer/original/MEMBERS.json')['files']
    parts=[]; hashes={}
    for s in frozen.SYMBOLS:
        name='source_tables_not_model_inputs/daily_features/'+s+'.parquet'
        p=state/'temporal-feature-transfer/original'/name
        frozen.require(frozen.sha(p)==member[name]['SHA256']==proof['source_sha256']['training_daily/'+p.name], 'Frozen actual training source differs')
        hashes['training_daily/'+p.name]=frozen.sha(p)
        d=pl.read_parquet(p).filter(pl.col('complete_kline')&pl.all_horizontal([pl.col(k).is_finite() for k in ('open','high','low','close','volume')]))
        d=d.with_columns(pl.lit(s).alias('symbol'),pl.col('dt').dt.epoch('us').alias('open_us'))
        d=d.with_columns((pl.col('open_us')+frozen.DAY).alias('close_us'),(pl.col('open_us')+frozen.DAY).alias('available_us'))
        parts.append(d.select('symbol','open_us','close_us','available_us','open','high','low','close','volume'))
    train=pl.concat(parts); parts=[]
    for s in frozen.SYMBOLS:
        p=state/'h1_validation/original/h1_market/data/normalized'/(s+'_daily.parquet')
        frozen.require(frozen.sha(p)==proof['source_sha256']['development_daily/'+p.name], 'Frozen development source differs')
        hashes['development_daily/'+p.name]=frozen.sha(p)
        d=pl.read_parquet(p).filter(pl.col('complete_kline')&pl.all_horizontal([pl.col(k).is_finite() for k in ('open','high','low','close','volume')]))
        parts.append(d.select('symbol','open_us','close_us','available_us','open','high','low','close','volume'))
    return train,pl.concat(parts),hashes


def independent(bars,full):
    """Scalar state and covariance; signal advances on every calendar day."""
    import numpy as np
    import polars as pl
    histories={s:bars.filter(pl.col('symbol')==s).sort('close_us') for s in frozen.SYMBOLS}
    state=np.zeros(5,bool); raw=np.zeros((len(full),5)); targets=np.zeros_like(raw); eligible=np.zeros_like(raw,dtype=bool)
    available=np.zeros_like(raw,dtype=np.int64); first=np.zeros_like(available)
    for i,t in enumerate(full):
        valid=[]; returns=[]
        for j,s in enumerate(frozen.SYMBOLS):
            d=histories[s]; clocks=d['close_us'].to_numpy(); a=d['available_us'].to_numpy(); c=d['close'].to_numpy(); k=int(np.searchsorted(clocks,t,side='right')-1)
            good=k>=199 and clocks[k]==t and np.all(np.diff(clocks[k-199:k+1])==frozen.DAY) and (a[k-199:k+1]<=t).all()
            if not good: state[j]=False; continue
            eligible[i,j]=True; first[i,j]=clocks[k-199]; available[i,j]=a[k-199:k+1].max()
            if state[j]:
                if c[k]>=c[k-30]:state[j]=False
            elif c[k]<c[k-30]:state[j]=True
            raw[i,j]=-.12 if state[j] else 0.; valid.append(j); returns.append(np.diff(c[k-30:k+1])/c[k-30:k])
        if valid:
            covariance=np.atleast_2d(np.cov(np.column_stack(returns),rowvar=False,ddof=1))*365
            own=raw[i,valid]; sigma=float(np.sqrt(max(0,own@covariance@own)))
            targets[i,valid]=own*min(1,.1/sigma) if sigma else own
    return raw,targets,eligible,available,first


def build(state,output):
    import numpy as np
    import polars as pl
    frozen.modules(state); recipe.source_check()
    from scripts.investment import momentum_short_pool_target as momentum
    original=HERE/'temporal-economics/PRE_MAY_TWO_EXPERT_ECONOMIC_CONTEXTS.npz'
    frozen.require(frozen.sha(original)==ORIGINAL_SHA,'Original three-slot context changed')
    with np.load(original,allow_pickle=False) as z:
        tt=z['decision_us'].copy(); ids=z['episode_id'].copy(); mask=z['expert_asset_eligible'][:,1].copy(); past=z['past_returns30'].copy()
    frozen.require(len(tt)==778 and (tt<frozen.START).all(),'Exact pre-May778 dates required')
    train,dev,hashes=source_bars(state); output.mkdir(parents=True,exist_ok=False); contexts=[]; checks=[]
    for name,selected,bars,episodes in [('TRAIN778',tt,train,ids),('DEV61',np.arange(frozen.START,frozen.END,frozen.DAY,dtype=np.int64),dev,np.zeros(61,np.int64))]:
        full=np.arange(int(selected[0]),frozen.START if name=='TRAIN778' else frozen.END,frozen.DAY,dtype=np.int64)
        frame,_=momentum.fixed_targets(bars,full,symbols=frozen.SYMBOLS)
        frame=frame.filter(pl.col('available_us').is_in(selected.tolist())); ix=np.searchsorted(full,selected)
        raw,targets,eligible,availability,first=(x[ix] for x in independent(bars,full))
        actual_raw=frame['raw_signed_target'].to_numpy().reshape(-1,5); actual=frame['target_weight'].to_numpy().reshape(-1,5)
        reasons=frame['eligibility_reason'].to_numpy().reshape(-1,5)
        frozen.require(np.array_equal(raw,actual_raw) and np.array_equal(eligible,reasons=='ELIGIBLE') and abs(targets-actual).max()<=1e-14,'Independent momentum state/eligibility/covariance mismatch')
        if name=='TRAIN778':
            frozen.require(np.array_equal(eligible,mask),'Original VOL200-bar per-asset eligibility changed')
            matrix=[]
            for t in selected:
                columns=[]
                for s in frozen.SYMBOLS:
                    d=bars.filter((pl.col('symbol')==s)&(pl.col('close_us')<=t)&(pl.col('available_us')<=t)).sort('close_us').tail(31)
                    frozen.require(d.height==31 and np.all(np.diff(d['close_us'])==frozen.DAY),'Original covariance history missing')
                    c=d['close'].to_numpy(); columns.append(np.diff(c)/c[:-1])
                matrix.append(np.column_stack(columns))
            frozen.require(np.array_equal(np.array(matrix),past),'Original covariance source changed')
        else:
            from scripts.investment.regime_ranking_screen import bounded_path
            import pyarrow.parquet as pq
            budget=bounded_path(np.tile([0.,1.],(61,1)),[1.,0.],.1); expected=actual*budget[:,1,None];expected[-1]*=0
            executed=pq.read_table(state/'momentum-short/MAYJUN2024/account/targets.parquet')['target_weight'].to_numpy().reshape(61,5)
            frozen.require(np.array_equal(expected,executed),'Saved development execution target parity differs')
        p=output/(name+'_MOMENTUM_SHORT_CONTEXTS.npz')
        np.savez_compressed(p,decision_us=selected,episode_id=episodes,symbol_order=np.array(frozen.SYMBOLS),expert_order=np.array([EXPERT]),
            expert_targets=actual[:,None],expert_raw_targets=actual_raw[:,None],expert_eligible=eligible.any(1)[:,None],expert_asset_eligible=eligible[:,None],
            target_available_us=selected[:,None],asset_context_available_us=availability,warmup_first_close_us=first,eligibility_reason=reasons)
        contexts.append(dict(path=p.name,bytes=p.stat().st_size,sha256=frozen.sha(p),dates=len(selected),eligible_asset_dates=int(eligible.sum()),
            decision_i64_sha256=hashlib.sha256(selected.tobytes()).hexdigest(),target_f64_sha256=hashlib.sha256(actual.tobytes()).hexdigest(),raw_f64_sha256=hashlib.sha256(actual_raw.tobytes()).hexdigest()))
        checks.append(dict(role=name,independent_raw_state_error=0,target_maximum_error=float(abs(targets-actual).max()),eligibility_exact=True,
            causal200_contiguous_completed_bars=True,original_covariance_source_exact=name=='TRAIN778',saved_native61_execution_target_exact=name=='DEV61',
            eligible_dates_by_asset=dict(zip(frozen.SYMBOLS,eligible.sum(0).tolist()))))
    frozen.require(frozen.sha(original)==ORIGINAL_SHA,'Original pack was modified')
    report=dict(schema='SEPARATE_FROZEN_MOMENTUM_SHORT_CONTEXTS_V1',status='PASS_EXACT778_61_DATES_CAUSAL_STATE_ELIGIBILITY_RISK_AND_NATIVE61_PARITY',
        contexts=contexts,independent_checks=checks,source_sha256=hashes,recipe_sha256=frozen.sha(frozen.REPO/'scripts/investment/momentum_short_pool_target.py'),
        recipe_plan_commit='05b5804bf26ef983205ad3c4ba1044a693a027ee',engine_sha256=frozen.sha(frozen.REPO/'scripts/investment/resumable_perpetual.py'),
        original_three_slot_payload_sha256=ORIGINAL_SHA,original_pack_unchanged=True,training_state='FRESH_FIRST_FROZEN_DATE_THEN_EVERY_CALENDAR_DAY; ECONOMIC_GAPS_NEVER_RESET_SIGNAL; FROZEN_MISSING_ELIGIBILITY_RESETS_FLAT',
        development_state='FRESH_MAY1_MATCH_SAVED61; SEEN_DEVELOPMENT_EXCLUDED_FROM_CANDIDATE_SELECTION',target_role='UNRAMPED_CAUSAL_EXPERT_TARGET_AND_MASK_ONLY; BUDGET_RAMP_AND_NATIVE_EXECUTION_REMAIN_SEPARATE',
        publication_clock='UNCERTIFIED_HISTORICAL_COMPLETED_DAILY_CLOSE_PROXY',future_labels_included=False,models_fit=0,wallets_run=0,provider_downloads=0)
    (output/'MOMENTUM_CONTEXT_READY.json').write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','POLARS_MAX_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6000000000,6000000000));resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    def blocked(*a,**kw):raise RuntimeError('Offline context generation forbids network')
    socket.create_connection=blocked;socket.socket.connect=blocked
    build(a.state,a.output)
