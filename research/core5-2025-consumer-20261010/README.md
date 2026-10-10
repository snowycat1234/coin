# 2025 CORE5 reproducible research inputs

Status: source economics, original features and expert targets reconstructed; no selector fit and no 2025 strategy return reported.

- 2025-01-01 through 2025-12-31, 365 decisions and 364 active daily intervals. BTC, ETH, SOL, XRP, DOGE in that order. A consumer must force and charge final liquidation.
- 120 official Binance monthly 1m trade/mark ZIPs, 163,950,407 bytes, verified against official SHA256 and ZIP CRC. All 120 grids have zero missing or duplicate minutes. Each asset has 1,092 owned funding events, all with strictly prior actual minute marks. Independent funding coefficient summation agrees within 1e-10. No 8-hour cadence substitution or zero-filled missing prices.
- 24 unchanged causal input formulas rebuilt from ten-asset daily histories. Old frozen pre-May2024 features/masks match bitwise. Cached overlap retained after numerical daily-source parity, explicitly preserving old values. New daily feature completeness refers to official 1d observations; minute-grid equivalence for the five context-only assets is NOT asserted.
- Unchanged CASH / VOL_MANAGED_HOLD / CSMOM21 / MOMENTUM30_SHORT recipes. All four eligible on 365 decision dates, but eligibility does not imply nonzero holdings or profit. Prefix invariance checked over 180 decisions; position target caps retained.
- Exact derived economics, complete source feature tables, feature arrays, targets, source receipts and producer scripts are in CONSUMER.zip. Original 163.95MB minute ZIPs remain local and are not in this archive. URL/checksum recipes support redownload; do not confuse that with remotely archived original bytes.
- Training consumer admission, shared-wallet replay and new model training are still pending. This is additional development history, not a claim of untouched out-of-sample validation. Costs remain the existing research contract (5.5bp fee +4bp half-spread +4bp slippage each side, actual funding, paid closing; no new leverage). No APR, CAGR, live-return estimate or superiority over Bybit robots follows from source validation.

Daily primitives source: https://github.com/snowycat1234/coin/tree/88a77396c7f1e6e0fd5b6249fe0f79dd923fda3b/research/core10-2025-primitives-20261010
Official archive documentation: https://github.com/binance/binance-public-data
