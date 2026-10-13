# CS SMA200 agreement experiment results

## Conclusion

The frozen AGREEMENT candidate fails qualification in both complete development years. Net return is −5.22076% in 2023 and −3.98495% in 2025; maximum drawdown is 17.30239% and 12.16629%, above the 12% limit. It beats signed SMA200 by a small cumulative amount but underperforms CS and STATIC50 in both years. No paired confidence interval has a positive lower bound. In 2025 the intervals versus CS and STATIC50 are wholly negative. Preserve this failed recipe; do not select the no-reallocation diagnostic as a replacement.

## Frozen calendar and economic model

- Decisions: 2023-01-01 through 2023-12-31 UTC and 2025-01-01 through 2025-12-31 UTC, exactly 365 daily decisions per independent wallet.
- Each decision uses available completed closes at 00:00 UTC, executes at 00:01:00.000001 UTC, and owns quantity for 24 hours. The final boundaries are 2024-01-01 and 2026-01-01 at the same execution time, including paid hypothetical terminal exit costs.
- Five arms use separate 10,000 USDT initial wallets in BTC, ETH, SOL, XRP and DOGE order. Weekly CS21 ranks remain sticky; signed SMA200 is long, short or flat. AGREEMENT keeps only CS legs agreeing with daily SMA200, without replacement ranks or raw-slot redistribution.
- The original 30-past-return sample covariance (ddof=1, annual factor 365) sizes four arms to nominal 10% risk with 30% single-asset and 60% gross caps. Scaling may amplify retained legs; this differs from the older downscale-only SMA implementation.
- The unchanged reviewed daily quantity proxy uses original owned p0/p1, interval masks and signed funding-per-unit. Positive funding debits longs and credits shorts; negative funding reverses that. Per-side cost is 13.5 bp: fee 5.5 bp + spread 4 bp + slippage 4 bp. Terminal costs are included in net return.
- All 10 wallets cover 365 days, pay the terminal and end with zero positions. Original saved float quantities independently reconcile in Decimal precision 60 with 1e−8 USDT tolerance; the largest NAV discrepancy is below 3.87e−11 USDT. Source and causal tests pass.

## Cumulative results

| Arm | 2023 net return | 2023 maximum drawdown | 2025 net return | 2025 maximum drawdown |
|---|---:|---:|---:|---:|
| CS | -0.89716% | 14.97081% | +21.95966% | 3.55994% |
| SMA200 | -7.01225% | 16.24125% | -4.61250% | 11.80630% |
| STATIC50 | -3.50132% | 15.07148% | +2.72442% | 9.91733% |
| AGREEMENT | -5.22076% | 17.30239% | -3.98495% | 12.16629% |
| AGREEMENT_NO_REALLOCATION | -2.49445% | 17.44567% | +1.13865% | 14.11519% |

The diagnostic row is descriptive only. Returns are cumulative wallet results, not a reliable estimate of live APR.

## Paired historical inference

14-calendar-day circular paired-date bootstrap, 1000 draws, frozen seeds 811760 (2023) and 811761 (2025). Saved date indices are shared across all arms and controls. The 95% percentile intervals below describe the mean daily paid-terminal return increment in basis points per day. They are conditional on seen history and are not research-selection-adjusted.

| Year | AGREEMENT minus control | Cumulative net-return difference | Mean daily increment | 95% paired interval |
|---|---|---:|---:|---:|
| 2023 | CS | -4.32360 pp | -1.3342 bp/day | [-7.2032, +5.2322] bp/day |
| 2023 | SMA200 | +1.79149 pp | +0.4428 bp/day | [-3.8030, +4.7185] bp/day |
| 2023 | STATIC50 | -1.71944 pp | -0.4995 bp/day | [-2.4765, +1.0868] bp/day |
| 2025 | CS | -25.94461 pp | -6.5072 bp/day | [-11.6059, -1.7105] bp/day |
| 2025 | SMA200 | +0.62755 pp | +0.2054 bp/day | [-2.1385, +2.5416] bp/day |
| 2025 | STATIC50 | -6.70937 pp | -1.8438 bp/day | [-3.4267, -0.4015] bp/day |

