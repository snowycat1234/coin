# Two fixed July wallets

Compare the frozen FULL773 LOW_LR3E4 fresh256 model at657aeaff93889da600ad88b3603739508ba03216 against the expanded1137 LOW_LR3E4 fresh256 model at0e5f41c255f315dccdd922de9a4ce762a1f40771. Same13,699 parameters, seed20261009, Adam0.0003, updates256 and original907-row scaler5c0085131d590e64316de3cc558e906f418bff50bc5d934339609da2c4b045ad. Earlier364 actual2021 intervals were added; originalfivewallets retained and date weights recomputed. Model/checkpoint/scaler identities and source closures are bound in PRESCORE.json.

Exactly two independent fresh10k daily-surrogate wallets on2024-07-01–2024-09-02 exclusive:63 decisions/62 active intervals, paidSep1 00:01:00.000001UTC close. Stop after this pair regardless of outcome. This is the second seen historical development comparison; no new OOS, fitting, tuning, model selection, downloads, native wallets or promotion.

Existing July inputs/controls pinned to90b8fd65d092b52091b3fee7717c0478b265bc6e; economics5109edcaa5a790a023a11828cfd1452b5705ba1a already cached. Original126 raw feature rows/64-step windows/eligibility/currentexpert inputs/covariance/funding/costs/ramp/risk/terminal ABI reused byte/parity-checked. The legacy July loader's April scaler is ignored; both requested models use their common907scaler. Audit56saved result receipts found no exact model/calendar path; the oldApril-prefix512 learned path cannot be reused. Three saved controls are reused without inference or wallet reruns.

The minute mark gap2024-08-12 10:02/10:03UTC remains for allfiveassets; full native validation is not claimed. Unchanged gross.6/asset.3/risk.1/budgetL1.1 limits, signed funding, fees.00055/spread.0004/slippage.0004 and paid flattening apply.

Use Python3.12 and pinned dependencies; CPU Torch from official https://download.pytorch.org/whl/cpu. Public source/data/model protocol must be verified before once-only execution:

```sh
PYTHONPATH=.:src taskset -c2 python research/temporal-april-transfer-20261009/BOUNDED_RESIDENT_RUNTIME.py --report STATE/PAIR_PREFLIGHT.json python -m modules.temporal_added_history_july.evaluate prepare --state STATE --economics STATE/july-frozen-transfer/economics --output STATE/paired-prefit
PYTHONPATH=.:src taskset -c2 python research/temporal-april-transfer-20261009/BOUNDED_RESIDENT_RUNTIME.py --report STATE/PAIR_RUN.json python -m modules.temporal_added_history_july.evaluate run --state STATE --economics STATE/july-frozen-transfer/economics --output STATE/paired-once --publication STATE/PAIR_PUBLIC_READBACK.json
PYTHONPATH=.:src taskset -c2 python research/temporal-april-transfer-20261009/BOUNDED_RESIDENT_RUNTIME.py --report STATE/PAIR_VERIFY.json python -m modules.temporal_added_history_july.verify --output STATE/paired-once
```

Four focused tests cover wrong512/model/scaler substitution, output masks, changedpublicsource guard and savedcontrolmanifest tampering. Preflight makes zero predictions and runs zero wallets. Evaluation preserves each actual request before its economic path and saves each completed wallet durably. Read-only verification makes zero model/wallet calls.
