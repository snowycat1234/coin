"""One frozen HAR fit and seen-training prediction/risk diagnostic; no wallets."""
import argparse
import io
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile
from datetime import datetime,timezone

import numpy as np
from har import DAY,SYMBOLS,calibrate,forecast,haircut,qlike,bootstrap
from prepare import sha,file_sha,save

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def stamp(day):
    return int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp()*1000000)


def run(args):
    git=lambda *x:subprocess.check_output(["git",*x],cwd=ROOT).decode().strip()
    assert git("rev-parse","HEAD")==args.source_commit and not git("status","--porcelain")
    sys.path.insert(0,str(args.dependencies.resolve()))
    import statsmodels
    assert statsmodels.__version__=="0.14.5"
    output=args.output.resolve()
    output.mkdir(parents=True)
    started=time.monotonic()
    save(output/"STARTED.json",dict(source_commit=args.source_commit,scientific_attempt=1,planned_parameter_fits=5,
        protocol_sha256=file_sha(HERE/"PROTOCOL.json"),amendment_sha256=file_sha(HERE/"PREFIT_AMENDMENT.json"),wallets=0))
    recovery=json.loads((args.prepared/"RECOVERY.json").read_bytes())
    assert recovery["status"]=="PASS_ACTUAL_FULL_INTRADAY_RV"
    for name,digest in recovery["artifacts"].items():
        assert file_sha(args.prepared/name)==digest
    data=np.load(args.prepared/"DAILY_RV.npz",allow_pickle=False)
    assert list(data["symbol_order"])==list(SYMBOLS)
    t=data["available_us"]
    rv=np.column_stack([data[s+"_RV"] for s in SYMBOLS])
    prices=np.column_stack([data[s+"_close"] for s in SYMBOLS])
    rise=np.column_stack([data[s+"_max_logrise"] for s in SYMBOLS])
    amendment=json.loads((HERE/"PREFIT_AMENDMENT.json").read_bytes())["frozen_strategy"]
    with zipfile.ZipFile(args.archive) as z:
        raw=z.read(amendment["wrapper_member"])
    assert sha(raw)==amendment["member_sha256"]
    context=np.load(io.BytesIO(raw),allow_pickle=False)
    assert list(context["symbol_order"])==list(SYMBOLS) and list(context["original_E5_slots"])==[0,1,4]
    assert list(context["expert_names"])==["CASH","VOL_MANAGED_HOLD","CSMOM21"]
    base=context["expert_targets"][:,2,:]
    assert sha(np.asarray(base,dtype="<f8",order="C").tobytes())==amendment["float64_C_order_base_array_sha256"]
    assert sha(np.asarray(context["raw_targets"][:,2,:],dtype="<f8",order="C").tobytes())==amendment["float64_C_order_raw_array_sha256"]
    assert np.array_equal(context["target_available_us"][:,2],context["decision_us"])
    training=np.flatnonzero((t>=stamp("2021-02-02"))&(t<=stamp("2021-06-30")))
    evaluation=np.flatnonzero((t>=stamp("2021-07-02"))&(t<=stamp("2021-12-30")))
    assert len(training)==149 and len(evaluation)==182
    maximum_return_error=0.
    for index in np.r_[training,evaluation]:
        i=int(index)
        j=int(np.searchsorted(context["decision_us"],t[i]))
        assert context["decision_us"][j]==t[i] and context["target_available_us"][j,2]<=t[i]
        actual_returns=np.diff(prices[i-30:i+1],axis=0)/prices[i-30:i]
        maximum_return_error=max(maximum_return_error,float(abs(actual_returns-context["past_returns"][j]).max()))
        assert np.allclose(actual_returns,context["past_returns"][j],rtol=0,atol=2e-14)
        w=base[j]
        assert np.isfinite(w).all() and abs(w).max()<=.3+1e-12 and abs(w).sum()<=.6+1e-12
        assert not np.any(w[~context["asset_eligible"][j,2,:]])
        if not (context["expert_eligible"][j,2] and context["fixed5_covariance_ready"][j]):
            assert not np.any(w)
    save(output/"SOURCE_INPUT_CHECKS.json",dict(common_dates=331,maximum_return_error=maximum_return_error,
        fit_count_before_checks=0,source_targets_exact=True,causal_clock_masks_caps_pass=True))
    model=calibrate(rv,t,stamp("2021-02-02"),stamp("2021-06-30"),stamp("2021-07-01"))
    # Durable checkpoint: later diagnosis failure cannot erase completed fit evidence.
    save(output/"MODEL.json",model)
    thresholds=np.quantile(rise[training+1],.95,axis=0)
    daily=[]
    training_scales=[]
    predictions={k:[] for k in ("HAR","LAST_RV","MEAN30_RV","DAILY_RETURN_VAR30")}
    weights={k:[] for k in ("BASE30","HAR","LAST_RV","STATIC_TRAIN_HAIRCUT")}
    losses={k:[] for k in predictions}
    changed=rv.copy()
    changed[t>=stamp("2021-09-01")]*=8
    prefix_error=0.
    for index in np.r_[training,evaluation]:
        i=int(index)
        decision=int(t[i])
        j=int(np.searchsorted(context["decision_us"],decision))
        assert context["decision_us"][j]==decision and context["target_available_us"][j,2]<=decision
        # Independent actual close comparison binds source past-return data causally.
        returns=np.diff(prices[i-30:i+1],axis=0)/prices[i-30:i]
        assert np.allclose(returns,context["past_returns"][j],rtol=0,atol=2e-14)
        eligible=bool(context["expert_eligible"][j,2] and context["fixed5_covariance_ready"][j])
        w=base[j].copy()
        assert np.isfinite(w).all() and abs(w).max()<=.3+1e-12 and abs(w).sum()<=.6+1e-12
        assert not np.any(w[~context["asset_eligible"][j,2,:]])
        if not eligible:
            assert not np.any(w)
        pred=forecast(rv,i,model)
        assert pred is not None
        scale,receipt=haircut(w,pred,returns)
        if decision<stamp("2021-09-01"):
            other=forecast(changed,i,model)
            prefix_error=max(prefix_error,float(abs(other-pred).max()),abs(haircut(w,other,returns)[0]-scale))
        if i in training:
            training_scales.append(scale)
            continue
        last=rv[i]
        mean=rv[i-29:i+1].mean(0)
        variance=returns.var(axis=0,ddof=1)
        all_predictions=dict(HAR=pred,LAST_RV=last,MEAN30_RV=mean,DAILY_RETURN_VAR30=variance)
        for name,value in all_predictions.items():
            predictions[name].append(value)
            losses[name].append(qlike(rv[i+1],value))
        weights["BASE30"].append(w)
        weights["HAR"].append(w*scale)
        weights["LAST_RV"].append(w*haircut(w,last,returns)[0])
        daily.append(dict(decision_us=decision,label_mature_us=int(t[i+1]),base_eligible=eligible,
            HAR_scalar=scale,HAR_forecast_annual_sigma=receipt["forecast_annual_sigma"],
            HAR_forecast=pred.tolist(),realised_next_RV=rv[i+1].tolist()))
    static=float(np.mean(training_scales))
    weights["STATIC_TRAIN_HAIRCUT"]=np.asarray(weights["BASE30"])*static
    weights={k:np.asarray(v) for k,v in weights.items()}
    losses={k:np.asarray(v) for k,v in losses.items()}
    predicted={k:np.asarray(v) for k,v in predictions.items()}
    dates=t[evaluation]
    gates=dict(causal_future_perturbation_pass=prefix_error==0,complete_common182dates=len(daily)==182)
    halves={}
    for half,mask in (("JUL_SEP",dates<stamp("2021-10-01")),("OCT_DEC",dates>=stamp("2021-10-01"))):
        record={}
        for name in ("LAST_RV","MEAN30_RV"):
            improvement=1-float(losses["HAR"][mask].mean()/losses[name][mask].mean())
            positive=int(np.sum(losses["HAR"][mask].mean(0)<losses[name][mask].mean(0)))
            record[name]=dict(relative_QLIKE_improvement=improvement,improved_assets=positive,
                HAR_mean_QLIKE=float(losses["HAR"][mask].mean()),baseline_mean_QLIKE=float(losses[name][mask].mean()))
            gates[half+"_"+name+"_improvement_ge002"]=improvement>=.02
            gates[half+"_"+name+"_at_least3assets"]=positive>=3
        halves[half]=record
    delta=np.column_stack([(losses["HAR"]-losses[name]).mean(1) for name in ("LAST_RV","MEAN30_RV")])
    intervals=bootstrap(delta)
    for j,name in enumerate(("LAST_RV","MEAN30_RV")):
        gates[name+"_paired_bootstrap_upper_negative"]=bool(intervals[j,1]<0)
    # Fixed-weight risk and price/cost proxies: not actual funds/capital accounting.
    five=np.load(args.prepared/"FIVE_MIN_CLOSES.npz",allow_pickle=False)
    sample_prices=np.column_stack([five[s] for s in SYMBOLS])
    sample_returns=np.concatenate([np.full((1,5),np.nan),np.diff(np.log(sample_prices),axis=0)]).reshape(365,288,5)
    future_prices=prices[evaluation+1]/prices[evaluation]-1
    past21=prices[evaluation]/prices[evaluation-21]-1
    masks={"short_tail":(rise[evaluation+1]>thresholds),
           "short_rebound":(past21<0)&(future_prices>0)&~(rise[evaluation+1]>thresholds),
           "short_normal_downtrend":(past21<0)&(future_prices<=0)&~(rise[evaluation+1]>thresholds)}
    risk_summary={}
    for arm,w in weights.items():
        variance=np.einsum("da,dab,db->d",w,np.einsum("dka,dkb->dab",sample_returns[evaluation+1],sample_returns[evaluation+1]),w)
        turnover=np.abs(np.diff(np.vstack([np.zeros((1,5)),w,np.zeros((1,5))]),axis=0)).sum()
        contrib=w*future_prices
        groups={}
        combined=np.zeros_like(contrib,dtype=bool)
        for name,mask in masks.items():
            m=mask&(weights["BASE30"]<0)
            combined|=m
            groups[name]=dict(asset_days=int(m.sum()),gross_price_proxy_USDT=float(contrib[m].sum()*10000),
                absolute_exposure_sum=float(np.abs(w[m]).sum()))
        for name,m in (("other_short",(weights["BASE30"]<0)&~combined),("long",weights["BASE30"]>0)):
            groups[name]=dict(asset_days=int(m.sum()),gross_price_proxy_USDT=float(contrib[m].sum()*10000),absolute_exposure_sum=float(np.abs(w[m]).sum()))
        risk_summary[arm]=dict(mean_projected_gross=float(np.abs(w).sum(1).mean()),
            annual_fixed_weight_intraday_RV_sigma=float(np.sqrt(variance.mean()*365)),
            gross_price_proxy_USDT=float(contrib.sum()*10000),weight_turnover=float(turnover),
            estimated_weight_turnover_cost_USDT=float(turnover*.00135*10000),groups=groups,
            scope="Target/shadow risk and closed-price proxies; no funding, fills,liquidation or actual walletPnL. No oracle-as-learned-profit.")
    np.savez_compressed(output/"SAVED_TARGETS.npz",decision_us=dates,symbol_order=np.asarray(SYMBOLS),**weights)
    np.savez_compressed(output/"PREDICTIONS.npz",decision_us=dates,actual_RV=rv[evaluation+1],**predicted)
    (output/"CONTEXT_INPUTS.npz").write_bytes(raw)
    save(output/"DAILY_CHECKS.json",daily)
    passed=all(gates.values())
    assert time.monotonic()-started<120
    save(output/"RESULT.json",dict(status="PREDICTIVE_GATE_PASS" if passed else "STOP_FIXED_HAR_RV_SIZING",
        gates=gates,halves=halves,joint_block_bootstrap95=intervals.tolist(),seed=811130,
        static_training_scalar=static,training_tail95=thresholds.tolist(),risk_diagnosis=risk_summary,
        all_asset_mean_QLIKE={k:float(v.mean()) for k,v in losses.items()},
        per_asset_QLIKE={k:v.mean(0).tolist() for k,v in losses.items()},
        calibration_mean_realised_over_forecast=(rv[evaluation+1]/predicted["HAR"]).mean(0).tolist(),
        scientific_attempts=1,parameter_OLS_fits=5,training_smearing_values=5,training_tail_quantiles=5,
        primary_train_observations_each=len(training),static_scalar_parameters=1,extra_prefix_refits=0,
        diagnostic_mature_dates=len(evaluation),future_prefix_max_error=prefix_error,
        wallets=0,economic_status="PERMITTED_BY_FROZEN_GATE" if passed else "NOT_RUN_FAILED_STATISTICAL_GATE",
        source_commit=args.source_commit,prepared_receipt_sha256=file_sha(args.prepared/"RECOVERY.json"),
        protocol_sha256=file_sha(HERE/"PROTOCOL.json"),amendment_sha256=file_sha(HERE/"PREFIT_AMENDMENT.json"),
        dependency_statsmodels=statsmodels.__version__,elapsed_seconds=time.monotonic()-started,
        artifacts={p.name:file_sha(p) for p in output.iterdir()},
        scope="Fixed2021within allowed2020-2022seen-training domain; no newOOS/nativecertification. Prediction and shadow risk alone cannot qualifyalpha."))
    print(json.dumps({"passed":passed,"halves":halves,"risk":{k:{n:v[n] for n in ("mean_projected_gross","annual_fixed_weight_intraday_RV_sigma","gross_price_proxy_USDT")} for k,v in risk_summary.items()}},indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--archive",type=Path,required=True)
    parser.add_argument("--prepared",type=Path,required=True)
    parser.add_argument("--dependencies",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--source-commit",required=True)
    run(parser.parse_args())
