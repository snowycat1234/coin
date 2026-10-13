# Signed intraday persistence diagnostic: fixed recipe stopped

## Conclusion

The extra signed-serial feature did not pass the predeclared gates. This stops only this fixed recipe. No sign flip, tuning, asset exclusion, or year exclusion was performed. No strategy or net-profit claim follows from this result.

One frozen pair of per-asset ordinary least-squares models was fit on 690 common mature 2021–2022 decision dates. All full 2023, 2024, and 2025 calendars were scored once with the same model. These are previously seen development years, not fresh out-of-sample evidence.

The candidate adds one standardized signed intraday-serial interaction per asset to the fixed price/HAR/semivariance/sampling/unsigned-jump controls. It has five more fitted coefficients overall (86 versus 81), so this is a nested information comparison, not an equal-degrees-of-freedom contest.

## Annual fixed-gate results

| Year | Dates | Control normalized MSE | Candidate normalized MSE | Relative MSE gain | Joint loss-improvement 95% CI | Primary gate |
|---|---:|---:|---:|---:|---|---|
| 2023 | 365/365 | 0.433186012 | 0.432982310 | +0.047024% | [-0.001581592, +0.002040744] | FAIL |
| 2024 | 366/366 | 0.474107313 | 0.474628757 | -0.109984% | [-0.001890482, +0.000756938] | FAIL |
| 2025 | 365/365 | 0.461819405 | 0.460771411 | +0.226927% | [-0.000620886, +0.003362003] | FAIL |

Every gain is below the required 2%, and every annual loss-improvement interval crosses zero. The training-only constant-return benchmark has lower MSE than both fitted arms in every year.

## Independent price-cost roundtrip probe

Units below are basis points of unit entry notional averaged over the five assets and natural dates, including flat decisions. This is a hypothetical independent one-day roundtrip relevance check. It includes the fixed transaction-price/slippage factors and excludes funding, compounding, portfolio risk, capacity, margin, shared-wallet execution, and native account PnL. It is not paid wallet income.

| Year | Control mean (bp) | Candidate mean (bp) | Paired increment (bp) | Increment 95% CI (bp) | Price-cost gate |
|---|---:|---:|---:|---|---|
| 2023 | -28.329116 | -25.799277 | +2.529840 | [-0.485295, +6.020101] | FAIL |
| 2024 | -4.934916 | -5.689281 | -0.754365 | [-6.704434, +4.302437] | FAIL |
| 2025 | -12.579004 | -6.086454 | +6.492550 | [+1.414998, +12.393459] | FAIL |

The positive 2025 paired increment is retained: +6.492550 bp, 95% CI [+1.414998, +12.393459] bp. The candidate’s absolute 2025 mean remains −6.086454 bp. Therefore it does not rescue the candidate’s failed information, absolute price-cost, or direction gates.

## Frozen added-feature coefficients

These coefficients multiply train-standardized features and predict raw simple returns; they are not normalized by label standard deviation. All five are negative, so the predeclared positive-mean mechanism-direction gate fails.

| Asset | Extra-feature coefficient |
|---|---:|
| BTCUSDT | -0.000876826915 |
| ETHUSDT | -0.000403738097 |
| SOLUSDT | -0.001021270861 |
| XRPUSDT | -0.000685606075 |
| DOGEUSDT | -0.006959922654 |

Mean: -0.001989472921. No after-result sign flip.

## 2023: full per-asset and half-year evidence

| Asset | Mean normalized loss improvement | Control probe mean (bp) | Candidate probe mean (bp) | Probe increment (bp) |
|---|---:|---:|---:|---:|
| BTCUSDT | +0.000079884 | -42.113831 | -40.276929 | +1.836902 |
| ETHUSDT | -0.000663354 | -33.635577 | -33.777360 | -0.141783 |
| SOLUSDT | +0.000787721 | -33.906751 | -29.196235 | +4.710516 |
| XRPUSDT | +0.002912041 | -24.612836 | -22.430534 | +2.182303 |
| DOGEUSDT | -0.002097782 | -7.376586 | -3.315325 | +4.061261 |

| Half-year | Joint loss improvement | Control probe mean (bp) | Candidate probe mean (bp) | Probe increment (bp) |
|---|---:|---:|---:|---:|
| H1 | -0.000043100 | -19.997328 | -18.160336 | +1.836992 |
| H2 | +0.000446480 | -36.525060 | -33.313669 | +3.211391 |

| Arm | Short decisions | Flat decisions | Long decisions |
|---|---:|---:|---:|
| CONTROL | 940 | 395 | 490 |
| CANDIDATE | 921 | 403 | 501 |

Training-only constant-return forecast normalized MSE: 0.386441236.

## 2024: full per-asset and half-year evidence

| Asset | Mean normalized loss improvement | Control probe mean (bp) | Candidate probe mean (bp) | Probe increment (bp) |
|---|---:|---:|---:|---:|
| BTCUSDT | -0.000515684 | -31.466100 | -29.632332 | +1.833768 |
| ETHUSDT | -0.001000533 | -15.713634 | -12.643241 | +3.070393 |
| SOLUSDT | +0.000302458 | -15.871156 | -12.014768 | +3.856388 |
| XRPUSDT | +0.000842155 | +14.338976 | +13.296045 | -1.042931 |
| DOGEUSDT | -0.002235617 | +24.037334 | +12.547891 | -11.489443 |

