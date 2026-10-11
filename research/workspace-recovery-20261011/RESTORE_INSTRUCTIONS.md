# Tested public recovery

The complete data/source transport commit is
30158b15702ec42b9b650bb9fa028c4ac55a6e8f. The final audit commit adds only audit,
resource receipts, direct bootstrap guard and these instructions. Pin that final
commit when available; no branch/default-head assumption is needed.

## Layout and acquisition

Use a fresh writable workspace with at least 15 GB free. Preserve any existing
files; the restore helper rejects differing bytes. Create an independent Git
transport checkout of research/workspace-recovery-20261011 using blob filtering
and a sparse checkout containing only research/workspace-recovery-20261011/.
This downloads this minimum recovery package, not every archived research body.

Create a separate financial repo at coin_single_stream from the exact commit
55434edfb4d6b9e8ba2b0176ce449dd739737231. The tested sparse paths were:
AGENTS.md, src/, tests/, scripts/, research/recover-frozen-runner-20261009/,
modules/transformer_v2/portfolio.py, modules/collector_research/pipeline/,
modules/collector_research/validation/data.py, third_party/jesse_example_donchian/,
third_party/jesse_example_smacrossover/. Exclude transport directories and ZIP,
bytepart, NPZ and parquet bodies in that financial checkout. The source archive
and complete manifest supply state files, including the recipe helper.

Fetch these two published commits with blob filtering into that financial repo:
d69e9ac94478c5be54cb46c622afec7aaf3c61f7 and
be48f5519c23f0e64eb4d75f8b8358915c254f7b. Their objects are referenced by the
frozen MINIMUM_SOURCE_PLAN.json instead of being duplicated on this branch.

## Runtime and resource guard

Python 3.12.14 was used. Recreate coin_runtime from requirements-runtime.txt,
using a workspace-local package cache and normal official package sources. The
independent verification reused this already pinned runtime; it did not reinstall
another copy. The direct bounded_cloud.py is the exact reconstructed launcher
SHA256 99432c34f2b7e6411ec9b68e5370deded6d1a94e6ff08d71e22e4a1164df914e.
Its identity is a reconstructed policy, not known original pre-loss bytes.

Run each Python stage through that guard with a unique --report path and at most
1200 seconds. It uses one CPU/thread, no GPU/swap, RSS 2 GB, address space 4 GB
and host-used stop 8 GB. Receipts are immutable. No cgroup-wide guarantee is
claimed. Keep project/cache/data in the writable workspace.

## Restore and verify

The following paths are relative to the workspace. Replace TRANSPORT and COMMIT
with the transport checkout and the pinned final commit. Every archive/chunk and
member is verified before a state file is written; ZIP paths and duplicates are
checked. No network is used by RESTORE.py itself.

coin_runtime/bin/python TRANSPORT/research/workspace-recovery-20261011/bounded_cloud.py --report restore-resource.json --seconds 600 -- coin_runtime/bin/python TRANSPORT/research/workspace-recovery-20261011/RESTORE.py --git-repo TRANSPORT --commit COMMIT --workspace .

coin_runtime/bin/python coin_single_state/bounded_cloud.py --report seeds-resource.json --seconds 1200 -- coin_runtime/bin/python coin_single_state/recovery-20261011/recover_minimal.py recover

Create coin-recovery-state as a symlink to coin_single_state only if absent. Never
replace an existing unrelated path. To rerun the write-once source verifier in
this new scratch restore, rename VERIFIED_RECOVERY.json to
PUBLISHED_REFERENCE_VERIFIED_RECOVERY.json first, preserving its bytes. Then run:

coin_runtime/bin/python coin_single_state/bounded_cloud.py --report targets-resource.json --seconds 600 -- coin_runtime/bin/python coin_single_state/recovery-20261011/verify_recovery.py

The regenerated report must match the reference exactly, SHA256
ede49e1b3b796f30c2cc18b476d0b44056056072b54f17203625de80f41cf14a.
Set PYTHONPATH to the absolute coin_single_stream/src and coin_single_stream
paths, and QUANT_ROOT to the absolute coin_single_stream path. Run under the guard:

coin_runtime/bin/python -m pytest coin_single_stream/tests/test_perpetual_account.py coin_single_stream/tests/test_native_margin_risk_summary.py coin_single_stream/tests/test_q4_native92.py -q --basetemp=coin_single_state/pytest-fresh -o cache_dir=coin_single_state/pytest-cache

Independent restoration verified 30 official ZIPs/60 chunks and 109 unique
source/derived members. All 48 financial source hashes and 365 CS/VOL mapped
rows match; the 38 original tests pass. The first external-CWD test invocation
omitted PYTHONPATH and failed collection; its receipt is retained. No financial
rule, source hash, test or strategy recipe was changed to make it pass.

## Coverage and missing originals

The package covers public Jan-Jun2026 trade-price warmup only: 260,640 minutes
per asset, 1,303,200 asset-minutes, 181 new daily bars, 2,373 combined daily price
rows per CORE5 asset. Last completed availability is July1 from June30 prices.
These Q1/Q2 dates had already been consumed by earlier studies. No premium or
funding is imputed. Original Q1/Q2 adapters, native mark/funding tapes, financial
ledgers and terminal checkpoints remain missing. Their old result hashes are
historical receipts, not replacement artifact bytes. This package cannot restore
those financial checkpoints or provide a complete Q1/Q2 native market tape.

New July/August outcomes remain closed under the collector reserve; no Q3 archive
or account was acquired/run. The AGENTS lock wording/source constants are
unchanged; no separately reserved collector dataset was opened. Older snapshot
files inside SOURCE_RECOVERY.zip record their pre-publication state; the final
PUBLICATION_AUDIT.json records this later durable publication.
