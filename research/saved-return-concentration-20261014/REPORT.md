# 2023 return concentration: public saved-result audit

## Main finding

Both runs remain positive after mechanically removing their best month, October. Both become negative after removing their ten best daily returns. Their annual profit therefore depends materially on a small set of winning days. This describes the already-observed paths; it neither predicts that those days will disappear nor supplies a deployable alternative strategy.

| Diagnostic | H090 CONTROL | Ordinary CS/HOLD |
|---|---:|---:|
| Full-year return | +20.1430% | +11.5645% |
| Best month | October +12.1551% | October +7.1458% |
| Best month's share of net annual log return | 62.5094% | 63.0709% |
| Return after deleting October's observed daily returns | +7.1222% | +4.1240% |
| Top 5 days / net annual log return | 66.2397% | 90.5356% |
| Top 10 days / net annual log return | 104.3893% | 152.0595% |
| Return after deleting top 5 daily returns | +6.3914% | +1.0411% |
| Return after deleting top 10 daily returns | −0.8023% | −5.5378% |
| Top 5 days / all positive daily log returns | 23.1801% | 13.2549% |
| Top 10 days / all positive daily log returns | 36.5303% | 22.2623% |
| Worst complete 30-day return | −2.9219% | −4.8258% |
| Worst complete 90-day return | −4.7517% | −6.6816% |
| Daily-boundary maximum drawdown | 6.7998% | 11.2434% |
| Published all-event maximum drawdown | 8.3544% | 11.9940% |

Shares of **net** annual log return can exceed 100% because losing days offset winning days. The alternative positive-day denominator makes clear that H090's winning returns are more concentrated in its top ten days, even though its share of net annual log return is lower. Neither denominator by itself ranks strategy quality.

The deletion diagnostic replaces selected observed daily returns by zero while retaining all other observed returns. It does not rerun signals, positions, compounding-dependent sizes, fees, funding or margin. Subtracting October's fixed dollar PnL instead gives +8.3199% and +4.6484% on initial capital; those are a different, explicitly additive calculation.

## Calendar-month contribution

Monthly return uses that month's opening NAV. Contribution is monthly net PnL divided by the original 10,000 USDT, in percentage points; contributions add to annual return, while monthly percentage returns compound.

| 2023 month | H090 monthly return | H090 contribution, pp | CS/HOLD monthly return | CS/HOLD contribution, pp |
|---|---:|---:|---:|---:|
| January | 0.0000% | 0.0000 | +3.7145% | +3.7145 |
| February | 0.0000% | 0.0000 | −1.8451% | −1.9137 |
| March | 0.0000% | 0.0000 | +5.8950% | +6.0012 |
| April | 0.0000% | 0.0000 | −2.4943% | −2.6889 |
| May | +2.9884% | +2.9884 | −1.4376% | −1.5111 |
| June | −2.4417% | −2.5147 | −1.3778% | −1.4274 |
| July | −0.5876% | −0.5904 | −0.7434% | −0.7595 |
| August | −1.4242% | −1.4226 | −3.9218% | −3.9773 |
| September | −1.2112% | −1.1925 | −0.6700% | −0.6529 |
| October | +12.1551% | +11.8230 | +7.1458% | +6.9160 |
| November | +4.2829% | +4.6723 | +3.2492% | +3.3695 |
| December | +5.6076% | +6.3794 | +4.1973% | +4.4940 |

H090 has four positive, four negative and four zero-return months. CS/HOLD has five positive and seven negative months. All months are reported; none were selected to improve results.

## Coverage, event timing and windows

Both saved files contain 365 completed, contiguous daily intervals, from **2023-01-01 00:00:00 UTC through 2024-01-01 00:00:00 UTC exclusive**. Each has 336 complete 30-day windows and 276 complete 90-day windows.

- H090 worst 30 days: May 31–June 29 inclusive; June 30 00:00 UTC end boundary.
- H090 worst 90 days: June 3–August 31 inclusive; September 1 00:00 UTC end boundary.
- CS/HOLD worst 30 days: April 19–May 18 inclusive; May 19 00:00 UTC end boundary.
- CS/HOLD worst 90 days: July 13–October 10 inclusive; October 11 00:00 UTC end boundary.

