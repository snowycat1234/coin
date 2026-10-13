# Bounded protective replay runner, review only

Status: **NO PROTECTIVE HISTORICAL WALLET LAUNCHED.** This harness is new and
separate from the published, frozen policy commit
`7564139f27d0963d6cec34b72bc0e7b0a80bffa7` on
`research/isolated-protection-policy-20261013`. It uses the exact eleven
predeclared cases and does not change their sources, targets, account class,
financial scheduler, quantity profile, or policy threshold.

## Read-only check

From the scratch workspace root:

```
PYTHONDONTWRITEBYTECODE=1 coin_native_half_mix_20261013/.venv/bin/python \
  coin_margin_protective_runner_20261013/run_guard_cases.py --check-only
PYTHONDONTWRITEBYTECODE=1 coin_native_half_mix_20261013/.venv/bin/python \
  coin_margin_protective_runner_20261013/test_runner_synthetic.py
```

`--check-only` validates policy freeze bytes, all eleven exact year/arm inputs,
source index and all monthly source files, original target archive and saved
array bytes, the original transport ports/manifests and 2024 window SHA, plus
current host RAM, zero swap, disk margin, and two available CPU IDs. It does
not create any case state or instantiate a financial wallet.

## Execution gate and limits

The controller requires both the previously reviewed inputs and `--parent-go`,
plus a never-existing state* root under this module. No `--parent-go`
has been used. After explicit review/GO only, the proposed command shape is:

```
PYTHONDONTWRITEBYTECODE=1 coin_native_half_mix_20261013/.venv/bin/python \
  coin_margin_protective_runner_20261013/run_guard_cases.py \
  --state-root coin_margin_protective_runner_20261013/state \
  --parent-go
```

The controller queues all eleven cases in fixed manifest order, uses at most
two distinct one-CPU children, caps each child at 4GB address space, 2GB
sampled RSS, 1200 CPU seconds, and 1200 wall seconds, and stops if host used
RAM exceeds 8GB, swap activates, or free disk falls below 15GiB. It checks
RAM and disk before each admission with full commitments for all active plus
new workers. Child launch requires a controller-created GO binding and a
matching per-run nonce. Python optimization is disabled to keep the frozen
monthly source-hash assertions active. There is no GPU, new leverage, top-up,
historical fit, or replay of original wallets. A resource or process failure
stops the remaining queue and retains genuine already-written state.

Each case gets a fresh exclusive BINDING, initial lossless native checkpoint,
30-day and terminal/stop checkpoints, original account journals, minute numeric
fingerprint, genuine signed-inventory/Nav bridge, and a result that distinguishes
full-calendar paid-flat return from a stopped/marked-only observation. Final
checkpoint pointer state/rows/cursor/stop and gzip snapshot SHA must equal the
live account before a result is written. An unfilled protective intent at the
calendar end is explicitly not labeled COMPLETE. Paid PnL/return fields are
null unless the full calendar is complete and flat. The
frozen financial account is still conditional research economics, not a claim
about historical exchange liquidation.

## Review cautions

- Resource RSS is sampled, not kernel peak. No shared cgroup was verified on
  this host, so the process and host-level observers are an operational guard,
  not a claim of kernel-enforced aggregate containment.
- An OS kill may leave a genuine but older last checkpoint. It must not be
  presented as a completed case. The controller records a failure and stops.
- Final result-time pointer parity does not rehash every checkpoint day NPZ.
  Checkpointing hashes them when written; full cold restore is a later audit.
- The policy's `NOT_EVALUABLE_UNEXECUTABLE_RISK_REDUCTION` can stop a protected
  case before flat, halt or calendar end. Resource and financial stops remain
  distinct, including genuinely unfilled full protective exits.
- Comparisons to frozen original baselines must use the exact same year/arm,
  retain all eleven cases and negative results, and never call marked but
  non-flat PnL a paid return. The runner saves individual cases; a separate
  audited comparison after replay is required.

Expected runtime after GO is approximately 4–6 minutes per case from frozen
native baselines, ~45–70 minutes sequential or ~25–40 minutes with two workers,
plus audit. This is an estimate, not measured guard replay runtime.
