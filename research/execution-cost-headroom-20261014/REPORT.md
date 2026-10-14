# Execution-cost headroom on six saved development paths

## Finding

All six completed whole-wallet results remain profitable under a mechanical tripling of their observed fees plus execution costs. H090 has the largest arithmetic cost headroom, but this is not a risk-matched comparison or evidence of live feasibility. The more decision-relevant paired GRID increment stays positive in 2023 at 3× costs, while the 2025 disadvantage deepens. Neither year establishes a dependable incremental edge.

This is **static fixed-observed-path arithmetic, not a rebacktest**. It holds quantities, trades, marks, timing and funding unchanged and subtracts additional charges at the endpoint. Changed costs can alter NAV, sizing, admission, margin, liquidation and the entire trading path. A positive endpoint does not establish that the path could have been executed or remained solvent.

## Whole-wallet fixed-path sensitivity

All amounts are USDT. Multipliers apply to the total of saved fees and saved execution costs, including the baseline charge: 1.5× means an additional 0.5× charge, not an additional 1.5×. Funding stays fixed.

| Saved arm | Baseline net PnL | Fee + execution | Net at 1.5× | Net at 2× | Net at 3× | Breakeven multiplier |
|---|---:|---:|---:|---:|---:|---:|
| 2023 H090 CONTROL | 2014.2992 | 117.5320 | 1955.5331 | 1896.7671 | 1779.2351 | 18.1383× |
| 2023 ordinary CS/HOLD | 1156.4487 | 277.8932 | 1017.5021 | 878.5555 | 600.6622 | 5.1615× |
| 2023 CASH | 1096.2026 | 269.7976 | 961.3038 | 826.4050 | 556.6074 | 5.0631× |
| 2023 GRID | 1140.6713 | 281.6660 | 999.8383 | 859.0054 | 577.3394 | 5.0497× |
| 2025 CASH | 1667.7766 | 315.8627 | 1509.8453 | 1351.9140 | 1036.0513 | 6.2801× |
| 2025 GRID | 1632.4116 | 341.2319 | 1461.7956 | 1291.1797 | 949.9477 | 5.7839× |

Breakeven is the algebraic multiplier where this static endpoint equals zero. It is not a deployable cost tolerance, a calibrated friction model, or a forecast. H090 and ordinary CS/HOLD have different configured risk budgets, actual exposures and entry timing, as documented by the earlier public return-concentration report. CASH is a matched portfolio with its BTC allocation held in cash while other allocations remain active, not an all-cash wallet or ordinary CS/HOLD.

## Paired GRID minus CASH sensitivity

Apply each common multiplier to each arm's own saved charges. These are shared-wallet portfolio differences, not isolated grid-owner PnL or causal standalone grid alpha.

| Year | 1× | 1.5× | 2× | 3× | Extra GRID baseline charges | Equality multiplier |
|---|---:|---:|---:|---:|---:|---:|
| 2023 | 44.4687 | 38.5345 | 32.6003 | 20.7319 | 11.8684 | 4.7468× |
| 2025 | -35.3650 | -48.0497 | -60.7343 | -86.1036 | 25.3693 | -0.3940× |

The 2023 GRID increment reaches static equality at 4.746822× combined charges. The 2025 equality point is negative, hence outside the economically meaningful nonnegative-cost domain. At zero fee/execution charges, its GRID-minus-CASH gap is still −9.9957 USDT with funding fixed. Increasing the common multiplier cannot cure that disadvantage.

## Saved accounting and sign verification

| Saved arm | Paid fees | Execution cost | Signed funding | Saved gross same-quantity PnL |
|---|---:|---:|---:|---:|
| 2023 H090 CONTROL | 47.8828 | 69.6492 | -67.8447 | 2199.6759 |
| 2023 ordinary CS/HOLD | 113.2154 | 164.6779 | -133.7948 | 1568.1368 |
| 2023 CASH | 109.9172 | 159.8805 | -128.4687 | 1494.4689 |
| 2023 GRID | 114.7524 | 166.9136 | -132.5502 | 1554.8875 |
| 2025 CASH | 128.6842 | 187.1784 | -67.7740 | 2051.4133 |
| 2025 GRID | 139.0199 | 202.2120 | -71.0618 | 2044.7054 |

The accounting identity verified across all six records is:

net = gross_same_quantities − fees − execution_cost + signed_funding.

All six funding values are negative; they are net outflows, not funding credits. Gross reconstructed from net is net + fees + execution_cost − signed_funding. It agrees with each separately saved gross value within 2.4e−35 USDT. These tiny native accounting residuals are retained in RESULTS.json, rather than claiming bit-for-bit native accounting equality. This verifies the saved numerical sign convention; it does not certify the economic correctness of the funding unit, which remains unconfirmed.

The stress arithmetic deliberately starts from the saved net figure rather than replacing it with reconstructed gross. For combined saved charge C = fees + execution_cost and multiplier m:

- extra charge = (m − 1) × C
- static net(m) = saved net − (m − 1) × C
- whole-wallet breakeven m = 1 + saved net / C
- paired delta(m) = saved GRID-minus-CASH net − (m − 1) × (GRID charges − CASH charges)

The 1×, 1.5×, 2× and 3× comparison set was fixed in the task before examining the outcomes. Equality points are analytical diagnostics, not optimized parameters. The execution field combines saved spread/slippage costs; this packet does not pretend to isolate slippage alone, impose a new order-size model, or infer turnover. The earlier reports identify BASE27 as the original nominal model, but multiplying realized aggregate charges here is not a new bps calibration.

## Source fields and precision

SOURCE_CATALOG.json supplies immutable public SUMMARY links for all six inputs. The new inputs contain only these allowlisted fields copied from those saved summaries:

- decimal_strings.net_PnL: original cumulative net profit; primary sensitivity baseline
- decimal_strings.fees_USDT and execution_cost_USDT: nonnegative saved charges; multiplier base
- decimal_strings.funding_USDT: signed funding contribution; held fixed
- decimal_strings.gross_PnL_same_quantities: independent saved gross for sign/bridge verification
- decimal_strings.NAV and paid_NAV_decimal: terminal NAV cross-check; NAV minus net recovers exactly 10,000 USDT initial capital
- decimal_strings.unpaid_liability: checked zero
- complete_calendar, completed_minutes, required_minutes, completion, terminal_cash_realized: completed 525,600-minute calendar and realized-terminal checks

All sums/products use 80-digit Decimal arithmetic on original decimal strings. These finite operations preserve their published precision exactly. Ratios may repeat: the JSON provides 80-significant-digit Decimal results plus exact numerator/denominator pairs. Display tables round to four decimal places. Synthetic edge cases and all six financial inputs pass 12 tests; the dataset test separately validates scenarios and threshold pairs with Python Fraction rational arithmetic. The accounting tolerance was fixed at 1e−30 USDT, well below economic materiality.

This diagnostic is distinct from the existing return-concentration and GRID daily/monthly-consistency analyses. It adds scalar cost sensitivity and algebraic equality points; the original gross/net decomposition is supporting source evidence, not claimed as a new backtest.

## Limits

These are already-seen development years, with no fresh out-of-sample period, new market data, strategy rerun, threshold tuning or future APR claim. Funding units remain unconfirmed. Historical instrument filters, provider timing and native exchange risk tiers/liquidation are not certified by this calculation. Same configured budget does not imply same actual risk. No live-trading or account access occurred.

The standalone packet contains only public financial extracts, source URLs, analysis, results and tests. It requires Python's standard library only and makes no network calls. It is prepared for review, not published by this task.
