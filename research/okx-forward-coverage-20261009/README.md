# OKX forward source coverage — 2026-10-09

This module contains public OKX USDT linear perpetual data only. It does not
change any strategy, train a model, run a wallet, or certify historical execution
rules, account fees, instrument specifications or publication clocks.

| Native instrument | UTC daily bars | Funding events | July 15 trade/mark sample |
| --- | ---: | ---: | --- |
| BTC-USDT-SWAP | 646 | 258 | 100 / 100 |
| ETH-USDT-SWAP | 646 | 258 | 100 / 100 |
| SOL-USDT-SWAP | 646 | 258 | 100 / 100 |
| XRP-USDT-SWAP | 646 | 258 | 100 / 100 |
| DOGE-USDT-SWAP | 646 | 258 | 100 / 100 |

Daily trade bars cover January 1, 2025 through October 8, 2026, with exclusive
end October 9. All five grids are complete: 3,230 daily rows and zero gaps.
The 200-day pre-July-15 daily lookback is present. Prices are original decimal
strings per underlying coin. Native contract values are 0.01 BTC, 0.1 ETH, 1 SOL,
100 XRP and 1,000 DOGE, all returned with contract multiplier 1. Current metadata
is preserved; it does not certify historical specifications. Trade volume stays
in [contracts, base, quote] fields; mark prices have no traded volume.

Funding history covers July 15 through October 8, 2026. Each instrument returned
258 events, July 15 00:00 through October 8 16:00 UTC, on the observed eight-hour
grid with no missing event and no empty actual rate. Both predicted `fundingRate`
and actual `realizedRate` strings are retained independently, with no rescaling,
zero filling or substitution. `fundingTime` is the provider's settlement event
clock, not a certified publication or account cash clock. OKX documents dynamic
funding schedules and a three-month history limit; the manifest includes the
observed interval histogram, an explicitly assumed eight-hour-grid diagnostic,
and an uncertified historical-schedule flag. This is observed API coverage,
not certified account settlement. See the official funding-history documentation:
https://app.okx.com/docs-v5/en/#public-data-rest-api-get-funding-rate-history

The only minute data requested were 100 completed minutes at July 15 00:00 UTC
for trade and mark for each instrument, 1,000 sample rows total. All samples were
complete. These samples establish that this window is retrievable; they do not
prove complete 86-day minute retention. No bulk minute acquisition ran.

The acquisition used 54 new public requests, 662,784 response-body bytes and
53.23 seconds. Requests were at least one second apart. DOGE's verified current
instrument response was reused with its original source/receipt binding. No keys,
Bybit requests, paid sources, proxy changes or local/private inventories appear
in this module. Every request and response checksum is in its instrument manifest.
The acquisition source is immutable at commit
`48f46802100568ee052b75b7db7b28d2adc88112`; its original SHA remains in all
receipts. The latest code only wraps one diagnostic string onto two lines.

A full July-15–October-9 five-asset native trade+mark series would contain
1,238,400 minute rows: 123,840 per instrument per kind. At 100 candles per request,
that is 12,390 candle requests and a minimum 3h 26m 30s at one request per second,
plus retries and other inputs. The ten small samples imply approximately
93,994,560 response-body bytes (~94 MB); wire bytes, compressed storage and
full-window availability are not certified. Funding and daily data do not make
this a completed native wallet backtest.

Each instrument directory contains `daily.jsonl`, `funding.jsonl`,
`minute-trade-sample.jsonl`, `minute-mark-sample.jsonl`, `manifest.json` and
checksum-named raw provider responses. `SCHEMA.json` gives row fields and types.
`SHA256SUMS` covers this module except itself. Tests: 45 passed; Ruff passed;
raw OHLC/volume/rates, complete grids, receipt clocks and raw hashes were
independently checked. No canceled continuous700 archive content is included.
