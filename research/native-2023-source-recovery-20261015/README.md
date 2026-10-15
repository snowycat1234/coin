# Exact 2023 public source recovery

A small source manifest and offline verifier. No raw payload, account state, strategy target, outcome, credential or execution approval is included.

## Verified coverage

All 120 original monthly trade/mark ZIPs and five genuine February 24 mark-day repair ZIPs passed indexed part/archive SHA256, official CHECKSUM text and ZIP CRC. Daily repairs required exact numeric overlap; no minute was interpolated.

All twelve normalized native NPZ containers reproduce original bytes. DAILY.json, EVENTS.json and SOURCE_INDEX.json are also exact originals. Coverage is [2023-01-01, 2024-01-01) UTC: 525,600 minutes per CORE5 symbol, 1,825 daily records, 5,475 funding events and zero derived mark cells. Value files total 43,174,614 bytes; the source index is 187,720 bytes.

The separate reviewed original200 proof covers 564 daily availability clocks, 2022-06-16 through 2023-12-31, and 2,820 genuine observed, complete, actual, nonimputed CORE5 bars. Every one of the 365 decisions binds its exact 200-day window and bit-identical prices. The extra 2024-01-01 terminal close is outside that prior proof; it matched the restored December 31 minute source separately.

Fixed CORE5 order: BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, DOGEUSDT. This order is implicit in pinned original source.py; the original warmup cube has no symbol_order member. RECOVERY_MANIFEST.json contains immutable public commits, repository paths and checksums.

## Offline verification

Requires Python and NumPy. From this directory:

    python -m unittest -v test_recovery_verifier.py
    python verify_recovered_2023_source.py --source-root /YOUR/prepared_2023 --warmup /YOUR/source_close_only.npz --proof-directory /YOUR/original200_proof

The verifier makes no network request, installation, financial import, account or simulation. It checks complete file bytes, original schemas and calendar. The optional proof check compiles the hash-pinned pure source checker directly from verified text.

Derive the source-only warmup export from the existing public original cube:

    python verify_recovered_2023_source.py --original-cube /YOUR/INPUTS.npz --derive-warmup-output /YOUR/new_source_close_only.npz

Only close_available_us and close are selected, restricted to 2022-06-16 through 2024-01-01. No reward, utility, target, label or funding_per_unit member is selected. Output must be fresh. The observed exact NPZ identity used NumPy 2.3.5; differing container bytes fail closed.

## Recovering originals elsewhere

Reuse the existing public objects in the manifest through an authorized repository connection or a local Git checkout containing those exact commits. No new raw upload is needed.

1. H1 SOURCE_INDEX files list ordered part paths, sizes/SHA256s, complete ZIP identities, official CHECKSUM identities and exact daily-union repairs. Verify assembled originals and CRC.
2. H2 JULY2023/OCTOBER2023 INDEX files list ordered wrapper parts and member identities. Verify wrappers, then extract only raw/ trade/mark originals and CHECKSUM companions. Outcome members are unnecessary.
3. Normalize with pinned original source.py and numeric_csv/validate_price functions, retaining source types, clocks, complete grids and JSON serialization. This recovery used an AST allowlist of pure functions instead of importing financial modules.
4. Funding member hashes are listed individually. Existing sparse-recovery Parquet members matched exactly, so no funding provider request was needed. Only calc_time_ms,last_funding_rate,funding_interval_hours were projected for 2023. An explicit Polars 1.44.2 reader replaced pyarrow at that boundary only; complete EVENTS.json had to reproduce the original 706,295-byte SHA256. No rate rescale occurred.
5. Retrieve the final source index from its separate artifact commit, not the earlier code-authority commit. Copy exact index bytes after all value files pass, then run this verifier.

This script verifies and binds existing source. It is not an automatic downloader or replacement normalizer, and does not fetch missing objects or retry denied requests.

## Builder interface

verify_prepared_source(source_root) verifies source values. verify_warmup_and_proof(warmup_file,proof_directory) supplies separate 200-day source authority. Neither grants account execution authority.

verified_source_window(source_root) returns:

- start,end: integer UTC microsecond boundaries
- symbols: fixed ordered CORE5 tuple
- daily: original list records with symbol,close_us,close
- events: original records with symbol,event_us,raw_rate,reported_interval_hours
- minute_blocks: a lazy callable yielding one day at a time, with times:int64 and market[symbol][open,close,quote_volume,mark]:float64 arrays

Every monthly file is rehashed when consumed. Convert daily records to the native DataFrame only after the consumer's source authorizer succeeds. Construct strategy targets from the separate close-only warmup cube; previously scaled targets cannot replace underlying CS/HOLD signals.

## Limits and retained corrections

This is previously seen 2023 development source. No holdout was opened, no 2024/2025 source transfer occurred, and no account ran.

Funding units remain archive-uncertified. event_us preserves calc_time_ms*1000, without certifying provider publication/arrival or exchange charge-price timing. The warmup proof inherits pinned prior raw reconstruction/checkpoint evidence; this recovery did not freshly verify every 2022 warmup minute.

Pre-year minute quote/mark prior is unknown. Never fabricate December 31, 2022 data. The first real January 1 minute quote is available at 00:01. A deferred coldstart policy must be separately frozen and common to compared accounts. No venue, margin/liquidation, historical constructor, live-use or investment-performance certification is granted.

Source data were unchanged by three nonfinancial corrections: an initial report requested a nonexistent symbol_order member; one helper-added trailing newline was removed from three JSON files to restore exact public Git identities; and a final-index lookup at the code commit returned 404 before its existing later artifact was located. Original failures and detailed receipts remain retained locally. None was an account attempt.