H090 has 95 positive, 87 negative and 183 zero-increment days. Its first nonzero daily increment is May 23, consistent with the published SUMMARY's `first_entry_us` field, **May 23 at 00:01:00.000001 UTC**. CS/HOLD has 180 positive and 185 negative days, with its saved first entry January 1 at 00:01:00.000001 UTC.

These are full-calendar records, not 365 days of identical exposure. A zero net increment does not establish zero exposure. This audit does not inspect fills or minute positions, determine the cause of earlier H090 inactivity, infer an active-exposure day count, or annualize an active subperiod.

The H090 top ten daily-return dates, ranked descending, are November 10, October 16, October 23, October 20, November 15, May 28, December 21, December 8, October 19 and October 21. CS/HOLD's are January 14, November 10, October 16, October 23, August 29, February 15, October 20, January 20, December 21 and November 15. Exact returns are in RESULTS.json.

## Why this is not a fair-dominance or live-readiness result

- Both runs use CORE5 and 2023, but H090 has nominal gross cap 0.90 and annual-volatility target 0.15, versus ordinary CS/HOLD's 0.60 and 0.10. Their timing, admission and exposure also differ. These are not risk-matched arms, and this audit cannot attribute their return difference causally.
- Both are explicitly **seen-development** results, not out of sample. Diagnostic selection was fixed before this analysis, but that does not turn the underlying data into a holdout. There is no retuning, training, new backtest or fresh-market-data claim.
- Both saved summaries say PAID_FLAT, zero remaining notional and zero unpaid liability. The 10,000 USDT initial NAV is independently recovered from saved final NAV minus saved net PnL. Daily increments reconcile to saved final paid NAV within 1e−8 USDT. Derived NAV/returns are floating-point reconstructions, not exact Decimal account balances.
- Both use **BASE27**, with 5.5 bps taker fee plus 4 bps half-spread plus 4 bps slippage per side, totaling nominal 27 bps round trip. Saved H090 fees, execution costs and funding are 47.8828, 69.6492 and −67.8447 USDT; CS/HOLD values are 113.2154, 164.6779 and −133.7948 USDT. This analysis preserves those saved assumptions and does not test worse costs.
- Funding uses the saved RAW_AS_FRACTION scenario with **unconfirmed funding units**. Historical instrument filters, native risk tiers/liquidation and provider publication/arrival are not certified. The saved 1e−8 quantity-step sensitivity is not an exchange-certified historical profile.
- Margin is modeled as isolated 1x with an assumed 0.005 maintenance-margin rate, not native risk tiers. Observations cover causal minute-close marks, fills and funding, not intraminute mark extremes. Daily-boundary drawdown is consequently below the broader saved all-event drawdown.
- Actual gross weight peaks are 0.904573 and 0.623302, exceeding the nominal 0.90/0.60 settings; instantaneous cap guarantees are explicitly false. Saved minimum observed free cash is 1,273.4634 and 3,290.8821 USDT. None of this establishes live margin safety.
- Long-term APR, live profitability, native exchange liquidation certification and risk parity remain unestablished.

## Provenance and checks

Only six small, already-public UTF-8 JSON files were restored, totaling 141,923 bytes. No archives, binary results, raw market history or denied/private source bindings were used. Every file's exact byte size and Git blob hash were verified; SHA256, pinned commit and immutable source URL are preserved.

- [H090 completed public results](https://github.com/snowycat1234/coin/tree/41ace7413665fc2d9d0f074544078e6812c78c1e/research/h090-original-control-2023-attempt003-result-20261014/results_attempt003/final_evidence)
- [Ordinary CS/HOLD completed public results](https://github.com/snowycat1234/coin/tree/4534f87c977572c09930479eacf5a29aa7e0e569/research/grid-original-wallet-2023-csh-optimized-result-20261014/results_attempt001/final_evidence)

Nine synthetic arithmetic tests pass. Both worst-30-day calculations reproduce the saved public risk files. A separate 50-digit Decimal check passes 68 numeric comparisons, with maximum absolute difference 2.23e−16. An additional independent calculation directly from raw DAILY files agrees on the headline metrics; sequential floating-point endpoint differences are below 1e−8 USDT. Bounded-run timing, resource use and output hashes are recorded in the receipts.
