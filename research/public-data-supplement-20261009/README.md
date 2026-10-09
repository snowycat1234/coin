# Independent public daily supplement — 2025 June–December

1,070 actual OKX UTC daily trade candles: 214 per asset, June 1 through December 31,
2025. Each native perpetual has a separate receipt, raw responses and normalized
JSONL file. This is an alternative venue robustness dataset. It does not replace
Binance observations or certify the frozen original selector evaluation.

| Binance reference | Actual OKX perpetual | Native price unit | Native contract value |
| --- | --- | --- | --- |
| WIFUSDT | WIF-USDT-SWAP | USDT / WIF | 1 WIF |
| WLDUSDT | WLD-USDT-SWAP | USDT / WLD | 1 WLD |
| ORDIUSDT | ORDI-USDT-SWAP | USDT / ORDI | 0.1 ORDI |
| 1000PEPEUSDT | PEPE-USDT-SWAP | USDT / PEPE | 10,000,000 PEPE |
| 1000SATSUSDT | SATS-USDT-SWAP | USDT / SATS | 10,000,000 SATS |

All contract multipliers returned 1. Prices are stored as original decimal
strings with no rescaling. The PEPE/SATS reference prices are per 1,000 underlying
coins; these OKX prices are per single coin. Returns do not establish instrument
identity, historical contract rules or interchangeable execution prices.

Instrument metadata was retrieved in October 2026 and is explicitly current,
not certification of historical specifications. Each row records the request's
raw SHA and local receipt time. Historical publication time is unknown. The day
close is an exclusive UTC boundary, not a certified historical availability time.
Local SHA256 checksums preserve bytes; they are not provider-signed attestations.

The initial Bybit API probe returned HTTP 403 with an explicit country block.
That service was stopped. The independently authorized OKX probe returned three
WIF candles and agreed with the corresponding later full-window observations.
There were 22 requests including the two initial probes and the five authorized
June-only additions, totaling 121,743 response-body bytes. The original 184 rows
per instrument remain byte-for-byte identical after the 30 new June rows.
Metadata and all July–December pages were reused without additional reads. No Binance request,
training, backtest, account key, order or paid source was used.

A separately authorized mark stage obtained all 44,640 OKX DOGE-USDT-SWAP
December 2025 minute mark candles, with zero gaps, using 448 requests and
2,762,130 response-body bytes. `doge-mark/DOGE-USDT-SWAP/bars.jsonl.gz`
contains the full normalized grid; its separate manifest retains all raw pages
and current metadata. Mark candles have no traded-volume observation.
This independent OKX series does not certify or replace the missing original
Binance mark file. Historical publication time remains unknown.

`COVERAGE.json` records exact coverage, source-code binding and validation.
Per-instrument `manifest.json` files retain every URL/query, native metadata,
HTTP outcome, receipt time and raw checksum. `SHA256SUMS` covers every artifact
in this directory except itself. The collector code and synthetic tests are in
`modules/collector_research`; its README documents the plan and daily-only CLI.

`SCHEMA.json` gives the exact shared row fields and types. Daily `bars.jsonl` files
contain 214 rows each; `warmup.jsonl` contains their 30 June rows. Separate
`june-manifest.json` receipts reference immutable H2 metadata at commit
`28236726b7ab8fa4f50759a314cc5303b74a86f2`.
