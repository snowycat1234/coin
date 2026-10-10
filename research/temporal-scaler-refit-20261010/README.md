# One training-union normalization ablation

Hypothesis: the added 2021 feature distribution is poorly scaled by the deliberately fixed original907-row normalizer. The preceding read-only distribution/gate diagnostic supplies evidence for testing this; it does not prove a cause of PnL. One fresh fit changes only normalization to the same valid-only mean/std algorithm over all1273 distinct completed rows in the existing six training wallets. No clipping, feature changes, data removal, new economic dates, architecture changes, or grid search.

1137 active training intervals/1143 decisions, original six wallets [365,54,88,62,144,430], exact existing economic identities, Adam .0003/256 updates, seed20261009,13699parameters, same date weights/costs/risk/paid closures. Initial trainable parameter bytes match the prior1137 fixed907 fit exactly; only normalization buffers and their identity differ. All normalization rows precede May1 2024. Old907 and new1273 scaler identities and complete source graph are bound in READY.json.

Source restoration reused existing feature/recovery caches and retrieved only previously published small derived training arrays/tables. No market-provider acquisition. Exact six episode identities, event funding, dynamic masks, source features and initial parameter identity are checked before training. Two real-data tests pass. Nine original synthetic gap/clock/gradient/mask/terminal tests pass in an isolated process. The attempted combined11-test process recorded6passes/5fixture errors because the immutable prototype was already loaded from a different path; the guard was not relaxed. New source lint/compile checks pass. This is not a full-repository test claim.

One CPU/thread, process RSS2GB/address space4GB, host used8GB cap, no swap/GPU. Each slice stops at1100seconds (hard1200); at most3 slices with exact model/Adam/RNG continuation; checkpoint after every complete update. Source/model/path failure retained and stops this recipe, without alternate initialization. Select terminal256 only, not a best seen epoch. No evaluation during training.

After public terminal freeze, score the single candidate once on each of the existing July63 and Q4 92decision seen periods; retain their distinct terminal ABIs. Reuse previous model/control outputs. Both are historical development comparisons, not new OOS. Report costs, actual exposure and drawdown regardless of sign. No native wallet or live promotion in this module. An encoder saturation measurement is not a financial success gate.

Commands from the repository root (Python3.12; exact dependencies listed):

    PYTHONPATH=.:src python -m modules.temporal_scaler_refit prepare --state STATE --economics STATE/early2021 --output STATE/scaler-refit
    PYTHONPATH=.:src python research/temporal-cached-july-20261010/bounded_cloud.py --report STATE/SCALER_SLICE1.json python -m modules.temporal_scaler_refit worker --state STATE --economics STATE/early2021 --output STATE/scaler-refit --publication STATE/SCALER_PUBLIC_READBACK.json
    PYTHONPATH=.:src python -m modules.temporal_scaler_refit.evaluate --state STATE --economics STATE/early2021 --fit STATE/scaler-refit --output STATE/scaler-eval-once --publication STATE/SCALER_TERMINAL_READBACK.json
    PYTHONPATH=.:src python -m modules.temporal_scaler_refit.verify --output STATE/scaler-eval-once

For recovery, restore PREFIT.zip and bound state inputs without replacing an existing live/completed claim. Public readback must confirm source/READY bytes before worker; terminal checkpoint/receipt/source graph must be public and verified before score. The inherited file lock and exclusive evaluation directory remain enforced. This publication contains zero optimizer updates and no candidate economic scores.
