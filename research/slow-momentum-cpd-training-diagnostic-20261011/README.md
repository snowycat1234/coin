# Read-only training adequacy diagnosis; continuation pending review

The existing six fits continue to improve their recorded training diagnostic.
This supports one bounded optimization-adequacy continuation proposal, but does
not establish generalization, investment ability or numerical convergence.
The original1024-step `STOP_RAW_POLICY_INCREMENT_NOT_ESTABLISHED` remains intact.
This follow-up executes **zero optimizer steps, gradients, model forward passes,
validation queries, new fits or wallets**. Seeded model objects are constructed
only to verify initial parameter hashes; no model training takes place.

| Seed | Arm | Final full-train epsilon-loss | Improvement896→1024 | Improvement768→1024 | Last Adam update / weight L2 |
|---|---|---:|---:|---:|---:|
| 2001 | trend | -4.627899 | 0.486871 | 0.655914 | 0.1043% |
| 2001 | trend + CPD | -5.338625 | 0.446733 | 0.755792 | 0.1075% |
| 2002 | trend | -4.003343 | 0.166400 | 0.520434 | 0.1863% |
| 2002 | trend + CPD | -4.764795 | 0.164285 | 0.474248 | 0.1430% |
| 2003 | trend | -4.342086 | 0.109764 | 0.209122 | 0.1479% |
| 2003 | trend + CPD | -5.303750 | 0.059718 | 0.213383 | 0.1558% |

The full-data diagnostic is algebraically reconstructed from the saved training
mean and population variance: `J=-sqrt365*mean(z)/sqrt(var(z)+1e-9)`. All eight
successive128-update checks improve for every fit. This is distinct from the
stored loss of one **different, pre-step minibatch** at each check, which varies
substantially and is not a monotone convergence curve. The expected minibatch
ratio is also not the ratio of the full-data moments; J is a useful full-train
diagnostic, not proof of stationarity for the stochastic training objective.

The old absolute unregularized pooled-SR tail threshold0.02 is a heuristic,
not a statistical test, gradient criterion or economic convergence criterion.
Sharpe is nonlinear, annualized and nearly invariant to positive exposure
scaling; a low-volatility policy can have high SR. Nevertheless, this heuristic
is **not the main explanation here**: the actual epsilon-loss still improves
0.209–0.756 over the last256 steps. Final epsilon fractions are0.340–1.398%,
positive captured/position variances and zero saturation. Do not replace the
original flag, relax evidence gates or call the runs converged.

Numerical failure is **not observed** in recorded checkpoints. All saved weights,
Adam moments and recorded losses/gradients are finite; second moments are
nonnegative. All48 recorded gradient checks exceed the clip1 threshold,
with preclip norms7.516–104.029. Only eight checks per fit exist, so the fraction
of all1024 updates clipped is UNKNOWN. Large Sharpe gradients alone do not
establish instability; low return variance and scaling can amplify derivatives.

The final Adam moments algebraically estimate the **last already executed**
update, not a next step: L2 norms0.00722–0.01305 versus weight norms6.845–7.043;
maximum coordinate estimates0.000642–0.001329. Float64 diagnostic reconstruction
can differ from actual float32 Adam rounding. These global ratios do not bound
function changes or individual near-zero-weight relative changes. Earlier
update-norm history and raw per-update losses/gradients were not saved and
cannot be reconstructed truthfully without a new training replay. None was run.

All six checkpoints contain model tensors, complete Adam moments/step1024,
Torch RNG and NumPy bit-generator state. Groups retain lr0.001, betas(.9,.999),
eps1e-8, zero weight decay, no AMSGrad/maximize. Pair RNG states and exact prior
1024 minibatch hashes reconcile. Baseline dormant CP input coefficients are
unchanged from seeded initialization. Only final1024 model checkpoints were
saved in attempt2; earlier model states are unavailable. Restoration can start
from the actual final weights/moments, rather than reinitializing or fabricating
earlier checkpoints.

Training covers **2526 mature asset endpoints across719 decision dates**:
BTC719, ETH719, SOL154, XRP406, DOGE528. Earliest decision2021-01-11, latest
2022-12-30; latest label2022-12-31, strictly before2023. Pooled asset-endpoint
Sharpe is not a719-day shared-wallet Sharpe; unequal asset observation counts
also weight the training loss differently from a fixed /5 calendar portfolio.
The effective independent sample count is UNKNOWN.

For each seed the exact recorded1024 replacement batches are regenerated
without training:131072 index draws, **51.889 endpoint-epoch equivalents**,
every endpoint visited,27–80 visits per endpoint across the seeds. This is not
failure to cover the dataset. Mean128-slot batches contain116.72–117.03 unique
dates and2.40–2.46% duplicate draws. Among pairs of slots,4.64–4.65% use the
same asset with overlapping63-day input windows; the mean shared-window fraction
is2.39–2.40%. These are input-overlap descriptions, not return covariance or an
ESS estimate. Conditional on this fixed dataset, the replacement indices are
independent RNG draws; the underlying market observations and features do not
become independent information by being redrawn. Features have even longer
history than the63-day input window. More steps add optimization, not new data;
overfitting remains possible.

