# Temporal two-expert selector

Code-ready, **economic training NOT_RUN**. One bounded comparison: shared
per-asset GRU64 against a matched latest-day MLP, each with NO_CASH and WITH_CASH.
No sweep, oracle classification, native wallet replay or data download is added.

|Architecture|NO_CASH parameters|WITH_CASH parameters|
|---|---:|---:|
|GRU 48→32, five final states, 160→32 head|13,057|13,090|
|Latest-day shared MLP 48→96→32, same final head|12,993|13,026|

The two arms share encoder and w-head initialization. Tanh and dropout 0.1 are
fixed defaults; eval disables dropout. One-layer GRU has no internal dropout;
explicit state/head dropout is used. CPU float64 retains the recovered mapper's
1e-12 simplex tolerance. There are no wallet observations or learned asset
targets. Wallet compounding and quantity carry remain inside the objective.

## Inputs and causal contract

`FeatureTimeline`/`load_feature_npz` require consecutive real daily calendar rows,
CORE5 order **BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, DOGEUSDT**, and these named24:

```
mom1 mom5 mom20 mom60 mom120 mom200 vol10 vol30 vol60 vol200
dist20 dist50 dist100 dist200 range vol_z premium funding
breadth1 breadth5 breadth20 breadth60 dispersion20 market_vol20
```

These are the existing `feature_frame` eighteen fields and `market_features`
six fields in `modules/collector_research/pipeline/`. Produce market aggregates
over the declared CORE5 universe, retaining the existing rolling/gap semantics;
bind that universe and all upstream input hashes in the producer manifest.
This module accepts precomputed features and does not regenerate labels/data.

NPZ fields, loaded with `allow_pickle=False` and an expected archive SHA256:

|Field|Shape/type|Meaning|
|---|---|---|
|values|D×5×24, floating|Unscaled causal features; invalid slots may be NaN|
|valid|D×5×24, bool|Per-feature observations; missing is never observed zero|
|step_valid|D×5, bool|Completed asset observation; false steps carry GRU state|
|completed_us|D, integer|UTC bar completion, exact day boundary|
|available_us|D×5×24, integer|Every valid feature available by its completion|
|source_sha256|scalar string|SHA of producer-verified source/input manifest|
|symbol_order / feature_names|string arrays|Exact orders above|

`timeline.windows(decision_us)` gives N×64×5×24 values and masks, ending at
each decision. Insufficient warmup and absent calendar rows reject; actual gaps
must appear as masked days. Per-asset states unavailable on the latest day are
masked before the shared head. The latest-day baseline sees only the last step.

Fit one `fit_standardizer([episode.windows, ...], training_cutoff_us=...)` for
all four models. It counts the union of actual training-window rows once, uses
valid observations only, shares each feature's mean/std across assets, uses
ddof0, replaces std≤1e-8 with one, and does not clip. Validation never enters
normalization. Real pre-episode history supplies features only, never extra
wallet resets or fabricated economic days.

## Output and unchanged economic objective

The returned E5 request columns remain CASH/VOL/SMA/DONCHIAN/CSMOM21. SMA and
Donchian are exactly zero. NO_CASH uses sigmoid w: VOL=1−w, CSMOM21=w.
WITH_CASH adds sigmoid s: CASH=1−s, VOL=s(1−w), CSMOM21=sw. Availability release,
initial CASH, risk and terminal flattening remain mechanical mapper behavior.

`exact.py` imports the recovered prototype unmodified, with SHA256
`46a0ca0b76bf29d50133bdd85b5730f4fd029f05378ce2ef086752b869a8fcab`.
It uses its actual `mapped_path`, `daily_proxy`, `mapping_vjp` and original
log-NAV-minus-five-times-negative-return-squared objective. Torch autograd
receives the exact exogenous request VJP. L1 active-set subgradients, release to
CASH, daily ramp≤0.1, allocated-leg gross≤0.6, per-asset≤0.3, covariance check,
10k shared capital, full fixed costs/funding and paid final flattening are
unchanged. This remains a daily proxy, not native execution certification.

`Episode` binds a complete producer-declared wallet interval, input identity,
role, active-label maturity and split cutoff. The forced terminal action follows
the original maturity exemption; its paid close is known at that decision.
Feature batching is independent of the
economic path: `training_loss` concatenates ordered requests, then rolls the
whole episode once. Separate real episodes retain independent wallets and
row-weighted losses; gaps are never joined into one wallet.

## Local commands and future fitting interface

Use the installed environment when available. A fresh Python 3.12 environment
can install CPU Torch from the official index and the other declared packages:

```bash
python -m pip install torch==2.6.0+cpu --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r modules/temporal_two_expert/requirements.txt
python -m modules.temporal_two_expert restore --recovery /absolute/state/new-recovery
python -m modules.temporal_two_expert check --recovery /absolute/state/new-recovery/source/modules/direct_path/prototype.py
```

The check command performs architecture inspection with a synthetic scaler;
that scaler cannot pass the training interface. Tests use synthetic losses for
optimizer/runner mechanics. Economic gradient checks perform no optimizer
updates; one read-only recovered fragment comparison preserves old checkpoints.

Run focused tests through the existing recovered bounded launcher, or the
repository's authorized WSL `with_task_progress.sh`/`bounded.sh` controls:

```bash
mkdir -p /absolute/state/tests/temporal
python research/two-expert-exact-recovery-20261009/runtime-delta/source/bounded_recovery.py \
  --report /absolute/state/temporal-test-resources.json --seconds 120 \
  python -m pytest modules/temporal_two_expert/test_temporal.py -q \
  --basetemp /absolute/state/tests/temporal/unique-run -p no:cacheprovider
```

After broader data and real warmup are bound, an explicit Python call to
`runner.train_steps(model, train_episodes, prototype, state_run_directory,
max_steps=..., feature_batch_size=..., checkpoint_every=1, max_seconds=120)`
starts one fixed CPU run. It uses matched Adam lr .001, clip norm1, no
validation selection. It is not called for economic fitting in this delivery.

Every completed update is checkpointed by default. Fsynced immutable model,
full Adam moments, Torch/Python/NumPy RNG, train/eval mode, completed step,
elapsed budget, input/split/source/config hashes precede an atomic latest
pointer. A local exclusive lock rejects duplicate live runs. Reconstruct the
original seeded model/scaler and call the same run specification/directory to
resume; completed runs return without new updates. Changed inputs, features,
split, source, dropout, batching, optimizer or stopping budget reject directory
reuse. A partial uncommitted generation is ignored. Cross-host shared-storage
locking is not certified. Use the existing bounded launcher for resource limits.

Required before fitting: broader pre-May2024 training coverage; real64 completed
days for every first decision; up to200-day underlying feature history (201
closes for mom200, or264 closes to make it valid across all64 input days);
complete execution prices/event-mark funding and eligible
expert targets bound to each full wallet. Masks preserve missing features but
do not certify missing economic outcomes. May–June2024 remains seen proxy
validation. Historical native restoration/validation is owned by the separate
task. Neither the old tiny failure nor engineering tests establish an economic
result for this selector.
