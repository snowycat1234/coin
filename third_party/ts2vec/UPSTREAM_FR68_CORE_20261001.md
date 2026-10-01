# TS2Vec minimal official core

Repository: https://github.com/zhihanyue/ts2vec
Commit: b0088e14a99706c05451316dc6db8d3da9351163
License: MIT

Original files, complete LICENSE and Git blob/SHA256 bindings retained.
Local changes: three package-relative imports in ts2vec.py; package export.
No new convolution, encoder, contrastive loss, representation framework or trainer.
Upstream data_dropout uses np.bool; the pinned NumPy 2.5.3 alias exists, and this utility
is not used by the adapter. No speculative compatibility modification.
CPU integration only. Common dataset owns windows, labels and frozen train normalization.
Bidirectional representation uses the full supplied past window; no token-level causal claim.
