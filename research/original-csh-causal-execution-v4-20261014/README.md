# Original CSH causal partial/execution adapter, synthetic-only v4

46 generated tests pass: all 21 unchanged v3 regressions plus 25 integration fixtures. Final receipt: `attempts/attempt004/TEST_RECEIPT.json`. No market history, annual run, financial-engine modification, or historical GO is included.

## Integration seam

`CausalPartialAdapter(simulator, CompletedBarSource(rows)).install()` delegates the original native `schedule` and `attempt` methods. Explicit `adapter.schedule(...)` and `adapter.attempt(...)` calls are also supported. Uninstall restores the original methods. Native recovery and simulator forks are outside this synthetic certification.

Signal source rows have exactly `symbol`, `close_us`, `available_us`, and `close`. The source binds the last 31 complete daily closes for each CORE5 asset to the actual decision. Both observation and publication must be at or before that signal. The last close must equal the decision. The annual covariance is the original 30 daily returns, sample `ddof=1`, multiplied by 365. A digest binds every selected source row. Later book rows cannot change the signal binding; unavailable selected rows and missing calendars fail closed.

Signal preview never receives the next execution open. It reuses the unchanged v3 allocator and native charged preview, fixed fractions `1,.75,.5,.25,0`, original `.60` gross, `.30` asset, `.10` annual volatility, 1x isolated leverage, and BASE27 costs. Ordinary lambda-1 dispatch preserves the raw original target, including non-tick Decimal quantities. Rounding dust remains pending. Genuine native whole-lot partials and opening refusals fail closed.

A signal certificate authorizes no execution. At every native increase with a positive planned lot, the execution guard reads fresh account state, already-applied funding, current net pending targets, the current already-available opens, and remaining shared native capacity. Independent clones revalue at those available opens, charge original native fills and fees, and enumerate actual/pending corners with the source-bound covariance. Future close, mark, and volume fields from the attempt minute are not read. Native zero-lot dust is passed to native refusal bookkeeping without claiming an exposure increase or a fill.

The independently revalued risk clone uses the open as a new observation at the fill event. It does not change the live account's completed-close mark ledger. Charged risk NAV appears in corner risk witnesses; `fresh_native_NAV` records the actual live native close-mark NAV before the attempt. All fresh monetary state includes legitimate funding already applied before the fill.

A rejected guard leaves account and pending unchanged during preview: no real trades, fee debits, margin allocation, funding changes, or fill-request insertion. Original scheduler rejection journals, retry counts and expiry proceed normally after that verdict. Reductions, protective/terminal exits, floor rounding, paid closes and scheduler priorities keep original ownership.

## Evidence

- Signal GO becomes a fresh rejection after a price gap, funding at the exact open+1 tie, changed pending targets, or capacity shrink; rejected account snapshots remain exact.
- An unguarded native control accepts the same annual-volatility-breaching gap fill, demonstrating why the external guard is needed.
- Lambda-1 native account snapshots, trades, scheduler snapshots and pending targets match baseline, including long/short sign flips, non-tick dust, retries and original weight*`.99`*NAV/price targets.
- A tight-capacity sign flip preserves the paid reduction before the increase and its remaining shared budget.
- Native `advance_day` integration completes a generated 1,440-minute day with the documented causal sequence: signal, funding at open+1, attempt, later funding, completed close marks. This is generated scheduler coverage, not market history.
- Independent fresh mixed corners repeat exactly without reusing live profit or fees.
- All preserved v3 files and all 18 minimal dependency bodies are SHA256-checked before and after each test process.

`PUBLIC_DEPENDENCY_MAP.json` references immutable existing bodies without copying them. `SOURCE_MANIFEST.json` binds final adapter/run/tests and those dependencies. Every attempt includes its exact adapter/run/test inputs, source manifest, receipt and log.

Attempts 001 and 002 are preserved failures. Attempt 001 exposed a returned receipt schema conflict (`symbol` duplicated by the original scheduler). Attempt 002 exposed a fixture-only Decimal string-format comparison. Attempt 003 passed 42 tests; attempt 004 adds four edge-case fixtures and a stronger preview immutability assertion and passes 46. No economic cap, cost or fraction was tuned.

Independent review and any historical source/provider installation remain separate requirements. This package must not be treated as historical or production execution approval.
