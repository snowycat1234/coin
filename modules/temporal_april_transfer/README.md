# One additional calendar-chosen April63 fold

One fresh 13,699-parameter model, seed20261009, empty Adam and fresh Python/NumPy/
Torch RNG, exactly512 updates. Reuse the frozen expanded-pool/current-expert GRU,
date-weighted own-path objective v2, dropout0.1, batch32, optimizer, costs/funding,
L1 ramp0.1, gross0.6/asset0.3 caps and paid closure. No recipe change or sweep.

TRAIN contains749 decisions in five original chronological prefixes of
54/88/62/144/401, with878 unique real scaler rows. Every admitted outcome and
paid close is strictly before April1, 2024. The forward block is April1 through
June3 exclusive:63 decisions,62 active intervals, one fresh10k wallet, no May
reset, paid close on June2 at00:01:00.000001 UTC. All windows contain64 real
completed daily observations,24 values/24 validity masks per CORE5 asset plus
separate time masks and18 causal current expert inputs. No observed wallet state.

Actual H1 contexts are joined as observations across their administrative split;
old economic paths are never joined. Use the original observed00:01 execution
prices and unchanged event/strictly-prior-mark funding normalizer. The exact
public momentum30 SHORT producer is vendored byte-for-byte at
`upstream/momentum_short_pool_target.py`, commit1291857d53360e4e06a4dd50540c130886deffbf;
it bridges April30 from existing local bars. April1–29 targets/prices/funding
match the original packet bitwise. Source hashes and coverage are in READY.

Dependencies: existing official CPU Torch/NumPy/pytest/Ruff recipe in
[../temporal_two_expert/requirements.txt](../temporal_two_expert/requirements.txt),
plus already installed Polars1.44.2, pandas and PyArrow23.0.1 for reading the
existing pinned source tables. No dependency install or market download here.
Restore the prior public recovery/feature/SHORT packets as described in their
existing modules. Set PYTHONPATH to checkout and its src directory. Invoke through
the existing bounded launcher (COIN_CLOUD_BOUNDED=1):

```
python -m modules.temporal_april_transfer prepare --state STATE --output OUTPUT
python -m modules.temporal_april_transfer fit --state STATE --output OUTPUT
python -m modules.temporal_april_transfer export --state STATE --output OUTPUT \
  --destination NATIVE63 --producer-commit PUBLIC_PREFIT_SHA
```

Prepare freezes prefix/scaler/source/model/emptyAdam/allRNG before fitting.
Fit resumes one atomic run in at most four1200s slices, never exceeds512.
Only feature windows are batched; the financial VJP retains full chronological
wallets. Export requires the actual512 terminal model and all13 Adam states at512,
then freezes E6 model requests plus unchanged Static50 and Cash50 controls,
context/clocks/scaler/checkpoint/source handoff. The separate executor owns
minute-native replay. The daily export is approximate execution evidence.

All three prior fold results remain byte-identical and are included in the
four-fold aggregate. Their failed worst-fold screen cannot be erased. This block
was selected by quarterly calendar and verified coverage, not returns. Historical
project-seen research; no pristine out-of-sample claim, alternative period,
seed/parameter/horizon search, continuation or APR claim.

Focused checks cover actual causal coverage/prefix invariance, warmup/counts,
fresh initialization/full RNG, empty-Adam serialization, changed-prefix rejection,
and the exact512 export barrier. Tests use separate STATE temporary directories;
they perform no historical optimization or native replay.
