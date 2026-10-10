The July2024 GRU advantage is mostly signed composition, with gains concentrated
in July. This read-only calculation reuses the pinned earlier ledger reader and
reconciles all252 saved rows. It makes zero fits/inferences/wallets/downloads.

| GRU minus control, USDT | Frozen VOL | Static50 |
|---|---:|---:|
| Price PnL excess | +295.43 | +112.25 |
| Funding excess | +6.23 | +.91 |
| Account cost saving | −15.08 | −1.10 |
| Net PnL excess | +286.58 | +112.07 |
| Descriptive signed-composition price component | +375.76 | +271.98 |
| Descriptive gross-magnitude price component | −83.20 | −158.95 |
| Own-NAV price component | +2.87 | −.77 |

The symmetric magnitude/composition/NAV identity is the same one used in the
earlier interpretation. It is additive accounting, not a causal exposure-matched
strategy test. Net costs remain at account level because expert trades netted.

GRU VOL/CS/SHORT legs contributed+93.29/+144.16/+37.34 price PnL. July produced
+254.05 net, with VOL+136.82 and CS+129.84 price gains; August produced−3.95
net, with VOL−43.53/CS+14.33/SHORT+37.69 price contributions. September1 was
only the−.96 paid close. Month grouping uses the decision/start date, so July31
ends August1. The machine-readable result includes all four wallets' monthly
price/funding/cost/exposure and expert-leg contributions.

Actual mean active gross/net exposure is14.96%/+5.19% for GRU,
12.88%/+12.88% VOL,18.64%/+6.44% Static50,10.58%/+3.59% Cash50.
GRU requested21.48% SHORT on average but applied only8.94% after its carried
L1 ramp. In August those means were41.97% requested versus17.28% applied;
the model also carried29.50% CS budget despite requesting only8.97% CS.
Budget percentages are not signed asset notionals: offsetting VOL/CS/SHORT
legs can cancel, and the target recipes already size their own risk.

SHORT does precede some profitable observed declines: on August27 the saved
request was97.48%, prior applied budget44.76%, current applied49.70%, and the
SHORT leg earned43.69. Of that contribution,38.56 belongs algebraically to
units already held before the interval and5.13 to the current quantity change.
Across the whole block SHORT earned37.34 price PnL:37.25 from prior held units
plus.09 from net quantity changes. This split is descriptive, not a wallet with
trades deleted or proof of predictive causation. High SHORT requests also
preceded losses: August23 requested97.45%/applied29.96% and lost26.27 on the
SHORT leg. Profitable SHORT intervals31/loss intervals28 contribute+86.35/−49.01.

The largest whole-wallet gain, August7 (+118.56), came mainly from CS+98.46
and VOL+20.02; its current SHORT request was0.000034%, with.92% carried budget
and only+.40 SHORT price PnL. Total price gains in actual negative underlier
positions were177.30, much larger than the explicit SHORT leg's37.34; signed
CS positions explain why “short exposure” cannot be equated to the SHORT head.

The top three/five observed model intervals contribute265.13/367.25, representing
31.19%/43.21% of positive contribution mass. Every interval is retained in
the CSV; no dates are deleted and no alternative wallet is evaluated.

What repeats from July2023 is favorable signed composition, some early long
participation and later short participation under the same ramp. What differs
is the economic source:2023 VOL/CS/SHORT price contributions225.52/−28.47/403.51,
versus2024+93.29/+144.16/+37.34. Top-five positive-mass concentration fell from
78.93% to43.21%; the2024 gain mostly occurred in July rather than a large
August SHORT win. This is not repeated success of precise short timing.
October2023 assigned37.91% mean budget to eligible but flat SHORT targets and
missed gains; January's signed composition hurt by604.54 versus its control;
April's same frozen checkpoint lost226.53 versus Static50−198.56. Those failures
remain. The2023/January models have different prefix checkpoints/scalers/starts;
only April and July2024 share the exact frozen model. No statistical stability,
pristine OOS, oracle, APR or promotion claim follows.

Native marks remain missing for all five assets August12 10:02/10:03 UTC;
daily economics remain verified. No marks are filled or native outcomes inferred.
STOP after this attribution. Source hashes and all dates are in
[RESULT.json](RESULT.json), [DAILY_ATTRIBUTION.csv](DAILY_ATTRIBUTION.csv) and
[RECEIPT.json](RECEIPT.json). Reproduce under the existing one-CPU NumPy bounded
recovery guard with `CALCULATE.py --repo REPO --destination NEW_OUTPUT`.
