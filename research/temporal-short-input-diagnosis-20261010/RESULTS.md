# No credible SHORT-error separator

Three economic input mechanisms were frozen before opening their later outcome relationships. None is stable enough to justify a filter or policy. Original CE20 scores, checkpoint, prefix scaler and four-way classes are unchanged. No fit, inference, threshold grid, downloads or trading replay occurred.

PLAN.json was frozen at 2026-10-10 16:17:23 UTC, SHA256 `52bf8ad8f70f98bf8f61d84d61d307e3904da96f09fd76a2a85c26475547e894`. All diagnostic windows/current18 expert-state tensors match the original causal episodes. The 744 mature TRAIN decisions reproduce the original 850 scaler-history dates. Missing values remain masked/UNKNOWN.

## Three prespecified associations

1. **Fall/rebound:** latest observed CORE5 median mom20<0 defines a fall; median mom5>0 identifies a rebound. In 2023, continuing-fall SHORT picks were 27/64 correct (42.19%), mean SHORT−VOL utility +.001652; rebounds 19/43 (44.19%), −.013410. Incorrect rebounds averaged −.064020 versus −.030441 for incorrect continuing falls. Rebounds barely separated correctness, though mistakes cost more. Their margin difference −.015062 had descriptive moving21-day-block interval [−.045181,+.016483]. Posthoc 2024 reversed the payoff ordering: rebound −.014525 versus continuing fall −.024566. Nonfalling20 picks in 2023 were 42/74 correct yet averaged −.004686.

2. **Volatility shock:** latest median paired vol10/vol60 above the single TRAIN-only q75 cutoff **1.0781771**. In 2023, shock SHORT picks were 16/41 correct (39.02%), mean margin −.021056; ordinary 72/140 (51.43%), +.000326. Shock-minus-ordinary precision differed −12.40 percentage points, block interval [−37.94,+10.42]; margin difference −.021382, interval [−.058930,+.015316]. Direction reversed in fitted TRAIN (82.35% versus 49.18%) and already-seen 2024 (9/12=75% versus 8/20=40%; margins +.019691 versus −.023806).

3. **Funding/premium agreement:** seven-day means of observed daily funding sums and premium-index closes; financial-zero sign bins. Negative agreement gave 3/15 correct in 2023, mean margin −.014501; positive 0/12, −.028427. All 12 positive-agreement errors had CS as winner. Positive agreement was instead 11/11 correct in fitted TRAIN and 17/25 in posthoc 2024. That block had zero negative-agreement observations. UNKNOWN rows were 31/7/0 in TRAIN/2023/2024. Funding is a completed-day raw event-rate sum, not an eight-hour rate or owned funding PnL; absolute units and actual publication timing remain uncertified.

## Counterexamples and limits

2023-06-29 was a continuing fall without a volatility shock, yet its false SHORT margin was −.221255. A rebound on 2023-08-31 was correctly SHORT, +.007765. Shock dates include false 2023-06-23 (−.210513) and correct posthoc 2024-01-15 (+.009868). EVIDENCE.json preserves correct/error illustrations for every observed state; they never set cutpoints.

TRAIN/2023/2024 have 182/103/27 SHORT-winner labels in 39/18/6 contiguous runs, longest 25/23/10 days. Runs break at other winners or calendar gaps: persistence counts, **not independent sample sizes**. Fixed phase0 has 36/17/5 horizons and 7/9/2 SHORT picks. In 2023 its fall/rebound cells have three picks each, shock/ordinary two/seven, and each funding-agreement sign only one. All 21 grids are retained without pooling/selection. Overlapping targets, 64-day inputs, regimes, exposures and conditioning on model choices prevent causal attribution; block intervals remain descriptive.

These are inherited-position continuing fixed-policy21-day utilities, not tradable switching returns. TRAIN is fitted, 2023 selected CE20, and 2024 was already audited and is strictly posthoc; no new holdout/live-return claim. Guarded diagnostic runs attempted no 2025 IO. Prior broad source discovery incidentally traversed 2025-named code/acquisition metadata without consuming 2025 market/outcome tensors or score-result files; absolute zero 2025 text IO is not claimed.

## One next step, proposed only

A bounded **input-only historical open-interest coverage/clock audit** is preferable to another filter sweep. OI change is absent from named24 and could measure position buildup/unwinding; this is an untested mechanism. Verify official archives for CORE5 through April 2024, units, availability and missing masks; stop if usable evidence is unavailable. [Official Binance documentation](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data) provides total OI/OI value and period-end timestamps but limits REST history to the latest month, so it cannot backfill these dates. Archive feasibility is unverified; no new feature/data was added.

## Reproduce and checks

Use existing coin_runtime from the repository. Wrap every command with `coin_single_state/bounded_cloud.py --report UNIQUE.json`, with `PYTHONPATH=.:src` and fresh OUT/TMP paths:

- `python research/temporal-short-input-diagnosis-20261010/diagnose.py freeze --state STATE --output OUT`
- `python research/temporal-short-input-diagnosis-20261010/diagnose.py diagnose --state STATE --output OUT`
- `python research/temporal-short-input-diagnosis-20261010/verify.py --state STATE --output OUT`
- `python -m pytest -q research/temporal-short-input-diagnosis-20261010/test_diagnose.py --basetemp TMP`

Six focused tests, Ruff, exact tensor/clock checks and row/group-margin/phase recomputation passed. Diagnosis: one CPU, 3.26s, peak RSS609MB, no GPU/swap. Full wallet validation NOT_RUN. Complete evidence: PLAN.json, EVIDENCE.json, ROWS.csv, VERIFY.json and IO/resource receipts.
