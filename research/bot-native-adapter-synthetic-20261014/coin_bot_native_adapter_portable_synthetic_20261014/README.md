# Portable generated-only native grid adapter

This is a separate transport revision of frozen c24974783e50ec8b83b199e1c6b271e75fe87d58951c4d581ce53dd46ddf1a0b. Its native adapter, generated fixtures, original 20 tests, export function and scientific protocol are byte-identical to c249. The original c249 source and receipts remain unchanged privately. The changes are the dependency locator/binder, separate toy-only checks and fresh-output wrapper.

The carrier contains exact original financial, cost, scheduler, fine-account bootstrap, terminal60 and selected original CSH source bodies. PUBLIC_SOURCE_LOCATORS.json gives immutable public commit/path/GitBlobSHA1 and exact SHA256/bytes for all 38 carrier bodies. CODE_ONLY_CARRIER.json separately binds those bodies and the five unchanged c249 top-level files. There are no target NPZs, price/funding arrays, original market source indexes or original 26-file LOCAL_CODE_MANIFEST in this package.

The separate code gate reports PASS_SYNTHETIC_CODE_CARRIER_ONLY. It never reports an original historical-closure PASS. The original port's verify, prepared and window transport entry points, and this binder's historical admission aliases, explicitly raise SYNTHETIC_ONLY_TRANSPORT_REFUSES_ORIGINAL26_HISTORICAL_ADMISSION. This replacement changes only transport reachability; all account, scheduler, numerical strategy and cost bodies remain exact. The unchanged original port still installs its original intentional symbol-order stub; no default target strategy or trainable model is introduced.

## Runtime and bounded from-start checks

Supply local installed runtime site directories explicitly, in priority order. The gate requires Python 3.12.14, NumPy 2.3.5, Polars 1.44.2 and PyArrow 23.0.1. Package __file__ and spec origin must equal the first resolvable package from those declared directories, including already-cached imports. Assertions remain enabled. No automatic installation, private host path or inherited PYTHONPATH is used as a dependency locator. The wrapper clears inherited PYTHONPATH and constructs child startup paths only from the supplied arguments.

Use a cache-free source tree. The gate rejects every __pycache__ or .pyc under this package; verified raw source is compiled directly. The binder disables writing bytecode, and the bounded wrapper's children inherit PYTHONDONTWRITEBYTECODE=1.

Run, substituting your own directories:

    python -B portable_checks.py --runtime-site /local/site1 --runtime-site /local/site2 --output-directory /fresh/output

The output directory must not exist and must be outside this source package. The wrapper runs the portable gate tests, unchanged generated tests, then unchanged 33-arm export serially. Each child has one CPU, 4 GiB address-space limit, 120 CPU seconds and 180 wall seconds. Logs, PORTABLE_CHECK_RECEIPT.json, GENERATED_SUMMARY.json and all full account/owner journals go into that fresh output directory. Source hashes are compared before and after. The export wrapper changes only export_generated.HERE, the destination root, leaving its function body unchanged. It does not restore snapshots or resume runs.

For an isolated code/runtime check:

    python -B bind_sources.py --runtime-site /local/site1 --runtime-site /local/site2

For direct unchanged tests, declare BOT_NATIVE_RUNTIME_SITES as a JSON list and set startup PYTHONPATH to exactly the same directories, then run python -B -m unittest -v test_native_adapter. Prefer the bounded wrapper to avoid path or limit mistakes. Consumer output receipts may contain consumer-local absolute paths; publication projections must label any path normalization and preserve the actual immutable source hashes.

## Evidence and limits

The saved c249 generated journals can be replay-audited separately without loading a financial runtime. Newly generated journals must match their complete native account, fill, funding, scheduler, rejection, breach and original-target bodies. Random unique helper session IDs remain unique and may differ between from-start runs; they are not native financial values. No market arrays are opened or even hashed by this new code-only gate. The earlier c249 gate did hash historical target artifact bytes without parsing market values; that accurate earlier boundary is preserved and is not relabeled as a target-free historical-closure check.

This is generated mechanics evidence only. Historical admission, source availability mapping, actual-account historical risk parity, restore/fork/split parity and live Bybit bot replication remain unsupported. The fixed mechanism-inspired policy and its causal/cost/shared-wallet assumptions are unchanged. A future historical driver needs a separate original-target/source/cost admission and explicit authorization; it cannot use this toy-only gate as historical admission.
