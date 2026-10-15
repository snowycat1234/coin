# Full-2023 native-account offline proxy with coarse-quantity sensitivity

This is a conditional offline account-model study. The implemented quantity profile is not verified exchange-native execution. XRP step 100, SOL step 1 and DOGE step 1000 are derived coarse-quantity assumptions. The reporting classification is BTC_DOCUMENT_EXAMPLE_ANCHORED_EQUAL_QUOTE_DECADE_SENSITIVITY; original frozen account/profile bytes remain unchanged.

This add-on composes with the public STATIC50_MID pilot at commit 07480c3b69654f075ce86f78f978f5bd38d8e912 and its V3 base. It includes only new eight-cell evidence and reporting helpers. The strategy, targets, execution/account engine, costs, source payloads and pilot evidence are not duplicated or changed. See PUBLIC_BASES.json for exact immutable locators and hashes. Read REPORT.md for the final nine-cell result.

## Offline checks

Unpack the public pilot ZIP separately, following its ARCHIVE.json. From this directory, with Python and NumPy:

    PYTHONDONTWRITEBYTECODE=1 python verify_saved_matrix.py --pilot-base /YOUR/traditional_2023_pilot_public_recovery_20261015_v1
    PYTHONDONTWRITEBYTECODE=1 python -m unittest -v test_saved_matrix.py

The checker validates this packet's complete file inventory and the exact public pilot inventory, unique economic-ledger arithmetic, zero terminal quantities/liability, daily returns and observed risk summaries, selected-row clocks/covariance, and summary/reviewer bindings. It never imports financial modules, constructs/advances an account, replays trades through an engine, or makes network requests. Its arithmetic checks sum saved Decimal fields; they are narrower than the retained independent source-dependent reviews.

## What each new cell contains

- RESULT.json, CASE_RECEIPT.json and OBSERVED_RISK.json: unchanged original bytes.
- ECONOMIC_LEDGER.json.gz: every actual trade-leg object and every applied account-funding object, including all original Decimal strings; complete non-event terminal snapshot state; and all non-applied zero-charge funding-journal exceptions. Duplicate fill-request snapshots, funding-event receipts and idempotency maps are omitted. Canonical JSON and deterministic gzip change formatting only. Original selected-subtree hashes and full-parent identities are recorded.
- DAILY_365.csv: exactly 365 UTC-day closes, NAV and returns, gross close/max/mean, forecast-volatility close/max/mean, forecast-budget breach counts, cash/margin extrema and closes, cumulative fees/execution/funding/turnover, and closing signed weights.
- SELECTED_MINUTE_EVIDENCE.npz: complete original 37-column rows selected by the predeclared deterministic calendar/extrema/terminal rule, their original indices and calculated past-only covariance forecast. All final 62 closes are included. PROJECTION_MANIFEST.json describes exact selection, formulas, scope, parent hashes and exported checks.
- GUARD_REJECTION_SUMMARY.json.gz: categorical counts and exact first/last original-row witnesses per documented category. These are summaries, not complete guard/rejection journals.

The eight cells remain separate even when STATIC50 and H090 have identical executed economics. Exact target identities are kept distinct. Numerical target differences do not establish independent strategies or independent alpha.

## Regenerate projections, only from exact retained parents

ORIGINAL_INPUT_PINS.json gives original relative directories, SHA256 and byte counts for every complete original file. With those exact retained files and the exact TARGETS.npz from the public pilot:

    python extract_saved_case.py --case /YOUR/original/STATIC50_LOW --targets /YOUR/pilot/traditional_three_tier_freeze_20261015/annual_2023_source_preparation_attempt003/TARGETS.npz --pins ORIGINAL_INPUT_PINS.json --output /YOUR/new_exclusive_projection

Replace the case name as needed. The extractor rejects changed parents, incomplete/noncanonical cells, wrong historical GO/preparation, nonfinite data, duplicate economic events, inconsistent duplicate receipts and changed public target bytes. It writes only an exclusive new directory. Historical GO records in this packet are provenance and do not authorize a new run.

The original full minute arrays and full account/funding/guard/rejection journals remain unchanged locally. They are deliberately omitted here. This packet cannot reconstruct all minute rows or the full original journals/snapshots. Hashes bind recorded identities; without the omitted parents, they do not independently prove the projection's original inputs. With exact public source recovery and pinned code, a reader can separately reproduce the model, but a fresh finance execution requires separate authorization and is not performed or implicitly authorized by these packaging helpers.

## Qualifications

This is seen-2023 development evidence. Funding fractions/publication/arrival and native venue filters/liquidation fidelity remain conditional. Nominal forecast-volatility budgets govern sizing/fresh openings, not a continuous held-inventory invariant. Reductions may remove hedges and increase forecast volatility. Cash comparisons and same-nominal-budget HOLD comparisons are qualified by realized and observed forecast risk. Own LOW, MID and HIGH HOLD causality addenda are preserved in reviews/. HOLD_HIGH’s 37.7204% peak and 16.5477% next-minute post-reduction risk also require the same continuous-cap qualification. HOLD_LOW’s own July 14 event is preserved in reviews/ANNUAL_HOLD_LOW_RISK_CAUSALITY_REVIEW.json: a covariance refresh raised the same midnight weights from 5.3100% to 13.9525%; the 13.9684% minute peak preceded paid reductions by one microsecond. Full coarse-lot-floor reductions left genuine sublot residuals, with next-minute risk 5.9919%, twenty zero-execution retries and five expiries. This is a material proxy/risk qualification. A useful next study is independently verified current/historical filters and predeclared finer-filter robustness, with no profit tuning.

No independent-alpha, untouched-OOS, equal-realized-risk excess, native-live fidelity or investment-performance claim is made. Exact capital binding cannot be inferred from compact rejection reasons, and observed exposure shortfall is not attributed to capital alone.

Nothing was downloaded, uploaded or published during packaging. No frozen code, target, cost, source or execution artifact was changed, and no financial engine was run.
