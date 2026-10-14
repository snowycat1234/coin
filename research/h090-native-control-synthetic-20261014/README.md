# H090 native single-control generated integration

This new package implements CSH_H090_CONTROL and an unchanged original .60 control. It uses only generated source bars and minute quotes. It has no live exchange transport, keys, wallet history, market downloader, historical-array loader, fitted parameters or paid service. There is no historical GO, trading permission, performance finding or qualified candidate.

## What is implemented

- Validate original CSH .30 asset / .60 gross / .10 annual-vol identity, propose a fixed 1.5 multiplier and call the reviewed latest-30-return H090 controller. The original generated recipe uses the exact unlagged six-source STATIC50/CSH function bodies. Archived funding-pair PRICE_ONLY_CSH is 24-hour lagged and is not imported or treated as original.
- Keep H090 .30 asset / .90 gross / .15 volatility, isolated1x, fresh10,000 and no-topup identity in a separate fixed native descriptor. Validate direct and preloaded weight paths, including exact certified fixed1.5 proposal equality. No preloaded weight bypass is used.
- Explicitly recreate the reviewed vendor PerpetualConfig from the original .60 config class, with exact Decimal cost/profile fields and only .90 gross changed. Passing HighRiskToyAccount directly to original account_for_cost still fails. BASE27 and STRESS43 identities remain exact.
- Retain one actual unchanged reviewed Decimal account behind a small fill-routing facade. Reserve9,000 original capital for the single control owner. CapitalGuard previews and commits exact charged fills, with actual isolated balance<=8,500 and freecash>=1,000 for increases. A .90 planned target can be admitted while its requested execution is capital-rejected. Target notional, planned commitment and actual margin/cash are different quantities.
- Check prospective charged actual inventory plus all single-owner pending quantity corners against .90/.30/.15 before every nonreplay increase. This conservative rectangle can reject intermediate hedge risk even when the final signed target is low risk. It introduces no extra position, debit or fee. Finite-program ownership/admission is absent.
- Preserve the original native daily loop after the distinct admission block, .99 sizing, all clocks, funding-before-fill, reductions-before-increases, original reversal behavior and shared prior-minute capacity. Reuse the exact cached reviewed terminal60 adapter: signal end-minus61minutes, 60 eligible real attempts, no free residual close.
- Use explicit externally supplied synthetic source registry hashes, exact latest UTC bars and real supplied per-bar availability fields within the generated fixtures. Invalid/stale/delayed source schedules original DATA_GAP_EXIT. Inventory survives until actual paid reduce-only fills; zero liquidity can stop the case with unpaid inventory.
- Normalize malformed null/order fields and huge JSON-close TypeError/OverflowError into SourceReadinessError. At the native boundary only the two exact covariance-invalid source risk codes also become source gaps; financial errors still propagate. Reviewed sizing bytes and mathematical AST remain unchanged. Original financial arithmetic is byte-identical, with the reviewed one-line vendor gross-validation extension only.

## Runnable generated checks

Use Python3.12 with numpy2.3.5, polars1.44.2 and pyarrow23.0.1. This workspace reuses cached official installations and does not download them.

    PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python run_verified.py --freeze-sha REVIEWED_FREEZE_SHA256 tests
    PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python run_verified.py --freeze-sha REVIEWED_FREEZE_SHA256 generated --receipt-dir generated_receipts_new
    python run_checks.py --freeze-sha REVIEWED_FREEZE_SHA256 --receipt-dir bounded_receipts_new

Run from this directory with the exact externally supplied SOURCE_FREEZE.json hash. COLD_RUN.txt contains the frozen command. Receipt directories must be new. The verified entry compiles checked project .py bytes for ordinary imports and explicit file-spec helpers, including vendor namespaces. Matching timestamp .pyc is never used; unverified cached project modules and changed compiled function bodies reject. Direct ordinary imports before this bootstrap are not a supported certified entry. The bounded command validates the frozen code closure and runs fixed generated commands under one CPU, one math thread, 4GiB address-space/60CPU-second/120wall-second limits. No historical argument is supported. Source normalization parity baselines are exact cached copies within dependencies; no sibling review directory is needed for those tests.

## Recovery and remaining blockers

H090 snapshots have a distinct version and capture its descriptor, source/risk identity and availability, config/account, original targets, reservation, pending state and receipt/cost/funding journals. Restore and fork explicitly refuse because exact split-run H090 source/owner/pending/Decimal parity has not been implemented and tested. Do not call this full recovery.

Real provider/index/arrival authority remains unavailable. Synthetic SHA consistency is not real source certification. Original complete200-bar eligibility remains required, and no missing source end/arrival is filled or backdated. Historical target/source recipe admission, native filter/mark/funding certification, independent review and explicit parent GO remain separate gates. Full recovery and the finite-program strategy remain unimplemented. History stays NO_GO.

## Source closure

DEPENDENCY_PINS.json binds all copied cached original/account/terminal/target/regression code. The original in-memory no-default-strategy stub is separately bound to its exact compiled port functions and immutable original metadata. SOURCE_FREEZE.json binds this new adapter and protocol. Original scheduler/controller/account/cost sources and ExecutionContractV2 are unedited. The old contract is reused for clock/cost arithmetic only; its .60/.30/.10 fields are not relabeled as H090 certification. The original strategy default-target loader is deliberately unreachable in the verified cached port; generated original function bodies or explicitly guarded factory targets supply this narrow boundary.

Development failures are retained in NATIVE_TEST_RESULTS_001.txt: two test-expectation errors (a Decimal zero exponent spelling and funding receipt field name), corrected without changing finance. ATTEMPTS.json records all bounded executions. No result here estimates future ruin probability or promises stable APR.
