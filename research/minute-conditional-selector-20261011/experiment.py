"""One fixed three-fit conditional-information diagnostic; no native wallet."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

import numpy as np
import pandas as pd
import polars as pl

from modules.collector_research.pipeline.economics import interval_arrays, replay
from scripts.research.conditional_selector_core import (
    DAY_US, UtilitySelector, budget_path, chronological_training_mask,
    nonoverlap_indices, shared_targets,
)
from scripts.research.conditional_selector_inputs import LATENCY_US, reference_utility
from scripts.investment.public_sma_perpetual import signed_risk_weights

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
NAMES=('CASH','VOL_MANAGED_HOLD','CSMOM21')
SEED=811134; BOOTSTRAP_SEED=811135; COST=.00135; CAPITAL=10000.
EXECUTION_DELAY_US=60_000_001


def utc(s):return int(pd.Timestamp(s,tz='UTC').value//1000)
def digest(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT)
def save(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+'\n')
def require(v,message):
    if not bool(v):raise ValueError(message)


def verify_manifest(path):
    for line in path.read_text().splitlines():
        sha,name=line.split(maxsplit=1)
        require(digest((ROOT/name).read_bytes())==sha,'Source identity: '+name)


def risk_features(w,rv1,rv5,plus,minus,covariance):
    """Known completed-day risk conditioned on signed CS exposure, no prices filled."""
    w=np.asarray(w,float);covariance=np.asarray(covariance,float)
    n,k=w.shape; out=np.full((n,3),np.nan)
    require(covariance.shape==(n,k,k),'Ordered covariance shape')
    for i in range(n):
        own=np.flatnonzero(w[i]!=0.)
        if not len(own):
            out[i]=0. # exact known zero exposure, not a missing-source estimate
            continue
        a=w[i,own]; r1=np.asarray(rv1)[i,own];r5=np.asarray(rv5)[i,own]
        adverse=np.where(a>0,np.asarray(minus)[i,own],np.asarray(plus)[i,own])
        c=covariance[i][np.ix_(own,own)]
        if not np.isfinite(np.r_[r1,r5,adverse,c.ravel()]).all():continue
        require((r1>=0).all() and (r5>=0).all() and (adverse>=0).all(),'Nonnegative source risk')
        require(np.allclose(c,c.T,rtol=0,atol=1e-14),'Symmetric synchronized covariance')
        den1=float(np.sum(a*a*r1));den5=float(np.sum(a*a*r5))
        diag=float(np.sum(a*a*np.diag(c)))
        if min(den1,den5,diag)<=0:continue
        out[i]=[np.log(den1/den5),np.sum(a*a*adverse)/den1,(a@c@a-diag)/diag]
    return out


def design(source):
    w=source['targets'];n=len(w)
    risk=risk_features(w[:,2],source['RV_1m'],source['RV_5m'],source['RSplus_1m'],source['RSminus_1m'],source['realized_covariance'])
    a=np.column_stack([source['baseline'],w.reshape(n,-1),source['expert_eligible'],source['asset_eligible'].reshape(n,-1)]).astype(float)
    x={'A':a,'B':np.column_stack([a,risk[:,:2]]),'C':np.column_stack([a,risk])}
    # The common feature support is independent of all future quality/labels.
    known=source['baseline_ready']&np.isfinite(x['C']).all(1)
    return x,known,risk


def owned_gap(decision,weights,symbols,holes):
    """Outcome quality only. It never changes today's budget or targets."""
    left=int(decision)+EXECUTION_DELAY_US; right=left+DAY_US
    for row in holes:
        j=symbols.index(row['symbol']);completion=int(row['open_ms'])*1000+60_000_000
        # A missing boundary mark also prevents certifying newly owned risk.
        if weights[j]!=0 and left-1<=completion<=right:
            return dict(symbol=row['symbol'],missing_open_ms=int(row['open_ms']),
                        known_at_us=completion,status='UNKNOWN_HELD_MARK_AT_COMPLETION')
    return None


