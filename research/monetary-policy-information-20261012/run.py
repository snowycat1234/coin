"""Exactly two frozen fits and chronological external-policy feature bundle test."""
import argparse,importlib.util,io,json,time
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from core import DAY,predict,retention,bootstrap
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('original',ROOT/'research/minute-conditional-selector-20261011/experiment.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
ARMS=('PRICE','POLICY');FIT=m.utc('2023-01-01');END=m.utc('2024-01-03')

def paid_utility(net):
    # Existing one-day endpoint MDD/utility; paid money is homogeneous in
    # uniform g for an independent fresh-capital proportional-cost reference.
    r=net/10000.;return np.log1p(r)-.5*np.maximum(-r,0.)

def run(state,source_commit,expected=None):
    m.require(not state.exists() and not m.git('status','--porcelain'),'Fresh STATE and clean frozen source')
    if not expected:m.require(m.git('rev-parse','HEAD').decode().strip()==source_commit,'Published exactfit source')
    m.verify_manifest(HERE/'FIT_SOURCE_SHA256.txt');state.mkdir();started=time.monotonic()
    with np.load(HERE/'input/INPUTS.npz',allow_pickle=False) as z:a={k:z[k].copy() for k in z.files}
    d=a['decision_us'];ix=a['training_indices'];y=a['utility'];x=dict(PRICE=a['price_features'],POLICY=np.column_stack([a['price_features'],a['policy_features']]))
    m.require(len(ix)>=600 and len(np.unique(d[ix]))==len(ix) and np.all(a['true_reward_maturity_us'][ix]<FIT) and np.all(d[ix]<FIT),'True mature >=600actual training dates')
    ev=np.flatnonzero((d>=FIT)&(d<m.utc('2024-01-01')));ed=d[ev]
    m.require(len(ev)==365 and np.all(np.diff(ed)==DAY),'Natural365same-calendar validation')
    known=a['known'][ev];mask=known&a['label_complete'][ev]&(a['true_reward_maturity_us'][ev]<END)
    m.require(mask.sum()>=300 and (a['policy_available_us'][ev]<=ed).all(),'Commonoutcomes/actualannouncedpolicyclock')
    if expected:
        with np.load(io.BytesIO(m.git('show',expected+':research/monetary-policy-information-20261012/result/MODELS.npz')),allow_pickle=False) as z:models={k:z[k].copy() for k in z.files}
        np.testing.assert_array_equal(ix,models['training_indices'])
    else:
        models=dict(training_indices=ix,utility_scale=np.array(max(1e-4,float(y[ix].std()))),training_mean=np.array(y[ix].mean()))
        m.save(state/'ATTEMPT.json',dict(scientific_attempts=1,new_fits=0,original_fits=0,source_commit=source_commit,seed=811500))
        for n,arm in enumerate(ARMS,1):
            train=x[arm][ix];mean=train.mean(0);scale=train.std(0);scale[scale==0]=1.;model=Ridge(alpha=30.).fit((train-mean)/scale,y[ix])
            models[arm+'_mean']=mean;models[arm+'_scale']=scale;models[arm+'_coef']=np.ascontiguousarray(model.coef_);models[arm+'_intercept']=np.array(model.intercept_)
            m.save(state/'ATTEMPT.json',dict(scientific_attempts=1,new_fits=n,original_fits=0,source_commit=source_commit,seed=811500))
        np.savez_compressed(state/'MODELS.npz',**models)
        with np.load(state/'MODELS.npz',allow_pickle=False) as z:models={k:z[k].copy() for k in z.files}
    trainrecords=[];positive={}
    for arm in ARMS:
        loss=(predict(x[arm][ix],models,arm)-y[ix])**2;m.require((loss>0).sum()>=600,'Atleast600positive actualeffective-lossdates PERarm')
        positive[arm]=int((loss>0).sum())
        for j,i in enumerate(ix):trainrecords.append(dict(arm=arm,decision_us=int(d[i]),true_reward_maturity_us=int(a['true_reward_maturity_us'][i]),objective_weight=1.,effective_loss=float(loss[j])))
    pd.DataFrame(trainrecords).to_csv(state/'ACTUAL_TRAIN_DATES.csv',index=False)
    prediction={arm:np.zeros(len(ev)) for arm in ARMS}
    for arm in ARMS:prediction[arm][known]=predict(x[arm][ev[known]],models,arm)
    prediction['TRAIN_MEAN']=np.full(len(ev),float(models['training_mean']))
    losses={arm:(p-y[ev])**2 for arm,p in prediction.items()};mse={arm:float(v[mask].mean()) for arm,v in losses.items()};checks={};blocks={}
    for base in ('PRICE','TRAIN_MEAN'):
        delta=losses[base]-losses['POLICY'];ci=bootstrap(delta,mask);gain=1-mse['POLICY']/mse[base];checks[base]=dict(relative_gain=gain,paired95CI=ci,gate=bool(gain>=.02 and ci[0]>0))
    target={};g={};paid={};rows=[]
    for arm,p in prediction.items():
        g[arm]=retention(p,float(models['utility_scale']),known);target[arm]=g[arm][:,None]*a['benchmark_targets'][ev]
        m.require(np.max(np.abs(target[arm]))<=.3+1e-12 and np.abs(target[arm]).sum(1).max()<=.6+1e-12,'Same risk/caps, no relevering')
        net=g[arm]*a['net_USDT'][ev];paid[arm]=paid_utility(net)
        for j in np.flatnonzero(mask):rows.append(dict(arm=arm,decision_us=int(ed[j]),retention=float(g[arm][j]),utility=float(paid[arm][j]),net_USDT=float(net[j]),fees_USDT=float(g[arm][j]*a['fees_USDT'][ev[j]]),funding_cash_USDT=float(g[arm][j]*a['funding_cash_USDT'][ev[j]])))
    economic={}
    for base in ('PRICE','TRAIN_MEAN'):
        delta=paid['POLICY']-paid[base];ci=bootstrap(delta,mask);economic[base]=dict(mean_increment=float(delta[mask].mean()),paired95CI=ci,gate=bool(ci[0]>0))
    for name,left,right in [('H1','2023-01-01','2023-07-01'),('H2','2023-07-01','2024-01-01')]:
        b=(ed>=m.utc(left))&(ed<m.utc(right));q=mask&b
        blocks[name]=dict(natural_calendar=int(b.sum()),common_mature=int(q.sum()),MSE={arm:float(v[q].mean()) for arm,v in losses.items()},price_minus_policy_MSE=float((losses['PRICE']-losses['POLICY'])[q].mean()),paid_policy_minus_price_mean=float((paid['POLICY']-paid['PRICE'])[q].mean()))
    info=all(v['gate'] for v in checks.values()) and all(b['price_minus_policy_MSE']>0 for b in blocks.values())
    paidmeans={arm:float(v[mask].mean()) for arm,v in paid.items()};econ=all(v['gate'] for v in economic.values()) and paidmeans['POLICY']>0 and all(b['paid_policy_minus_price_mean']>0 for b in blocks.values())
    trainlevels=a['policy_features'][ix,0];trainclock=a['policy_available_us'][ix];changes=np.count_nonzero(np.diff(trainclock));outside=(a['policy_features'][ev,0]<trainlevels.min())|(a['policy_features'][ev,0]>trainlevels.max())
    report=dict(status='PASS_FROZEN_BUNDLE_INCREMENT_NATIVE_READINESS_NEXT' if info and econ else 'STOP_FIXED_MONETARY_BUNDLE_INCREMENT_GATE',source_commit=source_commit,new_model_fits=2,original_model_fits=0,scientific_attempts=1,
        actual_training_dates_per_arm=len(ix),actual_positive_loss_training_dates_per_arm=positive,maximum_train_true_reward_maturity_us=int(a['true_reward_maturity_us'][ix].max()),fit_available_us=FIT,
        natural_validation_dates=len(ev),common_mature_dates=int(mask.sum()),source_unknown_validation_dates=int((~mask).sum()),
        information=dict(MSE=mse,paired=checks,halfyear_blocks=blocks,gate=bool(info)),
        paid_reference=dict(mean_utility=paidmeans,paired=economic,gate=bool(econ),scope='INDEPENDENT_ONE_DAY_CHARGED_REFERENCES_NOT_SUMMED_SHARED_WALLET_INCOME'),
        policy_identification=dict(actual_training_statement_innovations=int(changes),actual_training_policy_intervals=int(len(np.unique(trainclock))),distinct_training_upper_levels=int(len(np.unique(trainlevels))),
          training_upper_range=[float(trainlevels.min()),float(trainlevels.max())],common_eval_upper_outside_training_range_dates=int((outside&mask).sum()),all_eval_upper_outside_training_range_dates=int(outside.sum()),
          conditional_path_bootstrap_not_cross_policy_cycle_stability=True,feature_bundle_includes_negative_return_interaction_missing_from_linear_PRICE=True,
          interpretation='BUNDLE_INCREMENT_NOT_ISOLATED_POLICY_INFORMATION_OR_POLICY_SHOCK_CAUSAL_EFFECT'),
        target_diagnostics={arm:dict(mean_gross=float(np.abs(w).sum(1).mean()),max_gross=float(np.abs(w).sum(1).max()),active_dates=int((np.abs(w).sum(1)>0).sum()),mean_retention=float(g[arm].mean())) for arm,w in target.items()},
        fees_risk_terminal_unchanged=True,forced_short=False,native_accounts=0,old_account_reruns=0,
        native_status='NOT_RUN_INCREMENT_GATES_FAILED' if not(info and econ) else 'NOT_RUN_AWAIT_FROZEN_JAN2023_INPUT_READINESS',
        scope='ALREADY_SEEN2023_CHRONOLOGICAL_CONDITIONAL_DAILY_INFORMATION_PROBE_NOT_NATIVE_CERTIFIED_OR_NEW_OOS')
    np.savez_compressed(state/'VECTORS.npz',decision_us=ed,common_mature_mask=mask,policy_upper_outside_training=outside,**{arm+'_prediction':p for arm,p in prediction.items()},**{arm+'_retention':v for arm,v in g.items()},**{arm+'_targets':v for arm,v in target.items()})
    pd.DataFrame(rows).to_csv(state/'PAID_REFERENCES.csv',index=False);m.save(state/'RESULT.json',report);m.save(state/'TIMING.json',dict(seconds=time.monotonic()-started))
    if expected:
        old=json.loads(m.git('show',expected+':research/monetary-policy-information-20261012/result/RESULT.json'));m.require(report==old,'Exactscientificreport')
        for name in ('ACTUAL_TRAIN_DATES.csv','VECTORS.npz','PAID_REFERENCES.csv'):m.require((state/name).read_bytes()==m.git('show',expected+':research/monetary-policy-information-20261012/result/'+name),'Exactpublic '+name)
        m.save(state/'PUBLIC_RESTORE.json',dict(status='PASS_ZERO_FIT_MONETARY_BUNDLE_RESTORE',artifact_commit=expected,new_fits=0,new_wallets=0,old_account_reruns=0))
    m.require(time.monotonic()-started<120,'120sboundedstat');print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True);p.add_argument('--expected-commit');a=p.parse_args();run(a.state,a.source_commit,a.expected_commit)
