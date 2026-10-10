# One fixed direct-contrast target test

Change only the targets of the frozen eight-feature, lambda=1, prefix-scaled
ridge recipe to cost-after standalone VOL-minus-SHORT and VOL-minus-CS
21-day marked subperiod returns. Both predictions remain signed. Positive
forecast favors VOL, negative favors the other expert, zero abstains. No grid,
threshold optimization, neural training, new data, native rollout or policy.

Each historical path preserves its original wallet start, chronology, cached
causal expert targets/eligibility, mapper/ramp/caps, funding, costs, risk
reductions and paid final flattening. No reset at rolling-window boundaries.
Full 21-active-interval labels cannot cross original gaps or paid-terminal
rows; their actual execution/outcome clocks must precede the fold strictly.
Forward primary score has 42 full windows per fold and fixed disjoint starts
0/21. Start42 has 20 active intervals plus paidclose and is reported separately.
These are inherited standalone wallet outcomes, not realizable switching
profits or fresh 21-day accounts. All four blocks are repeatedly examined
historical development evidence, not new pristine OOS. Effective N is unknown;
overlap and just two disjoint spans preclude statistical-strength claims.

MSE and sign agreement compare ridge with its causal prefix contrast mean.
Constant VOL is an action baseline: compare its decision error and sign
agreement; MSE has no meaning without an arbitrary forecast magnitude.
No magnitude is invented. Forecast calibration is descriptive only.

[Duplicate check](DUPLICATE_CHECK.json) found no matching prior direct21 probe:
the earlier relative-performance ridge used 7 days, penalty10 and other experts.
[Fixed protocol/source hashes](PROTOCOL.json) precede labels and fitting.
Six new focused tests plus thirteen reused feature/ridge/maturity tests pass.

Reproduce with installed Python3.12/NumPy2.5.3; Torch2.6 CPU is needed only for
cached-context label preparation. pytest9.1.1/Ruff0.16.9 are test dependencies.
No installation. Use the existing bounded resource launchers with checkout/src
in PYTHONPATH:

```bash
python -m modules.temporal_contrast21_probe.labels --state STATE --root CHECKOUT --destination NEW_CACHE
python -m modules.temporal_contrast21_probe.probe --cache NEW_CACHE/INPUTS.npz --metadata NEW_CACHE/PREPARED.json --destination NEW_RESULTS
```

Preparation performs 15 original standalone surrogate paths and 12 bitwise
forward parity replays. The fit interface reads the published small NumPy cache
without loading Torch, wallets, old models or native tapes. Exactly four shared
two-output closed-form fits, 18 coefficients each; stop after this specification
regardless of outcome. A positive result would require a separately frozen
shared-wallet policy and paid switching validation.

Completed exactly four fits, 18 coefficients each. Strict prefix labels
371/462/553/644 have the identical dates and bitwise identical input scaler
as the market21 probe; actual outcome clocks add 60.000001 seconds. Each
label stays inside its original wallet and excludes the paid-terminal row.
There are 673 full historical labels across the five original wallets.
All twelve forward control NAV/target paths reproduce bitwise with the frozen
mapper and charged-risk kernel; their costs and risk-event counts reconcile.
[Published small fitting inputs](INPUTS.npz), [prepared labels/path audit](PREPARED.json),
[original historical standalone paths](TRAIN_STANDALONE_PATHS.npz),
[prefix coefficients/scalers](PREFIX_SCALERS_COEFFICIENTS.npz),
[primary predictions](PREDICTIONS.csv), [separate boundary spans](TRUNCATED_SPANS.csv),
[full metrics](RESULT.json), [independent verification](VERIFICATION.json).

The source/protocol/tests were public at `3d6863e60f38a0b05cf12a3f6113418f4027a22a`
before preparation/fitting, with all ten files remotely read back. Nineteen
tests pass; all 344 forward rows, 673 training labels, coefficient normal
equations and 24 metric sets reconcile without additional fitting.
Preparation took 3.514 seconds for 27 surrogate paths;
the four closed-form fits and scores took 0.252 seconds. One CPU,
shared sampled memory 5.466 GB, swap/GPU zero.
Per-process peak is UNKNOWN: the sampling receipt does not establish it.
No downloads, neural updates, native rollout or shared-wallet policy.

## Full windows with 21 active intervals: 42 per fold

MSE skill is relative reduction in error versus the direct contrast prefix
mean. Positive means lower error. Sign agreement uses the fixed zero rule.
The old market column is the byte-preserved preceding diagnostic, compared
on identical outcomes and dates; no old forecast was recalibrated.

