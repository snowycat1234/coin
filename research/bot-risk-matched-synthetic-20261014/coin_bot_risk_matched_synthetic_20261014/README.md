# CSH bot-mechanism research: synthetic-only, risk-matched line

This is one fixed mechanism-inspired candidate, **CSH_BTC_GRID_REPLACE10**. It
uses the publicly described fixed-range grid buy/sell replacement mechanism as a
long-only BTC target sleeve inside the **existing isolated 1x perpetual CSH
account**. It is not a Bybit Spot Grid, Futures Grid or Aurora AI reproduction.
Grid parameters, initial sizing and causal freeze rules here are transparent
research choices, not an inferred proprietary AI algorithm. Historical wallets,
provider data downloads, native execution adapters and public publication are
**NOT_RUN / NOT_IMPLEMENTED / NOT_AUTHORIZED in this stage**.

## Run generated tests only

From this directory:

    python run_checks.py

This runs the fixed unit suite and generated toy fixtures with a one-CPU,
60-second-per-command wall limit, 60 CPU seconds and 512MiB address-space limit.
The code is stdlib-only. There is no market-loader argument, account key,
network client, live order path, historical CLI or optimizer. Every explicit invocation writes a new exclusive receipt and preserves prior
receipts. The final source-bound suite includes stale/future price, callback
identity/deduplication, monotone-clock, fixed-session-expiry, strict-schema and
confirmed-cancellation/reservation regressions.
The generated toy fill callbacks are demonstrations of policy state transitions,
not executable fills or economic results.

## Fixed candidate, controls and causal schedule

- Original CSH STATIC50 targets are the baseline lineage. Their financial engine,
  shared-capital wallet and original remaining long/short exposure stay unchanged.
  The exact archive/code/source identities must be supplied and independently
  checked before any future adapter. The current funding-rank pair is not rerun.
- CSH_CONTROL: untouched original route, full 10,000USDT initial equity.
- CSH_CASH_REPLACE10: remove exactly the same 10% of the **positive original BTC
  CSH target** and retain that budget as cash. This distinguishes cash de-risking
  from the grid mechanism. It is not a separate extra-capital account combined
  with the first arm's PnL.
- CSH_BTC_GRID_REPLACE10: replace that same slice with one BTC grid sleeve. No
  added capital, funded sub-wallet, negative-BTC override, leverage or short
  sleeve. Original CS short targets on other coins are retained and risk-checked.
- Only Monday 00:00UTC may start a new session, using the prior 30 completed daily
  closes available at the decision. Candle end and logical availability are
  separate fields; the newest complete candle and its availability may be at
  the decision, and each must be no older than24h. This is an explicit synthetic
  admission rule, not an inferred native timestamp/extra-day-lag convention.
  The later adapter must map actual source availability without adding or
  removing a day of lag. L=min(close), U=max(close), four arithmetic
  intervals. If history/masks/price/covariance are unknown, current price is
  outside (L,U), fee-aware spacing fails or opening lots cannot meet10USDT,
  the session is inactive. No alternative levels, symbols, windows or fallback
  recipes are selected from results.
- Quantity per slot is fixed for the session, with all four potential inventory
  slots at U plus one-sided BASE27 debit fitting the funded replacement budget.
  This conservative allocator is our declared choice. Profit is not reinvested;
  quantities never double, move the range or increase to recover losses.
- Initialization above the current price is an explicit paid buy. A crossed
  completed-close level creates an intent for the next eligible open; only an
  actual fill callback with immutable instance-nonce/session/order ID, side and unique fill ID
  replaces its order. Duplicate or obsolete callbacks fail without mutation. This is a conservative market-intent
  adaptation, not an optimistic limit-touch fill simulator.
- Outside the range, new grid orders stop but owned inventory remains marked.
  The helper fixes session_end=start+7days and automatically expires new intents
  at that clock or when their next eligible open reaches it. Initial and later
  prices are timestamped completed-minute observations; future/stale/conflicting
  observations and reversed fill/cancel/expiry clocks are rejected. Session IDs include a new UUID
  instance nonce; this is identity entropy only, never randomized strategy
  parameters. Native restart/persistence binding is still unimplemented.
  At weekly expiry, request cancellation, retain pending orders/reservations until
  original-scheduler confirmed-cancel callbacks, and request an original paid close. A
  new session cannot start until the old sleeve is actually flat. At a daily
  target/mask/budget decrease or hard-risk breach, cancel buys and use original
  reduction priority/persistence; never silently remove inventory. The exact
  financial/native scheduler integration of these rules remains unimplemented.

