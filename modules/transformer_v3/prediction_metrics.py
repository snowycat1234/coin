"""Forecast accuracy and proxy oracle regret, kept separate from native economics."""
import numpy as np
from scipy.stats import spearmanr

def old_policy_probability(utility):
    scores=np.stack((utility[...,0],np.zeros(utility.shape[:-1]),utility[...,1]),-1)
    scores=(scores-scores.max(-1,keepdims=True))/.02
    p=np.exp(scores);return p/p.sum(-1,keepdims=True)

def metrics(pred,relative,experts,active):
    scores=pred['relative'][...,1];pearson=[];spearman=[];hit=[];spread=[]
    for i in range(len(scores)):
        mask=active[i]&np.isfinite(relative[i,:,1])&np.isfinite(scores[i])
        if mask.sum()<4:continue
        forecast=scores[i,mask];future=relative[i,mask,1]
        if np.ptp(forecast)<=1e-12 or np.ptp(future)<=1e-12:continue
        pearson.append(float(np.corrcoef(forecast,future)[0,1]));spearman.append(float(spearmanr(forecast,future).statistic))
        order=np.argsort(forecast,kind='stable');spread.append(float(future[order[-2:]].mean()-future[order[:2]].mean()))
        delta=future[:,None]-future[None,:];estimated=forecast[:,None]-forecast[None,:]
        pairs=np.triu(np.abs(delta)>1e-12,1)
        if pairs.any():hit.append(float((np.sign(delta[pairs])==np.sign(estimated[pairs])).mean()))
    probabilities=pred['policy_probability'] if 'policy_probability' in pred else old_policy_probability(pred['utility'])
    mask=active&np.isfinite(experts).all(-1)&np.isfinite(probabilities).all(-1)
    u=experts[mask];p=probabilities[mask]
    if len(u):
        gap=np.sort(u,-1)[:,-1]-np.sort(u,-1)[:,-2]
        regret=np.maximum(0.,u.max(-1)-(p*u).sum(-1))
        categorical=np.maximum(0.,u.max(-1)-u[np.arange(len(u)),p.argmax(-1)])
        non_tie=gap>1e-9
        action_hit=float((p[non_tie].argmax(-1)==u[non_tie].argmax(-1)).mean()) if non_tie.any() else None
    else:regret=categorical=np.array([]);action_hit=None
    return dict(rank_IC_mean=float(np.mean(pearson)) if pearson else None,rank_IC_median=float(np.median(pearson)) if pearson else None,
                Spearman_mean=float(np.mean(spearman)) if spearman else None,Spearman_median=float(np.median(spearman)) if spearman else None,
                pairwise_hit_rate=float(np.mean(hit)) if hit else None,valid_rank_days=len(spearman),
                top2_minus_bottom2_30d_realized_future_spread_mean=float(np.mean(spread)) if spread else None,
                top2_minus_bottom2_30d_realized_future_spread_median=float(np.median(spread)) if spread else None,
                mean_soft_policy_oracle_regret=float(np.mean(regret)) if len(regret) else None,
                mean_argmax_action_oracle_regret=float(np.mean(categorical)) if len(categorical) else None,
                expert_action_hit_rate_non_tie=action_hit,valid_expert_asset_samples=int(mask.sum()),
                score_horizon_days=30,expert_horizon_days=60,regret_scope='CONTINUOUS_DAILY_EXPERT_PROXY; NOT_NATIVE_WALLET_RETURN',
                spread_scope='FUTURE30D_PRICE_SPREAD_WITHOUT_REBALANCE_COSTS_OR_LIQUIDATION; NOT_PORTFOLIO_NET',
                future_labels_diagnostics_only=True,not_a_trade_availability_filter=True)
