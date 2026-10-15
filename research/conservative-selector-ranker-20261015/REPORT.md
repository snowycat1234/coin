# Conservative linear ranking replacement: one frozen experiment

## Result
The challenger modestly improved the saved STATE_ONLY Ridge decision diagnostic, but remained worse than the zero-utility CASH/train-best action. It does not establish a useful deployable replacement.

Across the same 22 preselected, nonoverlapping, repeatedly seen 2024H1 development blocks:

| Diagnostic | New ordinal ranker | Saved STATE_ONLY Ridge | CASH/train-best |
|---|---:|---:|---:|
| Mean chosen reference utility | -0.000891148823 | -0.002061852500 | 0 |
| Mean oracle regret | 0.012099219094 | 0.013269922771 | 0.011208070271 |
| Pooled pairwise accuracy | 63.8095% | 62.5397% | Not a ranking forecast |

Mean paired chosen-utility difference: +0.001170703678. Challenger better on 8 blocks, worse on 8, tied on 6; choices differ on 16. Pairwise accuracy uses 315 eligible unequal-utility comparisons, not 315 independent samples. The evaluation has only 22 date blocks.

The aggregate improvement is fragile descriptively: the single largest favorable difference, April 30 (+0.0406943), exceeds the sum of all 22 paired differences (+0.0257555). This is a transparent description, not a new exclusion rule or an alternative selected evaluation. The complete frozen set remains the reported result.

CASH remained best on average at exactly zero. The unattainable ex-post best expert had mean utility 0.011208070271. It is an opportunity ceiling, not an executable strategy. Utilities are log(1 + seven-day net reference return) minus 0.5 times reference daily maximum drawdown; they are not portfolio returns.

## Fit and source gates
Actual fit start: 2026-10-15T01:49:54.817221+00:00. Optimizer success: True; 10 iterations and 12 objective/gradient evaluations. Gradient infinity norm 2.25224378045e-08 satisfies the fixed 1e-6 gate. Total loss 0.670401062899 = data loss 0.652488733612 + penalty 0.017912329287.

One actual fit, exact zero initialization, SciPy L-BFGS-B, analytic gradient, no bounds, maxiter 500, maxls 40, ftol 1e-12, gtol 1e-8; lambda 1.0 including all intercepts. A single CPU affinity and one BLAS/OpenMP thread were enforced. No sweep, fallback, restart, old-baseline refit or learned-expert refit occurred.
The original stage ended after 0.056111 seconds with a reporting-only NumPy-integer serialization error after convergence and coefficient saving. The original receipt remains unchanged. Saved-coefficient reporting recovered at 2026-10-15T01:50:13.115206+00:00; elapsed from original start 18.297942 seconds, within the 120-second cap. No coefficients were changed. All failures are recorded.

Fourteen synthetic tests ran before actual fitting: analytic gradient finite differences, pair masks, exact ties, equal-date weighting, zero-pair date weight, all-tied dates, CASH anchor, penalized intercepts, train-only scaler, causal clocks, synthetic optimizer determinism, numerical stability, argmax ties and manual loss. A serialization regression test was added after the reporting failure; all 15 final tests pass.

The exact local approved-source identities were checked against the existing manifest. All original 40 dates have labels strictly mature before 2023-12-25 UTC and nonoverlapping intervals; all 182 original scoring dates are retained. The same 176 mature evaluation rows and 22 preselected blocks are used. Six final dates have states/scores retained but no outcome labels exported or evaluated because they did not mature by the frozen endpoint.

The original 60 state-only features use 30 consecutive strictly past feedback observations and causally available current targets. All 222 train/scoring learned-expert provenance-clock checks passed. Original feature order, expert eligibility, utility reconstruction, label latency and saved forecast identity were checked. The train-only population-standard-deviation transform matches original StandardScaler semantics on this support, including 10 zero-variance CASH columns mapped to zero. No model was unpickled.

The saved 2024-01-01 fit availability is a simulated historical causal cutoff. This new fit happened in 2026 and was not issued in 2024. Saved arrays lack independent row-level forecast-publication receipts; historical live issuance is not certified.

## Training fit, separate from evaluation
Forty independent training dates produce 583 unequal eligible pairs. Pooled training pairwise accuracy is 68.7822%; equal-date mean accuracy is 68.8036%. Pair counts do not multiply independent support. Date loss is the mean of its unequal-pair logistic losses; every date receives exactly 1/40 weight, including zero-pair dates.

## Limitations and interpretation
There are 305 free coefficients for only 40 independent dates. The fixed strong quadratic penalty (including intercepts) gives a unique strongly convex optimization problem, but does not fix limited evidence or repeated-development selection. The loss normalization, regularization and intercept treatment differ from Ridge alpha 30: this is a conservative replacement comparison, not pure causal attribution to ranking loss. Lambda 1 is not asserted equivalent to Ridge alpha 30.

Scores are ordinal, not predicted utilities. There is no utility-MSE comparison, old-temperature softmax, wallet target generation, annualization, significance claim, portfolio-return claim or live-performance claim. No holdout was opened and no live trade was placed. Even a stronger improvement would require a separately approved past-only validation design before considering deployment. No new experiment or tuning was run after observing this result.

