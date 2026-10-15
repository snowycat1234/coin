# Full-2023 STATIC50_MID pilot: minimal public recovery add-on

Read REPORT.md first. This add-on preserves the unchanged reviewed annual entry, protocol, controller, reporting code, tests, preparation attempt003 and the saved pilot. It adds transparent 365-day and selected-minute exports plus complete losslessly compressed synthetic account/audit records. It does not contain the 60.6 MB full-minute matrix or the twelve monthly market payloads. The full original records remain retained locally.

Only STATIC50_MID is covered. The other eight annual cells belong to a separate execution decision and are absent here. The included historical GO is provenance, not permission to start another run. Nothing in this package was uploaded or published by its packager.

## Read and check the compact evidence

Python with NumPy is sufficient; the published V3 requirements pin the reviewed environment. From this directory:

    python verify_saved_pilot.py

This checks every inventoried file, lossless gzip parent identities, saved trade/funding cashflow arithmetic, daily NAV/return/risk summaries and selected-row covariance calculations. It never imports an account engine, constructs an account or fetches data. The original source-dependent reviews are preserved unchanged, together with their receipts and logs. Their full re-execution requires the omitted original minute matrix and recovered source. The compact checker is deliberately narrower.

saved_projection/DAILY_365.csv contains exactly 365 UTC-day closes, NAV and returns, actual gross exposure close/max/mean, forecast volatility close/max/mean, breach-minute counts, free cash/margin, cumulative financial charges and signed asset weights. SELECTED_MINUTE_EVIDENCE.npz contains 1,716 original rows selected by a documented calendar/extrema rule, all 37 original columns, their original minute indices and separately calculated forecast volatility. EXPORT_MANIFEST.json binds both exports to exact parent hashes and explains the formulas and limits.

## Compose the unchanged executable sources

The public base is [V3 at commit 8e613c13](https://github.com/snowycat1234/coin/tree/8e613c13be04ec9c724d0f52f699dfb0c1fcaff8/research/traditional-three-tier-smoke-20261015). Its ARCHIVE.json describes reproduction.zip.part000 through reproduction.zip.part007. Concatenate those parts in order to recover the V3 ZIP, whose SHA256 must be e7fc0566da1eb14d6b1c3ca805531111144ad22c95223c77826e3048508acae6. Extract it into a separate directory. SOURCE_PINS.json records the exact locators and verification scope.

    python assemble_recovery_workspace.py --base-v3 ../traditional_three_tier_public_recovery_20261015_v3 --destination ../new_annual_recovery

This verifies all base/add-on hashes, copies the exact existing V3 base into an exclusive new destination, overlays only annual additions, and losslessly expands the saved audit JSON. It does not run code from the financial modules. Frozen core, strategy, account, guard, targets and costs are unchanged. No original directory is overwritten.

Recover prepared_2023/DAILY.json, EVENTS.json, SOURCE_INDEX.json and months/2023-01.npz through months/2023-12.npz through the immutable public objects in source_recovery/RECOVERY_MANIFEST.json. Follow source_recovery/README.md and the corresponding base helper. The base already contains exact small warmup/proof support. The recovery helper verifies bytes and schemas; it is not a downloader or replacement normalizer. Private workspace paths are unnecessary.

The annual gate tests and unchanged entry remain available for source-only validation once source recovery is complete. Source-only tests block or mock actual construction. Any new financial execution still needs a separately authorized exact GO and must use a fresh output directory. No run command is supplied as an implied authorization.

## Regenerate only the reporting projection

If the exact retained original MINUTE.npz is available, the reporting projection can be regenerated into a new directory:

    python derive_saved_evidence.py --minute /YOUR/exact/MINUTE.npz --targets traditional_three_tier_freeze_20261015/annual_2023_source_preparation_attempt003/TARGETS.npz --output /YOUR/new_projection

This refuses changed parents. It reads saved arrays only. Without the omitted minute parent, the compact exports cannot reconstruct every minute or repeat the complete original source-dependent risk audit. The original full records are retained, not replaced by the export.

## Qualifications

This is seen-2023 development evidence. Funding fractions/publication/arrival and native venue filters/liquidation fidelity remain conditional. Continuous held-inventory forecast volatility is not capped at 10%. The saved actual-opening-leg review found no fresh-increase cap violation; it did not verify every hypothetical preview corner. No independent alpha, untouched OOS, matched-realized-risk excess, live-use or investment-performance claim follows.