| Half-year | Joint loss improvement | Control probe mean (bp) | Candidate probe mean (bp) | Probe increment (bp) |
|---|---:|---:|---:|---:|
| H1 | -0.000803237 | -9.693976 | -12.970887 | -3.276911 |
| H2 | -0.000242714 | -0.227585 | +1.513177 | +1.740761 |

| Arm | Short decisions | Flat decisions | Long decisions |
|---|---:|---:|---:|
| CONTROL | 815 | 491 | 524 |
| CANDIDATE | 808 | 488 | 534 |

Training-only constant-return forecast normalized MSE: 0.459358452.

## 2025: full per-asset and half-year evidence

| Asset | Mean normalized loss improvement | Control probe mean (bp) | Candidate probe mean (bp) | Probe increment (bp) |
|---|---:|---:|---:|---:|
| BTCUSDT | +0.000688496 | -16.964874 | -15.862569 | +1.102305 |
| ETHUSDT | -0.000001093 | -0.181899 | +2.262906 | +2.444805 |
| SOLUSDT | +0.000411102 | -9.853537 | -7.537042 | +2.316495 |
| XRPUSDT | +0.001139782 | -12.479197 | -14.888652 | -2.409455 |
| DOGEUSDT | +0.003001684 | -23.415514 | +5.593085 | +29.008600 |

| Half-year | Joint loss improvement | Control probe mean (bp) | Candidate probe mean (bp) | Probe increment (bp) |
|---|---:|---:|---:|---:|
| H1 | +0.002429061 | -9.334143 | +1.694126 | +11.028269 |
| H2 | -0.000310555 | -15.770960 | -13.740177 | +2.030783 |

| Arm | Short decisions | Flat decisions | Long decisions |
|---|---:|---:|---:|
| CONTROL | 819 | 521 | 485 |
| CANDIDATE | 811 | 516 | 498 |

Training-only constant-return forecast normalized MSE: 0.439615503.

## Provenance and execution receipts

Scientific freeze SHA256: bd6d3ba9756212288ebc28141242eccd87a3165853b9506394949901b772a0c7
Model SHA256: 31e61c6beea5b19e0fe8ecedec8db0a990c8f44464d33bb3e59e12eac04c91d8
Preparation SHA256: 39067ed5c28908783157615cb76f4e3343c6b96f1959cc0c316e5623a85ea2b3

The model hash was recorded before any annual score. Source-only preparation was reused without repetition. The original README is frozen pre-run documentation; this report is the completed-run status. SOURCE_REFERENCES.json pins the previously public source packet and source certifications; raw market archives are not included. PREPARED_001 contains only the derived diagnostic features/labels required for fit/score reproduction.

Nine frozen synthetic tests passed before historical fits. Independent checks of the saved model predictions, losses, price-cost arrays, natural dates, deterministic 14-day/1000-draw joint-asset bootstrap, and gates accepted the stopped result without a refit or score-entrypoint repeat.

| Phase | Wall seconds | CPU seconds | Sampled self RSS (MB) | Kernel self peak (MB) |
|---|---:|---:|---:|---:|
| FIT | 0.129609 | 0.129355 | 31.646 | 31.465 |
| SCORE | 0.304550 | 0.304552 | 44.556 | 47.423 |

Same-process runpy used one CPU/BLAS thread, 4 GB address-space cap, 2 GB active sampled-RSS stop, 8 GB host-used-memory stop, no swap/GPU, 15 GiB disk reserve, CPU soft/hard 59/60 seconds, and separate 60-second wall-watchdog enforcement for each phase. Both inner and outer receipts passed. The legacy outer descendant-RSS field is not the memory authority; active self RSS and Linux RUSAGE_SELF kernel peak are. The 80 MB synthetic allocation probe verifies that the capsule samples its own allocations.

## Reproduce fit/score from derived inputs

Run from this module directory on Linux with Python 3.12 and NumPy. At least 15 GiB free disk is required by the frozen resource budget. Do not overwrite any existing outputs. The following creates new reproduction paths and does not redo source preparation:

    python outer_wall_watchdog.py --report REPRO_FIT_OUTER.json --seconds 60 -- python same_process_capsule.py --report REPRO_FIT_RESOURCE.json --seconds 60 run.py fit --prepared PREPARED_001 --output REPRO_FIT

Hash REPRO_FIT/MODEL.json and freeze that exact SHA before scoring. Then substitute the exact returned hash below:

    python outer_wall_watchdog.py --report REPRO_SCORE_OUTER.json --seconds 60 -- python same_process_capsule.py --report REPRO_SCORE_RESOURCE.json --seconds 60 run.py score --prepared PREPARED_001 --model REPRO_FIT/MODEL.json --model-sha256 EXACT_FROZEN_HASH --output REPRO_SCORES

The historical execution above was not repeated for this report. No wallet, new source/provider search, credential access, or trading action is part of the diagnostic.
