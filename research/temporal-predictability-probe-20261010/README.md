# Fixed next-day predictability probe

One eight-input/two-output ridge recipe, penalty1 on mean squared error,
four prescribed63-day forward blocks. Features/standardization/penalty/targets/
trailing20 baseline fixed before scoring; no feature/grid selection or retuning.
True completed-close labels only, strict prefix maturity; no synthetic paidflat
outcomes. Return is equal-weightCORE5 simple return; risk is mean squared five
asset daily returns, not intraday realized variance. Original market aggregates
retain their ten-asset semantics. No portfolio execution or profit claim.

Installed NumPy suffices; tests use pytest/Ruff. Reproduce with PYTHONPATH pointing
to checkout and src, through existing bounded resource launcher:
`python -m modules.temporal_predictability_probe.probe --state STATE --destination NEW_OUTPUT`.
Immutable output, four closed-form fits,18 coefficients per fit, no deep training.
Historical project-seen data;63 observations perblock, dependent market days.
7 label-clock/maturity/normalization/trailing/mask/ridge unit tests pass.

All four fits completed in the recorded0.252seconds launcher interval (sampling
cannot reliably measure a peak that short). Prefix475/566/657/748 true labels;
the last prestart raw next-day label is excluded, including March31→April1.
All63 forecast labels perblock exist; trailing20 fallback0, negative risk
forecast clipping0 in every block. Existing models and four policy results intact.

Skill=1−forecastMSE/baselineMSE; positive means lower squared error.

| Block | Prefix labels | Return vsmean | Return vstrailing20 | Risk vsmean | Risk vstrailing20 |
|---|---:|---:|---:|---:|---:|
| 2023-07-03 | 475 | +0.17% | +4.35% | -1.13% | +5.16% |
| 2023-10-02 | 566 | -0.07% | -3.83% | +7.92% | -0.04% |
| 2024-01-01 | 657 | +4.47% | -2.22% | +4.06% | -13.15% |
| 2024-04-01 | 748 | -0.13% | +7.99% | -6.05% | -1.66% |

Calibration uses forward outcomes descriptively, without recalibrating forecasts.
Return bias is in basispoints; risk meanratio=forecastmean/observedmean.
OLS slope regresses actual on forecast; calibration intercept/MSE/std and both
baseline calibration reports remain in RESULT.json.

| Block | Return bias bp | Return corr | Return slope | Return sign accuracy | Risk meanratio | Risk corr | Risk slope |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2023-07-03 | -2.72 | +0.039 | +1.144 | 50.8% | 0.863 | -0.108 | -2.526 |
| 2023-10-02 | -77.93 | +0.047 | +1.697 | 39.7% | 1.422 | +0.162 | +0.801 |
| 2024-01-01 | -37.83 | +0.287 | +5.159 | 58.7% | 1.677 | +0.230 | +0.953 |
| 2024-04-01 | +31.51 | +0.012 | +0.713 | 41.3% | 1.457 | -0.007 | -0.043 |

[All fixed forecasts](PREDICTIONS.csv), [all errors/calibration/baselines](RESULT.json),
[prefix scalers and18 coefficients perblock](PREFIX_SCALERS_COEFFICIENTS.npz),
[frozen protocol/source](PROTOCOL.json), [test receipt](TEST_OUTPUT.txt),
[independent CSV reconciliation](VERIFICATION.json). Four historical project-seen
63-day blocks, serial dependence and large tail events limit these descriptive
results. No pristine OOS, portfolio execution, profit or universal predictability
claim. No features/penalty/scaling changed after results.

The evidence supports episodic risk persistence, chiefly already captured by
trailing20 in October/January, and a January directional association. Neither
stable directional predictability nor incremental ridge risk skill across all
four blocks is established. Risk calibration is uneven: mean forecasts exceed
actual means by42%/68%/46% in October/January/April; July/April risk correlations
are negative/nearzero. July retains its large July13 return shock; no outlier is
deleted. January return correlation0.287 and58.7% sign accuracy are descriptive
63-day evidence and do not establish a repeatable trading edge. In the other
three blocks return correlations are0.039/0.047/0.012.

One next-step implication: use causal trailing20 as the risk-forecast benchmark
on genuinely new forward observations, checking calibration and squared-error
skill before using that signal for another expert-selection policy change.
This diagnostic does not establish absence of all possible signals.
