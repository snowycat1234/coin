# Bounded account continuation: generated-only primitive evidence

This publication contains a public-safe copy of the reviewed bounded isolated-margin continuation primitive. The sealed ZIP is the complete reproducible packet; the selected direct files are for browsing and review, not a standalone runnable checkout. Existing repository artifacts and frozen baselines are preserved.

## Evidence and scope

- 57 synthetic-observation tests passed in the sealed review evidence: 45 author tests plus 12 independent tests. The independent clean-extraction packaging review also records 57 passed tests. This publication step does not rerun tests or financial accounts.
- No historical GO/admission, historical replay, new financial result, live order, credentials or locked-source access is included or authorized by publishing this packet.
- Native V3 scheduler/32-corner integration, persistent restart/recovery and post-HALT resume remain unadmitted.
- Conditional collateral forfeiture is a disclosed research scenario. It is not venue-certified liquidation or proof of historical Bybit behavior. Conditional insurance value and residual forfeiture remain explicit; real unpaid debt is never forgiven.
- C minus B measures the entire bounded management package, not a pure transfer-only effect. An unfinished A HALT prefix cannot be compared as a completed annual return.

## Sealed files

Download [the complete ZIP](bounded_account_continuation_public_recovery_20261015_v1.zip) and check its 83,855-byte length and SHA256:

48757bc9936c45443af10b7a36421ea8e141c553e4fe7dc1e77bb7b6f1c2cc09

[RECOVERY_MANIFEST.json](RECOVERY_MANIFEST.json) records publication file hashes and recovery steps. [PUBLIC_COPY_INDEPENDENT_PACKAGING_REVIEW.json](PUBLIC_COPY_INDEPENDENT_PACKAGING_REVIEW.json) binds the ZIP, public manifest and sanitized transformation map.

The unchanged reviewed primitive [README](bounded_account_continuation_public_recovery_20261015_v1/README.md), [POLICY](bounded_account_continuation_public_recovery_20261015_v1/POLICY.json), [code](bounded_account_continuation_public_recovery_20261015_v1/continuation.py), [original primitive review](bounded_account_continuation_public_recovery_20261015_v1/independent_review/REVIEW.json), and [binding addendum](bounded_account_continuation_public_recovery_20261015_v1/independent_review/FINAL_BINDING_ADDENDUM.json) are browseable directly.

## Recover and verify

After checking the ZIP SHA256, extract it to a clean directory. From the extracted packet, with Python and NumPy installed, run:

python -B verify_packet.py

python -B -m unittest -v test_continuation independent_review.test_independent

Use the extracted packet's FILES.json and verify_packet.py. Files under original_receipts are historical original-packet seals, not the public-copy manifest. Only four copied evidence documents were sanitized, replacing private execution-prefix text while preserving failure history and line structure. Code, financial policy, tests, five primitive pins, and original independent reviews are unchanged.

POLICY.json's publication=false and the original README's no-publication statements are preserved as frozen pre-publication evidence. This page records the separately authorized public publication; it changes no financial or historical admission status.
