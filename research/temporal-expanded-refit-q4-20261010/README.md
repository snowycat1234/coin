# One controlled added-history fit

Fresh seed20261009, 13,699 parameters, Adam0.0003, exactly256 updates; original773 active intervals plus364 actual2021 intervals. Six independent chronological wallets, unchanged original907-row scaler, date weights over1,143 decisions, unchanged costs/risk/ramp and paid closures. No tuning or checkpoint selection. The same Q4 is seen historical development: score the new frozen model once and reuse the existing773 model and three saved controls. This comparison changes economic history and date weights at fixed updates, not fixed compute.

Source packet: immutable1009a6cf6d7c79e3cd914861dc2aeafc3d23709e, consumer SHA3ba1e64d7c91150a73c28642bed46d1dd2325fcf8fa8aade9425164f526d66ba. Only551,118 derived bytes materialized; no provider downloads or raw archive restoration. Full December native tape is not claimed.

Input:64 completed daily steps ×5 assets ×(24 causal values +24 validity masks), separate time masks, and18 current expert inputs. Wallet state is endogenous in the mapper/objective. Outputs use the existing allowed expert simplex, dynamic eligibility and CASH.

Use Python3.12 and the pinned requirements. Install CPU Torch from the official https://download.pytorch.org/whl/cpu index. Restore verified original cached inputs and the small2021 consumer packet into STATE. Run through the resident resource guard:

```sh
PYTHONPATH=.:src taskset -c2 python research/temporal-april-transfer-20261009/BOUNDED_RESIDENT_RUNTIME.py --report STATE/PREPARE.json python -m modules.temporal_expanded_refit prepare --state STATE --economics STATE/2021-economics --output STATE/fit
PYTHONPATH=.:src taskset -c3 python research/temporal-april-transfer-20261009/BOUNDED_RESIDENT_RUNTIME.py --report STATE/FIT1.json python -m modules.temporal_expanded_refit worker --state STATE --economics STATE/2021-economics --output STATE/fit --publication STATE/PREFIT_PUBLIC_READBACK.json
```

Worker requires an actual verified public prefit readback bound to READY.json. Each invocation consumes one durable slice before any gradient; max3,1100s per slice,1200s hard guard. Checkpoint every completed update includes model, Adam and all RNG. Failure stops without a new recipe. Tests use synthetic fixtures and no economic fitting.

The first published initialization failed restricted Torch loading before STARTED, gradients, or updates: a real receipt np.float64 was serialized in the checkpoint binding. The correction canonicalizes the same numeric binding to plain JSON types and verifies restricted load during preparation. Both initializations and resource receipts are retained; prefit-safe is the executable freeze. Same model, scaler, recipe and sole authorized economic fit.

The single expanded1137/fixed907/fresh256 fit and once-only seen historical Q4 comparison completed. New model net PnL+1168.87USDT/MDD1.188%; change vs saved773model+184.05USDT/utility+0.016768729, vs savedVOL-97.35USDT/utility-0.005469262. Exactly256 updates/13,699parameters/seed20261009/Adam.0003, unchanged907scaler and originalfivewallets, 364actual2021 intervals added for1137active/1143decisions/sixpaidwallets. Old773model and three controls reused, zero reruns; one new paid dailywallet,92source-bound native requests, native replay NOT_RUN. Eight focused tests and92savedrows independently reconcile; model/Adam/allRNG unchanged in score. No tuning/epochselection/providerdownloads/newOOS/promotion.

| Policy | Net PnL USDT | Daily MDD | Source |
|---|---:|---:|---|
|Cash50|+732.28|0.908%|saved result reused|
|EXPANDED1137_FIXED907_FRESH256|+1168.87|1.188%|one new score|
|FROZEN_VOL|+1266.22|3.200%|saved result reused|
|SELECTED_FULL773_256|+984.82|1.660%|saved result reused|
|Static50|+1446.98|1.812%|saved result reused|

The model is fixed at update256; no additional recipe is authorized. This charged daily comparison is seen historical development, not new OOS or a native execution result. Native92 request replay remains a separate data/calendar validation task; the same five-symbol/expert order, causal availability and paid-close contract are in q4-results/native-handoff/MANIFEST.json. No full December2021 native tape is claimed.

After verified public terminal/source freeze, run the one score through the guard:

```sh
PYTHONPATH=.:src taskset -c2 python research/temporal-april-transfer-20261009/BOUNDED_RESIDENT_RUNTIME.py --report STATE/Q4_ONCE.json python -m modules.temporal_expanded_q4.evaluate --state STATE --train-economics STATE/2021-economics --q4-economics STATE/q4-economics --fit-output STATE/fit --output STATE/q4-once --publication STATE/FROZEN_PUBLIC_READBACK.json
PYTHONPATH=.:src taskset -c2 python research/temporal-april-transfer-20261009/BOUNDED_RESIDENT_RUNTIME.py --report STATE/Q4_VERIFY.json python -m modules.temporal_expanded_q4.verify --output STATE/q4-once
```
