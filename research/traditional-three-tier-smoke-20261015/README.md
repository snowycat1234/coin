# Traditional 3-strategy × 3-risk 1x DEV recovery package

This is a new clean recovery package of the completed V3 technical smoke. Read REPORT.md first. It contains unchanged frozen source, public dependencies, generated tests, independent review, compact saved simulation evidence, source-only preparation, and source recovery locators. No new actual-source historical account or financial history run, fit, download, upload, or publication was performed to build it. Generated tests use synthetic account fixtures.

The smoke covered [2023-01-01 00:00, 2023-01-04 00:00) UTC. Every one of the nine separate 10,000-USDT conditional simulated accounts completed all 4,320 minutes and paid flat. This is three-day seen-development technical evidence. It establishes no annual, untouched-OOS, live-use, investment, or independent-alpha claim.

## Check the package without market payloads

Use Python 3.12 and the pinned existing dependencies in requirements.txt. From this package root:

    python verify_package.py
    python run_portable_checks.py

The second command runs 56 builder generated tests, 32 independent generated tests, seven constructor-negative tests, and five offline recovery-helper schema tests. Generated tests use synthetic account fixtures; no actual historical account is constructed or advanced. Validation logs and receipts are under validation/.

All 39 original independent test sources and their original passing log are included unchanged. The remaining seven independent source-gate checks require the exact source payloads described below. They patch the actual account constructor and perform source/target checks only.

## Recover the omitted public source

No raw market archive or normalized twelve-month market payload is included. The exact source is already public. Recover its bytes through an authorized existing repository checkout using native_2023_source_restore_20261015/public_recovery_package/RECOVERY_MANIFEST.json, README.md, and the offline verify_recovered_2023_source.py helper. PUBLIC_SOURCE_LINKS.json adds recorded GitHub locators without downloading them. The helper verifies recovered bytes; it is not an automatic downloader or replacement normalizer.

Keep the sibling directory names in this package. Place recovered original DAILY.json, EVENTS.json, SOURCE_INDEX.json and months/2023-01.npz through months/2023-12.npz under native_2023_source_restore_20261015/prepared_2023/. Small exact warmup/proof support is already included.

Then, only for read-only source verification:

    python native_2023_source_restore_20261015/public_recovery_package/verify_recovered_2023_source.py --source-root native_2023_source_restore_20261015/prepared_2023 --warmup native_2023_source_restore_20261015/SOURCE_WARMUP_CLOSE_ONLY.npz --proof-directory native_2023_source_restore_20261015/original200_proof
    python run_portable_checks.py --with-restored-source

The latter runs all 39 independent checks. It cannot authorize a historical or annual run. The unchanged saved-output reviewer can also re-audit the saved smoke without account creation after those source bytes are restored; its command is in REPORT.md.

## Exact copies and sanitation

COPY_SOURCE_MANIFEST.json identifies every copied source and any sanitized derivative. FILES.json covers the complete deliverable inventory. Original public dependencies are byte-identical; three already-public /home reference strings in the hash-pinned joint_expert_information.py remain unchanged. No newly captured private execution path or raw traceback is included. The failure addendum is sanitized and explicitly says the failed MID partial financial snapshot was never saved.

The old V2 runtime and spec were recovered by a narrow reversal and verified against their preexisting exact SHA256 identities. They are separate archival files under superseded_attempt001_v2/, not the active runtime. Do not combine attempt001 prefixes with attempt002 to make a longer or complete account.

The copied module README.md is preserved as source documentation. REPORT.md supplies the completed smoke status and current evidence qualifications. Annual source-only work is separate and absent from this package; no annual execution approval is created here.
