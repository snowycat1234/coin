Six fresh fits completed under the reviewed [protocol](PROTOCOL.json).
Selected recipe: **LOW_LR3E4**, Adam lr **0.0003**, wallet-equal mix **0.0**.
Return **256 updates** for the later fresh773-date refit; that refit has **not run**. Q4 reserved outcomes were **not read**.

| Fold | Candidate | Actual updates | Stop | Best update | Best utility excess vs VOL | Best net PnL (USDT) | Best MDD |
|---|---|---:|---|---:|---:|---:|---:|
| FOLD_20240101 | BASE_DATE_LR1E3 | 640 | EARLY_STOP_RULE | 256 | -0.07498917 | 98.0157 | 1.9577% |
| FOLD_20240101 | LOW_LR3E4 | 640 | EARLY_STOP_RULE | 256 | -0.05447482 | 296.1074 | 1.6163% |
| FOLD_20240101 | MIXED_WALLET_HALF | 1024 | UPDATE_CAP_NOT_CONVERGENCE | 768 | -0.08012134 | 47.9253 | 2.0015% |
| FOLD_20240401 | BASE_DATE_LR1E3 | 640 | EARLY_STOP_RULE | 256 | -0.03350390 | -215.2284 | 3.4107% |
| FOLD_20240401 | LOW_LR3E4 | 640 | EARLY_STOP_RULE | 256 | -0.01125051 | -17.6948 | 0.7812% |
| FOLD_20240401 | MIXED_WALLET_HALF | 640 | EARLY_STOP_RULE | 256 | -0.04213593 | -299.7874 | 4.4545% |

| Recipe | Mean best utility excess | Worst fold excess | Best updates |
|---|---:|---:|---|
| BASE_DATE_LR1E3 | -0.05424653 | -0.07498917 | [256, 256] |
| LOW_LR3E4 | -0.03286266 | -0.05447482 | [256, 256] |
| MIXED_WALLET_HALF | -0.06112863 | -0.08012134 | [768, 256] |

These are project-seen development daily-surrogate results on Jan–Mar and Apr–Jun2024,63decisions/62active intervals each; each complete wallet pays its terminal flattening. They establish a recipe under the fixed selection rule, not convergence or native validation.

The model has13,699 parameters and uses CORE5 BTC/ETH/SOL/XRP/DOGE,64completed daily steps,24causal values plus24validity masks. Shared per-asset GRU32 feeds joint160→32 and18current expert values/masks. CASH/VOL/CS/SHORT weights form a masked simplex; canonical SMA/DONCHIAN outputs remain zero. No observed wallet state. Same sigmoid allocation heads, risk mapper, L1≤.1, gross≤.6, per-asset≤.3, costs/funding and own-path gradient contract.

Exactly653/744active prefix dates across five natural chronological wallets per fold; seed20261009,dropout.1, train-only787/878-row normalization. Fresh Adam for every fit. OneCPU per fit, at most two fits concurrently,2GB resident each/shared8GB,swap0/GPU0. Every completed update fsynced and slices resume full model/Adam/allRNG.

[VERIFIED_RESULT.json](VERIFIED_RESULT.json) contains selection and all validation metrics; [VERIFICATION.json](VERIFICATION.json) rechecks source-bound snapshots, all Adam ages, initial identities, chronology, masked requests, NAV/PnL/MDD/utility, ordered stopping rules and exact reviewed tie ranking. Verification runs zero fits, inferences or wallet rollouts. Both baseline512 model/Adam/allRNG states match the earlier frozen512 models bitwise.

[TEST_RECEIPT.json](TEST_RECEIPT.json): seven adapter tests, two independent post-fit checks and eighteen operational extension tests pass (27 total). Original68 sources and all77 fitting-source identities remain unchanged; old failed warm mixed-weight result remains. Checkpoint generation files and pointers in [final/](final/) retain their original filenames for strict restoration. [PREFIT_RECEIPT.json](PREFIT_RECEIPT.json), [postfit/](postfit/) and [CONTROLLER_RECEIPT.json](CONTROLLER_RECEIPT.json) hold test, verification and resource receipts.

Frozen execution: `python -m modules.temporal_small_tuning prepare|worker|select`; final verified ranking: `python postfit/VERIFY_SELECT.py --output STATE/small-tuning-run`. The independent selector checks terminal status/weights/source identities and uses mean-score tolerance1e-5, then exact worst-fold max and fixed recipe order. It leaves all fitting sources byte unchanged.

The prepared 3600→5400-second operational extension was **not needed or applied**; the zero-update cap finalizer was also unused. [Decision receipt](RUNTIME_EXTENSION_DECISION.json) and all earlier checkpoints/resource receipts are preserved. The eighteen extension tests cover only the unchanged time guards and exact checkpoint continuation.

Dependencies reuse the pinned [official CPU Torch recipe](../temporal-july-frozen-transfer-20261010/requirements-transfer.txt). No provider downloads or reserved outcome access occurred in these six fits. The later773-date refit and Q4 feature binding/native evaluation remain separate authorized stages.

Historical [training-start](TRAINING_START.json), [live progress](PROGRESS_CHECKPOINT.json) and [matched512](matched512/) snapshots remain preserved. Those public copies use MODEL_ADAM_RNG.pt; rename to the pointer generation filename for strict restoration. Final copies already use original generation names.
