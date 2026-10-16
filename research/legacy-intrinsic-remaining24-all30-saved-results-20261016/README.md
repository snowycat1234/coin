# legacy remaining24 all30: public recovery wrapper

Exact saved native40 event/state proof recovery for the remaining 24 cases, plus the exact 30-row aggregate. This is saved-results recovery; historical new24 financial/source execution code is not included.

This additive wrapper preserves the reviewed compact ZIP and review bytes unchanged. Historical local-only, publication-false, authority-false or earlier pending-status statements inside the frozen packet remain historical facts. This wrapper provides recovery instructions and no source or financial execution authority.

## Exact trust pins

- Archive: legacy_intrinsic_D_REMAINING24_ALL30_compact_saved_results_recovery_20261015_v1.zip
- Archive bytes: 48739816
- Archive SHA256: 5315aace9ae26210d868d11937e564d8a642c63f17300bbcb2b74a5f4d70b777
- External launcher SHA256: c3c847816b8707f53c76a1154ef91f98aec41264491f5f7cccc62d927c2904ff
- Compact MANIFEST.json SHA256: 9f0038d787ac7eccb9f3288d777188a2774f89882bf97b575a0e39858d6247cc
- Independent review: FINAL_INDEPENDENT_PACKAGING_REVIEW_RECEIPT.json
- Independent review SHA256: 1480a33e7e717d13bd0bdcf4e9c38a6e2170bf1d26946ce933e30b7dcf13568a

The separately supplied launcher and manifest are exact copies of their reviewed ZIP members. Obtain expected archive, launcher and review hashes through a trusted independent channel. An archive's internal manifest is not its own external trust root.

## Recover the exact archive

The archive is carried as 6 raw byte slices under transport/, each at most 8,388,608 bytes. They concatenate to the exact reviewed ZIP; there is no recompression or repacking. Obtain every part and both transport sidecars. From this directory, run:

python -I -B transport/REASSEMBLE.py --trusted-zip-sha256 5315aace9ae26210d868d11937e564d8a642c63f17300bbcb2b74a5f4d70b777 --output legacy_intrinsic_D_REMAINING24_ALL30_compact_saved_results_recovery_20261015_v1.zip

Use a fresh output path. The helper checks every part's size, offset and SHA256 and the combined ZIP pin. Authenticate the helper separately before running it. The additive transport does not change or extend the independent compact-packet review.

## Saved-only cold verification

The exact launcher uses Linux CPU 6 and numerical pools 1. It requires that CPU to be available. Verify the launcher SHA256 externally before execution. Add -O for the optimized saved-only checker.

After substituting the exact archive name and trusted hashes:

python -I -B run_isolated_cold.py ARCHIVE --trusted-zip-sha256 ZIP_SHA256 --receipt NEW_COLD_RECEIPT.json

These commands describe the authenticated saved-only recovery boundary. No source replay, financial-engine import, account/provider construction, source capture or new financial clock advance is part of compact verification. Do not execute inert historical code snapshots.

## Recovery limits

The first six financial payloads are referenced at immutable commit b2e3acd6b4cd718d717b52a85c50254f5e74f3e9 rather than duplicated. Their ZIP SHA256 is 1a7cd6f0bff059cb76053dd6a41b4e6c03e45291f1fb26fda1a3b8bb1f0afc3b. The new24 source commit is unspecified and source/code publication is unverified. Historical source/runtime, MINUTE, targets, covariance/decision/source arrays and prepared RAW_EVENTS bodies remain hash/local only. Hashes cannot restore those omitted bytes. Full minute-risk/source reconstruction and historical financial restart are not self-contained.

All 30 cases ended saved actual paid-flat, but sessions 27834 and 6043 shell exits remain UNOBSERVED; completion is not converted to exit 0. Each annual case starts a fresh 10,000 USDT wallet. All periods are seen DEV; 2021 is Apr 2–Dec 31 (274 days), with unannualized paid return. Nominal tiers do not establish matched realized risk. Funding units/arrival, venue filters/risk tiers, gap marks and liquidation remain uncertified.

The exact reports, metrics, source-quality qualifications, historical failure records and dependency classifications remain inside the reviewed ZIP. Financial event payloads are never duplicated as loose public files outside that ZIP.

## Direct saved results

Read [LEGACY30_SAVED_RESULTS_SUMMARY.md](results/LEGACY30_SAVED_RESULTS_SUMMARY.md), an exact byte-for-byte copy of the reviewed ZIP member. This small report contains saved summary metrics and qualifications, with no duplicated account-event payloads.

## Fixed provenance dependencies

- prior_saved_results: https://github.com/snowycat1234/coin/tree/b2e3acd6b4cd718d717b52a85c50254f5e74f3e9/research/legacy-intrinsic-first6-saved-results-20261015

These immutable evidence references do not fix the parent of this new wrapper commit.