The training-only reader uses Parquet predicates **before feature derivation**,
returns only UTC bar starts with `dt+1day<2023-01-01`, and retains2020 warmup.
Opaque public archive/member bytes are hashed for provenance; no post-training
rows or validation policy metrics are used. It never calls the existing
`prepare`/`load_close` paths that construct validation. Same archive SHA
`bdbcdc488fc4245c1fb6b433df1fc4bf806a120433db71e180816119cebbcc30`, same mature
endpoint hash `983baa27d9c0105c48b7c7debfea24089c28bff277014e1e43e2b27721d9e50f`.
[DIAGNOSTIC.json](results/DIAGNOSTIC.json) contains complete curves, optimizer
summaries, exact index hashes, checkpoint/input identities and limitations.

[CONTINUATION_PROPOSAL.json](CONTINUATION_PROPOSAL.json) is frozen as
`NOT_RUN_PENDING_PARENT_REVIEW`, SHA256
`33869fc5cf2d60951a6ed2fcd3b543df4849f8bb5dca4f47f9216247f9a2407b`:

- Continue both arms for the same seeds2001/2002/2003 from the exact six1024
  checkpoints, restoring complete Adam then both RNG states; start at the
  original next minibatch1025. Same data/GP/scaler/model/optimizer/loss.
- Six models advance in common128-update rounds, with at most1024 additional
  updates each. All must reach the same global step before any stop decision.
- At the first common step k≥1408 where **each of six** has all three adjacent
  absolute full-training J changes≤0.02, stop all at that current checkpoint.
  Thus four points are needed, initially1024/1152/1280/1408. Otherwise stop all
  at the fixed2048 cap. No best checkpoint, individual stop or validation choice.
- Numerical failure stops INVALID without retry. Record actual update norms,
  gradient summaries, variance/epsilon/saturation and immutable checkpoint
  lineage; these are diagnostics, not extra post-hoc stop/adoption gates.
- Only after the common training stop is fixed, perform one final evaluation
  and the **unchanged** four policy gates/bootstrap. No interim validation,
  seed selection, learning-rate/clip/batch change or later update extension.

This is a prospective local-plateau diagnostic, not a convergence guarantee.
The proposal follows already inspected validation history, so a futurePASS
would still be seen-development evidence with selection limitations. It cannot
retroactively repair attempt2 or become independent confirmation of the paper.
One new scientific attempt if executed:6 continuation segments/0 fresh training
initializations; actual new updates `6*(k-1024)`, range2304–6144; cumulative
scientific attempts3, fresh fits12, training segments18 and updates9984–13824.
These formulas/ranges apply to normal common-step completion only. A mid-round
numerical/resource failure can leave unequal segment counts and fewer2304 total
updates; record actual confirmed per-segment counts, with unlogged tails UNKNOWN,
and run no validation. Current totals remain2 attempts/12 fits/7680 updates.
No continuation runner
has been implemented or run; review authorization and a published tested
source/protocol commit are required before any continuation optimizer step.

Estimated continuation1–3minutes including monitoring/checkpoints/evaluation,
using the previous6144-update32.236s internal/37.047s guard run as a reference.
This is an estimate, not a benchmark. Hard1200s remains,1CPU/thread, GPU0/swap0,
4GB address space, sampled2GB RSS/shared8GB host-used stop,10MiB extra outputs,
15GiB disk reserve; no new downloads, paid services, credentials or wallets.
The six per-arm budgets and seeds are equal at any common stopping point.

[NET_INPUT_GAPS.json](NET_INPUT_GAPS.json) distinguishes an available frozen
native engine from missing **binding/certification**, not necessarily absent
market bytes. The existing native61 engine SHA318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585
is a reusable reference, not a certified483-day CPD wallet. Minimum remaining
needs are source-bound trade/quote/mark/index and actual signed funding with
complete policy/closure coverage; actual fee/filter/contract/MMR profiles and
units/clocks; causal publication-to-fill latency, target mapper, masks/exits,
capacity/partial fills and purged-boundary behavior; shared10k/abs30%/gross60%/
isolated1x risk handling; charged terminal flat closure and independent capital
conservation. Close-only daily features, assumed BASE27/cross-venue costs or
free exits cannot substitute. **No native wallet/net return/APR measured.**
Original2026Q1/Q2 ledgers remain unavailable and the2026Mar–Sep lock remains closed.

Four focused diagnostic tests pass: closed-form Adam moments, sampling/overlap,
and future-row exclusion for both naive and UTC-aware timestamps. The initial
test fixture hit a missing temporary-parent directory; the initial diagnostic
reader rejected a timestamp-zone mismatch before feature/model computation.
Both failures and resource receipts are preserved, then corrected in the
isolated namespace. They add zero scientific fits or retries. Full repository
tests are NOT_RUN; original fits/results and both earlier evidence manifests
remain unchanged. Successful diagnosis2.330s internal/10.272s guard, sampled
RSS312,975,360B; concurrent tests share a CPU so these timings are descriptive.

Minimal **read-only** reproduction, fresh diagnostic state, existing models
and archive (does not start the continuation):

```bash
export COIN_CPD_STATE=/workspace/slow-momentum-training-diagnostic-reproduction
mkdir -p "$COIN_CPD_STATE/tests"
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python -m pytest modules/slow_momentum_cpd/test_diagnose_training.py -q --basetemp="$COIN_CPD_STATE/tests/focused"
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python -m modules.slow_momentum_cpd.diagnose_training --state "$COIN_CPD_STATE"
```

If the six external models are unavailable, exact Adam/update/RNG diagnostics
cannot be recovered from JSON alone; use the published static report and mark
the model inspection unavailable. Do not retrain or substitute approximate
optimizer state under this read-only command. Models/full logs stay external;
small code/protocol/evidence are committed on the existing independent research
branch, without changes to the separate return-distribution work.
