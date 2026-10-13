# Frozen complete-2024 five-arm source and target preflight

`PROTOCOL.json`, `targets_2024.py`, `mark_gap_bridge.py`, the ten-row
`derived_mark/` overlay, `test_frozen.py`, and `HISTORY_REPRO_QA.json` freeze
the 2024 recipe before 2024 targets or financial accounts are generated.
Original market files and missingness are kept unchanged. The bridge overlays
only ten absent August-12 mark OHLC bars for a separately identified source
sensitivity. It does not create trade, funding, volume, signal or wallet data.

The original target functions are imported from an existing public checkout:
`scripts/research/public_cross_section_momentum_compat.py`,
`scripts/research/cs_numpy_risk_compat.py`,
`research/portfolio-risk-budget-20261012/risk_budget.py`, and
`modules/transformer_v2/portfolio.py`. The target builder checks their exact
SHA-256. The new research branch must retain those exact files. A branch based
on `research/static50-sma-half-proxy-20261013` includes them; otherwise copy
the original exact blobs before running the builder. The optional saved-year
regression requires the four original target NPZs and original Y2023/Y2025
daily-close NPZs at their previously published SHAs. Do not substitute a
recomputed or shortened packet.

Local preflight, with the current cloud restoration directories:

    python coin_expanded_coverage_20261013/targets_2024.py \
      --repo coin_cs_sma_recovery_20261013/repo \
      --inputs coin_cs_sma_recovery_20261013/inputs \
      --saved coin_strong_candidates_20261013 --verify-history
    python -m unittest discover -s coin_expanded_coverage_20261013 \
      -p 'test_frozen.py' -v

For a new public checkout, stage the original Y2023/Y2025 NPZs in an input
directory and the original `STATIC50_Y2023.npz`, `STATIC50_Y2025.npz`,
`SMA200_Y2023.npz`, `SMA200_Y2025.npz` in a saved directory. Set
`COIN_REPO_ROOT`, `COIN_INPUTS_DIR`, `COIN_SAVED_TARGETS_DIR`, and optionally
`COIN_JULY_WRAPPER` for the raw-wrapper integration test. For example:

    COIN_REPO_ROOT="$PWD" COIN_INPUTS_DIR="$TMP/inputs" \
    COIN_SAVED_TARGETS_DIR="$TMP/saved" \
      python -m unittest discover \
        -s research/expanded-frozen-2024-20261013 -p test_frozen.py -v

`test_frozen.py` does not create 2024 targets. After parent-verified remote
publication, the target-only command is:

    python research/expanded-frozen-2024-20261013/targets_2024.py \
      --repo "$PWD" --inputs "$TMP/inputs" --saved "$TMP/saved" \
      --verify-history --prepare-2024 --output "$TMP/Y2024_TARGETS"

The output 366-day matrix and proof must be remotely published and verified
before any financial run. Native source still requires full-year trade, mark,
funding and original account-profile admission under `PROTOCOL.json`. The
original public July/August wrapper restored here is SHA-256
`d86a50dee14ea13df4a83fc8d5d90ec1ab0d42e352f430173d759b094c96013e`.
The existing H1 wrapper is
`a998b786d781a5dd314c6efb44dc55702972977b9bdf2fea315426b7c4362deb`;
`H1_GRID_QA.json` confirms all 60 Jan–Jun original trade/mark monthly
streams have complete exact 1m grids, with no economic simulation.
