# Frozen CORE5, 2024 full-calendar native replay

Five independent fresh 10,000 USDT shared wallets ran against the prepublished frozen targets and 2024-01-01 to 2025-01-01 UTC market window. The engine, conditional quantity grid, fees, funding, and margin rules match the prior 2023/2025 native comparator. Financial code, target data, and source index were published before these wallets started. This is previously seen development history, not a fresh out-of-sample test.

| Frozen arm | 2024 outcome | Net USDT | Return | Observed-minute max DD | Annual daily vol | Mean actual gross | Paid flat? |
|---|---|---:|---:|---:|---:|---:|---|
| VOL_MATCHED risk-controlled HOLD | Full 366 days | +2,394.20 | +23.94% | 8.19% | 11.34% | 17.53% | Yes |
| EXACTHALF, 50% STATIC50 + 50% SMA | Full 366 days | +1,408.46 | +14.08% | 9.89% | 9.57% | 22.39% | Yes |
| SMA200_10PCT downscale-only | Full 366 days | +919.37 | +9.19% | 16.47% | 11.46% | 25.47% | Yes |
| STATIC50 risk-controlled CS + HOLD | HALTED Nov 16 10:49 UTC | +1,563.08 at halt | No annual return | 10.38% prefix | No annual volatility | 36.11% prefix | No |
| CS_MATCHED risk-controlled cross-section | HALTED Nov 16 10:49 UTC | +805.32 at halt | No annual return | 10.80% prefix | No annual volatility | 45.31% prefix | No |

The two halted accounts stopped at minute 461,448 of 527,040 with `LIQUIDATION_REQUIRED_HALT`. The model did not simulate liquidation fills and did not pay a terminal cash close. Their marked-at-stop P&L is preserved as a partial observation, not a 2024 result. All five resource guards exited normally, the independent Decimal NAV bridges agreed within 1e-35 USDT, and the three complete accounts ended paid-flat with no simulated liquidation.

The exact-half mix beat original SMA by 489.09 USDT / 4.89 percentage points with lower observed drawdown. It trailed risk-controlled HOLD by 985.74 USDT / 9.86 percentage points and had higher drawdown. Thus the mix is not the strongest 2024 full-year outcome. The frozen paired 14-calendar-day circular bootstrap (1,000 draws, seed 811764) yields descriptive 95% intervals of -10.15 to +17.96 percentage points for mix minus SMA and -26.44 to +4.25 points for mix minus HOLD. Both intervals cross zero; neither observed difference establishes robust superiority. No full-year pair is reported against either halted control.

Economics: BASE27 charges 5.5 bp fee, 4 bp half-spread, and 4 bp slippage per side; actual signed funding rates are read as fractions. Execution uses actual one-minute trade opens at 00:01 and previous quote volume × 0.001 capacity. Each account has one-way 1× isolated margin, no top-up, 0.5% maintenance ratio, conditional quantity steps BTC 0.001, ETH 0.01, SOL 1, XRP 100, DOGE 1,000, and the original paid final six-minute reduction attempts. Target caps are 0.30 per asset and 0.60 gross; actual drift and inability to fill remain visible. These venue-filter and funding-unit assumptions are conditional, not certified live exchange terms.

| Arm | Fees USDT | Spread/slippage USDT | Signed funding cash USDT | Gross fill turnover USDT |
|---|---:|---:|---:|---:|
| VOL_MATCHED | 8.06 | 11.72 | -273.74 | 14,646.41 |
| EXACTHALF | 69.53 | 101.14 | -183.80 | 126,423.49 |
| SMA200_10PCT | 74.70 | 108.66 | -213.34 | 135,826.98 |
| STATIC50, partial to halt | 75.79 | 110.24 | -128.13 | 137,794.39 |
| CS_MATCHED, partial to halt | 91.61 | 133.25 | +15.94 | 166,567.48 |

At the two August 12 mark minutes, all five wallets had unchanged quantities and no fills, funding, risk breaches, rejections, or liquidation event in the 10:00–10:10 UTC interval. The smallest held isolated-equity/notional ratio at the gap was 0.967 versus 0.005 maintenance; no gap-local replay was needed. Exactly ten original absent mark rows used the prepublished time-linear overlay. Original trade bars, trade volume, funding, and daily targets were untouched.

Artifacts: `FIVE_ARM_OBSERVER_REPORT.json` is the complete machine-readable comparison and valid-pair bootstrap. `RESULTS_FIVE_WALLETS.json` preserves the five original result records, bindings, resource receipts, and local audit-file hashes. `GAP_LOCAL_QA.json` contains the per-wallet August 12 observer check. The original `compare_2024.py` and target/source protocol remain unchanged; `compare_2024_observer.py` is a reporting-only adapter for the two genuine halted controls.
