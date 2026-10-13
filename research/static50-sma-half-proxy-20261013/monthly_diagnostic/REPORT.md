# CS+HOLD versus SMA200: saved-trace monthly diagnostic

This is a descriptive decomposition of the existing full-year 2023 and 2025 same-horizon daily-quantity-proxy wallets. It reads the four frozen original row traces and RESULTS.json, verifies the trace SHA-256 hashes, and does not rerun targets, wallet economics or random inference. The script writes only to this directory.

Each 24-hour held interval is assigned to the UTC month of its decision/start timestamp. A month return is its last saved daily NAV after divided by its first saved daily NAV before, minus one. December includes the saved paid exit at the next January 1 boundary. These are adjacent portions of ongoing annual wallets, not independent monthly start/stop backtests.

| Month (UTC decision) | CS+HOLD | SMA200 | SMA−CS+HOLD | Both lost? |
|---|---:|---:|---:|:---:|
| 2023-01 | +3.764% | -5.977% | -9.741 pp |  |
| 2023-02 | -1.846% | -3.295% | -1.449 pp | Yes |
| 2023-03 | +5.960% | +1.120% | -4.840 pp |  |
| 2023-04 | -2.507% | -4.204% | -1.697 pp | Yes |
| 2023-05 | -1.298% | +0.817% | +2.115 pp |  |
| 2023-06 | -1.354% | -0.014% | +1.340 pp | Yes |
| 2023-07 | -0.820% | +3.221% | +4.041 pp |  |
| 2023-08 | -3.843% | -6.026% | -2.184 pp | Yes |
| 2023-09 | -0.638% | -2.134% | -1.496 pp | Yes |
| 2023-10 | +7.161% | +2.853% | -4.307 pp |  |
| 2023-11 | +3.244% | +4.186% | +0.942 pp |  |
| 2023-12 | +4.294% | +2.955% | -1.338 pp |  |
| 2025-01 | +1.273% | +2.349% | +1.076 pp |  |
| 2025-02 | -2.586% | -3.631% | -1.045 pp | Yes |
| 2025-03 | +2.800% | +2.129% | -0.671 pp |  |
| 2025-04 | +3.154% | -1.554% | -4.707 pp |  |
| 2025-05 | +0.644% | -4.654% | -5.298 pp |  |
| 2025-06 | +1.934% | +0.915% | -1.019 pp |  |
| 2025-07 | +6.763% | +2.113% | -4.650 pp |  |
| 2025-08 | +4.107% | -0.201% | -4.308 pp |  |
| 2025-09 | -0.045% | -0.135% | -0.090 pp | Yes |
| 2025-10 | -2.391% | -4.453% | -2.062 pp | Yes |
| 2025-11 | -1.099% | +1.312% | +2.412 pp |  |
| 2025-12 | +1.424% | +1.475% | +0.052 pp |  |

Both negative: 8 of 24 months (2023-02, 2023-04, 2023-06, 2023-08, 2023-09, 2025-02, 2025-09, 2025-10).
Largest observed SMA lead: 2023-07, +4.041 percentage points. This is an after-the-fact maximum, not a prespecified hypothesis or a statistically significant result.

No verified complete calendar year in this saved same-horizon comparison shows SMA outperforming CS+HOLD or both strategies losing. A separate 2024 SMA-versus-plain-CS observation must not be described as SMA-versus-CS+HOLD; full-year 2024 CS+HOLD comparison is unavailable here. No 2021/2022 full-year comparison or protected 2026 holdout was used.

Source: https://github.com/snowycat1234/coin/blob/b9b31228143530e6904b08e9937525b36663e309/research/static50-sma-half-proxy-20261013/REPORT.md
The exact source trace SHA-256 values are in MONTHLY_RESULTS.json. This diagnostic introduces no selection rule or future trading recommendation.
