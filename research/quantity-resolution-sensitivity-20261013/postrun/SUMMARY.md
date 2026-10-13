# Quantity-resolution sensitivity, completed 2026-10-13

Offline conditional simulation, fixed in advance: six frozen source/target pairs, each under the existing coarse lot proxy and a fine-grid idealized limit, with the original and frozen 50% protective-exit modes. The 12 fine wallets each started with 10,000 USDT; no coarse wallet was rerun. This is not a historical venue-filter certification or a tradability claim.

**Bottom line.** Finer lots generally reduced target-weight tracking error and terminal residue, but increased fills, turnover, fees, and modeled execution cost. They did not avert the 2024 STATIC50 original account halt or remove the adverse 2025 protective-exit effects. Where both sides finished and paid flat, profit changes were mixed. Marked PnL with open positions is not cash realized.

P = full-calendar terminal cash realized; M = full-calendar marked PnL with open residue; H = stopped early, marked PnL at halt. All monetary entries are USDT per wallet. Target gap is minute-weighted mean sum of five absolute realized signed-weight minus frozen target-weight differences; it also includes market drift and guard intent, so it is not a pure lot-rejection measure.

| Pair | Mode | P/M/H: coarse → fine | Drawdown %: coarse → fine | Residual notional: coarse → fine | Fill legs: coarse → fine | Turnover: coarse → fine | Fees: coarse → fine | Execution cost: coarse → fine | Target gap: coarse → fine |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023 STATIC50 | original | P 1,152.92 → P 1,159.69 | 12.07 → 11.99 | 0.00 → 0.00 | 1,091 → 2,046 | 190,917.29 → 205,855.35 | 105.00 → 113.22 | 152.73 → 164.69 | n/a → 0.00924 |
| 2023 STATIC50 | guard 50% | P 1,267.94 → P 1,258.58 | 11.33 → 11.21 | 0.00 → 0.00 | 1,116 → 2,047 | 192,088.97 → 206,373.33 | 105.65 → 113.51 | 153.67 → 165.10 | 0.01546 → 0.00952 |
| 2023 COMBINED | original | M 326.98 → P 254.98 | 9.80 → 9.98 | 89.58 → 0.00 | 908 → 1,667 | 155,920.14 → 174,814.09 | 85.76 → 96.15 | 124.74 → 139.85 | 0.01172 → 0.00551 |
| 2023 COMBINED | guard 50% | M 326.98 → P 254.98 | 9.80 → 9.98 | 89.58 → 0.00 | 908 → 1,667 | 155,920.14 → 174,814.09 | 85.76 → 96.15 | 124.74 → 139.85 | 0.01172 → 0.00551 |
| 2024 STATIC50 | original | H 1,563.08 → H 1,512.48 | 10.38 → 9.98 | 2,132.43 → 1,775.63 | 602 → 1,735 | 137,794.39 → 161,816.24 | 75.79 → 89.00 | 110.24 → 129.45 | 0.02147 → 0.00825 |
| 2024 STATIC50 | guard 50% | P 2,140.36 → P 1,981.83 | 9.29 → 9.50 | 0.00 → 0.00 | 658 → 1,922 | 157,514.13 → 183,610.84 | 86.63 → 100.99 | 126.01 → 146.89 | 0.02346 → 0.00818 |
| 2024 EXACTHALF | original | P 1,408.46 → P 1,386.55 | 9.89 → 9.28 | 0.00 → 0.00 | 599 → 1,629 | 126,423.49 → 155,779.28 | 69.53 → 85.68 | 101.14 → 124.62 | 0.02110 → 0.00456 |
| 2024 EXACTHALF | guard 50% | P 1,408.46 → P 1,386.55 | 9.89 → 9.28 | 0.00 → 0.00 | 599 → 1,629 | 126,423.49 → 155,779.28 | 69.53 → 85.68 | 101.14 → 124.62 | 0.02110 → 0.00456 |
| 2025 STATIC50 | original | M 1,813.34 → M 1,612.84 | 7.99 → 8.50 | 2,227.97 → 1,304.44 | 626 → 2,791 | 210,333.11 → 249,246.88 | 115.68 → 137.09 | 168.27 → 199.40 | n/a → 0.00947 |
| 2025 STATIC50 | guard 50% | M 1,073.00 → M 897.44 | 12.29 → 13.30 | 1,926.46 → 1,143.35 | 602 → 2,682 | 203,503.46 → 242,328.33 | 111.93 → 133.28 | 162.80 → 193.86 | 0.03703 → 0.01133 |
| 2025 COMBINED | original | M 661.89 → M 597.57 | 7.49 → 7.55 | 1,088.64 → 266.76 | 448 → 1,606 | 135,458.88 → 177,474.63 | 74.50 → 97.61 | 108.37 → 141.98 | 0.03112 → 0.00569 |
| 2025 COMBINED | guard 50% | M 240.78 → M 220.17 | 9.34 → 9.51 | 1,088.64 → 210.58 | 438 → 1,598 | 130,323.41 → 174,900.81 | 71.68 → 96.20 | 104.26 → 139.92 | 0.03283 → 0.00608 |

