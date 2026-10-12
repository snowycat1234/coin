"""Two fixed scalar calibrators inside the old training calendar."""
import argparse,importlib.util,io,json,sys,time
from pathlib import Path
import numpy as np
import pandas as pd
from calibration_core import split,omission,utility_scores
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge,LogisticRegression

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PREV=ROOT/'research/short-selection-attribution-20261012'
sys.path.insert(0,str(PREV));spec=importlib.util.spec_from_file_location('attribution',PREV/'run.py');attr=importlib.util.module_from_spec(spec);spec.loader.exec_module(attr);m=attr.m
SEED=811337;CUT=m.utc('2022-04-01');END=m.utc('2022-09-14')

def paired_ci(difference,mask,seed):
    rng=np.random.default_rng(seed);n=len(mask);b=rng.integers(0,n,(1000,int(np.ceil(n/14))))
    ix=((b[:,:,None]+np.arange(14))%n).reshape(1000,-1)[:,:n]
    return np.quantile(np.nanmean(np.where(mask,difference,np.nan)[ix],axis=1),[.025,.975]).tolist()

def risk_targets(source,dates,net):
    out=net.copy()
    for j,t in enumerate(dates):
        own=np.flatnonzero(out[j]!=0)
        if not len(own):continue
        p=int(np.searchsorted(source['close_available_us'],t));past=source['close'][p-30:p+1][:,own]
        m.require(past.shape==(31,len(own)) and np.isfinite(past).all(),'Past-only risk data')
        out[j,own],_=attr.signed_risk_weights(out[j,own],np.diff(past,axis=0)/past[:-1],annual_vol_target=.10)
    m.require(np.abs(out).max()<=.3+1e-12 and np.abs(out).sum(1).max()<=.6+1e-12,'Unchangedcaps');return out

