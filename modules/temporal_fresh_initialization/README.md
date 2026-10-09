# One fixed fresh initialization comparison

Reuse the frozen 13,699-parameter expanded-pool/current-expert GRU, original five
complete training wallets (778 dates), exact 907-row training-prefix scaler and
date-weighted charged objective v2. One seed, one fresh model/empty Adam/all RNG,
exactly 512 updates. Same recipe as the three fresh chronological folds; no model
or Adam from the warm comparator enters the actual fit. No new economic kernel.

The exact comparator is `GRU64_WEIGHT_DATE` at
`d3d57332ca45b7a4443108db21f46abad0e1ac99`. Its base Adam age is 1292 and added heads
are 512, whereas this fresh run ends with all parameters at 512. This compares
initialization regimes with different lifetime optimizer/data exposure. May–June
61 is explicitly seen development, never out of sample. Export terminal requests
before scoring; minute-native replay belongs to the separate executor.

Dependencies are the unchanged official CPU Torch/NumPy/pytest/Ruff recipe in
[`../temporal_two_expert/requirements.txt`](../temporal_two_expert/requirements.txt).
No install or market download is required in the existing environment.

Set `PYTHONPATH` to the checkout and its `src` directory, use the installed Python
and existing resource guards. CLI: `python -m modules.temporal_fresh_initialization
{prepare,fit,export,score} --state STATE --output OUTPUT`; `export` additionally
requires `--destination NATIVE --producer-commit PUBLIC_PREFIT_SHA`; `score`
requires that already complete `--destination NATIVE`. Prepare is exclusive and
requires the completed comparability audit. Fit resumes the same atomic run in
bounded 1200-second slices up to 512; terminal state cannot continue beyond 512.

Inputs remain CORE5, 64 completed daily steps, 24 causal values plus 24 validity
masks per asset and separate time masks, plus 18 current expert inputs. Four
active canonical E6 actions: CASH/VOL/CS/SHORT; two historical slots stay zero.
No observed wallet state. Original endogenous mapper, L1 ramp 0.1, gross 0.6,
per-asset 0.3, costs, funding and paid flattening remain unchanged. Full wallets
stay chronological; feature batches alone are independent.

Focused tests use synthetic non-economic export/checkpoint fixtures; no extra
historical fit. Frozen audit reproduces every training request bitwise after
copying warm weights into a separate probe and exactly reproduces its objective.
All reused source bytes and original model/scaler identities are retained.
