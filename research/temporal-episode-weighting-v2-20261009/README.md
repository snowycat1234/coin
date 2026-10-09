One fixed-update comparison: date-weighted own-path loss versus
0.5 date-weighted + 0.5 equal-wallet loss. Both arms retain the expanded
CASH/VOL/CS/MOMENTUM30_SHORT_ONLY pool, explicit causal expert inputs, the same
13,699-parameter GRU, and one byte-pinned preserved pre-ablation model/Adam/RNG
snapshot at base step780, before its first training evaluation. No June-selected
terminal initializes either arm.

Input: CORE5 BTC/ETH/SOL/XRP/DOGE,64 completed daily steps,24 causal values plus24
validity masks; current canonical VOL/CS/SHORT targets15 divided by fixed0.3,
then three eligibility bits. Keep the907-row train-only scaler, causal time
masks, dropout0.1, charged own-path objective, endogenous wallet/risk mapper,
caps/cost/funding and paid terminal flattening unchanged. Target availability
at or before decision uses the existing uncertified completed-bar proxy;
execution is decision+60,000,001µs. No measured release guarantee is implied.

Same778 mature training dates in five complete chronological wallets of
54/88/62/144/430 days. Coefficients are n/778 versus0.5*n/778+0.1. Every update
rolls every intact wallet; only independent feature windows are batched32.
Exactly512 new Adam updates each, saving every update. A1200s invocation slice
pauses and resumes the same model/Adam/RNG until512; it does not terminate the
experiment. No convergence stop or development checkpoint selection.

Predetermined training diagnostics at0/128/256/512 report per-wallet loss,
gradient norm, coefficient and signed projection dot(a_i*g_i,G)/||G||², plus
both common objective values. Projections may be negative; they are not norm
fractions or cumulative stochastic Adam directions. Freeze both512 terminals
before seen May–June scoring; export strict native61 requests immediately.
Minute-native replay remains assigned to the separate executor.

Use Python3.12 and the existing official CPU dependency
[recipe](../../modules/temporal_two_expert/requirements.txt). Entrypoint:
`python -m modules.temporal_episode_weighting_v2` with `check`, `arm`, `run`,
`score` or `export`, explicit `--state` and `--output`. Use the existing bounded
worker/controller launchers, at most two1CPU/2GB workers, shared8GB/swap0/GPU0.
`run` requires a published producer SHA and new `--request-directory`.

Completed512/512 updates without fitting failures. Both final common training
losses are slightly lower for mixed weighting, while seen May–June charged
daily-proxy PnL is−502.47 date versus−521.17 mixed (difference−18.70 USDT).
Both paid terminal flattening. This pair shows no seen-period benefit from the
weighting change; fixed completion does not establish convergence. See the
[result receipt](results/RECEIPT.json) and [native handoff](native61-requests/INDEX.json).
Both native transport checks passed; actual minute-native replay remains separate.
