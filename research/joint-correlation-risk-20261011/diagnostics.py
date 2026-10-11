"""Frozen forecast gates, then conditional target-only trade-path diagnostics."""
import numpy as np
from joint import PAIRS,bootstrap,losses

NAMES=('NATIVE30','JOINT_BLEND30','PURE_REALIZED30','LAST_DAY_REALIZED','TRAIN_LONGRUN')
TARGET_NAMES=('BASE','JOINT','STATIC_TRAIN_GROSS','STATIC_TRAIN_RISK')


def prediction(predictions,actual,roles):
    loss=np.column_stack([losses(predictions[:,k],actual) for k in range(len(NAMES))])
    reports={};allpass=True
    for block in ('A','B'):
        selected=roles==block;x=loss[selected];means=x.mean(axis=0)
        pair={}
        for k,name in enumerate(NAMES):
            if name=='JOINT_BLEND30':continue
            delta=x[:,1]-x[:,k]
            pair[name]=dict(mean_delta=float(delta.mean()),ratio=float(means[1]/means[k]),
                relative_improvement=float(1-means[1]/means[k]),
                paired_joint7day_bootstrap95=bootstrap(delta,7),
                paired_joint30day_sensitivity95=bootstrap(delta,30))
        gates=dict(native_improvement_2pct=pair['NATIVE30']['relative_improvement']>=.02,
            native_CI_upper_negative=pair['NATIVE30']['paired_joint7day_bootstrap95'][1]<0,
            lastday_CI_upper_negative=pair['LAST_DAY_REALIZED']['paired_joint7day_bootstrap95'][1]<0,
            pure_realized30_not_worse_2pct=pair['PURE_REALIZED30']['ratio']<=1.02,
            train_longrun_not_worse_2pct=pair['TRAIN_LONGRUN']['ratio']<=1.02)
        secondary={}
        for name,w in (('fixed_common_long',np.full(5,.2)),('fixed_signed',np.array([.25,.25,-.25,-.25,0]))):
            q=np.einsum('i,dkij,j->dk',w,predictions[selected]-actual[selected,None,:,:],w)
            secondary[name]={n:float(np.mean(q[:,k]**2)) for k,n in enumerate(NAMES)}
        passed=all(gates.values());allpass=allpass and passed
        reports[block]=dict(joint_dates=int(selected.sum()),MSE={n:float(means[k]) for k,n in enumerate(NAMES)},
            paired_comparisons=pair,gates=gates,passed=passed,secondary_quadratic_correlation_losses=secondary,
            sample_unit='one joint date; neither ten pairs norfive coins are independent samples')
    return dict(status='PASS_FIXED_PREDICTION_GATE' if allpass else 'STOP_FIXED_JOINT_CORRELATION_BLEND',
        passed=allpass,blocks=reports,seed=811132,bootstrap_draws=1000,bootstrap_primary_days=7,
        limitations='Dependent seen development history; circular block CI diagnostic, not pristine OOS/regime independence or forecastESS'),loss


def portfolio_variance(weights,realized):
    return np.einsum('di,dij,dj->d',weights,realized,weights)


def proportional_controls(base,candidate,scale,training,next_cov):
    selected=training&(np.abs(base).sum(axis=1)>0)
    mean_scale=float(np.mean(scale[selected]))
    base_v=float(portfolio_variance(base[training],next_cov[training]).mean())
    joint_v=float(portfolio_variance(candidate[training],next_cov[training]).mean())
    if base_v<=0 or joint_v<0:raise ValueError('Positive training trade variance required')
    risk_scale=min(1.,float(np.sqrt(joint_v/base_v)))
    return np.stack([base,candidate,base*mean_scale,base*risk_scale],axis=1),dict(
        STATIC_TRAIN_GROSS=mean_scale,STATIC_TRAIN_RISK=risk_scale,
        calibration_joint_dates=int(training.sum()),BASE_train_mean_realized_variance=base_v,
        JOINT_train_mean_realized_variance=joint_v,
        scope='Only mature training labels, in-sample fitted-model calibration; not diagnostic/oracle parameter fitting')


