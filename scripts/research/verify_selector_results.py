"""Read-only scalar reference review of the completed, frozen selector DAG."""
import hashlib,json,math,os,time,resource
from pathlib import Path
import joblib,numpy as np,polars as pl
from quant.paths import ROOT,STATE
from scripts.research.selector_jobs import atomic

DAY=86400000000
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def close(a,b,tol=1e-7):
    assert math.isfinite(a) and math.isfinite(b) and abs(a-b)<=tol,(a,b)
def main():
    began=time.monotonic();source=ROOT/'reports/SELECTOR_ML_RESULTS.json';r=json.loads(source.read_bytes())
    assert r['status']=='COMPLETE_SELECTOR_ML_DAG_DEVELOPMENT_ONLY'
    c=r['config'];run=Path(c['run_dir']);assert run.is_relative_to(STATE)
    assert sha(ROOT/'configs/selector_v1_runtime_fix.yaml')==r['binding']['config_sha256']
    for name,digest in r['binding']['source_hashes'].items():assert sha(ROOT/name)==digest,name
    assert sha(ROOT/'state/dataset_lock.json')==c['data']['locked_sha256']
    f=pl.read_parquet(run/'features.parquet');times=f['decision_us'].to_numpy();x=f.select(c['features']).to_numpy()
    assert np.all(f['feature_available_us'].to_numpy()<=times) and len(times)==730
    assert sha(run/'features.parquet')==r['features']['sha256']
    # Reconstruct every utility label directly from the original expert NAVs.
    producers=json.loads((ROOT/c['data']['oracle_library']['path']).read_bytes())['producers'];navs={}
    for ref in producers:
        assert sha(ROOT/ref['path'])==ref['sha256']
        for case in json.loads((ROOT/ref['path']).read_bytes())['cases']:
            wanted='CASH' if case['strategy']=='CASH' else 'LONG_ONLY' if case['strategy']=='HOLD' else 'LONG_SHORT'
            if case['strategy'] in c['experts'] and case['mode']==wanted:
                a=case['artifacts']['daily_nav.parquet'];assert sha(a['path'])==a['sha256']
                frame=pl.read_parquet(a['path']).sort('day_end_us');assert np.array_equal(frame['day_end_us'].to_numpy()-DAY,times)
                navs[case['strategy'],case['unit']]=[10000.,*frame['nav'].to_list()]
    assert len(navs)==6
    labels_checked=0
    for unit in c['units']:
        for h in c['horizons']:
            saved=np.load(run/f'labels_{unit}_{h}.npz');assert np.array_equal(saved['label_ends'],times+h*DAY)
            for i in range(730):
                if i+h>730:assert np.isnan(saved['utility'][i]).all() and np.isnan(saved['relative'][i]).all();continue
                row=[navs[e,unit][i+h]/navs[e,unit][i]-1 for e in c['experts']];center=math.fsum(row)/3
                for j,v in enumerate(row):close(v,float(saved['utility'][i,j]),1e-12);close(v-center,float(saved['relative'][i,j]),1e-12)
                labels_checked+=1
    fits=r['fit_records'];assert len(fits)==380 and len({v['id'] for v in fits})==380
    assert sum(v['scalar_model_fits'] for v in fits)==r['actual_scalar_model_fits']==440
    assert sum(v['scaler_fits'] for v in fits)==r['actual_scaler_fits']==350
    starts=list((run/'cv').glob('*/attempts/*/started.json'));assert len(starts)==380 and not r['unfinished_fit_attempts']
    scaler_max_error=0.;chronology=[]
    for item in fits:
        assert item['model_fit_train_only'] and item['scaler_fit_train_only']
        assert item['train_max_label_available_us']<=item['validation_start_us']-item['horizon']*DAY
        assert item['train_max_feature_us']<=item['train_max_label_available_us']-item['horizon']*DAY
        for name,digest in [('prediction',item['prediction_sha256']),('model_path',item['model_sha256'])]:assert sha(item[name])==digest
        if item['placebo'] is None and item['model']=='LINEAR':
            train=times+2*item['horizon']*DAY<=item['validation_start_us'];assert train.sum()==item['train_rows']
            scaler=joblib.load(item['model_path']).steps[0][1];assert int(scaler.n_samples_seen_)==int(train.sum())
            for j in range(x.shape[1]):
                values=x[train,j];mean=math.fsum(float(v) for v in values)/len(values)
                error=abs(mean-float(scaler.mean_[j]));scaler_max_error=max(error,scaler_max_error);assert error<1e-12
        if item['placebo'] is None:chronology.append({k:item[k] for k in ('model','horizon','unit','fold','train_rows','train_R2','validation_mature_R2')})
    rows=r['rows'];assert len(rows)==158 and len({v['id'] for v in rows})==158 and all(v['complete'] for v in rows)
    artifact_bytes=0;worker_peak=0;max_wallet=max_nav=0.;economic={}
    for n,row in enumerate(rows):
        assert row['initial_capital']==10000 and row['wallet_error']<1e-7 and row['NAV_error']<1e-7
        max_wallet=max(max_wallet,row['wallet_error']);max_nav=max(max_nav,row['NAV_error'])
        for name,a in row['artifacts'].items():
            p=Path(a['path']);assert p.is_relative_to(run) and p.stat().st_size==a['bytes'] and sha(p)==a['sha256'];artifact_bytes+=a['bytes']
        close(row['gross_PnL']-row['fees']-row['execution']+row['funding'],row['net_PnL'])
        close(math.fsum(v['net_contribution'] for v in row['direction'].values()),row['net_PnL'])
        close(math.fsum(v['net'] for v in row['calendar_year'].values()),row['net_PnL'])
        nav=pl.read_parquet(row['artifacts']['daily_nav.parquet']['path']).sort('day_end_us');assert nav.height==457
        assert np.array_equal(nav['day_end_us'].to_numpy(),np.arange(times[273]+DAY,times[-1]+2*DAY,DAY))
        values=[10000.,*nav['nav'].to_list()];returns=[b/a-1 for a,b in zip(values,values[1:])];mean=math.fsum(returns)/457
        vol=math.sqrt(math.fsum((v-mean)**2 for v in returns)/456)*math.sqrt(365)
        close(values[-1]-10000,row['net_PnL']);close(vol,row['volatility'],1e-12)
        close(mean*365/vol if vol else 0.,row['Sharpe'],1e-10);close((values[-1]/10000)**(365/457)-1,row['annualized_return'],1e-12)
        raw=json.loads((run/'accounts'/row['id']/'result.json').read_bytes());worker_peak=max(worker_peak,raw['peak_RSS_bytes'])
        if row['id'].startswith(('LINEAR_H60_','HOLD_','SMA200_SIGNED_','STATIC_','ORACLE_H60_')):economic[row['id']]=dict(net=row['net_PnL'],gross=row['gross_PnL'],fees_execution=row['fees']+row['execution'],funding=row['funding'],years=row['calendar_year'],volatility=vol,MDD=row['MDD'],Sharpe=row['Sharpe'])
        if n%10==0:print(f'[REFERENCE {n+1}/158] artifact SHA, wallet bridges and scalar metrics',flush=True)
    for d in r['decisions']:
        by={v['id']:v for v in rows if v['unit']==d['unit']};winner=by[d['selected_model']+'_'+d['unit']];base=by[d['best_static_id']];oracle=by[d['oracle_id']]
        close((winner['net_PnL']-base['net_PnL'])/(oracle['net_PnL']-base['net_PnL']),d['capture_ratio'],1e-12)
        assert d['capture_ratio']<0 and not d['pass_development_screen'] and d['year_checks']=={'2022':True,'2023':False}
    assert r['investment_candidate']=='NONE_CASH' and r['FINAL_LOCKED_TEST']=='NOT_RUN_NOT_AUTHORIZED'
    receipt=dict(status='PASS_FROZEN_SELECTOR_REFERENCE_NO_PROMOTION',task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),results_sha256=sha(source),
        source_binding=r['binding'],utility_labels_checked=labels_checked,normalizer_train_only_scalar_max_error=scaler_max_error,fit_attempts=len(starts),
        actual_scalar_fits=440,actual_scaler_fits=350,accounts_checked=158,artifact_bytes_SHA_checked=artifact_bytes,maximum_wallet_error_USDT=max_wallet,maximum_NAV_error_USDT=max_nav,
        worker_peak_RSS_bytes=worker_peak,primary_chronology=chronology,economic=economic,locked_body_read=False,new_model_fits=0,new_backtests=0,
        caution=['SEEN_INTERNAL_VALIDATION_NOT_INDEPENDENT','Champion selected among six on same validation; placebo not selection-adjusted','16 shuffle replicates: empirical95 quantile is not p<.05 proof; minimum finite p=1/17','Only2022Q4 short capture; direction ratio>1 not a global oracle bound','Funding units and Bybit native execution remain conditional'],
        elapsed_seconds=time.monotonic()-began,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    atomic(ROOT/'reports/SELECTOR_ML_INDEPENDENT_REVIEW_20261006_V1.json',receipt)
    print(json.dumps({k:receipt[k] for k in ('status','accounts_checked','actual_scalar_fits','maximum_wallet_error_USDT','maximum_NAV_error_USDT','elapsed_seconds')}))
if __name__=='__main__':main()
