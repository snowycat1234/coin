One fresh full-data refit selected by the completed six-fit study at `08a6b0546ddef301645bd71380b51836d4afe702`: Adam0.0003, original date weighting, seed20261009, unchanged13,699 parameters, exactly256 updates. All773 active dates/778 decisions in five original wallets, same train-only907-row scaler. `DECISION.json`, source hashes in `prefit/READY.json`, initial checkpoint and focused test receipt are published before optimization.

Run from repository root with the official CPU dependency recipe in `research/temporal-july-frozen-transfer-20261010/requirements-transfer.txt`. Set PYTHONPATH to root and src; use the existing `BOUNDED_RESIDENT_RUNTIME.py` guard (1CPU,2GBresident/4GBvirtual/shared8GB,1200seconds,swap0/GPU0):

```sh
python -m modules.temporal_selected_refit prepare --state STATE --output OUTPUT
python -m modules.temporal_selected_refit worker --state STATE --output OUTPUT
```

The worker checkpoints every complete update; bounded slice recovery restores model, Adam, Python/NumPy/Torch RNG and progress. Only terminal256 is selected. No reserve stopping, recipe adjustment, or extra fits. Q4 is project-seen but untouched by this tuning study; score once after refit freeze against fixed VOL, Static50 and Cash50. Daily surrogate only; native replay follows exported requests. Supplied Q4 economic source is152606ad56fe6d8943b27ce89c8c57e2068ee944; Dec31 00:01:00.000001 UTC paid closure, no synthetic input rows or later return.
