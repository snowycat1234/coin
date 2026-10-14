# Generated-only native adapter: CSH_BTC_GRID_REPLACE10

Status: synthetic mechanics preparation. No historical run, market download,
training, risk-parity certification, live account, or publication action occurs.
The original financial sources and the previously frozen helper stay unchanged.

## Run

From this directory in the prepared workspace:

    PYTHONDONTWRITEBYTECODE=1 python run_checks.py

This verifies the existing original financial/target/helper closures, runs fixed
unittest cases and serial generated comparisons, then writes complete account and
owner journals to `generated_journals/`. Exact prerequisites are the paths and
hashes in `FINAL_CHECK_RECEIPT.json` and `bind_sources.py`; missing/mismatched
prerequisites fail before financial execution. It installs nothing.

The runner uses one CPU, one BLAS/Polars thread, 4 GiB address-space limit,
120 CPU-seconds and 180 wall-seconds per child. The receipt reports actual costs.
Opaque session UUIDs differ across runs to prevent callback collisions; all
strategy choices and financial outcomes remain deterministic from start.

## Fixed policy and controls

- CONTROL: unchanged original CSH targets and original native terminal60 engine.
- CASH: independently implemented diagnostic control, trimming exactly10% of
  each positive original **Decimal BTC target quantity**; all other signed legs
  remain unchanged. Trimming float weights before native sizing is not equivalent
  at lot boundaries, so the independent reference transforms native quantities.
- GRID: the frozen four-level, equal-base-quantity, arithmetic Spot Grid-inspired
  policy replaces that same10% positive BTC collar only when eligible. It uses
  a frozen30 completed-daily-close range, Monday UTC decision and seven-day end;
  no optimizer, martingale, trailing, leverage change or reinvestment is added.

Pre-history clarification: if GRID is ineligible before any grid trades, its
original BTC CSH target remains intact. It does not become the CASH control.
CASH remains the frozen fixed10% trim even when GRID is ineligible. GRID rejects
zero/short BTC, unknown/singular covariance, missing/stale initial observation,
unusable range/spacing/minimum, or a replacement endpoint envelope that increases
original-target gross, per-asset, absolute-net or covariance risk.

This is an adapted perpetual policy, not a reproduction of Bybit Spot Grid,
Futures Grid or proprietary Aurora AI. Public fixed-grid replacement mechanics
motivate the signal only. Existing BASE27 perpetual fees and funding apply.
Mechanism sources and bounded111-branch dedup evidence remain in the frozen
`coin_bot_risk_matched_synthetic_20261014` package; no second grid/DCA/selector
candidate is introduced.

## One native account and causal ownership

All CORE5 positions share the original single fresh10000USDT wallet, isolated1x,
no topup, fine1e-8 quantity grid, opening10USDT minimum, closing exemption,
BASE27 fee5.5/half-spread4/slippage4bps per side, conditional raw fraction funding
scale1 and .001 previous-minute quote-volume execution capacity.

The adapter never executes an independent sleeve fill or debits a second wallet.
It observes the original engine's actual fill legs, then deterministically
allocates quantity and actual fee/friction, with a final Decimal remainder to
make allocated totals exactly equal native totals. Funding is similarly allocated
from the single native applied event. Buy initialization is paid. Price touches
cannot create ownership or realized cash. All inventory stays in account NAV.

The original engine gets one aggregate BTC order, while immutable helper order,
slot, session and fill identities bind each allocation. Native order supersession
removes the executable pending order before confirming helper cancellation.
Partial fills update only actual received quantity; cancel/expiry never clears
owned inventory. Helper identity checks happen before native finance. Repeated or
rewound native attempts fail before mutations. All original shorts are retained;
BTC becomes short only after old grid ownership is actually paid closed.

The initial grid observation must be an explicit CompletedMinute at native start
or an actual native latest completed mark, with distinct bar end/availability.
A native daily price is never mislabeled as a minute observation. The generated
start observation is100 at the toy start clock. Production source admission is
still unimplemented and cannot be inferred from caller-provided mappings.

The close hook runs after all same-clock funding and original hard-risk handling.
It reads only the original immutable tape row whose exclusive close equals that
admitted decision for capacity admission. Later eligible next-open execution
rechecks its own native prior-minute quote; that later volume may differ, causing
partial/no fills. No future volume or open is used for admission. Mixed-side grid
intents serialize actual sells first; unsubmitted opposite intents are canceled,
not netted into a free round trip.

## Admission and exits

Actual positions, existing native targets, owned grid inventory and all possible
unfilled grid buys jointly enter signed endpoint vertices, including reversals.
Gross, per-asset, absolute-net and covariance bounds are compared against the
contemporaneous original **target** lineage at actual marks/current candidate NAV
and against unchanged absolute .60/.30/.10 caps. Singularity fails closed.
Opening collateral plus actual friction is reserved against real free cash; a
reversal cannot borrow presumed proceeds from an unfilled close. Sell orders do
not free inventory exposure before paid execution. Native capacity and hard-risk
remain authoritative even after an admission check.

Weekly/sign/budget changes expire and confirm-cancel old grid orders, then use
persistent native paid reductions to settle old inventory. New sessions cannot
own old fills. A truly paid-flat and confirmed-canceled expired session is cleared;
expiry is logged once, including the helper's next-open boundary expiry. A hard
risk exit suppresses restoration of obsolete pre-breach base targets until a new
original daily decision. DOGE-only pool/data exits do not bypass the BTC trim.
Native terminal60 owns the exact sixty charged next-open exit opportunities;
zero capacity leaves a visible residual and false terminal_paid_flat.

Exact native lot/minimum expiry may leave the base marginally unfilled or another
retained asset a lot above the new target. These legitimately block grid admission;
no risk tolerance or original five-attempt behavior is relaxed to make it trade.
Weekly lifecycle tests separately validate paid-owned and already-flat renewal,
including new session activation even when subsequent admission stays a no-op.

## Evidence and remaining blockers

`FINAL_CHECK_RECEIPT.json` is the only final resource/source receipt.
`FINAL_TESTS_LOG.txt` lists final synthetic tests. `GENERATED_SUMMARY.json` records
all fixed serial CONTROL/CASH/GRID outcomes; full actual account/fill/funding,
owner, target, rejection and policy journals are retained per run. Earlier failed
runs/logs are preserved as preliminary evidence, not reported as final passes.
Most fixtures intentionally force simple target states to isolate plumbing. The
ORIGINAL_CSH fixture executes exact source-pinned original CSH function bodies
only on generated daily history, without fitting or loading historical arrays.

No historical GO or unchanged-risk claim is produced. Required later review:
real daily/minute/covariance availability and target admission binding; complete
serial paired original/candidate ledgers and unchanged costs/source hashes;
actual all-event drawdown, daily realized volatility/tails/30-day loss, gross/net/
per-asset exposure, halts/ruin, execution failure and paid terminal residual
comparisons. Target-envelope arithmetic cannot certify future or ex-post risk.
Funding-unit/publication and fine quantity-grid uncertainties remain inherited.

Snapshots expose complete final adapter ownership state for audit, but adapter
restore/fork raise explicit NOT_IMPLEMENTED_NO_HISTORICAL_GO errors. There is no
restart, split/restore or resumability claim. Real persistence/event replay and
historical admission need separate review; this minimal patch adds no production
OMS infrastructure and no original financial-kernel rewrite.
