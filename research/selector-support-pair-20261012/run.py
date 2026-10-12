"""Two fixed Ridge fits; real owned intervals and true reward maturity separate."""
import argparse
import importlib.util
import io
import json
from pathlib import Path
import sys
import time
import zipfile

import numpy as np
import pandas as pd
import polars as pl
import pyarrow.parquet as pq

from dates import owned_indices,interval_events
from scripts.research.conditional_selector_core import UtilitySelector,nonoverlap_indices,budget_path,shared_targets
from scripts.investment.public_sma_perpetual import signed_risk_weights

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('original_selector',ROOT/'research/minute-conditional-selector-20261011/experiment.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sys.path.insert(0,str(ROOT/'research/core5-continuous-risk600-20261011'))
from prepare import SourceReader
from modules.collector_research.pipeline.common import EXEC_OFFSET_US

ARMS=('MATURITY_CONTROL','OWNED_FULL');CUTOFF=m.utc('2022-09-15');VALIDSTART=m.utc('2022-10-01');VALIDEND=m.utc('2022-12-01')
SEED=811134;BSEED=811135;DAY=m.DAY_US
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')


def require(v,msg):
    if not bool(v):raise ValueError(msg)


def raw_funding(state):
    inv=json.loads(m.git('show','306b58c4a52035ac9f374de7c25d40dff22fb658:research/core5-continuous-risk600-20261011/SOURCE_COVERAGE.json'))
    reader=SourceReader(inv,state,local=False);year=reader.wrapper('Y2021')
    yi=json.loads(m.git('show','94fe13c494c82bb6e6868e6614eb7298fb15b3c3:research/core5-2021-economic-data/Y2021/INDEX.json'))
    ym={r['name']:r for r in yi['members']}
    spec=importlib.util.spec_from_file_location('original_funding',ROOT/'research/short-funding-residual-20261011/experiment.py')
    fmod=importlib.util.module_from_spec(spec);spec.loader.exec_module(fmod);raw=fmod.source_archive(ROOT,state)
    streams={};proof=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        members=json.loads(z.read('MEMBERS.json'))['files']
        for s in SYMBOLS:
            name=f'derived/economics/{s}_funding_events.parquet';old=year.read(name)
            require(m.digest(old)==ym[name]['SHA256'],'Yearfunding source identity')
            columns=['calc_time_ms','funding_interval_hours','last_funding_rate','past_mark_price']
            past=pq.read_table(io.BytesIO(old),columns=columns).to_pandas()
            recent_name=f'source_tables_not_model_inputs/economics/{s}_funding_events.parquet';recent=z.read(recent_name)
            require(m.digest(recent)==members[recent_name]['SHA256'],'2022funding source identity')
            future=pq.read_table(io.BytesIO(recent),columns=columns,filters=[('calc_time_ms','>=',m.utc('2022-01-01')//1000),
                ('calc_time_ms','<',VALIDEND//1000)]).to_pandas()
            combined=pd.concat([past,future],ignore_index=True).sort_values('calc_time_ms')
            require(not combined.calc_time_ms.duplicated().any(),'No repeatedrawfunding event IDs')
            times=combined.calc_time_ms.to_numpy(np.int64)*1000;hours=combined.funding_interval_hours.to_numpy(float)
            require(np.all(np.diff(times)>0) and np.isfinite(hours).all(),'Exactrawfunding chronology')
            streams[s]=dict(times=times,hours=hours,rates=combined.last_funding_rate.to_numpy(float),marks=combined.past_mark_price.to_numpy(float))
            proof.append(dict(symbol=s,year_member_SHA256=m.digest(old),year_source='94fe13c494c82bb6e6868e6614eb7298fb15b3c3',
                recent_member_SHA256=m.digest(recent),recent_source=fmod.SOURCE_COMMIT,events=len(times),last_event_us=int(times[-1])))
    reader.close();return streams,proof


def boundaries(source,vectors,frames,streams):
    d=source['decision_us'];require(EXEC_OFFSET_US==m.EXECUTION_DELAY_US,'Originalreference executionclock identity')
    starts=d+EXEC_OFFSET_US;ends=starts+DAY
    maturity=np.full(len(d),np.iinfo(np.int64).max,dtype=np.int64);watermark=np.zeros(len(d),np.int64)
    records=[];event_owner={};old_cutoff=m.utc('2021-12-31');symbols=tuple(source['symbol_order'])
    available=frames[symbols[0]].available_us.to_numpy(np.int64);fi=np.searchsorted(available,d)
    for i in range(len(d)):
        complete=bool(vectors['label_complete'][i].all());after=[];event_ids=[]
        held=np.any(source['targets'][i,1:]!=0,axis=0)
        if complete:
            for j,s in enumerate(symbols):
                if not held[j]:continue
                stream=streams[s];t=stream['times'];before=int(np.searchsorted(t,starts[i],side='right')-1)
                last=int(np.searchsorted(t,ends[i],side='right'));inside=interval_events(t,starts[i],ends[i])
                require(before>=0 and last<len(t),'Fundcoverage evidence beforeandafter ownedinterval')
                diffs=np.diff(t);hours=stream['hours'];good=(np.abs(diffs-hours[:-1]*3600000000)<=1000000)|(np.abs(diffs-hours[1:]*3600000000)<=1000000)
                require(good[before:last].all() and np.isfinite(stream['marks'][inside]).all(),'Completeactual fundinterval includingafter-event watermark')
                coefficient=float(np.dot(stream['rates'][inside],stream['marks'][inside]))
                saved=float(frames[s].mark_funding_per_unit.iloc[fi[i]+1])
                require(np.isclose(coefficient,saved,rtol=1e-12,atol=1e-12),'Originalsource fundingcoefficient/ownedwindow identity')
                after.append(int(t[last]))
                for event in t[inside]:
                    key=f'{s}:{int(event)}'
                    require(key not in event_owner or event_owner[key]==i,'A rawfundingevent cannotbelongtotwo decisionrewards')
                    event_owner[key]=i;event_ids.append(key)
            watermark[i]=max(after,default=0)
            maturity[i]=max(int(vectors['label_available_us'][i]),int(watermark[i]))
        records.append(dict(decision_us=int(d[i]),UTC_date=pd.Timestamp(int(d[i]),unit='us',tz='UTC').date().isoformat(),
            owned_start_us=int(starts[i]),owned_end_us=int(ends[i]),terminal_cost_dependency_us=int(ends[i]),
            old_declared_maturity_us=int(vectors['label_available_us'][i]),fund_completeness_after_event_us=int(watermark[i]) if complete else None,
            full_reward_maturity_us=int(maturity[i]) if complete else None,full_reward_complete=complete,
            owned_interval_convention='START_EXCLUSIVE_END_INCLUSIVE',raw_owned_funding_event_ids='|'.join(event_ids)))
    old_indices=vectors['training_indices']
    require(np.all(maturity[old_indices]<old_cutoff),'Old181labels still trulycomplete beforeoldcutoff; otherwise discloseSTOP')
    return starts,ends,maturity,records,dict(raw_funding_event_owner_uniqueness=True,old181_true_maturity_before_oldcutoff=True,
        original_two_minute_clock_incomplete_as_completeness_proof=True,owned_holding_days=1,
        maximum_old181_full_reward_maturity_us=int(maturity[old_indices].max()),new_native_reward_certificate='BLOCKED')


def fit_original_learner(x,y,indices,maturity,d):
    """Same original Ridge learner; only supported date selection is adapted."""
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import Ridge
    require(np.all(maturity[indices]<CUTOFF) and np.isfinite(x[indices]).all() and np.isfinite(y[indices]).all(),'True maturefinite training data')
    selector=UtilitySelector('RIDGE',SEED)
    selector.model=make_pipeline(StandardScaler(),Ridge(alpha=30.))
    selector.model.fit(x[indices],y[indices])
    selector.training_indices=indices.copy();selector.cutoff_us=CUTOFF;selector.fit_available_us=CUTOFF
    centered=y[indices]-y[indices].mean(1,keepdims=True)
    selector.utility_scale=max(1e-4,float(np.median(np.abs(centered))))
    return selector


def routing(source,d,prediction,scales,known,eval_ix):
    ed=d[eval_ix];w=source['targets'][eval_ix];symbols=tuple(source['symbol_order']);names=m.NAMES
    frames={name:pl.DataFrame([dict(available_us=int(t),symbol=s,target_weight=float(w[i,e,j]),
        raw_signed_target=float(w[i,e,j]),eligibility_reason='ELIGIBLE') for i,t in enumerate(ed) for j,s in enumerate(symbols)]) for e,name in enumerate(names)}
    arrays={};reports={};available=source['close_available_us'];close=source['close']
    for arm in ARMS:
        eligible=source['expert_eligible'][eval_ix].copy();eligible[~known[eval_ix],1:]=False
        scores=np.where(np.isfinite(prediction[arm]),prediction[arm],0.)
        budgets,_=budget_path(scores,scales[arm],cash_index=0,eligible=eligible,initial=np.array([1.,0.,0.]),max_l1=.1)
        netted,proof=shared_targets(frames,names,ed,symbols,budgets)
        weights=netted['target_weight'].to_numpy().reshape(len(ed),5).copy();peak=0.
        for i,t in enumerate(ed):
            own=np.flatnonzero(weights[i]!=0)
            if not len(own):continue
            j=int(np.searchsorted(available,t));past=close[j-30:j+1][:,own]
            require(available[j]==t and past.shape==(31,len(own)) and np.isfinite(past).all(),'Truepast30 riskcontext')
            r=np.diff(past,axis=0)/past[:-1];after,_=signed_risk_weights(weights[i,own],r,annual_vol_target=.10);weights[i,own]=after
            covariance=np.atleast_2d(np.cov(r,rowvar=False,ddof=1))*365;peak=max(peak,float(np.sqrt(max(0.,after@covariance@after))))
        require(np.abs(weights).max()<=.3+1e-12 and np.abs(weights).sum(1).max()<=.6+1e-12 and peak<=.1+1e-10,'Nettedtarget caps/risk')
        arrays[arm+'_budgets']=budgets;arrays[arm+'_targets']=weights
        reports[arm]=dict(target_calendar_dates=len(ed),mean_target_gross=float(np.abs(weights).sum(1).mean()),
            maximum_target_gross=float(np.abs(weights).sum(1).max()),allocated_leg_gross_max=float(max(proof['allocated_leg_gross'])),
            target_absolute_changes=float(np.abs(np.diff(np.vstack([np.zeros((1,5)),weights]),axis=0)).sum()),
            maximum_past30_signed_cov_annual_vol=peak,native_wallet='NOT_RUN_REWARD_CERTIFICATE_BLOCKED',scope='TARGET_INTENTS_NOT_REALIZED_PROFIT_OR_EXPOSURE')
    return arrays,reports


def statistics(d,y,prediction,complete):
    losses={arm:np.mean((p[:,1:]-y[:,1:])**2,axis=1) for arm,p in prediction.items()}
    means={arm:float(v[complete].mean()) for arm,v in losses.items()};delta=np.where(complete,losses[ARMS[0]]-losses[ARMS[1]],np.nan)
    rng=np.random.default_rng(BSEED);starts=rng.integers(0,len(d),size=(1000,int(np.ceil(len(d)/7))))
    samples=((starts[:,:,None]+np.arange(7))%len(d)).reshape(1000,-1)[:,:len(d)]
    boot=np.nanmean(delta[samples],axis=1);ci=np.quantile(boot,[.025,.975]);gain=float(delta[complete].mean()/means[ARMS[0]])
    passed=gain>=.02 and ci[0]>0
    months={}
    for name,left,right in [('OCTOBER','2022-10-01','2022-11-01'),('NOVEMBER','2022-11-01','2022-12-01')]:
        own=complete&(d>=m.utc(left))&(d<m.utc(right));months[name]=dict(common_dates=int(own.sum()),
            MSE={arm:float(v[own].mean()) for arm,v in losses.items()})
    return dict(status='PASS_FIXED_SUPPORT_INFORMATION_GATE' if passed else 'STOP_FIXED_SUPPORT_INFORMATION_GATE',
        natural_calendar_dates=len(d),common_statistical_dates=int(complete.sum()),MSE=means,
        relative_MSE_reduction_full=gain,paired_MSE_difference_95CI=ci.tolist(),descriptive_months=months,
        bootstrap_seed=BSEED,bootstrap_replicates=1000,block_calendar_days=7,
        conditional_common_label_scores_not_native_returns=True)


def run(state,source_commit,expected=None):
    require(not state.exists() and state.resolve().is_relative_to(Path('/workspace')),'Fresh boundedSTATE')
    require(not m.git('status','--porcelain'),'Cleanpublishedsource')
    if expected is None:require(m.git('rev-parse','HEAD').decode().strip()==source_commit,'Publishedexactsource')
    manifest='COLD_SOURCE_SHA256.txt' if expected else 'SOURCE_SHA256.txt'
    for line in (HERE/manifest).read_text().splitlines():
        sha,name=line.split(maxsplit=1);require(m.digest((ROOT/name).read_bytes())==sha,'SourceSHA '+name)
    state.mkdir();began=time.monotonic()
    source,frames,holes,preparation=m.load_inputs(ROOT/'research/minute-conditional-selector-20261011/input')
    with np.load(ROOT/'research/minute-conditional-selector-20261011/result/VECTORS.npz',allow_pickle=False) as a:v={k:a[k].copy() for k in a.files}
    x_all,known,_=m.design(source);x=x_all['A'];d=source['decision_us'];y=v['utility']
    require(np.all(d%DAY==0) and np.all(np.diff(d)==DAY),'Distinct dense UTC decision dates')
    recreated=m.one_day_labels(frames,d,source['targets'],source['expert_eligible'],holes,tuple(source['symbol_order']))
    for key in recreated:np.testing.assert_array_equal(recreated[key],v[key],err_msg='Originalreference labelidentity '+key)
    streams,fundproof=raw_funding(state);s,e,mature,clock_rows,clock_proof=boundaries(source,v,frames,streams)
    mask=known&v['label_complete'].all(1)&(mature<CUTOFF)&(d<CUTOFF)
    selections={ARMS[0]:nonoverlap_indices(d,mature,mask),ARMS[1]:owned_indices(d,s,e,mature,mask,CUTOFF)}
    require(len(selections[ARMS[1]])>=600,'Atleast600truly matureowned dates beforefullfit')
    legacy=nonoverlap_indices(d,v['label_available_us'],mask)
    np.testing.assert_array_equal(legacy,selections[ARMS[0]],err_msg='Coveragewatermark doesnotchangelegacycontrol dates')
    eval_ix=np.flatnonzero((d>=VALIDSTART)&(d<VALIDEND));ed=d[eval_ix]
    require(len(eval_ix)==61,'Samefull naturaldevelopmentcalendar')
    pd.DataFrame(clock_rows).to_csv(state/'REWARD_BOUNDARY_LEDGER.csv',index=False)
    preflight=dict(status='PASS_LABEL_COEFFICIENT_OWNER_DATE_MATURITY_PREFIT',source_commit=source_commit,
        owned_nonoverlap_dates=len(selections[ARMS[1]]),legacy_maturity_dates=len(selections[ARMS[0]]),
        labels_bytevalue_exact=True,holdshortened=False,clock_proof=clock_proof,funding_sources=fundproof,
        maximum_full_train_reward_maturity_us=int(mature[selections[ARMS[1]]].max()),cutoff_us=CUTOFF,
        development_start_us=VALIDSTART,natural_development_dates=len(eval_ix),source_preparation=preparation['prepared_SHA256'],
        native_reward_status='BLOCKED_CONDITIONAL_REFERENCE_ONLY')
    m.save(state/'PREFIT.json',preflight);print('PREFIT_PASS',preflight['owned_nonoverlap_dates'],preflight['legacy_maturity_dates'],flush=True)
    models={};prediction={};scales={};date_rows=[];fit_seconds=[];fit_start=time.monotonic()
    if expected:
        saved_np=m.git('show',expected+':research/selector-support-pair-20261012/result/MODELS.npz')
        with np.load(io.BytesIO(saved_np),allow_pickle=False) as a:models={k:a[k].copy() for k in a.files}
    else:
        m.save(state/'ATTEMPT.json',dict(scientific_attempts=1,fits_planned=2,fits_completed=0,seed=SEED,source_commit=source_commit))
    for arm in ARMS:
        ix=selections[arm]
        if not expected:
            b=time.monotonic();selector=fit_original_learner(x,y,ix,mature,d);fit_seconds.append(time.monotonic()-b)
            scaler,ridge=selector.model.steps[0][1],selector.model.steps[1][1]
            for key,value in [('mean',scaler.mean_),('scale',scaler.scale_),('coef',ridge.coef_),('intercept',ridge.intercept_),
                              ('utility_scale',np.asarray(selector.utility_scale)),('training_indices',ix)]:models[arm+'_'+key]=value
            m.save(state/'ATTEMPT.json',dict(scientific_attempts=1,fits_planned=2,fits_completed=len(fit_seconds),seed=SEED,source_commit=source_commit))
            np.savez_compressed(state/'MODELS.npz',**models)
        else:np.testing.assert_array_equal(ix,models[arm+'_training_indices'])
        train_pred=((x[ix]-models[arm+'_mean'])/models[arm+'_scale'])@models[arm+'_coef'].T+models[arm+'_intercept']
        train_loss=np.mean((train_pred-y[ix])**2,axis=1);active=int((train_loss>0).sum())
        if arm==ARMS[1]:require(active>=600,'Atleast600distinct actualpositiveeffective-loss dates')
        for j,i in enumerate(ix):date_rows.append(dict(arm=arm,UTC_date=pd.Timestamp(int(d[i]),unit='us',tz='UTC').date().isoformat(),
            sample_id=f'{arm}:MARKET_VECTOR:{int(d[i])}',decision_us=int(d[i]),split='TRUE_MATURE_TRAIN_BEFORE_20220915',
            owned_start_us=int(s[i]),owned_end_us=int(e[i]),reward_complete_maturity_us=int(mature[i]),
            terminal_cost_dependency_us=int(e[i]),objective_weight=1.,effective_data_loss=float(train_loss[j]),
            entered_nonzero_effective_loss=bool(train_loss[j]>0)))
        p=np.full((len(eval_ix),3),np.nan);good=known[eval_ix]
        p[good]=((x[eval_ix[good]]-models[arm+'_mean'])/models[arm+'_scale'])@models[arm+'_coef'].T+models[arm+'_intercept']
        if not expected:
            original=selector.predict(x[eval_ix[good]],ed[good],feature_available_us=ed[good],feedback_available_us=np.zeros(good.sum(),np.int64))
            np.testing.assert_array_equal(original,p[good])
        prediction[arm]=p;scales[arm]=float(models[arm+'_utility_scale'])
        print('FIT_OR_RESTORE_COMPLETE',arm,len(ix),'active_loss_dates',active,flush=True)
    require(time.monotonic()-fit_start<120,'Frozenfit/diagnostic120s budget')
    complete=known[eval_ix]&v['label_complete'][eval_ix].all(1)&(mature[eval_ix]<VALIDEND)
    scores=statistics(ed,y[eval_ix],prediction,complete);targets,target_reports=routing(source,d,prediction,scales,known,eval_ix)
    usage={arm:dict(actual_objective_dates=len(selections[arm]),distinct_positive_loss_UTC_dates=sum(r['arm']==arm and r['entered_nonzero_effective_loss'] for r in date_rows),
        maximum_reward_maturity_us=int(mature[selections[arm]].max()),first_UTC_date=pd.Timestamp(int(d[selections[arm][0]]),unit='us',tz='UTC').date().isoformat(),
        last_UTC_date=pd.Timestamp(int(d[selections[arm][-1]]),unit='us',tz='UTC').date().isoformat()) for arm in ARMS}
    report=dict(status=scores['status'],source_commit=source_commit,scientific_attempts=1,model_fits=2,seed=SEED,alpha=30.,
        feature_columns=46,scores=scores,training_usage=usage,true_maturity_cutoff_us=CUTOFF,logical_fit_available_us=CUTOFF,
        corrected_date_selection='OWNED_INTERVAL_GEOMETRY_WITH_SEPARATE_TRUE_REWARD_MATURITY',old_core_byte_unchanged=True,
        target_diagnostics=target_reports,preflight=preflight,native_reward_qualification='BLOCKED_NOT_DEFAULT_WALLET_REWARDS',
        native_wallets=0,provider_downloads=0,holdshortened=False,validation_resampled=False,short_fraction_forced=False,
        all_original_181_date_and_four_failed_gates_and_terminal_STOPs_preserved=True,
        scope='SEEN_DEVELOPMENT_CONDITIONAL_REFERENCE_INFORMATION_ONLY_NOT_INVESTMENT_RETURN')
    vectors=dict(eval_decision_us=ed,common_statistical_mask=complete,full_reward_maturity_us=mature,train_candidate_mask=mask,
        owned_start_us=s,owned_end_us=e,**{arm+'_prediction':p for arm,p in prediction.items()},**targets)
    pd.DataFrame(date_rows).to_csv(state/'ACTUAL_LOSS_DATES.csv',index=False);np.savez_compressed(state/'VECTORS.npz',**vectors)
    m.save(state/'RESULT.json',report);m.save(state/'TIMING.json',dict(total_seconds=time.monotonic()-began,fit_seconds=fit_seconds))
    if expected:
        old=json.loads(m.git('show',expected+':research/selector-support-pair-20261012/result/RESULT.json'))
        require(old==report,'Exactscientificpair report')
        for name in ('REWARD_BOUNDARY_LEDGER.csv','VECTORS.npz'):
            require(m.git('show',expected+':research/selector-support-pair-20261012/result/'+name)==(state/name).read_bytes(),'Exactpublicartifact '+name)
        old_dates=pd.read_csv(io.BytesIO(m.git('show',expected+':research/selector-support-pair-20261012/result/ACTUAL_LOSS_DATES.csv')),
                              dtype=str,keep_default_na=False)
        new_dates=pd.read_csv(state/'ACTUAL_LOSS_DATES.csv',dtype=str,keep_default_na=False)
        old_loss=old_dates.pop('effective_data_loss').to_numpy(float);new_loss=new_dates.pop('effective_data_loss').to_numpy(float)
        pd.testing.assert_frame_equal(old_dates,new_dates,check_exact=True)
        np.testing.assert_allclose(old_loss,new_loss,rtol=1e-12,atol=1e-18)
        m.save(state/'PUBLIC_RESTORE.json',dict(status='PASS_ZERO_FIT_EXACT_DATES_CLOCKS_PREDICTION_TARGET_SCORE_NUMERICAL_LOSS',
            artifact_commit=expected,new_fits=0,native_wallets=0,provider_downloads=0,
            scientific_report_exact=True,reward_boundary_ledger_byte_exact=True,prediction_target_vectors_byte_exact=True,
            all_date_identity_clock_weight_positive_loss_fields_exact=True,loss_rtol=1e-12,loss_atol=1e-18,
            maximum_loss_absolute_difference=float(np.max(np.abs(old_loss-new_loss))),elapsed_seconds=time.monotonic()-began))
    require(time.monotonic()-began<600,'Source/full600s budget')
    print(json.dumps(scores,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True);p.add_argument('--expected-commit')
    a=p.parse_args();run(a.state,a.source_commit,a.expected_commit)
