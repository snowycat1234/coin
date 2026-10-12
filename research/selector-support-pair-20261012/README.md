# Fixed training-date support pair

This parent-authorized continuation tests one hypothesis: with the same A46
features, Ridge30 learner, fixed expert pool and conditional paid-cost rewards,
does using all actually disjoint one-day owned intervals improve prediction over
the original conservative maturity-based thinning? It is an adaptation and a
seen-history development experiment, not a paper replication or native return.

Exactly two historical fits are frozen. Both train on truly complete rewards
before 2022-09-15, and predict the same natural 61-date October–November calendar.
OWNED_FULL must contain at least 600 distinct UTC dates with positive effective
data loss. The control may have approximately 305 dates. No shortened holding,
resampled validation, forced SHORT, alternative seed or recipe rescue is allowed.

Owned intervals remain `(decision+60000001us, decision+DAY+60000001us]`.
The funding event after the owned end is a separate completeness watermark;
it enters true reward maturity and is purged before fitting. Boundary funding
events belong to one reward only. This corrects date geometry without moving
publication clocks backwards. Support count is not independent information/ESS.

The previous 181-date experiment, four failed selector gates, default-account
paid-flat failure and finite-exit dust STOP are preserved. Native financial
reward certification remains BLOCKED: this daily quantity reference does not
implement the native wallet's capacity, minimum filters, exact charge prices,
historical margin tiers or terminal paid-flat behavior. No native wallet runs.

Source identities, protocol, interval tests and independent read-only review
were frozen before fits at `43c6fecffe9af7f1a8e32c7a834d6c57b01235fc`.
The two fits and original result were published at
`813abe3b8d81f69f06743d43fc3390a4c8b26eca`. The original source/result manifests
are immutable. See PROTOCOL.json for the exact MSE/CI gate and resource limits.

Completed: **STOP_FIXED_SUPPORT_INFORMATION_GATE**. Control/full actual positive
effective-loss dates are **305/607**, with one unweighted vector per distinct UTC
date. They span 2021-01-03 through 2022-09-12/13; the full arm's last complete
reward matures at 2022-09-14 08:00 UTC, strictly before the Sep15 fit cutoff.
Complete owned intervals and raw funding ownership were verified before fitting.

|Same 61-date development calendar / 59 mature common labels|Control|Full|
|---|---:|---:|
|Non-CASH conditional utility MSE|0.0001403626441737506|0.0001401431712217956|
|Actual objective dates with positive loss|305|607|

Full's relative MSE reduction is only **0.156361%**, below the frozen 2% gate;
paired 7-day calendar bootstrap 95% CI is **[-8.0397964e-6, 8.3309528e-6]**, crossing
zero. Seed811134, bootstrap811135/1000 replicates, one scientific attempt/two
fits, total5.679660s, fit times0.019337s/0.002043s. These dates are real loss support,
not 607 independent observations or evidence of investment return. No rescue.

[ACTUAL_LOSS_DATES.csv](result/ACTUAL_LOSS_DATES.csv) contains every actual sample
ID, UTC date, split, owned start/end, full reward maturity, terminal dependency,
weight and fitted data loss. [REWARD_BOUNDARY_LEDGER.csv](result/REWARD_BOUNDARY_LEDGER.csv)
also records actual raw funding event IDs. Scalers/coefficients/indices are in
[MODELS.npz](result/MODELS.npz); all natural-calendar predictions/target intents
are in [VECTORS.npz](result/VECTORS.npz). No oracle winner labels or native NAV.

Four focused interval/maturity tests PASS and independent read-only review found
no substantive prefit blocker. Scientific source/labels/coefficients/date/maturity
checks pass. Initial cold byte assertion failed solely on final floating digits
of reconstructed training loss; that failure is retained in verification_failures.
The explicit [verifier amendment](REPRODUCIBILITY_AMENDMENT.json) does not change
fits, checkpoints, gates or results. Successful cold restore adds zero fits:
scientific report, prediction/target vectors and reward boundary ledger exact;
all date/clock/weight/positive-loss fields exact. Effective-loss numeric comparison
uses rtol1e-12/atol1e-18, measured max absolute difference5.421010862427522e-20.
Cold elapsed4.022115s. The low-level floating arithmetic cause is unestablished.

Minimal **zero-fit** reproduction from this branch (fresh state required):

```bash
export COIN_CPD_STATE=/workspace/selector-support-pair-reproduction
export QUANT_ROOT=/workspace/coin-tail-risk
export QUANT_STATE="$COIN_CPD_STATE"
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python research/selector-support-pair-20261012/run.py \
  --state "$COIN_CPD_STATE/PUBLIC_COLD" \
  --source-commit 43c6fecffe9af7f1a8e32c7a834d6c57b01235fc \
  --expected-commit 813abe3b8d81f69f06743d43fc3390a4c8b26eca
```

This verifies published Git-bound inputs/results and reconstructs funding streams
from existing local public Git objects; it makes no provider request. COLD_SOURCE
binds the amended verifier separately. To rerun the two fits, use a clean checkout
of the original source43c6fecf, a fresh state, and omit --expected-commit; current
verifier source intentionally does not match the immutable original fit manifest.
All Python uses the bounded cloud launcher, not the unavailable original WSL slice.
No collector or locked holdout was changed. Source wrapper reuse adds about167MB
to STATE; large wrappers are not duplicated in this research commit.

The earlier [paper mechanism adaptation](../slow-momentum-cpd-20261011/README.md)
also failed its frozen prediction gates. The original 181-date selector's four
failures remain in its own directory. The [finite native exit](../terminal-reduce-only-exit-20261011/README.md)
still leaves51.39732453DOGE /3.0905211239889USDT after60minutes, with actual paid
costs and minimum-order rejection. The [funding source audit](../funding-charge-evidence-20261011/README.md)
still lacks actual associated charge-price evidence and native authority. These
are independent blockers; this support experiment does not repair them.
