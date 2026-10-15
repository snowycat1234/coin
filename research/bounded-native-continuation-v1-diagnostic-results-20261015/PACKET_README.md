# Full-2024 bounded continuation V1: saved diagnostic recovery

**V1 DIAGNOSTIC / SUPERSEDED. Intended-policy conformity failed.** This packet preserves completed STATIC50_MID / BASE27 B and C results as a diagnostic record. It does not establish intended-policy performance, unchanged-admission A-to-B continuation-only attribution, or a pure top-up effect.

Both cases completed 527,040 minute observations from 2024-01-01 through 2025-01-01 UTC. Their primary cash/isolated/quantity ledgers reconcile exactly. The V1 monitor nevertheless manufactured full-position paid exits during a known stale/unknown mark gap. Frozen A only blocked new risk. The first new exit intent was 2024-08-12 10:03 UTC; the first differing paid trade was 10:04:00.000001 UTC; the first differing minute close was 10:05 UTC. This happened before B's first conditional settlement.

## Observed diagnostic numbers

- B / CONTINUE_ONLY: conditional-model return 10.545535019463025%; terminal NAV 11054.55350194630240837520000000000000001 USDT. Paid net return is null. There were 352 paid trade legs and one conditional takeover row. One XRP conditional collateral-forfeiture settlement cleared the remaining position; this was not a paid market liquidation or certified native insurance. Conditional NAV adjustment: -1.150515 USDT; positive residual forfeited: 1.150515 USDT; remaining isolated collateral forfeited: 156.796962 USDT; insurance received: zero.
- C / TOPUP_THEN_CONTINUE: observed paid diagnostic return 10.468792390123087%; terminal NAV 11046.87923901230873666250000000000000001 USDT. There were 359 paid trade legs, five internal transfers totaling 571.63171980128461538461538462 USDT, no extra external cash, and zero conditional settlements.
- Both ended with zero positions and unpaid liability. The saved all-observation maximum drawdown was 6.136158775542977%. The observed C-minus-B difference is -0.07674262933993758 percentage points. It has no intended-policy or pure-top-up causal interpretation.
- The native secondary PnL bridge retains its explicit 9E-36 USDT arithmetic residual. It is not forgiven or inserted into the exact primary cashflow ledger.

## Authoritative qualification and original history

The policy-variance addendum controls interpretation over earlier generated review/admission claims. Its exact SHA-256 is 5f146314d84f48a68199d57326c6d0037d7238d2eb06b81d804ae63227854f78. Original generated reviews, ROOT_GO, case/controller receipts, comparison and progress logs remain byte-preserved for provenance, even where their claims were later corrected. Their presence is historical evidence, not new execution authority. No original output was modified or deleted.

