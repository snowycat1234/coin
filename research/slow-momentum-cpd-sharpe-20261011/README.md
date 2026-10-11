# Sharpe objective correction, attempt 2

Execution of the already-published [frozen proposal](../slow-momentum-cpd-20261011/SHARPE_CORRECTION_PROPOSAL.json), SHA256 `8895319f41a91ebdb44a87fe67959c5f45c62cd7ad7c325fe87e0875eadc816b`.
This is a bounded frozen-GP crypto policy adaptation on seen development history.
Original MSE source, protocol, results and checkpoints remain unchanged.

Fixed six fresh fits, seeds2001/2002/2003, 1024 steps each; no search/retry/validation fit.
GP/scaler are reused from the exact predecessor training artifact; no new fitting.
Same63day last-head LSTM, hidden16, two paired inputs; tanh positions, negative
pooled captured-return Sharpe with epsilon1e-9 only in training. Evaluation has
no epsilon, uses a fixed five-asset denominator, and never turns missing future
outcomes into cash. Annual calendar365; current vol_t with realized r_t+1.
Headline policy returns are gross statistical proxies, without actual fills,
costs, slippage, funding, wallet caps/risk or paid terminal closure. Native net
profit/APR is UNKNOWN. Policy increment cannot itself establish fast-reversion profit.

Minimum commands, from this research branch:

```bash
export COIN_CPD_STATE=/workspace/slow-momentum-sharpe-state
mkdir -p "$COIN_CPD_STATE/tests"
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python -m pytest modules/slow_momentum_cpd/test_sharpe.py -q --basetemp="$COIN_CPD_STATE/tests/focused"
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python -m modules.slow_momentum_cpd.sharpe --state "$COIN_CPD_STATE" --archive /workspace/slow-momentum-state/source/features.zip --preflight
# Fit only after reviewed code/test/protocol commit is pushed and remote verified.
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python -m modules.slow_momentum_cpd.sharpe --state "$COIN_CPD_STATE" --archive /workspace/slow-momentum-state/source/features.zip
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python -m modules.slow_momentum_cpd.audit_sharpe --state "$COIN_CPD_STATE"
```

Use a fresh state for an authorized reproduction; existing attempts/checkpoints
are never overwritten. Archive option reuses existing 2.25MB Git-recovered bytes;
if omitted, the same local Git objects reconstruct it, no provider download.
Cloud guard is reused unchanged:1CPU,4GB address space, sampled2GB RSS/shared8GB
stop,swap0/GPU0,1200s hard wall,15GiB disk reserve. No collector changes, locked
reads,2026Q1/Q2ledger recovery claim,live/paid/credential or Library operations.