def one_day_labels(frames,decisions,targets,eligible,holes,symbols):
    """Same fixed expert utilities with paid proxy entry and terminal exit."""
    d=np.asarray(decisions,np.int64);w=np.asarray(targets,float)
    available=frames[symbols[0]].available_us.to_numpy(np.int64)
    for s in symbols:
        require(np.array_equal(frames[s].available_us,available),'Full common economic calendar')
        require(np.all(np.diff(available)==DAY_US),'No compressed source clock')
    indices=np.searchsorted(available,d)
    require(np.array_equal(available[indices],d),'Exact decision/economic source alignment')
    n,e,_=w.shape
    y=np.full((n,e),np.nan);ret=y.copy();fees=y.copy();funds=y.copy();mdd=y.copy()
    reason=np.full((n,e),'OUTSIDE_COMPLETE_BOUNDARY',dtype='U48')
    for i,index in enumerate(indices):
        y[i,0]=ret[i,0]=fees[i,0]=funds[i,0]=mdd[i,0]=0.;reason[i,0]='ANALYTIC_CASH'
        if index+2>=len(available):continue
        for expert in range(1,e):
            if not eligible[i,expert]:reason[i,expert]='TARGET_NOT_AVAILABLE';continue
            if owned_gap(d[i],w[i,expert],symbols,holes):
                reason[i,expert]='UNKNOWN_HELD_MARK_AT_COMPLETION';continue
            # The existing proxy checks only touched/owned assets; unrelated
            # missing zero-exposure sources cannot create fictitious cash costs.
            arrays=[interval_arrays(frames[s],np.asarray([index]),1.) for s in symbols]
            holding=w[i,expert]!=0
            p0,p1,fp,good=[np.stack([a[k] for a in arrays],axis=1)[0] for k in range(4)]
            valid=(np.isfinite(p0)&(p0>0)&np.isfinite(p1)&(p1>0)&np.isfinite(fp)&good)
            if np.any(holding&~valid):reason[i,expert]='UNKNOWN_OWNED_PRICE_OR_FUNDING';continue
            metrics,_=replay(frames,np.asarray([index]),w[i,expert][None,:],1.,COST,CAPITAL)
            y[i,expert]=reference_utility(metrics);ret[i,expert]=metrics['net_return']
            fees[i,expert]=metrics['fees'];funds[i,expert]=metrics['funding'];mdd[i,expert]=metrics['mdd']
            reason[i,expert]='COMPLETE_CONDITIONAL_REFERENCE'
    return dict(utility=y,label_available_us=d+DAY_US+LATENCY_US,label_complete=np.isfinite(y),
                label_net_return=ret,label_fees_USDT=fees,label_funding_USDT=funds,label_daily_mdd=mdd,
                label_reason=reason)


