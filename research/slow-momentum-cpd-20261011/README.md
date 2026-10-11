# Slow momentum / CPD minimum experiment

Completed: **STOP_PREDICTION_INCREMENT_NOT_ESTABLISHED**. The complete
[result](results/RESULT.json), [2,209 saved forecasts](results/PREDICTIONS.csv),
[training freeze](results/FROZEN_TRAINING.json), and
[read-only reconciliation](results/SAVED_RESULT_AUDIT.json) preserve this negative
finding. Protocol/source were published and remote SHA verified before the one
real scientific attempt (code commit `abea0de9ec9f2e69d8d6212f10b89313bfb9cabb`).
The subsequent [complete gate audit](results/SAVED_RESULT_GATE_AUDIT.json) verifies
all five gates, every CSV record and actual training scaler/GP observation axes
with pure arithmetic, adding zero fits and zero repeated LSTM inference sets.

|Seen validation|CPD ensemble MSE improvement vs trend|Daily rank-IC increment|
|---|---:|---:|
|2023 H1|−0.250%|−0.03667|
|2023 H2|−0.088%|+0.02295|
|2024 Jan–Apr|+0.106%|−0.11750|

Only one block and one seed improve aggregate MSE. Date-mean squared-loss
improvement is −0.000970, 14-day bootstrap95% interval [−0.003615,+0.001896];
all five frozen gates fail. Both learned arms also fail to beat the training-mean
MSE control on the last two blocks. This fixed small-budget result does not
establish model convergence or disprove the paper's original online/Sharpe method.
There was no seed selection, horizon/window/threshold search or extra fit.

Actual counts: one attempt, six LSTM fits, 1,809 parameters per arm, 1,536 total
updates; one GP group/two optimizers (23/51 iterations, both report convergence),
zero validation fits, zero wallets/provider downloads. Fourteen focused tests and
Ruff pass. Initial pytest infra failure is retained; independent review's two
implementation findings were fixed before the real fit. Full repository tests
and native economics are NOT_RUN, appropriate to this isolated prediction module.
Saved forecast metrics reconcile within4.45e−16, all18 frozen inference sets are
bit-identical, paired initial/RNG states and allAdam256 ages pass. Synthetic
mechanism tests are not counted as market results.
The first audit checked inference and reported MSE/rank/bootstrap; independent
review identified missing explicit gate/record-coverage checks. The later audit
adds those checks and recomputes unique training observations/normalisation,
preserving both receipts and every original result byte. No science rerun occurred.

Measured experiment13.018s; complete bounded command17.752s. Sampled descendant
RSS maximum373,628,928B; shared used-memory maximum1,164,230,656B. Resource receipts
are in results/receipts; sampling is not a kernel peak. Context, Git-object fetch,
implementation and human/model reasoning time are outside those command timings;
unmeasured intervals remain UNKNOWN. No new permission prompt or tool denial arose.

One frozen, paired **prediction mechanism adaptation**, on already-seen historical
crypto data. Hypothesis and complete finite recipe are in [PROTOCOL.json](PROTOCOL.json).
This does not reproduce the paper's Sharpe-trained trading DMN. MSE output is a
forecast, and cannot establish that a model has learned profitable fast reversion.

Paper [2105.13727v3](https://arxiv.org/abs/2105.13727v3) uses an LSTM with
volatility-scaled historical returns/MACD, plus Gaussian-process changepoint
location and severity. Reversal is learned implicitly through positions; there
is no separate reversal head or selector. Its 50 traditional CLC futures and
1995–2020 results provide no crypto-performance evidence. The specified official
[repository](https://github.com/kieranjwood/trading-momentum-transformer/tree/e0352cb0bdbf8045accb1bf1a5705ae0cb9ea624)
also contains a later Transformer paper, which is outside this experiment.

Our two arms share eight trend inputs, 63-day LSTM, exact initial weights, sample
axis, minibatch order, and 256-update budget at three prescribed seeds. Only the
two CPD information channels differ. Stationary and left/right Matérn parameters,
noise, steepness, return scaling, and feature scaling are fitted before 2023 and
frozen. Inference computes likelihoods on a fixed six-location grid with uniform
prior; it never refits a GP or scaler. Code-style **age** is the opposite of the
paper's gamma. Severity equals 0.5 for equal evidence and is not event probability.
Missing bars reset rolling history. No backward fill, synthetic prices, oracle
label or future economic feature enters inference.

The recovered feature archive has original public-market evidence Parquets and
an earlier 24-feature model payload. This new adaptation explicitly reads only
`dt,close,complete_kline,symbol` from the evidence tables to derive the eight
paper-inspired inputs; it does not import other evidence columns or silently
relabel the old 24-feature NPZ. Archive and member identities are verified. 2020
is warmup, 2021–2022 training, and three later blocks are **seen development
validation**, never pristine OOS. Labels are known at the next completed-day
boundary and must mature strictly before each split end. Overlapping sequences
and the completed-day publication proxy remain explicit limitations.

Run from this branch, with the existing CPU runtime (Torch 2.6.0+cpu, NumPy 2.5.3,
SciPy 1.18.1, Polars from the frozen environment):

```bash
# Use a fresh, independent state. Existing scientific attempts are never overwritten.
export COIN_CPD_STATE=/workspace/slow-momentum-reproduction
export COIN_CPD_PYTHON=/workspace/coin/.venv/bin/python
mkdir -p "$COIN_CPD_STATE/tests"
bash research/slow-momentum-cpd-20261011/launch.sh "$COIN_CPD_PYTHON" -m pytest modules/slow_momentum_cpd/test_core.py -q --basetemp="$COIN_CPD_STATE/tests/check"
bash research/slow-momentum-cpd-20261011/launch.sh "$COIN_CPD_PYTHON" -m modules.slow_momentum_cpd.run --state "$COIN_CPD_STATE" --preflight
bash research/slow-momentum-cpd-20261011/launch.sh "$COIN_CPD_PYTHON" -m modules.slow_momentum_cpd.run --state "$COIN_CPD_STATE"
bash research/slow-momentum-cpd-20261011/launch.sh "$COIN_CPD_PYTHON" -m modules.slow_momentum_cpd.audit --state "$COIN_CPD_STATE"
```

Recovery reads three pinned, already-public **local Git objects**, 2,246,454 bytes;
if absent, fetch branch `research/temporal-feature-data-20261009` normally first.
No market-data provider download is performed. The immutable recovered cloud
guard enforces one CPU/thread, 4GB address space, sampled 2GB descendant RSS,
8GB shared used-memory stop, swap0/GPU0, 1200s per command, 15GiB disk reserve.
It is a conservative cloud adaptation, not the original WSL slice launcher.
No active local progress service was reachable; command updates and JSON resource
receipts show actual progress. No collector was stopped or modified.

Native shared-wallet evaluation is conditional on the frozen prediction gate.
It would require source-bound actual trade/mark/funding input and existing fees,
slippage, masks, risk and paid terminal closure. A prediction failure stops this
attempt; no daily toy wallet or guessed funding substitutes for native evidence.
Original 2026 Q1/Q2 ledgers remain unavailable. The 2026-03-01–2026-09-01 collector
lock was not opened. This study uses its own branch, module and state; the separate
return-distribution study and all older experiments remain unchanged.

Exact paper reproduction is NOT_RUN: the original CLC data, historical code
version, seeds and selected hyperparameter/model artifacts are unavailable.
Synthetic tests are engineering evidence; real historical forecast metrics are
reported separately in the eventual RESULT.json. Financial PnL/APR is UNKNOWN
until a properly audited native account actually runs.
