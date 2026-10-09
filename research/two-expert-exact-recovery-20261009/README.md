# Exact two-expert policy recovery

This small recovery bundle preserves the original 3/6-parameter heads and both original 64-epoch checkpoints byte-for-byte. No fitting or wallet replay occurred during recovery. Four fixed training/validation NPZ fragments and their exact index are retained. All exact hashes are in MANIFEST.json and RECOVERY.json.

Original metadata JSON bodies and optimizer moments were not retained by the executor. Newly generated metadata is explicitly marked as reconstructed. Native journal bodies and auxiliary execution dependencies remain missing; this bundle does not claim execution readiness. Completed six-wallet numerical results are transcribed and clearly distinguished from original journal evidence.

The original byte-bound training archive is already public at commit d69e9ac94478c5be54cb46c622afec7aaf3c61f7, research_artifacts/direct_path_fragments_20261008/coin_direct_path_byte_bound_fragments_20261008.zip, SHA256 5c693dbae6a8702d5304d92e5890697a11ffa1f5579b69f05dd16322f248aef5. Its four unchanged source-receipt files are referenced rather than republished. To restore, resolve the checkout directory, verify that public archive's SHA and ZIP CRC, and copy only its fragments/*_SOURCE_RECEIPT.json.gz files into direct_path_fragments/. Every required receipt hash is recorded in RECOVERY.json.

A future optimizer continuation must exactly reproduce the original 64 steps before taking a new step, remain within the predeclared training-only stopping/resource limits, and freeze both terminal models before scoring validation. Wallet execution additionally requires the separately recovered original guard-OFF native engine and real input bindings. No live trading, new data retrieval, or policy tuning is included.
