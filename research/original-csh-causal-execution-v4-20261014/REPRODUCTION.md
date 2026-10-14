# Generated-only reproduction

Use Python 3.12.14, NumPy 2.3.5 and Polars 1.44.2. Install the immutable v3 files and the 18 minimal native dependency bodies described by `PUBLIC_DEPENDENCY_MAP.json`, retaining their destination paths and exact hashes. No market archives are required. The source manifest must match before launching. Choose a fresh, nonexistent output directory for each attempt.

The final process used this command, from the restored workspace:

```sh
timeout --signal=TERM --kill-after=5 120s env ROOT_CAUSAL_TEST_GO=REVIEWED_GENERATED_ONLY \
  coin_partial_restore_20261014/.venv/bin/python -I -S -B \
  coin_partial_restore_20261014/research/original-csh-causal-execution-v4-20261014/run_synthetics.py \
  --code-root /workspace/scratch/68ef1b82bcac/coin_partial_restore_20261014/minimal_code_root \
  --v3-root /workspace/scratch/68ef1b82bcac/coin_partial_restore_20261014/research/original-csh-admission-partial-v3-20261014 \
  --output /workspace/scratch/68ef1b82bcac/coin_partial_restore_20261014/causal_execution_attempt004 \
  --manifest-sha 24b91fdda425e2dc9e28d1ccc22bb0182c3c8fb11b0c2a5ab0c00819900a34f4 \
  --runtime-sites-json '["/workspace/scratch/68ef1b82bcac/coin_partial_restore_20261014/.venv/lib/python3.12/site-packages", "/opt/codex/runtimes/codex-primary-runtime/dependencies/python/lib/python3.12/site-packages"]'
```

For a portable installation, substitute the interpreter, launcher, code root, v3 root, fresh output directory and local site-package directories. Keep the exact versions, isolated/no-site/no-bytecode flags and final manifest SHA. The launcher reads its own directory for the adapter, tests and manifest, so all four belong together.

The 120-second wall limit begins at actual test-process launch, after implementation is complete. The process records its own start and deadline, has an independent outer wall timeout, 120 CPU seconds, 4GB address-space limit, 2GB monitored RSS, 25MB output limit and one-core affinity. Network connections, subprocesses and market/data-container reads are forbidden inside the generated test stage. Logs, manifests, exact input snapshots and receipts are preserved on failure and success.

Final observed receipt: 46 tests, exit 0, 0.759323868 seconds wall, 0.785116 seconds CPU, 94,588,928 bytes peak RSS. No historical GO.
