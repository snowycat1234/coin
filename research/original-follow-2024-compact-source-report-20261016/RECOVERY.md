# Isolated compact cold read

Authenticate ZIP and launcher SHA256 from an independent trusted receipt. Python stdlib only; no package install.

Run python -I -S -B run_isolated_cold.py PACKET.zip --trusted-zip-sha256 TRUSTED_SHA256 --receipt NEW_NORMAL.json --cache-root NEW_CACHE_DIRECTORY

Run a separate python -O -I -S -B process with the same ZIP and --cache-root plus --reuse-cache, writing NEW_OPTIMIZED.json. The normal run creates a fresh cache; the optimized run authenticates the ZIP again and byte-verifies every member and exact cache inventory before installing its independent read/exec/write/network boundary. Only one small retained cache is needed. No cache is deleted by these tools.

The launcher rejects unsafe paths, case collisions, encrypted/nonregular entries, oversized inventories and wrong outer hashes before executing authenticated reader code. The isolated reader can read only the packet and stdlib, write only its fresh receipt and cannot run historical code or network/process actions. Eight negative boundary probes must fail. Exact final CSV and JSON field binding, audit/checkpoint/proof/source/authority identity, raw-vs-stored compression pins, scope and omissions are checked. This is a saved-report/source-binding check, not native40 financial replay or target recomputation. Historical builders and snapshot CLIs are inert and must never be run.
