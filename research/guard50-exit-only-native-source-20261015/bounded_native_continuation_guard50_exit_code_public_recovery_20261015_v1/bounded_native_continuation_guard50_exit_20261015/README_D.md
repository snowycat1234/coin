# Separate D: Guard50 paid exit only

Status: source/generated development. No historical launch or authority is granted by this directory, its preparation, or its invalid GO template.

## Fixed comparison

D is `GUARD50_EXIT_ONLY`: keep the corrected V2 native strategy, source, costs, shared wallet, risk/capital caps, causal quality and conditional-settlement accounting, but replace C's warning margin top-up with a full-actual-position paid protective exit. At an otherwise healthy, genuinely known/fresh observation, the warning is the same fixed `equity <= isolated_balance / 2` predicate. D never transfers collateral, including by a direct `_transfer` call. No warning threshold, sizing parameter or hyperparameter grid is introduced.

Only D is prepared for a possible full-2024 `STATIC50_MID`/`BASE27` case. Existing corrected B/C outputs are reused; neither is rerun by this entry.

## Native event ownership

1. Original native signal intent, causal source clocks and pending lifecycle are unchanged, including signals inside a missing-quality interval.
2. Native funding and immediate native mark-risk checks run at their original clocks. The continuation monitor waits for the complete same-clock funding batch; it cannot rescue a triggered position.
3. Missing or stale quality blocks new positive risk and new warning exits. It does not manufacture an exit. Ordinary strategy reductions, native risk/terminal exits, and previously legitimate warning exits remain payable through the original native execution rules.
4. A new genuine Guard50 warning records an idempotent `pending_exits` intent at that clock. Existing intent signal/renewal ownership is preserved. The native scheduler owns paid protective-exit latency, prior-completed-quote participation, partial fills, five-open expiry and causal renewal. No instantaneous/free close is inserted.
5. A paid warning exit is not a conditional settlement and does not acquire a liquidation-only new-signal lock. Actual conditional takeover still cancels only the affected symbol's stale increases, while every other symbol remains subject to fresh shared-wallet guards.
6. Fresh charged previews retain D state, permanent financial/intent IDs, bounded no-op replay and real fallback inventory; callbacks are suppressed and hypothetical forced settlement cannot admit new risk.

## Scope and reporting

The original V2 code and inputs remain immutable and pinned. D has a distinct policy/source/preparation/review/GO identity and a fresh-genesis historical constructor, separate from the generated flag. Snapshot/restart is uncertified and rejected. A valid independent review and external exact root GO are required before any historical constructor is called.

The one-case envelope is 600 seconds wall/CPU cap, one CPU thread, 2 GB RSS stop, 4 GB address space and 250 MB outputs. A finite generated profile is only an observation, not a full-calendar runtime guarantee.

The saved terminal validator retains the frozen controller's strict precision-100 stored-delta sum. Native financial/capture arithmetic uses precision 40, and independently proven captured-delta rounding can make that additional check reject an otherwise exact native event ledger. No epsilon or silent reporting correction is introduced here. Such a rejection must remain explicit and requires separate exact saved-event evidence; it cannot be relabeled a completed controller run.

Financial reports distinguish actual paid market flat from conditional-model settled flat, full calendar from native HALT/interruption, and internal transfers from PnL. Conditional support/forfeiture and genuine unpaid debt remain explicit; no actual exchange-liquidation or insurance certification is claimed.