def turnover(w):
    return float(np.abs(np.diff(np.vstack([np.zeros((1,5)),w,np.zeros((1,5))]),axis=0)).sum())


def economy(targets,roles,next_returns):
    reports={};allpass=True
    for block in ('A','B'):
        ix=roles==block;w=targets[ix];r=next_returns[ix]
        metrics={}
        for k,name in enumerate(TARGET_NAMES):
            p=np.einsum('di,dti->dt',w[:,k],r)
            rv=np.sum(p*p,axis=1);sigma=float(np.sqrt(rv.mean()))
            path=np.cumsum(p,axis=1)
            adverse=np.maximum(0.,-path.min(axis=1))
            threshold=float(np.quantile(adverse,.95))
            es=float(adverse[adverse>=threshold].mean())
            gross=np.abs(w[:,k]).sum(axis=1);mean_gross=float(gross.mean())
            to=turnover(w[:,k])
            metrics[name]=dict(mean_realized_trade_log_variance=float(rv.mean()),
                realized_trade_log_sigma=sigma,annual365_trade_variation_proxy=sigma*np.sqrt(365),
                adverse_trade_path_q95=threshold,adverse_trade_path_ES95=es,
                ES95_over_realized_sigma=es/sigma if sigma else None,
                mean_gross=mean_gross,max_gross=float(gross.max()),max_abs_asset=float(np.abs(w[:,k]).max()),
                max_abs_net=float(np.abs(w[:,k].sum(axis=1)).max()),
                target_turnover_including_initial_and_terminal_zero=to,
                turnover_per_mean_gross=to/mean_gross if mean_gross else None,
                hypothetical_fee_plus_slippage_reference_USDT=to*.00135*10000,
                terminal_target_zero_included=True,terminal_execution='NOT_RUN_UNKNOWN',
                native_fees_slippage_funding_netPnL='UNKNOWN_NOT_RUN')
        b=metrics['BASE'];j=metrics['JOINT']
        ratios=dict(actual_variance_ratio=j['mean_realized_trade_log_variance']/b['mean_realized_trade_log_variance'],
            risk_normalized_ES95_ratio=j['ES95_over_realized_sigma']/b['ES95_over_realized_sigma'],
            turnover_per_mean_gross_ratio=j['turnover_per_mean_gross']/b['turnover_per_mean_gross'])
        gates=dict(risk_normalized_tail_improvement_5pct=ratios['risk_normalized_ES95_ratio']<=.95,
            realized_variance_not_higher=ratios['actual_variance_ratio']<=1.,
            normalized_turnover_not_worse_5pct=ratios['turnover_per_mean_gross_ratio']<=1.05)
        # A constant position haircut has identically the same risk-normalized tail.
        for name in TARGET_NAMES[2:]:
            assert np.isclose(metrics[name]['ES95_over_realized_sigma'],b['ES95_over_realized_sigma'],rtol=1e-12)
        passed=all(gates.values());allpass=allpass and passed
        reports[block]=dict(joint_dates=int(ix.sum()),metrics=metrics,ratios=ratios,gates=gates,passed=passed,
            identical_target_limit_does_not_imply_equal_actual_risk=True,
            equal_risk='Only ES/sqrt(realized_variance) outcome normalization. No ex-post oracle saved targets, net returns or learnable profit.')
    return dict(status='PASS_CONDITIONAL_TARGET_RISK_GATE_ONLY' if allpass else 'STOP_FIXED_JOINT_CORRELATION_BLEND',
        passed=allpass,blocks=reports,wallets=0,
        domain='Fixed-weight TRADE5m log-path proxy, not mark risk/account/execution/liquidation protection/netPnL. Actual funding/fee/slippage/paid terminal close unknown.')
