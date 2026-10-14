# Independent native grid-adapter review

## Decision

PASS for frozen generated mechanics only. No historical GO, economic conclusion,
realized-risk parity, future-risk guarantee, production source admission, or
restart certification is granted.

The reviewed candidate is CSH_BTC_GRID_REPLACE10, using the existing shared CORE5
isolated1x account. It replaces 10% of eligible positive original Decimal BTC
target quantity. CONTROL stays untouched. CASH remains its explicit diagnostic
10% trim. An ineligible GRID session retains original BTC before grid trading;
this does not redefine CASH or imply that CASH itself is risk-matched.

Exact producer freeze: FINAL_MANIFEST.json SHA256
c24974783e50ec8b83b199e1c6b271e75fe87d58951c4d581ce53dd46ddf1a0b.
Adapter SHA256:
65277cc7fc79955792198ceaf1c300a0aac4b7c0ad461ec88d11ae1b320ed5c4.
The freeze's 59 declared files, sizes and hashes were independently checked.
Candidate and original-source hashes matched before/after acceptance.

## Verification completed

- 20 producer generated tests independently rerun and passed.
- 26 independent generated/adversarial tests passed.
- All 33 frozen serial CONTROL/CASH/GRID journals independently audited, covering
  754 native fill legs and 300 applied funding events. Per-leg quantity, actual
  fees and friction sum exactly to native journals. Each funding event's GRID
  allocation matches causally owned inventory replayed from prior actual fills.
- Original financial executable/runtime identity verified through the existing
  pinned loader; no original finance, execution, scheduler, terminal or helper
  source was edited by this reviewer. No financial patch is needed.
- The exact previously reviewed helper sources are reused, along with their
  existing 81-test review receipt, instead of rerunning an unchanged helper suite.
  Helper publication: 8d8a26a375607dfdb5f97bbaabf047a18125fd13.

Acceptance ran one CPU/one numeric-library thread, with 4GiB address-space,
120 CPU-second and 180 wall-second limits per child. Producer tests took
22.829s; independent tests 17.671s; runtime identity 0.221s; journal audit 0.073s.
Peak child RSS was 127072KiB. Detailed commands, stdout/stderr and source hashes
are in REVIEW_RECEIPT_0001.json. Only generated tapes were executed; saved target
artifacts in the original dependency closure were hash-checked, not parsed or
advanced as historical arrays. No downloads or external mutations occurred.

## Five independently reproduced findings, now fixed

The immutable archived pre-review adapter hash is
5c1e1dfc66f05b3deab88856065a7e017a3d273bb5b6d63a8e75c1cf93d7585a.
reproduce_archived_findings.py reruns all five cases against that preserved source.
PRE_FIX_FINDINGS.json records the measured failures. Final source retains focused
independent regressions.

1. Original-target envelope missing. A balanced [.2,0,0,0,-.2] hedge admitted 25
   GRID allocation legs despite zero original absolute net. Final source compares
   every actual/pending vertex's gross, per-asset, absolute-net and covariance
   risk to original-target lineage as well as absolute caps. A replacement that
   is itself inadmissible retains original BTC before trimming or grid trading.
2. Unrelated exit bypassed replacement. DOGE-only POOL_EXIT sent positive BTC19.8
   through CASH unchanged instead of17.82. Final special handling is scoped to
   BTC; unrelated pool/data exits retain their original kinds without bypassing
   BTC replacement. Both pool and data-gap independent regressions pass.
3. Obsolete target restored after hard risk. A100-to200 BTC gap caused a real
   paid reduction to18.86570758, followed by a stale DAILY_TARGET25.8390. Original
   finance rejected the increase, but policy had overridden the risk-reduced
   state. Final source suppresses stale restoration until a new daily decision.
4. Already-flat expiry stranded successor. An expired paid-flat session stayed
   active in the adapter, blocked its successor and logged1380 weekly expiries.
   Final source clears only inventory-zero/pending-empty expired sessions and
   logs expiry once. New session identity activation is verified independently.
5. Exact .99 collar boundary crashed. A49.2 preliminary budget passed helper
   opening minimums, but the actual native48.708 collar failed the second
   constructor outside its exception guard. Final source makes this an inactive
   original-target fallback without changing grid configuration or minimums.

## Financial, scheduling and causal checks

Disabled CONTROL matches the original native account snapshot, trades, funding,
rejections, breaches and every minute array across eight generated days. CASH
sign reversal matches an independent exact-Decimal native-quantity reference,
including complete account snapshots and paid journals. Float-weight trimming
was correctly rejected as an inequivalent reference at lot boundaries.

