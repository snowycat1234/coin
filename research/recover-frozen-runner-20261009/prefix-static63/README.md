The four prefix-static baseline requests are bound to public export commit
57a90f59bb702eab8fe74803e7de765b350cab93 and the byte-identical selections
published before evaluation at 49c0ff4b88286ccb7131af99e88838b4015dc5be.
Choices are SHORT/VOL/VOL/VOL. No model, fit, inference or alternative rule search.

Each fold preserves its original seven-array REQUESTS.npz, including the one-hot
terminal request. All admitted context values, masks, clocks, E6 slot identities,
63 mapped targets and ramped budgets match the original cached source exactly.
The original engine owns final-day target forcing and charged flat closure.

The export's financial reference is immutable April contract SHA256
5163c9b4e0cf7305662b715b46d0dabd4e8de35fc8ee38728aff8ff74f9c9b77.
New ADAPTER_CONTRACT.json bindings explicitly associate those unchanged financial
semantics with each existing fold calendar, cached canonical context and actual
trade/mark/quote-USDT/funding tape. The April calendar is not reused for other
folds. Existing contracts, market bytes, retrieval provenance and funding event
offsets remain unchanged. Historical publication and exchange/account rules
remain uncertified.

Execution uses exact guard-OFF engine SHA256
318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585:
fresh10k, isolated1x, MMR.005, fee5.5bp each side, spread/slip4/4bp, actual
signed funding scale1, gross/asset targets .6/.3, daily expert L1 .1, causal
30-day covariance/10% annual risk mapping, original Jan1 2024 rank anchor,
previous-minute quote participation .001, lot1e-8, minimum opening notional10,
delayed/partial fills, reductions first, five-attempt expiry, funding before
fills with strictly prior completed marks, and paid terminal-flat closure.
Fresh previous_quote=None and zero initial capacity/positions are checked.

Ten synthetic fixture checks cover changed terminal requests, future clocks,
wrong masks, reordered slots, covariance mismatches, tampered checkpoints and
bit-identical continuation through partial orders, funding and charged closure.
Existing financial sources and shared acceptance evidence are unchanged.

Each EXECUTION_PLAN.json authorizes exactly one new account on its explicit
calendar. Run only these four; reuse the twelve completed GRU/Static50/Cash50
accounts linked by prequential-four-folds/COMPARISON.json. No provider download,
training, account stitching, parameter tuning or completed-wallet rerun.

The runner commits a durable snapshot at every complete daily boundary. The
unchanged engine's full snapshot is transported as JSON plus immutable numeric
minute chunks and a source/request/plan-bound atomic CHECKPOINT.json. Resume
uses NativeDailySimulator.from_snapshot with BybitIsolatedAccount, verifies all
bytes, original account journals and live state, then advances from the next
uncompleted day. An externally interrupted day can replay from its prior
committed boundary in the same original account. Financial failures stop;
audited completed accounts cannot restart. Final account publication is atomic.
Final checkpoint restoration advances no wallet. Resource caps remain one CPU,
6GB, cumulative600seconds/account and 15GiB free disk reserve.

READINESS.json retains exact source and grid checks. Recorded prefix means and
strict maturity are verified against the precommitted selection receipt; the
underlying standalone label means are not recomputed. Surrogate result paths
are parity/evidence references, never native market input or tuning targets.

Use the existing requirements-native61.txt dependency recipe and retained
source/data state. For a published plan commit, run:

    python prefix_static_native63.py run --state STATE --fold FOLD_20230703 --plan-commit COMMIT

The same command resumes that fold's reserved original account after an external
interruption. Substitute only the other three declared fold names. Results and
checkpoint archives are split into hashed768KiB GitHub parts. Public readback
checks original journals, restores the exact final engine state and independently
audits actual fills/capacity/costs/funding without advancing a wallet.

Results are historical development evidence on repeatedly examined periods,
with unequal realized risk. They cannot establish pristine OOS, APR, convergence
or executable switching profits. The prior failed prequential screen is retained.
