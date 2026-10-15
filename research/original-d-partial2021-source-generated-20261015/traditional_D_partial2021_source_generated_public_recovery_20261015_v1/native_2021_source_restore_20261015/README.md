# CORE5 2021 local source qualification

This directory restores the exact already-public 2021 market sources and checks
the original source preparation. It does not grant financial execution GO.
No targets, accounts, historical strategy runs, publication or uploads are part
of this work. No denied 2022/2025 source is used. No 2026 market body is opened.

## Frozen sources and limits

- Source gate: public commit `3f3a5db3b5f1f276bc642890c57c39772f11c0f3`,
  `research/core5-2021-fullsource-20261013`.
- Original year wrapper: commit `94fe13c494c82bb6e6868e6614eb7298fb15b3c3`,
  212 parts, 166,692,849 bytes, SHA256
  `b427bd0a17322f4c238cd7a813450fe5dee0f3c3a673ec38743a70784d387ab2`.
- December actual mark originals: commit
  `a23f8cc36bdaddce832b2305a16fda493d1cf764`, ten parts, 5,239,195 bytes.
- Total source part cap: 222 parts, 171,932,044 bytes.
- Separate small-input cap: four parts, 2,635,847 bytes. Only the exact
  `Y2023.npz` cube member and five daily-feature members are permitted. Other
  members in the mixed cube packet, including its Y2025 members, stay unopened.
- The five exact existing funding parquets are reused locally. They are not
  fetched again as separate files.
- CPU affinity 7, numerical pools 1, observed RSS below 2 GiB; source preparation
  scripts retain their original 2 GiB address-space limit. No software install.

`FROZEN_SOURCE_ALLOWLIST.json` fixes every part identity, wrapper member and
the fifteen real daily-repair ZIPs before transfer. Serial transport uses the
original immutable raw GitHub host. A request error or identity failure writes
a persistent `TRANSFER_STOP.json`; there is no automatic retry or fallback.

## Original code and narrow reader changes

Exact published source code is retained in `original/` and verified against the
published reproduction manifest. Working parser, assemble, prepare and boundary
checks retain their original bytes. `ORIGINAL_CODE_ADAPTER_DIFF.json` records
reader-only changes for unavailable PyArrow: installed Polars projects the
original named columns, applies date predicates before materialization, and
preserves nanosecond clocks and floating-point source bits. Funding audit reads
the verified local original parquets. Per-read ledgers identify exact source
hashes, selected fields, predicates and selected row counts.

The original parser's thirteen synthetic checks and the adapter's date-scope,
clock, numeric-bit and helper-thread-affinity checks run before real source
preparation. Synthetic test rows are never used as market inputs.

## Reproduction sequence

Use `coin_partial_restore_20261014/.venv/bin/python -B`, with all numerical pool
environment variables set to 1 and `taskset -c 7`.

1. `download_public_parts.py`: serial exact-source transport.
2. `restore_small_public_inputs.py`: allowed only after all 222 parts verify.
3. `assemble_offline.py`: original local-only assembly, SHA256 and CRC checks.
4. Set `COIN_CUBE_PATH` and `COIN_FEATURES_PATH` to this directory's exact
   `small_inputs/Y2023.npz` and `small_inputs/features.zip`; set
   `COIN_SOURCE_READER_LEDGER_PATH` to a new local JSONL receipt.
5. `audit_warmup.py`, `audit_funding.py`, `prepare_full_2021.py`,
   `verify_few_boundaries.py`, then `qualify_apr_dec_candidate.py`.

Preparation refuses to overwrite an existing prepared source run. A failed
run remains identifiable; investigate and retain the failure before any retry.

## Candidate and unresolved gates

The unchanged all-five, 200-completed-close candidate can first be available on
2021-04-02. This is 274 decision dates through 2021-12-31. January 1 through
April 1 cannot be silently relabeled as the same full-five strategy. The older
21/31-close source masks remain a different preparation contract.

Pre-2021 warmup is exact saved daily provenance, not newly revalidated minute
tape. Rate units, historical publication/arrival, exchange listing/filter and
maintenance rules, cross-venue semantics, fees and slippage remain explicit
assumptions or separate admission gates. Actual start/end quotes and real
strict-prior funding marks can be source-qualified; paid terminal-flat costs
and funding ownership must be independently reviewed in the native engine.

Completion is established by local restore, source preparation, independent
boundary and candidate qualification receipts, not by the existence of this
README. No financial return is computed here.
