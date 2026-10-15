# Public-safe generated primitive packet

This is a new public-safe copy of the reviewed bounded continuation primitive. It contains no new financial result, historical replay, live order or integration admission. The original working packet and integration inputs were not modified.

## What changed

Only four copied evidence documents were sanitized: the source-reference README and the three failed-test logs. Absolute execution/runtime or example directory prefixes were replaced with portable placeholders. Error messages, traceback frames, original source line numbers, line breaks and failure history remain. Code, POLICY.json, test code, the five pinned primitives and the original independent review evidence are byte-identical.

TRANSFORMATION_MAP.json binds every changed file's original and public SHA256, length, exact replacement byte offsets, prefix lengths/hashes, replacement text, line numbers and changed-line hashes. It intentionally does not publish the raw private prefix text. An independent transformation review checks the map against the authorized original bytes.

## Which seal to use

FILES.json is the manifest for THIS public copy. verify_packet.py checks that manifest, all five original primitive pins, the exact reviewed execution hashes, transformation metadata, the absence of private absolute prefixes, and the distinction between this copy and the original receipts.

Files under original_receipts are immutable historical receipts for the ORIGINAL working packet. In particular, original_receipts/FILES.json and original_receipts/HANDOFF.json bind the original evidence bytes before sanitization. They are not manifests of this public copy. original_receipts/verify_packet.py is retained as historical code and is not the public verifier. Do not interpret the original hand-off's old manifest hash as this copy's manifest hash.

Files under independent_review are the original primitive review, final documentation/status binding addendum, tests and logs, unchanged. Their original review admits generated primitives only. It does not certify the new document transformation; that is a separate packaging review. It also does not admit historical runs, native scheduler/32-corner integration, recovery or venue liquidation certification.

README.md describes the unchanged primitive and its financial/model limitations. C minus B is the entire bounded management-package effect, not a pure transfer-only causal increment. Conditional insurance/forfeiture value remains separately ledgered; real debt is never forgiven.

## Verify and test after extracting

Use Python with NumPy installed. From the extracted packet directory:

python -B verify_packet.py

python -B -m unittest -v test_continuation independent_review.test_independent

The verifier is read-only and does not construct a trading account. The 57 tests use synthetic observations only. No historical source is read. Bytecode files, private execution paths and external account credentials are excluded from this packet.
