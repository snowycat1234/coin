# Fresh-daily reentry after a paid-flat 50% protective exit

Prepared on 2026-10-13 UTC. **Zero new historical wallets. Independent exact-byte review and separate parent GO are required before execution.** This stage writes only new code, synthetic tests, and preregistration in its own directory. It neither publishes nor opens a historical wallet. No live trading, credentials, account connection, Library access, protected-data download, or retained 2026 dataset access is in scope.

## Question and single changed mechanism

Does the existing guard's stopped-direction lock, rather than the fixed 50% isolated-equity loss trigger, explain part of its adverse 2025 outcomes? Keep the existing trigger and paid, capacity-limited full reduce-only exit. Remove only the subsequent direction restriction.

For a protected symbol, the first new DAILY_TARGET with signal_us strictly greater than its recorded paid-flat flat_us may reset the lock and schedule any direction (same, opposite, or zero), provided actual Decimal quantity is exactly zero, the account status is ACTIVE, stop is None, and terminal is false. A residual of even one 1e-8 step is not flat. The triggering day's target is not cached or rescheduled at the close fill. Equal-clock and old signals cannot unlock. Non-daily exit/risk instructions cannot unlock. While nonzero, the original protective zero-target persists and a later daily target cannot overwrite it. The original hard exposure-cap reduction takes priority and retains its genuine five-attempt STOP. Account halt and fixed-horizon terminal handling have priority; neither can be rescued or followed by reentry. All equal-time funding events are processed before the inherited mark-close protection decision, exactly as in the frozen guard.

The implementation subclasses the frozen ProtectiveFullExitSimulator, overriding only the entry gate. Original account finance, risk_schedule, funding_through, protective attempts/deferral, advance_day, and original policy files are unchanged. New terminal-attempt counters are observers only. Snapshot metadata binds the new policy and code identity.

## Exact fixed design

Exactly three independent new wallets, each fresh 10,000 USDT and fine quantity step/minimum 0.00000001: 2024 STATIC50, 2025 STATIC50, and 2025 COMBINED. Full original calendar windows are fixed. Reuse the completed fine ORIGINAL and GUARD50 controls for each pair; **zero comparator reruns**. No fourth case, arm, alternate year/date, threshold, parameter search, cooldown, or winning-case selection is permitted by this manifest.

Reuse all existing frozen target archives and numerical arrays, source indexes/months and mark overlay, RAW_AS_FRACTION funding-unit assumption, BASE27 costs (5.5 bp fee, 4 bp half-spread, 4 bp slippage per side), previous completed minute quote volume × 0.001 capacity, 10 USDT opening-only minimum notional and closing exemption, .30 per-asset/.60 gross caps, .99 sizing buffer, shared free cash, one-way isolated 1×, .005 MMR, no top-up, latency, reductions-before-increases and fixed final-horizon convention. CASE_BINDINGS.json records full source/target identities and exact completed control ACCOUNT, RESULT, BINDING, minute-fingerprint, POINTER, and zero-advance cold-receipt hashes. The original fine profile and all financial/dependency hashes are reused, never edited.

The frozen global terminal signal remains at end minus six minutes. Ordinary TERMINAL orders retain the original five eligible attempts. The old protective adapter keeps PROTECTIVE_STOP when a protected position remains nonzero at terminal; that inherited interaction is deliberately unchanged for a single-factor ablation. Actual terminal-phase attempt kind, count, first/last timestamp are separately recorded, and continuing protective attempts are never described as five TERMINAL attempts. No post-terminal new daily target is allowed.

## Strong acceptance before any performance interpretation

For each new wallet, find the first SAME_DIRECTION_REENTRY_ALLOWED event. Its signal is a real new DAILY_TARGET after exact paid-flat. Every financial minute with close_us <= that signal, every full trade-journal row with event_us <= that signal, and every full funding-journal row with event_us <= that signal must be byte/equality identical to the existing fine GUARD50 control. All numerical minute bits, including signed zero, must match. Funding includes the complete equal-clock batch. If no such event occurs, the entire observed financial path must match the guard exactly, including completion/halt horizon. Prefix shape/horizon mismatches fail closed. No guard replay is used to generate this check; read the hash-bound lossless day chunks and journals.