| Fold | Contrast | MSE skill vs mean | Ridge sign | Mean sign | Constant VOL | Old market sign |
|---|---|---:|---:|---:|---:|---:|
| 2023-07-03 | VOL−SHORT | 3.98% | 73.81% | 71.43% | 28.57% | 61.90% |
| 2023-07-03 | VOL−CS | 6.13% | 50.00% | 50.00% | 50.00% | 40.48% |
| 2023-10-02 | VOL−SHORT | 24.72% | 100.00% | 100.00% | 100.00% | 54.76% |
| 2023-10-02 | VOL−CS | 23.14% | 95.24% | 95.24% | 95.24% | 54.76% |
| 2024-01-01 | VOL−SHORT | 3.36% | 61.90% | 61.90% | 61.90% | 61.90% |
| 2024-01-01 | VOL−CS | 3.09% | 92.86% | 92.86% | 92.86% | 92.86% |
| 2024-04-01 | VOL−SHORT | 9.94% | 54.76% | 61.90% | 61.90% | 50.00% |
| 2024-04-01 | VOL−CS | -8.28% | 78.57% | 78.57% | 78.57% | 66.67% |

## Fixed full-active disjoint starts 0/21: two spans per fold

| Fold | Contrast | MSE skill vs mean | Ridge sign | Mean sign | Constant VOL |
|---|---|---:|---:|---:|---:|
| 2023-07-03 | VOL−SHORT | 2.36% | 50.00% | 50.00% | 50.00% |
| 2023-07-03 | VOL−CS | 13.08% | 50.00% | 50.00% | 50.00% |
| 2023-10-02 | VOL−SHORT | 30.06% | 100.00% | 100.00% | 100.00% |
| 2023-10-02 | VOL−CS | -14.43% | 50.00% | 50.00% | 50.00% |
| 2024-01-01 | VOL−SHORT | -82.42% | 50.00% | 50.00% | 50.00% |
| 2024-01-01 | VOL−CS | -134.02% | 100.00% | 100.00% | 100.00% |
| 2024-04-01 | VOL−SHORT | 54.92% | 0.00% | 0.00% | 0.00% |
| 2024-04-01 | VOL−CS | -14.13% | 100.00% | 100.00% | 100.00% |

## Original third span: 20 active intervals plus paid close

These are boundary records, not full21-day primary observations. Observed
and predicted spreads are percentage points. No boundary value enters fitting.

| Fold | Contrast | Observed spread | Forecast spread | Ridge sign | Mean sign | Constant VOL |
|---|---|---:|---:|---:|---:|---:|
| 2023-07-03 | VOL−SHORT | -9.413pp | +0.771pp | 0.00% | 100.00% | 0.00% |
| 2023-07-03 | VOL−CS | -4.730pp | +1.107pp | 0.00% | 0.00% | 0.00% |
| 2023-10-02 | VOL−SHORT | +0.932pp | +0.771pp | 100.00% | 100.00% | 100.00% |
| 2023-10-02 | VOL−CS | +0.289pp | +1.752pp | 100.00% | 100.00% | 100.00% |
| 2024-01-01 | VOL−SHORT | +9.601pp | +1.897pp | 100.00% | 100.00% | 100.00% |
| 2024-01-01 | VOL−CS | +8.690pp | +1.382pp | 100.00% | 100.00% | 100.00% |
| 2024-04-01 | VOL−SHORT | +5.682pp | +1.269pp | 100.00% | 100.00% | 100.00% |
| 2024-04-01 | VOL−CS | +5.046pp | +0.995pp | 100.00% | 100.00% | 100.00% |

Constant VOL has decision error = 1 − sign agreement. Its MSE is explicitly
undefined because it supplies an action, not a numerical contrast forecast.
All exact ties and zero predictions are retained/countable in RESULT.json.
Two disjoint spans per fold and serial market dependence remain far too few
for statistical-strength claims. No fold was removed or selected by outcome.

Direct targets improve sign agreement over the old market-return forecast in
six of eight primary comparisons and tie in two; squared-error skill versus
the direct prefix mean is positive in seven of eight. This is development
evidence of target alignment, not stable conditional expert selection. The
direct prefix mean already makes nearly all the same choices: the ridge gains
only 2.38 percentage points for July VOL−SHORT, loses 7.14 points for April
VOL−SHORT, and ties in the other six. All four VOL−CS sign comparisons match
the direct mean; April VOL−CS error is 8.28% worse than that mean. October/
January high agreement is also captured by constant VOL. Thus changing the
target improves alignment with expert spreads, but consistent incremental
decision benefit from the eight features is not established.

On the fixed full-active disjoint subset, all eight sign comparisons match
the direct prefix mean. Squared-error skill splits four positive and four
negative; two spans per fold cannot establish statistical strength.

STOP after this one specification. The old market/risk, selector and negative
findings are unchanged. No new threshold, grid, follow-up fit, native rollout
or shared-wallet policy was run. Standalone expert spreads cannot establish
realizable switching returns; even a positive decision diagnostic would need
a separately frozen shared-wallet policy with paid transitions.
