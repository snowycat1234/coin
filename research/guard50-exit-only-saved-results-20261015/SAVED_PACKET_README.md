# Saved D GUARD50_EXIT_ONLY results: adaptive 2024 development evidence

This is a distinct saved-results recovery packet for one finished full-2024 STATIC50_MID BASE27 D run. Source code publication is referenced separately. It contains no account constructor or financial simulation entry point. No historical account, market advancement, financial rerun, source download, live order, Library operation, or strategy-code change was performed to prepare it.

## Result and taxonomy

- Initial simulated wallet: 10,000 USDT
- Terminal paid-flat NAV: 11,625.3968100935644481993 USDT
- Paid net return: 16.253968100935644481993%
- Saved all-observation MDD: 5.891240783337448%
- 298 actual paid market trade legs within the offline model
- Three genuine Guard50 warning intents, all closed through charged market fills; zero renewals
- Zero internal transfers, conditional settlements, unpaid liability, insurance support, or paid liquidation events
- Fees: 28.26320377416800 USDT; embedded execution cost: 41.111289280 USDT; signed funding: -140.69649685226755180070 USDT
- D controller succeeded, child exit 0. The older B serial-controller exact100 failure is retained only as B history and does not apply to D
- Every-event native40 cash/debt/quantity/basis/margin/native-total arithmetic verified; strict100 stored-delta terminal errors all zero
- The secondary native PnL bridge residual 1E-36 USDT is retained exactly. It is not cashflow and is never silently zeroed

D was chosen after observing corrected B/C 2024 outcomes. This is an adaptive development comparison, not independent out-of-sample validation. No locked/holdout or 2025 source was read. The single fixed MID BASE27 year establishes neither robustness nor future profitability nor long-term APR.

## Saved comparison

The independent B/C/D comparison and exact prior B/C receipts are retained, without duplicating the B/C archive. B's 8.140378314267891803966% is a conditional-model settled-flat return with two forfeiture settlements, not a paid liquidation return. C's paid-flat return is 5.877740661483466886176%. D-minus-B is 8.113589786667752678027 percentage points; D-minus-C is 10.376227439452177595817 percentage points.

D-minus-B measures the fixed paid-exit overlay. C-versus-D compares different warning-response packages, not a pure internal-transfer increment. The exact saved B/C public reference is commit 832aa1fc4d3c2d941060d7b5b0f9080344539637, linked in B_C_PUBLICATION_REFERENCE.json.

## Retained evidence

- Authoritative decimal financial ledger, all trades, all funding observations with explicit account-application flags, terminal state and reconciliation
- Exact empty transfer, settlement, and liquidation journals
- Exact warning monitor and mode journals
- 366 daily and 12 monthly NAV/cost/exposure/extrema summaries
- Exact controller, root GO, source preparation, terminal checkpoint and independently reviewed finance/arithmetic receipts, all hash-bound
- Four selected B and D minute-close rows each around the first warning, its exact warning monitor and paid SOLUSDT close, and independent full-prefix review
- The retained prior SOLUSDT minute close has equity 127.65376128 USDT above half the isolated balance 255.19488064 USDT; the warning minute has equity 125.45156918 USDT below that fixed Guard50 threshold. These are saved float64 witness observations
- The first warning was signaled at 2024-03-16 05:37:00 UTC; the 2-SOL paid close occurred at 05:38:00.000001 UTC, with a 0.21120382800 USDT fee. The first differing financial minute close is 05:39:00 UTC
- The independently reviewed pre-divergence equality comprises 109 trades, 1,125 funding rows, and 108,338 byte-equal minute rows. The complete byte prefix is omitted and cannot be re-proved from four selected witness rows

FULL_SAVED_OUTPUT_HASH_PINS.json pins original source bytes; EXACT_COPY_SOURCE_MAP.json maps byte-exact copies. DERIVED_SOURCE_BINDINGS.json binds retained canonical reductions to the exact omitted parent files. Hashes cannot restore missing bytes. All source originals were re-hashed after packaging without changes.

## Offline verification

From this directory, run:

    python verify_saved_packet.py
    python -m unittest -v test_saved_packet.py

Only the Python standard library is required. The verifier checks manifest files, exact original-copy pins, GO/code/source/review identity, report and comparison semantic binding, controller taxonomy, complete journals, every native40 event, strict100 arithmetic, warnings, funding assumptions, daily/monthly cost and exposure aggregates, and descriptive asset attribution. Deliberate-corruption tests call semantic checks without relying on the manifest hash gate.

rebuild_from_saved.py additionally requires NumPy and the separately retained workspace originals. It only reduces saved data, refuses to overwrite an existing packet, and never launches a financial model. It is not a cold historical reproduction route; the omitted market/source files remain required.

## Recovery limits and assumptions

The full minute arrays, market arrays, full account/native exports, target/rejection/fill-request/idempotency/no-op histories, and general guard history are omitted. The exact warning journals remain included. Daily/monthly extrema and exposures are float64 reductions; complete paths and intraday ordering cannot be recovered from them. Saved all-observation MDD/exposure maxima include fills and funding observations and cannot be regenerated solely from these period summaries.

The offline model assumes fixed MMR 0.005, coarse uncertified research quantity filters, causal minute-close marks, and BASE27 friction. Funding RAW_AS_FRACTION uses scale 1 with unconfirmed units and conditional event-time publication. Native venue risk tiers, filters, fills, latency, insurance sufficiency, partial liquidation, ADL, intraminute prices and funding publication remain uncertified. No restart/resume or snapshot equivalence is certified.

SOURCE_PUBLICATION_REFERENCE.json records the D source publication state. Packaging itself performs no publication; this candidate awaits an independent packaging review. Publication does not transform development evidence into OOS validation or certify venue execution.
