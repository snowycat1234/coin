# high365 v3: public recovery wrapper

Final v3 only: compact report, exact small saved metadata/proof receipts, inert exact source recovery and source/report/review cross-bindings. The cold checker authenticates earlier native40 proof receipts; it does not freshly reconstruct the financial events.

This publication preserves the reviewed compact ZIP unchanged. The public review is an explicitly labeled path-only projection of an unchanged historical original review. Historical local-only, publication-false, authority-false or earlier pending-status statements inside the frozen packet remain historical facts. This wrapper provides recovery instructions and no source or financial execution authority.

## Exact trust pins

- Archive: original_high365_D_compact_source_report_recovery_20261016_v3.zip
- Archive bytes: 3733777
- Archive SHA256: 9e2fde3375a1457f29a24e148dc425f9b6c037aed9b5d7191776af63c4359a49
- External launcher SHA256: b5c9442e97fcf1d3a76637d266d367ccd45035d032aefde022878447716123e3
- Compact MANIFEST.json SHA256: ac993028fb9be01a0945a6049b75412526272cf9e840f9956c41f76283690d1d
- Historical original review: FINAL_INDEPENDENT_COLD_REVIEW.json (retained privately, unchanged)
- Historical original review SHA256: 87be34818a33c8a29516609b9d5472e9406ffcb875300f718ac641679b4e1519
- Historical original review bytes: 14029
- Public review: [PUBLIC_REVIEW_PROJECTION.json](PUBLIC_REVIEW_PROJECTION.json)
- Public review projection SHA256: 0397f842280f7c5c0054739f7e8222f20bbc092c5a4dd0ca8c7e083472a8da7a
- Public review projection bytes: 14017
- [Path-only projection provenance](ORIGINAL_REVIEW_PROJECTION_PROVENANCE.json)

The separately supplied launcher and manifest are exact copies of their reviewed ZIP members. Obtain expected archive, launcher and historical original-review hashes through a trusted independent channel. The public projection has a separate hash and is not byte-identical to the original review; its companion provenance lists every JSON-pointer path change without exposing the private path values. An archive's internal manifest is not its own external trust root.

## Recover the exact archive

The unchanged reviewed ZIP is included directly. Verify its exact byte count and SHA256 before use.

## Saved-only cold verification

Use Python 3.12+ standard library, a fresh receipt destination, numerical pools 1 and at least 1.5 GiB free plus the launcher expansion allowance. Authenticate the separate launcher SHA256 before execution. Add -O for optimized checking.

After substituting the exact archive name and trusted hashes:

python -I -S -B run_isolated_cold.py ARCHIVE --trusted-zip-sha256 ZIP_SHA256 --receipt NEW_COLD_RECEIPT.json

These commands describe the authenticated saved-only recovery boundary. No source replay, financial-engine import, account/provider construction, source capture or new financial clock advance is part of compact verification. Do not execute inert historical code snapshots.

## Recovery limits

The archive is not self-contained for saved native40 event/account/minute reconstruction or historical financial reproduction. Exact omitted source/funding/target/controller/account/event inputs and external runtime dependencies are required, along with fresh appropriate execution authorization. Hashes cannot restore omitted bodies. All 205 dependencies are classified; 51 exact dependency identities are included and 154 are external/hash-only. V1/v2 failures and the prior v2 FAIL remain immutable; v3 corrects dependency metadata and verifier regressions only.

Fifteen annual cases each start fresh with 10,000 USDT and end saved actual paid-flat. No annual or tier compounding. 2021 is Apr 2–Dec 31 (274 days), with unannualized paid return. The 2022 and 2024 UNKNOWN held-position source marks remain disclosed; zero interval trades/funding do not establish zero valuation impact. All seen DEV. Nominal tiers are not exact realized-risk matching; source arrival, funding units, venue filters/risk tiers and liquidation remain uncertified. The final aggregate and observed root EXIT 0 receipt establish completed historical status despite preserved earlier authority-false/exit-pending metadata.

The exact reports, metrics, source-quality qualifications, historical failure records and dependency classifications remain inside the reviewed ZIP. Financial event payloads are never duplicated as loose public files outside that ZIP.

## Direct saved results

Read [COST_MDD_EXPOSURE_MATRIX.csv](results/COST_MDD_EXPOSURE_MATRIX.csv), an exact byte-for-byte copy of the reviewed ZIP member. This small report contains saved summary metrics and qualifications, with no duplicated account-event payloads.

## Fixed provenance dependencies

- inert_public_expert_source: https://github.com/snowycat1234/coin/blob/1bbc51212c9cf7b7569c1a252efd0e923c2e70c5/research/high-reference-expert-20261012/expert.py

These immutable evidence references do not fix the parent of this new wrapper commit.
