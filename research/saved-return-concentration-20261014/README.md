# 2023 saved-return concentration audit

Two completed, already-public daily result series, analyzed without executing a strategy or reading market data. Diagnostics were chosen before calculations. See [REPORT.md](REPORT.md) for findings and limits, [DIAGNOSTIC_PLAN.md](DIAGNOSTIC_PLAN.md) for definitions, and [SOURCE_CATALOG.json](SOURCE_CATALOG.json) for immutable public source URLs and Git blob identities.

## Reproduce

Python 3 standard library only; no installation or network required:

```sh
python -m unittest -v test_arithmetic.py
python analyze_saved_returns.py --output results
python crosscheck_decimal.py
```

The analysis and Decimal cross-check each enforce 120-second CPU and wall-alarm limits and a 2 GiB address-space cap on Linux. Six public JSON inputs total 141,923 bytes. Every analysis run verifies their expected bytes and Git blob hashes, recalculates SHA256, validates all 365 contiguous UTC days, and reconciles final NAV and both published 30-day loss diagnostics. Output timestamps, timing and resource use vary on rerun; numeric results should agree within floating-point tolerance.

- `results/RESULTS.json`: full diagnostics, exact window dates, top-day observations and limits.
- `results/MONTHLY_CONTRIBUTION.csv`: all 24 calendar-month rows; monthly return and additive contribution are distinct columns.
- `results/*_DAILY_DERIVED.csv`: daily NAV and returns reconstructed from saved increments.
- `results/VERIFIED_SOURCES.json`: URLs, pinned commits, bytes, Git blob and SHA256 verification.
- `results/RUN_RECEIPT.json`: bounded-run receipt and output hashes.
- `DECIMAL_CROSSCHECK.json`: 68 independent 50-digit Decimal/end-point numeric checks.
- `INDEPENDENT_ARITHMETIC_CHECK.json`: separately calculated raw-input verification of headline results, using an independent sequential-float calculation. Tiny terminal rounding differences are expected.
- `TEST_LOG.txt`: nine synthetic arithmetic tests.

The inputs retain the original published text exactly. `FILES.json` inventories this package. These are seen-development diagnostics with different risk settings, not an out-of-sample test, matched experiment, live margin certification, executable deletion strategy or APR estimate.
