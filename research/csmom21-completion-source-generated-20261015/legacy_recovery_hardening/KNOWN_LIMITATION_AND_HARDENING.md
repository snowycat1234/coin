# Additive legacy FIRST6 pre-import hardening

The already-published legacy FIRST6 financial ZIP remains byte-for-byte unchanged:

- legacy_intrinsic_D_FIRST6_compact_saved_results_public_recovery_20261015_v3.zip
- SHA256: 1a7cd6f0bff059cb76053dd6a41b4e6c03e45291f1fb26fda1a3b8bb1f0afc3b

Its previously completed cold saved-proof and corruption checks under normal Python with -B remain valid. The original launcher uses assert for pre-import checks. Optimized Python (-O or PYTHONOPTIMIZE) removes those assertions, so that original launcher must not be used in optimized mode.

hardened_legacy_first6_recovery.py is a small, separately reviewed additive launcher. Obtain this sidecar and the ZIP digest from trusted publication/review records before running them. It uses explicit exceptions, requires the exact externally known digest, rejects missing/wrong trust before raw-file opening, then verifies the actual outer ZIP hash before ZIP parsing or packet imports. Duplicate/unsafe names, symlinks/nonregular entries, unsupported/encrypted members, more than512 members, individual expanded members over4 MiB, archives over16 MiB and total expansion over32 MiB are rejected before extraction. Fresh extracted member bytes are checked exactly.

This sidecar explicitly refuses optimized Python (-O or PYTHONOPTIMIZE) before any archive access or packet import. Normal Python with -B is the supported mode. The default mode checks the boundary and safe fresh extraction only. Optional --verify-saved invokes the unchanged saved-only financial verifier from the exact trusted ZIP. It does not run the original launcher or any historical financial/source process.

Use the archive path and mandatory --trusted-zip-sha256 argument. --receipt may specify a new local JSON receipt. This sidecar does not alter or reupload the old results ZIP, rewrite previous reviews, replay cases, capture sources, call providers, create accounts or grant execution authority. It is published beside the completion SOURCE packet, outside that immutable source ZIP.
