# Original D partial2021: compact saved-results recovery

This packet preserves all nine separately executed original D cases: STATIC50, H090 and VOL_MANAGED_HOLD at LOW/MID/HIGH, Apr2-Dec31 2021 UTC. Each has its own fresh 10000-USDT account, 274 days and 394560 minutes. January-March data is warmup only. These are adaptive development observations. Returns are not annualized; accounts and periods are not compounded.

Start with summary/REPORT.txt, REPORT.csv, REPORT.json and DESCRIPTIVE_PERIOD_TABLE.csv. The 27-row descriptive table retains the completed 2023/2024 observations at their different 365/366-day lengths. It is not an equal-horizon ranking, OOS validation or evidence of adoption.

STATIC50/H090 raw targets differ at all three tiers. All nine approved executions were retained. Their same-tier realized financial and minute paths match post hoc, but full audits differ in scope metadata and requested/unfilled intent quantities. The three realized duplicate pairs are non-independent evidence. No alias or future execution reuse is authorized.

Financial evidence is original-byte exact, with deterministic lossless gzip for large JSON. EXACT_COPY_SOURCE_MAP.json and LOSSLESS_GZIP_SOURCE_MAP.json map public members to original relative paths, hashes and sizes. Decompressing a .json.gz restores the exact original JSON bytes. The pure saved_native_reconciliation.py is the pinned unchanged chronological native40 checker. It reconstructs saved event states without constructing accounts, advancing financial clocks or loading market arrays. Raw precision100 stored-delta residuals and legacy diagnostic booleans are retained. There is no tolerance, epsilon or forced balancing.

Run saved-only validation from the extracted packet directory:

python verify_packet.py
python test_packet.py

These checks validate member hashes, exact original recovery, typed scope identity, independent review bindings, nine saved native40 reconstructions, request-intent differences, and byte-exact JSON/CSV/text report regeneration. The negative tests corrupt authentic saved cash, debt, margin, fees, funding ownership and scope fields. They do not run the financial engine. Original review scripts are retained as evidence and are not the standalone validation entry points; some require separately pinned omitted local source arrays.

Costs, signed funding, turnover, forecast-budget overshoots, actual cash/margin/gross/asset exposure, D warning paid exits, support, conditional settlement and debt are preserved. Native funding coverage is 4110 source observations versus 4105 account-applied events after five initial fresh-flat/no-past-mark events; actual owned charges depend on each held position. Nominal risk budgets are not exact realized-risk matching. Admission caps are not continuous marked-state guarantees. All-observation MDD does not establish an intraminute high/low path. Exchange fills, funding publication/units, filters, maintenance tiers, insurance/ADL and settlement remain uncertified model assumptions.

Full MINUTE outputs and raw source/target/covariance arrays are deliberately omitted. Their hashes and sizes do not recover their bytes. Deep minute-risk/full-MDD reproduction requires the exact pinned local arrays or a separately admitted identical run. Full originals, including arrays and private process/authority bodies, are preserved unchanged locally and inventoried by a full file-set/hash/size manifest. This compact packet never grants permission to rerun finance, acquire source data, change policy or publish. Private GO, launch, bootstrap and ownership bodies are omitted; only hashes and explicit non-authority scope facts are included.

SOURCE_PUBLICATION_REFERENCE.json pins the fully remote-byte-verified source packet and its exact commit. Results publication must be an additive child of that verified source commit. No publication is performed by these saved-only tools.
