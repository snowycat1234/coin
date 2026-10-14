# Independent native-pair miniature oracle

Six independently written toy tests, against V1 exact commit 6a8bf05102a2b08a4df0cf65549970b2eb1c1797. No historical wallet, market-source scan or target archive is run. This evidence does not authorize economics. V1 remains NO_GO; the missing original diagnosis receipt remains pinned.

## Restore and run

Restore the 23-file module at that exact commit/directory and this additive oracle. Use its immutable SYNTHETIC_DEPENDENCIES.json and restore_synthetic_dependencies.py to restore the 69 compact original code/identity/reference files into a fresh directory from an already available same-origin Git cache:

```sh
python "$MODULE/restore_synthetic_dependencies.py" --git-cache "$GIT_CACHE" --output "$ABSOLUTE_FRESH_DEPENDENCIES"
PYTHONDONTWRITEBYTECODE=1 PYTHONOPTIMIZE=0 POLARS_MAX_THREADS=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  python "$ORACLE/test_native_pair_oracle.py" --module "$MODULE" --roots "$ABSOLUTE_FRESH_DEPENDENCIES/SYNTHETIC_ROOTS.json"
```

MODULE is the restored original module directory; ORACLE is this independent_oracle directory. Explicit --module permits another restoration location; default is the parent of the oracle directory. The roots file is generated locally and is not public metadata. Do not add --fetch-missing unless fetching the exact public source is separately permitted. If optional package files are installed workspace-only, include their directory on PYTHONPATH.

The tested runtime is Python 3.12.14, NumPy 2.5.3, Polars 1.44.2, PyArrow 23.0.1. Polars matches original public uv.lock. DEPENDENCY_PROVENANCE.json records official wheel hashes; no wheels are copied into this package.

## What the six tests establish

1. Actual imported financial paths and original SHA256 bindings, and original simulator/account identities.
2. Exact full miniature account/funding/minute parity between direct native arrays/target rows and normalized daily/minute-block wrapper transport; long debit and short credit belong to actual pre-fill inventory.
3. Identical second-day targets do not undo first-day financial divergence: replay the entire year for each fresh paired account.
4. Original snapshot/state-hash parity and independent signed-inventory/NAV bridge.
5. Finite, per-asset .30 and gross .60 cap failures, plus imported fine-module shadow rejection.
6. Original missing document pin and V1 economic-review, candidate-order and later-year NO_GO gates.

The native module's separate 12-test miniature suite also passed independently. Combined evidence is 18 tests, not historical compatibility or economic success. SOURCE_MAP.json identifies preserved runtime imports and guards, and describes the independently versioned replacement route. Recheck final V2 bytes and adapt only explicit interface differences before using this oracle against V2.
