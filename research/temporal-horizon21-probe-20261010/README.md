# One fixed21-day horizon probe

Same8 canonical aggregates, prefix-only scaling, ridgeλ1 and four fixed blocks
as the [preserved next-day probe](../temporal-predictability-probe-20261010/README.md).
No horizon grid/feature selection/retuning/policy execution or new data.

Return: mean overCORE5 of close[t+21]/close[t]−1; risk: average over21 days of
mean five squared daily simple asset returns, not strategy PnL or intradayRV.
All22 real closes must be observed; training stays inside one original wallet,
full outcome strictlybeforefoldstart.63 outcome days perblock permit43 starts;
fixed disjoint starts0/21/42 cover those63 days. Overlapping windows are not43
independent observations; even three disjoint spans need not be independent.
The final endpoint may equal blockexclusiveend, but no outcome day is outside.

Baselines are prefix targetmean and latest20 fullymatured21-day targets.
Trailing history must be whollywithin an original wallet or currentforwardblock;
missing eligible history fallsback to prefixmean and is reported. Forecast risk
is clippedat0 using the unchanged rule.6 maturity/clock/gap/target/baseline tests
pass. Four closedform8x2 fits,18 coefficients perfit; NumPy/pytest/Ruff only.

Reproduce through existing bounded guard, with checkout/src in PYTHONPATH:
`python -m modules.temporal_horizon21_probe.probe --state STATE --destination NEW_OUTPUT`.
Protocol/source hashes are publicbeforefit. No continuation after this fixedrun.

Completed four fixed fits. Positive squared-error skill means lowerMSE than the
specified baseline. Prefix labels below are overlapping / greedily disjoint
original-wallet coverage; neither count is a statistical effectiveN.

| Block | Prefix overlap/disjoint | Return vsmean | Return vstrailing | Risk vsmean | Risk vstrailing |
|---|---:|---:|---:|---:|---:|
| 2023-07-03 | 371 / 20 | +4.22% | +71.78% | +3.53% | +66.28% |
| 2023-10-02 | 462 / 24 | +9.13% | -13.89% | -62.85% | +18.95% |
| 2024-01-01 | 553 / 28 | +6.54% | +51.78% | +5.21% | -259.97% |
| 2024-04-01 | 644 / 33 | +16.90% | +72.47% | +36.14% | +82.51% |

Prespecified disjoint starts0/21/42 only: three spans perblock. Extremely small
sample; all cases retained, no inference/selection based on this subsample.

| Block | Return vsmean | Return vstrailing | Risk vsmean | Risk vstrailing |
|---|---:|---:|---:|---:|
| 2023-07-03 | -21.40% | +51.31% | +14.72% | +59.31% |
| 2023-10-02 | +5.62% | +17.33% | -123.91% | -248.34% |
| 2024-01-01 | +11.15% | +41.27% | -1.94% | -123.46% |
| 2024-04-01 | +20.17% | +76.40% | +22.17% | +73.23% |

Calibration on overlapping forecasts is descriptive, never applied to predictions.
Return bias in percentagepoints; risk ratio forecastmean/observedmean. Full
intercepts/std/MSE and calibration of both baselines and disjoint samples saved.

| Block | Return bias | Return corr | Return slope | Risk meanratio | Risk corr | Risk slope |
|---|---:|---:|---:|---:|---:|---:|
| 2023-07-03 | +1.57pp | +0.124 | +0.728 | 1.222 | +0.433 | +5.190 |
| 2023-10-02 | -22.22pp | +0.636 | +5.385 | 1.550 | +0.585 | +1.298 |
| 2024-01-01 | -5.28pp | +0.356 | +7.205 | 2.396 | +0.695 | +2.793 |
| 2024-04-01 | +1.73pp | +0.583 | +5.196 | 1.255 | +0.261 | +0.525 |

[Full metrics](RESULT.json), [every prediction](PREDICTIONS.csv),
[prefix scalers/coefficients](PREFIX_SCALERS_COEFFICIENTS.npz), [verification](VERIFICATION.json).
The [next-day findings](../temporal-predictability-probe-20261010/README.md) remain
byte-identical. Historical project-seen research; overlapping label windows,
serial market dependence and twelve disjoint spans preclude claims of statistical
strength, pristine OOS, portfolio profits or universality. No continuation,
hyperparameter/horizon grid, feature selection, downloads or existingmodel edits.

Horizon mismatch is plausible: overlapping21-day return forecasts improve on
prefixmean in allfour blocks and matured-target trailing in three; nextday
return improvements were small/episodic. The fixeddisjoint view retains July
return failure againstmean, with improvement in the otherthree. This is a
preliminary multiweek directional association, not evidence of stable trading
profit or statistical strength from172 overlapping starts. Return calibration
is poor (Octoberbias−22.22pp, slopes5.39/7.21/5.20 in the lastthree blocks).
Risk forecast skill is mixed and mean levels overstated, especiallyJanuary
ratio2.396; positive overlapping correlation does not establish useful calibration.

One next-step implication: carry the frozen21-day return forecast into a new
chronological validation with preregistered error/calibration criteria before
changing any trading selector. This run is complete; no retuning/continuation.