def paired_statistics(d,labels,prediction,known):
    """Bootstrap whole date vectors on the original calendar, never asset IID."""
    blocks=[('H12022','2022-01-02','2022-07-01'),('H22022','2022-07-02','2022-12-01')]
    reports=[];all_pass=True
    for name,left,right in blocks:
        own=(d>=utc(left))&(d<utc(right))&(labels['label_available_us']<utc(right))
        rows=np.flatnonzero(own);complete=known[rows]&labels['label_complete'][rows].all(1)
        losses={k:np.mean((prediction[k][rows,1:]-labels['utility'][rows,1:])**2,axis=1) for k in prediction}
        require(int(complete.sum())>=40,'Insufficient common diagnostic date vectors')
        rng=np.random.default_rng(BOOTSTRAP_SEED)
        # Draw calendar blocks before applying outcome-quality support. Missing
        # dates retain their actual locations and cannot turn into adjacency.
        starts=rng.integers(0,len(rows),size=(1000,int(np.ceil(len(rows)/7))))
        samples=((starts[:,:,None]+np.arange(7))%len(rows)).reshape(1000,-1)[:,:len(rows)]
        comparisons={};means={k:float(v[complete].mean()) for k,v in losses.items()}
        for base in ('A','B'):
            delta=np.where(complete,losses[base]-losses['C'],np.nan)
            boot=np.nanmean(delta[samples],axis=1);ci=np.quantile(boot,[.025,.975])
            improvement=float(delta[complete].mean()/means[base])
            passed=improvement>=.02 and ci[0]>0;all_pass=all_pass and passed
            comparisons[base]=dict(relative_MSE_reduction_C=improvement,paired_MSE_difference_95CI=ci.tolist(),gate_pass=bool(passed))
        reports.append(dict(block=name,calendar_dates=len(rows),common_statistical_dates=int(complete.sum()),
            unknown_or_feature_missing_dates=int((~complete).sum()),MSE=means,comparisons=comparisons,
            score_scope='CONDITIONAL_COMMON_LABEL_DATES_NOT_A_COMPLETE_FINANCIAL_PATH'))
    return dict(status='PASS_FIXED_PAIRED_INFORMATION_GATE' if all_pass else 'STOP_FIXED_PAIRED_INFORMATION_GATE',
                blocks=reports,bootstrap=dict(seed=BOOTSTRAP_SEED,replicates=1000,block_calendar_days=7,
                interval='percentile95',sampling_unit='whole_date_nonCASH_utility_vector'))


def routed_targets(source,prediction,known,scales,holes):
    d=source['decision_us'];symbols=tuple(source['symbol_order']);eval_mask=d>=utc('2022-01-01')
    ed=d[eval_mask];w=source['targets'][eval_mask];names=NAMES
    # The old combiner expects a complete canonical target frame. These rows are
    # already materialized intents (including true zero targets). Actual expert
    # eligibility is retained separately and enforced before budget allocation.
    frames={name:pl.DataFrame([dict(available_us=int(t),symbol=s,target_weight=float(w[i,e,j]),
            raw_signed_target=float(w[i,e,j]),eligibility_reason='ELIGIBLE')
            for i,t in enumerate(ed) for j,s in enumerate(symbols)]) for e,name in enumerate(names)}
    target_outputs={};budget_outputs={};diagnostics={}
    available=source['close_available_us'];close=source['close']
    for arm in ('A','B','C'):
        scores=np.where(np.isfinite(prediction[arm][eval_mask]),prediction[arm][eval_mask],0.)
        eligible=source['expert_eligible'][eval_mask].copy()
        eligible[~known[eval_mask],1:]=False
        budgets,budget_proof=budget_path(scores,scales[arm],cash_index=0,eligible=eligible,initial=np.array([1.,0.,0.]),max_l1=.1)
        netted,leg_proof=shared_targets(frames,names,ed,symbols,budgets)
        weights=netted['target_weight'].to_numpy().reshape(len(ed),len(symbols)).copy()
        risk_downscales=0;peak_sigma=0.
        for i,t in enumerate(ed):
            own=np.flatnonzero(weights[i]!=0.)
            if not len(own):continue
            j=int(np.searchsorted(available,t));past=close[j-30:j+1][:,own]
            require(j>=30 and available[j]==t and past.shape==(31,len(own)) and np.isfinite(past).all(),
                    'Owned target must have known native past30 risk context')
            returns=np.diff(past,axis=0)/past[:-1]
            before=weights[i,own].copy();after,proof=signed_risk_weights(before,returns,annual_vol_target=.10)
            weights[i,own]=after;risk_downscales+=int(not np.array_equal(before,after))
            covariance=np.atleast_2d(np.cov(returns,rowvar=False,ddof=1))*365
            peak_sigma=max(peak_sigma,float(np.sqrt(max(0.,after@covariance@after))))
        require(np.abs(weights).max()<=.3+1e-12 and np.abs(weights).sum(1).max()<=.6+1e-12 and peak_sigma<=.1+1e-10,'Final shared target caps/risk')
        first=None
        for t,row in zip(ed,weights):
            gap=owned_gap(t,row,symbols,holes)
            if gap:
                first=dict(decision_us=int(t),**gap);break
        target_outputs[arm]=weights;budget_outputs[arm]=budgets
        diagnostics[arm]=dict(calendar_predictions=len(ed),feature_unknown_dates=int((~known[eval_mask]).sum()),
            mean_target_gross=float(np.abs(weights).sum(1).mean()),maximum_target_gross=float(np.abs(weights).sum(1).max()),
            sum_absolute_target_changes=float(np.abs(np.diff(np.vstack([np.zeros((1,5)),weights]),axis=0)).sum()),
            maximum_past30_signed_covariance_annual_vol=peak_sigma,risk_downscaled_dates=risk_downscales,
            budget_eligibility_forced_dates=int((np.asarray(budget_proof['forced_eligibility_L1'])>0).sum()),
            allocated_leg_gross_max=float(max(leg_proof['allocated_leg_gross'])),
            first_uncertifiable_owned_mark=first,
            financial_path_status='STOP_UNKNOWN_OWNED_MARK' if first else 'NOT_RUN_NATIVE_CERTIFICATION_BLOCKED',
            scope='CAUSAL_NETTED_TARGETS_ONLY_NO_FILLS_OR_NAV_OR_SUMMED_EXPERT_PROFITS')
    return dict(eval_decision_us=ed,**{k+'_targets':v for k,v in target_outputs.items()},
                **{k+'_budgets':v for k,v in budget_outputs.items()}),diagnostics


