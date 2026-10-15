# Financial V1 saved results: DIAGNOSTIC / SUPERSEDED

**Intended-policy conformity failed. These are the original financial V1 diagnostic results, not corrected financial V2 results.** The V1 monitor manufactured full-position paid exits during a known stale/unknown-mark gap, while frozen A only blocked new risk. B changed before its first conditional settlement. No intended-policy performance, unchanged-admission continuation-only attribution, or pure top-up causal effect is established.

This additive saved-results publication follows corrected V2 source commit [c00c14b25b30a339195fe089acb6bd4d24a29f5f](https://github.com/snowycat1234/coin/commit/c00c14b25b30a339195fe089acb6bd4d24a29f5f) only to preserve publication history. Its parent does not change the financial policy version or meaning of this immutable V1 packet. The earlier source archive's packaging V2 suffix was not a financial-policy correction.

## Direct evidence

- [Saved diagnostic summary](SAVED_DIAGNOSTIC_SUMMARY.json) and [exact original diagnostic report](DIAGNOSTIC_REPORT.json)
- [Exact policy-variance addendum](V1_DIAGNOSTIC_POLICY_VARIANCE_ADDENDUM.json), controlling interpretation over earlier admission/performance claims
- [Exact independent packaging PASS](INDEPENDENT_PACKAGING_REVIEW.json), SHA256 be930638320197ee1a63fea5f811945a2597e3a26f1864b9a0cb117d4ac3297b
- [Exact packet README](PACKET_README.md), [payload manifest](PACKET_MANIFEST.json), and [original archive receipt](ARCHIVE_RECEIPT.json)
- [Transport manifest](TRANSPORT_MANIFEST.json) and [publication recovery manifest](RECOVERY_MANIFEST.json)

The immutable report, packet README and archive receipt retain their pre-publication status fields. The later independent PASS is external to the archive; those earlier fields are preserved history rather than the current publication status. The independent approval covers saved-source fidelity, integrity, diagnostic qualification, privacy and stated recovery limits. It does not certify strategy performance, venue behavior, restart recovery, or financial-policy conformity. The author saved verifier and all 11 packaging tests passed; the independent reviewer checked saved evidence and four narrow tamper tests, without repeating the full author suite or financial model.

B observed conditional-model return was 10.545535019463025%, with paid net return null and one conditional collateral-forfeiture settlement. C observed paid diagnostic return was 10.468792390123087%, with five internal transfers and no extra external cash. Their observed difference has no pure-top-up causal interpretation. Exact values and assumptions are in the report. Both saved primary ledgers reconcile exactly; the explicit 9E-36 USDT secondary bridge residual is retained separately.

## Reassemble the unchanged ZIP

The original ZIP is **951,860 bytes**, SHA256 **e10988b38ac13f3dea6caa48ea3d1096132f6f932a1587feb0f68cd3129ae514**. It is transported as two consecutive 475,930-byte raw chunks, each below 500,000 bytes. This is a byte split, with no archive modification or recompression. Download both parts and the transport manifest from this same commit. Verify their sizes and SHA256 values in TRANSPORT_MANIFEST.json, then concatenate in sequence:

    cat bounded_native_continuation_v1_diagnostic_saved_results_public_recovery_20261015_v1.zip.part001 bounded_native_continuation_v1_diagnostic_saved_results_public_recovery_20261015_v1.zip.part002 > bounded_native_continuation_v1_diagnostic_saved_results_public_recovery_20261015_v1.zip
    sha256sum bounded_native_continuation_v1_diagnostic_saved_results_public_recovery_20261015_v1.zip

Verify the full ZIP size and SHA256 above before extraction. Extract into an empty directory. The ZIP contains 49 exact files under one packet directory; MANIFEST.json pins its 48 payload files. The included Python verifier and 11 tests need only the standard library and validate saved data without constructing accounts or running the strategy. See PACKET_README.md for commands and detailed limits.

## Recovery limits and scope

This packet preserves saved primary ledgers, exact event records, terminal audit state, 366 daily and 12 monthly summaries per case, narrow stale-gap evidence and original attempt history. It omits full minute arrays, full raw audit/native JSON, complete source market arrays, scheduler/pending history and restartable state. Hash pins do not replace omitted bytes. The narrow gap witness does not re-prove complete A/B prefix identity. The DEV coarse venue profile, BASE27 friction and unconfirmed RAW_AS_FRACTION funding assumptions remain uncertified.

No historical financial run, strategy change, new download, live order, Library action, pull request or merge was performed for this publication. The existing parent tree is preserved and main is unchanged. This archive grants no new execution authority.
