# One frozen paired continuation — completed, no additional training

Status: **RAW_POLICY_INCREMENT_ESTABLISHED_NATIVE_REQUIRED**. The original1024-step attempt remains
`STOP_RAW_POLICY_INCREMENT_NOT_ESTABLISHED`. This run is a crypto frozen-GP/Sharpe-objective adaptation,
not an exact paper reproduction or a pristine out-of-sample test. No native wallet.

Parent authorized the exact proposal at9a974947, SHA
33869fc5cf2d60951a6ed2fcd3b543df4849f8bb5dca4f47f9216247f9a2407b.
Fit source commit **bd5440c9e9c4f636c5417368a9d3d99811d42a9b**, remotely SHA/13public-file-byte
verified before any real update. Seeds2001/2002/2003, unchanged two arms,
63-step sequences/hidden16/tanh/Adam.001/batch128/clip1, frozen GP/scaler and
strict label maturity preserved. Archive e0d3400b / SHA
bdbcdc488fc4245c1fb6b433df1fc4bf806a120433db71e180816119cebbcc30 reused;
no provider download. Original2026Q1/Q2 ledgers remain unavailable and the
2026Mar–Sep collector lock remains closed. Separate return-distribution work untouched.

## Training adequacy

Exact six model/Adam/NumPy/Torch states restored at1024; next update1025
batch hashes were frozen in [prefit/PREFLIGHT.json](prefit/PREFLIGHT.json).
Train-only reader returned2526mature endpoints,719decision dates; inputs/targets/
rows/frozen artifact/source checkpoints hashed before updates. No new GP/scaler
fit. All6 advanced128-step common rounds. No validation access occurred before
[TRAIN_STOP.json](results/TRAIN_STOP.json) fixed the stop. Earliest allowed1408
was not reached by the flatness condition; common stop was **2048 hard cap**.
All6 have at least one of the final3 absoluteJ changes>.02: final local-flat
criterion **false**. No earlier qualifying common stop was skipped.

|Seed|Arm|J1024|J2048|Training J improvement|
|---|---|---:|---:|---:|
|2001|trend|-4.627899|-5.904888|1.276989|
|2001|trend_cpd|-5.338625|-6.488394|1.149769|
|2002|trend|-4.003343|-5.668461|1.665118|
|2002|trend_cpd|-4.764795|-6.214371|1.449576|
|2003|trend|-4.342086|-5.891290|1.549204|
|2003|trend_cpd|-5.303750|-7.176522|1.872773|

Training objective improved over the added budget, but last128 changes are
non-monotone in some models. Finite gradients/parameters/moments throughout;
actual update/weight ratios, clipping, epsilon and saturation are recorded in
[TRAINING_SUMMARY.json](results/TRAINING_SUMMARY.json) and complete FIT curves.
No numerical collapse observed; local convergence not established, no further
training permitted. Added51.889endpoint sampling epochs per model add no fresh
independent market information; overlap/asset imbalance and unknown effectiveN
remain. The pooled train Sharpe objective is not the fixed-five-asset portfolio.

## One final seen-development validation

Ensemble positions are averaged across all3seeds before nonlinear scoring;
fixed5asset denominator/cash mask, current vol/next mature return maintained.
483decision days/2415asset rows in saved [POSITIONS.csv](results/POSITIONS.csv).

|Block available dates (end exclusive; maturity purge)|Days|Trend SR|CPD SR|Increment|
|---|---:|---:|---:|---:|
|2023-01-01–2023-07-01|180|0.025581|1.039006|+1.013425|
|2023-07-01–2024-01-01|183|-0.774098|-0.041650|+0.732448|
|2024-01-01–2024-05-01|120|-0.956882|-0.123115|+0.833767|

|Seed|Aggregate trend SR|Aggregate CPD SR|Increment|
|---|---:|---:|---:|
|2001|-0.312199|-0.384604|-0.072405|
|2002|-0.896987|-0.357840|+0.539147|
|2003|-0.187396|1.348302|+1.535698|

