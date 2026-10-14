# GRID marginal consistency: saved 2023 and 2025 paired paths

## Finding

The unchanged GRID replacement adds a small, mixed marginal contribution to the matched CASH portfolio. It does not show a reliably positive improvement across the two observed development years. In both years, 7 of 12 months are positive, but positive increment days are roughly half the year. The 2023 gain is concentrated partly in October and stays positive after removing that month's dollar contribution. The 2025 marginal result is negative despite a majority of positive months.

This does **not** prove that the difference is statistical noise, nor establish a future expected edge. These two selected, already-seen paths do not provide an independent sampling design. No confidence interval or profitability gating rule is inferred.

| Metric | 2023 | 2025 |
|---|---:|---:|
| Annual GRID minus CASH | +44.4687 USDT | -35.3650 USDT |
| Difference relative to common 10,000 USDT starting balance | +0.4447 percentage points | -0.3537 percentage points |
| Positive / negative / zero months | 7 / 5 / 0 | 7 / 5 / 0 |
| Positive / negative / exact-zero increment days | 177 / 188 / 0 | 182 / 183 / 0 |
| Positive-day fraction, including zeros | 48.49% | 49.86% |
| Lag-zero correlation of daily portfolio simple returns | 0.999402 | 0.999085 |
| Worst drawdown of cumulative paired difference | 34.1956 USDT | 79.3960 USDT |
| Best month's contribution | October: +27.5089 USDT | July: +14.0931 USDT |
| Annual contribution with best month mechanically removed | +16.9598 USDT | -49.4581 USDT |

October contributes 61.86% of the net 2023 increment. Removing it reduces, but does not reverse, the annual sign. Removing July's positive 2025 increment deepens the annual shortfall. These are dollar-contribution subtractions, **not** newly simulated wallets or suggestions to switch GRID on/off in particular months.

The very high correlation is consistent with the large shared base portfolio. It does not by itself establish or refute incremental alpha, and it is not evidence of a new independent return source.

## Every calendar month

Dollar change in the GRID-minus-CASH NAV gap during the month; positive favors GRID. Rows exhaust the full calendar and sum to the annual differences.

| Month | 2023 increment (USDT) | 2025 increment (USDT) |
|---|---:|---:|
| 01 | +14.3449 | +6.4115 |
| 02 | -3.0378 | -17.1295 |
| 03 | +10.8465 | +6.5817 |
| 04 | -0.2137 | +13.9874 |
| 05 | -8.9612 | +4.0761 |
| 06 | +2.0319 | -10.9171 |
| 07 | -4.0548 | +14.0931 |
| 08 | -2.8024 | -5.0979 |
| 09 | +3.8675 | +0.2874 |
| 10 | +27.5089 | -27.3877 |
| 11 | +3.3277 | -34.0842 |
| 12 | +1.6113 | +13.8142 |

## Cumulative difference and drawdown

Let D(t) = GRID NAV(t) - CASH NAV(t), starting at D(0) = 0. The daily increment is D(t) - D(t-1), and the drawdown is the largest running peak of D minus a later D. It is measured in USDT. A zero-capital difference series has no meaningful percentage-return denominator.

- 2023 minimum difference: -10.0001 USDT on March 10; maximum: +47.8141 on December 27. Worst difference drawdown: 34.1956, from +24.1954 on February 18 to -10.0001 on March 10. Final difference: +44.4687.
- 2025 minimum difference: -55.9140 USDT on November 25; maximum: +23.4820 on August 13. Worst difference drawdown: 79.3960, from +23.4820 on August 13 to -55.9140 on November 25. Final difference: -35.3650.

Dates label the UTC calendar day's closing NAV. The initial zero is included when finding peaks, minima and maxima; first dates break ties. Daily sampling does not measure intraday spread-path extremes.

## What is and is not matched

CASH is the matched portfolio whose BTC allocation is held in cash; its other allocations remain active. It is not an all-cash wallet and is not the original CSH strategy. Each arm starts at 10,000 USDT and covers January 1 through December 31, with 365 complete days and 525,600 minutes.

