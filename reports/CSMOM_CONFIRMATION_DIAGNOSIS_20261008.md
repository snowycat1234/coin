# SHORT confirmation: hedge loss, churn and isolated survival

## Decision and actual money

**Keep original CSMOM/SMA research controls; pause the exact daily own21d absolute-sign gate. Investment qualification NONE/CASH, stable net APR UNKNOWN.** This module changes diagnosis and next research choice, not trading parameters or previous returns.

The server read saved targets and actual fill/funding journals for20 complete independent10k wallets, five seen development stages. **0new wallets,0fits,0parameter trials.** Previous failed gate and losses remain in [the original economic report](CSMOM_ABSOLUTE_SHORT_20261008.md). Two funding units are conditional scenarios, not independent samples; no NAV stitching.

|Seen stage|Extra covariance downscale days / nonterminal days|LONG weight-days reduction|Actual same-week gate reopens|Gross PnL change|Extra fees + execution|Net PnL change|
|---|---:|---:|---:|---:|---:|---:|
|2024 Jan–Jul|77/181|10.58%|10|+633.34|+26.16|+606.06|
|2024 Jul–Aug12|19/40|13.52%|2|−288.58|+13.14|−301.78|
|2024 Aug13–Jan2025|71/141|14.08%|5|−27.84|+8.76|−36.92|
|2025 Jan–Jul|56/180|10.41%|5|+279.22|+6.50|+272.61|
|2025 Jul–Jan2026|55/183|9.75%|7|−106.11|+44.83|−151.11|

Money columns are USDT, funding-scale.01, full capital10k in each independent wallet. Funding delta reconciles the remainder. Both units and actual source identities remain in [the diagnosis JSON](CSMOM_CONFIRMATION_DIAGNOSIS_20261008.json). No new APR or matched-risk alpha claim.

## Verified mechanisms and limits

1. **Removing shorts removes hedges.** For every saved intent, the inspector independently reconstructs the sign veto and past30-return signed covariance. Final targets equal vetoed targets times the required downscale, error<1e−12. Largest direct-veto risk estimate27.62% annualized; extra multiplier reaches.362, final target estimate<=10%. Retained legs never exceed their original targets. Five stages lose9.75%–14.08% LONG weight-days. Weight-days are not causal dollar attribution: NAV sizing, execution and risk paths interact. In2024H1 LONG gross actually improves despite less LONG weight-days.
2. **Different failures have different sources.** In2024H2(scale.01), SHORT gross improves446.34 but LONG gross loses474.19; extra costs8.76 do not explain most of this tradeoff. July loses238.43 SHORT gross and50.15 LONG gross, so not all failures are long-budget losses. In2025H2 SHORT gross+3.75 is outweighed by SHORT cost increase31.03; LONG gross loses109.87.
3. **Gate churn exists.** Actual full-flat same-week reopens10/2/5/5/7 are fewer than intent sign toggles; partial reductions are not reopens.2025H2 gate-full-close associated costs28.36 and reopening costs10.08 differ from SHORT cost increment31.03 and whole-wallet increment44.83. These costs cannot all be removed from an old return curve to invent a new strategy. Any buffer/cooldown requires a complete wallet rerun.
4. **Portfolio risk differs from isolated SHORT survival.** Existing [XRP forensics](SHORT_LIQUIDATION_FORENSIC_20261008.md) showed individually exhausted1x isolated SHORT collateral while portfolio gross was low. Proportional reductions release proportional collateral: they reduce loss dollars without generally widening remaining bankruptcy distance. Profitable LONG collateral is not automatically transferred. Signed covariance is not a single-leg survival guarantee.

Actual partial fills are grouped into logical order legs. Normal entries/adds, full/partial reductions, terminal paid flattening, hard risk reductions, gate exits/reopens and external liquidation are distinguished. Missing/ambiguous clock reasons remain UNKNOWN/AMBIGUOUS. Order reasons are cost associations, not profit causality.

## Mature references and reuse

