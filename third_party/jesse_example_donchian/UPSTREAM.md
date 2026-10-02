# Pinned public Donchian rules

Strategy: https://github.com/jesse-ai/example-strategies
Commit: `7c91e0a37bf62165790120d730442e4f6eb00364`.
Original path: `Donchian/__init__.py`; Git blob
`7c75352422d86f8e8e0626e8b2e51894e694f709`, SHA256
`fc635b257ad1e12951dc140dae46a63bd37e9abfa5f2d681ef1e754d8ce393fe`.
`donchian_original.py` is the unchanged 1,478-byte upstream file.
`LICENSE` is its unchanged MIT notice (2020 jesse-ai).

Indicator: https://github.com/jesse-ai/jesse
Commit: `417f8765225e3bfc12043d4b712f19fe15a3c078`.
Original path: `jesse/indicators/donchian.py`; Git blob
`2ec6cca83e5f1f5d81066313437f3c4f62a99c95`, SHA256
`b7e96ebe3ba476c771a65b353c269a84d02e04587f0d76166c5f322bbbb3a401`.
`donchian_indicator_original.py` is unchanged. `JESSE_LICENSE` is its unchanged
MIT notice (2020 Jesse.Trade).

Use: `COIN_JESSE_DONCHIAN_1H_SPOT_ADAPTER`, a public-rule transplant for historical
screening. The original strategy does not specify a timeframe; this comparison
preselects closed 1h candles. Reuse its unchanged class signal hooks and unchanged
nonsequential Donchian function, with a small explicit context port. The full Jesse
engine and Rust indicator runtime are not installed. The port supplies a past-only
candle array, NumPy's mean for SMA200, identity slicing of an already bounded
201-candle context, and an exit flag for `liquidate`. It does not call upstream
balance sizing or submit Jesse orders. All sizing, fees, risk, latency, capacities,
accounting and terminal valuation belong to the existing COIN common engine.

Changes: no upstream bytes changed; imports are excluded from an AST-based loader
and only the pinned class/function are loaded. The runtime port and 1h candle
adapter are new COIN code. Allocation is 0/30% per symbol, with the common gross
and volatility limits; original whole-balance allocation is not reproduced.
This is not a replication of the upstream published backtest, nor evidence of
profitability. No upstream performance numbers are used to select parameters.
