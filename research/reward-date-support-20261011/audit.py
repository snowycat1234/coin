"""Verify actual effective-loss UTC dates; prepare source support, never fit."""
import argparse
import importlib.util
import io
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
from scripts.research.conditional_selector_core import nonoverlap_indices,DAY_US

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('published_joint_selector',ROOT/'research/minute-conditional-selector-20261011/experiment.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
ARTIFACT='71c892964d769cc16458a74652370134a2a98039';PREFIX='research/minute-conditional-selector-20261011/'


def require(v,message):
    if not bool(v):raise ValueError(message)


def unique_active_dates(rows):
    """Objective rows only. Models, assets, contexts or repeated draws add no dates."""
    return sorted({r['UTC_decision_date'] for r in rows if r['objective_weight']>0 and r['effective_data_loss']>0})


def source_arrays(path):
    b=m.git('show',ARTIFACT+':'+PREFIX+path)
    with np.load(io.BytesIO(b),allow_pickle=False) as a:return {k:a[k].copy() for k in a.files},m.digest(b)


def actual_ledger(source,vectors,models,result):
    x,known,_=m.design(source);d=source['decision_us'];ix=models['training_indices']
    require(np.array_equal(d,vectors['decision_us']) and np.array_equal(ix,vectors['training_indices']),'Actual saved sample order')
    require(np.array_equal(known,vectors['common_feature_known']),'Exact original feature support')
    require(np.all(np.diff(ix)>0) and known[ix].all() and vectors['label_complete'][ix].all(), 'Unique complete actual training rows')
    cutoff=result['training']['cutoff_us'];fit=result['training']['logical_fit_available_us'];y=vectors['utility']
    require(np.all(vectors['label_available_us'][ix]<cutoff) and np.all(d[ix]<cutoff) and cutoff<=fit,'Reward/cost maturity andtraining-only scaler cutoff')
    rows=[];metrics={}
    for arm in ('A','B','C'):
        require(np.allclose(x[arm][ix].mean(0),models[arm+'_mean'],rtol=0,atol=1e-14),'Scaleractual selected rows')
        predicted=((x[arm][ix]-models[arm+'_mean'])/models[arm+'_scale'])@models[arm+'_coef'].T+models[arm+'_intercept']
        loss=np.mean((predicted-y[ix])**2,axis=1) # originalmultioutput unweighted data loss
        for j,i in enumerate(ix):
            date=pd.Timestamp(int(d[i]),unit='us',tz='UTC').date().isoformat()
            rows.append(dict(arm=arm,UTC_decision_date=date,decision_us=int(d[i]),sample_id=f'{arm}:MARKET_VECTOR:{int(d[i])}',
                source_row_index=int(i),split='TRAIN_2021',reward_complete_maturity_us=int(vectors['label_available_us'][i]),
                terminal_cost_dependency_us=int(d[i])+DAY_US+m.EXECUTION_DELAY_US,
                scaler_source_available_us=int(d[i]),train_cutoff_us=int(cutoff),logical_fit_available_us=int(fit),
                objective_weight=1.,effective_data_loss=float(loss[j]),entered_nonzero_effective_loss=bool(loss[j]>0),
                CASH_reward=float(y[i,0]),VOL_reward=float(y[i,1]),CS_reward=float(y[i,2]),
                reward_scope='CONDITIONAL_ONE_DAY_PAID_COST_REFERENCE_NOT_NATIVE_WALLET'))
        own=[r for r in rows if r['arm']==arm]
        metrics[arm]=dict(actual_objective_rows=len(own),unique_nonzero_loss_UTC_dates=len(unique_active_dates(own)),
            zero_loss_rows=int((loss==0).sum()),sample_weight=1.,padding_rows=0,repeated_draws=0,
            first_UTC_date=own[0]['UTC_decision_date'],last_UTC_date=own[-1]['UTC_decision_date'],
            maximum_reward_maturity_us=max(r['reward_complete_maturity_us'] for r in own),
            data_loss_minimum=float(loss.min()),data_loss_mean=float(loss.mean()))
    union=unique_active_dates(rows)
    return rows,dict(per_arm=metrics,unique_active_loss_UTC_date_union=len(union),arm_rows_sum=len(rows),
        source_calendar_dates=len(d),old_candidate_training_dates=int(vectors['train_candidate_mask'].sum()),
        requirement600_met=bool(len(union)>=600),no_cross_arm_or_asset_count_multiplication=True,
        holding_days=1,source_fit_code=result['source_commit'],actual_fit_calls=result['model_fits'])


def prepare_support(source,vectors):
    d=source['decision_us'];cutoff=m.utc('2022-09-15');validstart=m.utc('2022-10-01');validend=m.utc('2022-12-01')
    common=source['baseline_ready']&vectors['common_feature_known']&vectors['label_complete'].all(1)
    train=(d>=m.utc('2021-01-02'))&(d<cutoff)&(vectors['label_available_us']<cutoff)&common
    eligible_ix=np.flatnonzero(train);registered=nonoverlap_indices(d,vectors['label_available_us'],train)
    validation=(d>=validstart)&(d<validend);natural=np.flatnonzero(validation)
    mature=validation&(vectors['label_available_us']<validend)&vectors['label_complete'].all(1)
    require(np.all(vectors['label_available_us'][train]<cutoff) and cutoff<validstart,'Costcomplete train rewards cannot reach validation')
    records=[]
    for i in np.r_[eligible_ix,natural]:
        is_train=bool(train[i]);date=pd.Timestamp(int(d[i]),unit='us',tz='UTC').date().isoformat()
        records.append(dict(UTC_decision_date=date,decision_us=int(d[i]),sample_id=f'PREPARED_MARKET_VECTOR:{int(d[i])}',
            split='PREPARED_TRAIN_NOT_FIT' if is_train else 'NATURAL_SEEN_DEVELOPMENT_NOT_SCORED',
            source_row_index=int(i),reward_complete_maturity_us=int(vectors['label_available_us'][i]),
            terminal_cost_dependency_us=int(d[i])+DAY_US+m.EXECUTION_DELAY_US,
            feature_known=bool(vectors['common_feature_known'][i]),reward_complete=bool(vectors['label_complete'][i].all()),
            reward_mature_before_role_boundary=bool(vectors['label_available_us'][i]<(cutoff if is_train else validend)),
            actual_loss_weight=0.,actual_model_fit=False))
    calendar_bounds={}
    for horizon in (1,7,30):
        mature_at=d+horizon*DAY_US+m.LATENCY_US
        calendar_bounds[str(horizon)]=dict(calendar_dates_before_cutoff=int(((d>=m.utc('2021-01-02'))&(mature_at<cutoff)).sum()),
            full_horizon_cost_quality='REUSED_EXISTING_ONE_DAY_ONLY' if horizon==1 else 'NOT_RUN_UNKNOWN',
            holding_shortened_to_reach600=False)
    info=dict(status='PASS_600_PREPARED_CONDITIONAL_REWARD_DATES_NOT_ACTUAL_TRAINING' if len(eligible_ix)>=600 else 'STOP_LESS_THAN600_COMPLETE_PREPARED_DATES',
        prepared_complete_unique_train_dates=len(eligible_ix),actual_new_fit_dates=0,new_models_fit=0,
        registered_old_UtilitySelector_fit_dates_if_reused=len(registered),registered_old_learner_can_meet600=len(registered)>=600,
        train_reward_cutoff_us=cutoff,first_prepared_train_us=int(d[eligible_ix[0]]),last_prepared_train_us=int(d[eligible_ix[-1]]),
        maximum_prepared_reward_maturity_us=int(vectors['label_available_us'][eligible_ix].max()),
        development_start_us=validstart,development_end_exclusive_us=validend,natural_full_development_calendar_dates=len(natural),
        complete_mature_development_outcome_dates=int(mature.sum()),validation_resampled=False,short_fraction_forced=False,
        calendar_only_horizon_upper_bounds=calendar_bounds,
        new_model_gate='NOT_RUN_OLD_RECIPE_STOP_PRESERVED_NEXT_MODEL_NEEDS_FROZEN_MECHANISM_AND600_EFFECTIVE_LOSS_DATES',
        native_reward_certificate='BLOCKED_RAW_UNIT_EXACT_CHARGE_MARK_FILTER_AND_PAID_FLAT_UNRESOLVED')
    arrays=dict(prepared_train_indices=eligible_ix,registered_nonoverlap_indices=registered,natural_development_indices=natural,
        decision_us=d,reward_complete_maturity_us=vectors['label_available_us'],complete_reward_mask=vectors['label_complete'],
        common_feature_known=vectors['common_feature_known'],prepared_train_mask=train,development_mask=validation,
        utility=vectors['utility'],expert_order=np.asarray(m.NAMES),symbol_order=source['symbol_order'])
    return records,arrays,info


def run(state,source_commit,expected=None):
    require(not state.exists() and state.resolve().is_relative_to(Path('/workspace')),'Fresh bounded STATE')
    require(not m.git('status','--porcelain'),'Clean published source')
    if expected is None:require(m.git('rev-parse','HEAD').decode().strip()==source_commit,'Exactpublishedsource')
    for line in (HERE/'SOURCE_SHA256.txt').read_text().splitlines():
        sha,name=line.split(maxsplit=1);require(m.digest((ROOT/name).read_bytes())==sha,'Exactsource '+name)
    state.mkdir();began=time.monotonic()
    source,s_sha=source_arrays('input/SOURCE_PREPARED.npz');v,v_sha=source_arrays('result/VECTORS.npz');models,model_sha=source_arrays('result/MODELS.npz')
    result=json.loads(m.git('show',ARTIFACT+':'+PREFIX+'result/RESULT.json'))
    ledger,usage=actual_ledger(source,v,models,result);prepared_rows,prepared,support=prepare_support(source,v)
    pd.DataFrame(ledger).to_csv(state/'ACTUAL_LOSS_DATE_LEDGER.csv',index=False)
    pd.DataFrame(prepared_rows).to_csv(state/'PREPARED_DATE_ROLES.csv',index=False)
    np.savez_compressed(state/'PREPARED_REWARD_DATE_SUPPORT.npz',**prepared)
    report=dict(status='ACTUAL_FIT600_NOT_MET_SEPARATE_SOURCE_PREPARATION_COMPLETE',source_commit=source_commit,artifact_source=ARTIFACT,
        source_SHA256=s_sha,vector_SHA256=v_sha,model_SHA256=model_sha,actual_usage=usage,preparation=support,
        old_selector_four_failed_gates_unchanged=True,original_terminal_paidflat_STOP_unchanged=True,
        models_fit=0,wallets=0,provider_downloads=0,new_training_set_predictions='SAVED_COEFFICIENT_ARITHMETIC_ONLY_NO_REFIT',
        seen_development_not_pristine_out_of_sample=True,artifacts={p.name:m.digest(p.read_bytes()) for p in state.iterdir()})
    m.save(state/'RESULT.json',report)
    if expected:
        old=json.loads(m.git('show',expected+':research/reward-date-support-20261011/result/RESULT.json'))
        require(report==old,'Exactpubliceffective-loss-date andpreparationrestore')
        for name,sha in report['artifacts'].items():require(m.digest(m.git('show',expected+':research/reward-date-support-20261011/result/'+name))==sha,'Exactartifact '+name)
        m.save(state/'PUBLIC_RESTORE.json',dict(status='PASS_EXACT_ACTUAL_LOSS_DATE_AND_PREPARED_SUPPORT_RESTORE',artifact_commit=expected,
            models_fit=0,wallets=0,provider_downloads=0,elapsed_seconds=time.monotonic()-began))
    m.save(state/'TIMING.json',dict(elapsed_seconds=time.monotonic()-began));require(time.monotonic()-began<60,'Frozen60s budget')
    print(json.dumps(dict(actual=usage,prepared=support),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True);p.add_argument('--expected-commit')
    a=p.parse_args();run(a.state,a.source_commit,a.expected_commit)
