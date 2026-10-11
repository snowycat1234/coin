"""Independent small unit/share cashflows; source pure functions only, no model."""
import argparse
import hashlib
import json
import resource
import sys
import time
from decimal import Decimal as D, localcontext
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from modules.slow_momentum_cpd.core import DAY_US, trend_features
from modules.slow_momentum_cpd.cost_feasibility import arithmetic
from modules.slow_momentum_cpd.sharpe import InvalidScore, calendar_axis, capture, scored_sharpe, scaled_outcomes


def assert_close(a, b, tol=1e-12):
    if abs(float(a)-float(b)) > tol:
        raise AssertionError((a, b))


def hand_share_cashflows(weights, returns, capital=D(10000)):
    """Tiny supplied synthetic prices/quantities, not a native wallet/backtester."""
    w, r = [[D(str(v)) for v in row] for row in weights], [[D(str(v)) for v in row] for row in returns]
    prices, shares = [D(100)]*len(w[0]), [D(0)]*len(w[0])
    cash_gross = cash_after_fee = cash_after_all = capital
    turnover = D(0)
    for t in range(len(w)+1):
        for asset in range(len(prices)):
            target = D(0) if t == len(w) else capital*w[t][asset]/prices[asset]
            dq = target-shares[asset]
            sign = D(1) if dq>0 else D(-1) if dq<0 else D(0)
            fill = prices[asset]*(1+sign*D('.0008'))
            nominal = abs(dq)*prices[asset]
            charged = abs(dq)*fill*D('.00055')
            cash_gross -= dq*prices[asset]
            cash_after_fee -= dq*prices[asset]+charged
            cash_after_all -= dq*fill+charged
            turnover += nominal/capital
            shares[asset] = target
        if t<len(w):
            prices = [p*(1+r[t][a]) for a,p in enumerate(prices)]
    return {'gross':(cash_gross-capital)/capital,'fee':(cash_gross-cash_after_fee)/capital,
            'cost':(cash_gross-cash_after_all)/capital,'net':(cash_after_all-capital)/capital,'turnover':turnover}


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path,required=True); args=parser.parse_args()
    if args.output.exists():
        raise FileExistsError('fresh synthetic receipt required')
    start=time.monotonic(); checks=[]
    with localcontext() as context:
        context.prec=40
        rate=D('.15')/D(365).sqrt(); daily_vol=D('.02'); pos=D('.5'); realized=D('.03')
        w=rate*pos/(daily_vol*5); annual_form=D('.15')*pos/(daily_vol*D(365).sqrt()*5)
        scaled=rate*realized/daily_vol
        assert abs(w-annual_form)<D('1e-38') and abs(w*realized-pos*scaled/5)<D('1e-38')
        assert_close(rate,float(.15/np.sqrt(365)))
        seed_positions=[D('.3'),D('-.1'),D('.4')]; mean=sum(seed_positions)/3
        assert_close(mean,D('.2'))
        five_asset_return=rate*mean*D('.10')/(daily_vol*5)
        assert_close(five_asset_return, sum(rate*p*D('.10')/daily_vol for p in seed_positions)/(3*5))
        assert_close((rate*D(1)/(daily_vol*5))/(rate*D(1)/daily_vol),D('.2'))
        checks.append({'name':'annual_daily_units_fixed5_assets_one3_seed_mean','target_fraction':float(w),
                       'captured_fraction':float(w*realized),'position_mean':float(mean),'only_one_eligible_asset_budget_fraction':.2})
        fixtures=[('long_paid_exit',[[.1]],[[.1]]),('short_paid_exit',[[-.1]],[[.1]]),
                  ('constant_target_drift',[[.1],[.1]],[[.1],[0.]]),
                  ('reverse_sign',[[.1],[-.1]],[[0.],[0.]]),
                  ('multiasset_sign_and_drift',[[.1,-.07],[.07,.03],[-.03,.02]],[[.1,-.2],[-.2,.1],[.5,-.1]])]
        for name, weights, returns in fixtures:
            summary,_=arithmetic(weights,returns); ref=hand_share_cashflows(weights,returns)
            for key, field in [('gross','gross_price_proxy'),('cost','fixed_cost_total'),('fee','fee'),
                               ('net','fixed_cost_adjusted_price_proxy'),('turnover','drift_trade_turnover')]:
                assert_close(ref[key],summary[field])
            larger=hand_share_cashflows(weights,returns,D(100000))
            for key in ref:
                assert_close(ref[key],larger[key])
            # A common exposure-unit scale affects G,T,C together, not break-even/sign.
            scale=3
            double,_=arithmetic((np.array(weights)*scale).tolist(),returns)
            for field in ['gross_price_proxy','fixed_cost_total','drift_trade_turnover']:
                assert_close(double[field],scale*summary[field])
            checks.append({'name':name,**{key:float(value) for key,value in ref.items()},'source_arithmetic_matches':True,
                           'reference_capital_fraction_invariant':True,'common_exposure_scaling_linear_no_rescue':True})
        summary,_=arithmetic([[.1]],[[.1]])
        assert_close(summary['fixed_cost_total'],D('.0002834956'))
        assert_close(summary['fixed_cost_total'],D('.00135')*D('.21')-D('.00055')*D('.0008')*D('.01'))
        checks.append({'name':'single_side13_5bp_already_counts_entry_and_exit','turnover':.21,'fee_on_fill_cost':.0002834956,
                       'no_extra27bp_multiplier':True})
        exit_summary,exit_daily=arithmetic([[.1],[0.]],[[.1],[np.nan]])
        assert_close(exit_daily[1]['drift_trade_turnover'],D('.11'))
        assert exit_summary['terminal_cost']==0
        for weights,returns in [([[.1]],[[np.nan]]),([[.1]],[[-1.]])]:
            try:
                arithmetic(weights,returns)
            except ValueError:
                pass
            else:
                raise AssertionError('missing/invalid held return was erased')
        mask=np.ones((1,5),bool)
        try:
            capture(np.zeros((1,5)),mask,np.full((1,5),np.nan))
        except InvalidScore:
            pass
        else:
            raise AssertionError('zero signal erased eligible unknown outcome')
        out,missing=scaled_outcomes(np.array([0]),mask,np.full((2,5),np.nan),np.full((2,5),.02))
        assert len(missing)==5 and np.isnan(out).all()
        checks.append({'name':'cash_NaN_allowed_old_hold_exit_paid_eligible_missing_rejected','paid_previous_hold_change':.11})
        a,_=arithmetic([[.1]],[[0.]]); b,_=arithmetic([[.1]],[[0.]])
        bridge,_=arithmetic([[.1],[.1]],[[0.],[0.]])
        assert_close(a['fixed_cost_total']+b['fixed_cost_total'],2*bridge['fixed_cost_total'])
        assert calendar_axis(np.arange(6)*DAY_US,0,5*DAY_US).tolist()==[0,1,2,3]
        checks.append({'name':'separate_blocks_paid_entry_terminal_and_strict_label_boundary','no_bridge':True})
        p1,_=arithmetic([[.1]],[[0.]]); p2,_=arithmetic([[-.1]],[[0.]])
        ensemble,_=arithmetic([[0]],[[0.]])
        assert ensemble['fixed_cost_total']==0 and (p1['fixed_cost_total']+p2['fixed_cost_total'])/2>0
        checks.append({'name':'seed_averaging_before_L1_not_average_wallet_cost','cancelled_ensemble_cost':0})
    _,raw,_=trend_features(np.array([[100.],[110.],[99.]]))
    assert_close(raw[1,0],.1); assert_close(raw[2,0],-.1)
    assert abs(raw[1,0]-np.log(1.1))>.004
    checks.append({'name':'simple_price_return_not_log_or_percent_units','return100_to110':float(raw[1,0]),'log_return_distinct':float(np.log(1.1))})
    synthetic_r=.01*np.sin(np.arange(190))+.001*np.cos(np.arange(190)*2)
    prices=100*np.cumprod(1+synthetic_r)
    _,r,v=trend_features(prices[:,None]); t=70; observed=r[1:t+1,0]; decay=1-2/61
    weights=decay**np.arange(len(observed)-1,-1,-1); mean=np.dot(weights,observed)/weights.sum()
    centered=np.dot(weights,(observed-mean)**2)/(weights.sum()-np.dot(weights,weights)/weights.sum())
    assert_close(v[t,0],np.sqrt(centered)); assert np.isnan(v[:60]).all()
    changed=prices.copy(); changed[t+1:]*=2; _,_,future_vol=trend_features(changed[:,None]); assert v[t,0]==future_vol[t,0]
    gap=prices.copy(); gap[65]=np.nan; _,gr,gv=trend_features(gap[:,None])
    assert np.isnan(gr[65:67]).all() and np.isnan(gv[65:126]).all() and np.isfinite(gv[126,0])
    checks.append({'name':'causal_daily_simple_return_EWMA_unbiased_std_gap_reset','daily_vol_reference':float(np.sqrt(centered)),
                   'source_daily_vol':float(v[t,0]),'annual_multiplier_not_inside_sigma':True,'future_change_no_effect':True})
    values=np.array([.01,-.005,.003,-.002]); manual=np.sqrt(365)*values.mean()/np.sqrt(np.mean((values-values.mean())**2))
    assert_close(scored_sharpe(values),manual); assert_close(scored_sharpe(values*5),manual)
    checks.append({'name':'daily_portfolio_Sharpe_population_variance_and_scale_invariance','manual_annual_Sharpe':float(manual)})
    result={'status':'PASS','checks':checks,'fixture_count':len(checks),'new_training':0,'model_objects_created':0,
            'new_inference':0,'native_wallets':0,'market_data_used':False,'elapsed_seconds':time.monotonic()-start,
            'max_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            'review_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':'PASS','fixtures':len(checks),'elapsed_seconds':result['elapsed_seconds'],'max_rss_bytes':result['max_rss_bytes']}))


if __name__=='__main__':
    main()
