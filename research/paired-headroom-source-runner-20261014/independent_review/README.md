# Independent source-runner review replay

Review status: code and generated-data PASS only. No historical source or wallet GO.

Verify the review receipt and exact runner manifest d0148be6c9e3ecd24742cd005fff93b512f11a0f59346fddd5113f04c269e297 before imports. Restore only the immutable code and metadata listed by the runner DEPENDENCY_PINS.json. Do not retrieve cached source arrays for this replay.

Supply a consumer-local code-only roots JSON with paired_module, input_module, resource_guard and resource_release. No historical source roots or derived CSV are needed. Run the runner's fixed run_synthetic_checks.py first to check metadata and 27 generated unit tests. Then run:

    python3 run_independent_bounded.py RUNNER_DIRECTORY NEW_REVIEW_OUTPUT CODE_ONLY_ROOTS_JSON

The independent replay has 19 active generated checks and 5 intentionally skipped probes of the rejected old freeze. It independently checks scientific endpoint populations, coefficients, strict-prior alignment, warmup/derived expiry, authorization mutations, failure preservation, all six repaired blockers and actual cold-CLI rejection of injected bytecode. Its nested cold check reruns the unchanged 27 generated tests. The wrapper uses one CPU/math thread, 4GB hard address space, 60 CPU seconds and 120 wall seconds per process, plus a 2GB sampled parent-process RSS stop. Nested numerical children inherit CPU affinity and hard limits. These limits are not completion forecasts.

The review assumes trusted Python 3.12 standard library, NumPy 2.3.5 and stable local files. Resource-host admission and cached source execution remain untested. A separate exact year GO is required before reading 2023/2024/2025 caches.2021,2022,locked2026 and unknown holdouts remain closed. Coefficient changes do not certify wallet triggers, PnL or safety. No universal paired dominance claim is made.
