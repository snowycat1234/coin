# Causal execution headroom shadow

Read `REPORT.md` for results and limitations. This module is a single frozen, independently reviewed, read-only scan of existing original fine CSH accounts. It does not construct or advance a financial account, change a strategy path, or compute counterfactual PnL.

## Components

- `headroom_buffer.py`: independent causal past-30-day feature/trigger calculations and posterior capacity/cost witnesses.
- `PROTOCOL.json`: exact formula, scope and resource bounds.
- `INPUTS.json`, `FROZEN_CODE.json`: existing source, targets, ledger, dependency and code identities.
- `REVIEW_RECEIPT.json`, `OUTPUT_REVIEW_RECEIPT.json`: independent pre-scan and post-scan validation.
- `COMPACT_RESULTS.json` and `scan/SUMMARY.json`: published complete population counts, unavailable coverage, exact 2024 XRP first/last witnesses and zero-trigger 2025 details. Four lossless `.csv.xz` archives preserve all 2,137 nonempty trigger rows. `TRIGGER_ARCHIVES.json` identifies exact compressed Git SHA/size and original CSV SHA256/count; decompress before checking the original CSV hashes. Complete 25-file outputs and all episode witnesses remain unchanged in the original research workspace and are bound by `OUTPUT_MANIFEST.json` and independent output review; empty headers and full episode-result JSONs are not duplicated here. Remote binary full-content restoration is NOT_RUN; remote archive validation is tree SHA/size.
- `OUTPUT_MANIFEST.json`: exact hashes of all 25 retained scan outputs.
- `RESOURCE_RECEIPT.json`, `PREFLIGHT.json`: actual bounded run observations.
- The preceding original-path maintenance-distance evidence remains in its original source workspace; this scan does not repeat it.

## Reproduction layout

The existing source/month NPZs and original lossless account checkpoints are intentionally external to this small public module. Materialize the exact already-authorized artifacts identified by `INPUTS.json` in a common workspace; place this module directly beside the named `coin_*` directories. Its filesystem root is the module's parent. These are input transport locators, not new provider downloads or permission to construct wallets. Independent tests use the same audited workspace layout.

`python test_synthetic.py` exercises only synthetic data. The historical scanner refuses a run unless its exact frozen code/input identity, independent review, finite CPU/address-space limits, one-CPU affinity, memory, swap and disk gates pass. Preserve the original output `scan/` directory: `mkdir` and exclusive writes prevent accidental replacement or rerun in that output namespace.

The actual authorized run used the exact bound existing `coin_native_half_mix_20261013/bounded_cloud.py` continuous aggregate-RSS/shared-host watchdog with a 900-second wall bound, plus inner `prlimit --cpu=600:600`; it executed `python coin_causal_headroom_shadow_20261013/scan_shadow.py scan`. One run completed in 33.06 seconds. Do not infer economic replay permission from this read-only module.

No new external model or copied third-party finance implementation is introduced. Finance, costs, source transport and quantity assumptions are existing project dependencies retained only as byte-bound read inputs. NumPy/stdlib are used for observer calculations.
