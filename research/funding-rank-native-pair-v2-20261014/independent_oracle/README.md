# Independent V2 loader correction tests

Base publication: ca11e94d11d9c40275f54a77397c30f3d9181e7b, research/funding-rank-native-pair-v2-20261014. The loader correction changes only v2_launcher.py and its matching V2_FREEZE launcher hash. All financial originals, dispatcher, adapter, source/targets, protocol and closure remain unchanged.

Use the parent module's SYNTHETIC_DEPENDENCIES.json and restore_synthetic_dependencies.py to restore its 39 exact compact public source files; no market data is needed. See the parent README for restore instructions. With the pinned runtime available, run:

```sh
python "$MODULE/test_v2_synthetic.py" "$ROOTS_JSON"
python "$MODULE/independent_oracle/test_v2_independent.py" --module "$MODULE" --roots "$ROOTS_JSON"
python "$MODULE/independent_oracle/test_loader_shadow_regression.py" --module "$MODULE" --roots "$ROOTS_JSON"
```

Run with PYTHONDONTWRITEBYTECODE=1, PYTHONOPTIMIZE=0, POLARS_MAX_THREADS=1, OPENBLAS_NUM_THREADS=1, OMP_NUM_THREADS=1. Tested Python3.12.14, NumPy2.5.3, Polars1.44.2, PyArrow23.0.1.

Results: 11 published plus6 independent plus1 regression PASS. The regression covers 19 actual file-backed financial/runtime modules and 38 path/spec-origin rejection subcases; it preserves the original intentional in-memory strategy stub. Independent fixtures compare direct native finance with the actual worker-style minute-block transport and actual dispatch calendar/checkpoint/output loop, prove persistent account divergence despite reconverged targets, and check target/review/GO failures. No historical wallet/source replay, target generation, or economic authorization occurs.

These receipts are miniature evidence, not the external publication-review/parent-GO documents that the dispatcher requires. Original ca11 bug evidence is retained separately; V1's missing diagnosis pin is not changed or waived.
