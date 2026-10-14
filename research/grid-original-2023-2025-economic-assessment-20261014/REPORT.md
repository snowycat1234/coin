# Fixed 10% BTC replacement: saved 2023/2025 assessment

The unchanged grid recipe did not show consistent improvement over its matched cash replacement. All four wallets completed 365 days / 525,600 minutes and paid flat, with zero residuals/liabilities. Each began with 10,000 USDT.

| Seen year | CASH net return | GRID net return | GRID minus CASH | CASH / GRID drawdown | CASH / GRID mean gross |
|---|---:|---:|---:|---:|---:|
| 2023 | 10.9620% | 11.4067% | +44.4687 USDT | 12.0724% / 12.1232% | 37.6134% / 38.2448% |
| 2025 | 16.6778% | 16.3241% | −35.3650 USDT | 7.8073% / 8.4187% | 43.8635% / 44.5108% |

## Charged economic delta

GRID minus CASH, USDT (saved native Decimal totals):

| Year | Price PnL | Funding cash | Extra fees | Extra execution friction | Net delta |
|---|---:|---:|---:|---:|---:|
| 2023 | +60.4186 | −4.0815 | 4.8352 | 7.0331 | +44.4687 |
| 2025 | −6.7079 | −3.2878 | 10.3356 | 15.0336 | −35.3650 |

2025 added fees/friction were 25.3693 USDT, 71.74% of the shortfall. Annualized daily volatility rose from 9.9427% to 10.0932%; daily ES95 loss from 0.9798% to 0.9980%; worst complete 30-day loss from 4.3236% to 4.5577%. Thus the 2025 loss is accompanied by higher observed exposure/tail risk.

Ownership is sparse: 30 grid-related fill rows in 2023 and 42 in 2025. Grid-assigned funding cash was −0.1265084 and −0.2078616 USDT respectively. Whole-wallet differences include base inventory/rebalance/NAV path effects, so they are not standalone grid-wallet alpha.

## Scope and next decision

Same original target bytes, source/covariance lineage, five-asset universe, fixed rules, BASE27 costs and terminal60 were retained. Actual exposure and turnover differ; this is not risk-parity certification. Funding units and fine instrument filters remain conditional; these are seen-development model results, not live APR or out-of-sample evidence. Risk observations cover minute closes, fills and funding, not every intraminute extreme.

Keep this exact recipe as mixed evidence and move to the independently frozen FINITE candidate currently pending. Do not tune thresholds using these two outcomes or infer that all grid/selector approaches fail. No verified 2025 CSH numerical comparison is made; the original control needs its retained full-packet proof.

The saved audits report full native/owner reconciliation with no financial advances. Preserve tiny Decimal rounding bridges: 2025 independent cash bridge is +1E−35 (CASH), +2E−35 (GRID), while inherited summary bridges are −6E−36 and −2.4E−35.

## Immutable results

- [2023 CASH](https://github.com/snowycat1234/coin/blob/a801d2c1f413b8cc9c975616391c07611a61dfe7/research/grid-original-wallet-2023-cash-optimized-result-20261014/results_attempt001/final_evidence/SUMMARY.json)
- [2023 GRID](https://github.com/snowycat1234/coin/blob/65cf1daa49cdd8dbec45c069c6856f24b6d2d7f2/research/grid-original-wallet-2023-grid-optimized-result-20261014/results_attempt001/final_evidence/SUMMARY.json)
- [2025 CASH](https://github.com/snowycat1234/coin/blob/bf7afc4ab20bbc271fb3ccdd48bcc05313dee01b/research/grid-original-wallet-2025-cash-optimized-result-20261014/results_attempt001/final_evidence/SUMMARY.json)
- [2025 GRID](https://github.com/snowycat1234/coin/blob/dfaf9ebd2427a1de1eec0294fc8949dc9c7609cb/research/grid-original-wallet-2025-grid-optimized-result-20261014/results_attempt001/final_evidence/SUMMARY.json)

Exact strings, risk figures and source/body hashes are in EVIDENCE.json. This assessment reads compact saved output only; no account/source execution or tuning was performed.