The [prior saved economic assessment](https://github.com/snowycat1234/coin/blob/9ccbd6df6507eea7c97fb54d710dba2f4c1291a0/research/grid-original-2023-2025-economic-assessment-20261014/REPORT.md) establishes the fixed recipe, common period, BASE27 cost model and configured risk-budget comparison. It already reports the annual net deltas, economic decomposition and risk observations; the new contribution here is the paired daily/monthly consistency and marginal-path sensitivity.

Same configured budget is not same actual risk. The prior assessment reports mean gross exposure increasing from 37.6134% to 38.2448% in 2023 and from 43.8635% to 44.5108% in 2025. Retained summary fields independently confirm higher maximum gross exposure and higher observed portfolio drawdown in GRID in both years. Different exposure, turnover, funding, shared-wallet admission effects and rebalance/NAV path interactions can contribute to the whole-wallet difference. The paired delta is not necessarily isolated grid-owner PnL or causal standalone grid alpha.

For Bybit-inspired research, this is mixed evidence for this particular fixed recipe. It does not support claiming strict same-risk dominance, portable live APR, or a stable cost-adjusted GRID edge. Nor does it rule out every other grid design. Funding-unit and instrument-filter limitations of the saved model results remain; this diagnostic does not resolve them. No thresholds, monthly switches or candidate parameters were tuned on these outcomes.

## Reproduction and precision

The calculation plan was recorded before daily values were read. The public DAILY files contain net increments, so each NAV is reconstructed from 10,000 plus cumulative daily increments. The script parses their original JSON number text with Decimal. This preserves published precision; it does not recreate unreported native engine precision.

- All four DAILY files match their immutable public Git blob hashes and recorded SHA-256 hashes.
- The packet retains only an allowlisted ordinary financial extract of each SUMMARY; the original source is referenced by public URL and Git blob hash.
- Monthly sums equal daily sums and the reconstructed final gap exactly at the published decimal precision.
- Maximum absolute reconstructed-terminal-versus-native-summary residual is below 0.00000000000009 USDT, far below the fixed 0.00000001 USDT check tolerance and one cent.
- Nine bounded offline tests pass. A separate checker uses independently implemented arithmetic rather than importing the main analysis; see INDEPENDENT_CHECK.json.

No new market data, strategy engine, training, additional evaluation period, trading, account access or source-system execution was used. This packet contains new descriptive analysis and the four existing public daily financial outputs.

## Immutable input references

- 2023 CASH: [DAILY](https://github.com/snowycat1234/coin/blob/a801d2c1f413b8cc9c975616391c07611a61dfe7/research/grid-original-wallet-2023-cash-optimized-result-20261014/results_attempt001/final_evidence/DAILY.json); [SUMMARY](https://github.com/snowycat1234/coin/blob/a801d2c1f413b8cc9c975616391c07611a61dfe7/research/grid-original-wallet-2023-cash-optimized-result-20261014/results_attempt001/final_evidence/SUMMARY.json)
- 2023 GRID: [DAILY](https://github.com/snowycat1234/coin/blob/65cf1daa49cdd8dbec45c069c6856f24b6d2d7f2/research/grid-original-wallet-2023-grid-optimized-result-20261014/results_attempt001/final_evidence/DAILY.json); [SUMMARY](https://github.com/snowycat1234/coin/blob/65cf1daa49cdd8dbec45c069c6856f24b6d2d7f2/research/grid-original-wallet-2023-grid-optimized-result-20261014/results_attempt001/final_evidence/SUMMARY.json)
- 2025 CASH: [DAILY](https://github.com/snowycat1234/coin/blob/bf7afc4ab20bbc271fb3ccdd48bcc05313dee01b/research/grid-original-wallet-2025-cash-optimized-result-20261014/results_attempt001/final_evidence/DAILY.json); [SUMMARY](https://github.com/snowycat1234/coin/blob/bf7afc4ab20bbc271fb3ccdd48bcc05313dee01b/research/grid-original-wallet-2025-cash-optimized-result-20261014/results_attempt001/final_evidence/SUMMARY.json)
- 2025 GRID: [DAILY](https://github.com/snowycat1234/coin/blob/dfaf9ebd2427a1de1eec0294fc8949dc9c7609cb/research/grid-original-wallet-2025-grid-optimized-result-20261014/results_attempt001/final_evidence/DAILY.json); [SUMMARY](https://github.com/snowycat1234/coin/blob/dfaf9ebd2427a1de1eec0294fc8949dc9c7609cb/research/grid-original-wallet-2025-grid-optimized-result-20261014/results_attempt001/final_evidence/SUMMARY.json)

Exact values and all 24 monthly contributions are in results/RESULTS.json and results/MONTHLY_INCREMENT.csv. Full paired daily contributions are in results/2023_PAIRED_DAILY.csv and results/2025_PAIRED_DAILY.csv.
