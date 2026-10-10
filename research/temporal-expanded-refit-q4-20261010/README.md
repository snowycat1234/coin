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
