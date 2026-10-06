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
