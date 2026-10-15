# Bounded native continuation: source/code-only integration

Known limitation: the frozen financial-policy V1 is diagnostic/superseded for the intended continuation-only comparison. A stale/unknown-mark path adds paid exits in B beyond the old baseline quality block. The source/generated review passed, but did not establish historical missing-gap policy equivalence. Read [KNOWN_LIMITATION_V1.txt](KNOWN_LIMITATION_V1.txt) before using any source or review in this publication. The archive's v2 suffix is a packaging revision, not a corrected financial-policy version. A corrected policy needs a fresh version, independent review and new exact GO.

This additive publication preserves the exact reviewed source, generated-test evidence and source-admission receipts. It contains no historical market arrays, saved financial account results, credentials or newly valid root GO. Publication grants no historical execution, retry, recovery, live-trading or venue-certification authority.

## Exact packet

The [complete ZIP](bounded_native_continuation_code_public_recovery_20261015_v2.zip) is 291,965 bytes, with SHA256:

84b608e47ddf684316ce8d3be043dc05682ebe0d52e3e0cd08991dbcf813ca49

The expanded [packet](bounded_native_continuation_code_public_recovery_20261015_v2/) contains 72 files. Its [FILES.json](bounded_native_continuation_code_public_recovery_20261015_v2/FILES.json) binds 71 payload files; the manifest itself is bound by the publication [RECOVERY_MANIFEST.json](RECOVERY_MANIFEST.json). The ZIP and every expanded file are byte-identical to the independently checked public copy. [PUBLIC_COPY_INDEPENDENT_PACKAGING_REVIEW.json](PUBLIC_COPY_INDEPENDENT_PACKAGING_REVIEW.json) records the separate packaging review.

Read the unchanged [integration README](bounded_native_continuation_code_public_recovery_20261015_v2/bounded_native_continuation_20261015/README.md), [original independent review](bounded_native_continuation_code_public_recovery_20261015_v2/bounded_native_continuation_independent_review_20261015/INDEPENDENT_NATIVE_CONTINUATION_REVIEW.json), and [public-copy metadata](bounded_native_continuation_code_public_recovery_20261015_v2/bounded_native_continuation_20261015/PUBLIC_COPY_METADATA.json), together with the publication-level known limitation above. The immutable review records 39 author-suite tests and 13 independent adversarial tests passed, plus reuse of 57 frozen primitive checks. The packaging review separately reran the generated-only 23-test subset. Those passes do not establish the missing historical policy equivalence. This publication step does not repeat financial runs or infer financial performance from generated tests.

## Recovery and limitations

Verify the ZIP length and SHA256 before extracting into a clean directory. The included read-only verify_code_package.py verifies the payload against FILES.json without creating an account or accepting a GO. Follow the integration README for generated-only tests and their dependencies. Source-audit tests require separately restored exact pinned source inputs and target artifacts; full cold historical replay is not supplied by this source-only packet.

The new ROOT_GO template is deliberately unapproved. Two old execution-environment-specific GO documents and an internal launch handoff are omitted from this public copy. Their exact dependency hashes and original runtime checks remain unchanged. The exact review-bound generated resource receipt and referenced source-only verification receipt are included. These choices are documented by PUBLIC_COPY_METADATA.json and the independent packaging review; no sanitized authority is substituted for missing original bytes.

Frozen source and receipts retain their original pre-publication status language. This page records separately authorized source/evidence publication only. Restart, post-HALT restoration, exchange execution, native venue risk tiers, insurance sufficiency, partial liquidation, ADL and intraminute triggering remain uncertified. Conditional insurance or collateral-forfeiture values are research assumptions. C minus B measures the entire bounded margin-management package, and a halted prefix is not a completed annual return.

All pre-existing parent artifacts are preserved byte-for-byte. This publication creates a separate research branch and adds only this directory; it opens no pull request and performs no merge.
