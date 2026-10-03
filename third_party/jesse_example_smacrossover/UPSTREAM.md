# Pinned public SMA crossover source

Repo: https://github.com/jesse-ai/example-strategies
Commit: `7c91e0a37bf62165790120d730442e4f6eb00364`; original `SMACrossover/__init__.py`.
Unchanged strategy: 1809 bytes, SHA256 `453440d7b934c494934a1c56b3826d94638594f79ad4e4c7faaff36b96d33fae`, Git blob `1d971f62367251d30975ad1a4f9b9886d4c47153`.
`LICENSE` reuses the same-commit original MIT bytes, SHA256 `80d873148413a3eb2f96bbe22657bf57ae42046e4d95e81852109c5f3a949d2d`.

Original class uses SMA50 > SMA200 for long eligibility and < for long liquidation; equal values preserve existing state. It is a state predicate, not a crossing event. The upstream class also supports shorts and whole-balance sizing and specifies no timeframe.

Planned COIN port fixes closed UTC1d, long-only, fresh-flat scoring and shared capital/risk/latency/Bybit fee proxy accounting. No upstream sizing or short hook is executed. Raw vendor bytes are unchanged; no Jesse framework/dependency is installed. This provenance operation does not test a target, account, profitability or future eligibility.
