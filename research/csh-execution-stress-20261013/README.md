# Fixed original fine STATIC50 execution sensitivity

See REPORT.md for six final cases, exact freeze, timing, economic comparisons and recovery scope. Public artifacts support readonly indicator and financial reconstruction; this is not complete checkpoint byte cold recovery. Full original checkpoints remain in the current instance. No automatic historical launch.

## Public historical reproduction contract

`PUBLIC_REPRODUCIBILITY.json` binds the original freeze, financial code, source index and frozen target hashes. `public_entry.py` omits only private non-economic DEDUP verification. It replaces that metadata gate for a newly explicitly authorized invocation; original `run.py`, FREEZE and financial results remain unchanged.

Missing from the public packet: original raw/source month tapes (restore them), complete per-asset minute checkpoint fields, private DEDUP metadata. The latter is not needed by the new public gate. The 2025 source index also references two unused prior native risk-study outputs; this strategy uses separately pinned frozen targets instead. Historical replay was NOT executed through the new entry: only source recovery and the nonfinancial hash gate were verified. Public remote cold verification reconstructs indicators and finance, not full checkpoint bytes.

From repository root, activate the prepared Python 3.12 environment with numpy/polars/pandas; enter `research/csh-execution-stress-20261013`. In a fresh restore directory at the documented default path, execute the five restore commands in PUBLIC_REPRODUCIBILITY.json. They restore pinned normal Git/public archived source bytes and original targets without constructing a wallet. Existing restore receipts prevent accidental duplicate restoration; reuse verified restored inputs. Stop on permissions or provider refusal. Restoring large original archives requires sufficient storage; do not redownload when valid caches exist.

Check: `python public_entry.py --inputs /workspace/coin-cloud/csh-execution-stress-20261013 --year 2021` (repeat 2023/2025). This checks all 60 pinned financial-code/target files and each selected year's 12 month source hashes plus raw funding/daily hashes, without financial imports.

A FUTURE newly authorized replay uses `python public_entry.py --inputs RESTORED_INPUTS --year 2021 --shock FRICTION_DOUBLE --output NEW_ABSENT_DIRECTORY --authorize-new-historical-wallet`. It creates owned output only, links immutable restored inputs, retains original resource guards and financial launcher. This command was not run in this research task; none of the six wallets were repeated. `test_public_entry.py` checks private metadata omission, corrupted financial code rejection, missing authorization rejection before output creation, and absence of financial imports.

The two upstream Git 503 interruptions and successful exact-commit cold audit are retained in evidence/REMOTE_D7CF56A.json. Same origin, TLS preserved; no alternative API domain or permission expansion.
