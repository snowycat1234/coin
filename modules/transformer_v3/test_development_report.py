import numpy as np
from .development_report import half_linearity,regret_comparison,profile_comparison,CANDIDATES,SEEDS

def row(family,seed,mapping,scale,window,net,complete=True,profile='FULL'):
    return dict(family=family,seed=str(seed),mapping=mapping,funding_scale=scale,window=window,
        net_return_percent=net if complete else None,full_calendar_and_paid_cash=complete,profile=profile,
        net_USDT=net*100 if complete else None,liquidation_count=0,liquidation_loss_USDT=0.,mean_gross=.3 if profile=='HALF' else .6)

def test_registered_gate_carries_incomplete_ensemble_with_full_denominator():
    rows=[]
    for scale in (1.,.01):
        for w in range(6):
            for family in ('BASE_HOLD','BASE_SMA200_SIGNED','BASE_STATIC_DIRECTION3','OLD_FROZEN_TRANSFORMER_SHARED'):
                rows.append(row(family,'FROZEN_LEGACY','DIRECTIONAL',scale,str(w),0.))
            for family in CANDIDATES:
                for mapping in ('DIRECTIONAL','NEUTRAL','COMBINED'):
                    for seed in (*SEEDS,'ENSEMBLE'):
                        complete=not(family==CANDIDATES[0] and mapping=='NEUTRAL' and scale==.01 and w==5 and seed=='ENSEMBLE')
                        rows.append(row(family,seed,mapping,scale,str(w),1.+w*.01,complete))
    summaries,paired,chosen=profile_comparison(rows,CANDIDATES)
    incomplete=next(r for r in summaries if r['family']==CANDIDATES[0] and r['mapping']=='NEUTRAL')
    assert incomplete['rank_worst_scale_median_net'] is None and not incomplete['development_gate_pass']
    assert chosen['family']==CANDIDATES[0] and chosen['mapping']=='DIRECTIONAL'
    assert len(rows)==6*2*(4+3*3*4)

def test_half_pair_retains_unknown_prefix_and_reports_non_linear_cash():
    full=row('M','ENSEMBLE','NEUTRAL',1.,'w',-8.)
    half=row('M','ENSEMBLE','NEUTRAL',1.,'w',-1.,profile='HALF')
    r=half_linearity([full,half])[0]
    assert r['half_minus_half_full_USDT']==300.
    full['full_calendar_and_paid_cash']=False;full['net_USDT']=None
    r=half_linearity([full,half])[0]
    assert r['half_minus_half_full_USDT'] is None and not r['both_complete']

def test_regret_difference_is_paired_proxy_not_native_net():
    old=dict(family='CROSS_ASSET_MULTITASK',seed='ENSEMBLE',fold=1,funding_scale=1.,mean_soft_policy_oracle_regret=.04,
        mean_argmax_action_oracle_regret=.05,expert_action_hit_rate_non_tie=.4,rank_IC_mean=.1,Spearman_mean=.12)
    new=dict(old,family=CANDIDATES[1],mean_soft_policy_oracle_regret=.02)
    rows=regret_comparison([old],[new]);soft=next(r for r in rows if r['metric']=='mean_soft_policy_oracle_regret')
    assert np.isclose(soft['new_minus_old'],-.02) and 'NOT_WALLET_NET' in soft['scope']
