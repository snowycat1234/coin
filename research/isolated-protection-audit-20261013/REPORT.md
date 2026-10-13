# Isolated half-equity guard: fixed 11-wallet audit

Research-only conditional account model. This does not establish real exchange liquidation rules or tradable returns.

The 50% isolated-equity full-exit rule was frozen before historical replay. All 11 source/target/account bindings match the original controls. Each guard checkpoint was cold-restored without another financial advance; all day chunks, account journals, target rows and every numeric minute column passed exact checks.

| Year | Arm | Base completed | Base marked USDT | Guard completed | Guard marked USDT | Guard paid USDT | Guard DD | Signals | Paired paid delta USDT |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023 | STATIC50 | 525,600 | +1152.92 | 525,600 | +1267.94 | +1267.94 | 11.33% | 1 | +115.03 |
| 2023 | SMA200_10PCT | 525,600 | -661.75 | 525,600 | -53.69 | — | 11.45% | 1 | — |
| 2023 | COMBINED | 525,600 | +326.98 | 525,600 | +326.98 | — | 9.80% | 0 | — |
| 2024 | CS_MATCHED | 461,448 | +805.32 | 527,040 | +1897.15 | +1897.15 | 9.03% | 3 | — |
| 2024 | VOL_MATCHED | 527,040 | +2394.20 | 527,040 | +2394.20 | +2394.20 | 8.19% | 0 | +0.00 |
| 2024 | STATIC50 | 461,448 | +1563.08 | 527,040 | +2140.36 | +2140.36 | 9.29% | 3 | — |
| 2024 | SMA200_10PCT | 527,040 | +919.37 | 527,040 | +919.37 | +919.37 | 16.47% | 0 | +0.00 |
| 2024 | EXACTHALF | 527,040 | +1408.46 | 527,040 | +1408.46 | +1408.46 | 9.89% | 0 | +0.00 |
| 2025 | STATIC50 | 525,600 | +1813.34 | 525,600 | +1073.00 | — | 12.29% | 2 | — |
| 2025 | SMA200_10PCT | 525,600 | -382.28 | 525,600 | -456.62 | — | 11.57% | 1 | — |
| 2025 | COMBINED | 525,600 | +661.89 | 525,600 | +240.78 | — | 9.34% | 2 | — |

In the two 2024 controls that originally stopped on November 16 under the conditional account, the guard generated XRP full-exit signals on November 14 (CS 19:37 UTC, STATIC50 19:41 UTC) and completed paid closes at the next minute's open. Those guard paths reached year-end; the original partial marked values do not establish a paired annual return improvement.

The three 2025 matched full-year cases all deteriorated on marked PnL and minute drawdown: STATIC50 −740.34 USDT / +4.30 drawdown percentage points; SMA −74.33 / +0.70; COMBINED −421.11 / +1.85. All retained residual positions, so none has a paid annual return.

Paired paid deltas require both full-year flat endpoints. The two halted 2024 original controls have only partial marked values; their paid deltas are intentionally blank. Full-year marked and drawdown deltas are separately recorded in COMPARISON.json.

No-trigger cases must reproduce the original full-year marked PnL, minute drawdown and paid classification. Both improved and worsened arms are retained; this is a sensitivity exercise, not an optimized strategy selection.

Exact baseline identity appendix SHA256: 407973d261dc441360f86acd70b162d83190487082009030726587e7bc44f794

Small audit receipts and summary are publication-safe. Full checkpoint archives remain local pending separate payload/destination review; no original 2025 backup is included.