## Choice mix
- challenger: CSMOM21 5, VOL_MANAGED_HOLD 2, DONCHIAN_EXIT10 4, PRICE_ONLY_PATCH_CAUSAL_RANK 8, PUBLIC_SMA50_200_SIGNED 2, CASH 1
- state: CASH 5, VOL_MANAGED_HOLD 5, PUBLIC_SMA50_200_SIGNED 1, CSMOM21 7, PRICE_ONLY_PATCH_CAUSAL_RANK 4
- cash_train_best: CASH 22

## All frozen evaluation blocks

| Date | New choice | New utility | Saved Ridge choice | Ridge utility | New minus Ridge | Oracle |
|---|---|---:|---|---:|---:|---:|
| 2024-01-01 | CSMOM21 | 0.0048633909 | CASH | 0.0000000000 | +0.0048633909 | 0.0054888432 |
| 2024-01-09 | VOL_MANAGED_HOLD | -0.0079622045 | VOL_MANAGED_HOLD | -0.0079622045 | +0.0000000000 | 0.0069218027 |
| 2024-01-17 | CSMOM21 | -0.0137441536 | CASH | 0.0000000000 | -0.0137441536 | 0.0043141826 |
| 2024-01-25 | DONCHIAN_EXIT10 | 0.0000000000 | PUBLIC_SMA50_200_SIGNED | 0.0020975578 | -0.0020975578 | 0.0020975578 |
| 2024-02-02 | DONCHIAN_EXIT10 | 0.0021850247 | VOL_MANAGED_HOLD | 0.0041822551 | -0.0019972304 | 0.0051197438 |
| 2024-02-10 | VOL_MANAGED_HOLD | 0.0167768282 | VOL_MANAGED_HOLD | 0.0167768282 | +0.0000000000 | 0.0167768282 |
| 2024-02-18 | CSMOM21 | 0.0014198799 | CASH | 0.0000000000 | +0.0014198799 | 0.0205839639 |
| 2024-02-26 | CSMOM21 | -0.0259557835 | CSMOM21 | -0.0259557835 | +0.0000000000 | 0.0696857849 |
| 2024-03-05 | PRICE_ONLY_PATCH_CAUSAL_RANK | -0.0037777935 | CSMOM21 | -0.0164008763 | +0.0126230828 | 0.0017599382 |
| 2024-03-13 | CSMOM21 | -0.0515765751 | CSMOM21 | -0.0515765751 | +0.0000000000 | 0.0000000000 |
| 2024-03-21 | PUBLIC_SMA50_200_SIGNED | 0.0022458237 | CSMOM21 | 0.0085796276 | -0.0063338039 | 0.0085796276 |
| 2024-03-29 | PRICE_ONLY_PATCH_CAUSAL_RANK | 0.0056941599 | CSMOM21 | -0.0170142461 | +0.0227084060 | 0.0056941599 |
| 2024-04-06 | CASH | 0.0000000000 | CSMOM21 | 0.0088232942 | -0.0088232942 | 0.0088232942 |
| 2024-04-14 | PRICE_ONLY_PATCH_CAUSAL_RANK | -0.0115130124 | VOL_MANAGED_HOLD | 0.0041522285 | -0.0156652410 | 0.0041522285 |
| 2024-04-22 | PRICE_ONLY_PATCH_CAUSAL_RANK | 0.0138189700 | PRICE_ONLY_PATCH_CAUSAL_RANK | 0.0138189700 | +0.0000000000 | 0.0138189700 |
| 2024-04-30 | DONCHIAN_EXIT10 | 0.0000000000 | PRICE_ONLY_PATCH_CAUSAL_RANK | -0.0406942988 | +0.0406942988 | 0.0037256711 |
| 2024-05-08 | PUBLIC_SMA50_200_SIGNED | -0.0074935080 | PRICE_ONLY_PATCH_CAUSAL_RANK | 0.0068766886 | -0.0143701965 | 0.0068766886 |
| 2024-05-16 | DONCHIAN_EXIT10 | 0.0117316975 | VOL_MANAGED_HOLD | 0.0153378834 | -0.0036061859 | 0.0184762789 |
| 2024-05-24 | PRICE_ONLY_PATCH_CAUSAL_RANK | 0.0009071987 | CASH | 0.0000000000 | +0.0009071987 | 0.0009071987 |
| 2024-06-01 | PRICE_ONLY_PATCH_CAUSAL_RANK | 0.0016973251 | CASH | 0.0000000000 | +0.0016973251 | 0.0016973251 |
| 2024-06-09 | PRICE_ONLY_PATCH_CAUSAL_RANK | 0.0096070017 | CSMOM21 | 0.0021274399 | +0.0074795619 | 0.0096070017 |
| 2024-06-17 | PRICE_ONLY_PATCH_CAUSAL_RANK | 0.0314704562 | PRICE_ONLY_PATCH_CAUSAL_RANK | 0.0314704562 | +0.0000000000 | 0.0314704562 |

Full six-expert utility vectors, saved forecasts, new ordinal scores, pairwise counts and all 176 mature rows are in RESULTS.json. This packet is local and unpublished.
