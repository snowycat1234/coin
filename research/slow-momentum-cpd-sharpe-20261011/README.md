# Fixed Sharpe correction completed: increment not established

Six fresh fits completed exactly 1024 updates each. On the three **seen
development** blocks, ensemble gross policy Sharpe rose from **0.235991 to
0.520626**, increment **+0.284635**. The paired joint-date 95% interval is
**[-0.180577, +0.803348]**, so the fourth frozen gate fails and the status is
`STOP_RAW_POLICY_INCREMENT_NOT_ESTABLISHED`. This positive point estimate does
not establish an increment; it also does not exclude a positive effect or
reject the original paper. No rescue search or budget extension was run.

| Development block, exclusive end | Calendar decisions | Eligible asset decisions | Trend SR | Trend + CPD SR | Increment |
|---|---:|---:|---:|---:|---:|
| 2023-01-01 to 2023-07-01 | 180 | 694 | 0.960956 | 1.034196 | +0.073240 |
| 2023-07-01 to 2024-01-01 | 183 | 915 | -0.617363 | -0.349653 | +0.267711 |
| 2024-01-01 to 2024-05-01 | 120 | 600 | 0.764840 | 1.159260 | +0.394420 |
| Concatenated 483 days | 483 | 2209 | 0.235991 | 0.520626 | +0.284635 |

Sharpe uses a fixed five-asset divisor, population variance and annual calendar
365, without scoring epsilon. Missing eligible future outcomes: zero. The
2023H1 mask has 206 cash asset decisions, determined only by information at the
decision. Each boundary purges the decision whose next-day label matures at
the exclusive end, explaining 180/183/120 calendar days. Three seed positions
are averaged **before** calculating returns and nonlinear Sharpe. Aggregate SR
is recomputed from concatenated daily returns, not a mean of block SRs.

Paired aggregate seed increments are **+0.086197 (2001), +0.676580 (2002),
-0.027306 (2003)**. Thus the first three gates pass: positive in at least two
blocks, positive in at least two seeds, and positive aggregate ensemble delta.
Seed disagreement remains material; the result is not uniformly stable. The
fourth gate requires a strictly positive bootstrap lower bound and fails.
All 1000 frozen replicates are valid: 14-day contiguous calendar blocks,
seed9901, common date draws across both arms and all five assets, no crossing
the declared block boundaries. This interval is conditional resampling of
already-seen development history, not independent OOS or search-adjusted evidence.

Mean daily cross-sectional rank IC is trend/CPD **0.02056/-0.00278** in 2023H1,
**-0.00820/0.01530** in 2023H2, and **-0.03083/-0.06083** in Jan–Apr2024.
Ranking is mixed. Position-versus-target MSE is also recorded as a diagnostic;
these tanh policy outputs are not calibrated return forecasts. The original
MSE experiment retains its original failed prediction gates and files.

| Seed | Arm | Final full-train pooled SR | Absolute SR drift, update768→1024 | Final epsilon fraction |
|---|---|---:|---:|---:|
| 2001 | trend | 4.650396 | 0.661432 | 0.9652% |
| 2001 | trend + CPD | 5.376334 | 0.766934 | 1.3979% |
| 2002 | trend | 4.010165 | 0.522437 | 0.3400% |
| 2002 | trend + CPD | 4.775770 | 0.476423 | 0.4591% |
| 2003 | trend | 4.366594 | 0.208775 | 1.1194% |
| 2003 | trend + CPD | 5.331334 | 0.214492 | 1.0321% |

Every tail drift exceeds the frozen 0.02 diagnostic threshold: **convergence
not established within this budget**. Always use the final1024 checkpoint;
validation never selects an earlier checkpoint. Full-train SR is pooled across
asset endpoints and differs from calendar portfolio SR. Final position
variance is positive in all six fits (0.00137–0.00451); final training and
validation saturation fractions are zero. Training epsilon is exactly1e-9;
the fraction above measures epsilon/(captured variance+epsilon), not a new
optimization parameter. These diagnostics cannot establish economic convergence.

