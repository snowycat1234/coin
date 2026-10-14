# Independent portable native grid source review

## Result

PASS for generated-only, from-start mechanics at portable freeze
`732c04cd365c06b487ccbaff1c5916e23e73bb6d9718c663450d0f1603f0a6f0`.
Prior scientific provenance remains frozen c249
`c24974783e50ec8b83b199e1c6b271e75fe87d58951c4d581ce53dd46ddf1a0b`.

All 59 tests passed: 6 binder tests, 7 new mathematical/transport tests,
20 unchanged producer tests and 26 byte-exact independent native-adapter tests.
The mathematical tests independently recomputed the original signed risk,
asset/gross cap and covariance formulas over 160 generated cases, then checked
completed 30-day covariance, fixed budget sizing, future-suffix invariance and
negative inputs. The unchanged native tests cover scheduler, isolated-1x shared
account, actual/pending risk admission, original-target fallback, hard-risk
priority, weekly expiry, sign reversal, exact fees/funding ownership, capacity,
partial fills, stale/cancelled orders and the original terminal60 opportunities.
The prior exact helper's 81-test review remains reused; no helper recipe changed.

Fresh serial exports reproduced all 33 native/owner economic journal bodies
exactly, with recursive type checks and no Decimal or numeric normalization.
The unchanged independent Decimal audit passed 754 fill legs and 300 applied
funding events. GENERATED_SUMMARY.json was raw-byte identical to c249, SHA256
`c4b41450885af676098b7229688bf210f6c13bcd7f84705d94f73a705aa97528`.

Complete journal JSON was separately equivalent after only session/order UUID
alpha-renaming and sorting four documented set-derived lists. Session timestamps,
order suffixes, repeated-reference consistency, all fields and all scalar types
were retained. Nine mutations, including financial values, clock/type changes,
crosswired identifiers, new fields and duplicate set entries, were rejected.
Fresh raw journal files were not byte-identical to c249. The saved c249 archive
must retain its exact original raw bytes; these are different claims.

## Source and cold boundary

The reviewer copied only the 51 declared source/code-metadata files plus the
freeze manifest into a fresh tree, without the old adjacent c249 locator,
arrays, caches or bytecode. All five scientific top-level bodies were unchanged.
All 38 immutable carrier SHA256/size/GitBlob identities and the 28 original raw
code inventory entries verified. Both frozen source sets remained unchanged.
No original financial, execution, scheduler, cost or terminal function was patched.

Six independent cold stages ran with an audit hook prohibiting array-file opens
and any warm workspace source reads outside explicitly declared third-party
runtime sites. All 279,773 observed open events completed with zero prohibited
attempts. Each child was bounded to one CPU, 4 GiB address space, 120 CPU seconds
and 180 wall seconds. Combined stage wall time was 94.319 seconds; peak child
RSS was 140,860 KiB. Runtime matched Python 3.12.14, NumPy 2.3.5,
Polars 1.44.2 and PyArrow 23.0.1, with explicit source/spec/site-priority checks.

The new binder explicitly refuses the original 26-file historical admission,
saved target and source-window entry points. It never opens or hashes historical
target arrays. The earlier c249 gate's distinct target-byte hashing boundary is
preserved in prior evidence and is not relabeled as this code-only gate.

## Evidence and correction

FINAL_ACCEPTANCE.json binds REVIEW_RECEIPT_0002.json, exact native-body parity,
the complete equivalence receipt and the exact summary. Source-bound runner,
test and comparison bodies, successful logs and the unchanged Decimal audit
are included. The original independent 26-test source is included unchanged.

The first reviewer guard run had a false positive on relative `os.open` cleanup
through a directory file descriptor. Python's audit event omits that descriptor;
the original guard incorrectly resolved the temporary directory name as a
workspace source path. The correction and failure receipt are retained under
reviewer_harness_preliminary. Its traceback has a labeled workspace/stdlib-prefix-only
projection with original and projected byte hashes. This was a reviewer harness
issue, not an adapter failure or financial change.

This artifact is independent source-test evidence. Its run_cold_review.py records
the original review-workspace layout and is not the public package launcher.
The separately frozen public cold wrapper supplies consumer-local runtime sites,
fresh output and the portable locators. Public transport acceptance is a separate
review against that wrapper's final exact manifest.

## Limits

No historical wallet, market-data download or historical source run was used.
No realized/future risk-parity certification, live Bybit equivalence, historical
GO, or restore/fork/split parity is granted. Equal risk caps and original-target
envelopes are admission mechanics; later matched actual-ledger analysis would be
needed to assess realized risk. The fixed CASH trim remains a diagnostic exposure
control rather than an automatic risk-parity guarantee. Unpaid native terminal
residuals remain visible. Source/runtime changes require a new bound review.
