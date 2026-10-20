Generated perpetual accounting consistency check

Run python -B run_generated.py and python -B -O run_generated.py from this directory. Standard library only. Output files are exclusive, so use a fresh copy without RESULT files for repeats.

108 synthetic cases cover two directions, two midpoint prices, three quantities, three cost settings and three signed funding rates. Explicit exceptions remain active under optimization. Checks include exact Decimal fees, execution, funding, flat terminal NAV, snapshot roundtrip, duplicate-fill/funding idempotence, and uninterrupted/restored state equality. No market history or credentials.

Three source files are byte-pinned copies from retained local Git. The recorded local commit is currently unavailable remotely; reproduction depends on vendored bytes. Public subset excludes the separately executed original provenance test and user fee snapshot. No personal metadata or private logs included.

An initial local fixture with quantity0.1 at price100 crossed opening minimum after adverse SELL pricing. Completed grid uses1/3/10 without account code changes. Fixture-domain correction, not engine defect. No historical replay, profitability conclusion or lost-run recovery is claimed.