def restore_prediction(x,known,d,models,arm):
    p=np.full((len(d),3),np.nan);own=known&(d>=utc('2022-01-01'))
    p[own]=((x[arm][own]-models[arm+'_mean'])/models[arm+'_scale'])@models[arm+'_coef'].T+models[arm+'_intercept']
    return p


def load_inputs(path):
    preparation=json.loads((path/'PREPARATION.json').read_bytes())
    require(preparation['status']=='PASS_SOURCE_PARITY_AND_COST_FRAME_RECOVERY','Source parity must precede labels/fits')
    require(digest((path/'SOURCE_PREPARED.npz').read_bytes())==preparation['prepared_SHA256'],'Prepared identity')
    for name,sha in preparation['artifacts'].items():require(digest((path/name).read_bytes())==sha,'Economic source identity')
    with np.load(path/'SOURCE_PREPARED.npz',allow_pickle=False) as a:source={k:a[k].copy() for k in a.files}
    symbols=tuple(source['symbol_order']);frames={s:pd.read_parquet(path/(s+'_ECONOMIC_SOURCE.parquet')) for s in symbols}
    coverage=json.loads((path/'MARK_COVERAGE.json').read_bytes())
    require(coverage['missing_source_minutes'] and len(coverage['missing_source_minutes'])==27,'Source-bound real holes')
    return source,frames,coverage['missing_source_minutes'],preparation


