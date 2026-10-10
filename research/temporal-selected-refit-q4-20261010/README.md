One fresh full-data refit selected by the completed six-fit study at `08a6b0546ddef301645bd71380b51836d4afe702`: Adam0.0003, original date weighting, seed20261009, unchanged13,699 parameters, exactly256 updates. All773 active dates/778 decisions in five original wallets, same train-only907-row scaler. `DECISION.json`, source hashes in `prefit/READY.json`, initial checkpoint and focused test receipt are published before optimization.

Run from repository root with the official CPU dependency recipe in `research/temporal-july-frozen-transfer-20261010/requirements-transfer.txt`. Set PYTHONPATH to root and src; use the existing `BOUNDED_RESIDENT_RUNTIME.py` guard (1CPU,2GBresident/4GBvirtual/shared8GB,1200seconds,swap0/GPU0):

```sh
python -m modules.temporal_selected_refit prepare --state STATE --output OUTPUT
python -m modules.temporal_selected_refit worker --state STATE --output OUTPUT
```

The worker checkpoints every complete update; bounded slice recovery restores model, Adam, Python/NumPy/Torch RNG and progress. Only terminal256 is selected. No reserve stopping, recipe adjustment, or extra fits. Q4 is project-seen but untouched by this tuning study; score once after refit freeze against fixed VOL, Static50 and Cash50. Daily surrogate only; native replay follows exported requests. Supplied Q4 economic source is152606ad56fe6d8943b27ce89c8c57e2068ee944; Dec31 00:01:00.000001 UTC paid closure, no synthetic input rows or later return.

The refit completed exactly256 updates in710.112s, no failure. All13 Adam states have age256. Frozen checkpoint SHA256 `58db72621c9596a195267869a9cfa75f56c52162521f3ff77bf5d69c7d7bb88a`, model identity `38eb7275e4f69382083cbc3d81463d5fd2de955be2ad55919bed42c55c435e84`; public freeze6124170 was byte-verified before Q4 input access. The original fitting sources remain unchanged.

Q4 input binding:155 real feature rows,92 windows of64×5×24 plus24 masks/time masks and18 current expert inputs; original ten-asset aggregates and scheduled weekly rank state. Same pre-May907-row scaler, no Q4 normalization fit. Supplied derived tables/NPZ from152606ad were materialized offline and byte-verified, with independent strict-prior event funding reconstruction; no provider acquisition or minute-wallet replay. Real92 prices/91 funding intervals, no economic padding. Six synthetic terminal/causal/accounting tests plus two economic binding tests and two refit tests pass.

```sh
python -m modules.temporal_q4_reserved.bind --state STATE --economics ECONOMICS --fit-output OUTPUT --output INPUT_BINDING.json
python -m modules.temporal_q4_reserved.evaluate --state STATE --economics ECONOMICS --fit-output OUTPUT --input-binding INPUT_BINDING.json --output Q4_RESULT
python -m modules.temporal_q4_reserved.verify --output Q4_RESULT
```

Scoring uses an exclusive result directory and refuses a repeat. Fixed controls keep their prescribed requests; the learned raw requests are preserved. Native requests bind exact clocks, action masks, model, optimizer snapshot, scaler, protocol and source bytes. The old61-day native adapter is reference-only:92-day calendar adaptation/real native execution remains NOT_RUN. Daily boundary full-fill, continuous quantities and source venue/cost/funding assumptions remain diagnostic limitations. Financial path failures are retained and comparisons become UNKNOWN rather than fabricating a terminal result.

Test harness receipt: the combined pytest process retained a9-pass/1-fixture-error receipt because two module fixtures attempted different immutable prototype paths. The path guard remains strict. `ISOLATED_TESTS.py` verifies the same10 focused tests in three separate processes; all pass (2/6/2), with zero reserve inference/wallets. Use that runner for the aggregate suite.
