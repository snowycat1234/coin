# Fresh-daily reentry ablation: all three fixed cases completed

Offline conditional simulation, fixed before execution: 2024 STATIC50, 2025 STATIC50 and 2025 COMBINED, each with 10,000 USDT and the frozen 1e-8 fine grid. Six already-completed fine original/guard controls were reused; zero control reruns, no threshold/date/arm search, and no financial advances during cold audit.

**Bottom line.** Removing the stopped-direction lock improved both 2025 arms relative to the old guard, but recovered only part of the adverse guard effect. It reduced 2024 paid profit relative to the old guard. All three new wallets completed without account halt. Both 2025 arms retain terminal exposure and have marked PnL only.

P = complete calendar and exact terminal-flat cash realized; M = complete calendar with terminal exposure; H = halted partial calendar, marked value at stop. All monetary amounts are USDT per independent wallet. Drawdown is the frozen all-observation drawdown.

| Pair | Mode | P/M/H | PnL | DD % | Terminal gross residue | Same-direction executed reentries |
|---|---|---|---:|---:|---:|---:|
| 2024 STATIC50 | ORIGINAL | H | 1,512.48 | 9.9765 | 1,775.63 | n/a |
| 2024 STATIC50 | GUARD50 | P | 1,981.83 | 9.5016 | 0.00 | n/a |
| 2024 STATIC50 | FRESH_DAILY_REENTRY | P | 1,828.74 | 9.9488 | 0.00 | 4 |
| 2025 STATIC50 | ORIGINAL | M | 1,612.84 | 8.4979 | 1,304.44 | n/a |
| 2025 STATIC50 | GUARD50 | M | 897.44 | 13.3037 | 1,143.35 | n/a |
| 2025 STATIC50 | FRESH_DAILY_REENTRY | M | 1,005.54 | 12.4441 | 1,167.69 | 1 |
| 2025 COMBINED | ORIGINAL | M | 597.57 | 7.5513 | 266.76 | n/a |
| 2025 COMBINED | GUARD50 | M | 220.17 | 9.5062 | 210.58 | n/a |
| 2025 COMBINED | FRESH_DAILY_REENTRY | M | 240.27 | 9.3283 | 213.58 | 1 |

## Fixed contrasts and interpretation

- 2024 STATIC50: new paid profit +1,828.74 versus guarded +1,981.83, a −153.08 USDT paid change; drawdown rose by 0.4472 percentage points. The original halted after 461,448 completed minutes and has no annual paid return. On the common completed-minute prefix, new marked PnL was 4.68 USDT lower than original; this excludes the later halt mark. The new wallet completed all 527,040 minutes and paid flat.
- 2025 STATIC50: new marked PnL +1,005.54 versus old guard +897.44, a +108.10 USDT marked change; drawdown fell by 0.8596 percentage points. Relative to the original, marked PnL remains 607.30 lower and drawdown 3.9462 percentage points higher. New terminal residue is 1,167.69 USDT, so no annual paid-return claim follows.
- 2025 COMBINED: new marked PnL +240.27 versus old guard +220.17, a +20.10 USDT marked change; drawdown fell by 0.1779 percentage points. Relative to the original, marked PnL remains 357.30 lower and drawdown 1.7770 percentage points higher. New terminal residue is 213.58 USDT, so no annual paid-return claim follows.
- Same-direction permissions actually produced four, one and one executed reentries. The 2024 path includes a further paid protective exit after one XRP reentry. The 2025 COMBINED opposite-direction DOGE reset permission produced no immediate opening fill; permission is not treated as execution.
- Compared with old guard, all three new paths increased accepted fill legs/turnover and modeled fees/execution cost, while lowering full-calendar target-weight gap. Target gap includes market drift and protective exits; it is not a pure lot-rejection count. Full absolute metrics, reason-wise rejections and common-prefix data are in RESULTS_COMPACT.json.

## Exact financial-prefix acceptance and cold audit

| Pair | First new same-direction DAILY_TARGET UTC | Exact matched minute rows through that signal | Matched trade legs | Matched funding rows |
|---|---|---:|---:|---:|
| 2024 STATIC50 | 2024-03-14 00:00:00 | 105,120 | 416 | 1,095 |
| 2025 STATIC50 | 2025-10-11 00:00:00 | 407,520 | 1,902 | 4,250 |
| 2025 COMBINED | 2025-10-11 00:00:00 | 407,520 | 1,192 | 4,250 |

All three mandatory prefix checks passed before RESULT acceptance and were independently rechecked after restoration. All financial minute bits, complete trade rows and funding rows through the first newly allowed same-direction signal match the exact frozen fine GUARD50 control. All three final checkpoints passed the explicit new-class/FineGrid zero-transition cold dispatcher, full account/journal/target/minute reconciliation and the frozen Decimal NAV bridge.

The pre-execution code/receipt was published at e1f42b8ed4fbdfcd2870799bd4b375a3873743cb before the three-wallet run. The frozen financial module was not changed. The postrun observer received separate independent exact-byte review and parent AUDIT/REPORT authorization; all bounded historical/audit/report workers exited zero without resource stops. Cgroup limits were unavailable and unverified; host memory, sampled RSS, zero swap and conservative reservations were enforced.

Terminal attempt evidence reports frozen scheduler counter increments by inherited order kind, distinct from accepted fills. A zero-delta order may be counted without execute_fill; continuing PROTECTIVE_STOP is never relabeled TERMINAL. Unsupported control attempt counts remain unavailable.

These are conditional Binance-observation/assumed-Bybit-cost accounting experiments. The fine grid, venue filters and execution assumptions are not historically venue-certified. No live-tradability or out-of-sample performance claim is made.
