# Existing 2024 funding inputs +22-day warmup — source export only

5820 actual preserved observations,2024=5490 and2023-12-10 inclusive to2024-01-01 exclusive=330. End2025-01-01 exclusive. Each asset1098year events +66warmup. Exact observed millisecond offsets are preserved in integer event_us; no arrival/publication/charge-time certification.

LIMITED: every requested hash-bound existing reference event is recovered with no missing/duplicate, but this is not independent certification of the provider's complete settlement set. Coverage authority is the pinned old year source index/canonical EVENTS plus actual H1 manifest and checksum-verified H2 monthly funding archives; no cadence-based completeness inference. Per asset/month counts, first/last, hashes and missing-from-reference are in COVERAGE.json; provider missing count remains null.

3060source_reported_interval_hours values are null:2730H1year observations+330warmup. H1 parquet has funding_interval_hours in its existing normalized data, but original provider CSV/derivation is not available in the inspected wrapper. Preserve that separately as existing_normalized_interval_hours; NEVER promote it to source-reported interval. The2760H2rows have exact original CSV reported interval. No neighboring/future event/cadence/default8-hour substitution.

H2 raw_rate_text is the exact CSV token. H1 raw_rate_text=null, but the actual existing Float64 last_funding_rate field is preserved exactly by hex and source parquet hash/row. The existing normalized rate is the unchanged original EVENTS raw_rate; original unit remains UNCONFIRMED_RAW_PRESERVED, no scaling or monetary reinterpretation. All source identities/row locators retained in SOURCE_IDENTITY.json.

Reproduce using existingPython3.12/polars only, no dependencies/network/provider downloads installed or invoked:

    python extract_funding.py --source-2024 EXISTING_2024_SOURCE_PREPARE_ROOT --source-2023 EXISTING_PREPARED_2023 --output NEW_EMPTY_EXPORT_DIRECTORY

The source2024 root contains source/H1.zip, original three tail wrappers and prepared_2024/{SOURCE_INDEX.json,EVENTS.json}. Inputs are exact old public wrapper bytes bound to d69e9ac94478c5be54cb46c622afec7aaf3c61f7 at research_artifacts/e5_h1_tail_coverage_pair_20261008/INDEX.json and research_artifacts/native_20261008/INDEX.json. Existing source archives are not republished. Source2023 reference is its original hash-bound prepared SOURCE_INDEX/EVENTS. The extractor refuses changed identities, missing references, duplicates or mismatched rates; raw unreported interval remains null. SOURCE_IDENTITY records exact reference index/EVENT hashes and coverage calendars.

One worker/CPU,2GBRSS/4GBAS/600secondwall; actual source extraction1.385691seconds, controller1.507848seconds, sampledpeak95.3MB. No wallet, strategy, backtest, fit, training, Library, credentials, holdout, purchases, account changes or missing-common200-byte reconstruction. Existing HEADROOM/combination/shared code and prior branches unchanged.
