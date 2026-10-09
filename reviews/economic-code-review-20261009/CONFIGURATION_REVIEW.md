# Executed input and model configuration diagnosis

No additional configuration coding defect was verified. The actual frozen GRU and
latest-day MLP reproduce both published request files exactly, use the intended
named inputs and train-only scaler, and propagate the economic gradient into their
encoders. The evidence does identify missing explicit expert state, concentrated
feature scales and nearly binary allocations. These are measurable design
properties, not demonstrated explanations of poor historical returns.

This follow-up pins model/input/objective code to
`316423e2b4174bbf072814c1627861469a2e952b`, the two frozen no-cash snapshots to
`2bf2dc03e1ca3f0594b7b15dcff0cdb5651c5f1d`, and the compact training economic
contexts to `0090a7182c75a655197afd85f4db2c66db6456f6`. It performs no model fit,
optimizer step, historical native backtest or publication-time certification.

## Executed dimensions, masks and alignment

[`model.py:65–83`](https://github.com/snowycat1234/coin/blob/316423e2b4174bbf072814c1627861469a2e952b/modules/temporal_two_expert/model.py#L65)
constructs the GRU with input48/hidden32 and the MLP with48→96→32. Both concatenate
five ordered asset states into 160→32→one VOL/CS logit. Hooks on the actual frozen
models observe GRU inputs `[160,64,48]` and `[145,64,48]`, corresponding to32/29
decisions times five assets; MLP inputs are `[32,5,48]` and `[29,5,48]`.
Actual trainable parameter counts are **13,057 GRU / 12,993 MLP**, including the
single no-cash readout. The latest MLP deliberately uses only the final day; it
does not accidentally flatten the entire64-day window.

The assets are BTC/ETH/SOL/XRP/DOGE in explicit CORE5 order. The24 values are
six momentum horizons, four volatility horizons, four distances to moving
averages, range, volume z-score, premium, funding, four breadth horizons,
cross-sectional dispersion and market volatility. The last six preserve the
original ten-asset aggregate context and repeat across asset rows. This duplication
is intentional; none of the24 numeric features is constant over the907 actual
training rows. Validity masks are an additional24 channels, not replacement values.

[`model.py:131–154`](https://github.com/snowycat1234/coin/blob/316423e2b4174bbf072814c1627861469a2e952b/modules/temporal_two_expert/model.py#L131)
masks invalid numbers before arithmetic, standardizes observed values, and carries
GRU state over unavailable asset-days. The33/778 training windows with incomplete
CORE5 histories stay masked;745 windows have all64 asset-days observed. All61
development windows have every feature/time mask true. Therefore constant masks
on development are real availability facts, not evidence that training missingness
was discarded. A wholly missing latest asset state is suppressed at the joint head.

[`inputs.py:139–159`](https://github.com/snowycat1234/coin/blob/316423e2b4174bbf072814c1627861469a2e952b/modules/temporal_two_expert/inputs.py#L139)
ends64 consecutive completed calendar days at the decision. The feature-only
loader admits finite values and causal close observations, excluding future labels,
old ready256 gates and label-conditioned eligibility. The verified907-row scaler
union ends at `2024-04-29T00:00Z`, before the exclusive May1 cutoff. Every retained
target availability clock is at or before its decision, and every start execution
is exactly decision +60,000,001µs. The last training outcome matures at
`2024-04-30T00:01:00.000001Z`. The existing completed-bar availability proxy remains
an assumption about historical publication, not measured exchange release time.

## Scaling is correctly applied but dominated by a few observations

Recomputing the frozen scaler from the five 778-decision training episodes using
[`inputs.py:351–398`](https://github.com/snowycat1234/coin/blob/316423e2b4174bbf072814c1627861469a2e952b/modules/temporal_two_expert/inputs.py#L351)
reproduces the complete saved identity exactly:
`5c0085131d590e64316de3cc558e906f418bff50bc5d934339609da2c4b045ad`.
The 907 real rows are counted once across overlapping windows, shared across
assets, valid-only, population variance, without clipping. Development is never
passed to fitting. Both frozen state dictionaries contain this same mean/scale.

The choice of scale has a measurable consequence:

| Feature | Largest training observation | Share of total squared deviations | Latest-development std after scaling |
|---|---|---:|---:|
| funding | SOL raw `-0.171661376953125`, available2022-11-11 |83.04% |0.04157 |
| premium | SOL raw `-0.17475390434265137`, available2022-11-10 |94.94% |0.17274 |

Funding has4526 observed training entries, premium4523. Their largest standardized
magnitudes are61.31 and65.53. The next two funding observations contribute another
7.07% and3.64% of variance. Thus ordinary development variation in these channels
is compressed by the shared standard deviation. This is **verified scale
concentration**, not a zero feature collapse or demonstrated unit mismatch.

The producer defines momentum/distances/range as fractions, volatility as daily
simple-return sample standard deviation, breadth as a fraction, and `vol_z` as a
dimensionless rolling z-score:
[`make_labels.py:23–44`](https://github.com/snowycat1234/coin/blob/316423e2b4174bbf072814c1627861469a2e952b/modules/collector_research/pipeline/make_labels.py#L23).
Funding features sum the stored raw rates strictly within the completed day;
future execution-interval funding coefficients are separate objective inputs:
[`normalize.py:193–241`](https://github.com/snowycat1234/coin/blob/316423e2b4174bbf072814c1627861469a2e952b/modules/collector_research/pipeline/normalize.py#L193).
The inherited raw-rate unit convention and extreme source rows have not been
independently certified here. Do not delete them or label them corrupt based only
on magnitude. The feature producer payload and the executed input source are
hash-bound; no inconsistent train/development unit conversion was identified.

## Gradient flow works; output saturation is substantial

Actual snapshots reproduce every float64 exported request exactly on61 decisions.
With the evaluated charged-v2 economic request VJP, every encoder parameter tensor
has a finite nonzero terminal gradient. Maximum-coordinate central finite
differences of the full economic loss agree to2.10e-12 for GRU and1.09e-12 for MLP;
readout checks agree within5.78e-13. This checks the neural chain rule in addition
to the previously independently checked mapper/accounting VJP.

The initial zero readout causes exactly zero encoder gradient at initialization,
as expected from multiplying by a zero final-layer weight. The readout receives
the first update. The saved terminal encoders are not disconnected. Warm restart
does not zero them again: exact snapshot loading reproduces their trained outputs.

| Frozen arm | Training weights `<.01` or `>.99` | Development weights `<.01` or `>.99` | Median development sigmoid derivative |
|---|---:|---:|---:|
| GRU |493/778 |53/61 |0.00290 |
| Latest MLP |572/778 |42/61 |0.000728 |

The sigmoid derivative is `w(1-w)`, maximum0.25. Joint tanh preactivations have
absolute magnitude above3 in35.7%/32.0% of development elements, while final asset
states exceed absolute0.99 in only0.53%/0.75%. Readout/joint saturation is therefore
more pronounced than complete encoder-state saturation. Small derivatives can
slow adjustment, but boundary allocations can also be legitimate optima. This
does not prove an incorrect loss, bad initialization or a need for more parameters.
Both retained runs explicitly report `CAPPED_NOT_CONVERGED`.

## Information supplied to the decision head

[`model.py:115–174`](https://github.com/snowycat1234/coin/blob/316423e2b4174bbf072814c1627861469a2e952b/modules/temporal_two_expert/model.py#L115)
accepts values, feature validity and observation validity only. It does not accept
Context expert targets, expert eligibility, a calendar clock, past requests,
actual wallet positions, current budget or matured expert performance. Context
targets/eligibility/30-return history instead enter the mapper and economic loss.

| Information | Present or derivable | Missing or narrower than the economic context |
|---|---|---|
| Current VOL rule | Long direction is fixed; volatility/long history are represented. A complete GRU mom1 sequence can approximately reconstruct30-return covariance. | Exact configured-pool eligibility and risk-sized target are not explicit. Latest MLP vol30 cannot recover the full covariance matrix. |
| CS direction and risk | GRU64 has enough daily-return history to derive21-day relative returns and30-return covariance where observed. Latest MLP has mom20/mom60 and vol30. | Current weekly held rank, calendar phase, exact named signed target and expert validity are not explicit. Latest-day summaries are not the exact21-day/rank-history inputs. |
| Entry/exit threshold distances | SMA50/200 distances contain moving-average relation information, although those experts are not admitted in this two-expert model. | No explicit CS rank margin, held-rank age or Donchian threshold distance. Adding thresholds for unadmitted experts would expand scope. |
| Active/flat/directional state | Market history can encode portions of deterministic expert behavior. | The actual causal expert target used by the mapper is omitted. Flat is not synonymous with unavailable; a validity bit is needed. |
| Matured trailing net utility | Past market funding and returns are present. | Costed fixed-expert performance histories with actual maturity clocks are not inputs. Generic historical returns are not their equivalent. |
| Switching cost | The loss charges target changes and carries the shared wallet. | The head lacks actual prior budget/position state and cannot observe its own current switching requirement. |

The current model restarts each64-day encoding rather than carrying a policy
state across the economic episode. A structural synthetic witness uses the exact
recovered mapper: identical current Context and request `[0,.5,0,0,.5]` produce
budgets `[0,.95,0,0,.05]` or `[0,.05,0,0,.95]` after21 VOL-only versus CS-only
requests from CASH. One asset target differs by0.243 and changes sign. This proves
that the current action has state-dependent consequences; it does not prove
that two such states collide under one deterministic trained policy on this dataset.
Wallet omission is a hypothesis, not a verified coding bug. The previously failed
wallet-aware HGB experiment, supplied by the parent/user, remains relevant; its
exact source/results were not independently rebound in this review.

The frozen training-context recipe receipt at
[`0090a71…/TRAIN_CONTEXT_READY.json`](https://github.com/snowycat1234/coin/blob/0090a7182c75a655197afd85f4db2c66db6456f6/research/recover-frozen-runner-20261009/temporal-economics/TRAIN_CONTEXT_READY.json)
declares the January1,2024 weekly CS anchor and pins the signal source hashes.
The matching CS signal source at
[`55ac3d2…/public_cross_section_momentum.py:75–103`](https://github.com/snowycat1234/coin/blob/55ac3d2ee730b1cd1381696330a6abaf1925eb92/scripts/research/public_cross_section_momentum.py#L75)
is SHA256 `7d6f1794c0ade6e2c2d951a325e4e68ca45be0e87c84c68f05061442fad8a38f`.
Time-translating an identical synthetic265-day price history by three days changes
its weekly phase and reverses two raw CS directions. Existing feature values are
invariant to that translation; no calendar is forwarded by the Selector. Rebuilding
the retained H1 prices from actual past30 returns reproduces all56 CS target rows
after the first fully reconstructible weekly rank (May6) within2.78e-16, and all61
VOL rows exactly. All eight observed CS direction changes occur at the fixed
weekly phase0. The first five CS rows lack enough pre-window30-return history to
initialize the preceding weekly rank. Their reconstruction mismatch is a warmup
limit, not evidence of an incorrect recipe. The H1 fragment remains a different
container from the native input NPZ; the earlier saved-target-byte parity check
links its mapped targets to the registered native targets for the two frozen arms.
This establishes the recipe/context link for the stated56 dates, not the frequency
of identical feature collisions or a return gain from adding calendar/expert state.

The minimal demonstration is saved in [STATE_ALIASING.json](STATE_ALIASING.json)
and [state_aliasing_checks.py](state_aliasing_checks.py). It asserts the two CS
directions and exact source hashes, so it can fail if the omission claim's recipe
assumption is wrong. Its optional H1 check explicitly excludes ranks whose warmup
cannot be reconstructed rather than silently filling missing observations.

## One compact candidate, before implementation

If the combined code/research review selects an expert-aware input ablation, the
smallest defensible block is **the current canonical signed VOL/CS target for
each CORE5 asset, with their causal eligibility bits**. Use the exact named
Context quantities already bound to the decision, not newly rebuilt indicator
variants. This reveals current direction, flat state, relative composition and
the existing risk scale without making the encoder relearn the entire expert
recipe or infer an unavailable weekly phase. A zero target must remain distinct
from an unavailable target. The source availability clocks must be checked and
preserved. This block does not supply wallet state or future utility.

The recommendation is a candidate information ablation, not a promised improvement
or a selected new training run. Keep total trainable parameters fixed and freeze
the input-layout/control change before any fit; the exact layout remains for the
parent to choose after combining literature evidence. Do not add an indicator
catalog, tune expert thresholds, or assume the earlier HGB state failure is
invalid. No feature, architecture, optimizer or active training change is made
by this review.

The retired43-feature direct-path head already included expert targets and
eligibility. Restoring this information to the present temporal model is therefore
not a claim that expert-conditioned features have never been tried. Earlier
HGB/pair failures and the7-day-label versus20-day-ramp mismatch remain constraints;
this review does not propose a new7-day winner/advantage label.

## Evidence and reproduction

[`INPUT_CONFIGURATION_DIAGNOSIS.json`](INPUT_CONFIGURATION_DIAGNOSIS.json) records
all24 raw/standardized distributions, masks, extrema/concentration, scaler
provenance, actual activation shapes, snapshot identities, gradient norms and
four parameter finite differences.
[`input_configuration_diagnostic.py`](input_configuration_diagnostic.py) consumes
only the small verified feature archives, compact existing economic contexts,
scaler and frozen snapshots. Both model constructors/checkpoint sources match the
exported source hashes. It never loads a market archive or optimizer for execution.

Run inside the existing one-CPU,2GB,no-swap/no-GPU launcher with source316423e…
on PYTHONPATH. The evidence directory contains the verified feature NPZ/manifest
from the 2.25MB feature transfer at d901f13…, the 26KB development append at e0d3400…,
the compact training context/scaler and original H1_VALIDATE fragment:

```bash
python input_configuration_diagnostic.py \
  --evidence "$SMALL_VERIFIED_EVIDENCE" \
  --requests-root "$EXPORT_2BF2DC0/research/temporal-surrogate-resume-v2-20261009/native61-requests" \
  --prototype "$EXACT_RECOVERY/source/modules/direct_path/prototype.py" \
  --output "$NEW_STATE/input-configuration.json"

python state_aliasing_checks.py \
  --native-root "$SIGNAL_SOURCE_55AC3D2" \
  --temporal-root "$TEMPORAL_SOURCE_316423E" \
  --prototype "$EXACT_RECOVERY/source/modules/direct_path/prototype.py" \
  --original-portfolio "$SIGNAL_SOURCE_55AC3D2/modules/transformer_v2/portfolio.py" \
  --h1-context "$EXACT_RECOVERY/direct_path_fragments/H1_VALIDATE.npz" \
  --output "$NEW_STATE/state-aliasing.json"
```

The bounded input run passed in 12.8 seconds, maximum sampled RSS 488.8MB, zero
fits and zero optimizer steps. The asserted structural test passed in 7.0 seconds
with maximum sampled RSS 174.3MB. Resource evidence is saved separately. Tests establish the
stated narrow source/configuration facts; they do not demonstrate predictive
utility, unseen validation improvement or complete native-gradient equivalence.
