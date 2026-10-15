# Saved four-cell causal monitor review

PASS: all four saved terminals reconcile exactly under frozen native40 event arithmetic. Root confirmed session71296 exited0 at2026-10-15T11:00:03UTC. No accounts or financial runs were created by the reviewer.

All values below are adaptive, seen2023/2024 development comparisons. The original D controls were reused.

| Cell | Return control → monitor | Full-native MDD control → monitor | Realized daily volatility control → monitor | Frozen forecast breach minutes control → monitor |
|---|---:|---:|---:|---:|
| 2023_STATIC50_MID | 24.0536% → 18.1449% | 6.4342% → 4.2957% | 9.5888% → 7.9017% | 68,425 → 2,723 |
| 2023_VOL_MANAGED_HOLD_MID | 24.5047% → 23.9291% | 7.6587% → 7.4940% | 11.1725% → 10.7117% | 245,098 → 169 |
| 2024_STATIC50_MID | 16.2540% → 11.2017% | 5.8912% → 9.9087% | 8.6894% → 8.3128% | 91,872 → 43 |
| 2024_VOL_MANAGED_HOLD_MID | 24.6802% → 22.3303% | 8.0001% → 6.6307% | 11.1768% → 9.4878% | 252,443 → 92 |

## Findings

- All four returns are lower and fees higher. 2024 STATIC50 has worse full-native MDD,5.8912%→9.9087%, despite fewer forecast-limit exceedances. The other three MDDs fall. This does not establish performance superiority.
- 209cohorts produce762actual paid forecast-fill rows.101individual fills increase contemporaneous marked variance, all in the two STATIC50 hedge cases. All admitted completed target projections strictly lower the original bound variance; sequential paid fills are not atomic. Some cohorts are superseded by genuine strategy decisions before completion.
- Forecast exceedance frequency and integrated excess fall sharply. Continuous10% forecast-limit compliance is not achieved.2023 HOLD realized daily-return volatility remains10.7117%, and its forecast maximum is24.2677%.
- Daily covariance changes create brief large excesses. At the2023 HOLD peak, identical held weights imply about9.4604% under the previous daily covariance versus24.2677% under the newly available covariance. Native latency and paid strategy/forecast fills are preserved in the separate trace.
- Exact D trades, funding, fill-request identities, native financial ledger, and all37minute columns match through the first legitimate monitor cohort:11,518 /4,320 /14,303 /14,302minutes respectively.
- All four finish full-calendar, actually paid market-flat. Transfers, conditional settlements, conditional insurance support, and genuine unpaid debt are zero. The2024 STATIC50 monitor has4Guard50paid warning exits versus3in its control; all finish at the first native eligible open,60,000,001microseconds after the original warning signal.
- No historical five-open forecast renewal or late native-hardcap handback occurs here. Their boundary behavior is supported by the frozen generated tests, not these historical observations.
- All255bound source/code/preparation/control files remain byte-identical. The controller shows maximum2workers on separateCPUs2/3, confined helper affinities, and peak aggregate workerRSS1,160,962,048bytes. Host quotas remain unverified.

## Arithmetic and reporting scope

The pure saved proof checks23,418chronological native40financial-ledger events over2,105,280case-minutes. Raw100stored-delta residuals are retained:BTC+3E−38in2023 STATIC50 andDOGE−5E−38in2024 HOLD; other terminal residuals are zero. Native40secondary PnL bridge residuals are separately retained. No financial epsilon, zeroing, cashflow repair, or rerun was used.

The frozen annual risk report indexes covariance at close_us−1. The new monitor evaluates after the completed close/full funding and same-clock daily binding. The additive report keeps both phase definitions. In the frozen report, strict and original1e−10 exceedance counts coincide in these four cases. Larger pre-existing per-cell strict counts use the post-same-clock-decision covariance; their difference is a phase difference, not merely a tolerance difference.2023 STATIC50 maximum is12.6890% in the frozen report and12.7539% in the post-binding view.

Daily-close and minute-close MDD, integrated sigma/variance excess, and all Guard50paid-exit witnesses are saved in ADDITIVE_SAVED_RISK_PHASE_MDD_AND_PAID_D_EXIT_SCOPE.json. Full-native MDD remains the primary drawdown scope.

No exact realized-risk match, OOS validation, continuous risk cap, native exchange execution, or funding-publication certification is claimed.
