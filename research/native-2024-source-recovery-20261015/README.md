# Exact 2024 public source recovery

Source-only handoff. No raw market payload, model, strategy target, account state, outcome, credential or financial execution approval is included. The small close-only warmup and prior-minute export are market source values.

## Verified coverage

Calendar [2024-01-01, 2025-01-01) UTC: 366 days, 527,040 minutes per CORE5 symbol, 1,830 daily records and 5,490 funding events. Twelve normalized NPZs, DAILY.json, EVENTS.json and SOURCE_INDEX.json reproduce all original bytes, totaling 45,999,392 bytes. Fixed symbol order: BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, DOGEUSDT.

Exactly ten original missing August 12 mark closes remain the previously frozen derived overlay. Five assets each lack 10:02 and 10:03 UTC original mark rows. The derivative values and rule were unchanged. They are excluded from daily decision features; they are not genuine exchange observations. The source index preserves the original missing coordinates and overlay SHA256.

The 566-row close-only export covers completed-close availability clocks June 16, 2023 through January 1, 2025. All 2,830 cells were compared bit-for-bit with freshly rehashed actual normalized trade-minute closes from seven 2023 months and all twelve 2024 months. Each of the 366 decisions has exactly 200 contiguous, finite, positive actual daily bars. The separate initial-prior export contains the verified December 31, 2023 last-minute quote/mark values; it does not select or change any initial execution/coldstart policy.

## Offline verification

Requires Python and NumPy. No network, provider request, financial import or account construction occurs.

    python -m unittest -v test_recovery_verifier.py
    python verify_recovered_2024_source.py --source-root /YOUR/prepared_2024 --warmup SOURCE_WARMUP_CLOSE_ONLY.npz --proof-directory .

verify_prepared_source(source_root) checks complete file hashes, schemas, source calendars and counts. verify_warmup_and_proof(warmup_file, proof_directory) binds all 366 exact 200-day windows. verified_source_window(source_root) returns start, end, symbols, daily, events and lazy minute_blocks yielding one UTC day at a time. Every monthly file is rehashed on consumption. The returned interface also exposes the ten-cell derivative provenance.

This source checker grants no account execution authority. The consumer must separately authorize any downstream simulation and preserve its previously frozen common policy.

## Recovering existing public originals

RECOVERY_MANIFEST.json pins exact public commits, repository paths, part sizes, SHA256 and Git blob identities. Reuse existing verified cache bytes. The same existing immutable public parts can be read through an authorized repository connection or their canonical raw.githubusercontent.com URLs; no new source upload is needed.

The four original wrappers comprise 23 public parts and 186,273,338 bytes. Verify ordered part identities and assembled whole-wrapper hashes first. Read ZIP directory metadata, then only the explicit 2024 price/funding source members. Do not run wrapper-wide testzip: wrappers also contain excluded non-source or outside-2024 members. This recovery read 305 selected member bodies: 120 original monthly trade/mark ZIPs, 30 original monthly funding ZIPs, all 150 original CHECKSUM companions and five H1 funding Parquets. Each selected raw ZIP passed its official CHECKSUM and inner CRC. No excluded member body was decompressed.

The pinned original prepare_native_2024.py is pure source transformation. SOURCE_ONLY_ADAPTER.diff records the narrow approved adaptation: enforce the selected-member read allowlist, omit wrapper-wide testzip, project five funding source columns, and derive daily closes from actual minute sources plus the verified 2023 terminal instead of reading a mixed daily cube. All original output file hashes had to match exactly. No Y2025 model/outcome packet was read.

The public ten-row derivative CSV was committed with LF endings, while the original source index pins its CRLF container. Exactly eleven LF-to-CRLF conversions reproduce the original 1,227-byte SHA256; the inverse reproduces the public Git blob. No numeric field or imputation rule changed. The explicit recovery receipt retains both identities.

## Limits and retained corrections

2024 is already-seen development source, not new OOS. Funding rate units, publication/arrival and exchange charge-price timing remain uncertified. No venue, quantity filter, margin/liquidation, live-use or investment-performance certification is granted.

The original connector returned empty content for an 8 MiB Contents object and UTF-8 failures for binary blob reads. A permitted immutable public raw read recovered the same exact objects. One interrupted downloader was resumed only after the previous process was confirmed stopped, reusing verified cache parts. The earlier transport failures and LF-container mismatch were retained; none was a financial attempt. No official provider request or new raw source upload occurred.
