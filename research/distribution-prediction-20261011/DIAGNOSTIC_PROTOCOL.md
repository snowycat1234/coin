# Frozen read-only attribution and tail diagnostic

Follow-up authorized after original results were reported. This protocol is
registered before calculating any new analytic-control scores, tail breakdown
or selection attribution. Original phase1/phase2 protocols, configurations,
trained model, forecasts, results and delivery manifest remain unchanged.
All history remains previously seen development; no reserve/locked data.

## Inputs, source audit and scope

Verify the saved model/forecast/unit-probe SHA from original results at
`0a11af1ffeeced4dcf8a84382da2d3975c34e5d5`. Use existing feature archive solely
to recover the original past22 mean/std and causal EWMA origin sigma. Confirm
reconstructed sample dates/assets/y and old Gaussian quantiles against saved
forecasts before computing new scores. Do not load/train the model, infer new
model forecasts, change original gates, or create native wallets. No downloads.

Audit official pinned code bf0a6554 with source lines and a synthetic TestDataset
witness: the distribution notebook uses30 lookback, Gaussian mu=np.mean(obs),
sigma=np.std(obs,ddof0). obs comes from past input timestamps, while future y
uses returns.shift(-lookforward). Do not confuse TestDataset with DistDataset's
different flow=True path. Original COIN control uses22 days and ddof1. Record
the exact horizon/scale/loss/CDF representation differences; paper's erroneous
CRPS grid is not adopted. Equal paired observations are fair for the stated
COIN comparison, but conditioning differences do not isolate architecture.

## Fixed analytic comparison (0 trained models)

Exactly two additional deterministic distributions, no calibration or search:

- A0, mean-removal attribution: N(0, original past22 sample sigma).
- A1, proposed minimum fair scale control: N(0, the original qLSTM's known
  origin EWMA sigma), decay.94/floor.0001 unchanged. It has no learned market
  multiplier, neural shape, mean drift, or fitted scale. This is the primary
  new control. It inherits the same causal long-memory volatility input as
  qLSTM, despite the latter's22-day feature sequence. No seed/decay grid.

Evaluate on exactly the old2265 windows/22 individual outcomes with the same37
quantile levels, CDF/endpoint atoms, proper CRPS, pinball and old eleven44-day
calendar clusters. Original model and control predictions are reused unchanged.
Report all periods, paired intervals and tail calibration. A0→A1 isolates the
scale change conditional on zero mean; original→A0 is mean removal. Differences
are not additive evidence of a neural contribution. Do not select a winner to
relabel the original experiment or apply either control to trade decisions.

## Exact tail denominator and uncertainty

Reproduce4.49% from economic q99: one actual execution-to-execution24-hour log
return per existing short opportunity,8/178 if the old stored result is correct.
Report eligible dates, distinct asset/exit pairs and unique dates; compare the
445 available asset-days and identify how eligibility chooses178. The22-day
distribution score instead counts overlapping future-return occurrences; report
its exact total/exceedances, unique labels and horizon-by-horizon values.

For Q4 tail rates report two-sided exact Clopper–Pearson95% binomial interval
as an **IID-only descriptive reference**, not a valid market-independence claim.
Primary dependence sensitivity: jointly resample nonoverlapping22-calendar-day
clusters retaining all assets/opportunities and their actual counts,2000 times.
Secondary sensitivity: same method with7-day clusters, fixed in advance.
Report counts and interval limitations; do not choose the narrower interval.
Keep dates fixed when forming clusters. Cross-asset shocks, overlapping input
windows and nonstationarity remain. For each symbol/month report denominators,
exceedances and the8 event witnesses with actual/predicted log/simple returns.
Also count distinct event dates and events shared with the Gaussian exceedances.

Use the saved public completed-close table only to compare the same day1 close
return with the actual00:01 return. Report threshold-crossing differences and
maximum clock/basis discrepancy. The late-December inference rows were not all
in the mature22-day scoring set; do not silently combine the two populations.

## Zero-selection attribution, no changed decision

On all178 original short opportunities, derive E[r] by integrating Q(u) and
E[exp(r)] by the original exact piecewise-quantile integral. Decompose expected
net into:
`1-exp(E[r])` (deterministic log-mean price term),
`-(E[exp(r)]-exp(E[r]))` (convexity/rebound term),
`-execution*(1+E[exp(r)])`,
`-fee*((1-execution)+(1+execution)*E[exp(r)])`,
and original strictly matured forecast funding under both1/.01 interpretations.
Report min/mean/max and fixed algebraic positive-count comparisons: price only,
price+funding, price+funding−execution, full net, full net without fee,
full net without execution. These are source attribution counterexamples,
not new policies or a cost/threshold search. The only actual rule remains
expected net>0. Confirm no tail penalty enters this expectation; the tail and
minimum-count gates are later replay sufficiency gates. Show whether the zero
count already occurs at gross price or is introduced by cost/funding.

Independently verify representative expectation integrals by scalar quadrature,
Jensen convexity, exact fee cashflows, and the source's selected mask. Tail
endpoint atoms are fixed, total mass.0001; report their contribution and do not
fit or change them to force acceptance. A high down probability need not offset
the magnitude of rebound losses. No evaluation threshold adjustment.

## Budget and stop

One fresh STATE diagnostic directory,0 fits,0 new neural inference,0 wallets,
2 fixed analytic controls,2000 resamples per specified interval. Command bound
120 seconds (within the existing30min wrapper),4 threads,7.5GB address cap,
15GB disk reserve; expected state<=10MB. Hash/source/row mismatch or nonfinite
input stops with retained attempt. Tests are limited to the new attribution and
interval/denominator counterexamples; original passed tests are source-bound
REUSED. Commit/push this plan and implementation before the new calculations.

After results, identify one next experiment only; do not run a third analytic
control, refit or recalibrate tails in this task. If A1 matches/exceeds qLSTM,
retain the simpler reference and pause neural-complexity claims. Tail calibration
would require a separately frozen validation-only map and locked evaluation,
not retrospective correction of the reported4.49%.
