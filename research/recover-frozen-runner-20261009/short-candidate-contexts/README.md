# Two frozen short candidate contexts and training complementarity

Recommendation: test **MOMENTUM30_SHORT_ONLY first** in one separately controlled pool-expansion experiment, after the other task completes its proxy risk-order correction. No fit or wallet is launched here. Negative standalone returns are not an exclusion gate; complementary action availability and conditional utility are the research question.

The original778-date CASH/VOL/CS pack stays byte-identical, SHA25666c5fdb2317689ed1d084c3f8eeb6e1781fa04ccc15e6243784a03a3555e7676. Existing Donchian single-expert778/61 contexts are referenced with exact hashes in `CONTEXT_PACKET.json`, not copied or overwritten. New momentum single-expert contexts have the same dates, episodes and symbol order. Each has exact masks/reasons and unramped raw/covariance-scaled targets; this is not an expanded model pack. Training signal state advances on every calendar day, including days excluded from mature economic outcomes. Genuine200-bar eligibility, strict availability and original covariance source verify independently. Training asset eligibility is3556/3890;334excluded asset-dates remain explicitly masked. Development305/305asset-dates are eligible, and applying the original cash ramp/final target-zero reproduces the saved native61 targets exactly.

May–June is already seen development. Its **outcomes are not read by the complementarity diagnostic**, used for candidate selection, fitting or any statistic below. Only the778mature pre-May dates and five original training episodes enter the evidence. Both short hypotheses were selected retrospectively after June inspection; no pristine OOS claim.

## Explicit proxy contract

Reuse `modules/collector_research/pipeline/economics.py:proxy_step`: quantity=NAV×individual covariance-scaled target/start execution price;13.5bp per traded notional (combined fee/friction approximation); actual signed funding scale1 with original strict-prior-mark ownership brackets. The primary reference starts each expert/day from10k flat and pays terminal exit. The secondary reference carries each single expert through one of five contiguous training episodes, with fresh cash at its start and paid exit at its end. These are daily quantity proxies, not native wallets or reconstructed switching returns. No independent-account PnL is stitched or added.

Utility is `log1p(net_return)−0.5×daily_endpoint_MDD`, where endpoint_MDD=`max(0,−net_return)`. This uses the original teacher's log-growth/half-drawdown convention (public d69e9ac source member `source/scripts/research/conditional_selector_inputs.py`, SHA9c6658cd7682b6c5470585cbe927c20893e98a3e071cd52e56c5de280e86f207), with an explicitly one-day horizon and no intraday drawdown claim. The proxy quantity convention differs from native completed-close sizing, lot/capacity/orders/liquidation. The original native financial, risk and execution sources remain unchanged. No new blend or budget/risk-order mapping is introduced; the separate semantic correction remains required before future training. `TRAIN778_SHORT_COMPLEMENTARITY_PROXIES.npz` is outcome diagnostic data, never causal features.

## Training-only comparison

| Measure | Donchian20/10 short | Momentum30 short |
|---|---:|---:|
| Available / active dates |778 /547|778 /587|
| Mean / peak target gross |10.19% /32.61%|12.46% /36.00%|
| Net target correlation with VOL |−.3182|−.4214|
| Pooled same-asset target correlation with CS |+.2680|+.2740|
| Daily net proxy correlation with VOL / CS |−.6954 /+.2001|−.8112 /+.4366|
| Shared loss days with VOL / CS |60 /215|60 /226|
| Shared bottom5% loss dates with VOL / CS |0 /7|0 /7|
| Active on both-existing-adverse dates |162 /242|171 /242|
| Mean utility on both-existing-adverse dates |9.16bp|13.87bp|
| Positive utility above CASH on those dates |113 /242|125 /242|
| Mean positive utility excess on those dates |11.96bp|16.24bp|

CS is exactly market-neutral, so correlation of its total signed target is undefined; report `null`, not fabricated zero. Asset-target and proxy-return correlations are provided instead. Target overlap uses shared/opposite signed absolute notional over maximum absolute notional, alongside full pairwise counts. The short candidates' net target correlation is+.6729 and proxy-return correlation+.7079; they share24bottom5% loss dates, arguing against admitting both initially.

The pre-analysis ranking criterion is mean positive daily utility excess over best of CASH/VOL/CS on ex-post days where both risky experts lose. Momentum ranks first, and also has the larger signed mean utility there. The continuous episode-reference check agrees: on179both-adverse dates, mean utility19.07bp versus13.19bp; positive-excess19.87bp versus14.29bp. Momentum's advantage holds in four of five training episodes for both references. Ex-post adverse/tail conditions require future outcomes and are descriptive associations, never executable decision gates. Positive-part excess is not a constrained oracle bound or portfolio profit.

Costs and utility losses are retained: unconditional primary mean utility is−12.33bp for momentum versus−10.05bp for Donchian. Even the causal past30CORE5-downtrend condition has negative mean utility for both. Momentum offers broader downside coverage but greater gross exposure, more CS co-movement and rebound/cost risk; no matched-risk or learnable-timing claim. These findings justify a controlled experiment, not adoption.

## Oracle and verification

No reusable optimizing shared-wallet bound with the exact dailyL1≤.1 switching budget/native quantities/cost state was found. `oracle_expert_opportunity.optimal_path` explicitly uses rebased independent growth and target-distance surcharges; frozen mixtures and transformer oracles produce comparisons rather than that bound. Incremental constrained bounds with/without each candidate are `NOT_RUN`; no optimizer was built.

`SHORT_CANDIDATE_CONTEXT_PLAN.json` binds sources and conventions before diagnostic computation. `MOMENTUM_CONTEXT_READY.json` proves independent causal state/eligibility/covariance and saved-target parity. `INDEPENDENT_CHECK.json` verifies all7,780expert-days across two panels with scalar Decimal arithmetic; maximum utility error4.76e−16. Recheck with `verify_short_candidate_packet.py --repo REPO`; reconstruct contexts with `momentum_training_context.py --state STATE --output NEW_DIRECTORY`; reproduce diagnostics with `short_candidate_complementarity.py` and the bound plan. No downloads are required when using recovered inputs. All packet references are relative. No model/scaler fit, new wallet, strategy change or pool promotion occurred. Historical publication and exchange/account rules remain uncertified.
