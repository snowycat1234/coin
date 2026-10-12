# Fixed causal score calibration inside training history

Selected after saved-model short attribution showed nonmonotone allocation
reliability and frequent rank-not-best events. This is exploratory seen training
history with a strictly chronological implementation, not a fresh holdout.

Exactly two scalar calibrator fits: fixed Ridge30 utility advantage and fixed
Logistic C1 win-event probability, trained only on Jan-Mar2022 rewards fully
matured before Apr1. Original181/607 models remain frozen. Validate full natural
Apr1–Sep13 calendar; outcomes must mature beforeSep14. Probability never substitutes
for expected utility. Compare raw scores/allocations and training-mean constants.
No parameter search, forced SHORT ratio, external59 outcomes or new market data.

Also distinguish actual absent negative targets from rank-not-best events using
saved paths. Two same-source paid one-day target references test existing BASE
versus utility-calibrated budgets under the existing L1/caps/past30 risk mapper.
These are conditional quantity references, not a continuous native wallet/return.
Funding units, exact charge mark, capacity/filter/margin and paid-flat authority
remain BLOCKED. Three causal-clock/omission/cash-preservation tests PASS. See
PROTOCOL.json and source manifests; checkpoints/results/date IDs are in result/.

Completed **STOP_FIXED_INTERNAL_CALIBRATION_GATE**: one attempt, exactly2scalar
fits,83real objective dates, maximum true reward maturity2022Mar31 08h<Apr1.
Source edd036fe2ce8ee5c97d36442820b76294fafe8b9; scientific result
9d0850edcade613534484eeaf9f70833085f827d.166natural internal validation dates,
160common mature labels beforeSep14. Original181/607/LSTM fits added:0.

Utility calibrated MSE3.9644352e-5 improves raw4.7916978e-5 by17.2645%, with
positive paired CI, but loses to training-mean constant3.9098178e-5: gateFAIL.
Probability Brier.1977773 vsrawallocation.2021516/constant.1981882, but constant−cal
95CI[-.00537985,+.00711214] crosseszero: gateFAIL. No calibrator/seed/threshold rescue.

On saved255-day original causal path,108of122positive short-reference dates
already have negative targets. Only14actually omit a negative target:9coupled
full action notbest and5rank-not-best; zero first-failing L1/risk omissions. This
does not count native fill absence because no wallet ran in this module.

Conditional short sleeve's mean per-new10k one-day net is+4.98759USDT, fromprice
10.48607−fees5.59625+fund.097765, while its riskutility isnegative. This is not a
continuous portfolio return or independent investment evidence. Aftercalibration,
negative-target dates decline142→114, mean short targetgross.04137→.00937.
Same common paid one-day targetreferences remainnegative:BASE mean net−3.57383,
calibrated−2.71545USDT. Probability is not used as expected utility in routing.

Actual invocation.897342s; two fit times.017453/.007794s. Three testsPASS, no
historical model/nativewallet/provider repeats. Zero-fit public restore is exact
for report, checkpoints' date support, omission/costCSV, predictions and targets.

```bash
export COIN_CPD_STATE=/workspace/short-calibration-reproduce
export QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE="$COIN_CPD_STATE"
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python research/short-score-calibration-20261012/run.py \
  --state "$COIN_CPD_STATE/COLD" --source-commit edd036fe2ce8ee5c97d36442820b76294fafe8b9 \
  --expected-commit 9d0850edcade613534484eeaf9f70833085f827d
```