The source-only publication is [commit cbdc3ccc55ee77f5d1773d2d72962289b59a6849](https://github.com/snowycat1234/coin/tree/cbdc3ccc55ee77f5d1773d2d72962289b59a6849/research/bounded-native-continuation-code-20261015). Its source archive uses **packaging V2**, while its financial policy remains **V1 diagnostic/superseded**. Packaging V2 does not repair the financial-policy defect. See SOURCE_PUBLICATION_REFERENCE.json and the published [V1 limitation](https://github.com/snowycat1234/coin/blob/cbdc3ccc55ee77f5d1773d2d72962289b59a6849/research/bounded-native-continuation-code-20261015/KNOWN_LIMITATION_V1.txt).

## Contents and exactness

- cases/B and cases/C: every original primary ledger record, exact-decimal compact trades and funding, every internal transfer and conditional settlement, terminal audit state, original small receipts/reconciliation/causal-quality records, monitor history, saved native summary/extrema, 366 daily summaries and 12 monthly summaries per case
- NARROW_STALE_GAP_EVIDENCE.json: eight saved minute-close financial rows each for A, B and C, plus relevant monitor entries and paid exits. It contains no full market or minute arrays. B's trade index 247, five manufactured pending exits, six resulting paid legs and first financial divergence are directly checkable. Full-prefix equality/counts remain reviewer attestations, not a new full A/B proof.
- independent_reviews: byte-exact saved B/C reviews, original generated review and correcting addendum
- original_attempt_history: original attempt001 GO, comparison, reviews, controller receipt, and both complete progress logs
- FULL_SAVED_OUTPUT_HASH_PINS.json: byte size and SHA-256 of every file in the full original B/C output directory, the relevant reviews, and four already-saved A witness sources. Hashes identify omitted data; they cannot replace it.

Compact trade/funding/transfer/settlement records replace duplicate approximate numeric fields with the original authoritative decimal_strings values and remove that redundant wrapper. Identity, timing, side, leg and other metadata are retained. Native funding metadata retains its original approximate raw-rate fields alongside exact assumed fractions; account_applied marks the 5,485 applied records among 5,490 observed events. The five initial flat/no-past-mark receipts moved no money. PRIMARY_LEDGER.json retains original ledger objects without financial-field transformations.

Daily/monthly observation intervals are start-exclusive and end-inclusive. Financial event totals use the same event-time boundaries; daily end observations are UTC midnight minute closes. Period returns chain saved float64 NAV endpoints. Minute-close extrema are reduced from the omitted saved NPZ, not inferred from daily endpoints. They differ in scope from the retained all-observation drawdown statistic. Exact event sums are calculated with Decimal precision 80; primary replay uses the source's precision 40. No account or financial model is constructed.

## Recovery limits and assumptions

Full MINUTE.npz files, full raw audit/native JSON, market arrays, full targets/rejections/guards, fill-request/operation-id maps and complete no-op history are omitted. The packet cannot recreate complete minute paths, all intra-period extrema from scratch, raw JSON formatting, scheduler/pending-state history, full source inputs, or a restartable execution state. Daily/monthly extrema have integrity and cross-period consistency checks; independently deriving them requires the omitted hash-pinned NPZs. This is a result-recovery packet, not self-contained strategy execution or snapshot recovery. The included narrow financial window cannot reconstruct complete A/B prefix identity.

This is DEV research with an uncertified coarse quantity profile (BTC 0.001, ETH 0.01, SOL 1, XRP 100, DOGE 1000), 10 USDT opening minimum notional, fixed 0.005 maintenance, and no verified historical exchange filters, native risk tiers, partial liquidation, native insurance or venue settlement. BASE27 uses 5.5 bps fee plus 4 bps half-spread and 4 bps slippage per side. Funding is RAW_AS_FRACTION, scale 1: the raw unit is unconfirmed, event-time availability is conditional, and publication is uncertified. The inherited GENERATED_ONLY policy-name label is misleading: generated_only=false and the actual historical scope is hash-pinned.

## Offline verification and saved-data reduction

With Python 3.10+ and no network or model dependencies:

    python -B verify_saved_packet.py
    python -B -m unittest -v test_saved_packet.py

The verifier checks the complete file manifest, exact primary replay and row cash identities, trade quantity/fee/friction paths, funding arithmetic, internal transfer neutrality, conditional value taxonomy, complete calendar, exact daily/monthly event totals, NAV return chains, monthly extrema consistency, and the narrow stale-gap witness. It deliberately reports intended_policy_performance_claim_valid=false and full_minute_path_recovered=false.

rebuild_from_saved.py is a data reducer, requiring NumPy and the existing hash-pinned saved files in their relative source layout. Run it only against saved files, with a new output directory. It makes compact data/history extracts; final README, verifier/tests and manifest/archive are packaging additions. It does not fetch sources, run strategy code, construct accounts, resume snapshots, or execute trades. It refuses to overwrite an existing output directory. No financial rerun or strategy code change was performed to create this packet.

The external archive receipt pins the ZIP's bytes. MANIFEST.json pins all payload files except itself. Independent packaging review and publication are separate root-controlled steps; neither is represented as completed here.
