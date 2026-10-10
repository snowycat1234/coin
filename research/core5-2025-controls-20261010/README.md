# 2025 fixed expert controls, no selector training

Four policies declared before replay. Each starts with its own 10,000 USDT shared CORE5 wallet and closes for a charge on 2025-12-31. Results must not be added together. Source period: 2025-01-01 to 2025-12-31, 364 active intervals, BTC/ETH/SOL/XRP/DOGE. Daily 00:01 trade execution; actual signed funding with prior marks.

| Policy | Net PnL USDT | Cumulative return | Daily max drawdown | Average actual gross |
|---|---:|---:|---:|---:|
| VOL | -296.43 | -2.9643% | 8.6620% | 14.7049% |
| CS momentum | +2130.10 | +21.3010% | 3.5248% | 47.2127% |
| MOM30 SHORT | +324.64 | +3.2464% | 7.9121% | 11.0082% |
| Static VOL/CS 50:50 | +896.32 | +8.9632% | 4.0217% | 25.0760% |

SHORT contributed +522.06 USDT during February (+5.2944% on that month's opening NAV) and +319.36 during November (+3.2329%), but July and September lost -225.15 and -256.81. These are contributions within one continuous annual wallet, not month-reset backtests or labels proven predictable. Other months are all disclosed in MONTHLY.json.

Costs: 5.5bp fee, 4bp half-spread, 4bp slippage per side, actual funding, charged final flat. Original 1x isolated context, 60% portfolio and 30% asset caps, 10% ex-ante covariance volatility target, L1 allocation ramp0.1. Actual exposure differs materially between controls: no equal-risk superiority claim. CS net exposure averages effectively zero while gross47.21%; net neutrality does not remove gross risk.

All 1460 saved rows independently reconciled price PnL, funding and transaction costs, maximum absolute NAV residual1.82e-12. CS triggered35 daily boundary risk reductions; costs retained. This is a daily full-fill research replay, NOT native minute liquidation/execution validation despite the underlying minute source being complete. Native CS risk/turnover execution checks are especially important. No parameter search, selector inference or optimizer updates.

2025 is now inspected development history. Do not train on it then describe earlier July/Q4 2024 as new out-of-sample. More years and chronological future-period validation remain necessary. These annual-period cumulative results are not an APR estimate, future promise, or evidence of beating most live Bybit robots. A same-period same-risk Bybit-style comparator and representative robot population data are absent.

Next: complete expanded history and continuous short-advantage diagnostics, then predeclare limited training-only balancing vs original-distribution controls. Preserve intact chronological wallets; do not create a strategy by selecting profitable months after seeing outcomes.

Inputs: https://github.com/snowycat1234/coin/tree/818bb756453aed6ce82aeb572362baecb27bb9e6/research/core5-2025-consumer-20261010
