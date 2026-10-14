# Saved execution-cost headroom

Read REPORT.md for findings and limitations. This is offline static arithmetic, not a trading simulation.

Run from this directory:

    python analyze_cost_headroom.py
    python -m unittest -v test_cost_headroom

Inputs are allowlisted ordinary financial fields from six already-public saved summaries. SOURCE_CATALOG.json maps them to immutable public originals. results/RESULTS.json contains exact-string finite arithmetic, ratio approximations and exact rational threshold pairs. No packages, credentials, downloads or external data are required.
