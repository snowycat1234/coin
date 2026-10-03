# Fixed public TurtleRules and mature ATR dependency

Turtle: https://github.com/jesse-ai/example-strategies, commit `7c91e0a37bf62165790120d730442e4f6eb00364`, `TurtleRules/__init__.py`; MIT, raw SHA `35e4c3cd69010ca81402277693cb6f7deaf52a284153f20f25d4cf605701408a`.
Original ATR wrapper: Jesse commit `417f8765225e3bfc12043d4b712f19fe15a3c078`, raw SHA `398a12258dbc59b350c8c9ed8a1199a57cd89e7503c7dcd3fa002030c77df06c`; MIT notice reused at `third_party/jesse_example_donchian/JESSE_LICENSE`.

No original source is modified. Donchian scalar implementation directly reuses `third_party/jesse_example_donchian/donchian_indicator_original.py`; helper/config/requirements/license identities reuse the frozen RSI2 originals. The already installed official jesse-rust 1.3.0 wheel is used unchanged, without a new environment or installation.

Original ATR API: `atr(candles, period=14, sequential=False)`; Turtle calls period20. Jesse nonsequential helper retains the last240 candles. Donchian uses current-inclusive candles in this upstream class; it does not use Donchian strategy prior-bar semantics. No local TR/EMA/ATR recurrence is written.

Original before() fixes S1/entry20/exit10/ATR20/stop2ATR/unit-risk1%/pyramid threshold0.5ATR/max4. The class supports both directions, balance/ATR sizing, pyramiding, stop-loss and prior-profitable S1 filter. It specifies no timeframe. These are source facts, not a promise of a complete COIN execution replication.

This source task verifies original bytes, frozen installation identity and callable ATR/atr_last/Donchian API. It does not call numeric ATR, read market data, replay strategy or establish profitability, publication availability or native market qualification.
