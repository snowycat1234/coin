# Project freeze: 2026-10-21

Status: FROZEN_FOR_LATER_RESTART

This repository is frozen at the user's request. No live trading, deployment, credentials, or new data downloads are part of this freeze.

## Reproducible evidence retained

- Branch: research/generated-cost-repro-20261020
- Published 2024 source-only weekly replacement prefreeze:
  research/public-2024-weekly-prefreeze-20261021/
- The prefreeze includes the frozen specification, manifest, analyzer, and 22 deterministic tests.
- Tests pass locally: 22/22.
- The 2024 source README reports 366 days, 527,040 minutes per CORE5 asset, 5,490 funding events, and 45,999,392 normalized source bytes.
- Ten original 2024-08-12 mark closes are missing. Policy is STOP/NOT_ESTIMABLE: no interpolation, overlay, splice, or silent repair.
- Therefore no 2024 economic outcome was published.

## Conclusions at freeze

- 2023 weekly replacement attribution: +0.7166 bp/week point estimate, two-week bootstrap 95% interval [-104.22, +113.63] bp; interval crosses zero.
- 2023 settlement-window attribution was negative after modeled execution and fees.
- The prior positive CS and HOLD results are development-period results, not strict out-of-sample evidence.
- The lost 565-day account/wallet replay directory was not recoverable in the current environment; no background run is claimed.
- A reliable live APR and live readiness have not been established.

## Restart order

1. Read this file and all manifests from this branch.
2. Recheck every branch head and verify remote blobs.
3. Re-review the 2024 missing-mark STOP rule and the independent source manifest.
4. Only if the original bytes are complete and independently reviewed, run the frozen 2024 analyzer with no parameter changes.
5. Keep all strategy, cost, funding, exposure, and terminal accounting causal and shared-wallet consistent.

Do not treat this freeze as project completion or as an investment recommendation.