PREFIX_ACCEPTANCE.json must pass before RESULT.json can be written. A failed check stops the queue, keeps genuine checkpoints and logs, and prohibits performance conclusions. Synthetic tests require first-day exact prefix identity, same-side divergence only at the next new daily decision, same-clock funding batching, exact-flat one-step residue rejection, partial fills without daily supersession, old/equal signal rejection, terminal/halt priority, original cap STOP, repeated protection cycles, snapshot recovery, no-trigger/native identity, old opposite-target identity, tamper rejection, and external-pack resource reservation.

## Output and interpretation

Preserve full source/target/profile/code/run binding, lossless 30-day and final checkpoints, all trade/funding/rejection/protection/reentry journals, daily NAV, exact numerical minute fingerprints, independent signed inventory and Decimal NAV bridge, resource/timing receipts, prefix acceptance, and terminal attempt observations. Report all three cases against both frozen controls. Primary outcomes: completed/required minutes, status/halt, paid-flat classification, marked/paid PnL as applicable, drawdown, first/new same-direction entries and subsequent exits/halts. Secondary: actual exposure, target gap, turnover, fees, execution costs, funding, rejected reasons, residue and terminal attempt kinds/counts.

A full calendar with exact terminal-flat inventory and COMPLETE_CONDITIONAL_ACCOUNT permits paid PnL. Otherwise report marked PnL and the actual horizon; a partial/halted case has no annual return. Unequal horizons need an explicitly matched observed prefix for path comparisons. Report negative cases and no-mechanism cases. Conditional Binance observations and assumed Bybit costs/fine grid are not historical venue-certified fills, live tradability, out-of-sample evidence, or a performance promise.

## Review, GO, and shared resource gate

FROZEN_CODE.json pins every prepared source/protocol/binding and all frozen dependencies. Its bootstrap verifies bytes before financial imports. Independent review must write REVIEW_RECEIPT.json with PASS_INDEPENDENT_PRE_GO_REVIEW, zero new historical wallets, exact manifest and bootstrap hashes. A code/input edit invalidates review and requires new review and GO. --check-only makes no wallet. Worker paths require controller nonce, exact bytes, review receipt, one-CPU affinity and original 4 GB address-space limit.

At most two one-CPU workers, original 2 GB sampled RSS cap each, zero swap, shared 8 GB host-used cap, actual cgroup checks, 15 GiB disk reserve, 250 MB wallet state cap, 1200-second per-wallet wall/CPU limit and 1200-second whole-controller ceiling. Plan about 12–20 minutes with two workers, subject to observed work and resource admission; budget stops are honest partial results. Parent GO must recheck resources.

resource_gate.py is the single admission point for this new controller. It holds a host-wide coin financial-controller advisory lock, blocks earlier running financial controllers/workers, and separately reserves the guard-pack task's full 2 GB commitment and CPU 8 until an explicit parent-verified completion/release receipt exists, even when no pack PID is visible. The parent confirmed 4,053 restored files, 11 native zero-advance wallets and heavy-work release at 11:42:41 UTC; GUARD_PACK_RELEASE.json records that verified release. Fresh resource admission remains mandatory. Any observed new pack/restore process still gets a full reservation and its affinity excluded. The already-launched pack cannot retroactively participate in that lock, so it is explicitly detected/reserved instead. Both current RSS and full commitments are counted conservatively. Each newly admitted worker rechecks this gate; memory/disk/swap limits remain monitored during execution. If two free CPUs or the conservative budget are unavailable, pause rather than silently reducing constraints.

Preparation commands (synthetic/read-only):

    PYTHONDONTWRITEBYTECODE=1 coin_native_half_mix_20261013/.venv/bin/python coin_daily_reentry_ablation_20261013/test_synthetic.py
    PYTHONDONTWRITEBYTECODE=1 coin_native_half_mix_20261013/.venv/bin/python coin_daily_reentry_ablation_20261013/run_cases.py --check-only

Historical launch shape, **not executed in preparation**, only after independent review, specific file/publication review and separate parent GO:

    PYTHONDONTWRITEBYTECODE=1 coin_native_half_mix_20261013/.venv/bin/python coin_daily_reentry_ablation_20261013/run_cases.py --parent-go --state-root coin_daily_reentry_ablation_20261013/state_GO_DATE

Publication is a separate parent action. Prepared file list and exact hashes must be supplied before any publish or history.
