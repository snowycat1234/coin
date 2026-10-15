# Bounded causal MARK overlay: source-only prototype

Status: generated-only implementation, not independently admitted. No actual 2022 overlay, source normalization, source erasure, Account/genesis, provider/history/claims, financial replay, or publication was performed. No main or frozen baseline file was edited.

## Scope and original evidence

The actual pre-existing July 2022 missingness is **27 MARK asset-minutes, 11 distinct original minute-OPEN clocks, 8 asset-specific runs**: four ETH single-minute runs, one ETH seven-minute run, SOL six, XRP five, DOGE five. These are not 27 independent singletons.

`evidence/EXACT_JULY_MARK_GAP_ALLOWLIST.json` is an exact byte copy of the source author's frozen metadata. `evidence/ORIGINAL_MARK_Q3_RECOVERY.json` preserves the original published monthly/daily genuine-source attempts, including five official daily confirmation ZIP identities, original hashes/bytes/URLs, and zero added rows. `evidence/FULL2022_GAP_TAXONOMY.json` retains the annual source classification without changing its prior statuses. The original receipt's public commit and URL are recorded in the exact allowlist. All three exact byte identities are in `EVIDENCE_PINS.json` and hard-pinned in `metadata_binding.py`.

These receipts establish provenance of the earlier genuine attempts. The July raw originals have not been restored/revalidated in this phase; metadata linkage does not certify current missingness, source arrival, or event impact. No URLs were requested here.

The denied ETH February 2022 **40,320 TRADE minutes** are a full monthly transport blocker and never an imputation target. H1 ETH-Feb, alternate copies/routes, fapi, 2025 part004, holdouts, and all unapproved source downloads remain closed.

## Clocks and exact causal policy

Actual missing timestamps are copied verbatim from the original `missing_open_ms` identities. They identify minute BAR OPEN, not a close or event time. The separately recorded nominal completed-minute boundary is OPEN + 60,000 ms; this does not certify historical arrival. The generated input contract explicitly distinguishes OPEN, raw inclusive CLOSE (OPEN + 59,999 ms), completed boundary, actual supplied availability, and installation. Ambiguous or shifted mappings fail.

For each approved generated missing minute, the evaluation clock is its own completion boundary. Select the latest earlier genuine selected MARK observation completed before that target and both available and installed at or before the evaluation clock. Later snapshot time cannot revise the original estimate. A missing/invalid/nonpositive anchor fails closed. An unlisted intervening gap or an anchor spanning more than seven missing minutes fails closed.

Copy the exact input decimal price string, including its original representation. There is no financial rounding, epsilon, curve fitting, interpolation, future value, fabricated OHLCV, trade price, or volume. Every consecutive missing minute keeps the original genuine anchor provenance. Estimates never become genuine observations. A present genuine target rejects overwrite, even when delivered later. Genuine recovery is untouched and retains its original source availability/installation; no synthetic fresh source timestamp is introduced.

Each returned frozen overlay record embeds its missingness proof and original genuine-anchor provenance. A separate frozen quality sidecar marks `UNKNOWN_OR_DERIVED`, blocks source eligibility for new increases/topups, and flags funding, trigger, and execution mark valuations. The method is `ESTIMATED_CAUSAL_PREVIOUS_GENUINE_MARK`, never DIRECT. Original anchor age, close/completion, availability, installation and freshness clocks remain visible. Native intent lifecycle/trading logic is not implemented or changed here. No estimate can certify liquidation or no liquidation.

## Pure API and hard scope boundary

`build_generated_overlay(observations, requested_holes, as_of_ms=...)` takes explicit generated genuine observation records and an exact subset of the immutable synthetic allowlist. It returns a new immutable overlay, embedded provenance, quality sidecar, per-record commitments, policy commitment and deterministic batch commitment. It has no I/O or financial adapter. Inputs are unchanged. At most 27 rows are returned.

`fixture_allowlist.json` and the in-code tuple use synthetic `FIXTURE_*` symbols and 2001 clocks, disjoint from all actual symbols and actual 2022 timestamps. Altered proof, missingness, duplicate/conflicting identity, unlisted hole, wide/full-month gap, TRADE, volume, OHLCV, derived anchor and real symbol are rejected. There is no authority flag, fake-historical flag, generic fill-any-gap API, real-data builder, or switch to enable actual application.

`validate_actual27_metadata_bytes(original_receipt_bytes, exact_allowlist_bytes, taxonomy_bytes)` is a separate pure byte-identity/metadata-linkage validator. It returns only a metadata report, not price estimates or repaired rows. `ACTUAL_METADATA_BINDING_VALIDATION.json` records 0 actual price values loaded and 0 actual overlay records created.

## Weak past-only sensitivity evidence

`build_generated_past_only_sensitivity(batch, observations)` uses exactly the last two genuine selected MARK point observations available/installed by each target clock. Their min/max is a fixed, untuned, weak descriptive reference range. It is **not a guaranteed bound on the missing/future price, robust stress guarantee, probability statement, or financial safety evidence**. The primary estimate remains previous-genuine carry. Fewer than two prior genuine observations leaves sensitivity PENDING. Endpoint text and original source availability/installation are preserved. Future perturbations cannot change an earlier reference range.