def run(state,source_commit,expected=None):
    m.require(not state.exists() and state.resolve().is_relative_to(Path('/workspace')),'Fresh state')
    m.require(not m.git('status','--porcelain'),'Cleanpublishedsource')
    if not expected:m.require(m.git('rev-parse','HEAD').decode().strip()==source_commit,'Exactpublishedsource')
    m.verify_manifest(HERE/'SOURCE_SHA256.txt');state.mkdir();start=time.monotonic()
    with np.load(PREV/'result/INTERNAL_PACKET.npz',allow_pickle=False) as z:packet={k:z[k].copy() for k in z.files if not k.startswith('full607')}
    roles,source,frames,holes,v,saved,old,full=attr.load();d=packet['decision_us'];clocks=roles.set_index('decision_us').reward_complete_maturity_us
    maturity=np.array([int(clocks.loc[t]) if t in clocks.index else np.iinfo(np.int64).max for t in d],np.int64)
    train,valid=split(d,maturity,packet['complete_mask'],CUT,END);eval_ix=np.flatnonzero((d>=CUT)&(d<END));ed=d[eval_ix]
    p=packet['old_prediction'];margin=(p[:,2]-p[:,:2].max(1))[:,None];y=packet['actual_CS_advantage'];winner=(y>0).astype(int)
    m.require(train.sum()>=60 and len(np.unique(winner[train]))==2,'Adequate causal calibrationprefix')
    models={};fit_times=[]
    if expected:
        with np.load(io.BytesIO(m.git('show',expected+':research/short-score-calibration-20261012/result/MODELS.npz')),allow_pickle=False) as z:models={k:z[k].copy() for k in z.files}
        np.testing.assert_array_equal(models['training_indices'],np.flatnonzero(train))
    else:
        m.save(state/'ATTEMPT.json',dict(attempt=1,calibration_fits_planned=2,completed=0,original_model_fits=0,source_commit=source_commit))
        for name,learner,target in [('UTILITY',Ridge(alpha=30.),y),('PROBABILITY',LogisticRegression(C=1.,solver='lbfgs',max_iter=1000,random_state=SEED),winner)]:
            b=time.monotonic();model=make_pipeline(StandardScaler(),learner);model.fit(margin[train],target[train]);fit_times.append(time.monotonic()-b)
            scaler,fitted=model.steps[0][1],model.steps[1][1]
            for key,value in [('mean',scaler.mean_),('scale',scaler.scale_),('coef',fitted.coef_),('intercept',fitted.intercept_)]:models[name+'_'+key]=np.asarray(value)
            models['training_indices']=np.flatnonzero(train);np.savez_compressed(state/'MODELS.npz',**models)
            m.save(state/'ATTEMPT.json',dict(attempt=1,calibration_fits_planned=2,completed=len(fit_times),original_model_fits=0,seed=SEED,source_commit=source_commit))
            print('CALIBRATOR_FIT_COMPLETE',name,int(train.sum()),flush=True)
    mu=(((margin-models['UTILITY_mean'])/models['UTILITY_scale'])@models['UTILITY_coef'].reshape(1,-1).T).ravel()+models['UTILITY_intercept'].item()
    logit=(((margin-models['PROBABILITY_mean'])/models['PROBABILITY_scale'])@models['PROBABILITY_coef'].T).ravel()+models['PROBABILITY_intercept'].item()
    probability=1/(1+np.exp(-np.clip(logit,-700,700)));mean_y=float(y[train].mean());mean_win=float(winner[train].mean())
    mask=valid[eval_ix];ey=y[eval_ix];truth=winner[eval_ix];base=margin[eval_ix,0];cal=mu[eval_ix]
    uloss=dict(RAW=(base-ey)**2,TRAIN_MEAN=(mean_y-ey)**2,CALIBRATED=(cal-ey)**2)
    ploss=dict(RAW_ALLOCATION=(packet['desired_budget'][eval_ix,2]-truth)**2,TRAIN_MEAN=(mean_win-truth)**2,CALIBRATED=(probability[eval_ix]-truth)**2)
    mse={k:float(x[mask].mean()) for k,x in uloss.items()};brier={k:float(x[mask].mean()) for k,x in ploss.items()}
    uci=paired_ci(uloss['RAW']-uloss['CALIBRATED'],mask,SEED+1);pci=paired_ci(ploss['TRAIN_MEAN']-ploss['CALIBRATED'],mask,SEED+2)
    gain=1-mse['CALIBRATED']/mse['RAW'];ugate=gain>=.02 and uci[0]>0 and mse['CALIBRATED']<mse['TRAIN_MEAN']
    pgate=brier['CALIBRATED']<min(brier['RAW_ALLOCATION'],brier['TRAIN_MEAN']) and pci[0]>0
    eligible=source['expert_eligible'][np.searchsorted(source['decision_us'],ed)].copy();known=v['common_feature_known'][np.searchsorted(source['decision_us'],ed)];eligible[~known,1:]=False
    prior=packet['path_budget'][eval_ix[0]-1];scale=float(old['A_utility_scale']);w=packet['raw_targets'][eval_ix]
    targets={};routing={};costs=[]
    f_index=np.searchsorted(frames[tuple(source['symbol_order'])[0]].available_us.to_numpy(np.int64),ed)
    for arm,scores in [('BASE',p[eval_ix]),('UTILITY_CALIBRATED',utility_scores(p[eval_ix],cal))]:
        budgets,_=attr.budget_path(scores,scale,cash_index=0,eligible=eligible,max_l1=.1,initial=prior)
        net=np.einsum('ne,nek->nk',budgets,w);target=risk_targets(source,ed,net);targets[arm]=target
        if arm=='BASE':np.testing.assert_allclose(target,packet['risk_net'][eval_ix],rtol=1e-13,atol=1e-16)
        negatives=(target<-1e-12).any(1)
        routing[arm]=dict(calendar_dates=len(ed),negative_target_dates=int(negatives.sum()),positive_short_reference_target_dates=int((packet['positive_short'][eval_ix]&negatives).sum()),
            short_target_gross_mean=float(np.maximum(-target,0).sum(1).mean()),below_fixed10USDT_short_asset_dates=int(((target<-1e-12)&(-target*10000<10)).sum()))
        for j in np.flatnonzero(mask):
            result=attr.sleeve_metrics(frames,f_index[j],target[j]);costs.append(dict(arm=arm,decision_us=int(ed[j]),**result))
    costframe=pd.DataFrame(costs);cost_report={arm:{k:float(f[k].mean()) for k in ('utility','net_USDT','price_USDT','fees_USDT','funding_cash_USDT')} for arm,f in costframe.groupby('arm')}
    negative=lambda a:(a<-1e-12).any(1)
    actual_stage=omission(packet['positive_short'],packet['full_CS_best'],p[:,2]>p[:,:2].max(1),negative(packet['desired_net']),negative(packet['path_net']),negative(packet['risk_net']))
    actual_stage[~packet['complete_mask']]='UNKNOWN_TRAINING_LABEL_OR_FEATURE'
    sleeve=pd.read_csv(PREV/'result/TRAIN607_SLEEVE_COSTS.csv');own=sleeve[sleeve.decision_us.isin(d[packet['complete_mask']])]
    original_costs={k:float(own['short_'+k].mean()) for k in ('net_USDT','price_USDT','fees_USDT','funding_cash_USDT')}
    report=dict(status='PASS_INTERNAL_CALIBRATION_SCREEN_ONLY' if ugate and pgate else 'STOP_FIXED_INTERNAL_CALIBRATION_GATE',source_commit=source_commit,
        calibration_fits=2,original_model_fits=0,seed=SEED,train_dates=int(train.sum()),training_max_true_reward_maturity_us=int(maturity[train].max()),fit_available_us=CUT,
        validation_calendar_dates=len(ed),validation_outcome_maturity_cutoff_us=END,common_mature_internal_dates=int(mask.sum()),utility=dict(MSE=mse,relative_gain=gain,paired95CI=uci,gate=bool(ugate)),
        probability=dict(Brier=brier,constant_minus_calibrated95CI=pci,gate=bool(pgate),probability_not_used_as_expected_utility=True),
        actual_original_omission=dict(positive_short_dates=int(packet['positive_short'].sum()),negative_target_present_positive_dates=int((packet['positive_short']&negative(packet['risk_net'])).sum()),
            missing_negative_target_positive_dates=int((packet['positive_short']&~negative(packet['risk_net'])).sum()),first_failing_stage_counts={str(k):int((actual_stage==k).sum()) for k in np.unique(actual_stage)}),
        conditional_short_reference_mean_USDT=original_costs,conditional_target_one_day_mean=cost_report,target_routing=routing,
        native_economic_status='BLOCKED_RAW_FUNDING_UNIT_PASTMARK_CAPACITY_FILTER_MARGIN_PAIDFLAT',new_native_wallets=0,provider_downloads=0,
        external59_validation_used=False,forced_short_fraction=False,scope='TRAINING_INTERNAL_SEEN_CONDITIONAL_PROXY_NOT_CONTINUOUS_INVESTMENT_RETURN')
    pd.DataFrame(dict(decision_us=d[train],true_reward_maturity_us=maturity[train],raw_CS_margin=margin[train,0],utility_target=y[train],win_event=winner[train],objective_weight=1.)).to_csv(state/'CALIBRATION_TRAIN_DATES.csv',index=False)
    costframe.to_csv(state/'PAID_TARGET_REFERENCES.csv',index=False)
    pd.DataFrame(dict(decision_us=d,positive_short_reference=packet['positive_short'],actual_negative_target=negative(packet['risk_net']),attribution=actual_stage)).to_csv(state/'ACTUAL_OMISSION_DATES.csv',index=False)
    np.savez_compressed(state/'VECTORS.npz',decision_us=ed,statistical_mask=mask,utility_prediction=cal,probability=probability[eval_ix],BASE_targets=targets['BASE'],CAL_targets=targets['UTILITY_CALIBRATED'])
    m.save(state/'RESULT.json',report);m.save(state/'TIMING.json',dict(seconds=time.monotonic()-start,calibration_fit_seconds=fit_times))
    if expected:
        old_report=json.loads(m.git('show',expected+':research/short-score-calibration-20261012/result/RESULT.json'));m.require(old_report==report,'Exact scientificcalibrationreport')
        for name in ('CALIBRATION_TRAIN_DATES.csv','PAID_TARGET_REFERENCES.csv','ACTUAL_OMISSION_DATES.csv','VECTORS.npz'):
            m.require(m.git('show',expected+':research/short-score-calibration-20261012/result/'+name)==(state/name).read_bytes(),'Exact restored '+name)
        m.save(state/'PUBLIC_RESTORE.json',dict(status='PASS_ZERO_FIT_INTERNAL_SCORE_CALIBRATION_RESTORE',artifact_commit=expected,new_fits=0,native_wallets=0))
    m.require(time.monotonic()-start<120,'120sbudget');print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True);p.add_argument('--expected-commit');a=p.parse_args();run(a.state,a.source_commit,a.expected_commit)
