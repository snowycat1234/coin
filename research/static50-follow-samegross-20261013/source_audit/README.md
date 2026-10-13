# Actual CORE5 2024 FOLLOW source gate

Status: PASS_REAL_CORE5_2024_OHLC_SOURCE_GATE. No financial history was run and no targets were generated.

The directly consumable `Y2024_REAL_OHLC.npz` has SHA-256 `e82bcc799caac824299ec66a254094319f7c1ecc3f9b817e53a888da3872d88a`, size 44,460 bytes, and exactly `symbol_order`, `available_us`, `high`, `low`, `close`, `ready`, `risk_t`, `risk_p`. Ordered CORE5 is BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, DOGEUSDT. The daily arrays are 397 x 5, covering all 31 completed December 2023 days and all 366 completed 2024 days. Availability clocks run 2023-12-02 00:00 UTC through 2025-01-01 00:00 UTC inclusive. All `ready` cells are true.

Daily highs and lows are max/min of actual trade candle fields; daily close is the last actual trade minute close. Neither marks nor a close series were substituted for actual high/low. Every raw close-time is exactly its open-time plus 59,999 ms. Candle availability is `(close_time_ms + 1) * 1000`, so a daily candle becomes available at the following UTC midnight. Exactly 21 completed candles are available for the first Jan 1 decision, from Dec 11 through Dec 31 trade days. The same source supplies 31 completed closes (30 returns) for its original risk context.

`SOURCE_GATE.json` records all 65 raw monthly trade ZIP/CSV/checksum hashes, actual row coverage and clocks, extrema array hashes, frozen source hashes, and complete parity results. All 2,858,400 actual minute clocks match the existing frozen native source. All 8,575,200 minute open/close/quote-volume cells match it bit for bit. All 1,985 aggregated completed daily close cells are bit-equal to the frozen STATIC50 cube (`88a698ceed87603a36ca2bcf4ae76d805aa90085b344bbeee47e58a8c9770add`), and the artifact `close` and `risk_p` arrays have identical bytes. The 2024 native source index is `0b319baf450c8a0f2f89c2a15fdabf2741471bd0ae75aef6f5be1f76cb439c69`.

`PUBLIC_PROVENANCE.json` contains verified pinned public manifest links. Exact public manifest text copies are included as evidence and match the corresponding existing local files. All market data bytes were read from existing local packages; no public binary or market-provider data were downloaded.

The existing 2024 native market inputs still include the original ten-cell derived mark overlay. This source gate validates actual trade HLC and its parity only; it does not certify venue assumptions or imply a financial result. Accounts, keys, retained March–September 2026, Library and uploads were not used.

Run `audit_sources.py` only in an absent evidence output location if repeating the source audit: it refuses to replace an existing dataset. It is pinned to the original wrappers/cube/index and compares exact bytes without importing account or target modules. The recorded audit took 14.07 seconds, on one CPU/thread, with 4 GiB AS limit and peak process RSS 111,943,680 bytes.
