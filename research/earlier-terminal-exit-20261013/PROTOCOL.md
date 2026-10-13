# Fixed earlier terminal exit, 2025 two-arm execution ablation

Prepared 2026-10-13 UTC. Exactly two new fresh 10,000 USDT wallets, ORIGINAL fine STATIC50 (CS+HOLD) and EXACTHALF. The existing 2025 exact-half archive column is named COMBINED; its array must equal 0.5 STATIC50 + 0.5 SMA200_10PCT. Baselines are the already executed original fine wallets. There are no baseline reruns, new fits, new strategy choices, or window searches. This is a prespecified execution ablation on already-seen development history, not new OOS evidence.

## Fixed sole intervention

At 2025-12-31 22:59 UTC, schedule zero inventory TERMINAL instructions. They can attempt at each of the 60 real minute opens 23:00 through 23:59 UTC, event timestamp open+1 microsecond. Stop at the unchanged 2026-01-01 00:00 UTC exclusive end. No extra 2026 quotes, extra period, forced/free fill, current/future quote capacity, same-minute retry, or read of retained 2026 data. The constant 60 is chosen before the new histories, will not be adjusted to achieve flat, and is shared by both arms. If inventory remains after 60 attempts, preserve it and report marked PnL, never paid-flat return.

The adapter changes only terminal signal timing and terminal expiry. Daily/risk/asset-mask target, nonterminal five-attempt expiry, and all native finance remain byte-bound. Terminal zero target cancels/supersedes older pending instructions and cannot increase/reverse inventory. The inherited 23:54 terminal branch is ignored as a duplicate so it cannot reset terminal signal or attempt count. The first terminal signal and all actual attempts remain in the original scheduler's funding/mark ordering.

## Unchanged contract

2025 source, 365 daily target rows, CORE5 symbol order, 525,600 real minutes, 10,000 USDT shared capital, one-way isolated 1x, no top-up, 0.30 per-asset/0.60 target gross cap and existing drift/risk exits, fine 1e-8 lot and same minimum, 10 USDT opening minimum with closing exemption, 5.5bp fee + 4bp half spread + 4bp slippage per side, original observed funding events and conditional rate interpretation, previous completed minute quote volume x 0.001 capacity. Price/mark/funding/provenance uncertainty remains; no native venue-filter or actual exchange-readiness certification. No reliable live APR claim.

## Validation, budget and stopping

Synthetic tests must prove 60 distinct real opens, signal delay, terminal no increase/re-entry or overwrite, unchanged nonterminal expiry, cost/funding normal, causality and capacity, halt preservation, snapshot restore and exact unchanged native attempt method except two terminal expiry substitutions. Read-only preflight checks all 12 already cached 2025 months and all input/source/target/baseline bytes, constructs zero historical wallets, downloads nothing, and never opens retained/unknown data. Independent exact-byte review, remote preregistration and a separate parent GO are required before launching history. A single module-wide budget forbids a second batch via another state root.

Reuse shared controller lock and conservative resource gate, maximum two distinct one-CPU workers, finite 4GB address-space and 1200-second CPU/wall per wallet, sampled RSS stop 2GB each, shared host-used cap 8GB, swap0/GPU0, 15GiB disk reserve and 250MB state/wallet. Economic halts are outcomes, not a reason to censor the other fixed arm. Program/integrity/resource failure stops peers and queue, preserving every real partial checkpoint and all STOP receipts. No unreviewed repair or rerun.

Previous fine 2025 wallets took 415 seconds each. Plan 7–10 minutes parallel histories plus 5–10 minutes independent cold restore/report; hard wallet cap20min. Recheck actual shared CPU/memory/disk at GO. No external account/credentials, persistent access, payment, provider-block bypass or large downloads.

## Reporting

For each arm and old/new identical calendar, report paid-flat eligibility and paid cash PnL separately from marked year-end PnL, cumulative PnL, minute DD, actual gross/net exposure, turnover, fees, execution loss, funding, fills, reasonwise rejections, terminal fills/attempts/capacity and signed residuals. Verify complete pre-intervention numeric minute prefix equality and signed-inventory/Decimal NAV bridge. Cold restore is zero-financial-advance and reproduces all saved account/journal/minute identities. Preserve negative, stopped or residual outcomes. Publish minimal reviewed code/protocol/small evidence plus necessary results to the dedicated research branch; verify remote SHA and exact bytes.
