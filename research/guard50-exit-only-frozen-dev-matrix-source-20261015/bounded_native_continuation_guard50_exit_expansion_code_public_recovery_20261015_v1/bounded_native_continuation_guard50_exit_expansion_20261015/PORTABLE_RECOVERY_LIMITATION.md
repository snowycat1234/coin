# Remaining portable recovery dependency

This is a separate metadata/recovery limitation. It does not alter the current fixed 17-cell manifest, financial code, source/targets, preparation or admitted scope.

The current expansion entry treats old authorization receipts as immutable historical evidence, never as new authority. However, `expansion_entry.preserved_evidence_identity()` still calls the ordinary-file exact-byte reader on every historical evidence pin. That function is used during source preparation, preparation validation and sealed-scope current validation. Consequently these four old GO bodies are **actual current runtime dependencies**, even though the public source packets deliberately omit private-prefix-bearing old GO contents:

- `traditional_three_tier_freeze_20261015/root_go_2024_pilot_attempt001.json`, SHA256 `a6a3f4b36a7fe008d99a140b32bc41a86f14c8bae281f068aac3b684c8a43851`
- `traditional_three_tier_freeze_20261015/root_go_2024_remaining_attempt001.json`, SHA256 `ab8f768beef74b0d45d8231a743fa5d25a919a6230cb166a71fd56d891e9a4b7`
- `traditional_three_tier_freeze_20261015/annual_go/ROOT_GO_2023_PILOT001.json`, SHA256 `6930d9450279f652db8f6b644ec00043a6cedb166410191859c2f666d62f37ef`
- `traditional_three_tier_freeze_20261015/annual_go/ROOT_GO_2023_REMAINING001.json`, SHA256 `c46cc26b8039c372ec973557a9b6a2fd8b4b0f80f354612795b1da9eb60489e0`

The same reader also requires exact old independent-review bytes, the original completed 2024 STATIC50 MID D receipt (`b23e84937ec85275187b14785ec815e5f50e7bb0b7e81ba2cce99f9fa91b8dc5`), and its paired-review receipt. Source/data and generated-test recovery are not a claim of fully self-contained cold historical execution. Restoring public code/data alone does not currently eliminate these evidence-file dependencies; a fresh GO alone does not bypass their absence.

## Separate post-batch metadata-only recovery entry

After this batch, an independently reviewed new entry can separate (a) immutable historical evidence *hashes* in a public provenance catalog from (b) files actually needed to reconstruct and validate source, targets, quality, fresh genesis and execution policy. A new external review and fresh scoped GO would remain mandatory. Omitted old private GO bodies would not become new authority or be reconstructed from sanitized copies.

That entry needs a distinct code/preparation/review/GO identity and explicit numeric-equivalence evidence: identical frozen finance and D monitor code objects, identical source/target/decision/covariance/profile bits, generated complete financial/pending/quality path equivalence, and exact saved native40 arithmetic checks. It must leave this batch and all original failures/receipts unchanged. No such portable historical entry or authority is provided by this note.
