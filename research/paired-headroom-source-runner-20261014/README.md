# Paired HEADROOM cached-source discriminator

This runner consumes the unchanged published paired coefficient module at
7a31299c0f7eb6136599d5954a206944f50b27a2. It compares all original calendar
minutes for 2023, 2024 or 2025 across CORE5 without wallets, owned-state triggers,
targets or new downloads. No source arrays have been run by this preparation.

DEPENDENCY_PINS.json gives immutable repository locators and byte identities.
SOURCE_CASES.json is an exact three-year projection of the original input
registry. Restore code/metadata only for preparation; do not regenerate source.

Use a private roots JSON containing paired_module, input_module, resource_guard,
resource_release, source2023, source2024, source2025 and derived_csv. Paths are
consumer-local. Never publish this roots file or operational command lines.

One fixed CLI:

    python3 source_cli.py preflight --runner-manifest-sha EXPECTED_SHA --roots PRIVATE_ROOTS.json

This checks source and dependency code/metadata identities without importing
NumPy/candidate code or reading any cached source-array file.

After independent code review and a separate exact per-year source-only GO:

    python3 source_cli.py run --runner-manifest-sha EXPECTED_SHA --roots PRIVATE_ROOTS.json --year 2023 --output NEW_ATTEMPT_DIR --review REVIEW.json --review-sha REVIEW_SHA --parent-go GO.json --parent-go-sha GO_SHA

The review and GO schemas are fixed in source_gate.authorization. They bind the
runner, published candidate, source cases and resource policy. The GO additionally
binds its exact year/source index and review hash and explicitly excludes wallets
and new downloads. No preparation receipt grants source execution.

Run synthetic unit tests with PAIRED_TEST_CODE_ROOTS set to the private code-only
roots JSON. They generate arrays and files, use the exact pure adapter primitives,
exercise prefix/derived/readiness/run-encoding controls and refuse missing GO.

    python3 run_synthetic_checks.py --runner-manifest-sha EXPECTED_SHA --roots PRIVATE_CODE_ROOTS.json --output NEW_SYNTHETIC_RECEIPTS

This fixed wrapper runs metadata-only preflight and synthetic tests under one
CPU/math thread, 4GB address space, 2GB sampled RSS, 60 CPU seconds and 120 wall
seconds per command, preserving logs and refusing to overwrite receipts.

Runner, pure input/resource adapters and the original paired/vendor modules are
loaded by directly compiling their hash-verified source bytes. Unpinned bytecode
caches are never executed; vendor initializers and preloaded namespaces are refused.
The worker checks finite positive soft and hard resource caps and all four
one-math-thread environment fields before NumPy or source adapters. Saved archives
are reopened without pickle, checked against their actual hash/schema and decoded,
including READY float bits, masks/reasons and missing NaNs, before decode_equal.
An inherited controller pipe binds the live parent, year, manifest, review/GO
and private roots hash before source imports. Direct worker invocations fail
closed. Observer or launch errors kill/reap any running worker and preserve an
explicit failure receipt; no automatic restart occurs.

Historical attempts retain START.json, WORKER.log and RESOURCE_RECEIPT.json.
Results contain all-minute lossless coefficient runs, exact array hashes, daily
and annual summaries. Six coefficients compare alignment separately from coupling.
No lossy precision, sampled scenarios or economic threshold is used. Archives
are decoded and checked before reporting success. An output cap failure preserves
the attempted output rather than silently dropping evidence.

The controller reuses unchanged original admission/resource guards and shared
lock, reserves one worker, and retains their two-free-CPU requirement. One CPU,
one math thread, 2GB aggregate RSS stop, 4GB address space, 600 CPU seconds,
900 wall seconds, original host/swap/cgroup/disk guard, and 50MB total output.
These are enforced limits, not a promised completion time. Symbols and years
are serial. No automatic retries or old output overwrites.

Coefficient differences help decide whether a changed stress assumption warrants
further review. They do not establish actual trigger changes, economic value,
profit or safety. Independent maxima remain conservative; joint observed pairs
can miss unseen co-occurring extremes. 2021, 2022 and all holdouts remain closed.
