# Independent review: bounded H090 synthetic prototype

## Verdict

PASS for the exact V2 source and generated-only component tests. Historical integration remains NO_GO. This review does not establish a working historical CSH/Martingale candidate, stable returns, a safe loss ceiling, or calibrated ruin/liquidation probabilities.

Reviewed source freeze SHA256:

`af840b51613335a83d5badd8454e0861863e6fb20dda136d2054457ffeb1cdf5`

The designer's 34 unit tests, 43 independent adversarial tests, and fixed generated toy runner all passed. Before/after source hashes were identical. Each check used one CPU, one numerical-library thread, a 4 GiB address-space limit, a sampled 2 GiB RSS stop, 60 CPU seconds and 120 wall seconds. Maximum sampled RSS was 36,306,944 bytes. No historical wallet, market-data read, download, exchange action or publication was performed by this review.

The initial V1 review and exact 39-test reviewer source are retained separately as attempt001. They are prior evidence, not the current publication target. The final V2 receipt is attempt002.

## Fixed scope checked

- Fresh shared wallet: 10,000 USDT; CORE5 symbol order.
- H090 target gross 0.90, absolute net intent cap 0.90, asset cap 0.30, generated past-covariance target 15%; isolated 1x.
- Commitment envelope: 9,000 original USDT maximum, retaining 1,000 uncommitted. The candidate reserves 8,000 for the CSH ownership allocation and 1,000 for the finite BTC program.
- Separate unchanged-account dry-run guard: at most 8,500 actual isolated margin, with at least 1,000 actual free cash before/after an increase. Later funding/losses can breach that floor; they are neither rolled back nor rescued. Explicit reduce-only fills remain eligible below the additional floor.
- Exact finite order margins: 150, 187.50, 234.3750 and 292.968750 USDT. Total 864.843750; fee/funding reserve 135.156250 inside the same 1,000 allocation. Exactly three maximum adds, one long-BTC non-refillable program, no renamed restart or profit compounding.
- The 1.20 gross / 2x stage is rejected and deferred.

## Financial source boundary

The original Decimal account file is pinned at `ffa57a4c3c3b031945fcbc5db429d8b5e6ef06e880a8a577265836602ad55110`. The separate vendor copy differs at exactly one validation bound: gross configuration maximum 0.60 becomes 0.90. Its default remains 0.60. All accounting methods are byte-identical. The independent review also matched complete original/extended snapshots after generated mixed long/short fills, signed funding, mark movement, partial closes and full closes under original caps.

ExecutionContractV2 is byte-identical at `b7fc110d84240233611e2f7e7360c1b7cc5c92308f842a796560964db33f97d1`. Its original timing and cost arithmetic remain in use. Its canonical 0.60 gross / 10% volatility fields remain unchanged and reject an H090 configuration. They cannot certify the new risk descriptor.

## Defects found and resolved before final acceptance

1. Released reservations could initially be reused through a new owner name. Retired allocations now continue consuming the original commitment cap. A full 8,000 + 1,000 allocation remains 9,000 after retirement and a renamed extra allocation rejects.
2. The initial envelope saw only scalar actual/pending gross. It now checks complete signed actual CORE5 notionals and owner/per-symbol pending increases, preserving opposing sleeve gross rather than netting it away. Omitted and explicit None inputs fail closed.
3. Finite-plan helper parameters initially admitted other margin geometries. The candidate now enforces the exact frozen 150 × 1.25 geometry and fixed program identity.
4. The initial completion helper accepted an inflated caller-supplied rounding bound. Such completion totals now always reject. Actual account-bound journal receipts accumulate partial margin under one order index; the final remainder derives from the pinned 1e-8 quantity step and actual fill price. Replays are idempotent and cannot migrate to another add.
5. CapitalGuard's positional fill ID extraction was off by one. The corrected guard preserves original duplicate replay and conflicting-identity rejection after a later cash-floor breach.
6. V1 preflight could proceed without a freeze manifest. V2 requires the complete V2 source-hash set and rejects absent/invalid manifests and source drift. Independent cold-copy tests verified missing freeze, changed protocol and changed policy rejection. A historical-path launch argument also rejects without reading it.

No implementation files were edited by the independent reviewer. The designer made the fixes and issued the exact final freeze before the final run.

## Adversarial results

The independent suite checks actual capacity-partial fills; small fully filled child requests that are still partial margin-program orders; duplicate/order ownership; wrong-symbol, short, closing and over-budget receipts; terminal locks; just-below/above 8,500 margin; rejected-fill nonmutation; free-cash-floor increases/reductions; fee/funding identity and non-replenishing credits; actual/pending per-symbol caps; opposing sleeves; marked cap drift; and 80 generated covariance cases. The controller observes only the last 30 generated return rows and never certifies historical timestamp availability.

