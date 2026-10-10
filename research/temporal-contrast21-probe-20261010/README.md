# One fixed direct-contrast target test

Change only the targets of the frozen eight-feature, lambda=1, prefix-scaled
ridge recipe to cost-after standalone VOL-minus-SHORT and VOL-minus-CS
21-day marked subperiod returns. Both predictions remain signed. Positive
forecast favors VOL, negative favors the other expert, zero abstains. No grid,
threshold optimization, neural training, new data, native rollout or policy.

Each historical path preserves its original wallet start, chronology, cached
causal expert targets/eligibility, mapper/ramp/caps, funding, costs, risk
reductions and paid final flattening. No reset at rolling-window boundaries.
Full 21-active-interval labels cannot cross original gaps or paid-terminal
rows; their actual execution/outcome clocks must precede the fold strictly.
Forward primary score has 42 full windows per fold and fixed disjoint starts
0/21. Start42 has 20 active intervals plus paidclose and is reported separately.
These are inherited standalone wallet outcomes, not realizable switching
profits or fresh 21-day accounts. All four blocks are repeatedly examined
historical development evidence, not new pristine OOS. Effective N is unknown;
overlap and just two disjoint spans preclude statistical-strength claims.

MSE and sign agreement compare ridge with its causal prefix contrast mean.
Constant VOL is an action baseline: compare its decision error and sign
agreement; MSE has no meaning without an arbitrary forecast magnitude.
No magnitude is invented. Forecast calibration is descriptive only.

[Duplicate check](DUPLICATE_CHECK.json) found no matching prior direct21 probe:
the earlier relative-performance ridge used 7 days, penalty10 and other experts.
[Fixed protocol/source hashes](PROTOCOL.json) precede labels and fitting.
Six new focused tests plus thirteen reused feature/ridge/maturity tests pass.

Reproduce with installed Python3.12/NumPy2.5.3; Torch2.6 CPU is needed only for
cached-context label preparation. pytest9.1.1/Ruff0.16.9 are test dependencies.
No installation. Use the existing bounded resource launchers with checkout/src
in PYTHONPATH:

```bash
python -m modules.temporal_contrast21_probe.labels --state STATE --root CHECKOUT --destination NEW_CACHE
python -m modules.temporal_contrast21_probe.probe --cache NEW_CACHE/INPUTS.npz --metadata NEW_CACHE/PREPARED.json --destination NEW_RESULTS
```

Preparation performs 15 original standalone surrogate paths and 12 bitwise
forward parity replays. The fit interface reads the published small NumPy cache
without loading Torch, wallets, old models or native tapes. Exactly four shared
two-output closed-form fits, 18 coefficients each; stop after this specification
regardless of outcome. A positive result would require a separately frozen
shared-wallet policy and paid switching validation.
