# Preregistered Transformer v2 research

Finite comparison of the unchanged old Transformer architecture, cross-asset utility,
cross-asset multitask and eight-day patch multitask. All fit three prescribed seeds,
two conditional funding interpretations and five expanding chronological folds.
Shared temporal attention is followed by asset attention. CLS, attention and last
readouts are learned together and averaged without choosing a winning pool.

The protocol is committed before any fit. Inner early stopping uses its own past-only
scaler, then the chosen number of epochs is refitted with the outer training scaler.
Utility remains a daily quantity-account proxy. Relative 7/30/60-day ordering and
market log volatility are masked auxiliary labels. No future gap filling is allowed.

```bash
python -m modules.transformer_v2.train \
  --state /external-state/transformer-v2 \
  --collector-root /external-state/collector \
  --work /external-state/collector-work \
  --source-run /external-state/original-collector-run
```

Execution requires CUDA; unavailable CUDA fails. Epoch checkpoints include weights,
optimizer, best state and all random generator states. A completed fit is hash-checked
and reused. A failed fit has at most one automatic retry. The original state is read-only.
Use a persistent service to retain the run when SSH disconnects. Epoch logs and
`train-progress.json` show stage, fold, seed, epoch, losses, GPU memory and measured ETA.

This is server execution. Windows only edits and transports source. Previous WSL
limits are unchanged. No new scientific runs are permitted on this Windows machine.

The 2026-03-01 through 2026-08-31 locked range cannot be loaded by development data.
No promotion or live orders occur here. Native economic evaluation, locked release
and final decisions must obey `reports/transformer_v2/TRANSFORMER_V2_PROTOCOL.json`.

After training, `evaluate` replays the fixed seed/ensemble/mapping targets through
the unmodified minute wallet and independent auditor. `audit_fits` checks every
checkpoint and exact train-only scaler. `final_fit --wait` waits for all five
development folds, then uses each seed's registered median inner epoch on mature
past labels only. `audit_fits --final-only` verifies those 24 final fits.

`pipeline` waits for the complete development report, commits the exact report
and candidate freeze, and requires the final-fit audit before releasing locked
archives. It performs one continuous locked experiment and publishes compact
final evidence and a registered A/B/C decision on this branch. The authenticated
host can then fetch and normally push the server's commits. There is no automatic
post-outcome rerun; one explicitly proven pre-account engineering repair preserves
its first failed attempt. Existing original collector locked guards are unchanged.

Real progress can be viewed without starting another experiment:

```bash
python -m modules.transformer_v2.watch --state /external-state/transformer-v2
```

The display includes authoritative service state, fit stage/fold/seed/epoch/loss,
CUDA memory and measured training ETA, completed distinct accounts and each live
account's actual minute count. Reset-wallet returns are never spliced into an APR.
