# One dense-training ablation

Read REPORT.md and FROZEN_DENSITY_PROTOCOL.md first. The single actual fit is complete; do not rerun a fit. FIT_RECEIPT.json blocks accidental actual-data restarts, including after failure. Use saved coefficients for verification:

    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python ranker.py reproduce --directory .
    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python verify_saved.py
    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m unittest -v test_ranker test_dense

Requires Python, NumPy, SciPy and threadpoolctl; fit-time versions are recorded in FIT_RECEIPT.json. Unit tests include tiny synthetic optimizer calls, not fits on the actual training data. Reproduction and verify_saved do not call any optimizer. The runner reproduction checks exact equality in the recorded environment; verify_saved uses tight tolerances for numerical arrays and direct objective/gradient, and exact identity/choice/count checks.

RESULTS.json names the dense model `challenger`, frozen original40 model `original40`, saved Ridge `state`, and fixed original40 CASH baseline `cash_train_best`. `models` summarizes the same fixed22 diagnostic dates; `all_mature_models` summarizes all176 mature dates. `all_182_scoring_rows` provides all states and predictions. `dense_vs_original40` provides paired comparisons for both scopes. Pairwise accuracy for CASH is undefined and stored as null.

The 301 overlapping training dates are not independent observations. The retained original40 rows provide separate disjoint admission support. All reported evaluation is repeatedly seen DEV.