## Exposure and accounting interpretation

AGREEMENT mean gross exposure is 31.036%/22.679% (2023/2025), compared with CS 44.146%/48.889%. Agreement reaches nominal estimated risk on 315/339 days; 50/26 days have shortfall, including 17 intrinsic cash days in 2025. Cap-bound days are 50/9, and retained-leg amplification occurs 119/35 days. Mean estimated annual risk is 9.782%/9.452%, while realized paid-return volatility is 9.992%/11.300%. CS realized volatility is 13.321%/9.695%. Identical nominal policies and lower gross do not imply all-day matched or lower realized risk.

Primary accounting:

| Year | Price PnL | Trading cost including terminal | Funding cash | Net PnL | Total turnover including terminal |
|---|---:|---:|---:|---:|---:|
| 2023 | -118.73 USDT | 304.76 USDT | -98.59 USDT | -522.08 USDT | 225750.08 USDT |
| 2025 | -128.03 USDT | 245.73 USDT | -24.74 USDT | -398.49 USDT | 182019.33 USDT |

Price PnL is already negative before costs and funding in both years, so transaction drag alone cannot explain the failure. For 2025, the net shortfall versus CS is 2594.46 USDT: price-PnL shortfall 2688.24 USDT, partly offset by 104.14 USDT lower trading cost, with 10.36 USDT worse funding cash.

The no-reallocation diagnostic retains surviving already-sized CS weights exactly. It removes hedges as well as gross exposure: estimated annual risk exceeds 10% on 154/254 days, reaches 18.660%/25.761%, and realized volatility is 10.542%/15.487%. Its 2025 positive return therefore does not establish a matched-risk improvement; its 14.115% drawdown also exceeds the frozen limit. It remains a predefined exposure diagnostic, never an alternative winner.

## Frozen gates

- PASS: source identity and causal tests; full 365 decisions and paid proxy terminal in both years.
- FAIL: primary positive net in both years; primary positive cumulative increment over every CS/SMA/STATIC50 control in both years; positive lower paired-CI bound over every control in both years; primary maximum drawdown ≤12%.
- Overall: FAIL. Stop expansion of this recipe and retain all results without changing the year, window, filter or thresholds.

## Limits and next evidence

Both years are known historical development calendars. This module does not cover the 2021 bull market, 2022 bear market or currently blocked full 2024 calendar, so it is not full-cycle qualification. CS and SMA are same-period, same-cost and common-risk-policy comparators. No representative Bybit bot population is included, so the results cannot establish performance against its median or a majority of bots. This is a conditional hypothetical-filled quantity proxy, with no capacity, margin/MMR, liquidation, minQty or execution-fill certification. It is not pristine out-of-sample evidence, native-wallet qualification or reliable live APR. No protected 2026 holdout or unknown reserve was accessed. The targeted dedup review found no exact symmetric SMA200 gate, while retaining earlier failed SMA/CS mixture and short-only confirmation evidence; it is not exhaustive proof of absence.

Next useful low-cost step: read-only attribution from the saved quantities, targets and original execution/funding arrays. Reconcile each asset’s price PnL, signed funding and per-side trading cost for AGREEMENT versus CS, especially 2025; distinguish discarded CS legs from resized survivors and identify whether losses concentrate in particular dates, assets or hedge removal. This should explain the failure without fitting, new thresholds, extra accounts, provider downloads or holdout access.

## Reproducibility

Pre-score code and targets were remotely verified at commit ea3c90cc85f0bb57749bf5489b245c0bf139d3ff. RESULTS.json, original quantity traces, saved shared bootstrap indices/samples and PUBLICATION_RECORD.json retain protocol, code, input and target hashes. The deterministic RESULTS.zip packet carries all result files plus the report, publication record, original input/target NPZs and audit source files for separate-directory cold validation without rerunning economics, target construction or random-index generation.