[Daniel & Moskowitz, Momentum Crashes, JFE2016](https://kentdaniel.net/papers/published/jfe_16.pdf), CC BY4.0, studies winners-minus-losers rebound risk and warns that forward-looking beta hedges overstate implementable performance. This motivates distinguishing relative hedges from outright bearish forecasts; it does not establish crypto conditional alpha.

[Barroso author page](https://sites.google.com/site/pedromsbarroso/) lists Momentum Has Its Moments, replication package and errata. Strategy-return risk scaling and today's signed asset covariance are different estimators; our existing30d10% downscale already supplies portfolio volatility management. Replication contents/license unconfirmed, no code copied. [Cederburg et al., JFE2020](https://www.lehigh.edu/~xuy219/research/COWY.pdf) cautions against universal performance claims for volatility management. No dependency, upstream code or new platform added.

## Decision and next step

Adopt the decomposition and separation of hedge, directional prediction and isolated protection. Retain original CSMOM/SMA controls, dual-direction and shared-capital capabilities. Pause the precise daily hard gate; reopen only with new independent mechanism evidence, not threshold/cooldown scanning on these stages. Buffer work stays conditional on avoidable costs being a decision-changing bottleneck. Complex selectors remain paused pending stable ranking predictability; original static mix needs independent conditional information or concrete risk-repair value.

**Next:** read the original SHORT pre-liquidation collateral, legal minute execution capacity, outstanding orders and complete exit costs. Determine whether one predeclared protection can act before exhaustion while retaining relative signal and existing margin/caps. No threshold selected here. If inputs/clock do not support this, state the limit and select a supported direction. Avoiding one historical liquidation is not evidence of improved net returns.

## Reproduction and actual resources

Run source commit39795e1, complete identity in JSON. Server entry must run in8GB/swap0 coin-research.slice, with a fresh state path:

```bash
systemd-run --user --unit=coin-short-diagnosis-replay --slice=coin-research.slice \
  -p MemoryMax=8000000000 -p MemorySwapMax=0 \
  -p WorkingDirectory=/home/ubuntu/coin/short-research-repository \
  env PYTHONDONTWRITEBYTECODE=1 POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 \
  OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  PYTHONPATH=/home/ubuntu/coin/short-research-repository:/home/ubuntu/coin/short-research-repository/src \
  timeout 300 /home/ubuntu/coin/coin_collector_v3_fixed/work/research-venv/bin/python -B \
  scripts/research/diagnose_csmom_confirmation.py \
  --state /home/ubuntu/coin/execution-state/short-diagnosis-replay
```

Local independent reconciliation (fresh output):

```bash
bash scripts/with_task_progress.sh --title 'SHORT mechanism independent reconciliation' -- \
  /usr/bin/python3 scripts/research/review_csmom_confirmation_diagnosis.py \
  --output /home/xflops/coin-state/short-diagnosis-replay-review.json
```

Final v2 completed5/5, exit0,1.669589s, state174,113B measured2026-10-07T23:01:47Z. ResultSHA4c09e7350a8ad812a6dc088ffab0fcdcb1448d1888f1e33ff8d3f3fb420d8b18. Initial v1 completed1.686530s/state169,087B but classified first LONG entries as ADD; independent code review caught it. Correction reran only the readonly inspector. Original v1 preserved at server execution-state/short-diagnosis-20261008-v1/RESULTS.json, SHAbc33148ea5460c9150bf2abbec60cb17d80c975165e8cb663dd173699f61c462. Total sequential science3.356120s; transfer/review/publication are separate. Both attempts0wallet/fit.

[Independent review](CSMOM_CONFIRMATION_DIAGNOSIS_REVIEW_20261008.json) reconciles20 saved cash/direction/cost summaries, category sums, reopening costs and paired deltas. Additional independent code review checked target algebra, fill grouping and reason semantics. The local arithmetic reviewer did not independently reread server market/ledger or reconstruct covariance. Target error<=1e−12, financial bridge tolerance1e−7 USDT; no unrelated tests rerun.

Completed unit has no usable RAM/CPU counters: true peak UNKNOWN; finite8GB/swap0 verified. No remaining server research unit at observation time, collector health not recertified. D's last real aggregate scan45,455,143,069B@1791408013.8738086 predates this small addition, not a current scan. No market data added. No keys/real/Testnet/mainnet orders, paid service, GPU or locked body. BinanceUSD-M+Bybit fees remains cross-venue proxy; funding-unit, MMR, CORE5 eligibility and actual cap-drift limitations remain. Complete capital10k,30%abs/60%gross,1x isolated/no autotopup unchanged.
