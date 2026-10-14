# Generated owned-journal preview candidate

This is a reviewable new module and generated-validation package, not a historical source archive or a self-contained historical runner. It includes no market data, source-binding manifest, private environment configuration, original source archive, historical roots, or market fingerprints. It has not been adopted by a historical runner.

## What changed

The explicit owned account variant commits recursively immutable journal rows and stores persistent AVL roots. Native append/identity lookup is O(log n), and account journal forks share immutable roots in O(1). Financial methods and original charged-corner risk logic remain native. The live ownership contract is new and explicit: historical row edits, journal replacement/deletion, and identity overwrites fail.

Exact internal guard tokens use the original native snapshot builder for every finite field, including Decimal strings and contract metadata, plus immutable journal roots. Public full snapshots remain ordinary complete mutable dict/list exports. The separate causal adapter has an AST-checked delta limited to preview dependencies and snapshot-to-exact-token guard comparisons.

## Verified result

The final revision passed 101 generated tests and independent review for the explicit generated-only variant. At 5,000/10,000 generated open-fund-close rounds:

- Complete 32-corner preview: 0.03327 / 0.03372 seconds.
- Complete fresh guard: 0.03373 / 0.03356 seconds.
- Actual native five-fill guarded attempt: 0.06160 / 0.06667 seconds.

Both sizes matched complete native snapshots, directly generated accounting history, and a complete same-tag native charged corner/probe. The processes used 21.41 / 40.52 seconds and 468.7 / 820.7 MB peak RSS under 120-second and 2 GB bounds. Generated validation details and all passing test names are included.

## Portable generated-only reproduction

Prerequisites: Linux with Python 3.12.14, NumPy 2.3.5 and Polars 1.44.2 already installed. PyArrow is not required. The runner performs no downloads or installations and rejects network, descendant processes and data-container access.

Public source dependencies are pinned separately from this new module:

- [v3 public commit](https://github.com/snowycat1234/coin/commit/5089f6ed7a7431ddc72f8b492a323bea394bff1a): directory `research/original-csh-admission-partial-v3-20261014`. Restore `candidate.py`, `native_preview.py`, `test_synthetic.py`, `SYNTHETIC_ONLY_MANIFEST.json`, and `SYNTHETIC_ONLY_RESTORE_MAP.json` into V3_DIR.
- [v4 public commit](https://github.com/snowycat1234/coin/commit/22a411fbcaeba255d62c1fbd510b11ac6d183f77): directory `research/original-csh-causal-execution-v4-20261014`. Restore `causal_adapter.py`, `test_causal_integration.py`, and `SOURCE_MANIFEST.json` into V4_DIR.
- Materialize the 18 public code bodies named by the v3 [synthetic-only restore map](https://github.com/snowycat1234/coin/blob/5089f6ed7a7431ddc72f8b492a323bea394bff1a/research/original-csh-admission-partial-v3-20261014/SYNTHETIC_ONLY_RESTORE_MAP.json), using each entry's already-public authority source and exact destination relative to CODE_ROOT. The runner checks all 18 sizes/SHA256 values. Do not substitute a historical restore map or market archive.
- MODULE_DIR is this new package directory. Its reviewed seven module/test files are pinned by the portable runner. The runner verifies the three public manifests and all required code before importing native finance.

Use explicit local paths; no particular parent directory layout is required:

```sh
timeout --signal=TERM --kill-after=5 125s \
  "$PYTHON" -I -S -B "$MODULE_DIR/run_portable_generated.py" \
  --code-root "$CODE_ROOT" \
  --v3-dir "$V3_DIR" \
  --v4-dir "$V4_DIR" \
  --module-dir "$MODULE_DIR" \
  --runtime-site "$NUMPY_POLARS_SITE_PACKAGES" \
  --rounds 25 --output "$FRESH_OUTPUT"
```

Repeat `--runtime-site` if the two installed packages occupy different site-package directories. Each output directory must be new. To repeat the large-journal measurements, run separate processes with `--rounds 5000 --bench-only` and `--rounds 10000 --bench-only`; keep the same resource limits. The non-benchmark-only run executes all 101 tests.

The runner stages exact reviewed code under the fresh output directory only to preserve an unchanged AST test's sibling-source lookup. No reviewed module is rewritten. It emits `PORTABLE_RECEIPT.json` without caller filesystem paths or historical metadata. `PORTABLE_SMOKE.json` records an actual relocated-directory smoke run: 101 tests passed in 2.63 seconds at about 104 MB peak RSS. A deliberately altered module copy was rejected before finance imports. Failing unittest logs can include caller paths and should be reviewed before sharing.

Only minimal new code, generated validation and the portable launcher are included here. Original dependency archives and full private receipts are not redistributed. This reproduction creates generated fixtures only and grants no historical data access or execution permission.

## Limits

- Total stored history, one-time admission, complete snapshots, state hashes and recovery remain O(history). There is no annual-runtime or bounded-total-memory guarantee.
- Supported execution is trusted, single-threaded, native append/new-key usage. Reflective/private-field invariant bypass is excluded.
- Use full public snapshots or returned ordinary receipts for serialization. Raw wrapper JSON and internal root-token serialization are unsupported.
- Bare native financial/scheduler checkpoint recovery is supported. Fork/state_hash fail closed with instance-bound schedule/attempt adapters. Portable snapshots do not serialize causal-adapter source bindings/receipt state; installed-adapter fork/hash/restart and pending-order continuation are not certified.
- New class/module identities must never be relabeled as the original verified runtime or used to bypass historical/public admission.

All original reviewed source and market-data access restrictions remain in force.
