# 2023 fixed BTC-grid replacement: no dominance over original CSH

**Decision:** Prioritize the independent H090 CONTROL/finite line next. Keep this fixed grid recipe unchanged; a later 2025 corroboration could discriminate regime dependence if the exact original terminal60 control can be reused. These results do not justify tuning 2023 or rejecting grid/selector families.

## Full-year paid results

Each account starts with 10,000 USDT and completes the same 365 days / 525,600 minutes, ending 2024-01-01 UTC. All three are PAID_FLAT, with zero inventory, residual notional, liability or halt. Each is an independent account, not a compounded sequence.

| Saved arm | Paid NAV / net gain (USDT) | Return | Maximum drawdown | Annualized daily vol | Daily ES95 loss | Worst complete 30-day loss |
|---|---:|---:|---:|---:|---:|---:|
| Original CSH | 11,156.448710 / 1,156.448710 | 11.5645% | 11.9940% | 10.3551% | 1.1606% | 4.8258% |
| CASH_REPLACE10 | 11,096.202630 / 1,096.202630 | 10.9620% | 12.0724% | 10.1533% | 1.1415% | 4.6932% |
| GRID_REPLACE10 | 11,140.671334 / 1,140.671334 | 11.4067% | 12.1232% | 10.3127% | 1.1580% | 4.7534% |

GRID loses 15.777376 USDT to CSH (0.1578 percentage points of initial capital), while recovering 44.468703 USDT over CASH (0.4447 points). Its slightly lower volatility, expected shortfall and worst 30-day loss than CSH coexist with worse maximum drawdown and lower paid return. There is no across-dimension dominance.

## Where the differences came from

Saved aggregate cash identities give these exact policy contrasts, rounded here:

- GRID minus CSH: gross trading PnL −13.2493, funding relief +1.2446, extra fees −1.5370 and spread/slippage execution costs −2.2357 = net −15.7774 USDT.
- GRID minus CASH: gross trading PnL +60.4186, extra funding cost −4.0815, fees −4.8352 and execution costs −7.0331 = net +44.4687 USDT.
- CASH minus CSH: gross trading PnL −73.6679, funding relief +5.3261 and execution/fee savings +8.0956 = net −60.2461 USDT.

GRID has only **30 grid-owned fill legs among 2,031 native legs**, with grid-owned funding cash −0.126508 USDT. All grid inventory is paid out. This is a sparse admitted mechanism, not evidence that grid trading broadly fails.

The CASH sleeve removes 10% of every positive BTC target. GRID replaces the sleeve only when weekly causal/risk admission succeeds; otherwise it retains original BTC. Thus GRID−CASH includes different retained BTC participation and downstream account sizing. It does **not** isolate grid-harvest alpha. The saved aggregates do not establish how much of the 60.4186 gross advantage is direct grid harvest versus the eligibility/fallback difference.

## Same recipe, different actual exposure

All three use the same five USDT-linear perpetual assets, original unlagged STATIC50 target bytes, covariance/source bindings, terminal60 policy, and BASE27 cost recipe: 5.5bps taker fee + 4bps half-spread + 4bps slippage per side. Actual traded quantities, turnover and total costs differ.

- Average observed gross exposure: CSH 38.4167%, CASH 37.6134%, GRID 38.2448%
- Maximum observed gross exposure: CSH 62.3302%, CASH 60.4689%, GRID 60.6001%
- Maximum observed BTC weight: CSH 18.8928%, CASH 17.3203%, GRID 18.8787%

This is not equal-exposure risk parity. Nominal entry/risk controls do not certify instantaneous realized exposure caps or intraminute tail risk.

Funding uses the conditional RAW_AS_FRACTION assumption; units, publication/arrival and venue are not certified. The 1e−8 quantity step is a sensitivity proxy, not certified historical venue filters or liquidation rules. The one-year seen-development result is not a long-term APR or live-trading claim. Saved per-leg owner/funding equalities pass; tiny original aggregate Decimal bridge residues remain preserved under the stated 1e−32 tolerance.

## Exact attempts and immutable evidence

- CSH_OPTIMIZED_ATTEMPT001: one fresh account, 203.265s. [Immutable CSH result](https://github.com/snowycat1234/coin/commit/4534f87c977572c09930479eacf5a29aa7e0e569)
- CASH_OPTIMIZED_ATTEMPT001: one fresh account, 195.802s. [Immutable CASH result](https://github.com/snowycat1234/coin/commit/a801d2c1f413b8cc9c975616391c07611a61dfe7)
- GRID_OPTIMIZED_ATTEMPT001: one fresh account, 224.322s. [Immutable GRID result](https://github.com/snowycat1234/coin/commit/65cf1daa49cdd8dbec45c069c6856f24b6d2d7f2)

The earlier 133-day CSH partial remains separate and unchanged. These are fresh complete accounts, not resumes. This report uses only saved small summaries, identities, bindings, risk metrics and audits; no historical source arrays, account reconstruction, reruns or parameter search.