Selected generated counterexamples:

- A correlated adverse gap leaves NAV 7,589.199296 and actual gross weight about 0.990882, exceeding the target cap 0.90. Zero capacity leaves all five inventories outstanding after 60 terminal attempts. The cap is not silently clipped into compliance.
- A funding drain leaves free cash 794.319296, below the 1,000 increase floor. Costs remain in the account and further increases are blocked; no top-up is invented.
- An isolated short gap produces LIQUIDATION_REQUIRED_HALT while total NAV is 6,824.399296 and free cash 1,994.319296. A slightly larger gap produces BANKRUPT_HALT while total NAV remains 6,789.199296. These are not whole-wallet economic ruin and are not certified Bybit liquidation fills.
- An independently generated completed finite BTC margin program gaps from an execution price of 100.08 to a mark of 50. Its net loss is 433.243198500817 USDT, beyond the 200-USDT exit signal. Sixty zero-capacity reduction attempts retain the exact 8.64152425 BTC quantity. A stop signal cannot guarantee an exit price or loss ceiling.
- A benign paid five-asset terminal produces NAV 9,978.4, not a free 10,000-USDT exit. Low capacity leaves unpaid residuals after 60 attempts. The finite shared-cash fixture has actual isolated margin 8,470.923748266952 and free cash 1,524.4172436715; its Decimal accounting bridge error is 7e-37, a rounding-level residue rather than invented capital.

These are constructed counterexamples and arithmetic checks. Their frequencies are not probability estimates. Sampled endpoint drawdown is not a full-path historical maximum drawdown.

## Matched control and native gate inventory

The protocol specifies CSH_H090_CONTROL: fixed 1.5× original causal CSH targets followed by H090 concentration, covariance and capital gates, without refitting original signals. CSH_MART_FINITE_REPLACE10 must use the same global H090 envelope and retain its explicit 8,000/1,000 ownership allocation. Neither control nor candidate has been executed on historical data by this package. The generated four non-BTC holdings are fixture inventory, not CSH signals.

NATIVE_GATE_REVIEW.json verifies the five native-map file hashes and expands the bounded relevant source inventory with seven original companion files. Remaining unchanged gates include:

- Original PerpetualConfig 0.60 default/validation and baseline metadata.
- NativeDailySimulator.advance_day 0.60 gross input guard, account/cost factory binding, config-driven reductions and original reduce-first shared-capacity execution.
- public_sma_perpetual signed_risk_weights and fixed_targets 0.60 sizing / at most 10% volatility.
- ExecutionContractV2 canonical baseline risk identity.
- Original directional RULES baseline risk descriptor.
- Original companion risk_budget constants/input/post-risk assertions, portfolio default gross and checks, compatibility signed_risk_weights, explicit CSH 10% calls, original .6/K target sizing and per-arm .60 validation, and original-functions baseline descriptors.

This is an inventory of relevant pinned code, not exhaustive content deduplication across every branch ancestor. None of these native/companion files was changed or bypassed by this review. A vendor config validation extension cannot by itself integrate H090 into the native engine.

## Required before historical readiness

1. Separately reviewed H090 target/controller, descriptor and account/cost-factory bindings, with exact original signal/expert parity where required. The shrink-only toy covariance helper is not a reviewed substitute for every original risk-matching allocator.
2. An actual CSH/finite-program ownership adapter and atomic program-specific admission before committing fills. Receipt validation after a fill is not itself that admission gate. Proposed order margins, expected opening/closing fees, actual funding debits, pending ownership and direction locks must reconcile to one shared account and reserved allocation.
3. Combined covariance and concentration checks connected to actual decisions. Account/CapitalGuard alone do not enforce the 15% covariance target or owner reservations.
4. Original shared per-symbol capacity, causal source availability, reduce-first execution, persistent paid exits, terminal60 and snapshot/replay parity. The small fixture scheduler is not a NativeDailySimulator adapter.
5. Historical source/calendar/profile admission, explicit funding-unit assumptions, complete required deduplication and an independently reviewed historical launch authorization. Closed holdouts remain closed and existing runs are not duplicated.
6. Separate exact public-safe transport/cold-restoration verification if the package is published. This review ran against the local pinned original code; it does not certify an unpublished portable wrapper or carrier.

The safe interpretation is a reviewed source-and-synthetic preparation package with concrete failure examples. Long-term viability, stable APR, predictive AI and future ruin/liquidation odds remain unevaluated.
