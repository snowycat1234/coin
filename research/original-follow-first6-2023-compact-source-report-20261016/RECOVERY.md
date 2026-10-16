# Cold report/source-binding recovery

1. Authenticate the ZIP SHA256 and run_isolated_cold.py SHA256 independently.
2. Use Python 3.12 (stdlib only). No package installation is required.
3. Run: python -I -S -B run_isolated_cold.py PACKET.zip --trusted-zip-sha256 TRUSTED_SHA256 --receipt NEW_RECEIPT.json
4. Repeat with -O if desired. All actual integrity checks use explicit exceptions
   and generated tests use unittest methods; they remain effective under -O.

The launcher verifies the outer digest before reading code, rejects unsafe ZIP
paths, case collisions, nonregular/encrypted entries, and size/count overruns.
It extracts into a fresh temporary directory, then prohibits external file reads,
historical execution/imports, network/process actions and all writes except the
fresh receipt. Its own external-read/process/import/exec controls must fail.
Only the authenticated top-level verify_packet.py is executed. Snapshot source
is read as bytes and never imported. The tiny extraction is retained for review.

Report JSON and CSV are exact final saved bytes. The reader crosschecks every
CSV field against its JSON value, all six row identities/statuses/economics,
actual-held risk summaries, proof/checkpoint chains, root exit, final audit,
source preparation identity and exhaustive dependency/omission classifications.
It does not read or reconstruct omitted financial bodies. The source-byte
snapshots and metadata are portable; their historical absolute/path literals
are inert data and are never followed by this reader.

The manifest authenticates all packet files except itself and requires exact
inventory. Authenticate the outer ZIP separately to protect the manifest too.
All historical manifests, prior review scripts and builder are inert reference
material, not authorized entry points. Never run historical financial CLIs.
