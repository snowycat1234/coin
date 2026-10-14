# Separate 2025 candidate recovery transport

This package is a distinct transport version, not a patch to the original 519b17f6 financial worker. It does not rerun control, change financial methods, alter source or targets, edit the original failed ledger, or claim the old transport succeeded.

The original 2025 control completed its saved 365-day financial state and all nine outputs, but its process exited -9 at the original 250,000,000-byte cap. The original ledger retains that failure. Actual retained case size was 250,426,051 bytes. A separate native zero-advance recovery at immutable commit 9eb7c529 validates the full saved state without financial advancement.

New admission additionally requires a hash-pinned compact recovery-admission receipt binding the exact final POINTER.json, its 365 chunk hashes, and all eight original source/target/publication/review/GO binding fields. Only after those checks is EFFECTIVE_COMPLETION_INPUT.json written, explicitly identifying recovered financial completion and the failed original attempt. This input is for the new transport; the original completed list remains unchanged.

The unchanged original dispatcher.py --worker is then called for one fresh 2025 candidate, with its original publication, source, saved-target, imported-financial, independent-review and original pair-GO gates. No financial worker or kernel code is copied or rewritten. A separate independent new-transport publication review and explicit candidate-only parent GO are mandatory before dispatch.

The new GO pins the exact roots JSON and a single deterministic output namespace beneath its workspace, preventing a second candidate through another output path. Existing output or a prior attempt is never overwritten or resumed.

The new output cap is explicitly 500,000,000 bytes, approximately twice the observed control output, and remains enforced. The old 250MB cap and failure are preserved. CPU1, RSS2GB, AS4GB, case600s, cumulative3600s, disk15GiB, original host/swap/cgroup/reservation and shared-controller exclusion remain. Actual original elapsed1308.5219291619942s is carried forward; no cumulative or case deadline reset occurs. New ledger and provenance are separate.

Run only the toy guard suite before external review:

    PYTHONDONTWRITEBYTECODE=1 python test_transport.py
    PYTHONDONTWRITEBYTECODE=1 python test_independent_transport.py --module .

Toy checkpoint metadata is never interpreted as a financial wallet or historical source. These tests do not establish historical candidate results. A transport worker exit success is still pending independent result review.

Required external review schema: INDEPENDENT_RECOVERY_TRANSPORT_PUBLICATION_REVIEW_V1, status PASS_EXACT_RECOVERY_TRANSPORT_NO_HISTORY, publication_commit, TRANSPORT_FREEZE_SHA256, recovery_receipt_SHA256, recovery_admission_receipt_SHA256.

Required new GO schema: EXPLICIT_PARENT_RECOVERED_CONTROL_CANDIDATE_ONLY_GO_V1. Its precise fields are checked by transport_authorization in recovery_transport.py. The old pair GO alone cannot authorize the resource change or this new transport.

Required recovery-admission schema: VALIDATED_FULL_CONTROL_RECOVERY_ADMISSION_V1, status PASS_SAVED_FINANCIAL_COMPLETION_ORIGINAL_TRANSPORT_FAILED. It binds original/recovery commits, original failed ledger, zero-advance receipt, results, snapshot, state hash, final POINTER, completed minutes/chunks, all-eight-field checkpoint binding, zero financial advance calls, and preserved original transport failure.
