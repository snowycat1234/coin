# 2021 source-only independent review

Result: PASS within the explicit source-only review scope. No source-blocking defect found. This does not admit targets, wallets, funded economics, or full historical-arrival causality.

## Independently checked

- All 222 local public parts: expected bytes and SHA256. Their ordered concatenations reproduce all six indexed source assemblies byte-hash exactly. Recoverability uses year commit `94fe13c494c82bb6e6868e6614eb7298fb15b3c3` and December-mark commit `a23f8cc36bdaddce832b2305a16fda493d1cf764`; no moving branch or provider request is needed.
- All 12 monthly prepared-file SHA256s, sizes, exact minute grids and following-minute availability; all 120 asset/domain/month boundaries. All 5,256,000 cached minute-close rows have expected shape, positive finite prices and exact clocks.
- All 1,825 trade daily OHLCV/quote-volume cells equal their cached-minute aggregation. All 1,825 daily close cells are bit-identical to the existing hash-bound cube.
- 5,475 original rates and reported intervals independently matched directly to two saved Parquet event tables. Each asset has 1,095 events, the 1,094 old overlapping rows match exactly, and the restored final event is 2021-12-31 16:00 UTC.
- All 5,475 prepared funding clocks checked using an independent integer formula. For event time e, strict-prior availability a = floor((e-1)/60,000,000) * 60,000,000, and mark open = a - 60,000,000. Every one of the 5,470 usable marks is bit-identical to the corresponding prepared mark tape. Jitter is preserved, ranging 0–47,000 microseconds.
- All five first events are 2021-01-01 00:00:00.002 UTC, remain UNKNOWN for the missing pre-2021 mark, and precede fresh-CASH first execution. No synthetic December 2020 minute was introduced.
- Raw subset checks: all five December mark ZIPs at first minute, last minute, and final funding quote; all 15 July official daily repair ZIPs at first/last minute. All 20 selected original archives passed independent inner-ZIP CRC; 45 selected raw price rows matched prepared mark bits. July repair assets are BTC/SOL/XRP, five actual days each, totaling 21,600 added minutes.
- The 13 existing source-only synthetic checks were re-executed successfully. Independently recomputed rolling cube masks give 365 joint decisions for 21/31 closes and 274 for 200 closes; full-five 200-close readiness begins 2021-04-02.

## Code review and admission consequences

The standalone source module contains no strategy, target or wallet generation. Its clocks use source candle closure, not historical publication/arrival certification. strict_prior excludes equality, caps age at one minute, and preserves event jitter. The month carry provides the previous two actual marks, so exact-equality funding at a month boundary correctly selects the prior minute rather than the equality candle. The half-open annual event interval includes December 31 16:00 for all five assets.

A 2021 target consumer must preserve the original dynamic masks. It cannot assume a full-five 200-close signal is ready on January 1. The first actual fresh-CASH execution contract is 2021-01-01 00:01:00.000001 UTC, using the first actual minute available at 00:01. January 1 daily risk context comes from the existing prior completed daily cube, not from reconstructed pre-2021 minute prices.

Funding units remain UNCONFIRMED. Numeric rate parity does not independently establish whether those rates may be used as raw fractions; any economic result using that interpretation must remain conditional.

Terminal execution/valuation must be declared separately. The source contains the December 31 final minute with availability at 2022-01-01 00:00. A strict-prior quote exactly at that boundary uses the preceding available minute. The old 364-active-interval consumer does not itself prove a 365-interval wallet, and no beyond-calendar quote may be invented.

The apparent restore count mismatch is reconciled by supplemental TRANSPORT_ACCOUNTING.json: initial shell 36 + connector probe 1 (part0036) + connector batch 185 = 222; bytes 28,311,552 + 786,432 + 142,834,060 = 171,932,044. The old bound receipt and prepared outputs were preserved.

## Exact reviewed identities

- source_parser.py: `4275d0fb6b09c20f67377af94dc5fcbf7830a07b40d9002ea9ce54aab291ac2f`
- prepare_full_2021.py: `808ad5102f3c94e0a10843d5e8f9926913bcb4c3bec5b6136bd333763523c959`
- SOURCE_INDEX.json: `13a0d6551deef1e5cc6865ff4487ebf3fed5dd518364e909fb25ab228838eb33`
- EVENTS.json: `2d275bc9e23857f83f2f8308c09b6e359efb7f9cf0dbf882737adaa2d3329ff3`
- DAILY_OHLC.npz: `303ce02f4e9843648e039e772279ef8ce6565d0f9b299f8f748ddb4226dc8c1e`
- Y2021.zip: `b427bd0a17322f4c238cd7a813450fe5dee0f3c3a673ec38743a70784d387ab2`

All monthly file, assembly, diagnostic and source-code hashes appear in INDEPENDENT_REVIEW.json.

## Scope and reproducibility

Run verify_readonly.py with the existing coin_native_half_mix_20261013/.venv/bin/python. It restricts itself to one CPU and 2 GiB address space. The final run took 3.00 seconds with peak RSS 135,712,768 bytes.

It read only existing local source caches, wrote only these new review outputs, and made no provider, network, Library, wallet, target-generation, or retained-2026 call. It did not rerun full source preparation, nor independently reparse all 135 original price ZIPs. The all-history original-parser assertions are code-reviewed and bound to independently verified file hashes; full raw-price reparse is deliberately outside this lightweight review.
