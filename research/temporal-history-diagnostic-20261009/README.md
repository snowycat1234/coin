# Existing temporal experiment diagnosis — no new fitting

The strongest falsifiable explanation is **successful in-sample adaptation without demonstrated forward persistence of conditional allocation**, accompanied by a strongly invested cash gate. This is a working explanation, not proof of overfitting or absence of selector signal.

`STATS.json` reads saved losses, inputs and three frozen snapshots. Valid gradients, changing weights and decreasing training loss argue against a disconnected encoder or VJP. Final gradient norms exceed initial norms; convergence is unproved. Reweighting lowers the longest wallet's initial signed gradient projection from 76.69% to 44.45%, yet worsens the seen proxy by 18.70 USDT. Wallet weights are not gradient shares.

Outputs use three factorized **sigmoids**. The inherited model has s>0.99 on 85.25% of seen decisions; both fixed512 terminals have this on all 61, leaving mean CASH 0.154%/0.202%. Joint tanh saturation also predates this comparison. Seen mom200 shifts upward, but maximum standardized value 3.83 is within training's 7.52. Authentic SOL funding/premium extremes remain unchanged.

Current own-path fits use all 778 dates and the 907-row scaler; later modules inherit the global780 model/Adam. The preserved snapshot precedes the ablation, **after exposure to those 778 dates**. Splitting its requests cannot create internal OOF. Older D108, seven-day joint Ridge and Transformer v2/v3 had past-only purged folds with different proxy teachers. The known expert-state omission is addressed by 18 causal target/eligibility inputs; its unequal, nonconverged ablation is inconclusive. Execution mismatch remains possible, although prior native pairs also lost. Fixed512 native results belong to the separate task. Weak conditional signal versus period shift remains unresolved.

## One proposed train-only falsification, NOT_RUN

Use the current 13,699-parameter active-input model and date-weighted own-path objective, one seed, exactly 512 updates per fold. Fresh model, Adam/RNG and prefix-only scaler each time; freeze configuration before fitting.

| First forward decision | Scored daily decisions | Earlier admitted training decisions |
|---|---:|---:|
| 2023-07-03 | 63 | 411 |
| 2023-10-02 | 63 | 502 |
| 2024-01-01 | 63 | 593 |

Require every admitted wallet/prefix's final outcome **and paid-close availability** strictly before forward-start minus 64 completed days. Recorded clocks give these counts; validate prefix close admissibility before execution. Retain natural-wallet chronology/gaps and paid termination. Older causal rolling-indicator history may be shared; observations are not independent.

Freeze each model throughout its 63-day block. Each registered scoring wallet starts with 10k CASH, persists throughout and pays terminal flattening. L1<=0.1 needs at least 20 decisions for the simplex distance 2 of a full CASH-to-risk switch; 63 days includes that ramp and two further intervals. Keep ramp days; no splicing or minibatch resets.

Fixed controls: CASH, VOL, CS, SHORT, VOL50/CS50 and CASH50/VOL25/CS25, same mapper/caps/funding/costs. Primary screen: mean block log-utility excess>0 and worst-block excess>=0 versus fixed VOL50/CS50; report all controls without selecting block winners. Training improvement with failed forward excess supports nonpersistent conditioning at this budget; passing forward excess shifts attention toward May–June specificity. Record saturation and convergence diagnostics. No May–June tuning or proxy labels. This is retrospective development, not independent qualification.

Source anchors: [current packet](../../modules/temporal_two_expert/training_packet.py), [warm resume](../../modules/temporal_surrogate_resume_v2/stage.py), [pinned initial](../../modules/temporal_episode_weighting_v2/snapshot.py), [own-path objective](../../modules/temporal_risk_proxy_v2/proxy.py), [fixed512 results](../temporal-episode-weighting-v2-20261009/results/RESULT.json), [D108](../../reports/SELECTOR_ML_REPORT.md), [repaired joint Ridge](../../reports/JOINT_REPAIRED_20261008.md). Transformer commits: 0350589199d4566ac519b0e581ff86eb065ba934 / c7d0ae99f53a46fac497ede31fe4962b5b4f19a5. Omission review: 96b917f7e728016b6ef17e8983b98e29fcf95a8d. SOL review: 7282bc15e5bcaf0a14d177dbc4cb48fc860caa40. Exact HGB/pairwise/20-day artifacts were unavailable; no verified protocol attribution.

Reproduce with the installed Torch/numpy environment and restored prior STATE, under the existing resource-only launcher:

```bash
PYTHONPATH="$PWD:$PWD/src" OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
taskset -c 2 python -m modules.temporal_two_expert.bounded_comparison \
  --report "$DIAGNOSTIC_STATE/resources.json" python \
  research/temporal-history-diagnostic-20261009/diagnose_existing.py \
  --state "$TEMPORAL_STATE" --output "$DIAGNOSTIC_STATE/stats.json"
```

This command performs inference and reads stored diagnostics only. `RECEIPT.json` records exact numeric repeat and model-identity checks; no new fit, scaler fit, economic rollout or provider download occurred.
