# Minimum reproducible daily distribution experiment

This directory is independent distribution research on branch
`research/dist-pred-minimal-20261011`, based on recovery source546cb9bd.
See PROTOCOL.md and config.json for the frozen target, dates, model, scoring,
uncertainty and stopping gate; SOURCES.md records the paper/code discrepancies
and existing baselines. Historical results will be added after remote freeze.

Use existing Python3.12 with NumPy2.5.3, SciPy1.18.1, Polars1.44.2,
PyArrow23.0.1, PyTorch2.6.0+cpu and pytest9.1.1. No new environment install is
necessary in this workspace. The wrapper limits CPU threads to4, GPU off,
7.5GB address space,30min command time and15GB free disk reserve. This is the
explicitly authorized cloud adapter to the inaccessible original WSL launcher.

From repo root (set PY to the existing dependency interpreter):

```sh
PY=/workspace/coin/.venv/bin/python
R=research/distribution-prediction-20261011
bash "$R/bounded.sh" "$PY" -m pytest -q -o addopts= "$R/test_contract.py" --basetemp=/workspace/distribution-state/contract-new
git fetch origin e0d3400b23842f11f167a63e7d80856d76501de8
bash "$R/bounded.sh" "$PY" "$R/experiment.py" --state /workspace/distribution-state/run-new
```

The experiment restores only the2.25MB public archive from existing Git objects,
checks all hashes/CRCs, creates a new output directory, writes ATTEMPT.json even
on failure and emits actual per-epoch progress. Do not overwrite an attempt or
rerun completed fitting merely for convenience. Deterministic CPU algorithms
and fixed seeds support numerical reproduction within the recorded runtime;
different libraries/hardware can change exact model serialization and arithmetic.

Synthetic tests are correctness evidence only. Historical scoring is a separate
stage. Any economic wallet is a third stage requiring the frozen distribution
gate and a complete native decision/input contract; no wallet is started here
before that gate. No live APR, bot superiority, deployment or investment claim.

To reproduce the official-source audit separately, clone the official project,
checkout bf0a6554054735448ea02910e0ced335c7481969, then run:

```sh
bash "$R/bounded.sh" "$PY" "$R/audit_upstream.py" --upstream /workspace/dist-pred-upstream --output /workspace/distribution-state/upstream-new.json
```

Models, predictions and derived inputs stay under external task STATE. Small
structured results include their SHA and the source/config identities. The
original unpublished Q1/Q2 ledgers remain missing. Collector locked history
and the separate Momentum Transformer task are outside this directory.
