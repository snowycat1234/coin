# continuous wallet v3: public recovery wrapper

Final v3 only: exact inert permitted generated/source/native/report snapshots, all six exact saved financial event/result payloads, strict native40 proofs and retained continuity/report evidence. V1/v2 findings remain preserved; neither earlier version receives the final v3 PASS.

This publication preserves the reviewed compact ZIP unchanged. The public review is an explicitly labeled path-only projection of an unchanged historical original review. Historical local-only, publication-false, authority-false or earlier pending-status statements inside the frozen packet remain historical facts. This wrapper provides recovery instructions and no source or financial execution authority.

## Exact trust pins

- Archive: continuous_wallet_D_compact_code_generated_saved6_recovery_20261016_v3.zip
- Archive bytes: 73667424
- Archive SHA256: b54cffe6347f9ad1a95f861a46e85ce34932781d9da460b7dc97dc535523941e
- External launcher SHA256: 05ca195be6773a52a882aa22ce17b94d8c7e4966268f182ef1502a0a9cfb00ad
- Compact MANIFEST.json SHA256: be63ed6785404d1421b1aea37be01821997d215f9e97f6b4f3161d1a35ebe20b
- Historical original review: FINAL_INDEPENDENT_COMPACT_RECOVERY_REVIEW.json (retained privately, unchanged)
- Historical original review SHA256: 481416ad66ee5b1a0ae0982fce15a69c74e26e35370dd27c25a1df72a1e531d9
- Historical original review bytes: 16480
- Public review: [PUBLIC_REVIEW_PROJECTION.json](PUBLIC_REVIEW_PROJECTION.json)
- Public review projection SHA256: 7237dba9bacf0f11a7850b131304f47834b36285bf7196030673e76a5e5a3714
- Public review projection bytes: 15890
- [Path-only projection provenance](ORIGINAL_REVIEW_PROJECTION_PROVENANCE.json)

The separately supplied launcher and manifest are exact copies of their reviewed ZIP members. Obtain expected archive, launcher and historical original-review hashes through a trusted independent channel. The public projection has a separate hash and is not byte-identical to the original review; its companion provenance lists every JSON-pointer path change without exposing the private path values. An archive's internal manifest is not its own external trust root.

## Recover the exact archive

The archive is carried as 9 raw byte slices under transport/, each at most 8,388,608 bytes. They concatenate to the exact reviewed ZIP; there is no recompression or repacking. Obtain every part and both transport sidecars. From this directory, run:

python -I -B transport/REASSEMBLE.py --trusted-zip-sha256 b54cffe6347f9ad1a95f861a46e85ce34932781d9da460b7dc97dc535523941e --output continuous_wallet_D_compact_code_generated_saved6_recovery_20261016_v3.zip

Use a fresh output path. The helper checks every part's size, offset and SHA256 and the combined ZIP pin. Authenticate the helper separately before running it. The additive transport does not change or extend the independent compact-packet review.

## Saved-only cold verification

Inherit exactly one available CPU and numerical pools 1. CPU 1 is the reviewed author example and CPU 3 the independent example. Verify the separately supplied launcher hash externally before running; its self-check is additional defense. Add -O for optimized checking. The historical review records its exact Python environment; full historical runtime dependencies are not restored.

After substituting the exact archive name and trusted hashes:

taskset -c 1 python -I -B run_isolated_cold.py ARCHIVE --trusted-zip-sha256 ZIP_SHA256 --trusted-launcher-sha256 LAUNCHER_SHA256 --receipt NEW_COLD_RECEIPT.json

These commands describe the authenticated saved-only recovery boundary. No source replay, financial-engine import, account/provider construction, source capture or new financial clock advance is part of compact verification. Do not execute inert historical code snapshots.

## Recovery limits

Saved native40 event reconstruction for all six is self-contained. Full generated/source/native execution, minute-risk/source reconstruction and historical financial restart are not self-contained. All MINUTE chunks, target/covariance/source input/prefix/rows/raw market/funding bodies, external runtime dependencies and private executable GO/claim/authority/log/credential bodies are omitted. The only excluded own-manifest member is the explicitly hash-only generated test log. Hashes cannot restore omitted bodies.

Six fixed continuous wallets each have one initial 10,000 USDT over [2021-04-02,2026-01-01), 1735 days and 2,498,400 minute opens. Four Jan 1 seams carry state with no annual reset, close or reseed. All terminal outcomes remain visible. All seen DEV. Historical whole-interval CAGR is not forward APR. Nominal tiers do not match realized risk. Funding units/arrival, venue filters/risk tiers, gap marks and liquidation remain uncertified; Guard50 installation does not certify permanent exit-only mode.

The exact reports, metrics, source-quality qualifications, historical failure records and dependency classifications remain inside the reviewed ZIP. Financial event payloads are never duplicated as loose public files outside that ZIP.

## Direct saved results

Read [REPORT.md](results/REPORT.md), an exact byte-for-byte copy of the reviewed ZIP member. This small report contains saved summary metrics and qualifications, with no duplicated account-event payloads.
