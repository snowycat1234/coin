# Quota preservation checkpoint

2023 financial execution finished all 365 days / 525600 minutes. It is paid flat with saved NAV 11027.113861548723 and net 1027.113861548724 USDT, versus the reused baseline 1027.94932285112 (descriptive change −0.835461302396 USDT). The derived compatibility report did **not** finish: reused holding.py imported another old module named driver. No scientific policy changed and no account was replayed. The failed log, ACCOUNT, DAILY, complete scheduler/account/pending/dedup maps, all37 minute bits and all genuine intermediate snapshots are preserved in `preserved/Y2023/`. State hash f2292ad0cdc464e0a2618042a02fcd19b09b018ae7c807ca4f238b9e3af113cc; final compressed snapshot SHA a8f149c04db1c3cd97befd7114501d6e9c639d2e1d6e483a8c2ed4625ea994c9.

2025 was **not started**. There is no active account, model fit or download. Public native cold verification and final holding/gate reports are NOT_RUN, not PASS. Project remains active; quota preservation is not deletion or completion of the two-year module. The old23 accounts, both original positive FOLLOW candidates and all prior STOPs remain unchanged. Original alpha confidence failures remain; this is known-rule execution compatibility, not new predictive alpha.

The original financial source/code and readiness commit is a801970c775a4590d006801be3826cda7ec67f92; freeze is 762959a86099027d1fe30461598266a43b0de34c. The first prepare call had a wrong literal HEAD SHA and was rejected before creating arrays/account; the second preparation passed. Two own counterexample tests PASS5.17s and three existing golden/prefix/risk tests PASS4.03s. The unpublished read-only compare.py is now saved but NOT_RUN.

Recovery uses only public Git objects. `restore_preserved.py --artifact-commit <published preservation SHA> --state /workspace/follow-cash-restored` validates part, packet, CRC and every member SHA and restores the account. Invoke under the unchanged guard:

```bash
COIN_CPD_STATE=/workspace/follow-cash-restore-guard QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE=/workspace/follow-cash-restore-guard bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python research/follow-cash-compatibility-20261012/restore_preserved.py --artifact-commit <preservation SHA> --state /workspace/follow-cash-restored
```

This byte restoration does not advance the financial account or certify native cold arithmetic. To produce the missing holding report, use the original script in its own subprocess, avoiding the module-name collision:

```bash
COIN_CPD_STATE=/workspace/follow-cash-report-guard QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE=/workspace/follow-cash-report-guard bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python research/rejected-break-follow-native-20261012/holding.py --window Y2023 --account /workspace/follow-cash-restored --destination /workspace/follow-cash-restored/HOLDING_DIAGNOSTIC.json
```

Afterward derive metrics/gates from saved ACCOUNT/DAILY/holding, or restore the complete scheduler via the unchanged restore_snapshot and NativeDailySimulator.from_snapshot APIs and call result only. Do **not** rerun `driver.py run` for 2023 or call advance_day. Fix the reporting import before a future authorized 2025 continuation; the current run entry still contains that known reporting failure.

Canonical public source caches remain at `/workspace/cs-2023-state/SOURCE_OBSERVED` and `/workspace/portfolio-risk-2025-state/PUBLIC_SOURCE_RECOVERED/source`; independent public recovered sources also remain at `/workspace/follow-native-2023-public-cold/source_rebuilt` and `/workspace/follow-native-2025-public-cold/source_rebuilt/source`. If the local caches disappear, use the existing published original cold_source.py SOURCE Git restore; public f38617c5/534a18fb,16e7784d and 9bdaf541/1b7ee23d source/account artifacts remain. No new provider download, lost2026 ledger claim or protected holdout access is needed. Local states/logs are retained. All necessary true2023 account fields are in the preservation packet; no unique necessary account data is intentionally left only locally.
