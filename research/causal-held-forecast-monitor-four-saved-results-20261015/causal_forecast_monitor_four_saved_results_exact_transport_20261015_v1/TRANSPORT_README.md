# Exact two-part saved-results ZIP transport

This transports the immutable compact four-case causal held-forecast monitor saved-results ZIP. The preserved research prototype was not adopted. No packet, financial JSON, review, manifest or ZIP member is repacked, recompressed or changed. Raw market/source/target/MINUTE arrays and private process/authority bodies remain excluded. The parts are byte ranges, not independently usable ZIP files.

Reconstruct the ZIP first, in this exact order:

    cat causal_forecast_monitor_four_compact_saved_results_public_recovery_20261015_v1.zip.part001of002 causal_forecast_monitor_four_compact_saved_results_public_recovery_20261015_v1.zip.part002of002 > causal_forecast_monitor_four_compact_saved_results_public_recovery_20261015_v1.zip

Validate all part sizes and SHA-256 values against TRANSPORT.json. Then verify the reconstructed ZIP has exactly 9763557 bytes and SHA-256 d67e29d7788f1867e165f6f72c74d157566277cd00293f6d7420bdb8e75c921f. It contains exactly 121 members; validate ZIP CRCs and the embedded MANIFEST.json before running the compact saved-only verifier/tests. Do not unzip the parts separately.

Part 1 is 8388608 bytes and part 2 is 1374949 bytes. Each is at most 8 MiB. Concatenation was verified byte-for-byte against the original sealed ZIP. Hashes of omitted arrays do not reconstruct those arrays; see the immutable packet README for deep-recovery and prior-control dependency limits. This transport is no financial execution or publication authority. Any later results publication must be an additive child of the fully byte-verified source commit 17869a926eee3c78863001b52860c2e6972d6891, with independent packet and transport review.