Aggregate ensemble SR **-0.607225 →
0.129357**, increment
**0.736582**, frozen joint14day
1000replicate/seed9901 bootstrap95%CI **[0.035013,
1.372596]**. All four original gates pass.
One seed is negative, two positive. Gate thresholds and all financial assumptions unchanged.

Absolute validation SR declined in both arms relative to original1024 results
(0.235991/0.520626).
The larger relative increment accompanies greater baseline deterioration, so it
must not be called an absolute performance improvement. Training improvement
contrasts with lower validation SR: compatible with overfitting, not causal proof.
This continuation was proposed after prior validation inspection. Bootstrap CI
is conditional on seen history and does not correct repeated research/selection;
PASS is exploratory relative evidence, not independent generalization confirmation.

## Tests, audit, counts and resource evidence

28focused tests pass; full repository tests NOT_RUN. Prefit independent read-only
review fixes and synthetic-vs-real distinction in [prefit/REVIEW.md](prefit/REVIEW.md).
[SAVED_POLICY_AUDIT.json](results/SAVED_POLICY_AUDIT.json) PASS: independent
54training-checkpoint inference sets and18final validation readbacks, all source/
Adam ages/cumulative batches/paired RNG/common-stop/cash/purge/vol alignment,
CSV arithmetic and nonlinear bootstrap reconciled. Inference residual0, maximum
metric residual8.88e-16. Audit adds0fits/updates and
is verification of the single final evaluation, not a new model-selection query.
Original43MSE+47Sharpe+24diagnostic evidence files and12original external models
remain byte-identical.48new immutable round checkpoints stay external.

Scientific attempt3; fresh historical fits this attempt0, continuation segments6,
addedupdates6144, cumulative freshfits12/segments18/updates13824. No scientific
retry or search. Experiment internal36.024s; training guard
46.367s (includes imports/preflight),
sampled descendantRSS457658368B,
hostused1209769984B. Single CPU/thread,
GPU0/swap0, hard1200s unchanged. Output scan2683724B
below10MiB; reserve15GiB enforced. Resource guard reconstructed from authorized
recovery, not a byte-exact reconstruction of the lost original WSL guard.

Net profit/APR **UNKNOWN**. Costs/slippage/actual funding, executable publication-
to-fill latency, source-bound trade/quote/mark/index coverage, availability exits,
shared10k/abs30%/gross60%/isolated1x risk and paid terminal flat closure have not
been measured. Existing native engine is available but this483day policy has no
certified binding. Minimum gaps remain exactly the published
[NET_INPUT_GAPS.json](../slow-momentum-cpd-training-diagnostic-20261011/NET_INPUT_GAPS.json).
Raw Sharpe PASS does not establish profitable fast reversion or net investment ability.

## Minimal commands

Tests and audit are safe to rerun with fresh output names/state. The training
command below documents the one completed run; existing ATTEMPT/checkpoint
files intentionally prevent a silent rerun. Any future training requires separate
explicit authorization; do not extend this attempt.

```bash
export COIN_CPD_STATE=/workspace/slow-momentum-sharpe-continuation-state
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python -m pytest modules/slow_momentum_cpd/test_continuation.py modules/slow_momentum_cpd/test_diagnose_training.py modules/slow_momentum_cpd/test_core.py modules/slow_momentum_cpd/test_audit_sharpe.py -q --basetemp="$COIN_CPD_STATE/tests/fresh"
# Actual completed run at published source SHA, after prefit publication proof:
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python -m modules.slow_momentum_cpd.continuation --state "$COIN_CPD_STATE"
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python -m modules.slow_momentum_cpd.audit_continuation --state "$COIN_CPD_STATE"
```

Exact resume/audit needs original6external1024 models, new48checkpoint files,
existing archive and published source. Models are excluded fromGit by repository
policy; absent model bytes must be marked unavailable, not fabricated/retrained.
Audit writes an exclusive receipt; preserve the existing receipt before an
explicit read-only repetition. The static published result and CSV remain usable.
