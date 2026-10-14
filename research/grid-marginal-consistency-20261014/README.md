# GRID marginal consistency diagnostic

Offline, standard-library-only descriptive analysis of four immutable public saved daily-result files. See REPORT.md for the finding, DIAGNOSTIC_PLAN.md for the predeclared scope and formulas, and SOURCE_CATALOG.json for public source references and integrity hashes.

Run from this directory with Python 3.10 or newer:

```sh
python analyze_grid_marginal.py
python -m unittest -v test_grid_marginal
python check_grid_independently.py
```

The main analysis regenerates five files under results/. It validates daily source Git blob and SHA-256 hashes, the allowlisted financial extracts, complete paired calendars, initial balances and terminal reconciliation. It never accesses a network or imports a trading/research engine. No external packages are needed.

The nine tests are bounded checks of calendar completeness, telescoping arithmetic, native terminal reconciliation, exact-zero denominators, zero-anchored dollar drawdown, peak/trough dates, return correlation, rejection of invalid inputs, best-month contribution subtraction, and byte-identical reproduction. An independently written checker verifies the full output from the same permitted inputs.

The summary extracts intentionally contain only ordinary financial fields. Their source public Git blob hashes identify the complete public originals; the extract SHA-256 hashes identify the exact inputs used here. Daily increments are published decimal values, not recreated unrounded native engine numbers.

This is an analysis of selected seen-development paths, not a new backtest, risk-parity certificate, confidence interval, live-return estimate or month-selection strategy. CASH means the BTC-cash replacement control with the rest of the portfolio still active; it does not mean the entire wallet is cash or identify the original CSH strategy.
