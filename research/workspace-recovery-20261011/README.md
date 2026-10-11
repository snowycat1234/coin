# Workspace recovery, 2026-10-11

This branch preserves the working recovered native finance code, source hashes,
recipe helpers, conservative resource launcher, reconstruction reports and restore
instructions. It starts from existing financial source commit
55434edfb4d6b9e8ba2b0176ce449dd739737231. No old branch/history is replaced.

First durable package: SOURCE_RECOVERY.zip and SOURCE_MANIFEST.json. Verify the
ZIP SHA256 and every declared member before extraction. Reject unsafe paths,
duplicates and undeclared members. Map state/... into a fresh workspace's
coin_single_state/..., preserving any existing differing bytes. Restore the full
financial repo as coin_single_stream from the pinned base commit, and reconstruct
the Python runtime from the package's RUNTIME_FROZEN_SUCCESS.txt with a workspace
local package cache. The launcher is a reconstructed policy, not known original
bytes. Published source archives are reused by exact commit/hash in
MINIMUM_SOURCE_PLAN.json; recover_minimal.py obtains only necessary pinned parts.
Run it at coin_single_state/recovery-20261011/recover_minimal.py in that layout.

Verified: 48 financial source hashes; 25 original account/margin tests; 13 native
terminal/resume tests; all 365 saved 2025 CS/VOL targets and budgets reproduced
exactly. 30 official previously-seen Jan-Jun 2026 trade ZIPs yield 1,303,200 asset
minutes, 181 daily bars per asset and 2,373 combined daily price rows. The raw
warmup and derived bytes will be persisted in subsequent bounded commits; consult
PUBLIC_RECOVERY_INDEX.json when present for their complete restore mapping.

The original unpublished Q1/Q2 adapters, mark/funding tapes, financial ledgers and
terminal checkpoints are still missing. Remembered old result hashes cannot
restore their bytes. Reconstructed 2026 price inputs explicitly have unknown
original byte identity; price-only recovery is not a complete native tape.
Q3 has not been acquired or replayed. July/August remain reserved. No financial
replay or model fit was performed during recovery.

HANDOFF.json and README.txt inside the source archive are immutable snapshots
from before publication and therefore record zero writes/local-only durability.
This branch is the subsequent publication; do not read the earlier snapshot's
publication status as current. Local 93MB convenience copies contain redundant
already-public archive parts and are deliberately not uploaded wholesale.
