# Published 2023 source recovery

This package recovers only previously published CORE5 2023 research inputs. It is not a strategy test, a wallet checkpoint, or recovery of an interrupted account. It does not establish profitability or native venue economic authority.

The immutable manifest identifies 312 files (158,865,245 bytes): all 239 raw archive parts, the original code closure, source certificates, daily closes and three funding transport parts. Reassembled originals comprise 120 monthly trade/mark archives plus five February 24 daily mark repairs. Each part and original archive was SHA-256 verified; all 125 original ZIPs passed CRC.

Run `python recover_public_cache.py --destination DIRECTORY` for offline verification. Add `--download` to fetch only missing files from the exact public GitHub commit URLs. The script does not overwrite mismatches, retry errors, request credentials, or fall back to other hosts. It never contacts a market-data provider. Access errors stop the operation. Current recovery used the GitHub connector's base64 file route, verified byte-for-byte; the standalone urllib network route has not been live tested here. Its cached-file validation and fail-closed cases have been tested.

Keep this entire small package alongside the downloaded directory; all large inputs already exist at the manifest's public immutable GitHub commits and are not duplicated in this branch. Source reconstruction and the remaining limitations are reported separately. Only 2023 funding columns are projected by an explicit timestamp predicate; unrelated feature members and held-out 2026 values are not inspected.

Generated execution tests in the sibling package are software checks, not substitutes for strategy economics. No old wallet is rerun. No claim is made that the lost 565-day account state was recovered.

## Exact reconstruction result

`reconstruct_source_only.py` ran the unmodified published 2023 source builder and normalizer, replacing only transport reads with finite SHA-bound local objects. Its two required funding/date functions are unchanged AST nodes, projected without importing unused wallet/ML modules. This is explicitly a materialized-source adapter, not a fabricated full Git checkout. Normal Python is required; optimized mode is rejected because the original source uses assertions.

Actual reconstruction completed in 75.83 seconds: all 12 monthly NPZ files, DAILY.json, EVENTS.json, and the complete SOURCE_INDEX.json match the original published bytes exactly. Coverage is 365 days, 525,600 minutes per asset, and 1,095 funding events for each of five assets. Peak measured RSS was approximately 346 MiB. No account, fit, provider request, or held-out2026 value was used.

To reconstruct in a new workspace, place this package's files in the chosen directory, use its recovery script to materialize the manifest there, and run `python reconstruct_source_only.py` from that directory. The adapter expects numpy/pandas plus pyarrow and requests/urllib3, either normally installed or in local `deps/`. This run used NumPy2.3.5, pandas2.2.3 and PyArrow26.0.0; inspect SOURCE_ADAPTER_PREFLIGHT.json for actual exact versions. No automatic package install is performed. A fresh `reconstructed_source` directory is required; existing results are never overwritten.

Limits retained: the January1 starting close is the original SHA-bound daily cube, not independently recovered December31 minute data; funding economic unit/charge point/MMR/arrival assumptions remain conditional. Full raw funding-member date extents were not inspected; only predicate-bounded2023 columns were read. This verified basis enables a newly specified research experiment, not continuation of the missing565-day wallet.
