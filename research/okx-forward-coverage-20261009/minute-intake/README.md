# OKX CORE5 minute intake

Read COVERAGE.json and SCHEMA.json. Paths are relative to this directory. Each COMPLETE instrument/date manifest binds separate ordered trade and mark JSONL gzip shards, exact original responses and local SHA256 receipts. Reject gaps, overlaps and other statuses. Funding remains in the parent directory; each date manifest records completed prior-minute marks for start/funding clocks.

Scope: BTC, ETH, SOL, XRP and DOGE USDT perpetual swaps, 2026-07-15 inclusive through 2026-10-09 exclusive, plus five preceding start marks. Original price/volume strings remain unchanged. Contract metadata is current. Historical publication, contract rules and account settlement are uncertified. This separate OKX dataset cannot certify the frozen Binance selector. No training or wallet backtest is performed.

Fixed official source, serial calls, shared start spacing at least 250 ms; 20/2s documented IP limits per endpoint; trade max 300, mark max 100. Stop on denial/rate limit or incomplete page; at most 14,000 new requests, 160 MB response bodies and four hours. Verified prior probes are reused.
