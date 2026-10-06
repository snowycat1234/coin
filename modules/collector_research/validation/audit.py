"""Read-only training audit and outcome-blind complete-data window selection."""
import csv,json,os,re,sys,time
from pathlib import Path
from .runtime import ROOT,WORK,SOURCE,CONFIG,DAY,atomic,sha,progress,kernel_guard
from .data import MODELS,CONTROLS,target_series
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from pipeline.common import load_config,code_digest
from pipeline.normalize import verify_dataset
from pipeline.train import folds_for,market_features,BASE_FEATURES,targets
from pipeline.models import scaler_for,inner_split,transform,build_model

FLAGS=('complete_kline','complete_mark','complete_premium','complete_funding','funding_interval_complete')
MIN_DAYS=30

def segments(stamps,good,minimum=MIN_DAYS):
    """Never splice time across a missing day. Threshold is fixed before PnL."""
    result=[];short=[];left=None
    for i,ok in enumerate(list(good)+[False]):
        if ok and left is None:left=i
        if not ok and left is not None:
            value=(int(stamps[left]),int(stamps[i-1])+DAY,i-left)
            (result if value[2]>=minimum else short).append(value);left=None
    return result,short

def plan(run,status):
    load_config();resources=kernel_guard()
    minimum=CONFIG.get('minimum_days',30)
    binding=json.loads((SOURCE/'BINDING.json').read_text())
    os.environ.update(binding['config'])
    os.environ.update(binding.get('extra_knobs',{}))
    assert binding['pipeline_code_sha256']==code_digest()
    assert binding['dataset_sha256']==sha(WORK/'reports/DATASET_MANIFEST.json')
    progress(status,'核对数据和训练产物',0,2,'规范化数据来源与哈希')
    manifest=verify_dataset()
    symbols=binding['symbols'];studies={};fold_records=[];files={};checks=[];log_audit=[]
    for tag,scale in [('raw_fraction',1.),('raw_percent',.01)]:
        os.environ['FUNDING_RATE_SCALE']=str(scale)
        result=json.loads((SOURCE/tag/'RESEARCH.json').read_text());study=Path(result['study_dir']);studies[tag]=str(study)
        lm_path=WORK/f'data/labels/{tag}/LABEL_MANIFEST.json';lm=json.loads(lm_path.read_text())
        assert lm['source_manifest_sha256']==binding['dataset_sha256']
        sb=json.loads((study/'BINDING.json').read_text());assert sb['label_manifest_sha256']==sha(lm_path)
        assert sb['code_sha256']==code_digest()
        labels={}
        for item in lm['files']:
            assert sha(item['path'])==item['sha256'],'Changed label artifact'
            labels[item['symbol']]=pd.read_parquet(item['path']).reset_index(drop=True)
        labels={s:labels[s] for s in symbols};dates=pd.DatetimeIndex(labels[symbols[0]].dt)
        market=market_features(labels).reset_index(drop=True)
        X={s:pd.concat([d[BASE_FEATURES],market],axis=1).to_numpy('float32') for s,d in labels.items()}
        length=int(binding['config']['LOOKBACK_DAYS']);embargo=int(binding['config']['EMBARGO_DAYS'])
        folds=list(folds_for(dates,labels,length,int(binding['config']['MIN_TRAIN_ASSET_ROWS']),embargo));stored=pd.read_csv(study/'fold_plan.csv')
        assert len(folds)==len(stored) and len(folds)>=4
        for fi,fold in enumerate(folds,1):
            r=stored.iloc[fi-1]
            assert pd.Timestamp(r.start)==fold['start'] and pd.Timestamp(r.end)==fold['end']
            assert int(r.training_rows)==len(fold['train']) and int(r.prediction_rows)==len(fold['valid'])
            assert r.active_assets.split(',')==fold['active']
            if tag=='raw_percent':
                assert fold['active']==fold_records[fi-1]['active']
                assert np.array_equal(dates[fold['calendar']].as_unit('us').asi8+DAY,fold_records[fi-1]['stamps'])
            assert all(dates[i]<fold['start'] and labels[s].label_end_at.iloc[i]<fold['cutoff'] for _,s,i in fold['train'])
            assert all(fold['start']<=dates[i]<fold['end'] for _,s,i in fold['valid'])
            mu,sd=scaler_for(X,fold['train'],length)
            inner,valid=inner_split(fold['train'],dates,{s:list(d.label_end_at) for s,d in labels.items()},embargo)
            if inner and valid:
                boundary=min(dates[i] for _,_,i in valid)-pd.Timedelta(days=embargo)
                assert all(labels[s].label_end_at.iloc[i]<boundary for _,s,i in inner)
            for model in MODELS:
                folder=study/'models'/f'fold{fi}'/model;cp=json.loads((folder/'CHECKPOINT.json').read_text())
                prediction=folder/'predictions.npy';assert sha(prediction)==cp['pred_sha256']
                pred=np.load(prediction,allow_pickle=False);assert pred.shape==(len(fold['valid']),2) and np.isfinite(pred).all()
                for f in cp['models']:
                    p=folder/f['name'];assert sha(p)==f['sha256'];files[str(p)]=f['sha256']
                with np.load(folder/'scaler.npz',allow_pickle=False) as sc:
                    assert np.array_equal(sc['mu'],mu) and np.array_equal(sc['sd'],sd),'Scaler not bound to causal training rows'
                epoch=cp['best_epoch'];assert epoch==0 if model=='PER_ASSET_XGB' else 1<=epoch<=int(binding['config']['EPOCHS'])
                sample=sorted({0,len(pred)//2,len(pred)-1});items=[fold['valid'][j] for j in sample]
                if model=='PER_ASSET_XGB':
                    from xgboost import XGBRegressor
                    reproduced=np.empty((len(items),2))
                    for k,(_,s,i) in enumerate(items):
                        for head in range(2):
                            estimator=XGBRegressor();estimator.load_model(folder/f'{s}_head{head}.json')
                            reproduced[k,head]=estimator.predict(transform(X[s][[i]],mu,sd))[0]
                else:
                    import torch
                    torch.set_num_threads(resources['cpu_count'] if CONFIG.get('resource_policy')=='server' else 4)
                    device='cuda' if CONFIG.get('resource_policy')=='server' and CONFIG.get('audit_device')!='cpu' and torch.cuda.is_available() else 'cpu'
                    if CONFIG.get('audit_device')=='cuda' and device!='cuda':raise RuntimeError('Requested CUDA audit cannot initialize')
                    network=build_model(model,len(mu)*2,len(symbols),length).to(device)
                    network.load_state_dict(torch.load(folder/'weights.pt',map_location=device,weights_only=True));network.eval()
                    x=torch.from_numpy(np.stack([transform(X[s][i-length+1:i+1],mu,sd) for _,s,i in items])).to(device)
                    a=torch.tensor([sid for sid,_,_ in items],device=device)
                    with torch.no_grad():reproduced=network(x,a).cpu().numpy()
                    del network,x,a
                assert np.allclose(reproduced,pred[sample],atol=1e-4,rtol=1e-3),'Saved weights do not reproduce frozen predictions'
                with np.load(study/f'fold{fi}_{model}_targets.npz',allow_pickle=False) as artifact:
                    assert np.array_equal(artifact['decision_us'],dates[fold['calendar']].as_unit('us').asi8+DAY)
                    assert np.array_equal(artifact['weights'],targets('MODEL',pred,fold,labels,symbols))
                files[str(prediction)]=cp['pred_sha256'];files[str(folder/'CHECKPOINT.json')]=sha(folder/'CHECKPOINT.json')
                checks.append(dict(scenario=tag,fold=fi,model=model,training_rows=len(fold['train']),prediction_rows=len(pred),
                    trained_epoch=epoch,finite_predictions=True,past_only_scaler=True,label_maturity_and_embargo=True,
                    saved_weight_prediction_reproduction=True,target_clock_and_weights=True))
            if tag=='raw_fraction':
                stamps=dates[fold['calendar']].as_unit('us').asi8+DAY
                fold_records.append(dict(fold=fi,stamps=stamps,active=fold['active']))
        for model in MODELS+CONTROLS:
            stamps,weights=target_series(study,model,symbols)
            assert np.isfinite(weights).all()
        files[str(study/'TARGETS_MANIFEST.json')]=sha(study/'TARGETS_MANIFEST.json')
        for item in json.loads((study/'TARGETS_MANIFEST.json').read_text())['files']:
            files[str(study/item['name'])]=item['sha256']
        log_path=SOURCE/('module-3.log' if tag=='raw_fraction' else 'module-4.log')
        log=log_path.read_text() if log_path.exists() else ''
        found=re.findall(r'^(?:.*)(Traceback|CUDA out of memory|Nonfinite training loss|Segmentation fault)(?:.*)$',log,re.M)
        assert not found,'Training execution failure remains in log'
        if log_path.exists():assert len(re.findall(r'\bFOLD \d+ (?:PER_ASSET_XGB|TCN_SHARED|GRU_SHARED|TRANSFORMER_SHARED):',log))>=len(folds)*4
        log_audit.append(dict(scenario=tag,training_execution_errors=found if log_path.exists() else 'LOG_NOT_AVAILABLE',baseline_gate_pass=result['promotion_gate_pass'],
            final_fit_expected='NOT_FIT_CANDIDATE_FAILED_BASELINE_GATE' if not result['promotion_gate_pass'] else 'RESEARCH_ONLY'))
    progress(status,'核对数据和训练产物',1,2,f'已核验{len(checks)}个模型折，构建共同完整区间')
    daily={s:pd.read_parquet(WORK/'data/normalized'/f'{s}_daily.parquet').set_index('open_us') for s in symbols}
    windows=[];excluded=[];short=[];requested=0
    for fold in fold_records:
        stamps=fold['stamps'];requested+=len(stamps);good=np.ones(len(stamps),bool)
        reasons=[[] for _ in stamps]
        for s in fold['active']:
            frame=daily[s].reindex(stamps)
            for flag in FLAGS:
                valid=frame[flag].fillna(False).astype(bool).to_numpy();good&=valid
                for i in np.flatnonzero(~valid):reasons[i].append(s+':'+flag)
        complete,tiny=segments(stamps,good,minimum)
        for start,end,days in complete:
            assert end<=1772323200000000
            windows.append(dict(id=f'fold{fold["fold"]}-{pd.Timestamp(start,unit="us",tz="UTC").date()}',fold=fold['fold'],
                start=start,end=end,days=days,active_symbols=fold['active']))
        for start,end,days in tiny:
            short.append(dict(fold=fold['fold'],start=start,end=end,days=days,reason='COMPLETE_BLOCK_SHORTER_THAN_FROZEN_MINIMUM'))
        for i in np.flatnonzero(~good):excluded.append(dict(fold=fold['fold'],day_us=int(stamps[i]),reasons=reasons[i]))
    assert windows,'No complete 30-day validation windows'
    audit=dict(status='PASS',fold_models_checked=len(checks),checks=checks,log_audit=log_audit,
        retrained=False,data_modified=False,labels_role='EXISTING_DAILY_QUANTITY_PROXY_NOT_MINUTE_CERTIFIED',
        scope='ENGINEERING_AND_CAUSALITY_AUDIT_NOT_PROFIT_GUARANTEE',source_run=str(SOURCE))
    atomic(run/'TRAINING_AUDIT.json',audit)
    value=dict(status='FROZEN_BEFORE_NEW_NATIVE_RESULTS',selection_rule=dict(flags=FLAGS,minimum_contiguous_days=minimum,
        universe='EACH_FOLDS_ORIGINAL_PAST_TRAINING_ELIGIBLE_ASSETS',uses_model_pnl=False,uses_future_return=False,
        calendar_role='RETROSPECTIVE_COMPLETE_DATA_DEVELOPMENT_SCREEN_NOT_UNSEEN_OOS',
        account_reset='INDEPENDENT_10000_USDT_PER_WINDOW_NO_RETURN_SPLICING'),
        closing_policy=dict(buffer_days=1,persist_cash_close=True,
            scope='LAST_WINDOW_DAY_ZERO_TARGET_THEN_NATIVE_VOLUME_LIMITED_PAID_REDUCE_ONLY; CLOCK_RETAINED'),
        requested_days=requested,eligible_days=sum(w['days'] for w in windows),excluded_gap_days=excluded,
        excluded_short_blocks=short,windows=windows,studies=studies,symbols=symbols,
        funding_scales=[1.,.01],models=MODELS+CONTROLS,total_cases=len(windows)*16,
        source_binding_sha256=sha(SOURCE/'BINDING.json'),dataset_sha256=binding['dataset_sha256'],reused_artifacts=files)
    atomic(run/'VALIDATION_PLAN.json',value)
    progress(status,'核对数据和训练产物',2,2,f'{len(windows)}完整区间，{value["eligible_days"]}/{requested}天，{value["total_cases"]}案例')
    return value

if __name__=='__main__':
    run=Path(sys.argv[1]);run.mkdir(parents=True,exist_ok=True)
    result=plan(run,run/'plan-progress.json')
    print(json.dumps({k:result[k] for k in ['requested_days','eligible_days','windows','excluded_gap_days','excluded_short_blocks','total_cases']},ensure_ascii=False))