## Risk matching is a gate, not a promise

The pure intent arithmetic helper checks supplied unfilled buys with retained strategy legs and
already owned inventory. Sells release no budget before they fill. Opposing
strategy legs cannot erase gross risk. All outstanding-fill vertices must stay
within both original baseline contemporaneous envelopes and absolute .60 gross,
.30 per-asset and .10 causal covariance-vol limits; absolute net exposure cannot
exceed the original baseline. Supplied free-cash, valuation NAV, reserved notional and .001 prior-minute quote
capacity are checked jointly across all sleeves; retained target vectors must
match the fixed replacement lineage and pending buy notionals must be funded.
These caller-supplied arithmetic checks do not establish an actual shared wallet.
The helper always returns allowed=false and NOT_CERTIFIED_NEEDS_NATIVE_BINDING
even when math_valid=true, because no native snapshot/adapter is bound. These strict rules may make some hedged states
ineligible. Singular/unknown covariance is inconclusive in this small skeleton,
not fabricated zero risk. No rescaling of realized equity paths is permitted.

A future candidate must preserve the exact native contract: fresh independent
10,000USDT arms, isolated1x/no-topup, full CORE5 order, BASE27 fee5.5/spread4/
slippage4bp per side, raw-fraction funding scale1 conditional, fine1e-8 assumed
lot grid, opening10/closing exemption, original hard-risk and terminal60 paid
exit. Original source/clock/capacity/masks and funding limitations remain.
This is a perpetual emulation, so all three arms pay the same perpetual costs
and actual conditional funding; there is no spot fee or funding exemption.

**Target caps do not establish equal realized risk.** A future full-ledger pair
must pass strict nonincrease of minute maximum drawdown, daily realized annual
volatility, daily95% expected-shortfall loss, worst30-day loss, maximum/mean
actual gross, maximum absolute net, maximum per-asset gross, halt/ruin counts,
unfilled-risk counts and terminal residuals. Actual .60/.30 exposure and .10 vol
limits apply even if the original control overshoots them; 62.33% actual gross
will fail rather than be called equal-risk. A halt or unpaid/partial/residual
ledger is never a full-year cash return. Unequal prefixes require descriptive
common-prefix reporting, not an annual noninferiority claim. The metric helper
validates schema, literal booleans and the matching original-engine contract, but
caller-supplied reports are still not verified native evidence. Non-worsening
numbers return NOT_CERTIFIED_NEEDS_NATIVE_BINDING, never a risk-match PASS or
guaranteed future safety. A later independently reviewed adapter must verify
actual complete ledger/source/clock identity before any observed-risk conclusion.

Net paid PnL and its price/fee/friction/funding attribution are separate economic
endpoints, after risk gates. All fixed controls, inactive periods, stopped and
losing cases must be retained. A profitable closed grid cycle with a floating
inventory loss can have negative total PnL: toy fixture +5 realized, −40 floating,
−35 total. It cannot be reported as +5 strategy performance.

## Future integration and stopping condition

A later adapter must compile sleeve intents into the reviewed original target
and scheduler APIs and receive actual original-engine fills, funding, masks,
marks, pending orders and account halts. It must first confirm paid reductions
free replacement collateral, account/sleeve attribution, one-way semantics,
shared capacity and persistent reductions. It must not modify financial-kernel
source, costs, margin model, lot assumptions or terminal semantics to make the
candidate pass. The current pure functions are not that adapter.

Only synthetic preparation is allowed now. Later historical source preflight,
immutable source/target identity, independent adapter review and a separate
explicit GO are prerequisites. Seen2021/2023/2024/2025 are development periods;
2021 provenance and2022 real-mark gaps remain blockers. Locked2026 March–September
and unknown reserve/holdouts stay closed. A future finite test should cover all
predeclared eligible development years regardless of the first outcome, never
select a period or reparameterize the recipe. Stop the recipe on risk failure;
do not sweep grid count, range, weight, selector or exit rules to rescue it.

See DEDUP_EVIDENCE.json, OFFICIAL_SOURCES.json, ADAPTER_CONTRACT.json and
SOURCE_INTEGRITY.json for bounded audit evidence and exact integration limits.