This is not a source of authority to admit or trade on estimates. Actual sensitivity admission remains blocked pending source and saved-event evidence. Quantity and cashflow sensitivities are PENDING; no risk or liquidation conclusion is computed.

## Saved-event impact audit

`audit_saved_generated_events(batch, saved_events)` only classifies supplied, saved fake records in seven categories: actual-position analogue intervals, fills, eligible opens, funding, Guard50, native risk, terminal. It never creates an event, position, account, order, fill, or cashflow and performs no financial arithmetic.

For non-position events, only the saved explicit `mark_reference_open_ms` maps a dependency. A coincident timestamp alone does not infer a strict-prior/at-boundary scheduler rule. Unmapped saved events stay visibly unmapped. Position intervals are start-inclusive/end-exclusive. Actual positions/fills/funding/risk/terminal overlap, quantity sensitivity, and cashflow sensitivity always remain PENDING actual saved evidence. No row claims negligible impact.

A later separately authorized audit must:
1. Revalidate genuine monthly/daily originals and confirm the exact original missing cells and genuine anchors, source-clock semantics and availability. Never erase absent source cells or rewrite raw CSV/NPZ.
2. Preserve source-only overlay/provenance/quality separately; retain all original source bytes, genuine attempts, recovery, UNKNOWN blocks, and native intent lifecycle.
3. Map only saved actual positions, fills/eligible opens, funding, Guard50/native-risk/terminal clocks to their exact original mark dependencies, including boundary strictness, latency, and recovery.
4. Identify every affected mark valuation. Compare primary carry with the weak two-prior-genuine reference anchors only as labelled sensitivity inputs. Missing evidence or undefined sensitivity remains blocked. No hindsight choice or financial safety certificate is allowed.
5. Obtain independent source/method review and the existing source/admission/financial gates before any actual application or scheduler work. This package grants none of those gates.

## Verification and reproduction

No dependencies were added. Use the existing Python with bytecode disabled on CPU0 (CPU1/8 are alternative light-test lanes; CPU6/7 are reserved):

    taskset -c 0 coin_partial_restore_20261014/.venv/bin/python -B causal_isolated_mark_overlay_20261015_v4/verify_source_only.py

`GENERATED_TESTS.log` contains 39 generated tests. Prefix/per-record commitment invariance, future perturbation, causality and availability, seven-minute anchor provenance, genuine recovery, exact representation, no mutation/overwrite, missing anchor, duplicate/conflicting identities, forbidden gaps/fields, OPEN/CLOSE boundaries, unknown quality, deterministic replay, past-only descriptive reference ranges, and saved-fake event mapping are covered.

The isolated runtime opens no files after imports and rejects any file-open, network/process attempt or call into another workspace source/financial module. All four counters are zero. The wrapper separately checks metadata identities and hashes 14 explicitly listed frozen original/code files before and after tests. These are byte-hash reads only, with zero archive decompression and zero historical price-row parsing. `PROTECTED_ORIGINALS_BEFORE_AFTER.json` proves those named files unchanged; it does not claim to hash the entire workspace. Originals include existing 2021/2023/2024 source archives, the five December2022 MARK originals, original source metadata, and frozen baseline source code.

`GENERATED_EXAMPLE_OVERLAY.json` contains generated prices only, clearly labelled, and is not an actual 2022 result. `VALIDATION.json`, `DEPENDENCY_PINS.json`, `EVIDENCE_PINS.json`, and `DELIVERABLE_PINS.json` provide exact execution and artifact pins. All metadata uses portable relative paths; private absolute prefixes are omitted.

## v2 independent-review correction

The first source-only checkpoint remains unchanged in the sibling v1 directory. Independent review identified that the saved-fake event audit checked commitments and scope without validating every exported overlay provenance field. Unkeyed commitments are integrity hashes, not authentication. A forged/rehashed malformed record could therefore receive an audit receipt.

v2 validates target OPEN/inclusive CLOSE/completion/evaluation, genuine anchor completion/availability/installation ordering, exact age/freshness, approved <=7-minute missing run, portable source IDs/hash, and positive finite decimal text before event audit or sensitivity. A regression recomputes all public hashes for18 malformed record variants and requires rejection. Actual application remains absent, as in v1.

## v3 subset-anchor correction

Independent review additionally found that a declared genuine observation at a frozen original missing cell outside the requested output subset could reset the anchor inside a multi-minute missing run. v3 rejects genuine declarations at every exact known missing fixture cell, whether requested now, unrequested or future. Exported/rehashed overlay batches also cannot name a frozen missing cell as the genuine anchor. True same-cell source recovery would need separately revalidated source evidence and a separately reviewed API; this frozen contract has no such route. v2 remains unchanged.

## v4 strict identity and shared-provenance hardening

The author additionally checked exact Python input types and cross-record anchor coherence. v4 rejects numerically equal float timestamps and non-boolean/non-string identity fields rather than relying on dataclass equality. The saved-fake audit rejects rehashed batches that give one shared genuine anchor conflicting price text, source identity or availability. Regression tests cover these cases; v3 remains unchanged. These are generated-input validation corrections, not actual source application or authentication guarantees.
