"""Independent CPU workers: official model libraries and existing account."""
import json,os,time,resource
from pathlib import Path
import joblib
import numpy as np
import polars as pl
from scipy.stats import rankdata
from quant.paths import ROOT,STATE
from quant import resources
from scripts.research import selector_data as data
from scripts.investment.reuse_cycle_controls import sha

def atomic(path,value):
    p=Path(path);tmp=p.with_name(p.name+'.'+str(os.getpid())+'.tmp')
    def native(v):
        if isinstance(v,np.generic):return v.item()
        raise TypeError(type(v).__name__)
    tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False,default=native)+'\n');tmp.replace(p)

def cv_job(config,run,model,h,unit,fold,placebo=None,seed=0):
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import Ridge
    from sklearn.multioutput import MultiOutputRegressor
    from xgboost import XGBRegressor
    began=time.monotonic();run=Path(run);f=pl.read_parquet(run/'features.parquet');x=f.select(config['features']).to_numpy()
    labels=np.load(run/('labels_'+unit+'_'+str(h)+'.npz'));times=f['decision_us'].to_numpy();start,end=map(data.stamp,config['folds'][fold])
    ti,vi=data.fold_indices(times,labels['label_ends'],h,start,end,config['min_train_rows']);y=labels['relative'][ti]
    assert np.isfinite(y).all() and np.max(f['feature_available_us'].to_numpy()[ti])<=start-h*data.DAY
    xt=x[ti].copy();rng=np.random.default_rng(seed)
    if placebo=='LABEL_SHUFFLE':y=y[rng.permutation(len(y))]
    elif placebo=='FEATURE_SHUFFLE':xt=xt[rng.permutation(len(xt))]
    else:assert placebo is None
    if model=='LINEAR':estimator=make_pipeline(StandardScaler(),Ridge(**config['models']['LINEAR']));fits=1;normalizers=1
    else:
        assert model=='TREE';estimator=MultiOutputRegressor(XGBRegressor(**config['models']['TREE']),n_jobs=1);fits=3;normalizers=0
    key=f'{model}_H{h}_{unit}_F{fold}'+(':'+placebo+':'+str(seed) if placebo else '')
    base=run/'cv'/key.replace(':','_');base.mkdir(parents=True,exist_ok=True);attempts=base/'attempts';attempts.mkdir(exist_ok=True)
    number=len(list(attempts.iterdir()));assert number<config['budget']['max_job_attempts'],'Finite retry budget exhausted'
    directory=attempts/str(number);directory.mkdir();atomic(directory/'started.json',dict(status='STARTED',scalar_fits_reserved=fits,seed=seed,model=model,fold=fold,at=time.time()))
    estimator.fit(xt,y);prediction=estimator.predict(x[vi]);assert prediction.shape==(len(vi),3) and np.isfinite(prediction).all()
    from sklearn.metrics import r2_score
    train_r2=float(r2_score(y,estimator.predict(xt)))
    mature=np.isfinite(labels['relative'][vi]).all(axis=1)
    validation_r2=float(r2_score(labels['relative'][vi[mature]],prediction[mature])) if mature.sum()>=2 else None
    joblib.dump(estimator,directory/'model.joblib')
    np.savez_compressed(directory/'prediction.npz',indices=vi,prediction=prediction)
    result=dict(id=key,model=model,horizon=h,unit=unit,fold=fold,placebo=placebo,seed=seed,train_rows=len(ti),predict_rows=len(vi),
        train_max_feature_us=int(times[ti].max()),train_max_label_available_us=int(labels['label_ends'][ti].max()),validation_start_us=start,
        embargo_days=h,scaler_fit_train_only=True,model_fit_train_only=True,scalar_model_fits=fits,scaler_fits=normalizers,
        prediction=str(directory/'prediction.npz'),prediction_sha256=sha(directory/'prediction.npz'),model_path=str(directory/'model.joblib'),model_sha256=sha(directory/'model.joblib'),
        train_R2=train_r2,validation_mature_R2=validation_r2,
        _binding=json.loads((run/'binding.json').read_bytes()),elapsed_seconds=time.monotonic()-began,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    atomic(directory/'result.json',result);atomic(base/'result.json',result);return result

def prediction_path(config,run,model,h,unit,cv_results):
    run=Path(run);f=pl.read_parquet(run/'features.parquet');times=f['decision_us'].to_numpy();begin=data.stamp(config['validation_start']);end=data.stamp(config['validation_end'])
    ix=np.flatnonzero((times>=begin)&(times<end));pred=np.full((len(times),3),np.nan);seen=set()
    for r in cv_results:
        assert r['model']==model and r['horizon']==h and r['unit']==unit and sha(r['prediction'])==r['prediction_sha256']
        p=np.load(r['prediction']);indices=p['indices'];assert not (seen&set(indices.tolist()));seen.update(indices.tolist());pred[indices]=p['prediction']
    assert seen==set(ix.tolist()) and np.isfinite(pred[ix]).all()
    weights=data.soft_path(pred[ix],config['softmax_temperature'],config['max_daily_L1_change'])
    labels=np.load(run/('labels_'+unit+'_'+str(h)+'.npz'));common=times[ix]<=data.stamp(config['validation_end'])-max(config['horizons'])*data.DAY
    ranks=np.array([(rankdata(row,method='average')-1)/2 for row in labels['utility'][ix[common]]]);score=float(np.mean((weights[common]*ranks).sum(axis=1)))
    return times[ix],weights,score

def account_job(config,run,case_id,unit,weights_path):
    from scripts.investment import perpetual_directional as engine,audit_shared_direction as finance
    from scripts.investment.perpetual_closing_exempt_account import USDTLinearPerpetualAccount
    from scripts.investment.bybit_cost_inputs import snapshot_cost
    from scripts.investment.frozen_expert_mixture import verify
    began=time.monotonic();run=Path(run);destination=run/'accounts'/case_id;destination.mkdir(parents=True,exist_ok=True)
    saved=np.load(weights_path);decisions=saved['decisions'];weights=saved['weights'];assert weights.shape==(len(decisions),3)
    lib=data.library(config);whole=data.window(config);target=data.targets(lib,unit,decisions,weights)
    proof=verify(target,{e:lib[e,unit]['targets.parquet'].filter(pl.col('available_us').is_in(decisions.tolist())) for e in data.EXPERTS},list(data.EXPERTS),decisions,('BTCUSDT',),weights,whole['daily'])
    start=data.stamp(config['validation_start']);end=data.stamp(config['validation_end'])
    assert np.array_equal(decisions,np.arange(start,end,data.DAY))
    window=dict(whole,start=start,end=end,events=[e for e in whole['events'] if start<=e['event_us']<end],minute_blocks=lambda:whole['minute_blocks'](start,end))
    cost=snapshot_cost(ROOT/'docs/input_evidence/BYBIT_USER_FEE_SNAPSHOT_20261004.json',symbols=('BTCUSDT',),fee_zone_by_symbol={'BTCUSDT':'DERIVATIVES_CRYPTO_STANDARD'},
        scenario_id='BASE27',half_spread_bps=4,slippage_bps=4,execution_source_ref='ACCEPTED_BINANCE_USDM_PROXY',execution_status='FIXED_NON_NATIVE_SPREAD_SLIPPAGE_SCENARIO')
    unit_spec=next(v for v in engine.UNITS if v['id']==unit)
    class Progress:
        value={}
        def update(self,phase,completed,total,measure,**metrics):
            if completed is not None and (completed%14400==1 or completed==total):
                atomic(destination/'progress.json',dict(stage=phase,completed=completed,total=total,updated=time.time(),pid=os.getpid()))
    def guard():
        assert time.monotonic()-began<config['budget']['account_wall_seconds']
        assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<config['budget']['worker_RSS_bytes']
    meta=dict(experts=list(data.EXPERTS),selector=case_id,one_shared_full_capital=True,future_informed='ORACLE' in case_id,capital_USDT=10000.,weights_source_sha256=sha(weights_path))
    attempts=destination/'attempts';attempts.mkdir(exist_ok=True)
    number=len(list(attempts.iterdir()));assert number<config['budget']['max_job_attempts'],'Finite account retry budget exhausted'
    attempt=attempts/str(number);attempt.mkdir()
    atomic(attempt/'started.json',dict(status='STARTED',case_id=case_id,unit=unit,at=time.time()))
    result=engine.simulate(window,'LONG_SHORT',cost,unit_spec,Progress(),guard,target_factory=lambda b,d,m:(target,meta),account_factory=USDTLinearPerpetualAccount,persist_cash_close=True)
    artifact_dir=attempt/'ledger';case=engine.save_case(result,artifact_dir);atomic(artifact_dir/'summary.json',case['summary'])
    checked=finance.verify(artifact_dir,('BTCUSDT',),unit_spec['scale']);checked['target_reference']=proof
    assert checked['maximum_NAV_error_USDT']<1e-7 and checked['maximum_wallet_error_USDT']<1e-7
    summary=case['summary'];years={}
    for d in checked['daily_direction_contributions']:
        year=str(__import__('datetime').datetime.fromtimestamp((d['day_end_us']-1)//1000000,__import__('datetime').UTC).year);v=years.setdefault(year,dict(LONG=0.,SHORT=0.,net=0.))
        v['LONG']+=d['LONG'];v['SHORT']+=d['SHORT'];v['net']+=d['LONG']+d['SHORT']
    out=dict(id=case_id,unit=unit,summary=summary,artifacts=case['artifacts'],independent=checked,calendar_year_contribution=years,
        _binding=json.loads((run/'binding.json').read_bytes()),elapsed_seconds=time.monotonic()-began,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,shared_RAM_observed_bytes=resources.status()['ram_current_bytes'])
    atomic(destination/'result.json',out);return out