The experiment executes the unchanged [frozen proposal](../slow-momentum-cpd-20261011/SHARPE_CORRECTION_PROPOSAL.json)
with SHA256 `8895319f41a91ebdb44a87fe67959c5f45c62cd7ad7c325fe87e0875eadc816b`.
Fit source: [6229da816bb7241aa5b75931090ecd84f3a1f19d](https://github.com/snowycat1234/coin/commit/6229da816bb7241aa5b75931090ecd84f3a1f19d),
pushed and remote/byte-verified before the first fit. Frozen data source commit
`e0d3400b23842f11f167a63e7d80856d76501de8`; archive SHA256
`bdbcdc488fc4245c1fb6b433df1fc4bf806a120433db71e180816119cebbcc30`.
No provider data downloads; 2,246,454 existing Git-recovered bytes were reused.
GP/scaler reuse the original training artifact SHA256
`8587adcb407ba7b55e66eed6e1d06596cbbcb1e743f5fe04a822b98eee6b4bd2`.

This is a **frozen-GP crypto adaptation**, not an exact paper reproduction.
BTC/ETH/SOL/XRP/DOGE; 2020 warmup, 2021–2022 training with2526 endpoints;
all later history is development validation already studied in this repository.
Normalization and GP parameters originate solely in the training period;
there are zero new GP/scaler fits and zero validation fits. The common63-day
last-head LSTM has hidden16 and tanh positions; the baseline zeros the two CPD
inputs while treatment uses frozen age/evidence. Both have1809 nominal
parameters, but128 baseline coefficients are dormant (1681 active versus1809).
Adam0.001, batch128 with replacement, clip1, identical paired initialization
and minibatches; three fixed seeds, no dropout, no hyperparameter selection.
Training minimizes pooled negative captured-return Sharpe in centered float64,
with target0.15/sqrt365 × r[t+1]/vol[t]. The original online per-window GP,
time-distributed output/nonoverlapping batching/dropout/search/CLC data remain
unreproduced; see the preserved [mechanism and gap crosswalk](../slow-momentum-cpd-20261011/REPRODUCTION_GAPS.md).
The paper's reported futures results are not cryptocurrency evidence.

**Economic stage: `NOT_RUN_NOT_BOUND`, zero native wallets.** The raw proxy
annual volatility is0.5363% trend versus0.3913% CPD; it is not the advertised15%
target and does not imply equal risk. Signal turnover/gross diagnostics are
uncapped signals without executable fills. Fees, slippage, actual funding,
risk handling and paid terminal closure are **NOT_MEASURED**; net profit/APR
is **UNKNOWN**. No guessed funding, free closure, oracle profit or daily toy
wallet substitutes for the shared native account. The frozen evidence gate
stops this attempt before wallet work. Minimum needs for any newly authorized
economic follow-on: source-bound trade/mark/funding for these dates, actual
fee profile and unit/clock interpretation, decision-to-fill latency and mask
exits, shared10k capital/abs30% per asset/gross60%/isolated1x risk handling,
charged terminal liquidation, and independent account conservation checks.
Original 2026Q1/Q2 ledgers are unavailable; none were fabricated or recovered.

The combined29 prefit tests pass (14 predecessor,15 new); the focused post-fit
receipt regression adds one pass, not another scientific fit. Full repository
tests are NOT_RUN. Ruff passes. Successful [saved-policy audit](results/SAVED_POLICY_AUDIT.json)
reconciles2415 rows, exact masks/vol_t/label maturity, six paired RNG/minibatch
hashes/Adam1024 ages,18 validation plus6 training inference sets, full metrics,
joint-date bootstrap and four gates. Maximum inference residual0 and metric
residual8.88e-16. First read-only audit failed only at NumPy-bool JSON encoding;
failure/partial-file hashes are preserved. The [repair](repairs/AUDIT_REPAIR.md)
was published as [b3d209c8d55958471c874fc2707d765ed56c3688](https://github.com/snowycat1234/coin/commit/b3d209c8d55958471c874fc2707d765ed56c3688)
before successful audit2. Trainer, tests, checkpoints, RESULT and POSITIONS
were unchanged; executing/original auditor identities are disclosed separately.

Actual fit timers total28.970s; experiment timer32.236s; enclosing training
guard37.047s, sampled descendant RSS381,382,656B and host used1,149,771,776B.
Successful audit guard5.787s/sample304,689,152B. Child and enclosing times are
not added. Guard enforces1CPU/thread,4GB address space, sampled2GB RSS/shared8GB
used-memory stop,swap0/GPU0,1200s per command and15GiB disk reserve; sampled
RSS is not a kernel peak or shared-cgroup enforcement. No resource stop occurred.
Runtime/package versions are in [RUNTIME.json](results/RUNTIME.json). Models
and full stdout logs remain external under `/workspace/slow-momentum-sharpe-state`.
Small evidence is committed; no model/market archive/db/env is added to Git.

This attempt has **6 fits/6144 updates**; cumulative with the unchanged MSE
attempt: **2 scientific attempts,12 fits,7680 updates**, searches/retries0,
wallets0. Original43 evidence files/4 fit source files/6 external checkpoint
bytes were actually verified before and after. Collector lock2026-03-01 to
2026-09-01 remained closed; no collector changes, live/paid/key/credential,
Library operations or edits to the separate return-distribution research.

Minimal reproduction from the published branch, using the recorded CPU runtime
and the existing archive (a **fresh** state is mandatory):

```bash
export COIN_CPD_STATE=/workspace/slow-momentum-sharpe-reproduction
export COIN_CPD_PYTHON=/workspace/coin/.venv/bin/python
test ! -e "$COIN_CPD_STATE"
mkdir -p "$COIN_CPD_STATE/tests"
bash research/slow-momentum-cpd-20261011/launch.sh "$COIN_CPD_PYTHON" -m pytest modules/slow_momentum_cpd/test_core.py modules/slow_momentum_cpd/test_sharpe.py modules/slow_momentum_cpd/test_audit_sharpe.py -q --basetemp="$COIN_CPD_STATE/tests/focused"
bash research/slow-momentum-cpd-20261011/launch.sh "$COIN_CPD_PYTHON" -m modules.slow_momentum_cpd.sharpe --state "$COIN_CPD_STATE" --archive /workspace/slow-momentum-state/source/features.zip --preflight
bash research/slow-momentum-cpd-20261011/launch.sh "$COIN_CPD_PYTHON" research/slow-momentum-cpd-sharpe-20261011/prepare_reproduction.py --state "$COIN_CPD_STATE"
bash research/slow-momentum-cpd-20261011/launch.sh "$COIN_CPD_PYTHON" -m modules.slow_momentum_cpd.sharpe --state "$COIN_CPD_STATE" --archive /workspace/slow-momentum-state/source/features.zip
bash research/slow-momentum-cpd-20261011/launch.sh "$COIN_CPD_PYTHON" -m modules.slow_momentum_cpd.audit_sharpe --state "$COIN_CPD_STATE" --run-number 1
```

The publication helper checks exact remote HEAD and unchanged trainer/tests;
it never trains. This reproduces the frozen training on the delivery commit
with the repaired auditor, so source receipts disclose that commit rather than
mislabeling a new run as the original6229 fit. No extra reproduction fits were
performed here. If the public archive is absent, recover only its pinned local
Git objects using `modules.slow_momentum_cpd.run.recover_archive` under the
same launcher; normally fetch `research/temporal-feature-data-20261009` if the
required Git objects are absent. Never fetch locked collector content.