def run(state,source_commit,artifact_commit=None):
    require(not state.exists() and state.resolve().is_relative_to(Path('/workspace')),'Fresh bounded STATE')
    verify_manifest(HERE/'FIT_SOURCE_SHA256.txt');verify_manifest(HERE/'INPUT_SHA256.txt')
    state.mkdir();began=time.monotonic();cold=artifact_commit is not None
    if cold:
        for sub in ('input','result'):
            folder=state/sub;folder.mkdir()
            names=git('ls-tree','-r','--name-only',artifact_commit,'research/minute-conditional-selector-20261011/'+sub).decode().splitlines()
            require(names,'Public artifact folder missing')
            for name in names:(folder/Path(name).name).write_bytes(git('show',artifact_commit+':'+name))
        input_path=state/'input'
    else:
        require(git('rev-parse','HEAD').decode().strip()==source_commit and not git('status','--porcelain'),'Published clean fit source')
        input_path=HERE/'input'
    source,frames,holes,preparation=load_inputs(input_path);d=source['decision_us'];x,known,risk=design(source)
    labels=one_day_labels(frames,d,source['targets'],source['expert_eligible'],holes,tuple(source['symbol_order']))
    mask=chronological_training_mask(d,labels['label_available_us'],known&labels['label_complete'].all(1),utc('2022-01-01'),embargo_days=1)
    training=nonoverlap_indices(d,labels['label_available_us'],mask)
    require(len(training)>=40,'At least40 disjoint mature training intervals')
    models={};prediction={};scales={};fit_seconds=[]
    if cold:
        with np.load(state/'result/MODELS.npz',allow_pickle=False) as a:models={k:a[k].copy() for k in a.files}
        require(np.array_equal(models['training_indices'],training),'Restored training support')
    else:
        save(state/'ATTEMPT.json',dict(scientific_attempts=1,source_commit=source_commit,fit_calls_completed=0,
            protocol_SHA256=digest((HERE/'PROTOCOL.json').read_bytes()),seed=SEED,models=['A','B','C'],alpha=30.))
        models['training_indices']=training
    for arm in ('A','B','C'):
        if not cold:
            b=time.monotonic()
            model=UtilitySelector('RIDGE',SEED).fit(x[arm],labels['utility'],d,labels['label_available_us'],mask,utc('2021-12-31'),
                fit_available_us=utc('2022-01-01'),feature_available_us=d,feedback_available_us=np.zeros(len(d),dtype=np.int64))
            require(np.array_equal(model.training_indices,training),'Same paired training support')
            scaler,ridge=model.model.steps[0][1],model.model.steps[1][1]
            for key,value in [('mean',scaler.mean_),('scale',scaler.scale_),('coef',ridge.coef_),('intercept',ridge.intercept_),('utility_scale',np.asarray(model.utility_scale))]:
                models[arm+'_'+key]=value
            own=known&(d>=utc('2022-01-01'))
            expected=model.predict(x[arm][own],d[own],feature_available_us=d[own],feedback_available_us=np.zeros(own.sum(),dtype=np.int64))
            restored=restore_prediction(x,known,d,models,arm)
            np.testing.assert_array_equal(restored[own],expected)
            fit_seconds.append(time.monotonic()-b)
            save(state/'ATTEMPT.json',dict(scientific_attempts=1,source_commit=source_commit,fit_calls_completed=len(fit_seconds),
                protocol_SHA256=digest((HERE/'PROTOCOL.json').read_bytes()),seed=SEED,models=['A','B','C'],alpha=30.))
            print('FIT_COMPLETE',arm,'disjoint_dates',len(training),flush=True)
        prediction[arm]=restore_prediction(x,known,d,models,arm)
        scales[arm]=float(models[arm+'_utility_scale'])
    scores=paired_statistics(d,labels,prediction,known)
    targets,routing=routed_targets(source,prediction,known,scales,holes)
    best=int(np.argmax(labels['utility'][training].mean(0)))
    controls={}
    for r in scores['blocks']:
        left,right=('2022-01-02','2022-07-01') if r['block']=='H12022' else ('2022-07-02','2022-12-01')
        own=(d>=utc(left))&(d<utc(right))&(labels['label_available_us']<utc(right))&known&labels['label_complete'].all(1)
        controls[r['block']]=dict(mean_independent_one_day_cost_reference_utilities={name:float(labels['utility'][own,j].mean()) for j,name in enumerate(NAMES)},
            train_only_best_expert=NAMES[best],train_only_best_mean_reference_utility=float(labels['utility'][own,best].mean()),
            scope='DESCRIPTIVE_SEPARATE_ONE_DAY_REFERENCES_NOT_CONTINUOUS_WALLET_RETURNS')
    report=dict(status=scores['status'],scores=scores,routing=routing,controls=controls,
        scientific_attempts=1,model_fits=3,seed=SEED,alpha=30.,feature_counts={k:v.shape[1] for k,v in x.items()},
        model_family='ORIGINAL_UTILITYSELECTOR_RIDGE_STANDARD_SCALER',horizon_days=1,
        training=dict(complete_candidate_dates=int(mask.sum()),disjoint_market_intervals=len(training),
            first_decision_us=int(d[training[0]]),last_decision_us=int(d[training[-1]]),
            maximum_label_maturity_us=int(labels['label_available_us'][training].max()),
            maximum_scaler_source_available_us=int(d[training].max()),cutoff_us=utc('2021-12-31'),logical_fit_available_us=utc('2022-01-01')),
        labels=dict(reference='EXISTING_CONDITIONAL_DAILY_QUANTITY_PROXY',cost_per_side=COST,capital=CAPITAL,
            funding_scale=1.,funding_unit='UNCONFIRMED_RAW_AS_FRACTION_CONDITIONAL',
            charge_mark='STRICTLY_PAST_MINUTE_NOT_EXACT_EVENT_MARK',downside_penalty='0.5_times_daily_path_MDD',
            noncash_complete_counts=labels['label_complete'][:,1:].sum(0).tolist(),
            held_mark_unknown_counts=(labels['label_reason'][:,1:]=='UNKNOWN_HELD_MARK_AT_COMPLETION').sum(0).tolist(),
            maturity_latency_us=LATENCY_US,no_oracle_winner_labels=True),
        scope='SEEN_HISTORICAL_CRYPTO_ADAPTATION_NOT_PAPER_ORIGINAL_OR_NEW_OUT_OF_SAMPLE',
        financial_acceptance='NOT_ACCEPTED_NATIVE_CERTIFICATION_AND_PAID_FLAT_GATE_BLOCKED',
        compatibility_residual_USDT=660.0772133978703,feedback_features='NONE_UNUSED_ZERO_CLOCK_ONLY',
        missing_outcomes_never_used_for_predecision_routing=True,no_full_wallet_path_claim=True,
        prior_STOPs_preserved=True,native_wallets=0,provider_downloads=0,
        source_commit=source_commit,prepared_source_commit=preparation['source_commit'],
        prepared_SHA256=preparation['prepared_SHA256'],mark_coverage_SHA256=digest((input_path/'MARK_COVERAGE.json').read_bytes()))
    vectors=dict(decision_us=d,common_feature_known=known,train_candidate_mask=mask,training_indices=training,minute_risk_features=risk,
        **labels,**{k+'_prediction':v for k,v in prediction.items()},**targets)
    if cold:
        for filename,actual in [('VECTORS.npz',vectors),('MODELS.npz',models)]:
            with np.load(state/'result'/filename,allow_pickle=False) as expected:
                require(set(expected.files)==set(actual),'Restored artifact keys')
                for key,value in actual.items():np.testing.assert_array_equal(value,expected[key],err_msg=filename+':'+key)
        require(report==json.loads((state/'result/RESULT.json').read_bytes()),'Exact statistical/routing report')
        save(state/'PUBLIC_RESTORE.json',dict(status='PASS_EXACT_PUBLIC_INPUT_LABEL_MODEL_PREDICTION_TARGET_SCORE_RESTORE',
            artifact_commit=artifact_commit,source_commit=source_commit,new_model_fits=0,new_scientific_attempts=0,
            private_input_paths=0,provider_downloads=0,native_wallets=0,elapsed_seconds=time.monotonic()-began))
    else:
        np.savez_compressed(state/'MODELS.npz',**models);np.savez_compressed(state/'VECTORS.npz',**vectors)
        save(state/'RESULT.json',report);save(state/'TIMING.json',dict(total_seconds=time.monotonic()-began,fit_seconds=fit_seconds))
    require(time.monotonic()-began<120,'Frozen120second experiment budget')
    print(json.dumps(report['scores'],indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True)
    p.add_argument('--artifact-commit');a=p.parse_args();run(a.state,a.source_commit,a.artifact_commit)