## Interpretation

- 2023 STATIC50 was paid flat in all four cells. Finer lots changed original paid PnL by +6.78 USDT and guarded paid PnL by −9.37; the protective improvement remained positive under both grids.
- 2023 COMBINED was marked with 89.58 USDT residue under the coarse grid but paid flat under the fine grid. Its −72.00 USDT marked-to-cash numerical change is not a comparable paid-profit delta. The 50% guard did not alter either grid’s path.
- 2024 STATIC50 original halted at the identical 461,448th completed minute under both grids. The common completed-minute prefix (before the halt mark) was −51.35 USDT lower in the fine path, with lower mean target gap. Neither original has a valid annual realized return. The guard rescued both paths to full-year paid/flat, at +2,140.36 coarse versus +1,981.83 fine; the grid delta is −158.54 USDT paid.
- 2024 EXACTHALF was paid/flat in every cell and guard-neutral. Finer lots decreased paid PnL by 21.91 USDT while reducing drawdown and target gap.
- Both 2025 arms ended the full calendar with open positions, under both grids and guard modes. The guard reduced marked PnL and increased drawdown in each arm even under finer lots: STATIC50 fine +1,612.84 → +897.44 USDT and 8.50% → 13.30% DD; COMBINED fine +597.57 → +220.17 and 7.55% → 9.51% DD. No 2025 paid-return claim follows.
- Among the nine full-calendar coarse/fine comparisons with both minute traces available, all nine had a smaller target gap under the fine grid. The halted 2024 STATIC50 original also had a smaller matched-prefix gap. The two older published coarse STATIC50 originals have result details but no local minute-recovery trace, so their gap is explicitly unavailable.
- Every matched-horizon coarse/fine comparison increased fill legs and turnover. This mechanically raises fees and modeled execution costs; it is a material part of why better target tracking need not improve PnL. The precise absolute/relative trade and reason-wise rejection changes, funding, exposure, and all hash-bound provenance are in RESULTS_COMPACT.json.

## Scope and verification

The original coarse source and target identities are bound in the frozen CASE_BINDINGS.json and the independently checked baseline appendix. The fine runner and account profile were published before historical execution. All 12 workers ended with code 0 and no resource stop, then independently passed zero-financial-advance cold restore, full checkpoint/minute/journal/target and Decimal NAV reconciliation. The postrun scripts, their V2 manifest and independent review receipt are byte-pinned. The first postrun cold-audit launch failed at an import before any receipt or financial advance; the repaired import was independently reviewed before the successful audit. POSTRUN_AUDIT_ATTEMPT_001.json and ATTEMPTS.json retain those facts. BRANCH_HEADS_20261013_1048.txt records the full branch inventory at 10:48 UTC.

The fine-grid 1e-8 step and 10 USDT opening minimum with closing exemption are conditional research settings. Dated historical venue filters remain unknown; Binance observations and assumed Bybit execution costs do not establish live tradability.
