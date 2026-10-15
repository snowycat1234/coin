Saved-only fixed D matrix comparison preparation

Scope
- Exactly the frozen 17 new DEV cells plus the already-completed original 2024 STATIC50 MID D case, for 18 displayed rows.
- No new algorithms, account construction, history advancement, market-provider calls, financial source edits, trades, strategy selection or publication.
- comparison.py imports only the Python standard library. It never loads MINUTE.npz or a market source. Its array-signature utility receives only supplied arrays and is used in tiny unit fixtures.
- The report is fixed-order rather than ranked. No winner, full-year excess against a halted prefix, return rescaling, continuous two-year account or multiplied annual return is produced.

Evidence and final gate
- Final execution requires both --authorize-saved-final and an evidence index whose parent_authorized_all17_terminal_saved_comparison is true. A final run then requires all 18 review-approved terminal rows.
- No actual 18-row snapshot has been generated during preparation.
- Partial mode exists for an explicitly requested future snapshot. Every unapproved, absent or pending cell retains null metrics and return fields; these are never replaced by zero. A partial approved halted account has only a prefix marked return, never an annual return.
- The index contains explicit SHA256-bound JSON references per cell. Small JSON references are rehashed on reading. Large audit/result/minute hashes are carried forward unchanged from independent saved terminal review, rather than repeatedly opening arrays.
- Exact source identity, original full code identity, policy identity, preparation, root approval, original source review, case receipt, terminal checkpoint and independent risk/finance review bindings remain per row.
- The reused MID case has different original receipt/code/contract wrappers. Its risk report is a separate supplementary posthoc report, never added to its original immutable case directory or mislabeled as an original frozen output.

Return taxonomy
- FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT: full required minutes, paid market flat, zero conditional settlement rows and zero debt. Only this populates comparable_paid_annual_return_fraction.
- FULL_CALENDAR_CONDITIONAL_MODEL_SETTLED_FLAT: full required minutes and declared conditional settlement. The model annual return is kept separately; it is never a paid-market liquidation return.
- PARTIAL_HALTED_PREFIX_NOT_ANNUAL: observed prefix marked return only.
- PENDING_UNREVIEWED / unresolved: no annual comparator.
- Returns use exact native decimal NAV divided by independent initial10000, with high-precision reporting arithmetic. Exact amount strings remain unchanged.

Risk scopes
- All-observation MDD: initial10000 peak plus observed minute-close marks, scheduler fills and funding. This is not a bar-high/low intraminute path claim.
- Held gross and per-asset weights, free cash, isolated margin, forecast volatility and overshoot minutes: post-transition minute-close observations.
- Separately labeled all-observation gross maximum and cash minimum can be included only from a pinned saved summary. No broader observation scope is inferred from a minute-close sample.
- Realized volatility: sample standard deviation (ddof1) of complete UTC daily simple NAV returns, including initial10000, multiplied by sqrt365 even for366-day2024.
- Forecast: held signed weights with the covariance at the last daily decision strictly before the close. Overshoot count follows frozen1e-10 tolerance; reported maximum excess is unrounded.
- Nominal tiers are not exact realized-risk matching. No posthoc rescaling or risk-matched excess is claimed.
- Costs retain fees, execution friction and signed funding separately. Internal transfers are not PnL. Settlement forfeiture, insurance support and unpaid debt have separate fields.

Strict realized-path duplicates
- Exact native projection: free_cash, unpaid_liability, positions, marks, totals, full trades and funding rows including IDs/decimal_strings, funding_events, funding_ids.
- No trade/funding operation IDs are omitted. Only scope/config/candidate metadata outside that projection are excluded. fill_requests are expressly excluded because tiny raw-target differences can create different requested quantities with identical realized fills; differing requests remain in original evidence.
- Saved equality proof must independently establish every projection field and monitor/settlement/transfer journal equality plus full37-column minute values and columns equality.
- Minute canonicalization includes original key order, dtype, shape and exact C-order raw bytes for values and columns. NPZ ZIP-container bytes alone are not a canonical numeric-path test. No rounding, tolerance, resampling or market-input hashing substitutes for output paths.
- Existing reviewer proof/addenda are reused. Matching NAV/MDD/returns alone never establishes equality, and duplicate paths are never counted as independent strategy confirmations.

Files
- comparison.py: gated saved-only normalizer, taxonomy, signatures, JSON/CSV/text writer.
- test_comparison.py and UNIT_TESTS.txt: 23 tiny fixture tests, including conditional/partial/pending exclusion, exact decimal changes, IDs, dtype, columns and path classification.
- COMPARISON_SCHEMA.json: prepared output/schema definitions.
- report_reused_mid_risk.py: authorized separate supplementary saved-only reporting script. Reads the old saved minute output once plus its exact original bound target/covariance preparation; uses frozen annual_reporting.py function, without invoking financial or source-preparation functions.
- supplementary_reused_2024_STATIC50_MID/: separate saved-only held-risk report, binding and small exact metrics; pending independent review until a separate reviewer receipt is provided.

No publication is performed by this directory. Future public packaging must remain compact: small reports/code/reviews and hash-only large-array references; never full local archives or minute arrays.