There is one fresh10000USDT account per serial arm. The sleeve adds no wallet,
capital, synthetic fill, fee exemption or funding exemption. Original1x isolated
one-way semantics, BASE27 fee5.5/spread4/slippage4bps per side, fine1e-8 lot grid,
opening10USDT/closing exemption and raw-fraction funding scale1 remain pinned.
Original DOGE shorts remain in the account. BTC shorts open only after old grid
ownership is actually paid flat. Every recorded native BTC quantity reconciles
to retained base plus owned grid, and opposing BTC ownership cannot be hidden.

Actual positions, outstanding native targets, owned grid and all potential grid
buys enter signed endpoint vertices. Other-asset pending increases cannot consume
replacement headroom. Reversals reserve opening collateral without assuming an
unfilled close released cash; pending sells retain owned exposure. Unknown,
malformed or singular covariance fails closed. The bound is explicitly against
contemporaneous original TARGET quantities at actual marks/current candidate NAV,
not a simultaneously running original account's actual ledger.

One aggregate native order owns BTC capacity. Known completed-quote admission is
causal; later execution rechecks its own original prior-minute quote and may
partially fill or fail. Independently replayed fill notionals obey the original
.001 per-symbol prior-minute capacity. Zero quotes cannot invent base/grid
inventory or consume fictitious released cash. Intent-side SELL/BUY serialization
does not book a net virtual round trip.

Stale native order, stale helper order, wrong helper side and tampered aggregate
quantity are rejected before any financial mutation. Duplicate/rewound native
attempts and duplicate paid-leg attribution fail without mutation. Native
cancellation removes the executable order before helper reserve release.
Immutable helper session/order/fill guards retain their previously reviewed
coverage. All-event funding allocations use actual held quantities and sum
exactly, with equal-clock funding completed before grid decisions.

Initial observations must be explicit timestamped CompletedMinute values or
actual native completed marks. Missing/future/stale observations fall back to
original targets. Future price/volume suffix changes cannot alter the paid
prefix. Next-week admission uses the already completed price; a future Monday
open cannot override an out-of-range prior completed mark.

Weekly/sign/budget expiry retains owned inventory and uses real persistent paid
reductions. New sessions cannot inherit old ownership. Native lot/minimum
remainders may validly leave BASE_UNFILLED_GRID_BLOCKED or fail a target envelope;
no tolerance or original five-attempt policy was loosened to manufacture trades.
The exact original terminal60 signal and all sixty exit opportunities are
preserved. The zero-liquidity terminal case remains visibly unpaid/residual,
with false terminal_cash_realized and reconciled ownership.

## Remaining gates and interpretation

The 11 exported generated GRID cases include four no-grid cases:
ORIGINAL_CSH, NEUTRAL, UNKNOWN_COV and BAD_RANGE. Seven cases contain GRID fills;
TERMINAL_RESIDUAL remains unpaid. These are fixed toy-case mechanics, not market
performance, strategy selection, annual returns or realized-risk evidence.
ORIGINAL_CSH executes source-pinned original function bodies only on generated
daily history. Strict legitimate no-op cases remain visible.

Actual .60/.30 drift can still breach after gaps; the unchanged native account
and paid hard-risk response remain authoritative. Ex-ante target-envelope
arithmetic does not establish equal future or realized risk. Later source/target/
mask/covariance/availability admission needs separate review. Any later authorized
serial pair must retain the complete original/candidate ledgers and compare
all-event drawdown, daily volatility/ES/30-day loss, actual gross/net/per-asset
exposure, halts/ruin, execution failures and paid terminal residuals. Inherited
funding-unit/publication, fine-profile and margin-tier uncertainties remain.

Snapshots are diagnostic ownership evidence. Restore and fork deliberately raise
NOT_IMPLEMENTED_NO_HISTORICAL_GO; no split/restore parity was advertised or
certified. Production persistence/event replay and historical entry points stay
outside this acceptance. A separate explicit root GO is still required.

## Reproduction

Keep the candidate, unchanged original dependencies, frozen helper and helper
review folders at their existing sibling paths. From this review folder:

    python run_review.py FINAL_MANIFEST.json

The runner verifies the exact freeze, original executable closure and prior helper
review, executes bounded generated suites/runtime verification and journal audit,
then writes a new exclusive source-bound receipt. It does not rerun the producer's
exporter or overwrite candidate files. The runner and full independent tests are
part of this review artifact.
